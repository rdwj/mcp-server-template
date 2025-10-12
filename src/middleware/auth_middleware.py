"""Authentication middleware example (commented pattern).

This file provides a pattern for implementing authentication middleware.
Uncomment and customize based on your authentication requirements.
"""

from typing import Any, Callable
from fastmcp import Context
from fastmcp.exceptions import ToolError
from core.app import mcp
from core.logging import get_logger

log = get_logger("middleware.auth")


# Uncomment to enable authentication middleware
# @mcp.middleware()
async def auth_middleware(
    ctx: Context,
    next_handler: Callable,
    *args: Any,
    **kwargs: Any
) -> Any:
    """Verify authentication before tool execution.

    This is a commented example showing how to implement authentication
    middleware. Uncomment the @mcp.middleware() decorator above to activate.

    Example authentication checks:
    - Verify JWT tokens from request headers
    - Check user permissions/scopes
    - Validate API keys
    - Rate limiting per user

    Args:
        ctx: FastMCP context with request information
        next_handler: Next handler in the middleware chain
        *args: Positional arguments passed to the tool
        **kwargs: Keyword arguments passed to the tool

    Returns:
        Result from the tool execution

    Raises:
        ToolError: If authentication fails
    """
    # Example: Check for authorization header
    # auth_header = getattr(ctx.request, "headers", {}).get("Authorization")
    # if not auth_header:
    #     raise ToolError("Authentication required: Missing Authorization header")

    # Example: Verify JWT token
    # try:
    #     from core.auth import verify_jwt
    #     token = auth_header.replace("Bearer ", "")
    #     claims = verify_jwt(token)
    #     ctx.user = claims  # Attach user info to context
    # except Exception as e:
    #     raise ToolError(f"Authentication failed: {e}")

    # Example: Check required scopes
    # tool_name = getattr(ctx.request, "tool_name", "unknown")
    # required_scopes = get_required_scopes(tool_name)
    # user_scopes = claims.get("scopes", [])
    # if not all(scope in user_scopes for scope in required_scopes):
    #     raise ToolError(f"Insufficient permissions for {tool_name}")

    log.debug("Auth middleware (commented) - passing through")

    # Execute the tool
    return await next_handler(*args, **kwargs)


# Example helper function for scope checking
def get_required_scopes(tool_name: str) -> list[str]:
    """Get required scopes for a tool.

    This is an example function showing how you might map tools
    to required authentication scopes.

    Args:
        tool_name: Name of the tool being invoked

    Returns:
        List of required scope strings
    """
    # Example scope mapping
    scope_map = {
        "fetch_user": ["read:users"],
        "update_user": ["write:users"],
        "delete_user": ["delete:users", "admin"],
        "admin_action": ["admin"],
    }
    return scope_map.get(tool_name, [])
