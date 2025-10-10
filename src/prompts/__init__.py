"""
Prompts module for FastMCP server.

This module exports all available prompts using Python decorators for type safety
and better IDE support. All prompt functions are automatically registered with
FastMCP through the @mcp.prompt() decorator.
"""

# Import all prompt modules to trigger decorator registration
from . import analysis  # noqa: F401
from . import documentation  # noqa: F401
from . import general  # noqa: F401

__all__ = ["analysis", "documentation", "general"]
