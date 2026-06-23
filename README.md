# AI Security Workshop: Insecure Strands E‑Commerce Agent

This repo contains an **intentionally insecure** Strands-based e-commerce assistant for running hands-on workshops about AI agent security. Topics covered: excessive tool authority, outbound exfiltration, PII scoping, and tool authorization.

## Get started

You need **Git** and **Node.js 18+** installed.

- **macOS** (Homebrew): `brew install node`
- **All platforms**: [nodejs.org](https://nodejs.org/)

**1. Clone the repository:**

```bash
git clone https://github.com/superluminar-io/ai-security-workshop.git
cd ai-security-workshop
```

**2. Start the workshop site:**

```bash
cd docs-site
npm install
npm run dev
```

**3.** Open [http://localhost:5173](http://localhost:5173) in your browser and follow the **Setup** module — it walks you through all remaining steps.

Keep the `docs-site` terminal running throughout the workshop.

---

## Quick reference

| Task | Command (run from repo root) |
|---|---|
| Workshop docs | `cd docs-site && npm install && npm run dev` → [localhost:5173](http://localhost:5173) |
| Install Python deps | `uv sync` |
| Start agent web UI | `AWS_PROFILE=ai-workshop uv run python server.py` → [localhost:5000](http://localhost:5000) |
| Run tests | `AWS_PROFILE=ai-workshop uv run pytest -q` |
| Reset database | `uv run python reset_db.py` |

## Repository tour

- `docs-site/`: Workshop instructions site (React + Vite) — `cd docs-site && npm run dev`
- `workshop/`: Workshop module content (markdown) served by the docs site
- `server.py`: Flask web server — serves the agent chat UI at [localhost:5000](http://localhost:5000)
- `app.py`: CLI entrypoint for the agent
- `tools.py`: Strands tools (intentionally vulnerable)
- `policy.py`: Policy abstraction (initially permissive / unused)
- `prompts.py`: System prompt (deliberately unsafe)
- `db.py`: SQLite schema + seed data (includes a prompt injection payload)
- `tests/test_guardrails.py`: Target secure behavior — expected to fail initially
- `reset_db.py`: Resets the database to its initial seeded state
