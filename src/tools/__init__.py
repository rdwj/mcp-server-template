"""
Tools package for the MCP server.

All tool modules in this directory are automatically discovered and imported.
FastMCP decorators (@mcp.tool) register tools when modules are imported.

To add a new tool:
1. Create a new .py file in this directory
2. Define your tool function with @mcp.tool() decorator
3. That's it! No need to update this __init__.py file

To remove a tool:
1. Simply delete the .py file
2. No cleanup needed in __init__.py
"""

import importlib
import pkgutil
from pathlib import Path

# Auto-discover and import all tool modules
_current_dir = Path(__file__).parent
_discovered_modules = []

for _, module_name, _ in pkgutil.iter_modules([str(_current_dir)]):
    if not module_name.startswith("_"):  # Skip __init__ and private modules
        importlib.import_module(f".{module_name}", package=__name__)
        _discovered_modules.append(module_name)

# Expose discovered modules for introspection
__all__ = _discovered_modules
