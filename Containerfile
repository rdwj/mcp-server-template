# syntax=docker/dockerfile:1
FROM registry.redhat.io/ubi9/python-311:latest AS base

# Use uv for fast installs when available
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1 \
    PATH="/opt/app-root/bin:$PATH"

WORKDIR /opt/app-root/src

# Copy metadata and install
COPY pyproject.toml README.md .
COPY uv.lock* ./
RUN uv sync --no-dev --no-cache || (echo "No lockfile yet; creating" && uv sync --no-cache)

# Copy source and prompts
COPY src/ ./src/
COPY prompts/ ./prompts/
COPY .env.example ./

USER 1001
CMD ["python", "-m", "src.main"]
