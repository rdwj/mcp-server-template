"""Logging middleware for tracking tool invocations.

This middleware logs all tool calls with execution time and status.
"""

from typing import Any, Callable
import time
from fastmcp import Context
from core.app import mcp
from core.logging import get_logger

log = get_logger("middleware.logging")


@mcp.middleware()
async def logging_middleware(
    ctx: Context,
    next_handler: Callable,
    *args: Any,
    **kwargs: Any
) -> Any:
    """Log tool invocations with timing information.

    This middleware captures:
    - Tool name
    - Execution start time
    - Execution duration
    - Success/failure status

    Args:
        ctx: FastMCP context with request information
        next_handler: Next handler in the middleware chain
        *args: Positional arguments passed to the tool
        **kwargs: Keyword arguments passed to the tool

    Returns:
        Result from the tool execution

    Raises:
        Any exception raised by the tool
    """
    # Extract tool name from context
    tool_name = getattr(ctx.request, "tool_name", "unknown") if hasattr(ctx, "request") else "unknown"

    # Log request start
    start_time = time.time()
    log.info(f"Tool invoked: {tool_name}")
    log.debug(f"Tool args: {args}, kwargs: {kwargs}")

    try:
        # Execute the tool
        result = await next_handler(*args, **kwargs)

        # Log successful completion
        duration = time.time() - start_time
        log.info(f"Tool completed: {tool_name} (duration: {duration:.3f}s)")

        return result
    except Exception as e:
        # Log failure
        duration = time.time() - start_time
        log.error(f"Tool failed: {tool_name} (duration: {duration:.3f}s) - {type(e).__name__}: {e}")
        raise
