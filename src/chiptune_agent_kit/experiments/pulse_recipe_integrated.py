from __future__ import annotations

from pathlib import Path
import json

from .pulse_recipe_ab import (
    BARS,
    BEATS_PER_BAR,
    Event,
    _ROOTS,
    _flatten_melody,
    _noise_groove,
    _triangle_bass,
    validate_variant,
    write_midi,
    write_wav,
)


def _bar_of(event: Event) -> int:
    return min(int(event.start_beat // BEATS_PER_BAR), BARS - 1)


def _events_in_bar(events: list[Event], bar: int) -> list[Event]:
    return [event for event in events if _bar_of(event) == bar]


def _copy_with_interval(events: list[Event], interval: int, velocity: float) -> list[Event]:
    return [
        Event(event.pitch + interval, event.start_beat, event.duration_beats, velocity)
        for event in events
    ]


def _intro_p2() -> list[Event]:
    output: list[Event] = []
    for bar in (0, 1):
        root = _ROOTS[bar]
        base = bar * BEATS_PER_BAR
        output.extend(
            [
                Event(root + 24, base, 1.25, 0.42),
                Event(root + 31, base + 2.0, 1.25, 0.38),
            ]
        )
    return output


def _block_switch_section(p1: list[Event], start_bar: int, end_bar: int, intervals: tuple[int, ...]) -> list[Event]:
    output: list[Event] = []
    span = max(1, end_bar - start_bar)
    bars_per_block = max(1, span // len(intervals))
    for bar in range(start_bar, end_bar):
        block = min((bar - start_bar) // bars_per_block, len(intervals) - 1)
        output.extend(_copy_with_interval(_events_in_bar(p1, bar), intervals[block], 0.56))
    return output


def _interval_lock_section(p1: list[Event], start_bar: int, end_bar: int) -> list[Event]:
    output: list[Event] = []
    for bar in range(start_bar, end_bar):
        output.extend(_copy_with_interval(_events_in_bar(p1, bar), -12, 0.52))
    return output


def _density_tradeoff_section(p1: list[Event]) -> list[Event]:
    output: list[Event] = []

    # Bar 8: P1 is dense, so P2 yields almost completely.
    bar = 8
    root = _ROOTS[bar]
    base = bar * BEATS_PER_BAR
    output.extend(
        [
            Event(root + 24, base, 1.6, 0.30),
            Event(root + 31, base + 2.25, 1.25, 0.28),
        ]
    )

    # Bar 9: P1 is sparse. P2 fills selected holes, but stays deliberately quiet.
    # This is not a second lead: low velocity + lower register + Triangle support.
    bar = 9
    root = _ROOTS[bar]
    base = bar * BEATS_PER_BAR
    fill = (
        (0.50, root + 24),
        (1.00, root + 28),
        (2.50, root + 31),
        (3.00, root + 28),
    )
    for offset, pitch in fill:
        output.append(Event(pitch, base + offset, 0.38, 0.28))
    return output


def _phase_chase_section(p1: list[Event]) -> list[Event]:
    output: list[Event] = []
    offset = 0.25

    # Deliberately short-lived: copy only a small motif in each bar instead of
    # phase-shifting the entire melody, because the A/B test sounded cluttered.
    for bar, take in ((10, 4), (11, 3)):
        motif = _events_in_bar(p1, bar)[:take]
        for event in motif:
            output.append(
                Event(
                    event.pitch,
                    event.start_beat + offset,
                    min(event.duration_beats, 0.42),
                    0.36,
                )
            )
    return output


def _finale_p2(p1: list[Event]) -> list[Event]:
    output: list[Event] = []
    # Main winning idea from A/B: phrase-level block changes.
    for bar in (12, 13):
        output.extend(_copy_with_interval(_events_in_bar(p1, bar), -5, 0.58))
    for bar in (14, 15):
        events = _events_in_bar(p1, bar)
        if bar == 15 and len(events) >= 2:
            # Keep the block-switch colour, then collapse into octave lock on the cadence.
            output.extend(_copy_with_interval(events[:-2], 7, 0.58))
            output.extend(_copy_with_interval(events[-2:], -12, 0.62))
        else:
            output.extend(_copy_with_interval(events, 7, 0.58))
    return output


def _supported_triangle() -> list[Event]:
    original = _triangle_bass()
    output = [event for event in original if _bar_of(event) not in (8, 9, 10, 11)]

    # Longer bass pedals under density-tradeoff and chase sections act as the
    # requested backing layer without introducing a fifth hardware voice.
    for bar in (8, 9):
        root = _ROOTS[bar]
        base = bar * BEATS_PER_BAR
        output.append(Event(root, base, 3.8, 0.80))

    # Keep the phase-chase section grounded and less busy in the low register.
    for bar in (10, 11):
        root = _ROOTS[bar]
        base = bar * BEATS_PER_BAR
        output.extend(
            [
                Event(root, base, 2.0, 0.74),
                Event(root + 7, base + 2.0, 1.8, 0.66),
            ]
        )
    return sorted(output, key=lambda event: event.start_beat)


def _supported_noise() -> list[Event]:
    output: list[Event] = []
    for event in _noise_groove():
        bar = _bar_of(event)
        if bar in (8, 9):
            # Slightly firmer groove when P2 is intentionally backgrounded.
            boost = 1.10 if event.pitch == 38 else 1.04
            output.append(Event(event.pitch, event.start_beat, event.duration_beats, min(0.82, event.velocity * boost)))
        elif bar in (10, 11):
            # Pull hats back a touch during the short phase chase.
            scale = 0.90 if event.pitch == 42 else 1.0
            output.append(Event(event.pitch, event.start_beat, event.duration_beats, event.velocity * scale))
        else:
            output.append(event)
    return output


def build_integrated_song() -> dict[str, list[Event]]:
    p1 = _flatten_melody()
    p2: list[Event] = []
    p2.extend(_intro_p2())
    p2.extend(_block_switch_section(p1, 2, 6, (-12, -5)))
    p2.extend(_interval_lock_section(p1, 6, 8))
    p2.extend(_density_tradeoff_section(p1))
    p2.extend(_phase_chase_section(p1))
    p2.extend(_finale_p2(p1))
    p2.sort(key=lambda event: (event.start_beat, event.end_beat))

    tracks = {
        "pulse_1": p1,
        "pulse_2": p2,
        "triangle": _supported_triangle(),
        "noise": _supported_noise(),
    }
    validate_variant(tracks)
    return tracks


def export_integrated_song(directory: str | Path) -> dict[str, object]:
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    tracks = build_integrated_song()

    midi = write_midi(root / "pulse_recipe_integrated_v1.mid", tracks)
    wav = write_wav(root / "pulse_recipe_integrated_v1.wav", tracks)

    sections = [
        {"bars": "1-2", "role": "intro", "pulse_2": "sparse anchors"},
        {"bars": "3-6", "role": "A", "pulse_2": "block switch: -12 then -5 semitones"},
        {"bars": "7-8", "role": "lift", "pulse_2": "octave interval lock"},
        {"bars": "9-10", "role": "break", "pulse_2": "quiet density tradeoff; Triangle pedals provide backing"},
        {"bars": "11-12", "role": "chase", "pulse_2": "short phase-shifted motif imitation only"},
        {"bars": "13-16", "role": "finale", "pulse_2": "block switch -5 to +7, cadence collapses to octave lock"},
    ]
    manifest = {
        "experiment": "pulse_recipe_integrated_v1",
        "intent": "One coherent tune using all four corpus-derived P1/P2 ideas after A/B listening feedback.",
        "files": {"midi": midi.name, "wav": wav.name},
        "sections": sections,
        "feedback_applied": [
            "block_switch is the main arrangement language",
            "phase interlock is restricted to short motifs instead of continuous copying",
            "density-tradeoff P2 is quieter and lower, with longer Triangle backing and firmer groove",
        ],
        "note_counts": {voice: len(events) for voice, events in tracks.items()},
    }
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (root / "README.txt").write_text(
        "Pulse Recipe Integrated v1\n\n"
        "Listen as one piece, not as an A/B test.\n"
        "Bars 1-2 intro: sparse P2.\n"
        "Bars 3-6: block-switch harmony.\n"
        "Bars 7-8: octave interval lock.\n"
        "Bars 9-10: quiet density tradeoff with Triangle backing.\n"
        "Bars 11-12: short phase-shifted chase only.\n"
        "Bars 13-16: block-switch finale, ending in octave lock.\n",
        encoding="utf-8",
    )
    return manifest
