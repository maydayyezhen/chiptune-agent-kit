from __future__ import annotations

from pathlib import Path
from statistics import mean
from typing import Any, Iterable

from .nes_midi import NoteSpan, extract_nes_note_spans
from .relationships import analyze_pulse_relationships

VOICE_NAMES = ("pulse_1", "pulse_2", "triangle", "noise")
SAMPLE_RATE = 44100.0


def filter_composition_spans(
    spans: Iterable[NoteSpan],
    *,
    drop_duration_at_or_below_seconds: float,
) -> list[NoteSpan]:
    """Remove sample-level micro-note states before composition-oriented analysis.

    Raw extraction remains untouched. This derived view intentionally treats very
    short pitch states as performance/detail candidates rather than canonical
    composition notes.
    """
    threshold = max(0.0, float(drop_duration_at_or_below_seconds))
    epsilon = 0.25 / SAMPLE_RATE
    return [
        span
        for span in spans
        if span.duration_seconds > threshold + epsilon
    ]


def _resolve_source(source: str, root: str | Path) -> Path:
    source_path = Path(source)
    if source_path.exists():
        return source_path
    root_path = Path(root)
    matches = list(root_path.rglob(source_path.name))
    if len(matches) != 1:
        raise FileNotFoundError(
            f"Expected one MIDI named {source_path.name!r} under {root_path}, found {len(matches)}"
        )
    return matches[0]


def _safe_mean(values: list[float]) -> float | None:
    return mean(values) if values else None


def _voice_hygiene(
    songs: list[dict[str, list[NoteSpan]]],
    voice_name: str,
    threshold_seconds: float,
) -> dict[str, Any]:
    raw = [span for song in songs for span in song[voice_name]]
    cleaned = filter_composition_spans(
        raw,
        drop_duration_at_or_below_seconds=threshold_seconds,
    )
    removed = len(raw) - len(cleaned)
    return {
        "raw_notes": len(raw),
        "kept_notes": len(cleaned),
        "removed_notes": removed,
        "removed_ratio": removed / len(raw) if raw else 0.0,
    }


def analyze_note_hygiene_sensitivity(
    report: dict[str, Any],
    *,
    root: str | Path,
    thresholds_seconds: Iterable[float],
    onset_tolerance_seconds: float = 0.005,
) -> dict[str, Any]:
    """Measure how micro-note filtering changes corpus-level P1/P2 conclusions."""

    loaded: list[dict[str, list[NoteSpan]]] = []
    for song in report.get("songs", []):
        path = _resolve_source(song["source"], root)
        loaded.append(extract_nes_note_spans(path))

    results: dict[str, Any] = {}
    for threshold in thresholds_seconds:
        threshold = float(threshold)
        relationship_rows: list[dict[str, Any]] = []

        for spans in loaded:
            p1 = filter_composition_spans(
                spans["pulse_1"],
                drop_duration_at_or_below_seconds=threshold,
            )
            p2 = filter_composition_spans(
                spans["pulse_2"],
                drop_duration_at_or_below_seconds=threshold,
            )
            if not p1 or not p2:
                continue
            duration = max(
                [span.end_seconds for voice in spans.values() for span in voice]
                or [0.0]
            )
            relationship_rows.append(
                analyze_pulse_relationships(
                    p1,
                    p2,
                    song_duration_seconds=duration,
                    onset_tolerance_seconds=onset_tolerance_seconds,
                )
            )

        sync = [
            float(row["onset_relationship"]["synchronized_onset_ratio"])
            for row in relationship_rows
        ]
        overlap = [
            float(row["time_relationship"]["overlap_ratio_of_active_union"])
            for row in relationship_rows
        ]
        density = [
            float(value)
            for row in relationship_rows
            if (value := row["density_relationship"]["pearson_onset_density_correlation"])
            is not None
        ]

        key = f"{threshold:.9f}"
        results[key] = {
            "drop_duration_at_or_below_seconds": threshold,
            "songs_with_both_pulses": len(relationship_rows),
            "voices": {
                voice: _voice_hygiene(loaded, voice, threshold)
                for voice in VOICE_NAMES
            },
            "pulse_1_pulse_2": {
                "mean_synchronized_onset_ratio": _safe_mean(sync),
                "mean_overlap_ratio_of_active_union": _safe_mean(overlap),
                "mean_onset_density_correlation": _safe_mean(density),
            },
        }

    return {
        "sample_songs": len(loaded),
        "sample_rate_hz": SAMPLE_RATE,
        "one_sample_seconds": 1.0 / SAMPLE_RATE,
        "onset_tolerance_seconds": onset_tolerance_seconds,
        "thresholds": results,
        "interpretation_note": (
            "Raw MIDI is retained unchanged. These filtered views are sensitivity probes for "
            "composition analysis, not claims that short NES pitch states are musically meaningless."
        ),
    }
