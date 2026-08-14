from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .corpus_recipes import (
    RECIPE_NAMES,
    _merge_recipe_windows,
    _summary,
    scan_song_for_recipes as _scan_song_v1,
    summarize_corpus_scan as _summarize_v1,
)

PHASE_STABILITY_MAX_SPREAD_IOI_RATIO = 0.10
PHASE_SIMPLE_FRACTION_MAX_DISTANCE = 0.03
PHASE_RESIDUAL_TARGETS: tuple[tuple[float, str], ...] = (
    (0.0, "0"),
    (0.125, "1/8"),
    (1.0 / 6.0, "1/6"),
    (0.25, "1/4"),
    (1.0 / 3.0, "1/3"),
    (0.375, "3/8"),
    (0.4, "2/5"),
    (0.5, "1/2"),
)


def _classify_phase_residual(value: float) -> tuple[str, float]:
    nearest_value, label = min(
        PHASE_RESIDUAL_TARGETS,
        key=lambda item: abs(item[0] - value),
    )
    distance = abs(nearest_value - value)
    if distance > PHASE_SIMPLE_FRACTION_MAX_DISTANCE:
        return "other", distance
    return label, distance


def _refine_phase_candidate(item: dict[str, Any]) -> dict[str, Any] | None:
    evidence = dict(item["evidence"])
    ioi = evidence.get("median_voice_ioi_seconds")
    if ioi is None or float(ioi) <= 0:
        return None

    ioi = float(ioi)
    spread_seconds = float(evidence["time_offset_spread_seconds"])
    spread_ratio = spread_seconds / ioi
    if spread_ratio > PHASE_STABILITY_MAX_SPREAD_IOI_RATIO:
        return None

    signed_offset_seconds = float(evidence["median_time_offset_seconds_p1_minus_p2"])
    signed_offset_iois = signed_offset_seconds / ioi
    nearest_integer_iois = round(signed_offset_iois)
    residual_signed = signed_offset_iois - nearest_integer_iois
    residual_abs = abs(residual_signed)
    label, label_distance = _classify_phase_residual(residual_abs)

    evidence.update(
        {
            "phase_stability_spread_ioi_ratio": spread_ratio,
            "signed_time_offset_in_median_voice_iois": signed_offset_iois,
            "nearest_integer_ioi_offset": nearest_integer_iois,
            "residual_phase_fraction_signed": residual_signed,
            "absolute_residual_phase_fraction": residual_abs,
            "simple_residual_phase_fraction": label,
            "simple_residual_phase_fraction_distance": label_distance,
        }
    )

    refined = dict(item)
    refined["evidence"] = evidence
    return refined


def refine_song_scan(song: dict[str, Any], *, step_seconds: float) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    rejected_unstable_phase_windows = 0

    for item in song.get("candidates", []):
        if item["recipe"] != "phase_shifted_riff_interlock":
            candidates.append(item)
            continue
        refined = _refine_phase_candidate(item)
        if refined is None:
            rejected_unstable_phase_windows += 1
            continue
        candidates.append(refined)

    refined_song = dict(song)
    refined_song["candidates"] = candidates
    refined_song["episodes"] = _merge_recipe_windows(candidates, step_seconds)
    refined_song["recipes_present"] = sorted({item["recipe"] for item in candidates})
    refined_song["refinement"] = {
        "rejected_unstable_phase_windows": rejected_unstable_phase_windows,
        "phase_stability_max_spread_ioi_ratio": PHASE_STABILITY_MAX_SPREAD_IOI_RATIO,
    }
    return refined_song


def _harmonic_family(interval_semitones: int) -> str:
    interval_class = abs(interval_semitones) % 12
    if interval_class == 0:
        return "unison_octave"
    if interval_class in {3, 4}:
        return "third_family"
    if interval_class in {5, 7}:
        return "fourth_fifth_family"
    if interval_class == 6:
        return "tritone"
    if interval_class in {8, 9}:
        return "sixth_family"
    if interval_class in {1, 2}:
        return "second_family"
    return "seventh_family"


def summarize_refined_corpus_scan(
    songs: list[dict[str, Any]],
    files_found: int,
) -> dict[str, Any]:
    summary = _summarize_v1(songs, files_found)

    lock_windows = [
        (song["name"], item)
        for song in songs
        for item in song.get("candidates", [])
        if item["recipe"] == "parallel_interval_lock"
    ]
    family_windows: Counter[str] = Counter()
    family_songs: dict[str, set[str]] = defaultdict(set)
    for song_name, item in lock_windows:
        family = _harmonic_family(
            int(item["evidence"]["dominant_interval_semitones"])
        )
        family_windows[family] += 1
        family_songs[family].add(song_name)

    lock_summary = summary["recipes"]["parallel_interval_lock"]
    lock_summary["harmonic_family_window_hits"] = dict(
        sorted(family_windows.items(), key=lambda item: (-item[1], item[0]))
    )
    lock_summary["harmonic_family_song_counts"] = dict(
        sorted(
            ((family, len(song_names)) for family, song_names in family_songs.items()),
            key=lambda item: (-item[1], item[0]),
        )
    )

    switch_windows = [
        item
        for song in songs
        for item in song.get("candidates", [])
        if item["recipe"] == "parallel_interval_block_switch"
    ]
    transitions: Counter[str] = Counter()
    for item in switch_windows:
        runs = item["evidence"]["long_interval_runs"]
        for left, right in zip(runs, runs[1:]):
            left_interval = int(left["interval_semitones"])
            right_interval = int(right["interval_semitones"])
            if left_interval == right_interval:
                continue
            transitions[f"{left_interval:+d}->{right_interval:+d}"] += 1
    summary["recipes"]["parallel_interval_block_switch"][
        "interval_block_transition_histogram"
    ] = dict(sorted(transitions.items(), key=lambda item: (-item[1], item[0])))

    phase_windows = [
        item
        for song in songs
        for item in song.get("candidates", [])
        if item["recipe"] == "phase_shifted_riff_interlock"
    ]
    phase_evidence = [item["evidence"] for item in phase_windows]
    phase_summary = summary["recipes"]["phase_shifted_riff_interlock"]
    phase_summary.pop("absolute_phase_fraction_of_median_voice_ioi", None)
    phase_summary.pop("nearest_simple_phase_fraction_histogram", None)
    phase_summary["phase_stability_max_spread_ioi_ratio"] = (
        PHASE_STABILITY_MAX_SPREAD_IOI_RATIO
    )
    phase_summary["simple_fraction_max_distance_ioi"] = (
        PHASE_SIMPLE_FRACTION_MAX_DISTANCE
    )
    phase_summary["absolute_residual_phase_fraction"] = _summary(
        float(item["absolute_residual_phase_fraction"])
        for item in phase_evidence
    )
    phase_summary["phase_stability_spread_ioi_ratio"] = _summary(
        float(item["phase_stability_spread_ioi_ratio"])
        for item in phase_evidence
    )
    phase_summary["simple_residual_phase_fraction_histogram"] = dict(
        sorted(
            Counter(
                str(item["simple_residual_phase_fraction"])
                for item in phase_evidence
            ).items(),
            key=lambda item: (-item[1], item[0]),
        )
    )
    phase_summary["nearest_integer_ioi_offset_histogram"] = {
        str(key): value
        for key, value in sorted(
            Counter(
                int(item["nearest_integer_ioi_offset"])
                for item in phase_evidence
            ).items()
        )
    }

    summary["refinement"] = {
        "rejected_unstable_phase_windows": sum(
            int(song.get("refinement", {}).get("rejected_unstable_phase_windows", 0))
            for song in songs
        ),
        "phase_stability_max_spread_ioi_ratio": (
            PHASE_STABILITY_MAX_SPREAD_IOI_RATIO
        ),
        "phase_simple_fraction_max_distance_ioi": (
            PHASE_SIMPLE_FRACTION_MAX_DISTANCE
        ),
    }
    return summary


def render_refined_corpus_scan_markdown(
    report: dict[str, Any],
    *,
    top_examples: int = 8,
) -> str:
    parameters = report["parameters"]
    summary = report["summary"]
    lines = [
        "# NES-MDB Full-Corpus Pulse Recipe Scan, Refined",
        "",
        "> Full-corpus measurements from the cleaned composition view. Detector hits are evidence, not universal composition laws.",
        "",
        f"- files found: `{summary['files_found']}`",
        f"- songs scanned: `{summary['songs_scanned']}`",
        f"- songs with both clean pulse voices: `{summary['songs_with_both_clean_pulses']}`",
        f"- windows scanned: `{summary['total_windows_scanned']}`",
        f"- micro-note floor: `<= {parameters['micro_note_floor_seconds']} s` removed from composition view",
        f"- base window / step: `{parameters['window_seconds']} s / {parameters['step_seconds']} s`",
        f"- synchronized-onset tolerance: `{parameters['onset_tolerance_seconds']} s`",
        f"- density validation scales: `{parameters['density_scales_seconds']}`",
        f"- phase stability gate: spread / median voice IOI `<= {PHASE_STABILITY_MAX_SPREAD_IOI_RATIO}`",
        f"- phase simple-fraction label tolerance: `<= {PHASE_SIMPLE_FRACTION_MAX_DISTANCE} IOI`",
        "",
        "## Prevalence",
        "",
        "| recipe | songs | prevalence among two-pulse songs | episodes | median episode |",
        "|---|---:|---:|---:|---:|",
    ]

    for recipe in RECIPE_NAMES:
        item = summary["recipes"][recipe]
        duration = item["episode_duration_seconds"]["median"]
        duration_text = "n/a" if duration is None else f"{duration:.2f}s"
        lines.append(
            f"| `{recipe}` | {item['songs']} | {item['prevalence_of_two_pulse_songs']:.3%} | "
            f"{item['episodes']} | {duration_text} |"
        )

    lock = summary["recipes"]["parallel_interval_lock"]
    lines.extend(
        [
            "",
            "## Parallel interval lock",
            "",
            "Harmonic-family prevalence. A song may contribute to more than one family:",
            "",
        ]
    )
    for family, count in lock.get("harmonic_family_song_counts", {}).items():
        lines.append(f"- `{family}`: {count} songs")

    lines.extend(["", "Most common exact signed intervals:", ""])
    for interval, count in sorted(
        lock.get("songs_exhibiting_interval_semitones", {}).items(),
        key=lambda item: (-item[1], int(item[0])),
    )[:16]:
        lines.append(f"- `{int(interval):+d} st`: {count} songs")

    switch = summary["recipes"]["parallel_interval_block_switch"]
    lines.extend(
        [
            "",
            "## Interval block switches",
            "",
            "Same-to-same long-run pairs are excluded from this transition table.",
            "",
        ]
    )
    for transition, count in list(
        switch.get("interval_block_transition_histogram", {}).items()
    )[:16]:
        lines.append(f"- `{transition} st`: {count} window transitions")

    phase = summary["recipes"]["phase_shifted_riff_interlock"]
    lines.extend(
        [
            "",
            "## Phase-shifted riff interlock",
            "",
            "Whole-IOI event displacement is removed before classifying the remaining phase residue. Only stable windows pass the spread/IOI gate.",
            "",
        ]
    )
    for fraction, count in phase.get(
        "simple_residual_phase_fraction_histogram", {}
    ).items():
        lines.append(f"- `{fraction}` residue: {count} window hits")
    residual = phase["absolute_residual_phase_fraction"]
    stability = phase["phase_stability_spread_ioi_ratio"]
    lines.extend(
        [
            "",
            f"Median absolute residual phase: `{residual['median']}` IOI",
            f"Median spread / IOI: `{stability['median']}`",
            f"Rejected unstable phase windows during refinement: `{summary['refinement']['rejected_unstable_phase_windows']}`",
        ]
    )

    density = summary["recipes"]["density_tradeoff_texture"]
    lines.extend(
        [
            "",
            "## Density tradeoff",
            "",
            "Counted only after multi-scale validation: at least two usable scales <= -0.30 correlation and at least one <= -0.45.",
            "",
            f"Median base density correlation: `{density['base_density_correlation']['median']}`",
            f"Median multi-scale correlation: `{density['multiscale_median_correlation']['median']}`",
            "",
            "## Recipe co-occurrence",
            "",
        ]
    )
    for pair, count in list(
        summary.get("recipe_cooccurrence_song_counts", {}).items()
    )[:16]:
        lines.append(f"- `{pair}`: {count} songs")

    lines.extend(["", "## Representative songs", ""])
    songs = report.get("songs", [])
    for recipe in RECIPE_NAMES:
        matching = [song for song in songs if recipe in song["recipes_present"]]
        matching.sort(
            key=lambda song: sum(
                float(episode["duration_seconds"])
                for episode in song["episodes"]
                if episode["recipe"] == recipe
            ),
            reverse=True,
        )
        lines.extend([f"### {recipe}", ""])
        for song in matching[:top_examples]:
            durations = [
                float(episode["duration_seconds"])
                for episode in song["episodes"]
                if episode["recipe"] == recipe
            ]
            lines.append(
                f"- `{song['name']}`: {len(durations)} episode(s), total `{sum(durations):.2f}s`, max `{max(durations):.2f}s`"
            )
        if not matching:
            lines.append("- no detector hits")
        lines.append("")

    lines.extend(
        [
            "## Interpretation guardrail",
            "",
            "Prevalence means at least one qualifying detector window occurs in a song. It does not mean the recipe dominates the whole piece. Exact signed intervals far outside a normal harmonic register can reflect wide register separation, so harmonic-family summaries should be preferred for recipe design. Promotion to SKILL still requires sensitivity checks and listening/composition A/B tests.",
            "",
        ]
    )
    return "\n".join(lines)


def scan_refined_corpus(
    root: str | Path,
    *,
    micro_note_floor_seconds: float = 0.001,
    window_seconds: float = 6.0,
    step_seconds: float = 3.0,
    onset_tolerance_seconds: float = 0.005,
    density_bin_seconds: float = 0.5,
    density_scales_seconds: tuple[float, ...] = (4.0, 8.0, 16.0),
    progress_every: int = 250,
) -> dict[str, Any]:
    root_path = Path(root)
    files = sorted(root_path.rglob("*.mid"))
    songs: list[dict[str, Any]] = []

    for index, path in enumerate(files, start=1):
        song = _scan_song_v1(
            path,
            micro_note_floor_seconds=micro_note_floor_seconds,
            window_seconds=window_seconds,
            step_seconds=step_seconds,
            onset_tolerance_seconds=onset_tolerance_seconds,
            density_bin_seconds=density_bin_seconds,
            density_scales_seconds=density_scales_seconds,
        )
        songs.append(refine_song_scan(song, step_seconds=step_seconds))
        if progress_every > 0 and (
            index % progress_every == 0 or index == len(files)
        ):
            print(f"scanned {index}/{len(files)} MIDI files")

    parameters = {
        "micro_note_floor_seconds": micro_note_floor_seconds,
        "window_seconds": window_seconds,
        "step_seconds": step_seconds,
        "onset_tolerance_seconds": onset_tolerance_seconds,
        "density_bin_seconds": density_bin_seconds,
        "density_scales_seconds": list(density_scales_seconds),
        "phase_stability_max_spread_ioi_ratio": (
            PHASE_STABILITY_MAX_SPREAD_IOI_RATIO
        ),
        "phase_simple_fraction_max_distance_ioi": (
            PHASE_SIMPLE_FRACTION_MAX_DISTANCE
        ),
    }
    return {
        "parameters": parameters,
        "summary": summarize_refined_corpus_scan(songs, len(files)),
        "songs": songs,
        "interpretation_note": (
            "Full-corpus detector pass over the cleaned composition view. "
            "Phase candidates receive a second stability/residual-phase gate. "
            "Keep raw NES-MDB MIDI for sample-level performance and timbre analysis."
        ),
    }
