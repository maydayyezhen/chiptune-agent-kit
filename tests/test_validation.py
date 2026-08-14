from chiptune_agent_kit.ir import ChipProject
from chiptune_agent_kit.validation import validate_nes2a03


def _valid_project() -> ChipProject:
    return ChipProject.from_dict(
        {
            "target": "nes_2a03",
            "tempo_bpm": 150,
            "voices": {
                "pulse_1": {"type": "pulse", "events": [{"start_beat": 0, "duration_beats": 1, "midi_note": 72, "duty": 0.25}]},
                "pulse_2": {"type": "pulse", "events": [{"start_beat": 0, "duration_beats": 1, "midi_note": 67, "duty": 0.5}]},
                "triangle": {"type": "triangle", "events": [{"start_beat": 0, "duration_beats": 1, "midi_note": 36}]},
                "noise": {"type": "noise", "events": [{"start_beat": 0, "duration_beats": 0.125, "noise_period": 4, "mode": "long"}]},
            },
        }
    )


def test_valid_project_has_no_errors() -> None:
    result = validate_nes2a03(_valid_project())
    assert result["errors"] == []


def test_overlap_is_rejected() -> None:
    project = _valid_project()
    project.voices["pulse_1"].events.append(
        {"start_beat": 0.5, "duration_beats": 1.0, "midi_note": 76, "duty": 0.25}
    )
    result = validate_nes2a03(project)
    assert any("overlaps" in error for error in result["errors"])


def test_invalid_duty_is_rejected() -> None:
    project = _valid_project()
    project.voices["pulse_1"].events[0]["duty"] = 0.33
    result = validate_nes2a03(project)
    assert any("duty" in error for error in result["errors"])
