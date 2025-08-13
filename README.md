# FastMCP Unified Template

- Dynamic **tools/resources** via decorators
- **YAML prompts** with automatic **JSON schema injection** into `{output_schema}`
- **Local STDIO** and **OpenShift HTTP** (streamable) transports
- **JWT auth** (optional) and **scope** checks for mutation tools
- **Hot‑reload** for dev, **Kubernetes/OpenShift** manifests, and **pytest** tests
- Works with **uv** or plain **pip**

## Quickstart

```bash
# Local dev
make dev

# Run tests
make test

# Deploy to OpenShift via interactive CLI (binary build)
source .venv/bin/activate
mcp-deploy
```

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

## OpenShift build/deploy

Two supported flows:

- Binary Build (no Git):
  ```bash
  make k8s-apply          # applies imagestream + buildconfigs + runtime manifests
  make oc-bc-binary       # ensures binary BC exists
  make oc-bc-binary-start # uploads current dir and builds in-cluster
  ```

- Git BuildConfig (set repo URL in `k8s/buildconfig.yaml`):
  ```bash
  make oc-setup
  make oc-bc-start
  ```

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
