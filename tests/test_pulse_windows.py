from chiptune_agent_kit.analysis.nes_midi import NoteSpan
from chiptune_agent_kit.analysis.pulse_windows import (
    analyze_pulse_window,
    build_onset_rows,
    midi_note_name,
    select_representative_window,
)


def _span(pitch: int, start: float, duration: float = 0.4) -> NoteSpan:
    return NoteSpan(pitch=pitch, start_seconds=start, end_seconds=start + duration)


def test_locked_window_preserves_synced_interval_sequence() -> None:
    pulse_1 = [_span(60, float(t)) for t in range(6)]
    pulse_2 = [_span(64, float(t)) for t in range(6)]

    result = analyze_pulse_window(pulse_1, pulse_2, 0.0, 6.0)

    assert result["synchronized_onset_ratio"] == 1.0
    assert result["active_overlap_ratio"] == 1.0
    assert result["signed_interval_sequence_semitones"] == [4] * 6

    rows = build_onset_rows(pulse_1, pulse_2, 0.0, 2.0)
    assert [row["relation"] for row in rows] == ["sync", "sync"]
    assert [row["signed_interval_semitones"] for row in rows] == [4, 4]


def test_interlocking_window_keeps_onsets_distinct_from_active_overlap() -> None:
    pulse_1 = [_span(60, float(t), 0.8) for t in range(6)]
    pulse_2 = [_span(67, float(t) + 0.5, 0.8) for t in range(6)]

    result = analyze_pulse_window(pulse_1, pulse_2, 0.0, 6.0)

    assert result["synchronized_onset_ratio"] == 0.0
    assert result["active_overlap_ratio"] > 0.5

    selected = select_representative_window(
        pulse_1,
        pulse_2,
        "interlocking",
        {"sync": 0.0, "overlap": 0.8, "density_correlation": 0.0},
        window_seconds=4.0,
        step_seconds=1.0,
    )
    assert selected["synchronized_onset_ratio"] == 0.0
    assert selected["active_overlap_ratio"] > 0.5


def test_midi_note_name_uses_standard_scientific_pitch_notation() -> None:
    assert midi_note_name(60) == "C4"
    assert midi_note_name(69) == "A4"
