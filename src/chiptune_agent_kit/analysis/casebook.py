from __future__ import annotations

from pathlib import Path
from statistics import median
from typing import Any


def _pulse_metrics(song: dict[str, Any]) -> dict[str, Any] | None:
    rel = song.get("relationships", {}).get("pulse_1_pulse_2")
    if not rel:
        return None

    counts = rel["note_counts"]
    if counts["pulse_1"] <= 0 or counts["pulse_2"] <= 0:
        return None

    time = rel["time_relationship"]
    onset = rel["onset_relationship"]
    motion = rel["motion_relationship"]
    density = rel["density_relationship"]

    corr = density.get("pearson_onset_density_correlation")
    consonance = (
        float(onset.get("third_like_ratio") or 0.0)
        + float(onset.get("sixth_like_ratio") or 0.0)
        + float(onset.get("unison_octave_like_ratio") or 0.0)
    )

    return {
        "source": song["source"],
        "name": Path(song["source"]).name,
        "pulse_1_notes": counts["pulse_1"],
        "pulse_2_notes": counts["pulse_2"],
        "overlap": float(time["overlap_ratio_of_active_union"]),
        "sync": float(onset["synchronized_onset_ratio"]),
        "synchronized_pairs": int(onset["synchronized_pairs"]),
        "third_like": float(onset.get("third_like_ratio") or 0.0),
        "sixth_like": float(onset.get("sixth_like_ratio") or 0.0),
        "unison_octave_like": float(onset.get("unison_octave_like_ratio") or 0.0),
        "consonance_family": consonance,
        "similar_direction": float(motion.get("similar_direction_ratio") or 0.0),
        "contrary": float(motion.get("contrary_ratio") or 0.0),
        "parallel_preserving": float(motion.get("interval_preserving_parallel_ratio") or 0.0),
        "density_correlation": float(corr) if corr is not None else None,
    }


def _ranked(items: list[dict[str, Any]], score_key: str, count: int) -> list[dict[str, Any]]:
    return sorted(items, key=lambda item: float(item[score_key]), reverse=True)[:count]


def select_pulse_cases(report: dict[str, Any], count_per_group: int = 5) -> dict[str, Any]:
    """Select interpretable discovery cases from a NES-MDB analysis report.

    These groups are heuristic lenses, not ground-truth musical labels.
    """

    metrics = [m for song in report.get("songs", []) if (m := _pulse_metrics(song)) is not None]
    if not metrics:
        return {"groups": {}, "population": {"songs_with_both_pulses": 0}}

    for item in metrics:
        item["locked_score"] = (
            0.40 * item["sync"]
            + 0.25 * item["overlap"]
            + 0.20 * min(1.0, item["consonance_family"])
            + 0.15 * item["parallel_preserving"]
        )
        item["interlocking_score"] = 0.55 * item["overlap"] + 0.45 * (1.0 - item["sync"])
        corr = item["density_correlation"]
        item["compensation_score"] = (
            0.70 * max(0.0, -(corr if corr is not None else 0.0))
            + 0.30 * item["overlap"]
        )

    locked_pool = [
        item for item in metrics
        if item["overlap"] >= 0.80 and item["sync"] >= 0.80 and item["synchronized_pairs"] >= 4
    ]
    interlocking_pool = [
        item for item in metrics
        if item["overlap"] >= 0.70 and item["sync"] <= 0.25
    ]
    compensation_pool = [
        item for item in metrics
        if item["density_correlation"] is not None and item["density_correlation"] <= -0.20
    ]

    groups: dict[str, list[dict[str, Any]]] = {
        "locked": _ranked(locked_pool, "locked_score", count_per_group),
        "interlocking": _ranked(interlocking_pool, "interlocking_score", count_per_group),
        "density_compensation": _ranked(compensation_pool, "compensation_score", count_per_group),
    }

    used = {item["source"] for group in groups.values() for item in group}
    sync_median = median(item["sync"] for item in metrics)
    overlap_median = median(item["overlap"] for item in metrics)
    correlations = [item["density_correlation"] for item in metrics if item["density_correlation"] is not None]
    corr_median = median(correlations) if correlations else 0.0

    middle_pool = []
    for item in metrics:
        if item["source"] in used:
            continue
        corr = item["density_correlation"] if item["density_correlation"] is not None else corr_median
        item["middle_distance"] = (
            abs(item["sync"] - sync_median)
            + abs(item["overlap"] - overlap_median)
            + 0.5 * abs(corr - corr_median)
        )
        middle_pool.append(item)

    groups["middle"] = sorted(middle_pool, key=lambda item: item["middle_distance"])[:count_per_group]

    def clean(item: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in item.items()
            if key not in {"locked_score", "interlocking_score", "compensation_score", "middle_distance"}
        }

    return {
        "population": {
            "songs_with_both_pulses": len(metrics),
            "median_sync": sync_median,
            "median_overlap": overlap_median,
            "median_density_correlation": corr_median,
        },
        "group_definitions": {
            "locked": "High overlap + high synchronized-onset ratio; candidate tightly coupled pulse writing.",
            "interlocking": "High overlap + low synchronized-onset ratio; candidate independent/interlocking pulse writing.",
            "density_compensation": "Negative onset-density correlation; candidate one-busy-while-the-other-relaxes behavior.",
            "middle": "Near corpus medians; useful control cases rather than an intended style label.",
        },
        "groups": {name: [clean(item) for item in items] for name, items in groups.items()},
        "interpretation_note": (
            "These are discovery buckets selected by transparent heuristics. "
            "Inspect the MIDI and listen before turning any bucket into a composition rule."
        ),
    }


def render_casebook_markdown(casebook: dict[str, Any]) -> str:
    lines = [
        "# Pulse Relationship Casebook",
        "",
        "> Discovery cases only. These buckets are not ground-truth musical genres or labels.",
        "",
    ]

    definitions = casebook.get("group_definitions", {})
    for group_name, items in casebook.get("groups", {}).items():
        lines.extend([
            f"## {group_name}",
            "",
            definitions.get(group_name, ""),
            "",
            "| file | sync | overlap | density corr | thirds | sixths | unison/oct | parallel |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ])
        for item in items:
            corr = item["density_correlation"]
            corr_text = "n/a" if corr is None else f"{corr:.3f}"
            lines.append(
                f"| `{item['name']}` | {item['sync']:.3f} | {item['overlap']:.3f} | "
                f"{corr_text} | {item['third_like']:.3f} | {item['sixth_like']:.3f} | "
                f"{item['unison_octave_like']:.3f} | {item['parallel_preserving']:.3f} |"
            )
        lines.append("")

    return "\n".join(lines)
