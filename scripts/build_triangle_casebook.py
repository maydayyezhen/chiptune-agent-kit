from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from chiptune_agent_kit.analysis.nes_midi import extract_nes_note_spans
from chiptune_agent_kit.analysis.note_hygiene import filter_composition_spans


PATTERNS = (
    "repeated_note_drive",
    "octave_pump",
    "dominant_pitch_pedal",
    "stepwise_motion",
)


def note_name(pitch: int) -> str:
    names = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
    return f"{names[pitch % 12]}{pitch // 12 - 1}"


def score_candidate(pattern: str, evidence: dict[str, Any]) -> float:
    if pattern == "repeated_note_drive":
        return float(evidence["repeated_transition_ratio"]) + min(0.25, int(evidence["longest_repeated_pitch_run_notes"]) / 100.0)
    if pattern == "octave_pump":
        return float(evidence["octave_transition_ratio"]) + min(0.25, int(evidence["longest_octave_chain_notes"]) / 100.0)
    if pattern == "dominant_pitch_pedal":
        # Prefer pedal cases with excursions, so this lens is not just a duplicate of repeated-note drive.
        repeat = float(evidence["repeated_transition_ratio"])
        excursion_bonus = max(0.0, 0.70 - repeat)
        return float(evidence["dominant_pitch_ratio"]) + excursion_bonus
    if pattern == "stepwise_motion":
        return float(evidence["stepwise_transition_ratio"]) - 0.25 * float(evidence["repeated_transition_ratio"])
    raise ValueError(pattern)


def select_cases(report: dict[str, Any], count: int) -> dict[str, list[dict[str, Any]]]:
    output: dict[str, list[dict[str, Any]]] = {}
    for pattern in PATTERNS:
        ranked: list[dict[str, Any]] = []
        for song in report["songs"]:
            for candidate in song["candidates"]:
                if candidate["pattern"] != pattern:
                    continue
                evidence = candidate["evidence"]
                if pattern == "dominant_pitch_pedal" and float(evidence["repeated_transition_ratio"]) >= 0.70:
                    continue
                ranked.append({
                    "song": song["name"],
                    "window": candidate["window"],
                    "evidence": evidence,
                    "score": score_candidate(pattern, evidence),
                })
        ranked.sort(key=lambda item: item["score"], reverse=True)
        chosen: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in ranked:
            if item["song"] in seen:
                continue
            seen.add(item["song"])
            chosen.append(item)
            if len(chosen) >= count:
                break
        output[pattern] = chosen
    return output


def expand_case(root: Path, case: dict[str, Any], floor: float) -> dict[str, Any]:
    matches = list(root.rglob(case["song"]))
    if not matches:
        raise FileNotFoundError(case["song"])
    spans = filter_composition_spans(
        extract_nes_note_spans(matches[0])["triangle"],
        drop_duration_at_or_below_seconds=floor,
    )
    start, end = map(float, case["window"])
    local = [span for span in spans if start <= span.start_seconds < end]
    rows: list[dict[str, Any]] = []
    previous_pitch: int | None = None
    for span in local:
        rows.append({
            "t": span.start_seconds - start,
            "note": note_name(span.pitch),
            "pitch": span.pitch,
            "duration": span.duration_seconds,
            "interval_from_previous": None if previous_pitch is None else span.pitch - previous_pitch,
        })
        previous_pitch = span.pitch
    expanded = dict(case)
    expanded["notes"] = rows
    expanded["pitch_sequence"] = [row["pitch"] for row in rows]
    expanded["interval_sequence"] = [row["interval_from_previous"] for row in rows[1:]]
    return expanded


def render_markdown(cases: dict[str, list[dict[str, Any]]]) -> str:
    lines = [
        "# Triangle Pattern Casebook",
        "",
        "> Representative local windows selected from the full-corpus discovery scan. These are evidence examples, not style labels.",
        "",
    ]
    for pattern in PATTERNS:
        lines.extend([f"## {pattern}", ""])
        if pattern == "dominant_pitch_pedal":
            lines.extend([
                "This lens intentionally excludes windows with repeated-transition ratio >= 0.70, so it focuses on pedal behavior with excursions rather than duplicating repeated-note drive.",
                "",
            ])
        for case in cases.get(pattern, []):
            lines.append(f"### {case['song']} @ {case['window'][0]:.3f}-{case['window'][1]:.3f}s")
            lines.append("")
            lines.append(f"Evidence: `{json.dumps(case['evidence'], sort_keys=True)}`")
            lines.append("")
            pitch_names = " ".join(row["note"] for row in case["notes"])
            intervals = " ".join(f"{value:+d}" for value in case["interval_sequence"] if value is not None)
            lines.append(f"Notes: `{pitch_names}`")
            lines.append("")
            lines.append(f"Intervals: `{intervals}`")
            lines.append("")
            lines.append("| t | note | dur | Δst |")
            lines.append("|---:|---:|---:|---:|")
            for row in case["notes"][:40]:
                delta = "" if row["interval_from_previous"] is None else f"{row['interval_from_previous']:+d}"
                lines.append(f"| {row['t']:.3f} | {row['note']} | {row['duration']:.3f} | {delta} |")
            if len(case["notes"]) > 40:
                lines.append(f"| ... | ... | ... | {len(case['notes']) - 40} more notes |")
            lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("midi_root", type=Path)
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--micro-note-floor-seconds", type=float, default=0.001)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8"))
    selected = select_cases(report, args.count)
    expanded = {
        pattern: [
            expand_case(args.midi_root, item, args.micro_note_floor_seconds)
            for item in items
        ]
        for pattern, items in selected.items()
    }
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(expanded, indent=2), encoding="utf-8")
    args.markdown_output.write_text(render_markdown(expanded), encoding="utf-8")
    print(args.markdown_output)


if __name__ == "__main__":
    main()
