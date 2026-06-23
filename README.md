# AI Security Workshop: Insecure Strands E‑Commerce Agent

This repo contains an **intentionally insecure** Strands-based e-commerce assistant for running hands-on workshops about:

- excessive tool authority (refunds, discounts)
- outbound exfiltration controls
- PII scoping / cross-customer data access
- tool authorization

The app is **supposed to start insecure**. The accompanying tests encode the **desired secure behavior**, so the initial version is expected to fail tests until you add guardrails.

## Setup

### Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.11 or higher | |
| Node.js | 18 or higher | For the workshop docs site |
| `uv` or `pip` | — | `uv` is recommended; `pip` works too |
| Git | any recent version | |
| AWS CLI | v2 | For configuring your IAM credentials |
| A code editor | — | VS Code recommended |

### 1. Node.js 18+

The workshop instructions are served as a local website. You need Node.js to run it.

- **macOS** (via Homebrew): `brew install node`
- **All platforms**: download from [nodejs.org](https://nodejs.org/)

Verify: `node --version` — expected output: `v18.x.x` or higher.

### 2. Python 3.11+

Check your current version:

```bash
python3 --version
```

If the version shown is below 3.11, install a newer one.

- **macOS** (via Homebrew): `brew install python@3.11`
- **Windows / Linux / macOS alternatives**: download from [python.org/downloads](https://www.python.org/downloads/)

You can also use [pyenv](https://github.com/pyenv/pyenv) to manage multiple Python versions. The repository includes a `.python-version` file that pins the project to Python 3.11.

### 3. Package manager — `uv` (recommended) or `pip`

You can use either `uv` or `pip` to install dependencies. `uv` is recommended — it is significantly faster and manages the virtual environment for you — but `pip` works fine if you prefer.

**To install `uv`:**

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Verify: `uv --version` — documentation: [docs.astral.sh/uv](https://docs.astral.sh/uv/)

If you prefer to use `pip`, no additional installation is needed — it comes with Python.

### 4. AWS CLI v2

The workshop agent calls Amazon Bedrock, so you need the AWS CLI to configure your credentials.

Install instructions by platform: [docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)

Verify: `aws --version` — expected output: `aws-cli/2.x.x ...`

### 5. Configure your AWS IAM credentials

You will be given an IAM user with access to the Bedrock model used in this workshop. You will receive:

- **Access Key ID**
- **Secret Access Key**

Configure a named profile for this workshop so it does not interfere with any existing AWS credentials you have:

```bash
aws configure --profile ai-workshop
```

You will be prompted for four values:

```
AWS Access Key ID [None]: <your Access Key ID>
AWS Secret Access Key [None]: <your Secret Access Key>
Default region name [None]: eu-central-1
Default output format [None]: json
```

> **Region is important.** The model used in this workshop is hosted in the AWS EU region. Enter `eu-central-1` exactly.

Verify the profile was saved correctly:

```bash
aws sts get-caller-identity --profile ai-workshop
```

You should see a JSON response with your account and user ARN. If you see an error, double-check the keys and region.


### 6. Install dependencies

From inside the repository directory, run one of the following depending on your chosen package manager:

**With `uv` (recommended):**

```bash
uv sync
```

`uv sync` creates a virtual environment (`.venv/`) and installs all dependencies from the lock file automatically.

**With `pip`:**

```bash
python3 -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### 7. Verify the setup

Activate the virtual environment:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

Then run the test suite:

```bash
AWS_PROFILE=ai-workshop pytest -q
```

or with uv
```bash
AWS_PROFILE=ai-workshop uv run pytest -q
```

or with PowerShell
```bash
$env:AWS_PROFILE="ai-workshop"; pytest -q
```

You should see output like:

```
FAILED tests/test_guardrails.py::test_pii_scoping_blocks_other_customer
FAILED tests/test_guardrails.py::test_refund_blocks_other_customers_order
...
6 failed in 0.XXs
```

**Failing tests are expected at this point.** The tests encode the secure behavior you will implement during the workshop. If the tests run (even if they fail), your environment is set up correctly.

### 8. Start the workshop docs site

The workshop instructions are served as a local website. Open a terminal in the `docs-site/` directory and run:

```bash
npm install
npm run dev
```

Then open [http://localhost:5173](http://localhost:5173) in your browser. **Use this site for all workshop instructions** — it guides you through each module step by step.

Keep this terminal running throughout the workshop.

### 9. Start the web interface

```bash
AWS_PROFILE=ai-workshop python server.py
```
or with uv:
```bash
AWS_PROFILE=ai-workshop uv run python server.py
```

or with PowerShell:
```bash
$env:AWS_PROFILE="ai-workshop"; python server.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser. You should see a chat interface and be able to send messages to the agent.

If port 5000 is already in use:

```bash
AWS_PROFILE=ai-workshop PORT=8080 python server.py
```

Then open [http://localhost:8080](http://localhost:8080) instead.

> **macOS note:** port 5000 is used by AirPlay Receiver by default. Disable it in System Settings → General → AirDrop & Handoff, or use a different port.

## Quick reference

| Task | Command |
|---|---|
| Start workshop docs | `cd docs-site && npm run dev` → [localhost:5173](http://localhost:5173) |
| Install Python deps | `uv sync` **or** `pip install -r requirements.txt` (pick one) |
| Activate virtualenv (macOS/Linux) | `source .venv/bin/activate` |
| Start web UI | `AWS_PROFILE=ai-workshop python server.py` |
| Start CLI (LLM mode) | `AWS_PROFILE=ai-workshop python app.py` |
| Start CLI (no LLM) | `ENABLE_LLM=0 python app.py` |
| Run tests | `AWS_PROFILE=ai-workshop pytest -q` |
| Reset database | `python reset_db.py` |

## Troubleshooting

**`uv: command not found`**
Restart your terminal after installing `uv`, or add `~/.local/bin` (macOS/Linux) to your `PATH`.

**`aws sts get-caller-identity` returns an auth error**
Re-run `aws configure --profile ai-workshop` and check for typos. Keys are case-sensitive.

**`python server.py` falls back to command mode or raises a Bedrock error**
Make sure `AWS_PROFILE=ai-workshop` is set. You can test Bedrock connectivity independently:
```bash
aws bedrock list-foundation-models --region eu-central-1 --profile ai-workshop
```

**Tests error instead of fail**
There is a difference between a test *failing* (assertion not met — expected) and a test *erroring* (exception raised — unexpected). If tests error, check that `uv sync` completed without errors and that your virtualenv is activated.

## Repository tour

- `docs-site/`: Workshop instructions site (React + Vite) — run with `npm run dev`
- `app.py`: CLI entrypoint (optionally uses a Strands `Agent`)
- `server.py`: Web server with Flask (serves chat UI on http://localhost:5000)
- `reset_db.py`: Script to reset the database to initial state
- `db.py`: SQLite schema + seed data (includes a malicious product description with prompt injection)
- `tools.py`: Strands tools (intentionally vulnerable)
- `policy.py`: policy abstraction (exists but initially permissive / unused)
- `prompts.py`: deliberately unsafe system prompt
- `templates/`: HTML templates for the web interface
- `tests/test_guardrails.py`: target secure behavior (fails initially)
