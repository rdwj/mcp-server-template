from fastmcp import Context
from core.app import mcp

@mcp.tool
async def delete_all(ctx: Context) -> str:
    """Example tool demonstrating context logging."""
    # Note: FastMCP doesn't support elicit() for user confirmation
    # This is a simplified example that just logs a warning
    await ctx.warning("delete_all called - this is a demo tool")
    await ctx.info("In a real implementation, you would add confirmation logic here")
    return "Operation cancelled (demo mode - no actual deletion)"