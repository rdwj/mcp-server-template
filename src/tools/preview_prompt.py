import argparse
import json
from pathlib import Path

from core.loaders import load_single_prompt_with_schema


def preview_prompt(
    prompt_name: str, strict: bool = False, _prompts_dir: Path = None, **kwargs
):
    # prompts/ sits at project root alongside src/
    prompts_dir = _prompts_dir or Path(__file__).resolve().parents[1].parent / "prompts"
    yaml_file = prompts_dir / f"{prompt_name}.yaml"
    if not yaml_file.exists():
        raise FileNotFoundError(f"Prompt '{prompt_name}' not found in {prompts_dir}")

    # Read raw to detect placeholders before schema injection
    raw_text = yaml_file.read_text(encoding="utf-8")
    had_output_schema_placeholder = "{output_schema}" in raw_text
    schema_file = yaml_file.with_suffix(".json")
    has_schema_file = schema_file.exists()

    prompt_data = load_single_prompt_with_schema(yaml_file)
    text = prompt_data["prompt"]

    # Strict mode: error if placeholder existed but schema file missing
    if strict and had_output_schema_placeholder and not has_schema_file:
        raise RuntimeError(
            f"{yaml_file.name} uses {{output_schema}} but missing schema file: {schema_file.name}"
        )

    # Non-strict: warn if placeholder still present after injection
    if "{output_schema}" in text:
        print(
            f"[WARN] {yaml_file.name} still contains '{{output_schema}}' — no schema injected or placeholder misspelled."
        )

    # Replace any provided {placeholders}
    for key, value in kwargs.items():
        text = text.replace(f"{{{key}}}", value)

    print("\n--- Prompt Preview ---\n")
    print(text)
    print("\n--- Metadata ---\n")
    print(json.dumps({k: v for k, v in prompt_data.items() if k != "prompt"}, indent=2))


def _parse_kv_list(kv_list):
    out = {}
    for item in kv_list:
        if "=" not in item:
            raise ValueError(f"Invalid var format: {item}, expected key=value")
        k, v = item.split("=", 1)
        out[k] = v
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Preview a prompt with placeholders filled."
    )
    parser.add_argument(
        "prompt_name", help="Name of the prompt YAML file without extension"
    )
    parser.add_argument(
        "--vars",
        nargs="*",
        default=[],
        help="Placeholder replacements in key=value format",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if {output_schema} is used but schema file is missing",
    )
    args = parser.parse_args()

    replacements = _parse_kv_list(args.vars)
    preview_prompt(args.prompt_name, strict=args.strict, **replacements)
