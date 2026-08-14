from chiptune_agent_kit.analysis.recipe_candidates import extract_pulse_recipe_candidates


def test_extracts_parallel_interval_lock() -> None:
    casebook = {
        "groups": {
            "locked": [
                {
                    "name": "locked.mid",
                    "selected_window": {
                        "start_seconds": 0.0,
                        "end_seconds": 4.0,
                        "synchronized_onset_ratio": 1.0,
                        "active_overlap_ratio": 1.0,
                        "density_correlation": 1.0,
                        "signed_interval_sequence_semitones": [-12] * 8,
                        "pulse_1_motion_sequence_semitones": [2, -2] * 4,
                        "pulse_2_motion_sequence_semitones": [2, -2] * 4,
                        "density_bins": {},
                    },
                    "onset_rows": [],
                }
            ]
        }
    }
    result = extract_pulse_recipe_candidates(casebook)
    recipes = [item["recipe"] for item in result["candidates"]]
    assert "parallel_interval_lock" in recipes


def test_extracts_phase_shifted_riff_interlock() -> None:
    rows = []
    pitches = [66, 59, 71, 66, 69, 64, 66, 59, 71, 66]
    for index, pitch in enumerate(pitches):
        rows.append({
            "relative_seconds": index * 0.2,
            "pulse_1_pitch": None,
            "pulse_2_pitch": pitch,
        })
        rows.append({
            "relative_seconds": index * 0.2 + 0.1,
            "pulse_1_pitch": pitch,
            "pulse_2_pitch": None,
        })

    casebook = {
        "groups": {
            "interlocking": [
                {
                    "name": "phase.mid",
                    "selected_window": {
                        "start_seconds": 0.0,
                        "end_seconds": 4.0,
                        "synchronized_onset_ratio": 0.0,
                        "active_overlap_ratio": 1.0,
                        "density_correlation": 0.2,
                        "signed_interval_sequence_semitones": [],
                        "pulse_1_motion_sequence_semitones": [-7, 12, -5, 3, -5, 2, -7, 12, -5],
                        "pulse_2_motion_sequence_semitones": [-7, 12, -5, 3, -5, 2, -7, 12, -5],
                        "density_bins": {},
                    },
                    "onset_rows": rows,
                }
            ]
        }
    }
    result = extract_pulse_recipe_candidates(casebook)
    phase = next(item for item in result["candidates"] if item["recipe"] == "phase_shifted_riff_interlock")
    evidence = phase["evidence"]["pitch_sequence_alignment"]
    assert evidence["match_ratio"] == 1.0
    assert abs(evidence["median_time_offset_seconds_p1_minus_p2"] - 0.1) < 1e-9
