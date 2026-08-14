from __future__ import annotations

from collections import Counter
from statistics import median
from typing import Any


def _interval_runs(values: list[int]) -> list[dict[str, int]]:
    if not values:
        return []
    runs: list[dict[str, int]] = []
    current = values[0]
    count = 1
    for value in values[1:]:
        if value == current:
            count += 1
        else:
            runs.append({"interval_semitones": current, "length": count})
            current = value
            count = 1
    runs.append({"interval_semitones": current, "length": count})
    return runs


def _best_lagged_match(
    left: list[int],
    right: list[int],
    *,
    max_lag: int = 4,
    min_pairs: int = 6,
) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    for lag in range(-max_lag, max_lag + 1):
        pairs = [
            (value, right[index + lag])
            for index, value in enumerate(left)
            if 0 <= index + lag < len(right)
        ]
        if len(pairs) < min_pairs:
            continue
        matches = sum(a == b for a, b in pairs)
        ratio = matches / len(pairs)
        candidate = {
            "lag_events": lag,
            "compared_pairs": len(pairs),
            "matches": matches,
            "match_ratio": ratio,
        }
        if best is None:
            best = candidate
            continue
        best_key = (
            float(best["match_ratio"]),
            int(best["compared_pairs"]),
            -abs(int(best["lag_events"])),
        )
        candidate_key = (ratio, len(pairs), -abs(lag))
        if candidate_key > best_key:
            best = candidate
    return best


def _pitch_time_sequences(
    rows: list[dict[str, Any]],
) -> tuple[list[tuple[int, float]], list[tuple[int, float]]]:
    p1 = [
        (int(row["pulse_1_pitch"]), float(row["relative_seconds"]))
        for row in rows
        if row.get("pulse_1_pitch") is not None
    ]
    p2 = [
        (int(row["pulse_2_pitch"]), float(row["relative_seconds"]))
        for row in rows
        if row.get("pulse_2_pitch") is not None
    ]
    return p1, p2


def _phase_match(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    p1, p2 = _pitch_time_sequences(rows)
    pitches_1 = [pitch for pitch, _ in p1]
    pitches_2 = [pitch for pitch, _ in p2]
    best = _best_lagged_match(pitches_1, pitches_2, max_lag=4, min_pairs=8)
    if best is None:
        return None

    lag = int(best["lag_events"])
    offsets: list[float] = []
    matching_offsets: list[float] = []
    for index, (pitch_1, time_1) in enumerate(p1):
        other = index + lag
        if not (0 <= other < len(p2)):
            continue
        pitch_2, time_2 = p2[other]
        offset = time_1 - time_2
        offsets.append(offset)
        if pitch_1 == pitch_2:
            matching_offsets.append(offset)

    selected = matching_offsets or offsets
    if not selected:
        return None
    return {
        **best,
        "median_time_offset_seconds_p1_minus_p2": median(selected),
        "time_offset_range_seconds": [min(selected), max(selected)],
        "time_offset_spread_seconds": max(selected) - min(selected),
    }


def _deduplicate_candidates(
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Count one musical window once even if several discovery buckets surface it."""

    unique: dict[tuple[str, str, float, float], dict[str, Any]] = {}
    for item in candidates:
        window = item["window"]
        key = (
            str(item["recipe"]),
            str(item["song"]),
            round(float(window[0]), 6),
            round(float(window[1]), 6),
        )
        group = str(item["source_group"])
        if key not in unique:
            clean = dict(item)
            clean["source_groups"] = [group]
            unique[key] = clean
            continue
        groups = unique[key].setdefault("source_groups", [])
        if group not in groups:
            groups.append(group)
            groups.sort()
    return list(unique.values())


def extract_pulse_recipe_candidates(
    window_casebook: dict[str, Any],
) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []

    for group_name, items in window_casebook.get("groups", {}).items():
        for item in items:
            local = item["selected_window"]
            sync = float(local["synchronized_onset_ratio"])
            overlap = float(local["active_overlap_ratio"])
            density_corr = local.get("density_correlation")
            intervals = [
                int(value)
                for value in local.get("signed_interval_sequence_semitones", [])
            ]
            runs = _interval_runs(intervals)

            if sync >= 0.90 and intervals:
                counts = Counter(intervals)
                dominant_interval, dominant_count = counts.most_common(1)[0]
                longest = max(runs, key=lambda run: run["length"])
                if longest["length"] >= 6:
                    candidates.append({
                        "recipe": "parallel_interval_lock",
                        "status": "candidate",
                        "source_group": group_name,
                        "song": item["name"],
                        "window": [local["start_seconds"], local["end_seconds"]],
                        "evidence": {
                            "sync_ratio": sync,
                            "overlap_ratio": overlap,
                            "dominant_interval_semitones": dominant_interval,
                            "dominant_interval_ratio": dominant_count / len(intervals),
                            "longest_constant_interval_run": longest,
                            "interval_runs": runs,
                        },
                        "recipe_hint": (
                            "Give P2 the same onset grid as P1 and preserve one harmonic interval "
                            "for a phrase-sized run; change the interval only at a deliberate boundary."
                        ),
                    })

                long_runs = [run for run in runs if run["length"] >= 4]
                distinct_long = {
                    run["interval_semitones"] for run in long_runs
                }
                if len(long_runs) >= 2 and len(distinct_long) >= 2:
                    candidates.append({
                        "recipe": "parallel_interval_block_switch",
                        "status": "candidate",
                        "source_group": group_name,
                        "song": item["name"],
                        "window": [local["start_seconds"], local["end_seconds"]],
                        "evidence": {
                            "sync_ratio": sync,
                            "overlap_ratio": overlap,
                            "long_interval_runs": long_runs,
                        },
                        "recipe_hint": (
                            "Keep the pulse pair rhythmically locked, but switch the fixed interval "
                            "between phrase blocks instead of transposing P2 by one interval forever."
                        ),
                    })

            if sync <= 0.10 and overlap >= 0.90:
                phase = _phase_match(item.get("onset_rows", []))
                motion = _best_lagged_match(
                    [
                        int(value)
                        for value in local.get(
                            "pulse_1_motion_sequence_semitones", []
                        )
                    ],
                    [
                        int(value)
                        for value in local.get(
                            "pulse_2_motion_sequence_semitones", []
                        )
                    ],
                    max_lag=4,
                    min_pairs=8,
                )
                if phase is not None and float(phase["match_ratio"]) >= 0.90:
                    candidates.append({
                        "recipe": "phase_shifted_riff_interlock",
                        "status": "candidate",
                        "source_group": group_name,
                        "song": item["name"],
                        "window": [local["start_seconds"], local["end_seconds"]],
                        "evidence": {
                            "sync_ratio": sync,
                            "overlap_ratio": overlap,
                            "pitch_sequence_alignment": phase,
                            "motion_sequence_alignment": motion,
                        },
                        "recipe_hint": (
                            "Reuse or closely imitate the same riff in both pulse voices, but offset "
                            "one voice by a stable rhythmic phase so their onsets interleave."
                        ),
                    })

            if density_corr is not None and float(density_corr) <= -0.45:
                candidates.append({
                    "recipe": "density_tradeoff_texture",
                    "status": "needs_multiscale_validation",
                    "source_group": group_name,
                    "song": item["name"],
                    "window": [local["start_seconds"], local["end_seconds"]],
                    "evidence": {
                        "sync_ratio": sync,
                        "overlap_ratio": overlap,
                        "local_density_correlation": float(density_corr),
                        "density_bins": local.get("density_bins"),
                    },
                    "recipe_hint": (
                        "Candidate behavior: raise one pulse voice's onset density while the other "
                        "relaxes. Validate at several window sizes before using as a durable rule."
                    ),
                })

    candidates = _deduplicate_candidates(candidates)
    counts = Counter(item["recipe"] for item in candidates)
    return {
        "candidate_counts": dict(sorted(counts.items())),
        "candidates": candidates,
        "interpretation_note": (
            "These recipes are automatically extracted hypotheses from cleaned composition windows. "
            "Duplicate evidence surfaced by multiple discovery buckets is counted once. "
            "Listening and broader-corpus validation are required before promotion to SKILL/reference rules."
        ),
    }


def render_recipe_candidates_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Pulse Recipe Candidates",
        "",
        "> Automatically extracted hypotheses from the cleaned composition view. Not final rules.",
        "",
    ]
    for recipe, count in result.get("candidate_counts", {}).items():
        lines.append(f"- `{recipe}`: {count} unique evidence cases")
    lines.append("")

    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in result.get("candidates", []):
        grouped.setdefault(item["recipe"], []).append(item)

    for recipe, items in grouped.items():
        lines.extend([f"## {recipe}", ""])
        if items:
            lines.extend([items[0]["recipe_hint"], ""])
        for item in items:
            evidence = item["evidence"]
            window = item["window"]
            groups = ", ".join(item.get("source_groups", []))
            lines.append(
                f"- `{item['song']}` `{window[0]:.3f}–{window[1]:.3f}s` "
                f"status=`{item['status']}` discovery=`{groups}`"
            )
            if recipe == "parallel_interval_lock":
                run = evidence["longest_constant_interval_run"]
                lines.append(
                    f"  - sync={evidence['sync_ratio']:.3f}, overlap={evidence['overlap_ratio']:.3f}, "
                    f"dominant={evidence['dominant_interval_semitones']:+d}st "
                    f"({evidence['dominant_interval_ratio']:.3f}), longest run="
                    f"{run['interval_semitones']:+d}st × {run['length']}"
                )
            elif recipe == "parallel_interval_block_switch":
                runs = ", ".join(
                    f"{run['interval_semitones']:+d}st×{run['length']}"
                    for run in evidence["long_interval_runs"]
                )
                lines.append(f"  - long runs: {runs}")
            elif recipe == "phase_shifted_riff_interlock":
                phase = evidence["pitch_sequence_alignment"]
                lines.append(
                    f"  - sync={evidence['sync_ratio']:.3f}, overlap={evidence['overlap_ratio']:.3f}, "
                    f"pitch match={phase['match_ratio']:.3f} over {phase['compared_pairs']} pairs, "
                    f"event lag={phase['lag_events']:+d}, median P1-P2 offset="
                    f"{phase['median_time_offset_seconds_p1_minus_p2']:+.6f}s, "
                    f"spread={phase['time_offset_spread_seconds']:.6f}s"
                )
            elif recipe == "density_tradeoff_texture":
                lines.append(
                    f"  - local density correlation={evidence['local_density_correlation']:.3f}, "
                    f"sync={evidence['sync_ratio']:.3f}, overlap={evidence['overlap_ratio']:.3f}"
                )
        lines.append("")
    return "\n".join(lines)
