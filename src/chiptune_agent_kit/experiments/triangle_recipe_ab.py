from __future__ import annotations

from pathlib import Path
import json

from .pulse_recipe_ab import (
    BARS,
    BEATS_PER_BAR,
    Event,
    _ROOTS,
    _block_switch_p2,
    _flatten_melody,
    _noise_groove,
    validate_variant,
    write_midi,
    write_wav,
)


def _baseline_triangle() -> list[Event]:
    output: list[Event] = []
    for bar, root in enumerate(_ROOTS):
        base = bar * BEATS_PER_BAR
        output.extend([
            Event(root, base, 1.8, 0.78),
            Event(root + 7, base + 2.0, 1.8, 0.66),
        ])
    return output


def _repeated_drive_triangle() -> list[Event]:
    output: list[Event] = []
    for bar, root in enumerate(_ROOTS):
        base = bar * BEATS_PER_BAR
        for step in range(8):
            output.append(Event(root, base + step * 0.5, 0.42, 0.62 if step % 2 else 0.72))
    return output


def _anchor_return_triangle() -> list[Event]:
    output: list[Event] = []
    # Corpus-inspired abstract shape: anchor -> short excursion -> anchor.
    offsets = (0, 3, 0, 2, 0, 5, 0, 2)
    for bar, root in enumerate(_ROOTS):
        base = bar * BEATS_PER_BAR
        for step, offset in enumerate(offsets):
            output.append(Event(root + offset, base + step * 0.5, 0.42, 0.66))
    return output


def _directional_step_triangle() -> list[Event]:
    output: list[Event] = []
    # Semitone/whole-tone local runs. Alternate direction by bar so it stays phrase-like.
    scale_offsets = (0, 2, 3, 5, 7, 8, 10, 12)
    for bar, root in enumerate(_ROOTS):
        base = bar * BEATS_PER_BAR
        offsets = scale_offsets if bar % 2 == 0 else tuple(reversed(scale_offsets))
        for step, offset in enumerate(offsets):
            output.append(Event(root + offset, base + step * 0.5, 0.42, 0.62))
    return output


def _two_register_octave_pump_triangle() -> list[Event]:
    output: list[Event] = []
    for bar, root in enumerate(_ROOTS):
        base = bar * BEATS_PER_BAR
        for step in range(8):
            pitch = root if step % 2 == 0 else root + 12
            output.append(Event(pitch, base + step * 0.5, 0.42, 0.61))
    return output


def _neighbor_oscillation_triangle() -> list[Event]:
    output: list[Event] = []
    for bar, root in enumerate(_ROOTS):
        base = bar * BEATS_PER_BAR
        # A one-semitone neighbor is deliberately used as a specialty tension gesture.
        for step in range(8):
            pitch = root if step % 2 == 0 else root + 1
            output.append(Event(pitch, base + step * 0.5, 0.40, 0.54))
    return output


def build_variants() -> dict[str, dict[str, list[Event]]]:
    pulse_1 = _flatten_melody()
    pulse_2 = _block_switch_p2(pulse_1)
    noise = _noise_groove()
    triangle_builders = {
        "00_baseline_root_support": _baseline_triangle,
        "01_repeated_note_drive": _repeated_drive_triangle,
        "02_anchor_return": _anchor_return_triangle,
        "03_directional_step_run": _directional_step_triangle,
        "04_two_register_octave_pump": _two_register_octave_pump_triangle,
        "05_neighbor_oscillation": _neighbor_oscillation_triangle,
    }
    return {
        name: {
            "pulse_1": list(pulse_1),
            "pulse_2": list(pulse_2),
            "triangle": builder(),
            "noise": list(noise),
        }
        for name, builder in triangle_builders.items()
    }


def export_triangle_ab_pack(directory: str | Path) -> dict[str, object]:
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    variants = build_variants()
    descriptions = {
        "00_baseline_root_support": "Baseline Triangle: long root/fifth support, no corpus-derived local motion recipe.",
        "01_repeated_note_drive": "Core candidate: repeated root retriggers for rhythmic propulsion; 21.664% refined corpus prevalence.",
        "02_anchor_return": "Core candidate: anchor -> excursion -> anchor cells; 8.661% refined corpus prevalence.",
        "03_directional_step_run": "Core candidate: phrase-local semitone/whole-tone directional runs; 26.497% refined corpus prevalence.",
        "04_two_register_octave_pump": "Specialty candidate: alternate one pitch class across two octave registers; 0.577% strict refined prevalence.",
        "05_neighbor_oscillation": "Specialty candidate: alternate two adjacent pitches; 0.556% strict refined prevalence.",
    }
    manifest: dict[str, object] = {
        "experiment": "triangle_recipe_ab_v1",
        "intent": "Controlled listening test for refined Triangle recipe candidates.",
        "fixed_tracks": ["pulse_1", "pulse_2", "noise"],
        "fixed_pulse_2_strategy": "block_switch",
        "variable_track": "triangle",
        "bars": BARS,
        "variants": {},
        "ranking_note": "Variants 01-03 are core candidates. 04-05 are low-prevalence specialty gestures, not default NES rules.",
    }
    for name, tracks in variants.items():
        validate_variant(tracks)
        midi = write_midi(root / f"{name}.mid", tracks)
        wav = write_wav(root / f"{name}.wav", tracks)
        manifest["variants"][name] = {
            "description": descriptions[name],
            "triangle_note_count": len(tracks["triangle"]),
            "midi": midi.name,
            "wav": wav.name,
        }
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (root / "README.txt").write_text(
        "Triangle Recipe A/B v1\n\n"
        "Pulse 1, Pulse 2 (block-switch), Noise, tempo, form, and renderer are fixed. Only Triangle changes.\n\n"
        + "\n".join(f"{name}: {descriptions[name]}" for name in descriptions)
        + "\n",
        encoding="utf-8",
    )
    return manifest
