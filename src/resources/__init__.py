"""
Resources package for the MCP server.

All resource modules in this directory (and subdirectories) are automatically
discovered and imported. FastMCP decorators (@mcp.resource) register resources
when modules are imported.

To add a new resource:
1. Create a new .py file in this directory or any subdirectory
   Example: resources/country-profiles/japan.py
2. Define your resource function with @mcp.resource() decorator
3. That's it! No need to update this __init__.py file

To remove a resource:
1. Simply delete the .py file
2. No cleanup needed in __init__.py

Subdirectories are supported and encouraged for organizing related resources.
"""

import importlib
from pathlib import Path

# Auto-discover and import all resource modules recursively
_current_dir = Path(__file__).parent
_discovered_modules = []


def _discover_modules(base_path: Path, package_prefix: str = __name__):
    """Recursively discover and import Python modules."""
    for py_file in base_path.rglob("*.py"):
        if py_file.name.startswith("_"):  # Skip __init__ and private modules
            continue

        # Calculate relative path and build module name
        rel_path = py_file.relative_to(base_path)
        parts = list(rel_path.parts[:-1]) + [rel_path.stem]
        module_suffix = ".".join(parts)

        module_name = (
            f"{package_prefix}.{module_suffix}" if module_suffix else package_prefix
        )

        try:
            importlib.import_module(module_name)
            _discovered_modules.append(module_suffix)
        except Exception as e:
            # Log import errors but don't fail the whole package
            print(f"Warning: Failed to import {module_name}: {e}")


# Perform discovery
_discover_modules(_current_dir)

# Expose discovered modules for introspection
__all__ = _discovered_modules
