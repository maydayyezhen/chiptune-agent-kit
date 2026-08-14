from chiptune_agent_kit.analysis.nes_midi import NoteSpan
from chiptune_agent_kit.analysis.note_hygiene import (
    SAMPLE_RATE,
    filter_composition_spans,
)


def _span(pitch: int, duration: float) -> NoteSpan:
    return NoteSpan(pitch=pitch, start_seconds=0.0, end_seconds=duration)


def test_filter_removes_one_sample_state_but_keeps_frame_scale_note() -> None:
    spans = [
        _span(100, 1.0 / SAMPLE_RATE),
        _span(60, 1.0 / 60.0),
    ]

    cleaned = filter_composition_spans(
        spans,
        drop_duration_at_or_below_seconds=0.001,
    )

    assert [span.pitch for span in cleaned] == [60]


def test_zero_threshold_preserves_positive_duration_notes() -> None:
    spans = [_span(100, 1.0 / SAMPLE_RATE), _span(60, 0.01)]
    cleaned = filter_composition_spans(
        spans,
        drop_duration_at_or_below_seconds=0.0,
    )
    assert len(cleaned) == 2
