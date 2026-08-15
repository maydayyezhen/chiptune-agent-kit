from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable

from .nes_midi import NoteSpan, extract_nes_note_spans
from .note_hygiene import filter_composition_spans


PATTERN_NAMES = (
    "repeated_note_drive",
    "octave_pump",
    "dominant_pitch_pedal",
    "stepwise_motion",
)


def _safe_mean(values: Iterable[float]) -> float | None:
    items = list(values)
    return mean(items) if items else None


def _safe_median(values: Iterable[float]) -> float | None:
    items = list(values)
    return median(items) if items else None


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


def _longest_run(pitches: list[int], predicate) -> int:
    if not pitches:
        return 0
    best = 1
    current = 1
    for left, right in zip(pitches, pitches[1:]):
        if predicate(left, right):
            current += 1
            best = max(best, current)
        else:
            current = 1
    return best


def analyze_triangle_window(
    spans: list[NoteSpan],
    start_seconds: float,
    end_seconds: float,
) -> dict[str, Any]:
    local = [
        span for span in spans
        if start_seconds <= span.start_seconds < end_seconds
    ]
    local.sort(key=lambda span: (span.start_seconds, span.pitch, span.end_seconds))
    pitches = [span.pitch for span in local]
    intervals = [right - left for left, right in zip(pitches, pitches[1:])]
    transitions = len(intervals)
    pitch_counts = Counter(pitches)
    dominant_pitch, dominant_count = pitch_counts.most_common(1)[0] if pitch_counts else (None, 0)

    repeat_count = sum(interval == 0 for interval in intervals)
    octave_count = sum(abs(interval) == 12 for interval in intervals)
    step_count = sum(abs(interval) in (1, 2) for interval in intervals)
    same_pc_count = sum(interval != 0 and interval % 12 == 0 for interval in intervals)

    return {
        "window": [start_seconds, end_seconds],
        "note_count": len(local),
        "pitch_range": [min(pitches), max(pitches)] if pitches else None,
        "dominant_pitch": dominant_pitch,
        "dominant_pitch_ratio": dominant_count / len(pitches) if pitches else 0.0,
        "repeated_transition_ratio": repeat_count / transitions if transitions else 0.0,
        "octave_transition_ratio": octave_count / transitions if transitions else 0.0,
        "stepwise_transition_ratio": step_count / transitions if transitions else 0.0,
        "same_pitch_class_nonrepeat_ratio": same_pc_count / transitions if transitions else 0.0,
        "longest_repeated_pitch_run_notes": _longest_run(pitches, lambda left, right: left == right),
        "longest_octave_chain_notes": _longest_run(pitches, lambda left, right: abs(right - left) == 12),
        "signed_interval_sequence": intervals,
        "interval_histogram": dict(sorted(Counter(intervals).items())),
    }


def detect_triangle_patterns(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    if int(metrics["note_count"]) < 6:
        return []

    repeat = float(metrics["repeated_transition_ratio"])
    octave = float(metrics["octave_transition_ratio"])
    stepwise = float(metrics["stepwise_transition_ratio"])
    dominant = float(metrics["dominant_pitch_ratio"])
    repeat_run = int(metrics["longest_repeated_pitch_run_notes"])
    octave_run = int(metrics["longest_octave_chain_notes"])
    output: list[dict[str, Any]] = []

    if repeat >= 0.70 and repeat_run >= 5:
        output.append({
            "pattern": "repeated_note_drive",
            "window": metrics["window"],
            "evidence": {
                "repeated_transition_ratio": repeat,
                "longest_repeated_pitch_run_notes": repeat_run,
                "dominant_pitch_ratio": dominant,
            },
        })

    if octave >= 0.65 and octave_run >= 5:
        output.append({
            "pattern": "octave_pump",
            "window": metrics["window"],
            "evidence": {
                "octave_transition_ratio": octave,
                "longest_octave_chain_notes": octave_run,
                "same_pitch_class_nonrepeat_ratio": metrics["same_pitch_class_nonrepeat_ratio"],
            },
        })

    if dominant >= 0.65:
        output.append({
            "pattern": "dominant_pitch_pedal",
            "window": metrics["window"],
            "evidence": {
                "dominant_pitch": metrics["dominant_pitch"],
                "dominant_pitch_ratio": dominant,
                "repeated_transition_ratio": repeat,
            },
        })

    if repeat <= 0.20 and stepwise >= 0.60:
        output.append({
            "pattern": "stepwise_motion",
            "window": metrics["window"],
            "evidence": {
                "stepwise_transition_ratio": stepwise,
                "repeated_transition_ratio": repeat,
                "pitch_range": metrics["pitch_range"],
            },
        })

    return output


def _merge_windows(candidates: list[dict[str, Any]], step_seconds: float) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in candidates:
        grouped[item["pattern"]].append(item)

    episodes: list[dict[str, Any]] = []
    for pattern, items in grouped.items():
        ordered = sorted(items, key=lambda item: item["window"][0])
        current: list[dict[str, Any]] = []
        start = 0.0
        end = 0.0
        for item in ordered:
            item_start, item_end = map(float, item["window"])
            if not current:
                current = [item]
                start = item_start
                end = item_end
                continue
            if item_start <= end + step_seconds * 0.25:
                current.append(item)
                end = max(end, item_end)
            else:
                episodes.append({
                    "pattern": pattern,
                    "start_seconds": start,
                    "end_seconds": end,
                    "duration_seconds": end - start,
                    "window_hits": len(current),
                })
                current = [item]
                start = item_start
                end = item_end
        if current:
            episodes.append({
                "pattern": pattern,
                "start_seconds": start,
                "end_seconds": end,
                "duration_seconds": end - start,
                "window_hits": len(current),
            })
    return episodes


def scan_triangle_song(
    path: str | Path,
    *,
    micro_note_floor_seconds: float = 0.001,
    window_seconds: float = 8.0,
    step_seconds: float = 4.0,
) -> dict[str, Any]:
    midi_path = Path(path)
    raw = extract_nes_note_spans(midi_path)
    triangle = filter_composition_spans(
        raw["triangle"],
        drop_duration_at_or_below_seconds=micro_note_floor_seconds,
    )
    duration = max([span.end_seconds for voice in raw.values() for span in voice] or [0.0])

    windows: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    if triangle:
        for start in _window_starts(duration, window_seconds, step_seconds):
            end = min(duration, start + window_seconds)
            metrics = analyze_triangle_window(triangle, start, end)
            windows.append(metrics)
            candidates.extend(detect_triangle_patterns(metrics))

    return {
        "source": str(midi_path),
        "name": midi_path.name,
        "duration_seconds": duration,
        "clean_triangle_note_count": len(triangle),
        "windows_scanned": len(windows),
        "patterns_present": sorted({item["pattern"] for item in candidates}),
        "candidates": candidates,
        "episodes": _merge_windows(candidates, step_seconds),
    }


def summarize_triangle_corpus(songs: list[dict[str, Any]], files_found: int) -> dict[str, Any]:
    triangle_songs = [song for song in songs if song["clean_triangle_note_count"] > 0]
    patterns: dict[str, Any] = {}

    for pattern in PATTERN_NAMES:
        songs_with = [song for song in triangle_songs if pattern in song["patterns_present"]]
        windows = [
            item for song in songs_with for item in song["candidates"]
            if item["pattern"] == pattern
        ]
        episodes = [
            item for song in songs_with for item in song["episodes"]
            if item["pattern"] == pattern
        ]
        block: dict[str, Any] = {
            "songs": len(songs_with),
            "prevalence_of_triangle_songs": len(songs_with) / len(triangle_songs) if triangle_songs else 0.0,
            "window_hits": len(windows),
            "episodes": len(episodes),
            "episode_duration_seconds": _summary(float(item["duration_seconds"]) for item in episodes),
        }
        if pattern == "repeated_note_drive":
            block["repeated_transition_ratio"] = _summary(
                float(item["evidence"]["repeated_transition_ratio"]) for item in windows
            )
            block["longest_run_notes"] = _summary(
                float(item["evidence"]["longest_repeated_pitch_run_notes"]) for item in windows
            )
        elif pattern == "octave_pump":
            block["octave_transition_ratio"] = _summary(
                float(item["evidence"]["octave_transition_ratio"]) for item in windows
            )
            block["longest_octave_chain_notes"] = _summary(
                float(item["evidence"]["longest_octave_chain_notes"]) for item in windows
            )
        elif pattern == "dominant_pitch_pedal":
            block["dominant_pitch_ratio"] = _summary(
                float(item["evidence"]["dominant_pitch_ratio"]) for item in windows
            )
        elif pattern == "stepwise_motion":
            block["stepwise_transition_ratio"] = _summary(
                float(item["evidence"]["stepwise_transition_ratio"]) for item in windows
            )
        patterns[pattern] = block

    cooccurrence: Counter[str] = Counter()
    for song in triangle_songs:
        names = sorted(song["patterns_present"])
        for index, left in enumerate(names):
            for right in names[index + 1:]:
                cooccurrence[f"{left} + {right}"] += 1

    return {
        "files_found": files_found,
        "songs_scanned": len(songs),
        "songs_with_clean_triangle": len(triangle_songs),
        "total_windows_scanned": sum(int(song["windows_scanned"]) for song in songs),
        "patterns": patterns,
        "pattern_cooccurrence_song_counts": dict(cooccurrence.most_common()),
    }


def render_triangle_markdown(report: dict[str, Any], *, top_examples: int = 8) -> str:
    summary = report["summary"]
    params = report["parameters"]
    lines = [
        "# NES-MDB Full-Corpus Triangle Pattern Scan",
        "",
        "> Exploratory composition-view measurements. Pattern names describe observable note behavior, not harmonic intent.",
        "",
        f"- files found: `{summary['files_found']}`",
        f"- songs scanned: `{summary['songs_scanned']}`",
        f"- songs with clean Triangle notes: `{summary['songs_with_clean_triangle']}`",
        f"- windows scanned: `{summary['total_windows_scanned']}`",
        f"- micro-note floor: `<= {params['micro_note_floor_seconds']} s` removed",
        f"- window / step: `{params['window_seconds']} s / {params['step_seconds']} s`",
        "",
        "## Prevalence",
        "",
        "| pattern | songs | prevalence among Triangle songs | episodes | median episode |",
        "|---|---:|---:|---:|---:|",
    ]
    for pattern in PATTERN_NAMES:
        item = summary["patterns"][pattern]
        med = item["episode_duration_seconds"]["median"]
        lines.append(
            f"| `{pattern}` | {item['songs']} | {item['prevalence_of_triangle_songs']:.3%} | "
            f"{item['episodes']} | {'n/a' if med is None else f'{med:.2f}s'} |"
        )

    lines.extend(["", "## Co-occurrence", ""])
    for pair, count in list(summary["pattern_cooccurrence_song_counts"].items())[:12]:
        lines.append(f"- `{pair}`: {count} songs")

    lines.extend(["", "## Representative songs", ""])
    for pattern in PATTERN_NAMES:
        matching = [song for song in report["songs"] if pattern in song["patterns_present"]]
        matching.sort(
            key=lambda song: sum(
                episode["duration_seconds"] for episode in song["episodes"]
                if episode["pattern"] == pattern
            ),
            reverse=True,
        )
        lines.extend([f"### {pattern}", ""])
        for song in matching[:top_examples]:
            durations = [
                episode["duration_seconds"] for episode in song["episodes"]
                if episode["pattern"] == pattern
            ]
            lines.append(
                f"- `{song['name']}`: {len(durations)} episode(s), total `{sum(durations):.2f}s`, max `{max(durations):.2f}s`"
            )
        lines.append("")

    lines.extend([
        "## Interpretation guardrail",
        "",
        "A hit means at least one local window met the detector threshold. These are discovery buckets, not final bass-style classes. The next gate is representative-window inspection, sensitivity checks, and listening/A-B composition tests before promotion to reusable recipes.",
        "",
    ])
    return "\n".join(lines)


def scan_triangle_corpus(
    root: str | Path,
    *,
    micro_note_floor_seconds: float = 0.001,
    window_seconds: float = 8.0,
    step_seconds: float = 4.0,
    progress_every: int = 250,
) -> dict[str, Any]:
    root_path = Path(root)
    files = sorted(root_path.rglob("*.mid"))
    songs: list[dict[str, Any]] = []
    for index, path in enumerate(files, start=1):
        songs.append(
            scan_triangle_song(
                path,
                micro_note_floor_seconds=micro_note_floor_seconds,
                window_seconds=window_seconds,
                step_seconds=step_seconds,
            )
        )
        if progress_every > 0 and (index % progress_every == 0 or index == len(files)):
            print(f"scanned {index}/{len(files)} MIDI files")

    return {
        "parameters": {
            "micro_note_floor_seconds": micro_note_floor_seconds,
            "window_seconds": window_seconds,
            "step_seconds": step_seconds,
        },
        "summary": summarize_triangle_corpus(songs, len(files)),
        "songs": songs,
        "interpretation_note": "Triangle detectors are exploratory composition-view evidence, not universal NES bass rules.",
    }
