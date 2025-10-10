# LLM Sampling

> Request the client's LLM to generate text based on provided messages through the MCP context.

export const VersionBadge = ({version}) => {
  return `<code className="version-badge-container">`
            `<p className="version-badge">`
                `<span className="version-badge-label">`New in version: 
                `<code className="version-badge-version">`{version}`</code>`
            `</p>`
        `</code>`;
};

<VersionBadge version="2.0.0" />

LLM sampling allows MCP tools to request the client's LLM to generate text based on provided messages. This is useful when tools need to leverage the LLM's capabilities to process data, generate responses, or perform text-based analysis.

## Why Use LLM Sampling?

LLM sampling enables tools to:

* **Leverage AI capabilities**: Use the client's LLM for text generation and analysis
* **Offload complex reasoning**: Let the LLM handle tasks requiring natural language understanding
* **Generate dynamic content**: Create responses, summaries, or transformations based on data
* **Maintain context**: Use the same LLM instance that the user is already interacting with

### Basic Usage

Use `ctx.sample()` to request text generation from the client's LLM:

```python
from fastmcp import FastMCP, Context

mcp = FastMCP("SamplingDemo")

@mcp.tool
async def analyze_sentiment(text: str, ctx: Context) -> dict:
    """Analyze the sentiment of text using the client's LLM."""
    prompt = f"""Analyze the sentiment of the following text as positive, negative, or neutral. 
    Just output a single word - 'positive', 'negative', or 'neutral'.
  
    Text to analyze: {text}"""
  
    # Request LLM analysis
    response = await ctx.sample(prompt)
  
    # Process the LLM's response
    sentiment = response.text.strip().lower()
  
    # Map to standard sentiment values
    if "positive" in sentiment:
        sentiment = "positive"
    elif "negative" in sentiment:
        sentiment = "negative"
    else:
        sentiment = "neutral"
  
    return {"text": text, "sentiment": sentiment}
```

## Method Signature

<Card icon="code" title="Context Sampling Method">
  <ResponseField name="ctx.sample" type="async method">
    Request text generation from the client's LLM

    `<Expandable title="Parameters">`
      `<ResponseField name="messages" type="str | list[str | SamplingMessage]">`
        A string or list of strings/message objects to send to the LLM
      `</ResponseField>`

    `<ResponseField name="system_prompt" type="str | None" default="None">`
        Optional system prompt to guide the LLM's behavior
      `</ResponseField>`

    `<ResponseField name="temperature" type="float | None" default="None">`
        Optional sampling temperature (controls randomness, typically 0.0-1.0)
      `</ResponseField>`

    `<ResponseField name="max_tokens" type="int | None" default="512">`
        Optional maximum number of tokens to generate
      `</ResponseField>`

    `<ResponseField name="model_preferences" type="ModelPreferences | str | list[str] | None" default="None">`
        Optional model selection preferences (e.g., model hint string, list of hints, or ModelPreferences object)
      `</ResponseField>`
    `</Expandable>`

    `<Expandable title="Response">`
      `<ResponseField name="response" type="TextContent | ImageContent">`
        The LLM's response content (typically TextContent with a .text attribute)
      `</ResponseField>`
    `</Expandable>`
  `</ResponseField>`
`</Card>`

## Simple Text Generation

### Basic Prompting

Generate text with simple string prompts:

```python
@mcp.tool
async def generate_summary(content: str, ctx: Context) -> str:
    """Generate a summary of the provided content."""
    prompt = f"Please provide a concise summary of the following content:\n\n{content}"
  
    response = await ctx.sample(prompt)
    return response.text
```

### System Prompt

Use system prompts to guide the LLM's behavior:

````python
@mcp.tool
async def generate_code_example(concept: str, ctx: Context) -> str:
    """Generate a Python code example for a given concept."""
    response = await ctx.sample(
        messages=f"Write a simple Python code example demonstrating '{concept}'.",
        system_prompt="You are an expert Python programmer. Provide concise, working code examples without explanations.",
        temperature=0.7,
        max_tokens=300
    )
  
    code_example = response.text
    return f"```python\n{code_example}\n```"
````

### Model Preferences

Specify model preferences for different use cases:

```python
@mcp.tool
async def creative_writing(topic: str, ctx: Context) -> str:
    """Generate creative content using a specific model."""
    response = await ctx.sample(
        messages=f"Write a creative short story about {topic}",
        model_preferences="claude-3-sonnet",  # Prefer a specific model
        include_context="thisServer",  # Use the server's context
        temperature=0.9,  # High creativity
        max_tokens=1000
    )
  
    return response.text

@mcp.tool
async def technical_analysis(data: str, ctx: Context) -> str:
    """Perform technical analysis with a reasoning-focused model."""
    response = await ctx.sample(
        messages=f"Analyze this technical data and provide insights: {data}",
        model_preferences=["claude-3-opus", "gpt-4"],  # Prefer reasoning models
        temperature=0.2,  # Low randomness for consistency
        max_tokens=800
    )
  
    return response.text
```

### Complex Message Structures

Use structured messages for more complex interactions:

```python
from fastmcp.client.sampling import SamplingMessage

@mcp.tool
async def multi_turn_analysis(user_query: str, context_data: str, ctx: Context) -> str:
    """Perform analysis using multi-turn conversation structure."""
    messages = [
        SamplingMessage(role="user", content=f"I have this data: {context_data}"),
        SamplingMessage(role="assistant", content="I can see your data. What would you like me to analyze?"),
        SamplingMessage(role="user", content=user_query)
    ]
  
    response = await ctx.sample(
        messages=messages,
        system_prompt="You are a data analyst. Provide detailed insights based on the conversation context.",
        temperature=0.3
    )
  
    return response.text
```

## Client Requirements

LLM sampling requires client support:

* Clients must implement sampling handlers to process requests
* If the client doesn't support sampling, calls to `ctx.sample()` will fail
* See [Client Sampling](/clients/sampling) for details on implementing client-side sampling handlers
