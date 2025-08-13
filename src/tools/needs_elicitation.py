from dataclasses import dataclass
from fastmcp import Context
from core.app import mcp

@dataclass
class Confirm:
    ok: bool

@mcp.tool
async def delete_all(ctx: Context) -> str:
    """Dangerous example: asks user to confirm via elicitation before proceeding."""
    ans = await ctx.elicit(Confirm, prompt="DELETE ALL DATA in workspace?")
    return "deleted" if ans.ok else "cancelled"
