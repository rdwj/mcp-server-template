# FastMCP Unified Template — Single Packed File

This is a **single-file pack** of the entire template so you can copy/save everything in one place. It includes:
- Dual transport (STDIO for local, HTTP for OpenShift)
- Tools, resources, YAML prompts with **JSON schema injection** into `{output_schema}`
- Hot‑reload (dev), Kubernetes/OpenShift manifests (Service/Route/HPA)
- JWT auth + scope checks for mutation tools
- Prompt preview CLI + tests, Makefile targets, Dockerfile, uv/pip support

---
## Directory Tree
```
.
├── pyproject.toml
├── requirements.txt
├── README.md
├── Makefile
├── .env.example
├── Dockerfile
├── k8s/
│   ├── namespace.yaml
│   ├── configmap-prompts.yaml         # optional (cluster-only prompts)
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── route.yaml                     # OpenShift
│   └── hpa.yaml                       # autoscaling
├── prompts/
│   ├── summarize.yaml
│   ├── summarize.json
│   ├── classify.yaml
│   └── classify.json
└── src/
    ├── main.py
    └── core/
        ├── __init__.py
        ├── app.py
        ├── auth.py
        ├── logging.py
        ├── loaders.py
        └── server.py
    ├── tools/
    │   ├── __init__.py
    │   ├── echo.py
    │   ├── needs_elicitation.py
    │   ├── needs_sampling.py
    │   └── preview_prompt.py          # CLI
    └── resources/
        ├── __init__.py
        └── sample_resource.py

# tests
├── tests/test_loaders.py
├── tests/test_prompts.py
└── tests/test_preview_prompt.py
```

---
## FILE: pyproject.toml
```toml
[project]
name = "fastmcp-unified-template"
version = "0.3.0"
description = "MCP server template with dynamic tools/resources, YAML prompts (JSON schema injection), hot‑reload, Kubernetes/OpenShift, and tests"
requires-python = ">=3.10"
authors = [{name = "Your Name", email = "you@example.com"}]
readme = "README.md"
dependencies = [
  "fastmcp>=2.11.0",
  "pyyaml>=6.0",
  "python-dotenv>=1.0.0",
  "watchdog>=4.0.0",
  "pytest>=7.0.0",
  "pyjwt>=2.9.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src"]

[project.scripts]
fastmcp-unified = "src.main:main"

[tool.black]
line-length = 88

[tool.ruff]
line-length = 88
```

---
## FILE: requirements.txt
```txt
fastmcp>=2.11.0
pyyaml>=6.0
python-dotenv>=1.0.0
watchdog>=4.0.0
pytest>=7.0.0
pyjwt>=2.9.0
```

---
## FILE: Makefile
```makefile
.PHONY: install run dev test test-preview docker k8s-apply k8s-delete

VENV ?=.venv
PY ?=python

HAS_UV := $(shell command -v uv 2>/dev/null)

install:
ifdef HAS_UV
	uv sync
else
	$(PY) -m venv $(VENV)
	. $(VENV)/bin/activate; pip install -U pip; pip install -e .
endif

run:
	MCP_HOT_RELOAD=1 MCP_TRANSPORT=stdio $(PY) -m src.main

dev: install run

test:
ifdef HAS_UV
	uv run pytest -q
else
	. $(VENV)/bin/activate; pytest -q
endif

# Focused test for the prompt preview CLI
# Usage: make test-preview  (runs tests/test_preview_prompt.py only)
# You can pass -k filters: make test-preview ARGS="-k missing_schema"
TEST_PREVIEW_PATH := tests/test_preview_prompt.py

test-preview:
ifdef HAS_UV
	uv run pytest -q $(TEST_PREVIEW_PATH) $(ARGS)
else
	. $(VENV)/bin/activate; pytest -q $(TEST_PREVIEW_PATH) $(ARGS)
endif

docker:
	docker build -t fastmcp-unified:latest .

k8s-apply:
	kubectl apply -f k8s/namespace.yaml
	kubectl apply -f k8s/configmap-prompts.yaml || true
	kubectl apply -f k8s/deployment.yaml
	kubectl apply -f k8s/service.yaml
	kubectl apply -f k8s/route.yaml || true
	kubectl apply -f k8s/hpa.yaml

k8s-delete:
	kubectl delete -f k8s/hpa.yaml --ignore-not-found
	kubectl delete -f k8s/route.yaml --ignore-not-found
	kubectl delete -f k8s/service.yaml --ignore-not-found
	kubectl delete -f k8s/deployment.yaml --ignore-not-found
	kubectl delete -f k8s/configmap-prompts.yaml --ignore-not-found
	kubectl delete -f k8s/namespace.yaml --ignore-not-found
```

---
## FILE: .env.example
```env
MCP_SERVER_NAME=fastmcp-unified
MCP_LOG_LEVEL=INFO
# stdio for local dev; http for OpenShift/remote
MCP_TRANSPORT=stdio
# HTTP settings (used when MCP_TRANSPORT=http)
MCP_HTTP_HOST=0.0.0.0
MCP_HTTP_PORT=8080
MCP_HTTP_PATH=/mcp/
# CORS / Origin allowlist (comma-separated origins); leave empty to allow any in dev
MCP_HTTP_ALLOWED_ORIGINS=

# Auth (Bearer JWT). Provide either a symmetric secret or an RSA public key
MCP_AUTH_JWT_ALG=HS256
MCP_AUTH_JWT_SECRET=
# or for RSA/EC
MCP_AUTH_JWT_PUBLIC_KEY=-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----
# Optional: required scopes for mutation tools (comma-separated)
MCP_REQUIRED_SCOPES=mutation:write

# Hot reload in dev only
MCP_HOT_RELOAD=1
```

---
## FILE: Dockerfile
```dockerfile
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
```

---
## FILE: k8s/namespace.yaml
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: mcp
```

---
## FILE: k8s/configmap-prompts.yaml (optional)
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fastmcp-prompts
  namespace: mcp
  labels:
    app: fastmcp-unified

data:
  # You can inline prompts here for cluster-only deployments.
  summarize.yaml: |
    name: summarize
    description: Summarize a document with clear section markers.
    prompt: |
      Summarize the following text:
      <document>{document}</document>
      Use clear, concise language.
      <output_schema>{output_schema}</output_schema>
```

---
## FILE: k8s/deployment.yaml
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fastmcp-unified
  namespace: mcp
  labels:
    app: fastmcp-unified
spec:
  replicas: 1
  selector:
    matchLabels:
      app: fastmcp-unified
  template:
    metadata:
      labels:
        app: fastmcp-unified
    spec:
      containers:
        - name: server
          image: fastmcp-unified:latest
          imagePullPolicy: IfNotPresent
          env:
            - name: MCP_SERVER_NAME
              value: fastmcp-unified
            - name: MCP_TRANSPORT
              value: "http"
            - name: MCP_HTTP_HOST
              value: 0.0.0.0
            - name: MCP_HTTP_PORT
              value: "8080"
            - name: MCP_HTTP_PATH
              value: /mcp/
            - name: MCP_HOT_RELOAD
              value: "0"
            - name: MCP_HTTP_ALLOWED_ORIGINS
              value: "https://*.apps.cluster.local,https://*.openshiftapps.com"
            - name: MCP_AUTH_JWT_ALG
              valueFrom:
                secretKeyRef:
                  name: fastmcp-auth
                  key: alg
                  optional: true
            - name: MCP_AUTH_JWT_PUBLIC_KEY
              valueFrom:
                secretKeyRef:
                  name: fastmcp-auth
                  key: public_key
                  optional: true
            - name: MCP_AUTH_JWT_SECRET
              valueFrom:
                secretKeyRef:
                  name: fastmcp-auth
                  key: secret
                  optional: true
            - name: MCP_REQUIRED_SCOPES
              value: "mutation:write"
          volumeMounts:
            - name: prompts
              mountPath: /app/prompts
          ports:
            - name: http
              containerPort: 8080
      volumes:
        - name: prompts
          configMap:
            name: fastmcp-prompts
```

---
## FILE: k8s/service.yaml
```yaml
apiVersion: v1
kind: Service
metadata:
  name: fastmcp-unified
  namespace: mcp
spec:
  selector:
    app: fastmcp-unified
  ports:
    - name: http
      port: 8080
      targetPort: 8080
  type: ClusterIP
```

---
## FILE: k8s/route.yaml (OpenShift)
```yaml
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: fastmcp-unified
  namespace: mcp
spec:
  to:
    kind: Service
    name: fastmcp-unified
  port:
    targetPort: http
  tls:
    termination: edge
```

---
## FILE: k8s/hpa.yaml
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: fastmcp-unified
  namespace: mcp
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: fastmcp-unified
  minReplicas: 1
  maxReplicas: 5
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

---
## FILE: prompts/summarize.yaml
```yaml
name: summarize
description: Summarize a document with clear section markers.
prompt: |
  Summarize the following text:
  <document>{document}</document>
  Use clear, concise language.
  <output_schema>{output_schema}</output_schema>
```

---
## FILE: prompts/summarize.json
```json
{
  "type": "object",
  "properties": {
    "summary": {"type": "string"},
    "key_points": {"type": "array", "items": {"type": "string"}}
  },
  "required": ["summary", "key_points"]
}
```

---
## FILE: prompts/classify.yaml
```yaml
name: classify
description: Classify text into categories.
prompt: |
  Classify the following text:
  <text>{text}</text>
  Return JSON matching this schema:
  <output_schema>{output_schema}</output_schema>
```

---
## FILE: prompts/classify.json
```json
{
  "type": "object",
  "properties": {
    "category": {"type": "string"},
    "confidence": {"type": "number"}
  },
  "required": ["category", "confidence"]
}
```

---
## FILE: src/core/__init__.py
```python
"""Core package for FastMCP unified template."""
```

---
## FILE: src/core/logging.py
```python
import logging
from fastmcp.utilities.logging import get_logger as _get


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def get_logger(name: str) -> logging.Logger:
    # Namespaced logger under FastMCP.* per docs
    return _get(name)
```

---
## FILE: src/core/app.py
```python
import os
from fastmcp import FastMCP
from .logging import get_logger

APP_NAME = os.getenv("MCP_SERVER_NAME", "fastmcp-unified")
mcp = FastMCP(APP_NAME)
logger = get_logger("server")
```

---
## FILE: src/core/auth.py
```python
import os
import jwt
from dataclasses import dataclass
from fastmcp import Context
from .logging import get_logger

log = get_logger("auth")

@dataclass
class AllowedOrigins:
    patterns: list[str]

    @classmethod
    def from_env(cls, key: str) -> "AllowedOrigins":
        raw = os.getenv(key, "")
        patterns = [p.strip() for p in raw.split(",") if p.strip()]
        return cls(patterns)


class BearerVerifier:
    def __init__(self, alg: str | None = None, secret: str | None = None, public_key: str | None = None) -> None:
        self.alg = alg
        self.secret = secret
        self.public_key = public_key

    @classmethod
    def from_env(cls) -> "BearerVerifier | None":
        alg = os.getenv("MCP_AUTH_JWT_ALG")
        secret = os.getenv("MCP_AUTH_JWT_SECRET")
        public_key = os.getenv("MCP_AUTH_JWT_PUBLIC_KEY")
        if not alg or not (secret or public_key):
            return None
        return cls(alg=alg, secret=secret, public_key=public_key)

    def verify(self, token: str) -> dict | None:
        try:
            if self.public_key:
                return jwt.decode(token, self.public_key, algorithms=[self.alg])
            return jwt.decode(token, self.secret, algorithms=[self.alg])
        except Exception as e:
            log.warning(f"JWT verify failed: {e}")
            return None


def _get_bearer_from_headers(headers: dict[str, str]) -> str | None:
    auth = headers.get("authorization") or headers.get("Authorization")
    if not auth:
        return None
    if not auth.lower().startswith("bearer "):
        return None
    return auth.split(" ", 1)[1].strip()


def claims_from_ctx(ctx: Context) -> dict | None:  # best‑effort; HTTP transport only
    try:
        headers = getattr(getattr(ctx, "request", None), "headers", {}) or {}
        token = _get_bearer_from_headers(headers)
        verifier = BearerVerifier.from_env()
        return verifier.verify(token) if (verifier and token) else None
    except Exception:
        return None


def requires_scopes(*scopes: str):
    required = set(scopes) if scopes else set((os.getenv("MCP_REQUIRED_SCOPES", "").split(",")))
    required = {s.strip() for s in required if s.strip()}

    def deco(fn):
        async def wrapper(*args, **kwargs):
            ctx = kwargs.get("ctx") or next((a for a in args if isinstance(a, Context)), None)
            if not ctx:
                return {"error": "missing context for auth"}
            claims = claims_from_ctx(ctx) or {}
            token_scopes = set((claims.get("scope") or "").split()) | set(claims.get("scopes", []))
            if not required.issubset(token_scopes):
                await ctx.error("Forbidden: missing required scopes")
                return {"error": "forbidden", "missing": sorted(required - token_scopes)}
            return await fn(*args, **kwargs)
        return wrapper
    return deco
```

---
## FILE: src/core/loaders.py
```python
import importlib
import json
import pkgutil
import sys
from pathlib import Path
from typing import Iterable

import yaml
from fastmcp import FastMCP
from .logging import get_logger

log = get_logger("loaders")


def _iter_modules(dir_path: Path, package_prefix: str) -> Iterable[str]:
    if not dir_path.exists():
        return []
    return (
        f"{package_prefix}.{name}"
        for _, name, _ in pkgutil.iter_modules([str(dir_path)])
    )


def load_tools(mcp: FastMCP, tools_dir: Path) -> int:
    list_tools = getattr(mcp.tools, "list_tools", lambda: [])
    before = len(list_tools())
    for module_name in _iter_modules(tools_dir, "tools"):
        try:
            importlib.import_module(module_name)
            log.info(f"Loaded tool: {module_name}")
        except Exception:
            log.exception(f"Failed to load tool: {module_name}")
    after = len(list_tools())
    return max(0, after - before)


def load_resources(mcp: FastMCP, resources_dir: Path) -> int:
    list_resources = getattr(mcp.resources, "list_resources", lambda: [])
    before = len(list_resources())
    for module_name in _iter_modules(resources_dir, "resources"):
        try:
            importlib.import_module(module_name)
            log.info(f"Loaded resource: {module_name}")
        except Exception:
            log.exception(f"Failed to load resource: {module_name}")
    after = len(list_resources())
    return max(0, after - before)


essential_prompt_keys = {"name", "prompt"}


def _normalize_yaml_prompts(data):
    if not data:
        return []
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict)]
    return []


def _inject_output_schema(raw_text: str, schema_path: Path | None) -> str:
    """If raw_text contains {output_schema} and schema_path exists, replace with minified JSON.
    Keeps everything else (e.g., {document}, {text}) untouched for runtime replacement.
    """
    if "{output_schema}" not in raw_text:
        return raw_text
    if not schema_path or not schema_path.exists():
        return raw_text
    try:
        loaded = json.loads(schema_path.read_text())
        minified = json.dumps(loaded, separators=(",", ":"))
        return raw_text.replace("{output_schema}", minified)
    except Exception:
        log.exception(f"Failed to inject schema from {schema_path}")
        return raw_text


def load_single_prompt_with_schema(yaml_path: Path) -> dict:
    """Load one YAML prompt file and inject same-stem .json into {output_schema} if present."""
    data = yaml.safe_load(yaml_path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"Invalid prompt format in {yaml_path}")
    if not essential_prompt_keys.issubset(data):
        raise ValueError(f"Prompt missing required keys in {yaml_path}: {essential_prompt_keys}")

    text = str(data.get("prompt", ""))
    schema_path = yaml_path.with_suffix(".json")
    text = _inject_output_schema(text, schema_path if schema_path.exists() else None)

    out = dict(data)
    out["prompt"] = text
    return out


def load_prompts(mcp: FastMCP, prompts_dir: Path) -> int:
    list_prompts = getattr(mcp.prompts, "list_prompts", lambda: [])
    before = len(list_prompts())

    if not prompts_dir.exists():
        return 0

    for f in prompts_dir.glob("*.y*ml"):
        try:
            doc = yaml.safe_load(f.read_text())
            prompts = _normalize_yaml_prompts(doc)
            for p in prompts:
                if not essential_prompt_keys.issubset(p):
                    log.warning(f"Skipping {f}: missing required keys (have {set(p.keys())})")
                    continue
                text = str(p.get("prompt", ""))

                schema_path = f.with_suffix(".json")
                had_placeholder = "{output_schema}" in text
                text = _inject_output_schema(text, schema_path)

                if "{output_schema}" in text:
                    if had_placeholder and not schema_path.exists():
                        log.warning(f"{f.name} uses {{output_schema}} but missing schema file: {schema_path.name}")
                    else:
                        log.warning(f"{f.name} still contains '{{output_schema}}' — placeholder may be misspelled or nested.")

                mcp.prompts.add_prompt(
                    name=p["name"],
                    description=p.get("description", ""),
                    tags=p.get("tags", []) or [],
                    text=text,
                )
                log.info(f"Registered prompt: {p['name']} (from {f.name})")
        except Exception:
            log.exception(f"Failed to load prompts from {f}")

    after = len(list_prompts())
    return max(0, after - before)


# ---------------------------
# Hot‑reload (dev only)
# ---------------------------
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except Exception:  # pragma: no cover
    Observer = None
    FileSystemEventHandler = object  # type: ignore


class _ReloadHandler(FileSystemEventHandler):  # type: ignore[misc]
    def __init__(self, mcp: FastMCP, base: Path) -> None:
        self.mcp = mcp
        self.base = base

    def on_any_event(self, event):  # noqa: N802
        try:
            importlib.invalidate_caches()
            tools_dir = self.base / "tools"
            resources_dir = self.base / "resources"
            prompts_dir = self.base.parent / "prompts"

            for module_name in list(_iter_modules(tools_dir, "tools")):
                if module_name in sys.modules:
                    importlib.reload(sys.modules[module_name])
                else:
                    importlib.import_module(module_name)

            for module_name in list(_iter_modules(resources_dir, "resources")):
                if module_name in sys.modules:
                    importlib.reload(sys.modules[module_name])
                else:
                    importlib.import_module(module_name)

            load_prompts(self.mcp, prompts_dir)
            log.info("Hot‑reload applied")
        except Exception:
            log.exception("Hot‑reload failed")


def start_hot_reload(mcp: FastMCP, base_dir: Path):
    if Observer is None:
        log.warning("watchdog not installed; hot‑reload disabled")
        return None

    handler = _ReloadHandler(mcp, base_dir)
    obs = Observer()

    tools_dir = base_dir / "tools"
    resources_dir = base_dir / "resources"
    prompts_dir = base_dir.parent / "prompts"

    for d in (tools_dir, resources_dir, prompts_dir):
        if d.exists():
            obs.schedule(handler, str(d), recursive=False)

    obs.daemon = True
    obs.start()
    log.info(f"Hot‑reload watching: {tools_dir}, {resources_dir}, {prompts_dir}")
    return obs


def load_all(mcp: FastMCP, src_base: Path) -> dict:
    counts = {
        "tools": load_tools(mcp, src_base / "tools"),
        "resources": load_resources(mcp, src_base / "resources"),
        "prompts": load_prompts(mcp, src_base.parent / "prompts"),
    }
    log.info(f"Loaded: {counts}")
    return counts
```

---
## FILE: src/core/server.py
```python
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from .app import mcp
from .loaders import load_all, start_hot_reload
from .logging import configure_logging, get_logger
from .auth import BearerVerifier, AllowedOrigins

log = get_logger("bootstrap")

class UnifiedMCPServer:
    def __init__(self, name: Optional[str] = None, src_root: Optional[Path] = None) -> None:
        load_dotenv(override=True)
        configure_logging(os.getenv("MCP_LOG_LEVEL", "INFO"))
        self.name = name or os.getenv("MCP_SERVER_NAME", "fastmcp-unified")
        self.src_root = src_root or Path(__file__).resolve().parent.parent
        try:
            mcp.name = self.name  # type: ignore[attr-defined]
        except Exception:
            pass
        self.mcp = mcp

    def load(self) -> None:
        load_all(self.mcp, self.src_root)

    def run(self) -> None:
        hot = os.getenv("MCP_HOT_RELOAD", "0").lower() in {"1", "true", "yes"}
        observer = None
        if hot:
            observer = start_hot_reload(self.mcp, self.src_root)

        transport = os.getenv("MCP_TRANSPORT", "stdio").lower()
        if transport == "http":
            host = os.getenv("MCP_HTTP_HOST", "127.0.0.1")
            port = int(os.getenv("MCP_HTTP_PORT", "8000"))
            path = os.getenv("MCP_HTTP_PATH", "/mcp/")
            origins = AllowedOrigins.from_env("MCP_HTTP_ALLOWED_ORIGINS")
            verifier = BearerVerifier.from_env()
            log.info(f"Starting FastMCP HTTP server at http://{host}:{port}{path}")
            self.mcp.run(
                transport="http",
                host=host,
                port=port,
                path=path,
                allowed_origins=origins.patterns or None,
                bearer_verifier=verifier.verify if verifier else None,
            )
        else:
            log.info("Starting FastMCP in STDIO mode")
            self.mcp.run(transport="stdio")

        if observer:
            observer.stop()
            observer.join(timeout=2)
```

---
## FILE: src/main.py
```python
#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.server import UnifiedMCPServer  # noqa: E402


def main() -> None:
    server = UnifiedMCPServer()
    server.load()
    server.run()


if __name__ == "__main__":
    main()
```

---
## FILE: src/tools/__init__.py
```python
# Namespace package for tools
```

---
## FILE: src/tools/echo.py
```python
from core.app import mcp
from fastmcp import Context

@mcp.tool
async def echo(message: str, ctx: Context) -> str:
    """Echo back the provided message and log it."""
    await ctx.info(f"echo called with: {message}")
    return message
```

---
## FILE: src/tools/needs_elicitation.py
```python
from dataclasses import dataclass
from fastmcp import Context
from core.app import mcp

@dataclass
class Confirm:
    ok: bool

@mcp.tool
async def delete_all(ctx: Context) -> str:
    """Dangerous example: asks user to confirm via elicitation before proceeding."""
    ans = await ctx.elicit(Confirm, prompt="DELETE ALL DATA in workspace?")
    return "deleted" if ans.ok else "cancelled"
```

---
## FILE: src/tools/needs_sampling.py
```python
from fastmcp import Context
from core.app import mcp

@mcp.tool
async def write_release_notes(diff: str, ctx: Context) -> str:
    """Use client's LLM to turn a git diff into release notes (sampling)."""
    system = "You are a release notes generator. Keep it concise."
    msg = {"role": "user", "content": f"Create release notes from this diff:\n{diff}"}
    return await ctx.sample(messages=[msg], temperature=0.3, maxTokens=400, systemPrompt=system)
```

---
## FILE: src/tools/preview_prompt.py
```python
import argparse
import json
from pathlib import Path

from core.loaders import load_single_prompt_with_schema


def preview_prompt(prompt_name: str, strict: bool = False, _prompts_dir: Path = None, **kwargs):
    # prompts/ sits at project root alongside src/
    prompts_dir = _prompts_dir or Path(__file__).resolve().parents[1].parent / "prompts"
    yaml_file = prompts_dir / f"{prompt_name}.yaml"
    if not yaml_file.exists():
        raise FileNotFoundError(f"Prompt '{prompt_name}' not found in {prompts_dir}")

    # Read raw to detect placeholders before schema injection
    raw_text = yaml_file.read_text(encoding="utf-8")
    had_output_schema_placeholder = "{output_schema}" in raw_text
    schema_file = yaml_file.with_suffix(".json")
    has_schema_file = schema_file.exists()

    prompt_data = load_single_prompt_with_schema(yaml_file)
    text = prompt_data["prompt"]

    # Strict mode: error if placeholder existed but schema file missing
    if strict and had_output_schema_placeholder and not has_schema_file:
        raise RuntimeError(f"{yaml_file.name} uses {{output_schema}} but missing schema file: {schema_file.name}")

    # Non-strict: warn if placeholder still present after injection
    if "{output_schema}" in text:
        print(f"[WARN] {yaml_file.name} still contains '{{output_schema}}' — no schema injected or placeholder misspelled.")

    # Replace any provided {placeholders}
    for key, value in kwargs.items():
        text = text.replace(f"{{{key}}}", value)

    print("\n--- Prompt Preview ---\n")
    print(text)
    print("\n--- Metadata ---\n")
    print(json.dumps({k: v for k, v in prompt_data.items() if k != "prompt"}, indent=2))


def _parse_kv_list(kv_list):
    out = {}
    for item in kv_list:
        if "=" not in item:
            raise ValueError(f"Invalid var format: {item}, expected key=value")
        k, v = item.split("=", 1)
        out[k] = v
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Preview a prompt with placeholders filled.")
    parser.add_argument("prompt_name", help="Name of the prompt YAML file without extension")
    parser.add_argument("--vars", nargs="*", default=[], help="Placeholder replacements in key=value format")
    parser.add_argument("--strict", action="store_true", help="Fail if {output_schema} is used but schema file is missing")
    args = parser.parse_args()

    replacements = _parse_kv_list(args.vars)
    preview_prompt(args.prompt_name, strict=args.strict, **replacements)
```

---
## FILE: src/resources/__init__.py
```python
# Namespace package for resources
```

---
## FILE: src/resources/sample_resource.py
```python
from core.app import mcp

@mcp.resource
def readme_snippet() -> str:
    """A small static resource example."""
    return "This is a sample resource string."
```

---
## FILE: tests/test_loaders.py
```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.app import mcp
from core.loaders import load_tools, load_resources, load_prompts


def test_load_tools_resources_prompts(tmp_path: Path):
    # Create temp dirs that mimic project layout
    src_base = tmp_path / "src"
    tools_dir = src_base / "tools"
    resources_dir = src_base / "resources"
    prompts_dir = tmp_path / "prompts"

    tools_dir.mkdir(parents=True)
    resources_dir.mkdir(parents=True)
    prompts_dir.mkdir(parents=True)

    # Write a simple tool
    (tools_dir / "t1.py").write_text(
        "from core.app import mcp\nfrom fastmcp import Context\n@mcp.tool\nasync def t1(x: int, ctx: Context) -> int:\n    await ctx.debug('adding one')\n    return x + 1\n"
    )

    # Write a simple resource
    (resources_dir / "r1.py").write_text(
        "from core.app import mcp\n@mcp.resource\ndef r1() -> str:\n    return 'ok'\n"
    )

    # YAML + JSON schema
    (prompts_dir / "p1.yaml").write_text(
        "name: demo\nprompt: |\n  <output_schema>{output_schema}</output_schema>\n  Hello {name}\n"
    )
    (prompts_dir / "p1.json").write_text('{"type":"object","properties":{"ok":{"type":"boolean"}},"required":["ok"]}')

    # Ensure import path includes temp src
    sys.path.insert(0, str(src_base))

    c1 = load_tools(mcp, tools_dir)
    c2 = load_resources(mcp, resources_dir)
    c3 = load_prompts(mcp, prompts_dir)

    assert c1 >= 1
    assert c2 >= 1
    assert c3 >= 1
```

---
## FILE: tests/test_prompts.py
```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.app import mcp
from core.loaders import load_prompts


def test_yaml_prompt_list_and_single(tmp_path: Path):
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()

    # Single mapping + schema injection
    (prompts_dir / "single.yaml").write_text(
        "name: a\nprompt: |\n  <output_schema>{output_schema}</output_schema>\n  Do A {thing}\n"
    )
    (prompts_dir / "single.json").write_text('{"type":"object","properties":{"x":{"type":"number"}},"required":["x"]}')

    # List mapping (no schema)
    (prompts_dir / "list.yaml").write_text(
        "- name: b\n  prompt: |\n    Do B {foo}\n- name: c\n  prompt: |\n    Do C {bar}\n"
    )

    added = load_prompts(mcp, prompts_dir)
    assert added >= 3
```

---
## FILE: tests/test_preview_prompt.py
```python
import pytest
from pathlib import Path
from tools.preview_prompt import preview_prompt


def test_missing_schema_warning(tmp_path, capsys):
    # Create prompt YAML with {output_schema} placeholder
    prompt_file = tmp_path / "test_prompt.yaml"
    prompt_file.write_text("""\
name: test_prompt
description: Test
prompt: "<output_schema>{output_schema}</output_schema>"
""")

    # No schema file created
    preview_prompt("test_prompt", strict=False, _prompts_dir=tmp_path)
    out = capsys.readouterr().out
    assert "still contains '{output_schema}'" in out


def test_strict_mode_raises(tmp_path):
    prompt_file = tmp_path / "strict_prompt.yaml"
    prompt_file.write_text("""\
name: strict_prompt
description: Test
prompt: "<output_schema>{output_schema}</output_schema>"
""")

    with pytest.raises(RuntimeError) as e:
        preview_prompt("strict_prompt", strict=True, _prompts_dir=tmp_path)
    assert "missing schema file" in str(e.value)
```

---
## FILE: README.md (excerpt)
```md
# FastMCP Unified Template

- Dynamic **tools/resources** via decorators
- **YAML prompts** with automatic **JSON schema injection** into `{output_schema}`
- **Local STDIO** and **OpenShift HTTP** (streamable) transports
- **JWT auth** (optional) and **scope** checks for mutation tools
- **Hot‑reload** for dev, **Kubernetes/OpenShift** manifests, and **pytest** tests
- Works with **uv** or plain **pip**

## Prompt placeholders & schema injection
Placeholders like `{document}` or `{text}` are left intact for runtime replacement by your client/agent. If the prompt contains `{output_schema}`, the loader looks for a **.json file with the same name** and injects a **minified** JSON string into the prompt text before registration.

Example:
```
prompts/
  summarize.yaml   # contains {output_schema}
  summarize.json   # schema injected by loader
```

## Transports
- Local dev: `MCP_TRANSPORT=stdio`
- OpenShift: `MCP_TRANSPORT=http` + Service + Route

## Auth & scopes
- Set `MCP_AUTH_JWT_*` envs. Use `@requires_scopes("mutation:write")` to protect tools.

## Prompt preview CLI
```bash
uv run python -m tools.preview_prompt summarize --vars document="This is the text"
uv run python -m tools.preview_prompt classify --vars text="A sample doc"
# Makefile shortcut
make preview PROMPT=summarize VARS='document=Hello world'
```

## Tests via Makefile
```bash
make test            # full suite
make test-preview    # only preview CLI tests
make test-preview ARGS="-k strict_mode"
```
```

---
**End of single-file pack.**
