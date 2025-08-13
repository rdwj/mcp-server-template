import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.app import mcp
from core.loaders import load_prompts


def test_yaml_prompt_list_and_single(tmp_path: Path):
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()

    # Single mapping + schema injection
    (prompts_dir / "single.yaml").write_text(
        "name: a\nprompt: |\n  <output_schema>{output_schema}</output_schema>\n  Do A {thing}\n"
    )
    (prompts_dir / "single.json").write_text('{"type":"object","properties":{"x":{"type":"number"}},"required":["x"]}')

    # List mapping (no schema)
    (prompts_dir / "list.yaml").write_text(
        "- name: b\n  prompt: |\n    Do B {foo}\n- name: c\n  prompt: |\n    Do C {bar}\n"
    )

    added = load_prompts(mcp, prompts_dir)
    assert added >= 3
