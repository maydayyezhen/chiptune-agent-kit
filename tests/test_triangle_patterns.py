from chiptune_agent_kit.analysis.nes_midi import NoteSpan
from chiptune_agent_kit.analysis.triangle_patterns import (
    analyze_triangle_window,
    detect_triangle_patterns,
    summarize_triangle_corpus,
)


def spans(pitches: list[int], step: float = 0.25) -> list[NoteSpan]:
    return [
        NoteSpan(pitch, index * step, index * step + step * 0.9)
        for index, pitch in enumerate(pitches)
    ]


def names(pitches: list[int]) -> set[str]:
    metrics = analyze_triangle_window(spans(pitches), 0.0, 8.0)
    return {item["pattern"] for item in detect_triangle_patterns(metrics)}


def test_repeated_note_drive_and_pedal() -> None:
    found = names([45] * 8 + [48, 45])
    assert "repeated_note_drive" in found
    assert "dominant_pitch_pedal" in found


def test_octave_pump() -> None:
    found = names([45, 57, 45, 57, 45, 57, 45, 57])
    assert "octave_pump" in found


def test_stepwise_motion() -> None:
    found = names([45, 47, 48, 50, 52, 53, 55, 57])
    assert "stepwise_motion" in found
    assert "repeated_note_drive" not in found


def test_summary_counts_song_prevalence() -> None:
    songs = [
        {
            "name": "one.mid",
            "clean_triangle_note_count": 10,
            "windows_scanned": 2,
            "patterns_present": ["octave_pump"],
            "candidates": [
                {"pattern": "octave_pump", "evidence": {"octave_transition_ratio": 1.0, "longest_octave_chain_notes": 8}},
            ],
            "episodes": [
                {"pattern": "octave_pump", "duration_seconds": 8.0},
            ],
        },
        {
            "name": "two.mid",
            "clean_triangle_note_count": 4,
            "windows_scanned": 1,
            "patterns_present": [],
            "candidates": [],
            "episodes": [],
        },
    ]
    summary = summarize_triangle_corpus(songs, files_found=2)
    assert summary["songs_with_clean_triangle"] == 2
    assert summary["patterns"]["octave_pump"]["songs"] == 1
    assert summary["patterns"]["octave_pump"]["prevalence_of_triangle_songs"] == 0.5
