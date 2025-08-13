import importlib
import importlib.util
import json
import pkgutil
import sys
from pathlib import Path
from typing import Iterable

import yaml
from fastmcp import FastMCP
from .logging import get_logger

log = get_logger("loaders")


def _iter_modules(dir_path: Path, package_prefix: str) -> Iterable[str]:
    if not dir_path.exists():
        return []
    return (
        f"{package_prefix}.{name}"
        for _, name, _ in pkgutil.iter_modules([str(dir_path)])
    )


def _load_module_from_path(module_name: str, file_path: Path) -> None:
    """Dynamically load a module from a file path with a synthetic module name."""
    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    else:  # pragma: no cover - defensive fallback
        importlib.import_module(module_name)


def load_tools(mcp: FastMCP, tools_dir: Path) -> int:
    added = 0
    if not tools_dir.exists():
        return 0
    for py_file in tools_dir.glob("*.py"):
        if py_file.name == "__init__.py":
            continue
        module_name = f"tools__{py_file.stem}"
        try:
            _load_module_from_path(module_name, py_file)
            log.info(f"Loaded tool module: {py_file.name}")
            added += 1
        except Exception:
            log.exception(f"Failed to load tool: {py_file}")
    return added


def load_resources(mcp: FastMCP, resources_dir: Path) -> int:
    added = 0
    if not resources_dir.exists():
        return 0
    for py_file in resources_dir.glob("*.py"):
        if py_file.name == "__init__.py":
            continue
        module_name = f"resources__{py_file.stem}"
        try:
            _load_module_from_path(module_name, py_file)
            log.info(f"Loaded resource module: {py_file.name}")
            added += 1
        except Exception:
            log.exception(f"Failed to load resource: {py_file}")
    return added


essential_prompt_keys = {"name", "prompt"}


def _normalize_yaml_prompts(data):
    if not data:
        return []
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict)]
    return []


def _inject_output_schema(raw_text: str, schema_path: Path | None) -> str:
    """If raw_text contains {output_schema} and schema_path exists, replace with minified JSON.
    Keeps everything else (e.g., {document}, {text}) untouched for runtime replacement.
    """
    if "{output_schema}" not in raw_text:
        return raw_text
    if not schema_path or not schema_path.exists():
        return raw_text
    try:
        loaded = json.loads(schema_path.read_text())
        minified = json.dumps(loaded, separators=(",", ":"))
        return raw_text.replace("{output_schema}", minified)
    except Exception:
        log.exception(f"Failed to inject schema from {schema_path}")
        return raw_text


def load_single_prompt_with_schema(yaml_path: Path) -> dict:
    """Load one YAML prompt file and inject same-stem .json into {output_schema} if present."""
    data = yaml.safe_load(yaml_path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"Invalid prompt format in {yaml_path}")
    if not essential_prompt_keys.issubset(data):
        raise ValueError(f"Prompt missing required keys in {yaml_path}: {essential_prompt_keys}")

    text = str(data.get("prompt", ""))
    schema_path = yaml_path.with_suffix(".json")
    text = _inject_output_schema(text, schema_path if schema_path.exists() else None)

    out = dict(data)
    out["prompt"] = text
    return out


def load_prompts(mcp: FastMCP, prompts_dir: Path) -> int:
    added = 0

    if not prompts_dir.exists():
        return 0

    for f in prompts_dir.glob("*.y*ml"):
        try:
            doc = yaml.safe_load(f.read_text())
            prompts = _normalize_yaml_prompts(doc)
            for p in prompts:
                if not essential_prompt_keys.issubset(p):
                    log.warning(f"Skipping {f}: missing required keys (have {set(p.keys())})")
                    continue
                text = str(p.get("prompt", ""))

                schema_path = f.with_suffix(".json")
                had_placeholder = "{output_schema}" in text
                text = _inject_output_schema(text, schema_path)

                if "{output_schema}" in text:
                    if had_placeholder and not schema_path.exists():
                        log.warning(f"{f.name} uses {{output_schema}} but missing schema file: {schema_path.name}")
                    else:
                        log.warning(f"{f.name} still contains '{{output_schema}}' — placeholder may be misspelled or nested.")

                # Register as a function prompt to match FastMCP v2 API
                name = p["name"]
                description = p.get("description", "")
                tags = set(p.get("tags", []) or [])

                def _make_prompt_fn(render_text: str):
                    # Create a zero-arg function; FastMCP FunctionPrompt forbids **kwargs-only
                    def _fn():
                        return render_text
                    return _fn

                fn = _make_prompt_fn(text)
                try:
                    # Preferred API per FastMCP 2.x: build a FunctionPrompt and add via add_prompt
                    from fastmcp.prompts import prompt as prompt_mod

                    prompt_obj = prompt_mod.FunctionPrompt.from_function(fn, name=name, description=description)
                    if tags:
                        try:
                            prompt_obj.tags = set(tags)
                        except Exception:
                            pass
                    mcp.add_prompt(prompt_obj)
                    log.info(f"Registered prompt: {name} (from {f.name})")
                    added += 1
                except Exception:
                    log.exception(f"Failed to register prompt: {name}")
        except Exception:
            log.exception(f"Failed to load prompts from {f}")

    return added


# ---------------------------
# Hot‑reload (dev only)
# ---------------------------
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except Exception:  # pragma: no cover
    Observer = None
    FileSystemEventHandler = object  # type: ignore


class _ReloadHandler(FileSystemEventHandler):  # type: ignore[misc]
    def __init__(self, mcp: FastMCP, base: Path) -> None:
        self.mcp = mcp
        self.base = base

    def on_any_event(self, event):  # noqa: N802
        try:
            importlib.invalidate_caches()
            tools_dir = self.base / "tools"
            resources_dir = self.base / "resources"
            prompts_dir = self.base.parent / "prompts"

            for module_name in list(_iter_modules(tools_dir, "tools")):
                if module_name in sys.modules:
                    importlib.reload(sys.modules[module_name])
                else:
                    importlib.import_module(module_name)

            for module_name in list(_iter_modules(resources_dir, "resources")):
                if module_name in sys.modules:
                    importlib.reload(sys.modules[module_name])
                else:
                    importlib.import_module(module_name)

            load_prompts(self.mcp, prompts_dir)
            log.info("Hot‑reload applied")
        except Exception:
            log.exception("Hot‑reload failed")


def start_hot_reload(mcp: FastMCP, base_dir: Path):
    if Observer is None:
        log.warning("watchdog not installed; hot‑reload disabled")
        return None

    handler = _ReloadHandler(mcp, base_dir)
    obs = Observer()

    tools_dir = base_dir / "tools"
    resources_dir = base_dir / "resources"
    prompts_dir = base_dir.parent / "prompts"

    for d in (tools_dir, resources_dir, prompts_dir):
        if d.exists():
            obs.schedule(handler, str(d), recursive=False)

    obs.daemon = True
    obs.start()
    log.info(f"Hot‑reload watching: {tools_dir}, {resources_dir}, {prompts_dir}")
    return obs


def load_all(mcp: FastMCP, src_base: Path) -> dict:
    counts = {
        "tools": load_tools(mcp, src_base / "tools"),
        "resources": load_resources(mcp, src_base / "resources"),
        "prompts": load_prompts(mcp, src_base.parent / "prompts"),
    }
    log.info(f"Loaded: {counts}")
    return counts
