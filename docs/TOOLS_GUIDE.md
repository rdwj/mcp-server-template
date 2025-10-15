# FastMCP Tools Development Guide

This guide provides comprehensive examples and best practices for creating MCP tools using FastMCP 2.x.

## Table of Contents

1. [Basic Tool Creation](#basic-tool-creation)
2. [Type Hints and Descriptions](#type-hints-and-descriptions)
3. [Tool Annotations](#tool-annotations)
4. [Field Validation](#field-validation)
5. [Error Handling](#error-handling)
6. [Structured Outputs](#structured-outputs)
7. [Context Usage](#context-usage)
8. [Runtime Dependencies](#runtime-dependencies)
9. [Async vs Sync](#async-vs-sync)
10. [Advanced Patterns](#advanced-patterns)
11. [Testing Tools](#testing-tools)

## Basic Tool Creation

The simplest tool is a decorated function:

```python
from core.app import mcp

@mcp.tool
def hello(name: str) -> str:
    """Greet a user by name."""
    return f"Hello, {name}!"
```

**Key points:**
- Use the `@mcp.tool` decorator
- Provide a clear docstring (shown to LLM)
- Use type hints for parameters and return value
- Keep tools focused on a single responsibility

## Type Hints and Descriptions

FastMCP 2.11.0+ supports `Annotated` types for rich parameter descriptions:

```python
from typing import Annotated
from core.app import mcp

@mcp.tool
def calculate_area(
    width: Annotated[float, "Width of the rectangle in meters"],
    height: Annotated[float, "Height of the rectangle in meters"],
) -> float:
    """Calculate the area of a rectangle."""
    return width * height
```

**Benefits:**
- Parameter descriptions appear in tool schemas
- Better documentation for LLMs and developers
- Self-documenting code
- No need for separate schema files

## Tool Annotations

Tool annotations (FastMCP 2.2.7+) provide hints about tool behavior:

```python
from core.app import mcp

@mcp.tool(
    annotations={
        "readOnlyHint": True,      # Doesn't modify state
        "idempotentHint": True,    # Same inputs = same outputs
        "openWorldHint": False,    # Doesn't access external systems
    }
)
def calculate_sum(numbers: list[float]) -> float:
    """Sum a list of numbers."""
    return sum(numbers)
```

### Available Annotations

- **readOnlyHint**: `True` if the tool doesn't modify any state
- **idempotentHint**: `True` if calling with same inputs always produces same outputs
- **destructiveHint**: `True` if the tool performs destructive operations
- **openWorldHint**: `True` if the tool accesses external systems (APIs, databases, etc.)

### Annotation Guidelines

| Tool Type | readOnlyHint | idempotentHint | destructiveHint | openWorldHint |
|-----------|--------------|----------------|-----------------|---------------|
| Math calculation | True | True | False | False |
| Read local file | True | True | False | False |
| Fetch from API | True | False* | False | True |
| Write to file | False | True | False | False |
| Delete data | False | False | True | False |
| Current time | True | False | False | False |

*API calls may not be idempotent if data changes

## Field Validation

Use Pydantic `Field` for parameter validation:

```python
from typing import Annotated
from pydantic import Field
from core.app import mcp

@mcp.tool
def process_batch(
    count: Annotated[int, Field(description="Number of items", ge=1, le=1000)],
    name: Annotated[str, Field(description="Batch name", min_length=1, max_length=50)],
    priority: Annotated[int, Field(description="Priority level", ge=1, le=5)] = 3,
) -> str:
    """Process a batch with validation."""
    return f"Processing {count} items in batch '{name}' with priority {priority}"
```

### Common Field Constraints

**Numeric constraints:**
- `ge` (greater than or equal)
- `gt` (greater than)
- `le` (less than or equal)
- `lt` (less than)

**String constraints:**
- `min_length`
- `max_length`
- `pattern` (regex)

**Other constraints:**
- `multiple_of` (for numbers)
- Custom validators

## Error Handling

Use `ToolError` for user-facing errors:

```python
from typing import Annotated
from fastmcp import Context
from fastmcp.exceptions import ToolError
from core.app import mcp

@mcp.tool
def divide(
    dividend: Annotated[float, "Number to divide"],
    divisor: Annotated[float, "Number to divide by"],
    ctx: Context = None,
) -> float:
    """Divide two numbers."""
    await ctx.info(f"Dividing {dividend} by {divisor}")

    if divisor == 0:
        raise ToolError("Cannot divide by zero")

    return dividend / divisor
```

**Error handling best practices:**
- Use `ToolError` for expected errors (validation, business logic)
- Let unexpected errors propagate (will be caught by FastMCP)
- Provide clear, actionable error messages
- Log context before raising errors

### Error Examples

```python
# Validation error
if not data.strip():
    raise ToolError("Data cannot be empty")

# Business logic error
if balance < amount:
    raise ToolError(f"Insufficient funds: have ${balance}, need ${amount}")

# Resource not found
if not file_exists(path):
    raise ToolError(f"File not found: {path}")

# External API error
if response.status_code != 200:
    raise ToolError(f"API request failed: {response.text}")
```

## Structured Outputs

Use dataclasses for complex return types (FastMCP 2.10.0+):

```python
from typing import Annotated
from dataclasses import dataclass
from fastmcp import Context
from core.app import mcp

@dataclass
class FileStats:
    """File statistics."""
    size_bytes: int
    line_count: int
    word_count: int
    last_modified: str

@mcp.tool
async def analyze_file(
    path: Annotated[str, "Path to the file"],
    ctx: Context = None,
) -> FileStats:
    """Analyze a file and return statistics."""
    await ctx.info(f"Analyzing file: {path}")

    # ... file analysis logic ...

    return FileStats(
        size_bytes=1024,
        line_count=42,
        word_count=350,
        last_modified="2025-10-10T12:00:00Z"
    )
```

**Benefits of structured outputs:**
- Type-safe return values
- Clear schema for LLMs
- Easy to serialize/deserialize
- Self-documenting results

### Nested Structures

```python
from dataclasses import dataclass

@dataclass
class Address:
    street: str
    city: str
    country: str

@dataclass
class Person:
    name: str
    age: int
    address: Address
    tags: list[str]

@mcp.tool
def get_person(person_id: int) -> Person:
    """Get person details."""
    return Person(
        name="Alice",
        age=30,
        address=Address(
            street="123 Main St",
            city="Boston",
            country="USA"
        ),
        tags=["developer", "fastmcp"]
    )
```

## Context Usage

The `Context` parameter provides access to MCP capabilities:

```python
from fastmcp import Context
from core.app import mcp

@mcp.tool
async def smart_summary(
    text: str,
    ctx: Context = None,
) -> str:
    """Summarize text using the client's LLM."""
    # Logging
    await ctx.info("Starting summarization")
    await ctx.debug(f"Text length: {len(text)} characters")

    # Sampling (use client's LLM)
    result = await ctx.sample(
        messages="Summarize this concisely: " + text,
        temperature=0.3,
        max_tokens=200
    )

    await ctx.info("Summarization complete")
    return str(result)
```

### Context Methods

**Logging:**
```python
await ctx.debug("Debug message")
await ctx.info("Info message")
await ctx.warning("Warning message")
await ctx.error("Error message")
```

**Sampling (LLM):**
```python
result = await ctx.sample(
    messages="Your prompt",
    temperature=0.7,
    max_tokens=500,
    system_prompt="Optional system prompt"
)
```

**Elicitation (user input):**
```python
from dataclasses import dataclass

@dataclass
class Confirmation:
    confirm: bool

result = await ctx.elicit(
    message="Are you sure?",
    response_type=Confirmation
)

if result.action == "accept":
    confirmed = result.data.confirm
```

**Progress reporting:**
```python
await ctx.report_progress(
    progress=50,
    total=100,
    message="Processing..."
)
```

### Context Best Practices

- Always include `ctx: Context = None` in tool signature
- Don't check for `None` - FastMCP guarantees injection
- Use logging for debugging and transparency
- Use sampling to leverage the client's LLM
- Use elicitation for interactive workflows

## Runtime Dependencies

FastMCP v2.2.11+ provides runtime dependency functions that allow you to access context and HTTP information from anywhere within your tool's execution flow, not just in the tool function itself. This is particularly useful for nested utility functions.

### get_context()

Access the current FastMCP Context from anywhere in the request execution flow:

```python
from fastmcp.server.dependencies import get_context

async def process_data_internal(data: list[float]) -> dict:
    """Utility function that needs context but doesn't receive it as a parameter."""
    # Get the active context - only works within a request
    ctx = get_context()

    await ctx.info(f"Processing {len(data)} data points")

    return {"processed": len(data)}

@mcp.tool
async def analyze_dataset(numbers: list[float]) -> dict:
    """Tool that calls utility function which uses context internally."""
    # No need to pass ctx to the utility function
    result = await process_data_internal(numbers)
    return result
```

**When to use:**
- Nested utility functions that need logging
- Shared helper functions used by multiple tools
- Deep call stacks where passing ctx through all layers is impractical

**Important:** `get_context()` only works during a request. Calling it outside a request will raise a `RuntimeError`.

### get_access_token()

Access authenticated user's token information (FastMCP v2.11.0+):

```python
from fastmcp.server.dependencies import get_access_token, AccessToken

@mcp.tool
async def get_user_info() -> dict:
    """Get information about the authenticated user."""
    token: AccessToken | None = get_access_token()

    if token is None:
        return {"authenticated": False}

    return {
        "authenticated": True,
        "client_id": token.client_id,
        "scopes": token.scopes,
        "user_id": token.claims.get("sub"),
        "tenant_id": token.claims.get("tenant_id"),
        "all_claims": token.claims,
    }
```

**Token attributes:**
- `client_id`: OAuth client identifier
- `scopes`: List of granted scopes
- `claims`: Full JWT claims dictionary
- `expires_at`: Token expiration timestamp

**When to use:**
- Multi-tenant applications (extract tenant ID from claims)
- Permission checking (verify scopes)
- User identification (get user ID from `sub` claim)
- Audit logging (track who performed actions)

### get_http_headers()

Safely access HTTP request headers:

```python
from fastmcp.server.dependencies import get_http_headers

@mcp.tool
async def analyze_request() -> dict:
    """Analyze the HTTP request headers."""
    # Get headers (returns empty dict if no request context)
    headers = get_http_headers()

    return {
        "user_agent": headers.get("user-agent", "Unknown"),
        "content_type": headers.get("content-type", "Unknown"),
        "accept": headers.get("accept", "Unknown"),
        "has_auth": bool(headers.get("authorization")),
    }
```

**Features:**
- Returns empty dict if not in HTTP request context (no errors)
- By default, excludes problematic headers like `host` and `content-length`
- Use `get_http_headers(include_all=True)` to include all headers

**When to use:**
- Content negotiation (check `accept` header)
- User agent detection
- Custom header processing
- Debugging request details

### get_http_request()

Access the full HTTP request object for advanced use cases:

```python
from fastmcp.server.dependencies import get_http_request
from starlette.requests import Request

@mcp.tool
async def get_request_details() -> dict:
    """Get detailed HTTP request information."""
    request: Request = get_http_request()

    return {
        "method": request.method,
        "url": str(request.url),
        "path": request.url.path,
        "client_ip": request.client.host if request.client else "Unknown",
        "headers_count": len(request.headers),
    }
```

**Request attributes:**
- `method`: HTTP method (GET, POST, etc.)
- `url`: Full URL object
- `headers`: Header collection
- `client`: Client connection info
- `path_params`: URL path parameters
- `query_params`: Query string parameters

**When to use:**
- Need full request details beyond headers
- IP-based access control
- Request logging and analytics
- URL path/query parameter access

### Runtime Dependencies Best Practices

1. **Prefer Parameter Injection**: Use `ctx: Context` parameter when possible - it's clearer and more testable
2. **Use for Utilities**: Runtime dependencies shine in shared utility functions
3. **Handle Absence Gracefully**: Check for `None` when using `get_access_token()` or use try/except for others
4. **Document Usage**: Clearly document when functions use runtime dependencies
5. **Test Carefully**: Mock runtime dependencies in tests (see examples below)

### Testing with Runtime Dependencies

```python
import pytest
from unittest.mock import patch, MagicMock
from fastmcp.server.dependencies import AccessToken

@pytest.mark.asyncio
async def test_tool_with_runtime_deps():
    """Test tool that uses runtime dependencies."""

    # Mock get_access_token
    mock_token = AccessToken(
        client_id="test_client",
        scopes=["read:data"],
        claims={"sub": "user_123", "tenant_id": "tenant_abc"}
    )

    with patch('fastmcp.server.dependencies.get_access_token', return_value=mock_token):
        result = await get_user_info()
        assert result["authenticated"] is True
        assert result["tenant_id"] == "tenant_abc"
```

### Example: Combining Runtime Dependencies

```python
from fastmcp.server.dependencies import get_context, get_access_token, get_http_headers

async def create_audit_entry(action: str, details: dict) -> dict:
    """Utility function that creates comprehensive audit records."""
    # Access context for logging
    ctx = get_context()
    await ctx.info(f"Audit: {action}")

    # Get user info from token
    token = get_access_token()
    user_id = token.claims.get("sub") if token else "anonymous"

    # Get request info
    headers = get_http_headers()
    user_agent = headers.get("user-agent", "unknown")

    return {
        "action": action,
        "details": details,
        "user_id": user_id,
        "user_agent": user_agent,
        "timestamp": "2025-10-15T00:00:00Z",
    }

@mcp.tool
async def perform_sensitive_operation(data: str) -> dict:
    """Tool that performs audited operation."""
    # Create audit record using runtime dependencies
    audit = await create_audit_entry(
        "sensitive_operation",
        {"data_length": len(data)}
    )

    # ... perform operation ...

    return {"status": "success", "audit": audit}
```

See `src/tools/examples/runtime_deps.py` for complete working examples.

## Async vs Sync

Choose async or sync based on your tool's needs:

### Async Tools (Recommended)

Use async for:
- I/O operations (file, network, database)
- Using Context methods (all are async)
- Long-running operations
- Concurrent operations

```python
@mcp.tool
async def fetch_data(url: str, ctx: Context = None) -> dict:
    """Fetch data from an API."""
    await ctx.info(f"Fetching {url}")

    async with httpx.AsyncClient() as client:
        response = await client.get(url)

    return response.json()
```

### Sync Tools

Use sync for:
- Pure computations
- Simple data transformations
- Quick operations without I/O

```python
@mcp.tool
def calculate_factorial(n: int) -> int:
    """Calculate factorial of a number."""
    if n < 0:
        raise ToolError("Number must be non-negative")

    result = 1
    for i in range(1, n + 1):
        result *= i

    return result
```

**Note:** Even sync tools can have `ctx: Context = None`, but you can't use ctx methods in sync tools.

## Advanced Patterns

### Optional Parameters with Smart Defaults

```python
@mcp.tool
async def search(
    query: Annotated[str, "Search query"],
    limit: Annotated[int, Field(description="Max results", ge=1, le=100)] = 10,
    case_sensitive: Annotated[bool, "Case sensitive search"] = False,
    ctx: Context = None,
) -> list[str]:
    """Search with configurable options."""
    await ctx.info(f"Searching for '{query}' (limit={limit}, case_sensitive={case_sensitive})")
    # ... search logic ...
    return []
```

### Literal Types for Enums

```python
from typing import Literal

@mcp.tool
def set_log_level(
    level: Annotated[Literal["debug", "info", "warning", "error"], "Log level to set"],
) -> str:
    """Set the logging level."""
    # level is guaranteed to be one of the specified values
    return f"Log level set to: {level}"
```

### Union Types for Flexible Input

```python
from typing import Annotated

@mcp.tool
def format_value(
    value: Annotated[int | float | str, "Value to format"],
    precision: Annotated[int, "Decimal places for numbers"] = 2,
) -> str:
    """Format different types of values."""
    if isinstance(value, (int, float)):
        return f"{value:.{precision}f}"
    return str(value)
```

### List and Dict Parameters

```python
@mcp.tool
async def analyze_dataset(
    data: Annotated[list[float], "List of numeric values"],
    metadata: Annotated[dict[str, str], "Optional metadata"] = None,
    ctx: Context = None,
) -> dict:
    """Analyze a dataset."""
    if not data:
        raise ToolError("Dataset cannot be empty")

    await ctx.info(f"Analyzing {len(data)} data points")

    return {
        "count": len(data),
        "mean": sum(data) / len(data),
        "min": min(data),
        "max": max(data),
        "metadata": metadata or {}
    }
```

### Conditional Processing

```python
@mcp.tool
async def process_text(
    text: Annotated[str, "Text to process"],
    uppercase: Annotated[bool, "Convert to uppercase"] = False,
    remove_punctuation: Annotated[bool, "Remove punctuation"] = False,
    max_length: Annotated[int | None, "Maximum length (None=unlimited)"] = None,
    ctx: Context = None,
) -> str:
    """Process text with various transformations."""
    result = text

    if uppercase:
        result = result.upper()
        await ctx.debug("Applied uppercase")

    if remove_punctuation:
        result = ''.join(c for c in result if c.isalnum() or c.isspace())
        await ctx.debug("Removed punctuation")

    if max_length and len(result) > max_length:
        result = result[:max_length] + "..."
        await ctx.debug(f"Truncated to {max_length} chars")

    return result
```

### Retry Logic

```python
import asyncio
from typing import Annotated

@mcp.tool(
    annotations={"openWorldHint": True}
)
async def fetch_with_retry(
    url: Annotated[str, "URL to fetch"],
    max_retries: Annotated[int, Field(description="Max retry attempts", ge=1, le=5)] = 3,
    ctx: Context = None,
) -> str:
    """Fetch URL with automatic retry on failure."""
    for attempt in range(1, max_retries + 1):
        try:
            await ctx.info(f"Attempt {attempt}/{max_retries}")
            # ... fetch logic ...
            return "Success"
        except Exception as e:
            if attempt == max_retries:
                raise ToolError(f"Failed after {max_retries} attempts: {e}")
            await ctx.warning(f"Attempt {attempt} failed, retrying...")
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

## Testing Tools

Create comprehensive tests for your tools:

```python
import pytest
from unittest.mock import AsyncMock
from fastmcp.exceptions import ToolError
from pydantic import ValidationError

from tools.my_tools import my_tool

class TestMyTool:
    @pytest.mark.asyncio
    async def test_basic_functionality(self):
        """Test basic tool operation."""
        ctx = AsyncMock()
        result = await my_tool("input", ctx=ctx)
        assert result == "expected output"
        ctx.info.assert_called_once()

    @pytest.mark.asyncio
    async def test_validation_error(self):
        """Test parameter validation."""
        ctx = AsyncMock()
        with pytest.raises(ValidationError):
            await my_tool(invalid_param=-1, ctx=ctx)

    @pytest.mark.asyncio
    async def test_tool_error(self):
        """Test error handling."""
        ctx = AsyncMock()
        with pytest.raises(ToolError) as excinfo:
            await my_tool("", ctx=ctx)
        assert "cannot be empty" in str(excinfo.value).lower()

    @pytest.mark.asyncio
    async def test_context_usage(self):
        """Test context methods are called."""
        ctx = AsyncMock()
        await my_tool("input", ctx=ctx)
        assert ctx.info.called
        assert ctx.debug.called
```

### Test Coverage Goals

Aim to test:
- ✅ Happy path (normal operation)
- ✅ Edge cases (boundary values)
- ✅ Validation errors (Field constraints)
- ✅ Tool errors (business logic)
- ✅ Context usage (logging, sampling, elicitation)
- ✅ Optional parameters (defaults and overrides)
- ✅ Structured outputs (correct types)

## Quick Reference

### Tool Template

```python
from typing import Annotated
from pydantic import Field
from fastmcp import Context
from fastmcp.exceptions import ToolError
from core.app import mcp

@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def my_tool(
    required_param: Annotated[str, Field(description="Description", min_length=1)],
    optional_param: Annotated[int, "Description"] = 10,
    ctx: Context = None,
) -> str:
    """Clear description of what the tool does."""
    await ctx.info("Starting operation")

    # Validation
    if not required_param.strip():
        raise ToolError("Parameter cannot be empty")

    # Processing
    result = f"Processed: {required_param}"

    await ctx.info("Operation complete")
    return result
```

## Best Practices Summary

1. ✅ Use `Annotated` for parameter descriptions
2. ✅ Add Pydantic `Field` constraints for validation
3. ✅ Include tool annotations for behavior hints
4. ✅ Always include `ctx: Context = None`
5. ✅ Use `ToolError` for user-facing errors
6. ✅ Return structured data (dataclasses) for complex results
7. ✅ Write comprehensive tests
8. ✅ Prefer async for I/O operations
9. ✅ Provide clear docstrings
10. ✅ Keep tools focused and single-purpose

## Additional Resources

- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [MCP Specification](https://modelcontextprotocol.io/)
- Example tools: `src/tools/advanced_examples.py`
