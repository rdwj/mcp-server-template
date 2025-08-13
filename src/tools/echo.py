from core.app import mcp
from fastmcp import Context

@mcp.tool
async def echo(message: str, ctx: Context) -> str:
    """Echo back the provided message and log it."""
    await ctx.info(f"echo called with: {message}")
    return message
