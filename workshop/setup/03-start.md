# Start the Agent

You now have all the tools and credentials in place. This page walks you through installing dependencies, verifying the setup with the test suite, and starting the agent web interface.

You will need **two terminals** open in the repository root for the rest of the workshop.

---

## Terminal 1 — Install dependencies

**In your terminal**, from the repository root, run:

```bash
uv sync
```

This creates a `.venv/` directory and installs all Python dependencies automatically.

<details>
<summary>Using pip instead of uv</summary>

```bash
python3 -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

</details>

---

## Terminal 1 — Verify with the test suite

Run the test suite to confirm everything is wired up correctly:

```bash
AWS_PROFILE=ai-workshop uv run pytest -q
```

<details>
<summary>Using pip / activated virtualenv</summary>

```bash
# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

AWS_PROFILE=ai-workshop pytest -q
```

</details>

<details>
<summary>Windows (PowerShell)</summary>

```powershell
$env:AWS_PROFILE="ai-workshop"; uv run pytest -q
```

</details>

You should see output like:

```
FAILED tests/test_guardrails.py::test_pii_scoping_blocks_other_customer
FAILED tests/test_guardrails.py::test_refund_blocks_other_customers_order
...
6 failed in 0.XXs
```

**Failing tests are expected.** The tests encode the secure behavior you will implement during the workshop. If they run — even if they fail — your environment is correct.

> If tests *error* rather than *fail*, check that `uv sync` completed without errors.

---

## Terminal 2 — Start the agent web interface

Open a **second terminal** in the repository root and run:

```bash
AWS_PROFILE=ai-workshop uv run python server.py
```

<details>
<summary>Using pip / activated virtualenv</summary>

```bash
AWS_PROFILE=ai-workshop python server.py
```

</details>

<details>
<summary>Windows (PowerShell)</summary>

```powershell
$env:AWS_PROFILE="ai-workshop"; uv run python server.py
```

</details>

**In your browser**, open [http://localhost:5000](http://localhost:5000). You should see a chat interface. Send a message to confirm the agent responds.

> **macOS note:** Port 5000 may be in use by AirPlay Receiver. If so, use `PORT=8080 AWS_PROFILE=ai-workshop uv run python server.py` and open [http://localhost:8080](http://localhost:8080) instead.

---

## You're ready

Keep both terminals running throughout the workshop:

| Terminal | What it runs |
|---|---|
| Terminal 1 | Available for running tests and code changes |
| Terminal 2 | The agent web interface at [localhost:5000](http://localhost:5000) |

Head to **Explore the Agent** to begin.
