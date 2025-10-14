# FastMCP Server Template

A production-ready MCP (Model Context Protocol) server template with dynamic tool/resource loading, Python decorator-based prompts, and seamless OpenShift deployment.

## Features

- 🔧 **Dynamic tool/resource loading** via decorators
- 📝 **Python-based prompts** with type safety and FastMCP decorators
- 🔀 **Middleware support** for cross-cutting concerns
- 🏗️ **Generator system** for scaffolding new components
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
│   ├── resources/      # Resource implementations
│   ├── prompts/        # Python-based prompt definitions
│   └── middleware/     # Middleware implementations
├── tests/              # Test suite
├── .fips-agents-cli/   # Generator templates
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

**Or use the generator:**
```bash
fips-agents generate tool my-tool --async --with-context
```

### Adding Resources

Create a file in `src/resources/`:

```python
from src.core.app import mcp

@mcp.resource("resource://my-resource")
async def get_my_resource() -> str:
    return "Resource content"
```

**Or use the generator:**
```bash
fips-agents generate resource my-resource --uri "resource://my-resource"
```

### Creating Prompts

Create Python files in `src/prompts/`. Prompts support multiple return types, async operations, context access, and metadata:

**Basic String Prompt:**
```python
from pydantic import Field
from src.core.app import mcp

@mcp.prompt
def my_prompt(
    query: str = Field(description="User query"),
) -> str:
    """Purpose of this prompt"""
    return f"Please answer: {query}"
```

**Async Prompt with Context:**
```python
from pydantic import Field
from fastmcp import Context
from src.core.app import mcp

@mcp.prompt
async def fetch_prompt(
    url: str = Field(description="Data source URL"),
    ctx: Context,
) -> str:
    """Fetch data and create prompt"""
    # Perform async operations
    return f"Analyze data from {url}"
```

**Structured Message Prompt:**
```python
from pydantic import Field
from fastmcp.prompts.prompt import PromptMessage, TextContent
from src.core.app import mcp

@mcp.prompt
def structured_prompt(
    task: str = Field(description="Task description"),
) -> PromptMessage:
    """Create structured message"""
    return PromptMessage(
        role="user",
        content=TextContent(type="text", text=f"Task: {task}")
    )
```

**Advanced with Metadata:**
```python
from pydantic import Field
from src.core.app import mcp

@mcp.prompt(
    name="custom_name",
    title="Human Readable Title",
    description="Custom description",
    tags={"analysis", "reporting"},
    meta={"version": "1.0", "author": "team"}
)
def advanced_prompt(
    data: dict[str, str] = Field(description="Data to process"),
) -> str:
    """Advanced prompt with full metadata"""
    return f"Analyze: {data}"
```

**Generator Examples:**
```bash
# Basic prompt
fips-agents generate prompt summarize_text \
    --description "Summarize text content"

# Async with Context
fips-agents generate prompt fetch_and_analyze \
    --async --with-context \
    --return-type PromptMessage

# With parameters file
fips-agents generate prompt analyze_data \
    --params params.json --with-schema

# Advanced with metadata
fips-agents generate prompt report_generator \
    --async --with-context \
    --prompt-name "generate_report" \
    --title "Report Generator" \
    --tags "reporting,analysis" \
    --meta '{"version": "2.0"}'
```

**Return Types:**
- `str` - Simple string prompt (default)
- `PromptMessage` - Structured message with role
- `list[PromptMessage]` - Multi-turn conversation
- `PromptResult` - Full prompt result object

See [CLAUDE.md](CLAUDE.md) for comprehensive prompt generation documentation and `src/prompts/` for working examples.

### Adding Middleware

Create a file in `src/middleware/`:

```python
from typing import Any, Callable
from fastmcp import Context
from core.app import mcp

@mcp.middleware()
async def my_middleware(
    ctx: Context,
    next_handler: Callable,
    *args: Any,
    **kwargs: Any
) -> Any:
    # Pre-execution logic
    result = await next_handler(*args, **kwargs)
    # Post-execution logic
    return result
```

Middleware wraps tool execution to add cross-cutting concerns like logging, authentication, rate limiting, caching, etc.

See `src/middleware/logging_middleware.py` for a working example and `src/middleware/auth_middleware.py` for a commented authentication pattern.

**Or use the generator:**
```bash
fips-agents generate middleware my-middleware --async
```

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

## Architecture

The server uses FastMCP 2.x with:
- Dynamic component loading at startup
- Hot-reload in development mode
- Python decorator-based prompts with type safety
- Automatic component registration via decorators (`@mcp.tool()`, `@mcp.resource()`, `@mcp.prompt()`, `@mcp.middleware()`)
- Middleware for cross-cutting concerns
- Generator system with Jinja2 templates for scaffolding
- Support for both STDIO (local) and HTTP (OpenShift) transports

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed architecture information and [GENERATOR_PLAN.md](GENERATOR_PLAN.md) for generator system documentation.

## Requirements

- Python 3.11+
- OpenShift CLI (`oc`) for deployment
- cmcp for local testing: `pip install cmcp`

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details on how to get started, development setup, and submission guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.