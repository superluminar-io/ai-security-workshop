# Start the Agent

You now have all the tools and credentials in place. This page walks you through installing dependencies and verifying the setup with the test suite.

---

## Install dependencies

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

## Verify with the test suite

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

## You're ready

For the rest of the workshop you'll have three things open simultaneously:

- **This site** ([localhost:5173](http://localhost:5173)) — workshop instructions, one module at a time
- **The chat interface** ([localhost:5000](http://localhost:5000)) — the agent you'll be attacking and fixing
- **Your code editor** — the cloned repository, where you'll make changes and run tests

Head to **Explore the Agent** to begin.
