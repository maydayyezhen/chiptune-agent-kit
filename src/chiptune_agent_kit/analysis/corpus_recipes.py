from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable

from .nes_midi import NoteSpan, extract_nes_note_spans
from .note_hygiene import filter_composition_spans
from .pulse_windows import analyze_pulse_window, build_onset_rows
from .recipe_candidates import _interval_runs, _phase_match

RECIPE_NAMES = (
    "parallel_interval_lock",
    "parallel_interval_block_switch",
    "phase_shifted_riff_interlock",
    "density_tradeoff_texture",
)

PHASE_FRACTION_TARGETS = (0.25, 1 / 3, 0.5, 2 / 3, 0.75, 1.0, 1.5, 2.0)


def _window_starts(duration_seconds: float, window_seconds: float, step_seconds: float) -> list[float]:
    if duration_seconds <= 0:
        return []
    if duration_seconds <= window_seconds:
        return [0.0]
    last = max(0.0, duration_seconds - window_seconds)
    starts: list[float] = []
    value = 0.0
    while value < last:
        starts.append(value)
        value += step_seconds
    starts.append(last)
    return starts


def _safe_median(values: Iterable[float]) -> float | None:
    items = list(values)
    return median(items) if items else None


def _safe_mean(values: Iterable[float]) -> float | None:
    items = list(values)
    return mean(items) if items else None


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    index = (len(ordered) - 1) * fraction
    low = int(index)
    high = min(low + 1, len(ordered) - 1)
    weight = index - low
    return ordered[low] * (1.0 - weight) + ordered[high] * weight


def _summary(values: Iterable[float]) -> dict[str, float | int | None]:
    items = list(values)
    return {
        "count": len(items),
        "mean": _safe_mean(items),
        "median": _safe_median(items),
        "p25": _percentile(items, 0.25),
        "p75": _percentile(items, 0.75),
        "min": min(items) if items else None,
        "max": max(items) if items else None,
    }


def _voice_ioi(spans: list[NoteSpan], start: float, end: float) -> list[float]:
    onsets = sorted(span.start_seconds for span in spans if start <= span.start_seconds < end)
    return [right - left for left, right in zip(onsets, onsets[1:]) if right > left]


def _nearest_phase_fraction(value: float | None) -> str | None:
    if value is None:
        return None
    nearest = min(PHASE_FRACTION_TARGETS, key=lambda target: abs(target - value))
    labels = {
        0.25: "1/4",
        1 / 3: "1/3",
        0.5: "1/2",
        2 / 3: "2/3",
        0.75: "3/4",
        1.0: "1",
        1.5: "3/2",
        2.0: "2",
    }
    return labels[nearest]


def _density_multiscale(
    pulse_1: list[NoteSpan],
    pulse_2: list[NoteSpan],
    *,
    center_seconds: float,
    song_duration_seconds: float,
    scales_seconds: tuple[float, ...],
    density_bin_seconds: float,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    seen_bounds: set[tuple[float, float]] = set()
    for requested in scales_seconds:
        actual = min(float(requested), song_duration_seconds)
        if actual <= density_bin_seconds * 2:
            continue
        start = max(0.0, center_seconds - actual / 2.0)
        if start + actual > song_duration_seconds:
            start = max(0.0, song_duration_seconds - actual)
        end = min(song_duration_seconds, start + actual)
        bounds = (round(start, 9), round(end, 9))
        if bounds in seen_bounds:
            continue
        seen_bounds.add(bounds)
        local = analyze_pulse_window(
            pulse_1,
            pulse_2,
            start,
            end,
            density_bin_seconds=density_bin_seconds,
        )
        corr = local.get("density_correlation")
        rows.append(
            {
                "requested_window_seconds": requested,
                "actual_window_seconds": end - start,
                "correlation": corr,
                "pulse_1_onsets": local["note_counts"]["pulse_1"],
                "pulse_2_onsets": local["note_counts"]["pulse_2"],
            }
        )

    correlations = [float(row["correlation"]) for row in rows if row["correlation"] is not None]
    negative = [value for value in correlations if value <= -0.30]
    strongly_negative = [value for value in correlations if value <= -0.45]
    validated = len(correlations) >= 2 and len(negative) >= 2 and bool(strongly_negative)
    return {
        "validated": validated,
        "scales": rows,
        "median_correlation": _safe_median(correlations),
        "negative_scale_count": len(negative),
        "strong_negative_scale_count": len(strongly_negative),
    }


def detect_window_recipes(
    pulse_1: list[NoteSpan],
    pulse_2: list[NoteSpan],
    *,
    start_seconds: float,
    end_seconds: float,
    song_duration_seconds: float,
    onset_tolerance_seconds: float = 0.005,
    density_bin_seconds: float = 0.5,
    density_scales_seconds: tuple[float, ...] = (4.0, 8.0, 16.0),
) -> list[dict[str, Any]]:
    local = analyze_pulse_window(
        pulse_1,
        pulse_2,
        start_seconds,
        end_seconds,
        onset_tolerance_seconds=onset_tolerance_seconds,
        density_bin_seconds=density_bin_seconds,
    )
    counts = local["note_counts"]
    if counts["pulse_1"] < 2 or counts["pulse_2"] < 2:
        return []

    sync = float(local["synchronized_onset_ratio"])
    overlap = float(local["active_overlap_ratio"])
    density_corr = local.get("density_correlation")
    intervals = [int(value) for value in local.get("signed_interval_sequence_semitones", [])]
    runs = _interval_runs(intervals)
    output: list[dict[str, Any]] = []

    if sync >= 0.90 and intervals:
        histogram = Counter(intervals)
        dominant_interval, dominant_count = histogram.most_common(1)[0]
        longest = max(runs, key=lambda run: run["length"])
        if longest["length"] >= 6:
            output.append(
                {
                    "recipe": "parallel_interval_lock",
                    "window": [start_seconds, end_seconds],
                    "evidence": {
                        "sync_ratio": sync,
                        "overlap_ratio": overlap,
                        "dominant_interval_semitones": dominant_interval,
                        "dominant_interval_ratio": dominant_count / len(intervals),
                        "longest_constant_interval_run": longest,
                    },
                }
            )

        long_runs = [run for run in runs if run["length"] >= 4]
        if len(long_runs) >= 2 and len({run["interval_semitones"] for run in long_runs}) >= 2:
            output.append(
                {
                    "recipe": "parallel_interval_block_switch",
                    "window": [start_seconds, end_seconds],
                    "evidence": {
                        "sync_ratio": sync,
                        "overlap_ratio": overlap,
                        "long_interval_runs": long_runs,
                    },
                }
            )

    if sync <= 0.10 and overlap >= 0.90:
        rows = build_onset_rows(
            pulse_1,
            pulse_2,
            start_seconds,
            end_seconds,
            onset_tolerance_seconds=onset_tolerance_seconds,
        )
        phase = _phase_match(rows)
        if phase is not None and float(phase["match_ratio"]) >= 0.90:
            ioi = _safe_median(
                _voice_ioi(pulse_1, start_seconds, end_seconds)
                + _voice_ioi(pulse_2, start_seconds, end_seconds)
            )
            signed_offset = float(phase["median_time_offset_seconds_p1_minus_p2"])
            fraction = abs(signed_offset) / ioi if ioi and ioi > 0 else None
            output.append(
                {
                    "recipe": "phase_shifted_riff_interlock",
                    "window": [start_seconds, end_seconds],
                    "evidence": {
                        "sync_ratio": sync,
                        "overlap_ratio": overlap,
                        "pitch_match_ratio": float(phase["match_ratio"]),
                        "compared_pairs": int(phase["compared_pairs"]),
                        "event_lag": int(phase["lag_events"]),
                        "median_time_offset_seconds_p1_minus_p2": signed_offset,
                        "time_offset_spread_seconds": float(phase["time_offset_spread_seconds"]),
                        "median_voice_ioi_seconds": ioi,
                        "absolute_phase_fraction_of_median_voice_ioi": fraction,
                        "nearest_simple_phase_fraction": _nearest_phase_fraction(fraction),
                    },
                }
            )

    if density_corr is not None and float(density_corr) <= -0.45:
        multiscale = _density_multiscale(
            pulse_1,
            pulse_2,
            center_seconds=(start_seconds + end_seconds) / 2.0,
            song_duration_seconds=song_duration_seconds,
            scales_seconds=density_scales_seconds,
            density_bin_seconds=density_bin_seconds,
        )
        if multiscale["validated"]:
            output.append(
                {
                    "recipe": "density_tradeoff_texture",
                    "window": [start_seconds, end_seconds],
                    "evidence": {
                        "sync_ratio": sync,
                        "overlap_ratio": overlap,
                        "base_density_correlation": float(density_corr),
                        "multiscale": multiscale,
                    },
                }
            )

    return output


def _merge_recipe_windows(candidates: list[dict[str, Any]], step_seconds: float) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in candidates:
        grouped[item["recipe"]].append(item)

    episodes: list[dict[str, Any]] = []
    for recipe, items in grouped.items():
        ordered = sorted(items, key=lambda item: (item["window"][0], item["window"][1]))
        current: list[dict[str, Any]] = []
        current_start = 0.0
        current_end = 0.0
        for item in ordered:
            start, end = map(float, item["window"])
            if not current:
                current = [item]
                current_start = start
                current_end = end
                continue
            if start <= current_end + step_seconds * 0.25:
                current.append(item)
                current_end = max(current_end, end)
                continue
            episodes.append(
                {
                    "recipe": recipe,
                    "start_seconds": current_start,
                    "end_seconds": current_end,
                    "duration_seconds": current_end - current_start,
                    "window_hits": len(current),
                    "evidence_windows": current,
                }
            )
            current = [item]
            current_start = start
            current_end = end
        if current:
            episodes.append(
                {
                    "recipe": recipe,
                    "start_seconds": current_start,
                    "end_seconds": current_end,
                    "duration_seconds": current_end - current_start,
                    "window_hits": len(current),
                    "evidence_windows": current,
                }
            )
    return episodes


def scan_song_for_recipes(
    path: str | Path,
    *,
    micro_note_floor_seconds: float = 0.001,
    window_seconds: float = 6.0,
    step_seconds: float = 3.0,
    onset_tolerance_seconds: float = 0.005,
    density_bin_seconds: float = 0.5,
    density_scales_seconds: tuple[float, ...] = (4.0, 8.0, 16.0),
) -> dict[str, Any]:
    midi_path = Path(path)
    raw = extract_nes_note_spans(midi_path)
    pulse_1 = filter_composition_spans(
        raw["pulse_1"],
        drop_duration_at_or_below_seconds=micro_note_floor_seconds,
    )
    pulse_2 = filter_composition_spans(
        raw["pulse_2"],
        drop_duration_at_or_below_seconds=micro_note_floor_seconds,
    )
    duration = max([span.end_seconds for voice in raw.values() for span in voice] or [0.0])

    candidates: list[dict[str, Any]] = []
    windows_scanned = 0
    if pulse_1 and pulse_2:
        for start in _window_starts(duration, window_seconds, step_seconds):
            end = min(duration, start + window_seconds)
            if end - start <= 0:
                continue
            windows_scanned += 1
            candidates.extend(
                detect_window_recipes(
                    pulse_1,
                    pulse_2,
                    start_seconds=start,
                    end_seconds=end,
                    song_duration_seconds=duration,
                    onset_tolerance_seconds=onset_tolerance_seconds,
                    density_bin_seconds=density_bin_seconds,
                    density_scales_seconds=density_scales_seconds,
                )
            )

    episodes = _merge_recipe_windows(candidates, step_seconds)
    return {
        "source": str(midi_path),
        "name": midi_path.name,
        "duration_seconds": duration,
        "clean_note_counts": {"pulse_1": len(pulse_1), "pulse_2": len(pulse_2)},
        "windows_scanned": windows_scanned,
        "recipes_present": sorted({item["recipe"] for item in candidates}),
        "candidates": candidates,
        "episodes": episodes,
    }


def _cooccurrence(songs: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for song in songs:
        recipes = sorted(song["recipes_present"])
        for index, left in enumerate(recipes):
            for right in recipes[index + 1 :]:
                counts[f"{left} + {right}"] += 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def summarize_corpus_scan(songs: list[dict[str, Any]], files_found: int) -> dict[str, Any]:
    two_pulse = [
        song
        for song in songs
        if song["clean_note_counts"]["pulse_1"] > 0 and song["clean_note_counts"]["pulse_2"] > 0
    ]
    recipe_summary: dict[str, Any] = {}

    for recipe in RECIPE_NAMES:
        songs_with = [song for song in two_pulse if recipe in song["recipes_present"]]
        windows = [
            item
            for song in songs_with
            for item in song["candidates"]
            if item["recipe"] == recipe
        ]
        episodes = [
            episode
            for song in songs_with
            for episode in song["episodes"]
            if episode["recipe"] == recipe
        ]
        block: dict[str, Any] = {
            "songs": len(songs_with),
            "prevalence_of_two_pulse_songs": len(songs_with) / len(two_pulse) if two_pulse else 0.0,
            "window_hits": len(windows),
            "episodes": len(episodes),
            "episode_duration_seconds": _summary(
                float(episode["duration_seconds"]) for episode in episodes
            ),
        }

        if recipe == "parallel_interval_lock":
            interval_windows = Counter(
                int(item["evidence"]["dominant_interval_semitones"])
                for item in windows
            )
            interval_songs: dict[int, set[str]] = defaultdict(set)
            for song in songs_with:
                for item in song["candidates"]:
                    if item["recipe"] == recipe:
                        interval_songs[int(item["evidence"]["dominant_interval_semitones"])].add(song["name"])
            block["dominant_interval_window_histogram_semitones"] = {
                str(key): value for key, value in sorted(interval_windows.items())
            }
            block["songs_exhibiting_interval_semitones"] = {
                str(key): len(value) for key, value in sorted(interval_songs.items())
            }

        elif recipe == "parallel_interval_block_switch":
            transitions: Counter[str] = Counter()
            for item in windows:
                runs = item["evidence"]["long_interval_runs"]
                for left, right in zip(runs, runs[1:]):
                    transitions[f"{int(left['interval_semitones']):+d}->{int(right['interval_semitones']):+d}"] += 1
            block["interval_block_transition_histogram"] = dict(
                sorted(transitions.items(), key=lambda item: (-item[1], item[0]))
            )

        elif recipe == "phase_shifted_riff_interlock":
            evidence = [item["evidence"] for item in windows]
            fractions = [
                float(value)
                for item in evidence
                if (value := item.get("absolute_phase_fraction_of_median_voice_ioi")) is not None
            ]
            fraction_labels = Counter(
                str(item["nearest_simple_phase_fraction"])
                for item in evidence
                if item.get("nearest_simple_phase_fraction") is not None
            )
            block["signed_time_offset_seconds"] = _summary(
                float(item["median_time_offset_seconds_p1_minus_p2"]) for item in evidence
            )
            block["absolute_phase_fraction_of_median_voice_ioi"] = _summary(fractions)
            block["nearest_simple_phase_fraction_histogram"] = dict(
                sorted(fraction_labels.items(), key=lambda item: (-item[1], item[0]))
            )
            block["event_lag_histogram"] = {
                str(key): value
                for key, value in sorted(Counter(int(item["event_lag"]) for item in evidence).items())
            }
            block["pitch_match_ratio"] = _summary(float(item["pitch_match_ratio"]) for item in evidence)
            block["time_offset_spread_seconds"] = _summary(
                float(item["time_offset_spread_seconds"]) for item in evidence
            )

        elif recipe == "density_tradeoff_texture":
            evidence = [item["evidence"] for item in windows]
            block["base_density_correlation"] = _summary(
                float(item["base_density_correlation"]) for item in evidence
            )
            block["multiscale_median_correlation"] = _summary(
                float(item["multiscale"]["median_correlation"])
                for item in evidence
                if item["multiscale"]["median_correlation"] is not None
            )

        recipe_summary[recipe] = block

    return {
        "files_found": files_found,
        "songs_scanned": len(songs),
        "songs_with_both_clean_pulses": len(two_pulse),
        "total_windows_scanned": sum(int(song["windows_scanned"]) for song in songs),
        "recipes": recipe_summary,
        "recipe_cooccurrence_song_counts": _cooccurrence(two_pulse),
    }


def render_corpus_scan_markdown(report: dict[str, Any], *, top_examples: int = 8) -> str:
    parameters = report["parameters"]
    summary = report["summary"]
    lines = [
        "# NES-MDB Full-Corpus Pulse Recipe Scan",
        "",
        "> Corpus measurements from the cleaned composition view. Detector hits are evidence, not universal composition laws.",
        "",
        f"- files found: `{summary['files_found']}`",
        f"- songs scanned: `{summary['songs_scanned']}`",
        f"- songs with both clean pulse voices: `{summary['songs_with_both_clean_pulses']}`",
        f"- windows scanned: `{summary['total_windows_scanned']}`",
        f"- micro-note floor: `<= {parameters['micro_note_floor_seconds']} s` removed from composition view",
        f"- base window / step: `{parameters['window_seconds']} s / {parameters['step_seconds']} s`",
        f"- synchronized-onset tolerance: `{parameters['onset_tolerance_seconds']} s`",
        f"- density validation scales: `{parameters['density_scales_seconds']}`",
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
    lines.extend([
        "",
        "## Parallel interval lock",
        "",
        "Songs exhibiting each dominant interval (a song may contribute to more than one interval):",
        "",
    ])
    for interval, count in sorted(
        lock.get("songs_exhibiting_interval_semitones", {}).items(),
        key=lambda item: (-item[1], int(item[0])),
    )[:16]:
        lines.append(f"- `{int(interval):+d} st`: {count} songs")

    switch = summary["recipes"]["parallel_interval_block_switch"]
    lines.extend(["", "## Interval block switches", ""])
    for transition, count in list(switch.get("interval_block_transition_histogram", {}).items())[:16]:
        lines.append(f"- `{transition} st`: {count} window transitions")

    phase = summary["recipes"]["phase_shifted_riff_interlock"]
    lines.extend([
        "",
        "## Phase-shifted riff interlock",
        "",
        "Nearest simple phase fraction relative to the median per-voice onset interval:",
        "",
    ])
    for fraction, count in phase.get("nearest_simple_phase_fraction_histogram", {}).items():
        lines.append(f"- `{fraction}`: {count} window hits")
    fraction_median = phase["absolute_phase_fraction_of_median_voice_ioi"]["median"]
    spread_median = phase["time_offset_spread_seconds"]["median"]
    lines.extend([
        "",
        f"Median absolute phase fraction: `{fraction_median}`",
        f"Median phase-offset spread: `{spread_median}` seconds",
    ])

    density = summary["recipes"]["density_tradeoff_texture"]
    lines.extend([
        "",
        "## Density tradeoff",
        "",
        "This detector is only counted after multi-scale validation (at least two usable scales <= -0.30 correlation and at least one <= -0.45).",
        "",
        f"Median base density correlation: `{density['base_density_correlation']['median']}`",
        f"Median multi-scale correlation: `{density['multiscale_median_correlation']['median']}`",
        "",
        "## Recipe co-occurrence",
        "",
    ])
    cooccurrence = summary.get("recipe_cooccurrence_song_counts", {})
    for pair, count in list(cooccurrence.items())[:16]:
        lines.append(f"- `{pair}`: {count} songs")

    lines.extend(["", "## Representative songs", ""])
    songs = report.get("songs", [])
    for recipe in RECIPE_NAMES:
        matching = [song for song in songs if recipe in song["recipes_present"]]
        matching.sort(
            key=lambda song: sum(
                episode["duration_seconds"]
                for episode in song["episodes"]
                if episode["recipe"] == recipe
            ),
            reverse=True,
        )
        lines.extend([f"### {recipe}", ""])
        for song in matching[:top_examples]:
            durations = [
                episode["duration_seconds"]
                for episode in song["episodes"]
                if episode["recipe"] == recipe
            ]
            lines.append(
                f"- `{song['name']}`: {len(durations)} episode(s), total `{sum(durations):.2f}s`, max `{max(durations):.2f}s`"
            )
        if not matching:
            lines.append("- no detector hits")
        lines.append("")

    lines.extend([
        "## Interpretation guardrail",
        "",
        "Prevalence means the detector found at least one qualifying window in a song. It does not mean the recipe dominates the whole composition. The next promotion gate is listening/A-B composition validation and detector sensitivity checks before any finding becomes a durable SKILL rule.",
        "",
    ])
    return "\n".join(lines)


def scan_corpus(
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
        songs.append(
            scan_song_for_recipes(
                path,
                micro_note_floor_seconds=micro_note_floor_seconds,
                window_seconds=window_seconds,
                step_seconds=step_seconds,
                onset_tolerance_seconds=onset_tolerance_seconds,
                density_bin_seconds=density_bin_seconds,
                density_scales_seconds=density_scales_seconds,
            )
        )
        if progress_every > 0 and (index % progress_every == 0 or index == len(files)):
            print(f"scanned {index}/{len(files)} MIDI files")

    parameters = {
        "micro_note_floor_seconds": micro_note_floor_seconds,
        "window_seconds": window_seconds,
        "step_seconds": step_seconds,
        "onset_tolerance_seconds": onset_tolerance_seconds,
        "density_bin_seconds": density_bin_seconds,
        "density_scales_seconds": list(density_scales_seconds),
    }
    return {
        "parameters": parameters,
        "summary": summarize_corpus_scan(songs, len(files)),
        "songs": songs,
        "interpretation_note": (
            "This is a corpus-wide detector pass over the cleaned composition view. "
            "Keep raw NES-MDB MIDI for sample-level performance and timbre analysis."
        ),
    }
