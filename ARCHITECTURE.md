# Architecture

This project implements a FastMCP 2.x server with local STDIO and OpenShift HTTP transports, dynamic tooling, prompts with JSON schema injection, and OpenShift-native build/deploy.

- Core framework: FastMCP 2.x
- Transports: STDIO (local), HTTP (OpenShift)
- Dynamic loading: tools, resources, prompts
- Auth: optional JWT verification and scope checks
- OpenShift: ImageStream, BuildConfigs (Git or Binary), Deployment, Service, Route, HPA

## Components

- `src/core/app.py`: Instantiates `FastMCP` and shared logger; imports prompts module for decorator registration
- `src/core/server.py`: Bootstraps logging, loads components, and runs server (STDIO or HTTP)
- `src/core/loaders.py`: Loads tools/resources/prompts from filesystem; hot-reload in dev
- `src/core/auth.py`: Optional JWT verification and scope decorator
- `src/tools/*.py`: Example tools including sampling and elicitation
- `src/resources/*.py`: Example resource with explicit URI
- `src/prompts/*.py`: Python-based prompts using FastMCP decorators (@mcp.prompt())
- `src/tools/preview_prompt.py`: CLI to preview a prompt with injected schema and variable replacements
- `src/ops/deploy_cli.py`: Interactive OpenShift deployer using `oc`

## Runtime Flow (HTTP)

```mermaid
sequenceDiagram
  autonumber
  participant Client
  participant Route
  participant Service
  participant Deployment as "FastMCP HTTP"
  Client->>Route: HTTPS request to /mcp/
  Route->>Service: Forward
  Service->>Deployment: Forward
  Deployment->>Deployment: Bearer JWT verify (optional)
  Deployment->>Deployment: Load tools/resources/prompts
  Deployment-->>Client: Streamable HTTP responses
```

## Loading Flow

```mermaid
flowchart TD
  A[Server start] --> B{Transport}
  B -- STDIO --> C[Run FastMCP in STDIO]
  B -- HTTP --> D[Run FastMCP in HTTP]
  A --> E[load_all]
  E --> F[load_tools]
  E --> G[load_resources]
  E --> H[load_prompts]
  H --> I[Import Python modules with @mcp.prompt decorators]
  I --> J[Decorators auto-register prompts with FastMCP]
```

## OpenShift Build/Deploy

```mermaid
flowchart TD
  L[Local dir] -->|oc start-build --from-dir| B(BuildConfig Binary)
  R[Git repo] -->|BuildConfig Git| B
  B --> I(ImageStreamTag:latest)
  I --> K(Deployment Image)
  K --> S(Service)
  S --> Rt(Route)
```

## Key Decisions

- Use FastMCP 2.x decorator APIs: `@mcp.prompt()` for Python-based prompts with type safety
- Python prompts in `src/prompts/` use Pydantic Field annotations for parameter descriptions
- Resource registration requires explicit URI: `@mcp.resource("resource://...")`
- OpenShift-native builds: prefer Binary Build for local projects without Git; Git Build also supported
- Images pulled from internal registry `image-registry.openshift-image-registry.svc:5000/<ns>/<name>:latest`

## Prompt System

Prompts are defined using Python decorators for better type safety and IDE support:

- Location: `src/prompts/` directory with `__init__.py`, `analysis.py`, `documentation.py`, `general.py`
- Pattern: Use `@mcp.prompt()` decorator on functions
- Type annotations: Use `Annotated[type, Field(...)]` from Pydantic for parameters
- Return types: Support `str`, `Message`, or `list[Message]`
- Hot-reload: Changes to prompt modules are automatically reloaded in dev mode

Example:
```python
from typing import Annotated
from pydantic import Field
from ..core.app import mcp

@mcp.prompt()
def summarize(
    document: Annotated[str, Field(description="The document text to summarize")],
) -> str:
    return f"Summarize the following text:\n<document>{document}</document>"
```

## Configuration

Environment variables (selected):
- `MCP_TRANSPORT` (stdio|http)
- `MCP_HTTP_HOST`, `MCP_HTTP_PORT`, `MCP_HTTP_PATH`
- `MCP_HTTP_ALLOWED_ORIGINS`
- `MCP_AUTH_JWT_ALG`, `MCP_AUTH_JWT_SECRET`, `MCP_AUTH_JWT_PUBLIC_KEY`
- `MCP_REQUIRED_SCOPES`

## CLI Deployment

`mcp-deploy` prompts for namespace, app name, and HTTP settings, applies ImageStream/BuildConfig, performs a binary build, applies runtime manifests, sets env, waits for rollout, and prints the Route host.
