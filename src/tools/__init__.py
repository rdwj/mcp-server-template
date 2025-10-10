"""
Tools package for the MCP server.

This package contains all tool implementations organized by functionality:
- echo.py: Simple echo example
- needs_sampling.py: Tools that use LLM sampling
- needs_elicitation.py: Tools that elicit user input
- advanced_examples.py: Comprehensive examples of FastMCP best practices
"""

# Import all tools to make them available when the package is imported
from .echo import echo
from .needs_sampling import write_release_notes
from .needs_elicitation import delete_all, get_weather
from .advanced_examples import (
    process_data,
    validate_input,
    analyze_text,
    configure_system,
    calculate_statistics,
    format_text,
)

__all__ = [
    # Basic tools
    "echo",
    "write_release_notes",
    "delete_all",
    "get_weather",
    # Advanced examples
    "process_data",
    "validate_input",
    "analyze_text",
    "configure_system",
    "calculate_statistics",
    "format_text",
]
