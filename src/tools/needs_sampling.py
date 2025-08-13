from fastmcp import Context
from core.app import mcp

@mcp.tool
async def write_release_notes(diff: str, ctx: Context) -> str:
    """Use client's LLM to turn a git diff into release notes (sampling)."""
    system = "You are a release notes generator. Keep it concise."
    msg = {"role": "user", "content": f"Create release notes from this diff:\n{diff}"}
    return await ctx.sample(messages=[msg], temperature=0.3, maxTokens=400, systemPrompt=system)
