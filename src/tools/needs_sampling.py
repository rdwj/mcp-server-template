from fastmcp import Context
from core.app import mcp

@mcp.tool
async def write_release_notes(diff: str, ctx: Context) -> str:
    """Use client's LLM to turn a git diff into release notes (sampling)."""
    system = "You are a release notes generator. Keep it concise."
    # FastMCP's sample method can accept a simple string or list of strings for messages
    prompt = f"Create release notes from this diff:\n{diff}"
    result = await ctx.sample(
        messages=prompt,  # Simple string format
        temperature=0.3, 
        max_tokens=400, 
        system_prompt=system
    )
    return str(result)
