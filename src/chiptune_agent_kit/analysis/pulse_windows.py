from __future__ import annotations

from collections import Counter
from math import sqrt
from pathlib import Path
from statistics import mean
from typing import Any, Iterable

from .nes_midi import NoteSpan, extract_nes_note_spans

NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


def midi_note_name(pitch: int) -> str:
    return f"{NOTE_NAMES[pitch % 12]}{pitch // 12 - 1}"


def _merged_intervals(intervals: Iterable[tuple[float, float]]) -> list[tuple[float, float]]:
    values = sorted((start, end) for start, end in intervals if end > start)
    if not values:
        return []
    merged: list[tuple[float, float]] = []
    start, end = values[0]
    for next_start, next_end in values[1:]:
        if next_start <= end:
            end = max(end, next_end)
        else:
            merged.append((start, end))
            start, end = next_start, next_end
    merged.append((start, end))
    return merged


def _clipped_intervals(spans: Iterable[NoteSpan], start: float, end: float) -> list[tuple[float, float]]:
    return _merged_intervals(
        (max(start, span.start_seconds), min(end, span.end_seconds))
        for span in spans
        if span.start_seconds < end and span.end_seconds > start
    )


def _duration(intervals: Iterable[tuple[float, float]]) -> float:
    return sum(max(0.0, end - start) for start, end in intervals)


def _overlap_duration(left: list[tuple[float, float]], right: list[tuple[float, float]]) -> float:
    total = 0.0
    i = 0
    j = 0
    while i < len(left) and j < len(right):
        start = max(left[i][0], right[j][0])
        end = min(left[i][1], right[j][1])
        if end > start:
            total += end - start
        if left[i][1] <= right[j][1]:
            i += 1
        else:
            j += 1
    return total


def _onsets_in_window(spans: Iterable[NoteSpan], start: float, end: float) -> list[NoteSpan]:
    return sorted(
        (span for span in spans if start <= span.start_seconds < end),
        key=lambda span: span.start_seconds,
    )


def _pair_onsets(pulse_1: list[NoteSpan], pulse_2: list[NoteSpan], tolerance_seconds: float) -> list[tuple[NoteSpan, NoteSpan]]:
    pairs: list[tuple[NoteSpan, NoteSpan]] = []
    i = 0
    j = 0
    while i < len(pulse_1) and j < len(pulse_2):
        delta = pulse_1[i].start_seconds - pulse_2[j].start_seconds
        if abs(delta) <= tolerance_seconds:
            pairs.append((pulse_1[i], pulse_2[j]))
            i += 1
            j += 1
        elif delta < 0:
            i += 1
        else:
            j += 1
    return pairs


def _pearson(left: list[float], right: list[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    left_mean = mean(left)
    right_mean = mean(right)
    left_dev = [value - left_mean for value in left]
    right_dev = [value - right_mean for value in right]
    numerator = sum(a * b for a, b in zip(left_dev, right_dev))
    denominator = sqrt(sum(value * value for value in left_dev) * sum(value * value for value in right_dev))
    if denominator == 0:
        return None
    return numerator / denominator


def _density_counts(spans: Iterable[NoteSpan], start: float, end: float, bin_seconds: float) -> list[int]:
    if end <= start or bin_seconds <= 0:
        return []
    count = max(1, int((end - start) / bin_seconds + 0.999999))
    buckets = [0] * count
    for span in spans:
        if not (start <= span.start_seconds < end):
            continue
        index = min(int((span.start_seconds - start) / bin_seconds), count - 1)
        buckets[index] += 1
    return buckets


def _motion_sequence(spans: list[NoteSpan]) -> list[int]:
    return [right.pitch - left.pitch for left, right in zip(spans, spans[1:])]


def analyze_pulse_window(
    pulse_1: list[NoteSpan],
    pulse_2: list[NoteSpan],
    start_seconds: float,
    end_seconds: float,
    *,
    onset_tolerance_seconds: float = 0.005,
    density_bin_seconds: float = 0.5,
) -> dict[str, Any]:
    p1_onsets = _onsets_in_window(pulse_1, start_seconds, end_seconds)
    p2_onsets = _onsets_in_window(pulse_2, start_seconds, end_seconds)
    pairs = _pair_onsets(p1_onsets, p2_onsets, onset_tolerance_seconds)

    left_active = _clipped_intervals(pulse_1, start_seconds, end_seconds)
    right_active = _clipped_intervals(pulse_2, start_seconds, end_seconds)
    p1_active = _duration(left_active)
    p2_active = _duration(right_active)
    overlap = _overlap_duration(left_active, right_active)
    union = p1_active + p2_active - overlap

    denominator = min(len(p1_onsets), len(p2_onsets))
    signed_intervals = [right.pitch - left.pitch for left, right in pairs]
    interval_histogram = Counter(signed_intervals)

    p1_density = _density_counts(p1_onsets, start_seconds, end_seconds, density_bin_seconds)
    p2_density = _density_counts(p2_onsets, start_seconds, end_seconds, density_bin_seconds)
    correlation = _pearson([float(value) for value in p1_density], [float(value) for value in p2_density])

    return {
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "duration_seconds": max(0.0, end_seconds - start_seconds),
        "note_counts": {"pulse_1": len(p1_onsets), "pulse_2": len(p2_onsets)},
        "active_overlap_ratio": overlap / union if union > 0 else 0.0,
        "synchronized_pairs": len(pairs),
        "synchronized_onset_ratio": len(pairs) / denominator if denominator else 0.0,
        "signed_interval_sequence_semitones": signed_intervals,
        "signed_interval_histogram_semitones": {str(key): value for key, value in sorted(interval_histogram.items())},
        "pulse_1_motion_sequence_semitones": _motion_sequence(p1_onsets),
        "pulse_2_motion_sequence_semitones": _motion_sequence(p2_onsets),
        "density_correlation": correlation,
        "density_bins": {"bin_seconds": density_bin_seconds, "pulse_1": p1_density, "pulse_2": p2_density},
    }


def build_onset_rows(
    pulse_1: list[NoteSpan],
    pulse_2: list[NoteSpan],
    start_seconds: float,
    end_seconds: float,
    *,
    onset_tolerance_seconds: float = 0.005,
) -> list[dict[str, Any]]:
    left = _onsets_in_window(pulse_1, start_seconds, end_seconds)
    right = _onsets_in_window(pulse_2, start_seconds, end_seconds)
    rows: list[dict[str, Any]] = []
    i = 0
    j = 0

    def row(span: NoteSpan, relation: str, is_p1: bool) -> dict[str, Any]:
        return {
            "time_seconds": span.start_seconds,
            "relative_seconds": span.start_seconds - start_seconds,
            "relation": relation,
            "pulse_1_pitch": span.pitch if is_p1 else None,
            "pulse_1_note": midi_note_name(span.pitch) if is_p1 else None,
            "pulse_1_duration_seconds": span.duration_seconds if is_p1 else None,
            "pulse_2_pitch": None if is_p1 else span.pitch,
            "pulse_2_note": None if is_p1 else midi_note_name(span.pitch),
            "pulse_2_duration_seconds": None if is_p1 else span.duration_seconds,
            "signed_interval_semitones": None,
        }

    while i < len(left) or j < len(right):
        if i < len(left) and j < len(right):
            delta = left[i].start_seconds - right[j].start_seconds
            if abs(delta) <= onset_tolerance_seconds:
                p1 = left[i]
                p2 = right[j]
                rows.append({
                    "time_seconds": min(p1.start_seconds, p2.start_seconds),
                    "relative_seconds": min(p1.start_seconds, p2.start_seconds) - start_seconds,
                    "relation": "sync",
                    "pulse_1_pitch": p1.pitch,
                    "pulse_1_note": midi_note_name(p1.pitch),
                    "pulse_1_duration_seconds": p1.duration_seconds,
                    "pulse_2_pitch": p2.pitch,
                    "pulse_2_note": midi_note_name(p2.pitch),
                    "pulse_2_duration_seconds": p2.duration_seconds,
                    "signed_interval_semitones": p2.pitch - p1.pitch,
                })
                i += 1
                j += 1
                continue
            if delta < 0:
                rows.append(row(left[i], "p1_only", True))
                i += 1
                continue
            rows.append(row(right[j], "p2_only", False))
            j += 1
            continue

        if i < len(left):
            rows.append(row(left[i], "p1_only", True))
            i += 1
        else:
            rows.append(row(right[j], "p2_only", False))
            j += 1

    return rows


def _resolve_midi_path(source: str, name: str, root: str | Path | None) -> Path:
    source_path = Path(source)
    if source_path.exists():
        return source_path
    if root is None:
        raise FileNotFoundError(source)
    root_path = Path(root)
    matches = list(root_path.rglob(name))
    if len(matches) != 1:
        raise FileNotFoundError(f"Expected one MIDI named {name!r} under {root_path}, found {len(matches)}")
    return matches[0]


def _candidate_starts(duration_seconds: float, window_seconds: float, step_seconds: float) -> list[float]:
    if duration_seconds <= window_seconds:
        return [0.0]
    last_start = max(0.0, duration_seconds - window_seconds)
    starts: list[float] = []
    value = 0.0
    while value < last_start:
        starts.append(value)
        value += step_seconds
    starts.append(last_start)
    return starts


def _window_score(group_name: str, local: dict[str, Any], global_case: dict[str, Any]) -> float:
    p1 = local["note_counts"]["pulse_1"]
    p2 = local["note_counts"]["pulse_2"]
    activity = min(1.0, (p1 + p2) / 20.0)
    sync = float(local["synchronized_onset_ratio"])
    overlap = float(local["active_overlap_ratio"])
    corr = local["density_correlation"]

    if group_name == "locked":
        return 0.45 * sync + 0.35 * overlap + 0.20 * activity
    if group_name == "interlocking":
        return 0.45 * overlap + 0.40 * (1.0 - sync) + 0.15 * activity
    if group_name == "density_compensation":
        negative = max(0.0, -(corr if corr is not None else 0.0))
        return 0.55 * negative + 0.25 * overlap + 0.20 * activity

    target_sync = float(global_case.get("sync") or 0.0)
    target_overlap = float(global_case.get("overlap") or 0.0)
    target_corr = global_case.get("density_correlation")
    corr_distance = 0.0
    if corr is not None and target_corr is not None:
        corr_distance = abs(float(corr) - float(target_corr))
    distance = abs(sync - target_sync) + abs(overlap - target_overlap) + 0.5 * corr_distance
    return 0.25 * activity + 0.75 * max(0.0, 1.0 - min(1.0, distance))


def select_representative_window(
    pulse_1: list[NoteSpan],
    pulse_2: list[NoteSpan],
    group_name: str,
    global_case: dict[str, Any],
    *,
    window_seconds: float = 6.0,
    step_seconds: float = 1.0,
    onset_tolerance_seconds: float = 0.005,
    density_bin_seconds: float = 0.5,
    min_onsets_per_voice: int = 2,
) -> dict[str, Any]:
    duration = max([span.end_seconds for span in pulse_1 + pulse_2] or [0.0])
    candidates: list[dict[str, Any]] = []

    for start in _candidate_starts(duration, window_seconds, step_seconds):
        end = min(duration, start + window_seconds)
        local = analyze_pulse_window(
            pulse_1,
            pulse_2,
            start,
            end,
            onset_tolerance_seconds=onset_tolerance_seconds,
            density_bin_seconds=density_bin_seconds,
        )
        counts = local["note_counts"]
        if counts["pulse_1"] < min_onsets_per_voice or counts["pulse_2"] < min_onsets_per_voice:
            continue
        local["selection_score"] = _window_score(group_name, local, global_case)
        candidates.append(local)

    if not candidates:
        local = analyze_pulse_window(
            pulse_1,
            pulse_2,
            0.0,
            duration,
            onset_tolerance_seconds=onset_tolerance_seconds,
            density_bin_seconds=density_bin_seconds,
        )
        local["selection_score"] = _window_score(group_name, local, global_case)
        return local

    return max(candidates, key=lambda item: float(item["selection_score"]))


def build_pulse_window_casebook(
    casebook: dict[str, Any],
    *,
    root: str | Path | None = None,
    window_seconds: float = 6.0,
    step_seconds: float = 1.0,
    onset_tolerance_seconds: float = 0.005,
    density_bin_seconds: float = 0.5,
    max_event_rows: int = 36,
) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for group_name, items in casebook.get("groups", {}).items():
        group_results: list[dict[str, Any]] = []
        for item in items:
            midi_path = _resolve_midi_path(item["source"], item["name"], root)
            spans = extract_nes_note_spans(midi_path)
            local = select_representative_window(
                spans["pulse_1"],
                spans["pulse_2"],
                group_name,
                item,
                window_seconds=window_seconds,
                step_seconds=step_seconds,
                onset_tolerance_seconds=onset_tolerance_seconds,
                density_bin_seconds=density_bin_seconds,
            )
            rows = build_onset_rows(
                spans["pulse_1"],
                spans["pulse_2"],
                local["start_seconds"],
                local["end_seconds"],
                onset_tolerance_seconds=onset_tolerance_seconds,
            )
            group_results.append({
                "name": item["name"],
                "source": str(midi_path),
                "global_case_metrics": item,
                "selected_window": local,
                "event_relation_counts": dict(Counter(row["relation"] for row in rows)),
                "onset_rows": rows[:max_event_rows],
                "onset_rows_truncated": max(0, len(rows) - max_event_rows),
            })
        groups[group_name] = group_results

    return {
        "parameters": {
            "window_seconds": window_seconds,
            "step_seconds": step_seconds,
            "onset_tolerance_seconds": onset_tolerance_seconds,
            "density_bin_seconds": density_bin_seconds,
            "max_event_rows": max_event_rows,
        },
        "groups": groups,
        "interpretation_note": "Representative windows are selected by transparent group-specific scores. The onset tables are measurement artifacts, not composition recipes.",
    }


def _fmt_sequence(values: list[int], limit: int = 18) -> str:
    if not values:
        return "[]"
    shown = values[:limit]
    suffix = ", ..." if len(values) > limit else ""
    return "[" + ", ".join(f"{value:+d}" for value in shown) + suffix + "]"


def render_pulse_window_casebook_markdown(window_casebook: dict[str, Any]) -> str:
    params = window_casebook.get("parameters", {})
    lines = [
        "# Pulse Window Inspection Casebook",
        "",
        "> Local note-level evidence for representative P1/P2 windows. These are observations, not final composition rules.",
        "",
        f"- window: `{params.get('window_seconds')} s`",
        f"- step: `{params.get('step_seconds')} s`",
        f"- onset tolerance: `{params.get('onset_tolerance_seconds')} s`",
        f"- density bin: `{params.get('density_bin_seconds')} s`",
        "",
    ]

    for group_name, items in window_casebook.get("groups", {}).items():
        lines.extend([f"## {group_name}", ""])
        for item in items:
            local = item["selected_window"]
            corr = local["density_correlation"]
            corr_text = "n/a" if corr is None else f"{corr:.3f}"
            lines.extend([
                f"### {item['name']}",
                "",
                f"Window `{local['start_seconds']:.3f}–{local['end_seconds']:.3f}s` | score `{local['selection_score']:.3f}` | sync `{local['synchronized_onset_ratio']:.3f}` | overlap `{local['active_overlap_ratio']:.3f}` | density corr `{corr_text}`",
                "",
                f"P1 onsets `{local['note_counts']['pulse_1']}`, P2 onsets `{local['note_counts']['pulse_2']}`, sync pairs `{local['synchronized_pairs']}`.",
                "",
                f"- synchronized interval sequence: `{_fmt_sequence(local['signed_interval_sequence_semitones'])}`",
                f"- P1 motion sequence: `{_fmt_sequence(local['pulse_1_motion_sequence_semitones'])}`",
                f"- P2 motion sequence: `{_fmt_sequence(local['pulse_2_motion_sequence_semitones'])}`",
                "",
                "| t | P1 | P2 | Δ(P2-P1) | relation |",
                "|---:|---|---|---:|---|",
            ])
            for onset in item["onset_rows"]:
                interval = onset["signed_interval_semitones"]
                interval_text = "" if interval is None else f"{interval:+d}"
                lines.append(f"| {onset['relative_seconds']:.3f} | {onset['pulse_1_note'] or ''} | {onset['pulse_2_note'] or ''} | {interval_text} | {onset['relation']} |")
            if item["onset_rows_truncated"]:
                lines.append(f"| ... | ... | ... | ... | {item['onset_rows_truncated']} additional onset rows omitted |")
            lines.append("")
    return "\n".join(lines)
