from __future__ import annotations

from collections import Counter
from math import sqrt
from pathlib import Path
from statistics import mean
from typing import Any, Iterable

from .nes_midi import NoteSpan, extract_nes_note_spans


def _merged_intervals(spans: Iterable[NoteSpan]) -> list[tuple[float, float]]:
    intervals = sorted(
        (span.start_seconds, span.end_seconds)
        for span in spans
        if span.end_seconds > span.start_seconds
    )
    if not intervals:
        return []

    merged: list[tuple[float, float]] = []
    start, end = intervals[0]
    for next_start, next_end in intervals[1:]:
        if next_start <= end:
            end = max(end, next_end)
        else:
            merged.append((start, end))
            start, end = next_start, next_end
    merged.append((start, end))
    return merged


def _duration(intervals: Iterable[tuple[float, float]]) -> float:
    return sum(max(0.0, end - start) for start, end in intervals)


def _overlap_duration(
    left: list[tuple[float, float]],
    right: list[tuple[float, float]],
) -> float:
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


def _pair_synchronized_onsets(
    pulse_1: list[NoteSpan],
    pulse_2: list[NoteSpan],
    tolerance_seconds: float,
) -> list[tuple[NoteSpan, NoteSpan]]:
    left = sorted(pulse_1, key=lambda span: span.start_seconds)
    right = sorted(pulse_2, key=lambda span: span.start_seconds)

    pairs: list[tuple[NoteSpan, NoteSpan]] = []
    i = 0
    j = 0
    while i < len(left) and j < len(right):
        delta = left[i].start_seconds - right[j].start_seconds
        if abs(delta) <= tolerance_seconds:
            pairs.append((left[i], right[j]))
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
    denominator = sqrt(
        sum(value * value for value in left_dev)
        * sum(value * value for value in right_dev)
    )
    if denominator == 0:
        return None
    return numerator / denominator


def _window_onset_counts(
    spans: list[NoteSpan],
    song_duration_seconds: float,
    window_seconds: float,
) -> list[int]:
    if song_duration_seconds <= 0 or window_seconds <= 0:
        return []

    count = max(1, int(song_duration_seconds / window_seconds) + 1)
    buckets = [0] * count
    for span in spans:
        index = min(int(span.start_seconds / window_seconds), count - 1)
        buckets[index] += 1
    return buckets


def _activity_state(
    spans: list[NoteSpan],
    start: float,
    end: float,
) -> bool:
    return any(
        span.start_seconds < end and span.end_seconds > start
        for span in spans
    )


def _alternating_activity(
    pulse_1: list[NoteSpan],
    pulse_2: list[NoteSpan],
    song_duration_seconds: float,
    window_seconds: float,
) -> dict[str, float | int | None]:
    if song_duration_seconds <= 0 or window_seconds <= 0:
        return {
            "exclusive_activity_ratio": 0.0,
            "adjacent_exclusive_switch_rate": None,
            "exclusive_windows": 0,
            "active_windows": 0,
        }

    window_count = max(1, int(song_duration_seconds / window_seconds) + 1)
    states: list[str] = []

    for index in range(window_count):
        start = index * window_seconds
        end = min(song_duration_seconds, start + window_seconds)
        p1_active = _activity_state(pulse_1, start, end)
        p2_active = _activity_state(pulse_2, start, end)

        if p1_active and p2_active:
            states.append("both")
        elif p1_active:
            states.append("p1")
        elif p2_active:
            states.append("p2")
        else:
            states.append("none")

    active_states = [state for state in states if state != "none"]
    exclusive_windows = sum(state in {"p1", "p2"} for state in states)

    comparable_adjacent = 0
    switches = 0
    for left, right in zip(states, states[1:]):
        if left in {"p1", "p2"} and right in {"p1", "p2"}:
            comparable_adjacent += 1
            if left != right:
                switches += 1

    return {
        "exclusive_activity_ratio": (
            exclusive_windows / len(active_states) if active_states else 0.0
        ),
        "adjacent_exclusive_switch_rate": (
            switches / comparable_adjacent if comparable_adjacent else None
        ),
        "exclusive_windows": exclusive_windows,
        "active_windows": len(active_states),
    }


def analyze_pulse_relationships(
    pulse_1: list[NoteSpan],
    pulse_2: list[NoteSpan],
    *,
    song_duration_seconds: float | None = None,
    onset_tolerance_seconds: float = 0.03,
    activity_window_seconds: float = 0.25,
    density_window_seconds: float = 1.0,
) -> dict[str, Any]:
    """Measure observable P1/P2 relationships without assigning stylistic intent."""

    if song_duration_seconds is None:
        song_duration_seconds = max(
            [span.end_seconds for span in pulse_1 + pulse_2] or [0.0]
        )

    p1_intervals = _merged_intervals(pulse_1)
    p2_intervals = _merged_intervals(pulse_2)
    p1_active = _duration(p1_intervals)
    p2_active = _duration(p2_intervals)
    overlap = _overlap_duration(p1_intervals, p2_intervals)
    active_union = p1_active + p2_active - overlap

    onset_pairs = _pair_synchronized_onsets(
        pulse_1,
        pulse_2,
        onset_tolerance_seconds,
    )
    interval_histogram = Counter(
        right.pitch - left.pitch
        for left, right in onset_pairs
    )

    abs_pitch_class_intervals = [
        abs(right.pitch - left.pitch) % 12
        for left, right in onset_pairs
    ]

    motion_counts: Counter[str] = Counter()
    interval_preserving_parallel = 0
    for (left_a, right_a), (left_b, right_b) in zip(
        onset_pairs,
        onset_pairs[1:],
    ):
        p1_motion = left_b.pitch - left_a.pitch
        p2_motion = right_b.pitch - right_a.pitch

        if p1_motion == 0 and p2_motion == 0:
            motion_counts["both_static"] += 1
        elif p1_motion == 0 or p2_motion == 0:
            motion_counts["oblique"] += 1
        elif p1_motion * p2_motion > 0:
            motion_counts["similar_direction"] += 1
            if (right_a.pitch - left_a.pitch) == (right_b.pitch - left_b.pitch):
                interval_preserving_parallel += 1
        else:
            motion_counts["contrary"] += 1

    motion_total = sum(motion_counts.values())
    synchronized_denominator = min(len(pulse_1), len(pulse_2))

    p1_density = _window_onset_counts(
        pulse_1,
        song_duration_seconds,
        density_window_seconds,
    )
    p2_density = _window_onset_counts(
        pulse_2,
        song_duration_seconds,
        density_window_seconds,
    )
    density_correlation = _pearson(
        [float(value) for value in p1_density],
        [float(value) for value in p2_density],
    )

    activity = _alternating_activity(
        pulse_1,
        pulse_2,
        song_duration_seconds,
        activity_window_seconds,
    )

    def ratio(count: int, total: int) -> float | None:
        return count / total if total else None

    third_like = sum(value in {3, 4} for value in abs_pitch_class_intervals)
    sixth_like = sum(value in {8, 9} for value in abs_pitch_class_intervals)
    unison_octave_like = sum(value == 0 for value in abs_pitch_class_intervals)

    return {
        "analysis_version": 1,
        "parameters": {
            "onset_tolerance_seconds": onset_tolerance_seconds,
            "activity_window_seconds": activity_window_seconds,
            "density_window_seconds": density_window_seconds,
        },
        "note_counts": {
            "pulse_1": len(pulse_1),
            "pulse_2": len(pulse_2),
        },
        "time_relationship": {
            "overlap_seconds": overlap,
            "overlap_ratio_of_active_union": (
                overlap / active_union if active_union > 0 else 0.0
            ),
            "overlap_ratio_of_song": (
                overlap / song_duration_seconds
                if song_duration_seconds > 0
                else 0.0
            ),
        },
        "onset_relationship": {
            "synchronized_pairs": len(onset_pairs),
            "synchronized_onset_ratio": (
                len(onset_pairs) / synchronized_denominator
                if synchronized_denominator
                else 0.0
            ),
            "signed_interval_histogram_semitones": {
                str(key): value
                for key, value in sorted(interval_histogram.items())
            },
            "third_like_ratio": ratio(third_like, len(onset_pairs)),
            "sixth_like_ratio": ratio(sixth_like, len(onset_pairs)),
            "unison_octave_like_ratio": ratio(
                unison_octave_like,
                len(onset_pairs),
            ),
        },
        "motion_relationship": {
            "transitions": motion_total,
            "similar_direction_ratio": ratio(
                motion_counts["similar_direction"],
                motion_total,
            ),
            "contrary_ratio": ratio(
                motion_counts["contrary"],
                motion_total,
            ),
            "oblique_ratio": ratio(
                motion_counts["oblique"],
                motion_total,
            ),
            "both_static_ratio": ratio(
                motion_counts["both_static"],
                motion_total,
            ),
            "interval_preserving_parallel_ratio": ratio(
                interval_preserving_parallel,
                motion_total,
            ),
        },
        "activity_relationship": activity,
        "density_relationship": {
            "pearson_onset_density_correlation": density_correlation,
            "density_compensation_score": (
                max(0.0, -density_correlation)
                if density_correlation is not None
                else None
            ),
        },
        "interpretation_note": (
            "These are observable relationships, not labels of musical intent. "
            "For example, exclusive activity is not automatically call-response."
        ),
    }


def analyze_pulse_relationships_from_midi(
    path: str | Path,
    **kwargs: Any,
) -> dict[str, Any]:
    spans = extract_nes_note_spans(path)
    song_duration_seconds = max(
        [
            span.end_seconds
            for voice_spans in spans.values()
            for span in voice_spans
        ]
        or [0.0]
    )
    return analyze_pulse_relationships(
        spans["pulse_1"],
        spans["pulse_2"],
        song_duration_seconds=song_duration_seconds,
        **kwargs,
    )
