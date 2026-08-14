from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from statistics import mean

from chiptune_agent_kit.analysis.nes_midi import extract_nes_note_spans
from chiptune_agent_kit.analysis.note_hygiene import filter_composition_spans
from chiptune_agent_kit.analysis.relationships import analyze_pulse_relationships


def _resolve_source(source: str, root: Path) -> Path:
    source_path = Path(source)
    if source_path.exists():
        return source_path
    matches = list(root.rglob(source_path.name))
    if len(matches) != 1:
        raise FileNotFoundError(
            f"Expected one MIDI named {source_path.name!r} under {root}, found {len(matches)}"
        )
    return matches[0]


def _safe_mean(values: list[float]) -> float | None:
    return mean(values) if values else None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a composition-oriented NES-MDB report while preserving raw MIDI analysis."
    )
    parser.add_argument("report", type=Path, help="Raw NES-MDB sample report")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--drop-micro-notes-at-or-below-seconds", type=float, default=0.001)
    parser.add_argument("--onset-tolerance-seconds", type=float, default=0.005)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    raw_report = json.loads(args.report.read_text(encoding="utf-8"))
    report = copy.deepcopy(raw_report)
    sync_values: list[float] = []
    overlap_values: list[float] = []
    density_values: list[float] = []

    for song in report.get("songs", []):
        path = _resolve_source(song["source"], args.root)
        spans = extract_nes_note_spans(path)
        p1 = filter_composition_spans(
            spans["pulse_1"],
            drop_duration_at_or_below_seconds=args.drop_micro_notes_at_or_below_seconds,
        )
        p2 = filter_composition_spans(
            spans["pulse_2"],
            drop_duration_at_or_below_seconds=args.drop_micro_notes_at_or_below_seconds,
        )
        raw_relation = song.get("relationships", {}).get("pulse_1_pulse_2")
        relation = analyze_pulse_relationships(
            p1,
            p2,
            song_duration_seconds=float(song["duration_seconds"]),
            onset_tolerance_seconds=args.onset_tolerance_seconds,
        )
        song.setdefault("relationships", {})["pulse_1_pulse_2_raw"] = raw_relation
        song["relationships"]["pulse_1_pulse_2"] = relation
        song["composition_view"] = {
            "drop_micro_notes_at_or_below_seconds": args.drop_micro_notes_at_or_below_seconds,
            "raw_note_counts": {
                "pulse_1": len(spans["pulse_1"]),
                "pulse_2": len(spans["pulse_2"]),
            },
            "clean_note_counts": {
                "pulse_1": len(p1),
                "pulse_2": len(p2),
            },
        }
        if p1 and p2:
            sync_values.append(float(relation["onset_relationship"]["synchronized_onset_ratio"]))
            overlap_values.append(float(relation["time_relationship"]["overlap_ratio_of_active_union"]))
            corr = relation["density_relationship"]["pearson_onset_density_correlation"]
            if corr is not None:
                density_values.append(float(corr))

    report["analysis_view"] = {
        "name": "composition",
        "raw_source_report": str(args.report),
        "drop_micro_notes_at_or_below_seconds": args.drop_micro_notes_at_or_below_seconds,
        "onset_tolerance_seconds": args.onset_tolerance_seconds,
        "note": "Raw MIDI analysis is retained per song under pulse_1_pulse_2_raw.",
    }
    report["composition_summary"] = {
        "songs_with_both_pulses": len(sync_values),
        "mean_synchronized_onset_ratio": _safe_mean(sync_values),
        "mean_overlap_ratio_of_active_union": _safe_mean(overlap_values),
        "mean_onset_density_correlation": _safe_mean(density_values),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")

    summary = report["composition_summary"]
    print(json.dumps(report["analysis_view"], indent=2))
    print(json.dumps(summary, indent=2))
    print(args.output)


if __name__ == "__main__":
    main()
