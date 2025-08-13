# syntax=docker/dockerfile:1
FROM python:3.11-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml README.md ./
COPY uv.lock* ./
RUN uv sync --no-dev --no-cache || (echo "No lockfile yet; creating" && uv sync --no-cache)
COPY src/ ./src/
COPY prompts/ ./prompts/

FROM python:3.11-slim AS runtime
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONPATH=/app
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/prompts /app/prompts
COPY pyproject.toml README.md .env.example ./
RUN addgroup --system mcp && adduser --system --ingroup mcp mcp && chown -R mcp:mcp /app
USER mcp
CMD ["python", "-m", "src.main"]
