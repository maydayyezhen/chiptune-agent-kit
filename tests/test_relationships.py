from chiptune_agent_kit.analysis import NoteSpan, analyze_pulse_relationships


def note(pitch: int, start: float, duration: float = 0.4) -> NoteSpan:
    return NoteSpan(pitch, start, start + duration)


def test_parallel_thirds_and_overlap_are_detected() -> None:
    p1 = [note(60, 0.0), note(62, 0.5), note(64, 1.0), note(65, 1.5)]
    p2 = [note(64, 0.0), note(66, 0.5), note(68, 1.0), note(69, 1.5)]

    result = analyze_pulse_relationships(p1, p2, song_duration_seconds=2.0)

    assert result["onset_relationship"]["synchronized_pairs"] == 4
    assert result["onset_relationship"]["synchronized_onset_ratio"] == 1.0
    assert result["onset_relationship"]["third_like_ratio"] == 1.0
    assert result["motion_relationship"]["similar_direction_ratio"] == 1.0
    assert result["motion_relationship"]["interval_preserving_parallel_ratio"] == 1.0
    assert result["time_relationship"]["overlap_ratio_of_active_union"] == 1.0


def test_contrary_motion_is_detected() -> None:
    p1 = [note(60, 0.0), note(62, 0.5), note(64, 1.0)]
    p2 = [note(72, 0.0), note(70, 0.5), note(68, 1.0)]

    result = analyze_pulse_relationships(p1, p2, song_duration_seconds=1.5)

    assert result["motion_relationship"]["contrary_ratio"] == 1.0


def test_alternating_activity_is_not_mislabeled_call_response() -> None:
    p1 = [note(60, 0.0, 0.2), note(62, 1.0, 0.2)]
    p2 = [note(67, 0.5, 0.2), note(69, 1.5, 0.2)]

    result = analyze_pulse_relationships(
        p1,
        p2,
        song_duration_seconds=2.0,
        activity_window_seconds=0.25,
    )

    activity = result["activity_relationship"]
    assert activity["exclusive_activity_ratio"] == 1.0
    assert "not automatically call-response" in result["interpretation_note"]
