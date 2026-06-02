# AgentCore Runtime Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the in-process Strands agent in Flask with a Bedrock AgentCore Runtime container; `server.py` becomes a thin boto3 proxy.

**Architecture:** `agentcore_app.py` is the container entrypoint (Strands agent wrapped in `BedrockAgentCoreApp`). The CDK stack in `infra/` builds the image, pushes it to ECR, and creates the `AWS::BedrockAgentCore::Runtime` resource. `server.py` drops Strands entirely and calls `invoke_agent_runtime` via boto3 with per-browser-tab UUID session IDs.

**Tech Stack:** Python 3.11, `strands-agents`, `bedrock-agentcore` SDK, Flask, boto3, `aws-cdk-lib`, Docker, uv

---

## Files

| File | Action | Purpose |
|---|---|---|
| `pyproject.toml` | Modify | Add `bedrock-agentcore`, `aws-cdk-lib`, `constructs` |
| `requirements.txt` | Modify | Mirror pyproject deps for pip users |
| `agentcore_app.py` | Create | Container entrypoint: BedrockAgentCoreApp + Strands agent |
| `Dockerfile` | Create | ARM64 container image using uv |
| `.dockerignore` | Create | Exclude .venv, tests, docs from build context |
| `infra/__init__.py` | Create | Empty — makes infra a package |
| `infra/app.py` | Create | CDK app entrypoint |
| `infra/stack.py` | Create | CDK stack: ECR image + IAM role + CfnRuntime |
| `cdk.json` | Create | CDK config pointing at infra/app.py |
| `server.py` | Modify | Remove Strands; add boto3 AgentCore client + session UUIDs |
| `app.py` | Modify | Remove `_llm_mode()`; default to command mode |
| `README.md` | Modify | Replace "Start the web interface" with CDK deploy instructions |
| `tests/test_agentcore_app.py` | Create | Unit test for the container handler function |
| `tests/test_server_agentcore.py` | Create | Unit test for server.py /api/chat with mocked boto3 |

---

## Task 1: Add new dependencies

**Files:**
- Modify: `pyproject.toml`
- Modify: `requirements.txt`

- [ ] **Step 1: Write import tests (they will fail until deps are installed)**

Create `tests/test_imports.py`:

```python
def test_bedrock_agentcore_importable():
    from bedrock_agentcore.runtime import BedrockAgentCoreApp
    assert BedrockAgentCoreApp is not None


def test_cdk_bedrockagentcore_importable():
    from aws_cdk import aws_bedrockagentcore as agentcore
    assert agentcore.CfnRuntime is not None
```

- [ ] **Step 2: Run to confirm they fail**

```
uv run pytest tests/test_imports.py -v
```

Expected: `ModuleNotFoundError` for both.

- [ ] **Step 3: Update `pyproject.toml`**

Replace the `dependencies` list:

```toml
[project]
name = "ai-security-workshop"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "strands-agents>=1.0.0",
    "pytest>=8.0.0",
    "flask>=3.1.3",
    "bedrock-agentcore>=0.1.0",
    "aws-cdk-lib>=2.238.0",
    "constructs>=10.0.0",
]

[tool.pytest.ini_options]
pythonpath = ["."]
```

- [ ] **Step 4: Update `requirements.txt`**

```
strands-agents>=1.0.0
pytest>=8.0.0
flask>=3.1.3
bedrock-agentcore>=0.1.0
aws-cdk-lib>=2.238.0
constructs>=10.0.0
```

- [ ] **Step 5: Sync dependencies**

```
uv sync
```

- [ ] **Step 6: Run import tests — expect PASS**

```
uv run pytest tests/test_imports.py -v
```

Expected: both tests PASS.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml requirements.txt tests/test_imports.py uv.lock
git commit -m "feat: add bedrock-agentcore and aws-cdk-lib dependencies"
```

---

## Task 2: Create `agentcore_app.py`

Container entrypoint. Strands agent is created lazily. DB initialised from `/tmp` at module load. The `_handle` function is separated from the `@app.entrypoint` registration to keep it testable.

**Files:**
- Create: `agentcore_app.py`
- Create: `tests/test_agentcore_app.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_agentcore_app.py`:

```python
from __future__ import annotations


def test_handle_extracts_prompt_and_returns_text(monkeypatch):
    """_handle must pass payload['prompt'] to the agent and surface the text response."""
    import agentcore_app

    class FakeResult:
        message = {"content": [{"text": "Your orders: order_001."}]}

    monkeypatch.setattr(agentcore_app, "_agent", lambda msg, **kw: FakeResult())

    result = agentcore_app._handle({"prompt": "show my orders", "actorCustomerId": "cust_001"})

    assert result["result"] == "Your orders: order_001."


def test_handle_uses_actor_customer_id_from_payload(monkeypatch):
    """_handle must pass actorCustomerId from payload into invocation_state."""
    import agentcore_app

    captured: dict = {}

    class FakeResult:
        message = {"content": [{"text": "ok"}]}

    def fake_agent(msg, **kw):
        captured.update(kw.get("invocation_state", {}))
        return FakeResult()

    monkeypatch.setattr(agentcore_app, "_agent", fake_agent)
    agentcore_app._handle({"prompt": "hello", "actorCustomerId": "cust_002"})

    assert captured["actor_customer_id"] == "cust_002"


def test_handle_defaults_actor_when_missing(monkeypatch):
    """_handle must default actorCustomerId to cust_001 when not in payload."""
    import agentcore_app

    captured: dict = {}

    class FakeResult:
        message = {"content": [{"text": "ok"}]}

    def fake_agent(msg, **kw):
        captured.update(kw.get("invocation_state", {}))
        return FakeResult()

    monkeypatch.setattr(agentcore_app, "_agent", fake_agent)
    agentcore_app._handle({"prompt": "hello"})

    assert captured["actor_customer_id"] == "cust_001"
```

- [ ] **Step 2: Run to confirm they fail**

```
uv run pytest tests/test_agentcore_app.py -v
```

Expected: `ModuleNotFoundError: No module named 'agentcore_app'`

- [ ] **Step 3: Create `agentcore_app.py`**

```python
from __future__ import annotations

import os
from typing import Any

import db
from prompts import SYSTEM_PROMPT
import tools as ecomm_tools

from bedrock_agentcore.runtime import BedrockAgentCoreApp

DB_PATH = "/tmp/ecomm.sqlite"
MODEL_ID = os.environ.get("STRANDS_MODEL", "eu.amazon.nova-2-lite-v1:0")

db.initialize(DB_PATH)

app = BedrockAgentCoreApp()

_agent = None


def _get_agent():
    global _agent
    if _agent is None:
        from strands import Agent
        from strands.models import BedrockModel

        model = BedrockModel(model_id=MODEL_ID, max_tokens=3000)
        _agent = Agent(
            model=model,
            system_prompt=SYSTEM_PROMPT,
            callback_handler=None,
            tools=[
                ecomm_tools.search_products,
                ecomm_tools.list_products,
                ecomm_tools.get_product_details,
                ecomm_tools.get_customer_profile,
                ecomm_tools.list_orders,
                ecomm_tools.refund_order,
                ecomm_tools.apply_discount,
                ecomm_tools.send_email,
            ],
        )
    return _agent


def _extract_text(result: Any) -> str:
    try:
        msg = result.message if hasattr(result, "message") else result
        content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", []) or []
        if isinstance(content, list) and content and isinstance(content[0], dict):
            return content[0].get("text", "")
    except Exception:
        pass
    return str(result)


def _handle(payload: dict) -> dict:
    agent = _get_agent()
    message = payload.get("prompt", "")
    actor_customer_id = payload.get("actorCustomerId", "cust_001")
    result = agent(
        message,
        invocation_state={"actor_customer_id": actor_customer_id, "db_path": DB_PATH},
    )
    return {"result": _extract_text(result)}


@app.entrypoint
def invoke(payload: dict) -> dict:
    return _handle(payload)


if __name__ == "__main__":
    app.run()
```

- [ ] **Step 4: Run tests — expect PASS**

```
uv run pytest tests/test_agentcore_app.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add agentcore_app.py tests/test_agentcore_app.py
git commit -m "feat: add agentcore_app.py container entrypoint"
```

---

## Task 3: Create Dockerfile and .dockerignore

**Files:**
- Create: `Dockerfile`
- Create: `.dockerignore`

No unit test — verified by `docker build`.

- [ ] **Step 1: Create `.dockerignore`**

```
.venv/
.git/
.pytest_cache/
__pycache__/
*.sqlite
*.pyc
tests/
workshop/
docs/
infra/
cdk.json
cdk.out/
*.md
```

- [ ] **Step 2: Create `Dockerfile`**

```dockerfile
FROM --platform=linux/arm64 ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache

COPY agentcore_app.py db.py policy.py prompts.py tools.py wrap.py ./

EXPOSE 8080

CMD ["uv", "run", "python", "agentcore_app.py"]
```

- [ ] **Step 3: Verify the image builds locally**

```bash
docker build --platform linux/arm64 -t ai-security-workshop:local .
```

Expected: `Successfully built <image-id>` with no errors. The build copies only the 6 Python files listed; `.venv`, tests, and docs are excluded via `.dockerignore`.

- [ ] **Step 4: Commit**

```bash
git add Dockerfile .dockerignore
git commit -m "feat: add Dockerfile and .dockerignore for AgentCore container"
```

---

## Task 4: Create CDK infrastructure

**Files:**
- Create: `cdk.json`
- Create: `infra/__init__.py`
- Create: `infra/app.py`
- Create: `infra/stack.py`

Verification is `cdk synth` (no AWS calls, just CloudFormation template generation).

- [ ] **Step 1: Create `cdk.json` at the project root**

```json
{
  "app": "python infra/app.py",
  "context": {
    "@aws-cdk/aws-ecr-assets:dockerIgnoreSupport": true
  }
}
```

- [ ] **Step 2: Create `infra/__init__.py`** (empty file)

```python
```

- [ ] **Step 3: Create `infra/app.py`**

```python
#!/usr/bin/env python3
from __future__ import annotations

import aws_cdk as cdk
from infra.stack import AiSecurityWorkshopStack

app = cdk.App()
AiSecurityWorkshopStack(
    app,
    "AiSecurityWorkshopStack",
    env=cdk.Environment(
        account=app.account,
        region=app.region,
    ),
)
app.synth()
```

- [ ] **Step 4: Create `infra/stack.py`**

```python
from __future__ import annotations

import os

import aws_cdk as cdk
from aws_cdk import (
    CfnOutput,
    Stack,
    aws_bedrockagentcore as agentcore,
    aws_ecr_assets as ecr_assets,
    aws_iam as iam,
)
from constructs import Construct


class AiSecurityWorkshopStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        project_root = os.path.join(os.path.dirname(__file__), "..")

        # Build image and push to ECR on cdk deploy
        image = ecr_assets.DockerImageAsset(
            self,
            "AgentImage",
            directory=project_root,
            platform=ecr_assets.Platform.LINUX_ARM64,
        )

        # IAM role the AgentCore Runtime container assumes
        role = iam.Role(
            self,
            "AgentRuntimeRole",
            assumed_by=iam.ServicePrincipal("bedrock-agentcore.amazonaws.com"),
            inline_policies={
                "BedrockInvoke": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "bedrock:InvokeModel",
                                "bedrock:InvokeModelWithResponseStream",
                            ],
                            resources=["*"],
                        )
                    ]
                )
            },
        )

        # AgentCore Runtime resource (L1 construct — no L2 yet)
        runtime = agentcore.CfnRuntime(
            self,
            "AgentRuntime",
            agent_runtime_name="ai-security-workshop",
            agent_runtime_artifact=agentcore.CfnRuntime.AgentRuntimeArtifactProperty(
                container_configuration=agentcore.CfnRuntime.ContainerConfigurationProperty(
                    container_uri=image.image_uri,
                )
            ),
            network_configuration=agentcore.CfnRuntime.NetworkConfigurationProperty(
                network_mode="PUBLIC",
            ),
            role_arn=role.role_arn,
        )

        CfnOutput(
            self,
            "AgentRuntimeArn",
            value=runtime.attr_agent_runtime_arn,
            description="Set as AGENTCORE_RUNTIME_ARN when running server.py",
        )
```

- [ ] **Step 5: Verify CDK synth succeeds**

```bash
uv run cdk synth --no-staging 2>&1 | tail -30
```

Expected: CloudFormation template printed to stdout with `AWS::BedrockAgentCore::Runtime` resource and `AWS::IAM::Role`. No errors.

- [ ] **Step 6: Commit**

```bash
git add cdk.json infra/
git commit -m "feat: add CDK stack for AgentCore Runtime deployment"
```

---

## Task 5: Modify `server.py` to use boto3 AgentCore client

Remove all Strands/local-agent code. Add boto3 `bedrock-agentcore` client. Add Flask session-based UUID for per-tab conversation threads.

**Files:**
- Modify: `server.py`
- Create: `tests/test_server_agentcore.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_server_agentcore.py`:

```python
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest


@pytest.fixture()
def flask_client(monkeypatch):
    monkeypatch.setenv(
        "AGENTCORE_RUNTIME_ARN",
        "arn:aws:bedrock-agentcore:eu-central-1:123456789012:runtime/test-abc123",
    )
    import server

    server.app.config["TESTING"] = True
    server.app.config["SECRET_KEY"] = "test-secret"
    with server.app.test_client() as c:
        yield c


class _FakeStreamingBody:
    def __init__(self, data: dict):
        self._bytes = json.dumps(data).encode()

    def read(self):
        return self._bytes


def _mock_client(response_text: str) -> MagicMock:
    mock = MagicMock()
    mock.invoke_agent_runtime.return_value = {
        "response": _FakeStreamingBody({"result": response_text})
    }
    return mock


def test_chat_returns_agent_response(flask_client, monkeypatch):
    """POST /api/chat should return the text from the AgentCore runtime."""
    import server

    monkeypatch.setattr(server, "_agentcore_client", _mock_client("Hello from the agent!"))

    resp = flask_client.post("/api/chat", json={"message": "hi"})

    assert resp.status_code == 200
    assert resp.get_json()["response"] == "Hello from the agent!"


def test_chat_passes_session_id_on_second_call(flask_client, monkeypatch):
    """Second request in same session must pass the same runtimeSessionId."""
    import server

    mock = _mock_client("ok")
    monkeypatch.setattr(server, "_agentcore_client", mock)

    with flask_client.session_transaction() as sess:
        pass  # open session so Flask creates it

    flask_client.post("/api/chat", json={"message": "first"})
    flask_client.post("/api/chat", json={"message": "second"})

    calls = mock.invoke_agent_runtime.call_args_list
    assert len(calls) == 2
    first_session = calls[0].kwargs["runtimeSessionId"]
    second_session = calls[1].kwargs["runtimeSessionId"]
    assert first_session == second_session  # same session across requests


def test_chat_empty_message_returns_400(flask_client):
    """Empty message must be rejected without calling the AgentCore runtime."""
    resp = flask_client.post("/api/chat", json={"message": ""})
    assert resp.status_code == 400


def test_health_endpoint(flask_client):
    """GET /api/health must return status ok."""
    resp = flask_client.get("/api/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"
```

- [ ] **Step 2: Run to confirm they fail**

```
uv run pytest tests/test_server_agentcore.py -v
```

Expected: tests either import-fail (no `_agentcore_client` attribute) or assertion-fail.

- [ ] **Step 3: Rewrite `server.py`**

```python
from __future__ import annotations

import json
import os
import secrets
import uuid
from typing import Any

import boto3
from flask import Flask, jsonify, render_template, request, session

import db

app = Flask(__name__, template_folder="templates")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))

ACTOR_CUSTOMER_ID = os.environ.get("ACTOR_CUSTOMER_ID", "cust_001")
REGION = os.environ.get("AWS_DEFAULT_REGION", "eu-central-1")
PORT = int(os.environ.get("PORT", 5000))
DB_PATH = os.environ.get("ECOMM_DB", "ecomm.sqlite")

_agentcore_client: Any = None


def _get_client() -> Any:
    global _agentcore_client
    if _agentcore_client is None:
        _agentcore_client = boto3.client("bedrock-agentcore", region_name=REGION)
    return _agentcore_client


@app.route("/")
def index():
    return render_template("index.html", actor_customer_id=ACTOR_CUSTOMER_ID)


@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        message = data.get("message", "").strip()

        if not message:
            return jsonify({"error": "Empty message"}), 400

        if "session_id" not in session:
            session["session_id"] = str(uuid.uuid4())
        session_id = session["session_id"]

        runtime_arn = os.environ["AGENTCORE_RUNTIME_ARN"]
        payload = json.dumps(
            {"prompt": message, "actorCustomerId": ACTOR_CUSTOMER_ID}
        ).encode("utf-8")

        response = _get_client().invoke_agent_runtime(
            agentRuntimeArn=runtime_arn,
            runtimeSessionId=session_id,
            payload=payload,
            qualifier="DEFAULT",
        )

        body = json.loads(response["response"].read())
        text = body.get("result", "")
        return jsonify({"response": text, "data": None})

    except KeyError as exc:
        return jsonify({"error": f"Missing configuration: {exc}"}), 500
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "actor_customer_id": ACTOR_CUSTOMER_ID})


def main():
    db.initialize(DB_PATH)
    print("Starting chat server...")
    print(f"Logged in as: {ACTOR_CUSTOMER_ID}")
    print(f"Open http://localhost:{PORT} in your browser")
    app.run(debug=False, host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests — expect PASS**

```
uv run pytest tests/test_server_agentcore.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Verify existing guardrail tests still pass**

```
uv run pytest tests/test_guardrails.py -v
```

Expected: same 6 failures as before (guardrails not yet implemented — expected).  
No new errors must appear.

- [ ] **Step 6: Commit**

```bash
git add server.py tests/test_server_agentcore.py
git commit -m "feat: replace local Strands agent in server.py with boto3 AgentCore client"
```

---

## Task 6: Clean up `app.py`

Remove `_llm_mode()` and all Strands imports. Default to command mode only.

**Files:**
- Modify: `app.py`

No new tests — existing import tests cover this.

- [ ] **Step 1: Replace `app.py` entirely**

```python
from __future__ import annotations

import json
import os
from typing import Any

import db
import tools as ecomm_tools

ACTOR_CUSTOMER_ID = os.environ.get("ACTOR_CUSTOMER_ID", "cust_001")
DB_PATH = os.environ.get("ECOMM_DB", "ecomm.sqlite")


def _print_result(result: dict[str, Any]) -> None:
    status = result.get("status", "unknown")
    blocks = result.get("content") or []
    text = ""
    if isinstance(blocks, list) and blocks and isinstance(blocks[0], dict):
        text = blocks[0].get("text", "")
    print(f"[{status}] {text}".strip())
    if "data" in result:
        print(json.dumps(result["data"], indent=2, sort_keys=True))


def _command_mode() -> None:
    print("Insecure e-commerce assistant (command mode)")
    print(f"DB: {DB_PATH}")
    print(f"Logged in as: {ACTOR_CUSTOMER_ID}")
    print("")
    print("Commands:")
    print("  search <query>")
    print("  product <sku>")
    print("  profile <customer_id>")
    print("  orders [customer_id]")
    print("  refund <order_id> <refund_cents>")
    print("  discount <order_id> <percent>")
    print("  email <to_email> <subject> | <body>")
    print("  quit")
    print("")

    while True:
        raw = input("> ").strip()
        if not raw:
            continue
        if raw in {"q", "quit", "exit"}:
            break

        try:
            if raw.startswith("search "):
                q = raw.removeprefix("search ").strip()
                _print_result(ecomm_tools.search_products(q, db_path=DB_PATH))
            elif raw.startswith("product "):
                sku = raw.removeprefix("product ").strip()
                _print_result(ecomm_tools.get_product_details(sku, db_path=DB_PATH))
            elif raw.startswith("profile "):
                cid = raw.removeprefix("profile ").strip()
                _print_result(ecomm_tools.get_customer_profile(ACTOR_CUSTOMER_ID, cid, db_path=DB_PATH))
            elif raw.startswith("orders"):
                cid = raw.removeprefix("orders").strip()
                _print_result(ecomm_tools.list_orders(ACTOR_CUSTOMER_ID, cid if cid else None, db_path=DB_PATH))
            elif raw.startswith("refund "):
                parts = raw.split()
                if len(parts) != 3:
                    raise ValueError("Usage: refund <order_id> <refund_cents>")
                _print_result(
                    ecomm_tools.refund_order(ACTOR_CUSTOMER_ID, parts[1], int(parts[2]), db_path=DB_PATH)
                )
            elif raw.startswith("discount "):
                parts = raw.split()
                if len(parts) != 3:
                    raise ValueError("Usage: discount <order_id> <percent>")
                _print_result(ecomm_tools.apply_discount(ACTOR_CUSTOMER_ID, parts[1], int(parts[2]), db_path=DB_PATH))
            elif raw.startswith("email "):
                payload = raw.removeprefix("email ").strip()
                if "|" not in payload:
                    raise ValueError("Usage: email <to_email> <subject> | <body>")
                left, body = payload.split("|", 1)
                left_parts = left.strip().split(" ", 1)
                if len(left_parts) != 2:
                    raise ValueError("Usage: email <to_email> <subject> | <body>")
                to_email, subject = left_parts[0].strip(), left_parts[1].strip()
                _print_result(
                    ecomm_tools.send_email(ACTOR_CUSTOMER_ID, to_email, subject, body.strip(), db_path=DB_PATH)
                )
            else:
                print("Unknown command. Try `search <query>` or `quit`.")
        except Exception as e:
            print(f"[error] {type(e).__name__}: {e}")


def main() -> None:
    db.initialize(DB_PATH)
    _command_mode()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify all tests pass**

```
uv run pytest tests/ -v --ignore=tests/test_guardrails.py
```

Expected: `test_imports.py`, `test_agentcore_app.py`, `test_server_agentcore.py` all PASS.

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "chore: remove LLM mode from app.py — agent now runs in AgentCore Runtime"
```

---

## Task 7: Update README.md

Replace the "Start the web interface" section with CDK deploy instructions. Add a quick-reference row for `cdk deploy`.

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace section 7 ("Start the web interface") in README.md**

Find the section that begins `### 7. Start the web interface` and replace it with:

```markdown
### 7. Deploy to Bedrock AgentCore Runtime

The agent runs in a managed AWS container. Deploy it with CDK (builds the image, pushes to ECR, creates the runtime):

```bash
# One-time bootstrap per AWS account/region (creates CDK assets bucket)
AWS_PROFILE=ai-workshop cdk bootstrap

# Build container image, push to ECR, create AgentCore Runtime (~2–3 min first time)
AWS_PROFILE=ai-workshop cdk deploy
```

CDK outputs the runtime ARN when complete:

```
Outputs:
AiSecurityWorkshopStack.AgentRuntimeArn = arn:aws:bedrock-agentcore:eu-central-1:123456789012:runtime/ai-security-workshop-abc123
```

### 8. Start the web interface

Start the local Flask server, pointing it at the deployed runtime:

```bash
AWS_PROFILE=ai-workshop AGENTCORE_RUNTIME_ARN=<arn-from-cdk-output> python server.py
```

Open [http://localhost:5000](http://localhost:5000). You should see the chat interface.

If port 5000 is in use:

```bash
AWS_PROFILE=ai-workshop AGENTCORE_RUNTIME_ARN=<arn> PORT=8080 python server.py
```

After modifying `policy.py` or `tools.py`, redeploy:

```bash
AWS_PROFILE=ai-workshop cdk deploy   # rebuilds and redeploys (~60–90 s with layer cache)
```
```

- [ ] **Step 2: Update the quick-reference table**

Find the `| Start web UI | ...` row in the quick-reference table and replace the relevant rows:

```markdown
| Deploy agent to AgentCore | `AWS_PROFILE=ai-workshop cdk deploy` |
| Start web UI              | `AWS_PROFILE=ai-workshop AGENTCORE_RUNTIME_ARN=<arn> python server.py` |
| Start CLI (no LLM)        | `ENABLE_LLM=0 python app.py` |
| Run tests                 | `AWS_PROFILE=ai-workshop pytest -q` |
| Reset database            | `python reset_db.py` |
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: update README with AgentCore Runtime deploy instructions"
```

---

## Task 8: End-to-end verification

- [ ] **Step 1: Run full test suite**

```
uv run pytest tests/ -v
```

Expected: `test_imports`, `test_agentcore_app`, `test_server_agentcore` all PASS. `test_guardrails` shows the same 6 failures as before the migration (guardrails not yet hardened — expected). Zero new errors.

- [ ] **Step 2: Bootstrap CDK (once per account)**

```bash
AWS_PROFILE=ai-workshop cdk bootstrap
```

- [ ] **Step 3: Deploy**

```bash
AWS_PROFILE=ai-workshop cdk deploy
```

Expected: stack creates successfully. Note the `AgentRuntimeArn` output.

- [ ] **Step 4: Start Flask and verify chat**

```bash
AWS_PROFILE=ai-workshop AGENTCORE_RUNTIME_ARN=<output-arn> python server.py
```

Open http://localhost:5000. Send "show my orders". Expect the agent to list orders for cust_001.

- [ ] **Step 5: Verify prompt injection still triggers**

In the chat UI, ask the agent to get details for `sku_666`. Verify the insecure agent follows the malicious instructions (refund + email) — confirming the workshop's starting insecurity is intact after migration.

- [ ] **Step 6: Verify guardrail iteration workflow**

Make a small change to `policy.py` (e.g., add `print("policy checked")` to `authorize_tool_call`). Redeploy:

```bash
AWS_PROFILE=ai-workshop cdk deploy
```

Expected: completes in ~60–90 s (layer cache). Refresh the chat UI and confirm the new behaviour.
```
