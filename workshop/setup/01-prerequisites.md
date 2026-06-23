# Prerequisites

Before you can run the workshop agent, you need a few tools installed on your machine. Work through each section below and verify before moving on.

---

## Python 3.11+

**In your terminal**, check what version you have:

```bash
python3 --version
```

If the version shown is below 3.11, install a newer one:

- **macOS** (Homebrew): `brew install python@3.11`
- **All platforms**: [python.org/downloads](https://www.python.org/downloads/)

---

## uv (Python package manager)

`uv` manages the virtual environment and dependencies for the workshop project. **In your terminal:**

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Restart your terminal, then verify:

```bash
uv --version
```

> If you prefer `pip`, you can skip `uv` — `pip` instructions are included at each step.

---

## AWS CLI v2

The workshop agent calls Amazon Bedrock, so you need the AWS CLI to configure your credentials.

Install for your platform: [docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)

Verify:

```bash
aws --version
```

Expected output: `aws-cli/2.x.x ...`

---

## Code editor

VS Code is recommended. Make sure you can open the repository folder in your editor.

---

Once all four are in place, move on to **AWS Credentials**.
