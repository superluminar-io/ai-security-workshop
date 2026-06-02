# Design: Migrate to Bedrock AgentCore Runtime

## Context

The workshop app currently runs a Strands agent in-process inside a local Flask server. Each participant runs `python server.py`, which initialises a `BedrockModel` + `Agent` locally and calls Bedrock directly. The goal is to move the agent runtime to AWS Bedrock AgentCore Runtime (cloud-hosted container) while keeping the local Flask server as a thin UI proxy. This removes the Strands/agent dependency from participants' local environments and centralises the agent lifecycle in AWS.

The SQLite database is a preseeded demo (prompt-injection, insecure tools) and does not need to persist between sessions. It lives inside the container and resets on restart.

---

## Architecture

```
Browser
  │
  ▼
Flask server.py  (local, port 5000)
  │  boto3  bedrock-agentcore-runtime
  ▼
AgentCore Runtime  (AWS managed container)
  │
  ├── agentcore_app.py      BedrockAgentCoreApp entrypoint
  ├── tools.py              Strands @tool functions
  ├── db.py + SQLite        ephemeral /tmp/ecomm.sqlite, initialised at startup
  ├── policy.py             permissive baseline (workshop hardens this)
  └── prompts.py            deliberately unsafe system prompt
```

Each browser tab gets a UUID session ID (stored in Flask session cookie). Flask passes this as `sessionId` to AgentCore Runtime, which maintains conversation history within the session. `ACTOR_CUSTOMER_ID` is included in the invocation payload so the container does not need per-participant environment variables.

---

## Files

### New files

| File | Purpose |
|---|---|
| `agentcore_app.py` | Container entrypoint. Initialises SQLite in `/tmp`, creates the Strands agent, serves via `BedrockAgentCoreApp` on port 8080. |
| `Dockerfile` | Python 3.11 slim image. Copies all workshop Python files. `CMD ["python", "agentcore_app.py"]`. |
| `infra/app.py` | CDK app entrypoint. |
| `infra/stack.py` | CDK stack: `DockerImageAsset` (builds + pushes image), IAM role for the runtime, `CfnResource` for the AgentCore Runtime L1 construct. Outputs the runtime ID. |
| `cdk.json` | CDK config pointing at `infra/app.py`. |

### Modified files

| File | Change |
|---|---|
| `server.py` | Remove `_get_agent()` and all Strands imports. Add boto3 `bedrock-agentcore-runtime` client. Generate UUID session IDs per browser session. Call `invoke_agent_runtime` per chat POST. |
| `app.py` | Remove `_llm_mode()` and Strands imports. Default to command mode only. |
| `pyproject.toml` | Add `bedrock-agentcore`, `aws-cdk-lib` dependencies. |
| `README.md` | Replace "Start the web interface" section with deploy + run instructions. |

### Untouched

`tools.py`, `db.py`, `policy.py`, `prompts.py`, `wrap.py`, `tests/`, `templates/`

---

## Key Decisions

**Session IDs**: Flask generates a `uuid4` per browser session and stores it in the session cookie. This becomes the `sessionId` passed to AgentCore Runtime, giving each tab an independent conversation thread.

**Actor identity**: `actor_customer_id` (default `cust_001`) is passed in the invocation JSON payload from Flask to the container, not as a container env var. This keeps the CDK stack participant-agnostic.

**SQLite lifecycle**: `agentcore_app.py` calls `db.initialize("/tmp/ecomm.sqlite")` once at startup. The database resets on container restart; no persistence is needed.

**CDK L1 for AgentCore**: AgentCore Runtime has no CDK L2 constructs yet. The stack uses `CfnResource` with type `AWS::BedrockAgentCore::Runtime`. `DockerImageAsset` handles ECR repo creation, image build, and push automatically.

**IAM role**: The AgentCore Runtime IAM role needs `bedrock:InvokeModel` (for Nova Lite) and `bedrock:InvokeModelWithResponseStream`. The CDK stack creates this role and attaches it to the runtime resource.

---

## Deployment Flow

```bash
# One-time bootstrap (per AWS account/region)
cdk bootstrap

# Build image, push to ECR, create/update AgentCore Runtime (~2-3 min first time)
cdk deploy
# Stack outputs: AgentCoreRuntimeId = <id>

# Run local Flask server pointing at the cloud agent
AGENTCORE_RUNTIME_ID=<id> AWS_PROFILE=ai-workshop python server.py
```

After modifying `policy.py` or `tools.py`, participants run `cdk deploy` again. ECR layer caching means rebuilds after the first deploy take ~60-90 seconds.

Tests (`pytest`) call `tools.py` directly and do not involve AgentCore — iteration speed for unit tests is unchanged.

---

## Verification

1. `cdk deploy` completes without error and outputs a runtime ID.
2. `python server.py` starts and the health endpoint returns `{"status": "ok"}`.
3. Sending a chat message via the browser receives a response from the agent.
4. The prompt-injection product (`sku_666`) triggers the expected insecure behaviour.
5. `pytest -q` still passes (or fails for the expected guardrail tests) — no regression.
6. After hardening `policy.py` + `cdk deploy`, the previously failing guardrail tests pass.
