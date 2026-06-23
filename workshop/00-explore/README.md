# Explore the Agent

Start the agent by running this in a terminal from the repository root:

```bash
AWS_PROFILE=ai-workshop uv run python server.py
```

> **macOS note:** Port 5000 may be in use by AirPlay Receiver. If so, use `PORT=8080 AWS_PROFILE=ai-workshop uv run python server.py` and open [http://localhost:8080](http://localhost:8080) instead.

Then open the agentic chat interface at [http://localhost:5000](http://localhost:5000) in your browser and start chatting. See what the agent can do — ask it about products, orders, your profile.

* Can you find any flaws?
* Are any of the things you found exploitable?
