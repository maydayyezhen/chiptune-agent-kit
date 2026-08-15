from chiptune_agent_kit.analysis.nes_midi import NoteSpan
from chiptune_agent_kit.analysis.triangle_recipe_candidates import detect_triangle_recipes, _window_metrics


def spans(pitches: list[int]) -> list[NoteSpan]:
    return [NoteSpan(p, i * 0.25, i * 0.25 + 0.20) for i, p in enumerate(pitches)]


def recipes(pitches: list[int]) -> set[str]:
    metrics = _window_metrics(spans(pitches), 0.0, 8.0)
    return {item["recipe"] for item in detect_triangle_recipes(metrics)}


def test_two_register_octave_pump() -> None:
    found = recipes([43, 55, 43, 55, 43, 55, 43, 55])
    assert "two_register_octave_pump" in found
    assert "multi_register_octave_cycle" not in found


def test_multi_register_octave_cycle() -> None:
    found = recipes([41, 53, 65, 53, 41, 53, 65, 53])
    assert "multi_register_octave_cycle" in found


def test_anchor_return_pattern() -> None:
    found = recipes([45, 48, 45, 47, 45, 45, 48, 45])
    assert "anchor_return_pattern" in found


def test_directional_step_run() -> None:
    found = recipes([44, 45, 46, 47, 48, 50, 53])
    assert "directional_step_run" in found


def test_neighbor_oscillation() -> None:
    found = recipes([52, 53, 52, 53, 52, 53, 52, 53])
    assert "neighbor_oscillation" in found


def test_repeated_note_drive() -> None:
    found = recipes([48, 48, 48, 48, 48, 48, 48, 48])
    assert "repeated_note_drive" in found
