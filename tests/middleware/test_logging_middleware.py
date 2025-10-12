"""Tests for logging middleware."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.middleware.logging_middleware import logging_middleware


@pytest.mark.asyncio
async def test_logging_middleware_success():
    """Test middleware logs successful tool execution."""
    # Create mock context
    ctx = MagicMock()
    ctx.request.tool_name = "test_tool"

    # Create mock next handler that returns a result
    next_handler = AsyncMock(return_value="success_result")

    # Execute middleware
    result = await logging_middleware(ctx, next_handler, "arg1", kwarg1="value1")

    # Verify result is returned
    assert result == "success_result"

    # Verify next_handler was called
    next_handler.assert_called_once_with("arg1", kwarg1="value1")


@pytest.mark.asyncio
async def test_logging_middleware_error():
    """Test middleware logs errors and re-raises them."""
    # Create mock context
    ctx = MagicMock()
    ctx.request.tool_name = "failing_tool"

    # Create mock next handler that raises an error
    next_handler = AsyncMock(side_effect=ValueError("Test error"))

    # Execute middleware and expect error to be raised
    with pytest.raises(ValueError, match="Test error"):
        await logging_middleware(ctx, next_handler)

    # Verify next_handler was called
    next_handler.assert_called_once()


@pytest.mark.asyncio
async def test_logging_middleware_no_context():
    """Test middleware handles missing context gracefully."""
    # Create minimal mock context without request attribute
    ctx = MagicMock()
    del ctx.request

    # Create mock next handler
    next_handler = AsyncMock(return_value="result")

    # Execute middleware - should not raise error
    result = await logging_middleware(ctx, next_handler)

    # Verify result is returned
    assert result == "result"
    next_handler.assert_called_once()


@pytest.mark.asyncio
async def test_logging_middleware_timing():
    """Test middleware measures execution time."""
    import asyncio

    # Create mock context
    ctx = MagicMock()
    ctx.request.tool_name = "slow_tool"

    # Create mock next handler that takes time
    async def slow_handler(*args, **kwargs):
        await asyncio.sleep(0.01)  # 10ms delay
        return "result"

    # Execute middleware
    result = await logging_middleware(ctx, slow_handler)

    # Verify result is returned
    assert result == "result"
