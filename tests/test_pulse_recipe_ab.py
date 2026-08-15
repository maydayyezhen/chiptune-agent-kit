from chiptune_agent_kit.experiments.pulse_recipe_ab import (
    TOTAL_BEATS,
    build_variants,
    validate_variant,
)


def _signature(events):
    return [(event.pitch, event.start_beat, event.duration_beats, event.velocity) for event in events]


def test_fixed_tracks_are_identical_across_variants() -> None:
    variants = build_variants()
    first = next(iter(variants.values()))
    for tracks in variants.values():
        assert _signature(tracks["pulse_1"]) == _signature(first["pulse_1"])
        assert _signature(tracks["triangle"]) == _signature(first["triangle"])
        assert _signature(tracks["noise"]) == _signature(first["noise"])


def test_only_pulse_2_changes_and_variants_validate() -> None:
    variants = build_variants()
    p2_signatures = set()
    for tracks in variants.values():
        validate_variant(tracks)
        signature = tuple(_signature(tracks["pulse_2"]))
        p2_signatures.add(signature)
        assert all(event.end_beat <= TOTAL_BEATS + 1e-9 for event in tracks["pulse_2"])
    assert len(p2_signatures) == len(variants)


def test_phase_interlock_has_fixed_quarter_beat_offset() -> None:
    variants = build_variants()
    p1 = variants["03_phase_interlock"]["pulse_1"]
    p2 = variants["03_phase_interlock"]["pulse_2"]
    assert len(p2) <= len(p1)
    for left, right in zip(p1, p2):
        assert left.pitch == right.pitch
        assert abs((right.start_beat - left.start_beat) - 0.25) < 1e-9
