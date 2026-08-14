from __future__ import annotations

import argparse
import json
from pathlib import Path

from chiptune_agent_kit.analysis.corpus_recipes import (
    render_corpus_scan_markdown,
    scan_corpus,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scan the full NES-MDB MIDI corpus for pulse-arrangement recipe candidates."
    )
    parser.add_argument("root", type=Path, help="Directory containing NES-MDB MIDI files recursively")
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    parser.add_argument("--micro-note-floor-seconds", type=float, default=0.001)
    parser.add_argument("--window-seconds", type=float, default=6.0)
    parser.add_argument("--step-seconds", type=float, default=3.0)
    parser.add_argument("--onset-tolerance-seconds", type=float, default=0.005)
    parser.add_argument("--density-bin-seconds", type=float, default=0.5)
    parser.add_argument(
        "--density-scales-seconds",
        type=float,
        nargs="+",
        default=[4.0, 8.0, 16.0],
    )
    parser.add_argument("--progress-every", type=int, default=250)
    args = parser.parse_args()

    report = scan_corpus(
        args.root,
        micro_note_floor_seconds=args.micro_note_floor_seconds,
        window_seconds=args.window_seconds,
        step_seconds=args.step_seconds,
        onset_tolerance_seconds=args.onset_tolerance_seconds,
        density_bin_seconds=args.density_bin_seconds,
        density_scales_seconds=tuple(args.density_scales_seconds),
        progress_every=args.progress_every,
    )

    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    args.markdown_output.write_text(
        render_corpus_scan_markdown(report),
        encoding="utf-8",
    )

    print(json.dumps(report["summary"], indent=2))
    print(args.markdown_output)


if __name__ == "__main__":
    main()
