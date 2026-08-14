from chiptune_agent_kit.analysis.corpus_recipes import detect_window_recipes
from chiptune_agent_kit.analysis.corpus_recipes_refined import (
    _refine_phase_candidate,
    summarize_refined_corpus_scan,
)
from chiptune_agent_kit.analysis.nes_midi import NoteSpan


def test_detects_parallel_interval_lock() -> None:
    pulse_1 = [
        NoteSpan(60 + (index % 4), index * 0.25, index * 0.25 + 0.20)
        for index in range(12)
    ]
    pulse_2 = [
        NoteSpan(span.pitch - 12, span.start_seconds, span.end_seconds)
        for span in pulse_1
    ]

    recipes = detect_window_recipes(
        pulse_1,
        pulse_2,
        start_seconds=0.0,
        end_seconds=3.0,
        song_duration_seconds=3.0,
    )

    lock = next(item for item in recipes if item["recipe"] == "parallel_interval_lock")
    assert lock["evidence"]["dominant_interval_semitones"] == -12
    assert lock["evidence"]["longest_constant_interval_run"]["length"] == 12


def test_refines_stable_phase_shift_to_half_ioi_residual() -> None:
    pitches = [66, 59, 71, 66, 69, 64, 66, 59, 71, 66, 69, 64]
    pulse_2 = [
        NoteSpan(pitch, index * 0.2, index * 0.2 + 0.20)
        for index, pitch in enumerate(pitches)
    ]
    pulse_1 = [
        NoteSpan(pitch, index * 0.2 + 0.1, index * 0.2 + 0.30)
        for index, pitch in enumerate(pitches)
    ]

    recipes = detect_window_recipes(
        pulse_1,
        pulse_2,
        start_seconds=0.0,
        end_seconds=2.5,
        song_duration_seconds=2.5,
    )

    phase = next(item for item in recipes if item["recipe"] == "phase_shifted_riff_interlock")
    refined = _refine_phase_candidate(phase)
    assert refined is not None
    evidence = refined["evidence"]
    assert evidence["pitch_match_ratio"] == 1.0
    assert abs(evidence["median_time_offset_seconds_p1_minus_p2"] - 0.1) < 1e-9
    assert abs(evidence["absolute_residual_phase_fraction"] - 0.5) < 1e-9
    assert evidence["simple_residual_phase_fraction"] == "1/2"
    assert evidence["phase_stability_spread_ioi_ratio"] < 1e-9


def test_refinement_rejects_unstable_phase_offset() -> None:
    candidate = {
        "recipe": "phase_shifted_riff_interlock",
        "window": [0.0, 6.0],
        "evidence": {
            "pitch_match_ratio": 1.0,
            "median_voice_ioi_seconds": 0.2,
            "median_time_offset_seconds_p1_minus_p2": 0.1,
            "time_offset_spread_seconds": 0.03,
        },
    }
    assert _refine_phase_candidate(candidate) is None


def test_refined_summary_counts_prevalence_and_harmonic_family() -> None:
    songs = [
        {
            "name": "one.mid",
            "clean_note_counts": {"pulse_1": 10, "pulse_2": 10},
            "windows_scanned": 3,
            "recipes_present": ["parallel_interval_lock"],
            "candidates": [
                {
                    "recipe": "parallel_interval_lock",
                    "evidence": {"dominant_interval_semitones": -12},
                },
                {
                    "recipe": "parallel_interval_lock",
                    "evidence": {"dominant_interval_semitones": -12},
                },
            ],
            "episodes": [
                {
                    "recipe": "parallel_interval_lock",
                    "duration_seconds": 9.0,
                }
            ],
            "refinement": {"rejected_unstable_phase_windows": 0},
        },
        {
            "name": "two.mid",
            "clean_note_counts": {"pulse_1": 8, "pulse_2": 8},
            "windows_scanned": 2,
            "recipes_present": [],
            "candidates": [],
            "episodes": [],
            "refinement": {"rejected_unstable_phase_windows": 0},
        },
    ]

    summary = summarize_refined_corpus_scan(songs, files_found=2)
    lock = summary["recipes"]["parallel_interval_lock"]
    assert lock["songs"] == 1
    assert lock["window_hits"] == 2
    assert lock["prevalence_of_two_pulse_songs"] == 0.5
    assert lock["harmonic_family_song_counts"]["unison_octave"] == 1
