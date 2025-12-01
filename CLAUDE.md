# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Test Commands

```bash
# Install dependencies (creates .venv)
make install

# Run server locally (STDIO mode with hot-reload)
make run-local

# Run all tests
make test
# Or directly:
.venv/bin/pytest tests/ -v

# Run single test file
.venv/bin/pytest tests/test_loaders.py -v

# Run tests matching pattern
.venv/bin/pytest tests/ -k "test_auth" -v

# Test with cmcp (requires separate terminal)
make test-local
# Or: cmcp ".venv/bin/python -m src.main" tools/list

# Deploy to OpenShift
make deploy PROJECT=my-project

# Build container for OpenShift (Mac)
podman build --platform linux/amd64 -f Containerfile -t my-mcp:latest .
```

## Architecture Overview

### Component Loading System

The server uses dynamic component loading at startup via `src/core/loaders.py`:

1. **Entry point**: `src/main.py` creates `UnifiedMCPServer` and calls `load()` then `run()`
2. **Server bootstrap**: `src/core/server.py` orchestrates loading and transport selection
3. **Central MCP instance**: `src/core/app.py` exports the shared `mcp` FastMCP instance
4. **Loaders**: `load_all()` discovers and imports modules from `src/tools/`, `src/resources/`, `src/prompts/`, `src/middleware/`

Components register themselves via FastMCP decorators (`@mcp.tool`, `@mcp.resource`, `@mcp.prompt`) that reference the shared `mcp` instance from `src/core/app.py`.

### Module Structure

```
src/
├── core/
│   ├── app.py        # Creates shared `mcp` FastMCP instance
│   ├── server.py     # UnifiedMCPServer: load + run orchestration
│   ├── loaders.py    # Dynamic discovery of tools/resources/prompts/middleware
│   ├── auth.py       # JWT authentication helpers
│   └── logging.py    # Logging configuration
├── tools/            # Tool implementations (flat directory)
├── resources/        # Resource implementations (supports subdirectories)
├── prompts/          # Python-based prompt definitions
└── middleware/       # Middleware classes (extend FastMCP Middleware base)
```

### Transport Modes

- **STDIO** (local): `MCP_TRANSPORT=stdio` - for cmcp testing
- **HTTP** (OpenShift): `MCP_TRANSPORT=http` - streamable-http on port 8080

## Testing FastMCP Decorated Functions

FastMCP decorators wrap functions in special objects. Access the underlying function via `.fn`:

```python
from src.tools.my_tool import my_tool

my_tool_fn = my_tool.fn  # Access underlying function

@pytest.mark.asyncio
async def test_my_tool():
    result = await my_tool_fn(param1="value1")
    assert result == "expected"
```

## Dependency Management

Dependencies must be listed in BOTH files:
- `pyproject.toml` - for local `pip install -e .`
- `requirements.txt` - for container builds

## Adding Components

### Tools (`src/tools/`)

```python
from typing import Annotated
from pydantic import Field
from fastmcp import Context
from src.core.app import mcp

@mcp.tool
async def my_tool(
    param: Annotated[str, Field(description="Parameter description")],
    ctx: Context = None,
) -> str:
    """Tool description for the LLM."""
    return f"Result: {param}"
```

### Resources (`src/resources/`)

Supports subdirectories. Files are auto-discovered.

```python
from src.core.app import mcp

@mcp.resource("weather://{city}/current")
async def get_weather(city: str) -> dict:
    """Weather for a city."""
    return {"city": city, "temperature": 22}
```

### Prompts (`src/prompts/`)

```python
from pydantic import Field
from src.core.app import mcp

@mcp.prompt
def my_prompt(
    query: str = Field(description="User query"),
) -> str:
    """Purpose of this prompt."""
    return f"Please answer: {query}"
```

**Type annotations**: Use parameterized types (`dict[str, str]`, `list[str]`) - never bare `dict` or `list`.

### Middleware (`src/middleware/`)

```python
from fastmcp.server.middleware import Middleware

class MyMiddleware(Middleware):
    async def on_call_tool(self, context, request, next_handler):
        # Pre-execution
        result = await next_handler(context, request)
        # Post-execution
        return result
```

## Generator CLI

```bash
# Generate tool
fips-agents generate tool my_tool --description "Tool description" --async --with-context

# Generate resource
fips-agents generate resource my_resource --uri "data://my-resource" --mime-type "application/json"

# Generate prompt
fips-agents generate prompt my_prompt --description "Prompt description"

# Generate middleware
fips-agents generate middleware my_middleware --description "Middleware description" --async
```

## Prompt Return Types

- `str` - Simple string (default)
- `PromptMessage` - Structured message with role
- `list[PromptMessage]` - Multi-turn conversation

## Pre-deployment

Run `./remove_examples.sh` before first deployment to remove example code and reduce build context size.
