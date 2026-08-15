from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable

from .nes_midi import NoteSpan, extract_nes_note_spans
from .note_hygiene import filter_composition_spans


RECIPE_NAMES = (
    "repeated_note_drive",
    "two_register_octave_pump",
    "multi_register_octave_cycle",
    "anchor_return_pattern",
    "directional_step_run",
    "neighbor_oscillation",
)


def _summary(values: Iterable[float]) -> dict[str, float | int | None]:
    items = list(values)
    if not items:
        return {"count": 0, "mean": None, "median": None, "min": None, "max": None}
    return {
        "count": len(items),
        "mean": mean(items),
        "median": median(items),
        "min": min(items),
        "max": max(items),
    }


def _window_starts(duration: float, window: float, step: float) -> list[float]:
    if duration <= 0:
        return []
    if duration <= window:
        return [0.0]
    last = max(0.0, duration - window)
    starts: list[float] = []
    value = 0.0
    while value < last:
        starts.append(value)
        value += step
    starts.append(last)
    return starts


def _longest_transition_run(intervals: list[int], allowed) -> int:
    best = 0
    current = 0
    for interval in intervals:
        if allowed(interval):
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best + 1 if best else 0


def _window_metrics(spans: list[NoteSpan], start: float, end: float) -> dict[str, Any]:
    local = [s for s in spans if start <= s.start_seconds < end]
    local.sort(key=lambda s: (s.start_seconds, s.pitch, s.end_seconds))
    pitches = [s.pitch for s in local]
    intervals = [b - a for a, b in zip(pitches, pitches[1:])]
    transitions = len(intervals)
    counts = Counter(pitches)
    dominant_pitch, dominant_count = counts.most_common(1)[0] if counts else (None, 0)
    repeat_ratio = sum(i == 0 for i in intervals) / transitions if transitions else 0.0
    octave_ratio = sum(abs(i) == 12 for i in intervals) / transitions if transitions else 0.0
    step_ratio = sum(abs(i) in (1, 2) for i in intervals) / transitions if transitions else 0.0
    unique = sorted(set(pitches))

    anchor_returns = 0
    if dominant_pitch is not None:
        for a, b, c in zip(pitches, pitches[1:], pitches[2:]):
            if a == dominant_pitch and b != dominant_pitch and c == dominant_pitch:
                anchor_returns += 1

    positive_step_run = _longest_transition_run(intervals, lambda i: i in (1, 2))
    negative_step_run = _longest_transition_run(intervals, lambda i: i in (-1, -2))

    neighbor_switches = 0
    if len(unique) == 2 and 1 <= abs(unique[1] - unique[0]) <= 2:
        neighbor_switches = sum(a != b for a, b in zip(pitches, pitches[1:]))

    return {
        "window": [start, end],
        "note_count": len(pitches),
        "pitch_sequence": pitches,
        "interval_sequence": intervals,
        "unique_pitches": unique,
        "dominant_pitch": dominant_pitch,
        "dominant_pitch_ratio": dominant_count / len(pitches) if pitches else 0.0,
        "repeat_ratio": repeat_ratio,
        "octave_ratio": octave_ratio,
        "step_ratio": step_ratio,
        "anchor_return_count": anchor_returns,
        "anchor_return_triplet_ratio": anchor_returns / max(1, len(pitches) - 2),
        "longest_positive_step_run_notes": positive_step_run,
        "longest_negative_step_run_notes": negative_step_run,
        "neighbor_switch_ratio": neighbor_switches / transitions if transitions else 0.0,
    }


def detect_triangle_recipes(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    if metrics["note_count"] < 6:
        return []
    pitches = metrics["pitch_sequence"]
    unique = metrics["unique_pitches"]
    output: list[dict[str, Any]] = []

    if metrics["repeat_ratio"] >= 0.70:
        output.append({
            "recipe": "repeated_note_drive",
            "window": metrics["window"],
            "evidence": {
                "repeat_ratio": metrics["repeat_ratio"],
                "dominant_pitch_ratio": metrics["dominant_pitch_ratio"],
            },
        })

    same_pc = bool(unique) and len({pitch % 12 for pitch in unique}) == 1
    if len(unique) == 2 and same_pc and abs(unique[1] - unique[0]) == 12 and metrics["octave_ratio"] >= 0.75:
        output.append({
            "recipe": "two_register_octave_pump",
            "window": metrics["window"],
            "evidence": {
                "octave_ratio": metrics["octave_ratio"],
                "registers": unique,
            },
        })
    elif len(unique) >= 3 and same_pc and metrics["octave_ratio"] >= 0.75:
        output.append({
            "recipe": "multi_register_octave_cycle",
            "window": metrics["window"],
            "evidence": {
                "octave_ratio": metrics["octave_ratio"],
                "registers": unique,
            },
        })

    if (
        0.50 <= metrics["dominant_pitch_ratio"] <= 0.80
        and metrics["repeat_ratio"] < 0.70
        and metrics["anchor_return_count"] >= 2
        and metrics["anchor_return_triplet_ratio"] >= 0.20
    ):
        output.append({
            "recipe": "anchor_return_pattern",
            "window": metrics["window"],
            "evidence": {
                "anchor_pitch": metrics["dominant_pitch"],
                "anchor_ratio": metrics["dominant_pitch_ratio"],
                "anchor_return_count": metrics["anchor_return_count"],
                "anchor_return_triplet_ratio": metrics["anchor_return_triplet_ratio"],
            },
        })

    longest_directional = max(
        metrics["longest_positive_step_run_notes"],
        metrics["longest_negative_step_run_notes"],
    )
    if longest_directional >= 5:
        direction = "up" if metrics["longest_positive_step_run_notes"] >= metrics["longest_negative_step_run_notes"] else "down"
        output.append({
            "recipe": "directional_step_run",
            "window": metrics["window"],
            "evidence": {
                "direction": direction,
                "longest_directional_run_notes": longest_directional,
                "step_ratio": metrics["step_ratio"],
            },
        })

    if len(unique) == 2 and 1 <= abs(unique[1] - unique[0]) <= 2 and metrics["neighbor_switch_ratio"] >= 0.75:
        output.append({
            "recipe": "neighbor_oscillation",
            "window": metrics["window"],
            "evidence": {
                "pitches": unique,
                "distance_semitones": abs(unique[1] - unique[0]),
                "switch_ratio": metrics["neighbor_switch_ratio"],
            },
        })

    return output


def _merge(candidates: list[dict[str, Any]], step: float) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in candidates:
        grouped[item["recipe"]].append(item)
    episodes: list[dict[str, Any]] = []
    for recipe, items in grouped.items():
        items.sort(key=lambda x: x["window"][0])
        start = end = None
        hits = 0
        for item in items:
            a, b = map(float, item["window"])
            if start is None:
                start, end, hits = a, b, 1
            elif a <= float(end) + step * 0.25:
                end = max(float(end), b)
                hits += 1
            else:
                episodes.append({"recipe": recipe, "start_seconds": start, "end_seconds": end, "duration_seconds": float(end) - float(start), "window_hits": hits})
                start, end, hits = a, b, 1
        if start is not None:
            episodes.append({"recipe": recipe, "start_seconds": start, "end_seconds": end, "duration_seconds": float(end) - float(start), "window_hits": hits})
    return episodes


def scan_song(path: str | Path, *, floor: float = 0.001, window: float = 8.0, step: float = 4.0) -> dict[str, Any]:
    path = Path(path)
    raw = extract_nes_note_spans(path)
    triangle = filter_composition_spans(raw["triangle"], drop_duration_at_or_below_seconds=floor)
    duration = max([s.end_seconds for voice in raw.values() for s in voice] or [0.0])
    candidates: list[dict[str, Any]] = []
    windows = 0
    if triangle:
        for start in _window_starts(duration, window, step):
            end = min(duration, start + window)
            windows += 1
            candidates.extend(detect_triangle_recipes(_window_metrics(triangle, start, end)))
    return {
        "name": path.name,
        "triangle_notes": len(triangle),
        "windows_scanned": windows,
        "recipes_present": sorted({c["recipe"] for c in candidates}),
        "candidates": candidates,
        "episodes": _merge(candidates, step),
    }


def summarize(songs: list[dict[str, Any]], files_found: int) -> dict[str, Any]:
    triangle_songs = [s for s in songs if s["triangle_notes"] > 0]
    blocks: dict[str, Any] = {}
    for recipe in RECIPE_NAMES:
        songs_with = [s for s in triangle_songs if recipe in s["recipes_present"]]
        candidates = [c for s in songs_with for c in s["candidates"] if c["recipe"] == recipe]
        episodes = [e for s in songs_with for e in s["episodes"] if e["recipe"] == recipe]
        blocks[recipe] = {
            "songs": len(songs_with),
            "prevalence": len(songs_with) / len(triangle_songs) if triangle_songs else 0.0,
            "window_hits": len(candidates),
            "episodes": len(episodes),
            "episode_duration_seconds": _summary(float(e["duration_seconds"]) for e in episodes),
        }
    co: Counter[str] = Counter()
    for song in triangle_songs:
        names = song["recipes_present"]
        for i, left in enumerate(names):
            for right in names[i + 1:]:
                co[f"{left} + {right}"] += 1
    return {
        "files_found": files_found,
        "songs_scanned": len(songs),
        "songs_with_triangle": len(triangle_songs),
        "windows_scanned": sum(s["windows_scanned"] for s in songs),
        "recipes": blocks,
        "cooccurrence": dict(co.most_common()),
    }


def render_markdown(report: dict[str, Any]) -> str:
    s = report["summary"]
    lines = [
        "# Refined Triangle Recipe Candidate Scan",
        "",
        "> Full-corpus composition-view detector pass. These remain candidates until listening/A-B validation.",
        "",
        f"- files: `{s['files_found']}`",
        f"- Triangle songs: `{s['songs_with_triangle']}`",
        f"- windows: `{s['windows_scanned']}`",
        "",
        "| recipe | songs | prevalence | episodes | median episode |",
        "|---|---:|---:|---:|---:|",
    ]
    for recipe in RECIPE_NAMES:
        b = s["recipes"][recipe]
        med = b["episode_duration_seconds"]["median"]
        lines.append(f"| `{recipe}` | {b['songs']} | {b['prevalence']:.3%} | {b['episodes']} | {'n/a' if med is None else f'{med:.2f}s'} |")
    lines.extend(["", "## Co-occurrence", ""])
    for pair, count in list(s["cooccurrence"].items())[:16]:
        lines.append(f"- `{pair}`: {count} songs")
    lines.extend(["", "## Guardrail", "", "These detectors describe local note-relationship structures. Triangle is often but not always a bass voice, so do not equate every detected pattern with low-register bass function.", ""])
    return "\n".join(lines)


def scan_corpus(root: str | Path, *, floor: float = 0.001, window: float = 8.0, step: float = 4.0, progress_every: int = 250) -> dict[str, Any]:
    files = sorted(Path(root).rglob("*.mid"))
    songs: list[dict[str, Any]] = []
    for index, path in enumerate(files, start=1):
        songs.append(scan_song(path, floor=floor, window=window, step=step))
        if progress_every and (index % progress_every == 0 or index == len(files)):
            print(f"scanned {index}/{len(files)} MIDI files")
    return {
        "parameters": {"floor": floor, "window": window, "step": step},
        "summary": summarize(songs, len(files)),
        "songs": songs,
    }
