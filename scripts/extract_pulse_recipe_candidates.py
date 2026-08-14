from __future__ import annotations

import argparse
import json
from pathlib import Path

from chiptune_agent_kit.analysis.recipe_candidates import (
    extract_pulse_recipe_candidates,
    render_recipe_candidates_markdown,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract interpretable pulse-arrangement recipe hypotheses from cleaned windows."
    )
    parser.add_argument("window_casebook", type=Path)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    args = parser.parse_args()

    window_casebook = json.loads(args.window_casebook.read_text(encoding="utf-8"))
    result = extract_pulse_recipe_candidates(window_casebook)

    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    args.markdown_output.write_text(render_recipe_candidates_markdown(result), encoding="utf-8")

    print(json.dumps(result["candidate_counts"], indent=2))
    print(args.markdown_output)


if __name__ == "__main__":
    main()
