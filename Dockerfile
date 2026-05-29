FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache

COPY agentcore_app.py db.py policy.py prompts.py tools.py wrap.py ./

EXPOSE 8080

CMD ["uv", "run", "python", "agentcore_app.py"]
