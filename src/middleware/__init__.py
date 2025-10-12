"""Middleware components for the MCP server.

Middleware functions wrap tool executions to add cross-cutting concerns
like logging, authentication, rate limiting, etc.

All middleware should be decorated with @mcp.middleware() and follow
the standard middleware signature:

    async def middleware_name(ctx: Context, next_handler: Callable, *args, **kwargs):
        # Pre-execution logic
        result = await next_handler(*args, **kwargs)
        # Post-execution logic
        return result
"""
