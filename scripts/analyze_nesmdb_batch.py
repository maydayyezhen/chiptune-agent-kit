from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Any

from chiptune_agent_kit.analysis import analyze_nes_midi

VOICE_NAMES = ("pulse_1", "pulse_2", "triangle", "noise")


def _mean(values: list[float]) -> float | None:
    return mean(values) if values else None


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    voices: dict[str, dict[str, Any]] = {}

    for voice_name in VOICE_NAMES:
        stats = [item["voices"][voice_name] for item in results]
        with_notes = [item for item in stats if item["note_count"] > 0]
        pitch_ranges = [item["pitch_range"] for item in with_notes if item["pitch_range"] is not None]

        voices[voice_name] = {
            "songs_with_notes": len(with_notes),
            "presence_ratio": len(with_notes) / len(results) if results else 0.0,
            "total_notes": sum(item["note_count"] for item in stats),
            "mean_notes_per_song": _mean([float(item["note_count"]) for item in stats]),
            "corpus_pitch_range": [
                min(r[0] for r in pitch_ranges),
                max(r[1] for r in pitch_ranges),
            ] if pitch_ranges else None,
            "mean_note_duration_seconds": _mean([
                float(item["mean_duration_seconds"])
                for item in with_notes
                if item["mean_duration_seconds"] is not None
            ]),
            "mean_inter_onset_seconds": _mean([
                float(item["mean_inter_onset_seconds"])
                for item in with_notes
                if item["mean_inter_onset_seconds"] is not None
            ]),
            "mean_active_time_ratio": _mean([
                float(item["active_time_ratio"])
                for item in stats
            ]),
            "total_cc11_changes": sum(item["cc11_changes"] for item in stats),
            "total_cc12_changes": sum(item["cc12_changes"] for item in stats),
        }

    return {
        "songs_analyzed": len(results),
        "total_duration_seconds": sum(float(item["duration_seconds"]) for item in results),
        "mean_duration_seconds": _mean([float(item["duration_seconds"]) for item in results]),
        "voices": voices,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch-analyze NES-MDB-style MIDI files.")
    parser.add_argument("root", type=Path, help="Directory containing MIDI files recursively")
    parser.add_argument("--limit", type=int, default=None, help="Analyze only the first N sorted MIDI files")
    parser.add_argument("--output", type=Path, required=True, help="Output JSON report")
    args = parser.parse_args()

    files = sorted(args.root.rglob("*.mid"))
    if args.limit is not None:
        files = files[: args.limit]
    if not files:
        raise SystemExit(f"No .mid files found under {args.root}")

    results = [analyze_nes_midi(path) for path in files]
    report = {
        "summary": summarize(results),
        "songs": results,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")

    summary = report["summary"]
    print(f"Analyzed {summary['songs_analyzed']} songs")
    for voice_name, voice in summary["voices"].items():
        print(
            f"{voice_name:10s} songs={voice['songs_with_notes']:3d} "
            f"notes={voice['total_notes']:6d} "
            f"active={voice['mean_active_time_ratio']:.3f}"
        )
    print(args.output)


if __name__ == "__main__":
    main()
