from __future__ import annotations

import argparse
import json
from pathlib import Path

from chiptune_agent_kit.analysis.triangle_recipe_candidates import render_markdown, scan_corpus


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan NES-MDB for refined Triangle recipe candidates.")
    parser.add_argument("root", type=Path)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    parser.add_argument("--floor", type=float, default=0.001)
    parser.add_argument("--window", type=float, default=8.0)
    parser.add_argument("--step", type=float, default=4.0)
    parser.add_argument("--progress-every", type=int, default=250)
    args = parser.parse_args()

    report = scan_corpus(
        args.root,
        floor=args.floor,
        window=args.window,
        step=args.step,
        progress_every=args.progress_every,
    )
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    args.markdown_output.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    print(args.markdown_output)


if __name__ == "__main__":
    main()
