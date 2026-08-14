from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from statistics import mean
from typing import Any

from chiptune_agent_kit.analysis import (
    analyze_nes_midi,
    analyze_pulse_relationships_from_midi,
)

VOICE_NAMES = ("pulse_1", "pulse_2", "triangle", "noise")
ONSET_TOLERANCES_SECONDS = (0.002, 0.005, 0.010, 0.030)


def _mean(values: list[float]) -> float | None:
    return mean(values) if values else None


def _mean_present(values: list[float | None]) -> float | None:
    return _mean([float(value) for value in values if value is not None])


def _select_files(
    files: list[Path],
    limit: int | None,
    strategy: str,
    seed: int,
) -> list[Path]:
    if limit is None or limit >= len(files):
        return files
    if limit <= 0:
        return []

    if strategy == "first":
        return files[:limit]
    if strategy == "random":
        return sorted(random.Random(seed).sample(files, limit))
    raise ValueError(f"Unsupported sample strategy: {strategy}")


def _relationship_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    relations = [
        item["relationships"]["pulse_1_pulse_2"]
        for item in results
        if item["voices"]["pulse_1"]["note_count"] > 0
        and item["voices"]["pulse_2"]["note_count"] > 0
    ]

    def values(section: str, key: str) -> list[float | None]:
        return [relation[section][key] for relation in relations]

    return {
        "songs_with_both_pulses": len(relations),
        "mean_overlap_ratio_of_active_union": _mean_present(
            values("time_relationship", "overlap_ratio_of_active_union")
        ),
        "mean_overlap_ratio_of_song": _mean_present(
            values("time_relationship", "overlap_ratio_of_song")
        ),
        "mean_synchronized_onset_ratio": _mean_present(
            values("onset_relationship", "synchronized_onset_ratio")
        ),
        "mean_third_like_ratio_at_synchronized_onsets": _mean_present(
            values("onset_relationship", "third_like_ratio")
        ),
        "mean_sixth_like_ratio_at_synchronized_onsets": _mean_present(
            values("onset_relationship", "sixth_like_ratio")
        ),
        "mean_unison_octave_like_ratio_at_synchronized_onsets": _mean_present(
            values("onset_relationship", "unison_octave_like_ratio")
        ),
        "mean_similar_direction_ratio": _mean_present(
            values("motion_relationship", "similar_direction_ratio")
        ),
        "mean_contrary_ratio": _mean_present(
            values("motion_relationship", "contrary_ratio")
        ),
        "mean_oblique_ratio": _mean_present(
            values("motion_relationship", "oblique_ratio")
        ),
        "mean_interval_preserving_parallel_ratio": _mean_present(
            values("motion_relationship", "interval_preserving_parallel_ratio")
        ),
        "mean_exclusive_activity_ratio": _mean_present(
            values("activity_relationship", "exclusive_activity_ratio")
        ),
        "mean_adjacent_exclusive_switch_rate": _mean_present(
            values("activity_relationship", "adjacent_exclusive_switch_rate")
        ),
        "mean_onset_density_correlation": _mean_present(
            values("density_relationship", "pearson_onset_density_correlation")
        ),
        "mean_density_compensation_score": _mean_present(
            values("density_relationship", "density_compensation_score")
        ),
        "interpretation_note": (
            "Corpus means summarize observable P1/P2 behavior. "
            "Do not promote them directly to composition rules without "
            "per-song inspection and listening tests."
        ),
    }


def _relationship_sensitivity_summary(
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for tolerance in ONSET_TOLERANCES_SECONDS:
        key = f"{tolerance:.3f}"
        relations = [
            item["relationships"]["pulse_1_pulse_2_sensitivity"][key]
            for item in results
            if item["voices"]["pulse_1"]["note_count"] > 0
            and item["voices"]["pulse_2"]["note_count"] > 0
        ]

        def values(section: str, field: str) -> list[float | None]:
            return [relation[section][field] for relation in relations]

        output[key] = {
            "tolerance_seconds": tolerance,
            "mean_synchronized_onset_ratio": _mean_present(
                values("onset_relationship", "synchronized_onset_ratio")
            ),
            "mean_third_like_ratio": _mean_present(
                values("onset_relationship", "third_like_ratio")
            ),
            "mean_sixth_like_ratio": _mean_present(
                values("onset_relationship", "sixth_like_ratio")
            ),
            "mean_unison_octave_like_ratio": _mean_present(
                values("onset_relationship", "unison_octave_like_ratio")
            ),
            "mean_similar_direction_ratio": _mean_present(
                values("motion_relationship", "similar_direction_ratio")
            ),
            "mean_contrary_ratio": _mean_present(
                values("motion_relationship", "contrary_ratio")
            ),
            "mean_interval_preserving_parallel_ratio": _mean_present(
                values(
                    "motion_relationship",
                    "interval_preserving_parallel_ratio",
                )
            ),
        }
    return output


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    voices: dict[str, dict[str, Any]] = {}

    for voice_name in VOICE_NAMES:
        stats = [item["voices"][voice_name] for item in results]
        with_notes = [item for item in stats if item["note_count"] > 0]
        pitch_ranges = [
            item["pitch_range"]
            for item in with_notes
            if item["pitch_range"] is not None
        ]

        voices[voice_name] = {
            "songs_with_notes": len(with_notes),
            "presence_ratio": len(with_notes) / len(results) if results else 0.0,
            "total_notes": sum(item["note_count"] for item in stats),
            "mean_notes_per_song": _mean(
                [float(item["note_count"]) for item in stats]
            ),
            "corpus_pitch_range": [
                min(r[0] for r in pitch_ranges),
                max(r[1] for r in pitch_ranges),
            ]
            if pitch_ranges
            else None,
            "mean_note_duration_seconds": _mean(
                [
                    float(item["mean_duration_seconds"])
                    for item in with_notes
                    if item["mean_duration_seconds"] is not None
                ]
            ),
            "mean_inter_onset_seconds": _mean(
                [
                    float(item["mean_inter_onset_seconds"])
                    for item in with_notes
                    if item["mean_inter_onset_seconds"] is not None
                ]
            ),
            "mean_active_time_ratio": _mean(
                [float(item["active_time_ratio"]) for item in stats]
            ),
            "total_cc11_changes": sum(item["cc11_changes"] for item in stats),
            "total_cc12_changes": sum(item["cc12_changes"] for item in stats),
        }

    return {
        "songs_analyzed": len(results),
        "total_duration_seconds": sum(
            float(item["duration_seconds"]) for item in results
        ),
        "mean_duration_seconds": _mean(
            [float(item["duration_seconds"]) for item in results]
        ),
        "voices": voices,
        "pulse_1_pulse_2": _relationship_summary(results),
        "pulse_1_pulse_2_onset_sensitivity": (
            _relationship_sensitivity_summary(results)
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch-analyze NES-MDB-style MIDI files."
    )
    parser.add_argument(
        "root",
        type=Path,
        help="Directory containing MIDI files recursively",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Analyze at most N MIDI files",
    )
    parser.add_argument(
        "--sample-strategy",
        choices=("random", "first"),
        default="random",
        help="How to choose files when --limit is used",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Random seed used by --sample-strategy random",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output JSON report",
    )
    args = parser.parse_args()

    population = sorted(args.root.rglob("*.mid"))
    files = _select_files(
        population,
        args.limit,
        args.sample_strategy,
        args.seed,
    )
    if not files:
        raise SystemExit(f"No .mid files selected under {args.root}")

    results: list[dict[str, Any]] = []
    for path in files:
        item = analyze_nes_midi(path)
        sensitivity = {
            f"{tolerance:.3f}": analyze_pulse_relationships_from_midi(
                path,
                onset_tolerance_seconds=tolerance,
            )
            for tolerance in ONSET_TOLERANCES_SECONDS
        }
        item["relationships"] = {
            "pulse_1_pulse_2": sensitivity["0.005"],
            "pulse_1_pulse_2_sensitivity": sensitivity,
        }
        results.append(item)

    report = {
        "sample": {
            "population_files_found": len(population),
            "selected_files": len(files),
            "strategy": (
                "all"
                if len(files) == len(population)
                else args.sample_strategy
            ),
            "seed": (
                args.seed
                if args.sample_strategy == "random"
                and len(files) < len(population)
                else None
            ),
        },
        "summary": summarize(results),
        "songs": results,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    summary = report["summary"]
    print(
        f"Analyzed {summary['songs_analyzed']} songs "
        f"from {len(population)} MIDI files"
    )
    for voice_name, voice in summary["voices"].items():
        print(
            f"{voice_name:10s} songs={voice['songs_with_notes']:3d} "
            f"notes={voice['total_notes']:6d} "
            f"active={voice['mean_active_time_ratio']:.3f}"
        )

    relation = summary["pulse_1_pulse_2"]
    print("P1/P2 relationship")
    print(
        "  active-overlap="
        f"{relation['mean_overlap_ratio_of_active_union']:.3f}"
    )
    print(
        "  synchronized-onsets="
        f"{relation['mean_synchronized_onset_ratio']:.3f}"
    )
    print(
        "  density-correlation="
        f"{relation['mean_onset_density_correlation']}"
    )
    print(args.output)


if __name__ == "__main__":
    main()
