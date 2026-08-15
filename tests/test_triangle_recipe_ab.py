from chiptune_agent_kit.experiments.triangle_recipe_ab import build_variants
from chiptune_agent_kit.experiments.pulse_recipe_ab import validate_variant


def test_only_triangle_changes() -> None:
    variants = build_variants()
    names = list(variants)
    reference = variants[names[0]]
    for name in names[1:]:
        current = variants[name]
        assert current["pulse_1"] == reference["pulse_1"]
        assert current["pulse_2"] == reference["pulse_2"]
        assert current["noise"] == reference["noise"]
        assert current["triangle"] != reference["triangle"]


def test_all_variants_are_monophonic_and_valid() -> None:
    for tracks in build_variants().values():
        validate_variant(tracks)


def test_expected_variant_set() -> None:
    assert set(build_variants()) == {
        "00_baseline_root_support",
        "01_repeated_note_drive",
        "02_anchor_return",
        "03_directional_step_run",
        "04_two_register_octave_pump",
        "05_neighbor_oscillation",
    }
