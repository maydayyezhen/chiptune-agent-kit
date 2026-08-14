from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from chiptune_agent_kit.analysis.nes_midi import extract_nes_note_spans
from chiptune_agent_kit.analysis.note_hygiene import filter_composition_spans
from chiptune_agent_kit.analysis.pulse_windows import (
    build_onset_rows,
    render_pulse_window_casebook_markdown,
    select_representative_window,
)


def _resolve(source: str, name: str, root: Path) -> Path:
    path = Path(source)
    if path.exists():
        return path
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise FileNotFoundError(f"Expected one {name!r} under {root}, found {len(matches)}")
    return matches[0]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect representative P1/P2 windows from the cleaned composition view."
    )
    parser.add_argument("casebook", type=Path)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--drop-micro-notes-at-or-below-seconds", type=float, default=0.001)
    parser.add_argument("--window-seconds", type=float, default=6.0)
    parser.add_argument("--step-seconds", type=float, default=1.0)
    parser.add_argument("--onset-tolerance-seconds", type=float, default=0.005)
    parser.add_argument("--density-bin-seconds", type=float, default=0.5)
    parser.add_argument("--max-event-rows", type=int, default=36)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    args = parser.parse_args()

    casebook = json.loads(args.casebook.read_text(encoding="utf-8"))
    groups: dict[str, list[dict]] = {}

    for group_name, items in casebook.get("groups", {}).items():
        group_results: list[dict] = []
        for item in items:
            midi_path = _resolve(item["source"], item["name"], args.root)
            raw = extract_nes_note_spans(midi_path)
            p1 = filter_composition_spans(
                raw["pulse_1"],
                drop_duration_at_or_below_seconds=args.drop_micro_notes_at_or_below_seconds,
            )
            p2 = filter_composition_spans(
                raw["pulse_2"],
                drop_duration_at_or_below_seconds=args.drop_micro_notes_at_or_below_seconds,
            )
            local = select_representative_window(
                p1,
                p2,
                group_name,
                item,
                window_seconds=args.window_seconds,
                step_seconds=args.step_seconds,
                onset_tolerance_seconds=args.onset_tolerance_seconds,
                density_bin_seconds=args.density_bin_seconds,
            )
            rows = build_onset_rows(
                p1,
                p2,
                local["start_seconds"],
                local["end_seconds"],
                onset_tolerance_seconds=args.onset_tolerance_seconds,
            )
            group_results.append({
                "name": item["name"],
                "source": str(midi_path),
                "global_case_metrics": item,
                "selected_window": local,
                "event_relation_counts": dict(Counter(row["relation"] for row in rows)),
                "onset_rows": rows[: args.max_event_rows],
                "onset_rows_truncated": max(0, len(rows) - args.max_event_rows),
                "hygiene": {
                    "drop_micro_notes_at_or_below_seconds": args.drop_micro_notes_at_or_below_seconds,
                    "raw_note_counts": {
                        "pulse_1": len(raw["pulse_1"]),
                        "pulse_2": len(raw["pulse_2"]),
                    },
                    "clean_note_counts": {
                        "pulse_1": len(p1),
                        "pulse_2": len(p2),
                    },
                },
            })
        groups[group_name] = group_results

    result = {
        "parameters": {
            "analysis_view": "composition",
            "drop_micro_notes_at_or_below_seconds": args.drop_micro_notes_at_or_below_seconds,
            "window_seconds": args.window_seconds,
            "step_seconds": args.step_seconds,
            "onset_tolerance_seconds": args.onset_tolerance_seconds,
            "density_bin_seconds": args.density_bin_seconds,
            "max_event_rows": args.max_event_rows,
        },
        "groups": groups,
        "interpretation_note": (
            "Windows use a cleaned composition view. Raw sample-accurate MIDI remains unchanged "
            "and should be used separately for performance/timbre analysis."
        ),
    }

    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    args.markdown_output.write_text(render_pulse_window_casebook_markdown(result), encoding="utf-8")

    for group_name, items in groups.items():
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
