# Tools

> Expose functions as executable capabilities for your MCP client.

export const VersionBadge = ({version}) => {
  return `<code className="version-badge-container">`
            `<p className="version-badge">`
                `<span className="version-badge-label">`New in version: 
                `<code className="version-badge-version">`{version}`</code>`
            `</p>`
        `</code>`;
};

Tools are the core building blocks that allow your LLM to interact with external systems, execute code, and access data that isn't in its training data. In FastMCP, tools are Python functions exposed to LLMs through the MCP protocol.

## What Are Tools?

Tools in FastMCP transform regular Python functions into capabilities that LLMs can invoke during conversations. When an LLM decides to use a tool:

1. It sends a request with parameters based on the tool's schema.
2. FastMCP validates these parameters against your function's signature.
3. Your function executes with the validated inputs.
4. The result is returned to the LLM, which can use it in its response.

This allows LLMs to perform tasks like querying databases, calling APIs, making calculations, or accessing files—extending their capabilities beyond what's in their training data.

## Tools

### The `@tool` Decorator

Creating a tool is as simple as decorating a Python function with `@mcp.tool`:

```python
from fastmcp import FastMCP

mcp = FastMCP(name="CalculatorServer")

@mcp.tool
def add(a: int, b: int) -> int:
    """Adds two integer numbers together."""
    return a + b
```

When this tool is registered, FastMCP automatically:

* Uses the function name (`add`) as the tool name.
* Uses the function's docstring (`Adds two integer numbers...`) as the tool description.
* Generates an input schema based on the function's parameters and type annotations.
* Handles parameter validation and error reporting.

The way you define your Python function dictates how the tool appears and behaves for the LLM client.

<Tip>
  Functions with `*args` or `**kwargs` are not supported as tools. This restriction exists because FastMCP needs to generate a complete parameter schema for the MCP protocol, which isn't possible with variable argument lists.
</Tip>

#### Decorator Arguments

While FastMCP infers the name and description from your function, you can override these and add additional metadata using arguments to the `@mcp.tool` decorator:

```python
@mcp.tool(
    name="find_products",           # Custom tool name for the LLM
    description="Search the product catalog with optional category filtering.", # Custom description
    tags={"catalog", "search"},      # Optional tags for organization/filtering
    meta={"version": "1.2", "author": "product-team"}  # Custom metadata
)
def search_products_implementation(query: str, category: str | None = None) -> list[dict]:
    """Internal function description (ignored if description is provided above)."""
    # Implementation...
    print(f"Searching for '{query}' in category '{category}'")
    return [{"id": 2, "name": "Another Product"}]
```

<Card icon="code" title="@tool Decorator Arguments">
  <ParamField body="name" type="str | None">
    Sets the explicit tool name exposed via MCP. If not provided, uses the function name
  </ParamField>

<ParamField body="description" type="str | None">
    Provides the description exposed via MCP. If set, the function's docstring is ignored for this purpose
  </ParamField>

<ParamField body="tags" type="set[str] | None">
    A set of strings used to categorize the tool. These can be used by the server and, in some cases, by clients to filter or group available tools.
  </ParamField>

<ParamField body="enabled" type="bool" default="True">
    A boolean to enable or disable the tool. See [Disabling Tools](#disabling-tools) for more information
  </ParamField>

<ParamField body="exclude_args" type="list[str] | None">
    A list of argument names to exclude from the tool schema shown to the LLM. See [Excluding Arguments](#excluding-arguments) for more information
  </ParamField>

<ParamField body="annotations" type="ToolAnnotations | dict | None">
    An optional `ToolAnnotations` object or dictionary to add additional metadata about the tool.

    `<Expandable title="ToolAnnotations attributes">`
      `<ParamField body="title" type="str | None">`
        A human-readable title for the tool.
      `</ParamField>`

    `<ParamField body="readOnlyHint" type="bool | None">`
        If true, the tool does not modify its environment.
      `</ParamField>`

    `<ParamField body="destructiveHint" type="bool | None">`
        If true, the tool may perform destructive updates to its environment.
      `</ParamField>`

    `<ParamField body="idempotentHint" type="bool | None">`
        If true, calling the tool repeatedly with the same arguments will have no additional effect on the its environment.
      `</ParamField>`

    `<ParamField body="openWorldHint" type="bool | None">`
        If true, this tool may interact with an "open world" of external entities. If false, the tool's domain of interaction is closed.
      `</ParamField>`
    `</Expandable>`
  `</ParamField>`

<ParamField body="meta" type="dict[str, Any] | None">
    <VersionBadge version="2.11.0" />

    Optional meta information about the tool. This data is passed through to the MCP client as the`_meta` field of the client-side tool object and can be used for custom metadata, versioning, or other application-specific purposes.
  `</ParamField>`
`</Card>`

### Async and Synchronous Tools

FastMCP is an async-first framework that seamlessly supports both asynchronous (`async def`) and synchronous (`def`) functions as tools. Async tools are preferred for I/O-bound operations to keep your server responsive.

While synchronous tools work seamlessly in FastMCP, they can block the event loop during execution. For CPU-intensive or potentially blocking synchronous operations, consider alternative strategies. One approach is to use `anyio` (which FastMCP already uses internally) to wrap them as async functions, for example:

```python
import anyio
from fastmcp import FastMCP

mcp = FastMCP()

def cpu_intensive_task(data: str) -> str:
    # Some heavy computation that could block the event loop
    return processed_data

@mcp.tool
async def wrapped_cpu_task(data: str) -> str:
    """CPU-intensive task wrapped to prevent blocking."""
    return await anyio.to_thread.run_sync(cpu_intensive_task, data)
```

Alternative approaches include using `asyncio.get_event_loop().run_in_executor()` or other threading techniques to manage blocking operations without impacting server responsiveness. For example, here's a recipe for using the `asyncer` library (not included in FastMCP) to create a decorator that wraps synchronous functions, courtesy of [@hsheth2](https://github.com/jlowin/fastmcp/issues/864#issuecomment-3103678258):

<CodeGroup>
  ```python Decorator Recipe theme={null}
  import asyncer
  import functools
  from typing import Callable, ParamSpec, TypeVar, Awaitable

  _P = ParamSpec("_P")
  _R = TypeVar("_R")

  def make_async_background(fn: Callable[_P, _R]) -> Callable[_P, Awaitable[_R]]:
      @functools.wraps(fn)
      async def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R:
          return await asyncer.asyncify(fn)(*args, **kwargs)

    return wrapper

```

  ```python Using the Decorator {6} theme={null}
  from fastmcp import FastMCP

  mcp = FastMCP()

  @mcp.tool()
  @make_async_background
  def my_tool() -> None:
      time.sleep(5)
```

</CodeGroup>

### Type Annotations

Type annotations for parameters are essential for proper tool functionality. They:

1. Inform the LLM about the expected data types for each parameter
2. Enable FastMCP to validate input data from clients
3. Generate accurate JSON schemas for the MCP protocol

Use standard Python type annotations for parameters:

```python
@mcp.tool
def analyze_text(
    text: str,
    max_tokens: int = 100,
    language: str | None = None
) -> dict:
    """Analyze the provided text."""
    # Implementation...
```

FastMCP supports a wide range of type annotations, including all Pydantic types:

| Type Annotation   | Example                                         | Description                                                                                 |
| :---------------- | :---------------------------------------------- | :------------------------------------------------------------------------------------------ |
| Basic types       | `int`, `float`, `str`, `bool`           | Simple scalar values - see[Built-in Types](#built-in-types)                                    |
| Binary data       | `bytes`                                       | Binary content - see[Binary Data](#binary-data)                                                |
| Date and Time     | `datetime`, `date`, `timedelta`           | Date and time objects - see[Date and Time Types](#date-and-time-types)                         |
| Collection types  | `list[str]`, `dict[str, int]`, `set[int]` | Collections of items - see[Collection Types](#collection-types)                                |
| Optional types    | `float \| None`, `Optional[float]`           | Parameters that may be null/omitted - see[Union and Optional Types](#union-and-optional-types) |
| Union types       | `str \| int`, `Union[str, int]`              | Parameters accepting multiple types - see[Union and Optional Types](#union-and-optional-types) |
| Constrained types | `Literal["A", "B"]`, `Enum`                 | Parameters with specific allowed values - see[Constrained Types](#constrained-types)           |
| Paths             | `Path`                                        | File system paths - see[Paths](#paths)                                                         |
| UUIDs             | `UUID`                                        | Universally unique identifiers - see[UUIDs](#uuids)                                            |
| Pydantic models   | `UserData`                                    | Complex structured data - see[Pydantic Models](#pydantic-models)                               |

For additional type annotations not listed here, see the [Parameter Types](#parameter-types) section below for more detailed information and examples.

### Parameter Metadata

You can provide additional metadata about parameters in several ways:

#### Simple String Descriptions

<VersionBadge version="2.11.0" />

For basic parameter descriptions, you can use a convenient shorthand with `Annotated`:

```python
from typing import Annotated

@mcp.tool
def process_image(
    image_url: Annotated[str, "URL of the image to process"],
    resize: Annotated[bool, "Whether to resize the image"] = False,
    width: Annotated[int, "Target width in pixels"] = 800,
    format: Annotated[str, "Output image format"] = "jpeg"
) -> dict:
    """Process an image with optional resizing."""
    # Implementation...
```

This shorthand syntax is equivalent to using `Field(description=...)` but more concise for simple descriptions.

<Tip>
  This shorthand syntax is only applied to `Annotated` types with a single string description.
</Tip>

#### Advanced Metadata with Field

For validation constraints and advanced metadata, use Pydantic's `Field` class with `Annotated`:

```python
from typing import Annotated
from pydantic import Field

@mcp.tool
def process_image(
    image_url: Annotated[str, Field(description="URL of the image to process")],
    resize: Annotated[bool, Field(description="Whether to resize the image")] = False,
    width: Annotated[int, Field(description="Target width in pixels", ge=1, le=2000)] = 800,
    format: Annotated[
        Literal["jpeg", "png", "webp"], 
        Field(description="Output image format")
    ] = "jpeg"
) -> dict:
    """Process an image with optional resizing."""
    # Implementation...
```

You can also use the Field as a default value, though the Annotated approach is preferred:

```python
@mcp.tool
def search_database(
    query: str = Field(description="Search query string"),
    limit: int = Field(10, description="Maximum number of results", ge=1, le=100)
) -> list:
    """Search the database with the provided query."""
    # Implementation...
```

Field provides several validation and documentation features:

* `description`: Human-readable explanation of the parameter (shown to LLMs)
* `ge`/`gt`/`le`/`lt`: Greater/less than (or equal) constraints
* `min_length`/`max_length`: String or collection length constraints
* `pattern`: Regex pattern for string validation
* `default`: Default value if parameter is omitted

### Optional Arguments

FastMCP follows Python's standard function parameter conventions. Parameters without default values are required, while those with default values are optional.

```python
@mcp.tool
def search_products(
    query: str,                   # Required - no default value
    max_results: int = 10,        # Optional - has default value
    sort_by: str = "relevance",   # Optional - has default value
    category: str | None = None   # Optional - can be None
) -> list[dict]:
    """Search the product catalog."""
    # Implementation...
```

In this example, the LLM must provide a `query` parameter, while `max_results`, `sort_by`, and `category` will use their default values if not explicitly provided.

### Excluding Arguments

<VersionBadge version="2.6.0" />

You can exclude certain arguments from the tool schema shown to the LLM. This is useful for arguments that are injected at runtime (such as `state`, `user_id`, or credentials) and should not be exposed to the LLM or client. Only arguments with default values can be excluded; attempting to exclude a required argument will raise an error.

Example:

```python
@mcp.tool(
    name="get_user_details",
    exclude_args=["user_id"]
)
def get_user_details(user_id: str = None) -> str:
    # user_id will be injected by the server, not provided by the LLM
    ...
```

With this configuration, `user_id` will not appear in the tool's parameter schema, but can still be set by the server or framework at runtime.

For more complex tool transformations, see [Transforming Tools](/patterns/tool-transformation).

### Disabling Tools

<VersionBadge version="2.8.0" />

You can control the visibility and availability of tools by enabling or disabling them. This is useful for feature flagging, maintenance, or dynamically changing the toolset available to a client. Disabled tools will not appear in the list of available tools returned by `list_tools`, and attempting to call a disabled tool will result in an "Unknown tool" error, just as if the tool did not exist.

By default, all tools are enabled. You can disable a tool upon creation using the `enabled` parameter in the decorator:

```python
@mcp.tool(enabled=False)
def maintenance_tool():
    """This tool is currently under maintenance."""
    return "This tool is disabled."
```

You can also toggle a tool's state programmatically after it has been created:

```python
@mcp.tool
def dynamic_tool():
    return "I am a dynamic tool."

# Disable and re-enable the tool
dynamic_tool.disable()
dynamic_tool.enable()
```

### Return Values

FastMCP tools can return data in two complementary formats: **traditional content blocks** (like text and images) and **structured outputs** (machine-readable JSON). When you add return type annotations, FastMCP automatically generates **output schemas** to validate the structured data and enables clients to deserialize results back to Python objects.

Understanding how these three concepts work together:

* **Return Values**: What your Python function returns (determines both content blocks and structured data)
* **Structured Outputs**: JSON data sent alongside traditional content for machine processing
* **Output Schemas**: JSON Schema declarations that describe and validate the structured output format

The following sections explain each concept in detail.

#### Content Blocks

FastMCP automatically converts tool return values into appropriate MCP content blocks:

* **`str`**: Sent as `TextContent`
* **`bytes`**: Base64 encoded and sent as `BlobResourceContents` (within an `EmbeddedResource`)
* **`fastmcp.utilities.types.Image`**: Sent as `ImageContent`
* **`fastmcp.utilities.types.Audio`**: Sent as `AudioContent`
* **`fastmcp.utilities.types.File`**: Sent as base64-encoded `EmbeddedResource`
* **A list of any of the above**: Converts each item appropriately
* **`None`**: Results in an empty response

#### Structured Output

<VersionBadge version="2.10.0" />

The 6/18/2025 MCP spec update [introduced](https://modelcontextprotocol.io/specification/2025-06-18/server/tools#structured-content) structured content, which is a new way to return data from tools. Structured content is a JSON object that is sent alongside traditional content. FastMCP automatically creates structured outputs alongside traditional content when your tool returns data that has a JSON object representation. This provides machine-readable JSON data that clients can deserialize back to Python objects.

**Automatic Structured Content Rules:**

* **Object-like results** (`dict`, Pydantic models, dataclasses) → Always become structured content (even without output schema)
* **Non-object results** (`int`, `str`, `list`) → Only become structured content if there's an output schema to validate/serialize them
* **All results** → Always become traditional content blocks for backward compatibility

<Note>
  This automatic behavior enables clients to receive machine-readable data alongside human-readable content without requiring explicit output schemas for object-like returns.
</Note>

##### Object-like Results (Automatic Structured Content)

<CodeGroup>
  ```python Dict Return (No Schema Needed) theme={null}
  @mcp.tool
  def get_user_data(user_id: str) -> dict:
      """Get user data without type annotation."""
      return {"name": "Alice", "age": 30, "active": True}
  ```

```json
  "{\n  \"name\": \"Alice\",\n  \"age\": 30,\n  \"active\": true\n}"
```

```json
  {
    "name": "Alice", 
    "age": 30,
    "active": true
  }
```

</CodeGroup>

##### Non-object Results (Schema Required)

<CodeGroup>
  ```python Integer Return (No Schema) theme={null}
  @mcp.tool  
  def calculate_sum(a: int, b: int):
      """Calculate sum without return annotation."""
      return a + b  # Returns 8
  ```

```json
  "8"
```

```python
  @mcp.tool
  def calculate_sum(a: int, b: int) -> int:
      """Calculate sum with return annotation."""  
      return a + b  # Returns 8
```

```json
  "8"
```

```json
  {
    "result": 8
  }
```

</CodeGroup>

##### Complex Type Example

<CodeGroup>
  ```python Tool Definition theme={null}
  from dataclasses import dataclass
  from fastmcp import FastMCP

  mcp = FastMCP()

  @dataclass
  class Person:
      name: str
      age: int
      email: str

  @mcp.tool
  def get_user_profile(user_id: str) -> Person:
      """Get a user's profile information."""
      return Person(name="Alice", age=30, email="alice@example.com")

```

  ```json Generated Output Schema theme={null}
  {
    "properties": {
      "name": {"title": "Name", "type": "string"},
      "age": {"title": "Age", "type": "integer"}, 
      "email": {"title": "Email", "type": "string"}
    },
    "required": ["name", "age", "email"],
    "title": "Person",
    "type": "object"
  }
```

```json
  {
    "name": "Alice",
    "age": 30,
    "email": "alice@example.com"
  }
```

</CodeGroup>

#### Output Schemas

<VersionBadge version="2.10.0" />

The 6/18/2025 MCP spec update [introduced](https://modelcontextprotocol.io/specification/2025-06-18/server/tools#output-schema) output schemas, which are a new way to describe the expected output format of a tool. When an output schema is provided, the tool *must* return structured output that matches the schema.

When you add return type annotations to your functions, FastMCP automatically generates JSON schemas that describe the expected output format. These schemas help MCP clients understand and validate the structured data they receive.

##### Primitive Type Wrapping

For primitive return types (like `int`, `str`, `bool`), FastMCP automatically wraps the result under a `"result"` key to create valid structured output:

<CodeGroup>
  ```python Primitive Return Type theme={null}
  @mcp.tool
  def calculate_sum(a: int, b: int) -> int:
      """Add two numbers together."""
      return a + b
  ```

```json
  {
    "type": "object",
    "properties": {
      "result": {"type": "integer"}
    },
    "x-fastmcp-wrap-result": true
  }
```

```json
  {
    "result": 8
  }
```

</CodeGroup>

##### Manual Schema Control

You can override the automatically generated schema by providing a custom `output_schema`:

```python
@mcp.tool(output_schema={
    "type": "object", 
    "properties": {
        "data": {"type": "string"},
        "metadata": {"type": "object"}
    }
})
def custom_schema_tool() -> dict:
    """Tool with custom output schema."""
    return {"data": "Hello", "metadata": {"version": "1.0"}}
```

Schema generation works for most common types including basic types, collections, union types, Pydantic models, TypedDict structures, and dataclasses.

<Warning>
  **Important Constraints**:

* Output schemas must be object types (`"type": "object"`)
* If you provide an output schema, your tool **must** return structured output that matches it
* However, you can provide structured output without an output schema (using `ToolResult`)
  `</Warning>`

#### Full Control with ToolResult

For complete control over both traditional content and structured output, return a `ToolResult` object:

```python
from fastmcp.tools.tool import ToolResult

@mcp.tool
def advanced_tool() -> ToolResult:
    """Tool with full control over output."""
    return ToolResult(
        content=[TextContent(text="Human-readable summary")],
        structured_content={"data": "value", "count": 42}
    )
```

When returning `ToolResult`:

* You control exactly what content and structured data is sent
* Output schemas are optional - structured content can be provided without a schema
* Clients receive both traditional content blocks and structured data

<Note>
  If your return type annotation cannot be converted to a JSON schema (e.g., complex custom classes without Pydantic support), the output schema will be omitted but the tool will still function normally with traditional content.
</Note>

### Error Handling

<VersionBadge version="2.4.1" />

If your tool encounters an error, you can raise a standard Python exception (`ValueError`, `TypeError`, `FileNotFoundError`, custom exceptions, etc.) or a FastMCP `ToolError`.

By default, all exceptions (including their details) are logged and converted into an MCP error response to be sent back to the client LLM. This helps the LLM understand failures and react appropriately.

If you want to mask internal error details for security reasons, you can:

1. Use the `mask_error_details=True` parameter when creating your `FastMCP` instance:

```python
mcp = FastMCP(name="SecureServer", mask_error_details=True)
```

2. Or use `ToolError` to explicitly control what error information is sent to clients:

```python
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

@mcp.tool
def divide(a: float, b: float) -> float:
    """Divide a by b."""

    if b == 0:
        # Error messages from ToolError are always sent to clients,
        # regardless of mask_error_details setting
        raise ToolError("Division by zero is not allowed.")
  
    # If mask_error_details=True, this message would be masked
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise TypeError("Both arguments must be numbers.")
      
    return a / b
```

When `mask_error_details=True`, only error messages from `ToolError` will include details, other exceptions will be converted to a generic message.

### Annotations

<VersionBadge version="2.2.7" />

FastMCP allows you to add specialized metadata to your tools through annotations. These annotations communicate how tools behave to client applications without consuming token context in LLM prompts.

Annotations serve several purposes in client applications:

* Adding user-friendly titles for display purposes
* Indicating whether tools modify data or systems
* Describing the safety profile of tools (destructive vs. non-destructive)
* Signaling if tools interact with external systems

You can add annotations to a tool using the `annotations` parameter in the `@mcp.tool` decorator:

```python
@mcp.tool(
    annotations={
        "title": "Calculate Sum",
        "readOnlyHint": True,
        "openWorldHint": False
    }
)
def calculate_sum(a: float, b: float) -> float:
    """Add two numbers together."""
    return a + b
```

FastMCP supports these standard annotations:

| Annotation          | Type    | Default | Purpose                                                                     |
| :------------------ | :------ | :------ | :-------------------------------------------------------------------------- |
| `title`           | string  | -       | Display name for user interfaces                                            |
| `readOnlyHint`    | boolean | false   | Indicates if the tool only reads without making changes                     |
| `destructiveHint` | boolean | true    | For non-readonly tools, signals if changes are destructive                  |
| `idempotentHint`  | boolean | false   | Indicates if repeated identical calls have the same effect as a single call |
| `openWorldHint`   | boolean | true    | Specifies if the tool interacts with external systems                       |

Remember that annotations help make better user experiences but should be treated as advisory hints. They help client applications present appropriate UI elements and safety controls, but won't enforce security boundaries on their own. Always focus on making your annotations accurately represent what your tool actually does.

### Notifications

<VersionBadge version="2.9.1" />

FastMCP automatically sends `notifications/tools/list_changed` notifications to connected clients when tools are added, removed, enabled, or disabled. This allows clients to stay up-to-date with the current tool set without manually polling for changes.

```python
@mcp.tool
def example_tool() -> str:
    return "Hello!"

# These operations trigger notifications:
mcp.add_tool(example_tool)     # Sends tools/list_changed notification
example_tool.disable()         # Sends tools/list_changed notification  
example_tool.enable()          # Sends tools/list_changed notification
mcp.remove_tool("example_tool") # Sends tools/list_changed notification
```

Notifications are only sent when these operations occur within an active MCP request context (e.g., when called from within a tool or other MCP operation). Operations performed during server initialization do not trigger notifications.

Clients can handle these notifications using a [message handler](/clients/messages) to automatically refresh their tool lists or update their interfaces.

## MCP Context

Tools can access MCP features like logging, reading resources, or reporting progress through the `Context` object. To use it, add a parameter to your tool function with the type hint `Context`.

```python
from fastmcp import FastMCP, Context

mcp = FastMCP(name="ContextDemo")

@mcp.tool
async def process_data(data_uri: str, ctx: Context) -> dict:
    """Process data from a resource with progress reporting."""
    await ctx.info(f"Processing data from {data_uri}")
  
    # Read a resource
    resource = await ctx.read_resource(data_uri)
    data = resource[0].content if resource else ""
  
    # Report progress
    await ctx.report_progress(progress=50, total=100)
  
    # Example request to the client's LLM for help
    summary = await ctx.sample(f"Summarize this in 10 words: {data[:200]}")
  
    await ctx.report_progress(progress=100, total=100)
    return {
        "length": len(data),
        "summary": summary.text
    }
```

The Context object provides access to:

* **Logging**: `ctx.debug()`, `ctx.info()`, `ctx.warning()`, `ctx.error()`
* **Progress Reporting**: `ctx.report_progress(progress, total)`
* **Resource Access**: `ctx.read_resource(uri)`
* **LLM Sampling**: `ctx.sample(...)`
* **Request Information**: `ctx.request_id`, `ctx.client_id`

For full documentation on the Context object and all its capabilities, see the [Context documentation](/servers/context).

## Parameter Types

FastMCP supports a wide variety of parameter types to give you flexibility when designing your tools.

FastMCP generally supports all types that Pydantic supports as fields, including all Pydantic custom types. This means you can use any type that can be validated and parsed by Pydantic in your tool parameters.

FastMCP supports **type coercion** when possible. This means that if a client sends data that doesn't match the expected type, FastMCP will attempt to convert it to the appropriate type. For example, if a client sends a string for a parameter annotated as `int`, FastMCP will attempt to convert it to an integer. If the conversion is not possible, FastMCP will return a validation error.

### Built-in Types

The most common parameter types are Python's built-in scalar types:

```python
@mcp.tool
def process_values(
    name: str,             # Text data
    count: int,            # Integer numbers
    amount: float,         # Floating point numbers
    enabled: bool          # Boolean values (True/False)
):
    """Process various value types."""
    # Implementation...
```

These types provide clear expectations to the LLM about what values are acceptable and allow FastMCP to validate inputs properly. Even if a client provides a string like "42", it will be coerced to an integer for parameters annotated as `int`.

### Date and Time Types

FastMCP supports various date and time types from the `datetime` module:

```python
from datetime import datetime, date, timedelta

@mcp.tool
def process_date_time(
    event_date: date,             # ISO format date string or date object
    event_time: datetime,         # ISO format datetime string or datetime object
    duration: timedelta = timedelta(hours=1)  # Integer seconds or timedelta
) -> str:
    """Process date and time information."""
    # Types are automatically converted from strings
    assert isinstance(event_date, date)  
    assert isinstance(event_time, datetime)
    assert isinstance(duration, timedelta)
  
    return f"Event on {event_date} at {event_time} for {duration}"
```

* `datetime` - Accepts ISO format strings (e.g., "2023-04-15T14:30:00")
* `date` - Accepts ISO format date strings (e.g., "2023-04-15")
* `timedelta` - Accepts integer seconds or timedelta objects

### Collection Types

FastMCP supports all standard Python collection types:

```python
@mcp.tool
def analyze_data(
    values: list[float],           # List of numbers
    properties: dict[str, str],    # Dictionary with string keys and values
    unique_ids: set[int],          # Set of unique integers
    coordinates: tuple[float, float],  # Tuple with fixed structure
    mixed_data: dict[str, list[int]] # Nested collections
):
    """Analyze collections of data."""
    # Implementation...
```

All collection types can be used as parameter annotations:

* `list[T]` - Ordered sequence of items
* `dict[K, V]` - Key-value mapping
* `set[T]` - Unordered collection of unique items
* `tuple[T1, T2, ...]` - Fixed-length sequence with potentially different types

Collection types can be nested and combined to represent complex data structures. JSON strings that match the expected structure will be automatically parsed and converted to the appropriate Python collection type.

### Union and Optional Types

For parameters that can accept multiple types or may be omitted:

```python
@mcp.tool
def flexible_search(
    query: str | int,              # Can be either string or integer
    filters: dict[str, str] | None = None,  # Optional dictionary
    sort_field: str | None = None  # Optional string
):
    """Search with flexible parameter types."""
    # Implementation...
```

Modern Python syntax (`str | int`) is preferred over older `Union[str, int]` forms. Similarly, `str | None` is preferred over `Optional[str]`.

### Constrained Types

When a parameter must be one of a predefined set of values, you can use either Literal types or Enums:

#### Literals

Literals constrain parameters to a specific set of values:

```python
from typing import Literal

@mcp.tool
def sort_data(
    data: list[float],
    order: Literal["ascending", "descending"] = "ascending",
    algorithm: Literal["quicksort", "mergesort", "heapsort"] = "quicksort"
):
    """Sort data using specific options."""
    # Implementation...
```

Literal types:

* Specify exact allowable values directly in the type annotation
* Help LLMs understand exactly which values are acceptable
* Provide input validation (errors for invalid values)
* Create clear schemas for clients

#### Enums

For more structured sets of constrained values, use Python's Enum class:

```python
from enum import Enum

class Color(Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"

@mcp.tool
def process_image(
    image_path: str, 
    color_filter: Color = Color.RED
):
    """Process an image with a color filter."""
    # Implementation...
    # color_filter will be a Color enum member
```

When using Enum types:

* Clients should provide the enum's value (e.g., "red"), not the enum member name (e.g., "RED")
* FastMCP automatically coerces the string value into the appropriate Enum object
* Your function receives the actual Enum member (e.g., `Color.RED`)
* Validation errors are raised for values not in the enum

### Binary Data

There are two approaches to handling binary data in tool parameters:

#### Bytes

```python
@mcp.tool
def process_binary(data: bytes):
    """Process binary data directly.
  
    The client can send a binary string, which will be 
    converted directly to bytes.
    """
    # Implementation using binary data
    data_length = len(data)
    # ...
```

When you annotate a parameter as `bytes`, FastMCP will:

* Convert raw strings directly to bytes
* Validate that the input can be properly represented as bytes

FastMCP does not automatically decode base64-encoded strings for bytes parameters. If you need to accept base64-encoded data, you should handle the decoding manually as shown below.

#### Base64-encoded strings

```python
from typing import Annotated
from pydantic import Field

@mcp.tool
def process_image_data(
    image_data: Annotated[str, Field(description="Base64-encoded image data")]
):
    """Process an image from base64-encoded string.
  
    The client is expected to provide base64-encoded data as a string.
    You'll need to decode it manually.
    """
    # Manual base64 decoding
    import base64
    binary_data = base64.b64decode(image_data)
    # Process binary_data...
```

This approach is recommended when you expect to receive base64-encoded binary data from clients.

### Paths

The `Path` type from the `pathlib` module can be used for file system paths:

```python
from pathlib import Path

@mcp.tool
def process_file(path: Path) -> str:
    """Process a file at the given path."""
    assert isinstance(path, Path)  # Path is properly converted
    return f"Processing file at {path}"
```

When a client sends a string path, FastMCP automatically converts it to a `Path` object.

### UUIDs

The `UUID` type from the `uuid` module can be used for unique identifiers:

```python
import uuid

@mcp.tool
def process_item(
    item_id: uuid.UUID  # String UUID or UUID object
) -> str:
    """Process an item with the given UUID."""
    assert isinstance(item_id, uuid.UUID)  # Properly converted to UUID
    return f"Processing item {item_id}"
```

When a client sends a string UUID (e.g., "123e4567-e89b-12d3-a456-426614174000"), FastMCP automatically converts it to a `UUID` object.

### Pydantic Models

For complex, structured data with nested fields and validation, use Pydantic models:

```python
from pydantic import BaseModel, Field
from typing import Optional

class User(BaseModel):
    username: str
    email: str = Field(description="User's email address")
    age: int | None = None
    is_active: bool = True

@mcp.tool
def create_user(user: User):
    """Create a new user in the system."""
    # The input is automatically validated against the User model
    # Even if provided as a JSON string or dict
    # Implementation...
```

Using Pydantic models provides:

* Clear, self-documenting structure for complex inputs
* Built-in data validation
* Automatic generation of detailed JSON schemas for the LLM
* Automatic conversion from dict/JSON input

Clients can provide data for Pydantic model parameters as either:

* A JSON object (string)
* A dictionary with the appropriate structure
* Nested parameters in the appropriate format

### Pydantic Fields

FastMCP supports robust parameter validation through Pydantic's `Field` class. This is especially useful to ensure that input values meet specific requirements beyond just their type.

Note that fields can be used *outside* Pydantic models to provide metadata and validation constraints. The preferred approach is using `Annotated` with `Field`:

```python
from typing import Annotated
from pydantic import Field

@mcp.tool
def analyze_metrics(
    # Numbers with range constraints
    count: Annotated[int, Field(ge=0, le=100)],         # 0 <= count <= 100
    ratio: Annotated[float, Field(gt=0, lt=1.0)],       # 0 < ratio < 1.0
  
    # String with pattern and length constraints
    user_id: Annotated[str, Field(
        pattern=r"^[A-Z]{2}\d{4}$",                     # Must match regex pattern
        description="User ID in format XX0000"
    )],
  
    # String with length constraints
    comment: Annotated[str, Field(min_length=3, max_length=500)] = "",
  
    # Numeric constraints
    factor: Annotated[int, Field(multiple_of=5)] = 10,  # Must be multiple of 5
):
    """Analyze metrics with validated parameters."""
    # Implementation...
```

You can also use `Field` as a default value, though the `Annotated` approach is preferred:

```python
@mcp.tool
def validate_data(
    # Value constraints
    age: int = Field(ge=0, lt=120),                     # 0 <= age < 120
  
    # String constraints
    email: str = Field(pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$"),  # Email pattern
  
    # Collection constraints
    tags: list[str] = Field(min_length=1, max_length=10)  # 1-10 tags
):
    """Process data with field validations."""
    # Implementation...
```

Common validation options include:

| Validation                     | Type               | Description                                    |
| :----------------------------- | :----------------- | :--------------------------------------------- |
| `ge`, `gt`                 | Number             | Greater than (or equal) constraint             |
| `le`, `lt`                 | Number             | Less than (or equal) constraint                |
| `multiple_of`                | Number             | Value must be a multiple of this number        |
| `min_length`, `max_length` | String, List, etc. | Length constraints                             |
| `pattern`                    | String             | Regular expression pattern constraint          |
| `description`                | Any                | Human-readable description (appears in schema) |

When a client sends invalid data, FastMCP will return a validation error explaining why the parameter failed validation.

## Server Behavior

### Duplicate Tools

<VersionBadge version="2.1.0" />

You can control how the FastMCP server behaves if you try to register multiple tools with the same name. This is configured using the `on_duplicate_tools` argument when creating the `FastMCP` instance.

```python
from fastmcp import FastMCP

mcp = FastMCP(
    name="StrictServer",
    # Configure behavior for duplicate tool names
    on_duplicate_tools="error"
)

@mcp.tool
def my_tool(): return "Version 1"

# This will now raise a ValueError because 'my_tool' already exists
# and on_duplicate_tools is set to "error".
# @mcp.tool
# def my_tool(): return "Version 2"
```

The duplicate behavior options are:

* `"warn"` (default): Logs a warning and the new tool replaces the old one.
* `"error"`: Raises a `ValueError`, preventing the duplicate registration.
* `"replace"`: Silently replaces the existing tool with the new one.
* `"ignore"`: Keeps the original tool and ignores the new registration attempt.

### Removing Tools

<VersionBadge version="2.3.4" />

You can dynamically remove tools from a server using the `remove_tool` method:

```python
from fastmcp import FastMCP

mcp = FastMCP(name="DynamicToolServer")

@mcp.tool
def calculate_sum(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b

mcp.remove_tool("calculate_sum")
```
