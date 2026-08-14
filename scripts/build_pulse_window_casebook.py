from __future__ import annotations

import argparse
import json
from pathlib import Path

from chiptune_agent_kit.analysis.pulse_windows import (
    build_pulse_window_casebook,
    render_pulse_window_casebook_markdown,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Expand pulse discovery cases into representative note-level windows.")
    parser.add_argument("casebook", type=Path, help="pulse_casebook.json")
    parser.add_argument("--root", type=Path, default=None, help="Root containing NES-MDB MIDI files")
    parser.add_argument("--window-seconds", type=float, default=6.0)
    parser.add_argument("--step-seconds", type=float, default=1.0)
    parser.add_argument("--onset-tolerance-seconds", type=float, default=0.005)
    parser.add_argument("--density-bin-seconds", type=float, default=0.5)
    parser.add_argument("--max-event-rows", type=int, default=36)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    args = parser.parse_args()

    casebook = json.loads(args.casebook.read_text(encoding="utf-8"))
    result = build_pulse_window_casebook(
        casebook,
        root=args.root,
        window_seconds=args.window_seconds,
        step_seconds=args.step_seconds,
        onset_tolerance_seconds=args.onset_tolerance_seconds,
        density_bin_seconds=args.density_bin_seconds,
        max_event_rows=args.max_event_rows,
    )

    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    args.markdown_output.write_text(render_pulse_window_casebook_markdown(result), encoding="utf-8")

    print(f"groups: {len(result['groups'])}")
    for group_name, items in result["groups"].items():
        print(f"{group_name}: {len(items)}")
        for item in items:
            local = item["selected_window"]
            corr = local["density_correlation"]
            corr_text = "n/a" if corr is None else f"{corr:.3f}"
            print(
                f"  {item['name']} {local['start_seconds']:.1f}-{local['end_seconds']:.1f}s "
                f"sync={local['synchronized_onset_ratio']:.3f} "
                f"overlap={local['active_overlap_ratio']:.3f} corr={corr_text}"
            )
    print(args.markdown_output)


if __name__ == "__main__":
    main()
