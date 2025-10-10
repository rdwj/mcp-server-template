# FastMCP Server Template

A production-ready MCP (Model Context Protocol) server template with dynamic tool/resource loading, YAML-based prompts, and seamless OpenShift deployment.

## Features

- 🔧 **Dynamic tool/resource loading** via decorators
- 📝 **YAML prompts** with automatic JSON schema injection
- 🚀 **One-command OpenShift deployment**
- 🔄 **Hot-reload** for local development
- 🧪 **Local STDIO** and **OpenShift HTTP** transports
- 🔐 **JWT authentication** (optional) with scope-based authorization
- ✅ **Full test suite** with pytest

## Quick Start

### Local Development

```bash
# Install and run locally
make install
make run-local

# Test with cmcp (in another terminal)
cmcp ".venv/bin/python -m src.main" tools/list
```

### Deploy to OpenShift

```bash
# One-command deployment
make deploy

# Or deploy to specific project
make deploy PROJECT=my-project
```

## Project Structure

```
├── src/
│   ├── core/           # Core server components
│   ├── tools/          # Tool implementations
│   └── resources/      # Resource implementations
├── prompts/            # YAML prompt definitions
├── tests/              # Test suite
├── Containerfile       # Container definition
├── openshift.yaml      # OpenShift manifests
├── deploy.sh           # Deployment script
├── requirements.txt    # Python dependencies
└── Makefile           # Common tasks
```

## Development

### Adding Tools

Create a Python file in `src/tools/`. Tools support rich type annotations, validation, and metadata:

```python
from typing import Annotated
from pydantic import Field
from fastmcp import Context
from fastmcp.exceptions import ToolError
from src.core.app import mcp

@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def my_tool(
    param: Annotated[str, Field(description="Parameter description", min_length=1, max_length=100)],
    ctx: Context = None,
) -> str:
    """Tool description for the LLM."""
    await ctx.info("Processing request")

    if not param.strip():
        raise ToolError("Parameter cannot be empty")

    return f"Result: {param}"
```

**Best Practices:**
- Use `Annotated` for parameter descriptions (FastMCP 2.11.0+)
- Add Pydantic `Field` constraints for validation
- Use tool `annotations` for hints about behavior
- Always include `ctx: Context = None` for logging and capabilities
- Raise `ToolError` for user-facing validation errors
- Use structured output (dataclasses) for complex results

See [TOOLS_GUIDE.md](docs/TOOLS_GUIDE.md) for comprehensive examples and patterns.

### Adding Resources

Create a file in `src/resources/`:

```python
from src.core.app import mcp

@mcp.resource("resource://my-resource")
async def get_my_resource() -> str:
    return "Resource content"
```

### Creating Prompts

Add YAML file to `prompts/`:

```yaml
name: my_prompt
description: Purpose of this prompt
prompt: |
  Your prompt text with {variable_name} placeholders
```

For structured output, add a matching JSON schema file (same base name).

## Testing

### Local Testing (STDIO)

```bash
# Run server
make run-local

# Test with cmcp
make test-local

# Run unit tests
make test
```

### OpenShift Testing (HTTP)

```bash
# Deploy
make deploy

# Test with MCP Inspector
npx @modelcontextprotocol/inspector https://<route-url>/mcp/
```

See [TESTING.md](TESTING.md) for detailed testing instructions.

## Environment Variables

### Local Development
- `MCP_TRANSPORT=stdio` - Use STDIO transport
- `MCP_HOT_RELOAD=1` - Enable hot-reload

### OpenShift Deployment
- `MCP_TRANSPORT=http` - Use HTTP transport (set automatically)
- `MCP_HTTP_HOST=0.0.0.0` - HTTP server host
- `MCP_HTTP_PORT=8080` - HTTP server port
- `MCP_HTTP_PATH=/mcp/` - HTTP endpoint path

### Optional Authentication
- `MCP_AUTH_JWT_SECRET` - JWT secret for symmetric signing
- `MCP_AUTH_JWT_PUBLIC_KEY` - JWT public key for asymmetric
- `MCP_REQUIRED_SCOPES` - Comma-separated required scopes

## Available Commands

```bash
make help         # Show all available commands
make install      # Install dependencies
make run-local    # Run locally with STDIO
make test         # Run test suite
make deploy       # Deploy to OpenShift
make clean        # Clean up OpenShift deployment
```

## Prompt Schema Injection

If a prompt contains `{output_schema}`, the system automatically injects a minified JSON schema:

```
prompts/
  summarize.yaml   # Contains {output_schema} placeholder
  summarize.json   # Schema to inject
```

## Architecture

The server uses FastMCP 2.x with:
- Dynamic component loading at startup
- Hot-reload in development mode
- Automatic prompt registration with schema injection
- Support for both STDIO (local) and HTTP (OpenShift) transports

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed architecture information.

## Requirements

- Python 3.11+
- OpenShift CLI (`oc`) for deployment
- cmcp for local testing: `pip install cmcp`

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details on how to get started, development setup, and submission guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.