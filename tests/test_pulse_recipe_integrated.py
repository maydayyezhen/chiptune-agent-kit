from chiptune_agent_kit.experiments.pulse_recipe_integrated import build_integrated_song
from chiptune_agent_kit.experiments.pulse_recipe_ab import BEATS_PER_BAR, validate_variant


def _bar(event):
    return int(event.start_beat // BEATS_PER_BAR)


def test_integrated_song_is_valid_four_voice_piece() -> None:
    tracks = build_integrated_song()
    validate_variant(tracks)
    assert set(tracks) == {"pulse_1", "pulse_2", "triangle", "noise"}
    assert all(tracks[voice] for voice in tracks)


def test_phase_chase_is_local_and_quiet() -> None:
    tracks = build_integrated_song()
    chase = [event for event in tracks["pulse_2"] if _bar(event) in (10, 11)]
    assert 1 <= len(chase) <= 8
    assert max(event.velocity for event in chase) <= 0.40


def test_density_tradeoff_is_backgrounded() -> None:
    tracks = build_integrated_song()
    p2 = [event for event in tracks["pulse_2"] if _bar(event) in (8, 9)]
    triangle = [event for event in tracks["triangle"] if _bar(event) in (8, 9)]
    assert p2
    assert max(event.velocity for event in p2) <= 0.30
    assert len(triangle) == 2
    assert all(event.duration_beats >= 3.5 for event in triangle)
