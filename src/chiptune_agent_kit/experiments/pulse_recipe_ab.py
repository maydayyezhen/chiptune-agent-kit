from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import math
import wave
from array import array

import mido


TEMPO_BPM = 150.0
BEATS_PER_BAR = 4.0
BARS = 16
TOTAL_BEATS = BEATS_PER_BAR * BARS
TICKS_PER_BEAT = 480
SAMPLE_RATE = 44100


@dataclass(frozen=True)
class Event:
    pitch: int
    start_beat: float
    duration_beats: float
    velocity: float = 0.8

    @property
    def end_beat(self) -> float:
        return self.start_beat + self.duration_beats


# One fixed foreground melody. Every A/B variant keeps this exact P1.
# The line is intentionally original and compact, with alternating dense/sparse bars
# so density tradeoff has something real to operate against.
_MELODY_BARS: tuple[tuple[tuple[float, int, float], ...], ...] = (
    ((0.0, 69, 0.5), (0.5, 72, 0.5), (1.0, 76, 1.0), (2.5, 74, 0.5), (3.0, 72, 0.5), (3.5, 69, 0.5)),
    ((0.0, 69, 1.0), (1.5, 72, 0.5), (2.0, 76, 1.0), (3.25, 79, 0.5)),
    ((0.0, 76, 0.5), (0.5, 74, 0.5), (1.0, 72, 0.5), (1.5, 69, 0.5), (2.0, 72, 0.5), (2.5, 76, 0.5), (3.0, 79, 0.5), (3.5, 76, 0.5)),
    ((0.0, 79, 1.0), (1.5, 76, 0.5), (2.0, 74, 0.5), (2.5, 72, 1.5)),
    ((0.0, 72, 0.5), (0.5, 74, 0.5), (1.0, 76, 0.5), (1.5, 79, 0.5), (2.0, 81, 0.5), (2.5, 79, 0.5), (3.0, 76, 0.5), (3.5, 74, 0.5)),
    ((0.0, 72, 1.0), (1.5, 76, 0.5), (2.0, 79, 1.0), (3.25, 81, 0.5)),
    ((0.0, 81, 0.5), (0.5, 79, 0.5), (1.0, 76, 0.5), (1.5, 74, 0.5), (2.0, 72, 0.5), (2.5, 69, 0.5), (3.0, 72, 0.5), (3.5, 76, 0.5)),
    ((0.0, 79, 1.0), (1.5, 76, 0.5), (2.0, 72, 0.5), (2.5, 69, 1.5)),
    ((0.0, 69, 0.5), (0.5, 72, 0.5), (1.0, 74, 0.5), (1.5, 76, 0.5), (2.0, 79, 0.5), (2.5, 76, 0.5), (3.0, 74, 0.5), (3.5, 72, 0.5)),
    ((0.0, 69, 1.0), (1.5, 72, 0.5), (2.0, 74, 1.0), (3.25, 76, 0.5)),
    ((0.0, 76, 0.5), (0.5, 79, 0.5), (1.0, 81, 0.5), (1.5, 79, 0.5), (2.0, 76, 0.5), (2.5, 74, 0.5), (3.0, 72, 0.5), (3.5, 69, 0.5)),
    ((0.0, 72, 1.0), (1.5, 74, 0.5), (2.0, 76, 0.5), (2.5, 69, 1.5)),
    ((0.0, 69, 0.5), (0.5, 76, 0.5), (1.0, 79, 0.5), (1.5, 81, 0.5), (2.0, 79, 0.5), (2.5, 76, 0.5), (3.0, 72, 0.5), (3.5, 69, 0.5)),
    ((0.0, 72, 1.0), (1.5, 76, 0.5), (2.0, 81, 1.0), (3.25, 79, 0.5)),
    ((0.0, 76, 0.5), (0.5, 74, 0.5), (1.0, 72, 0.5), (1.5, 69, 0.5), (2.0, 67, 0.5), (2.5, 69, 0.5), (3.0, 72, 0.5), (3.5, 76, 0.5)),
    ((0.0, 79, 0.75), (1.0, 76, 0.75), (2.0, 72, 0.75), (3.0, 69, 1.0)),
)

# A minor / F / C / G-ish low-register harmonic skeleton.
_ROOTS = (45, 41, 48, 43) * 4


def _flatten_melody() -> list[Event]:
    events: list[Event] = []
    for bar_index, bar in enumerate(_MELODY_BARS):
        base = bar_index * BEATS_PER_BAR
        for offset, pitch, duration in bar:
            events.append(Event(pitch, base + offset, duration, 0.90))
    return events


def _triangle_bass() -> list[Event]:
    events: list[Event] = []
    for bar, root in enumerate(_ROOTS):
        start = bar * BEATS_PER_BAR
        events.extend(
            [
                Event(root, start, 1.5, 0.78),
                Event(root + 12, start + 2.0, 0.75, 0.70),
                Event(root + 7, start + 3.0, 0.75, 0.65),
            ]
        )
    return events


def _noise_groove() -> list[Event]:
    events: list[Event] = []
    # MIDI pitches are descriptive tags for the experimental renderer:
    # 42 = short hat-like burst, 38 = longer snare-like burst.
    for bar in range(BARS):
        base = bar * BEATS_PER_BAR
        for step in range(8):
            beat = base + step * 0.5
            if step in (2, 6):
                events.append(Event(38, beat, 0.18, 0.74))
            else:
                velocity = 0.30 if step % 2 else 0.42
                events.append(Event(42, beat, 0.10, velocity))
    return events


def _plain_p2() -> list[Event]:
    events: list[Event] = []
    for bar, root in enumerate(_ROOTS):
        base = bar * BEATS_PER_BAR
        events.append(Event(root + 24, base, 1.25, 0.62))
        events.append(Event(root + 31, base + 2.0, 1.25, 0.58))
    return events


def _interval_lock_p2(p1: list[Event]) -> list[Event]:
    # Corpus result: unison/octave is one of the two strongest harmonic families.
    return [Event(event.pitch - 12, event.start_beat, event.duration_beats, 0.64) for event in p1]


def _block_switch_p2(p1: list[Event]) -> list[Event]:
    # Phrase-sized exact interval blocks. Perfect-interval families are intentionally
    # emphasized because they were the strongest full-corpus harmonic family.
    phrase_intervals = (-12, -5, 7, 12)
    output: list[Event] = []
    for event in p1:
        phrase = min(int(event.start_beat // 16.0), 3)
        interval = phrase_intervals[phrase]
        output.append(Event(event.pitch + interval, event.start_beat, event.duration_beats, 0.62))
    return output


def _phase_interlock_p2(p1: list[Event]) -> list[Event]:
    # Half of the common 0.5-beat foreground subdivision = 0.25 beat residue.
    # Keep pitch identity and a fixed phase offset, matching the refined detector idea.
    offset = 0.25
    output: list[Event] = []
    for event in p1:
        start = event.start_beat + offset
        if start >= TOTAL_BEATS:
            continue
        duration = min(event.duration_beats, TOTAL_BEATS - start)
        output.append(Event(event.pitch, start, duration, 0.56))
    return output


def _density_tradeoff_p2(p1: list[Event]) -> list[Event]:
    by_bar: list[list[Event]] = [[] for _ in range(BARS)]
    for event in p1:
        by_bar[min(int(event.start_beat // BEATS_PER_BAR), BARS - 1)].append(event)

    output: list[Event] = []
    for bar, root in enumerate(_ROOTS):
        base = bar * BEATS_PER_BAR
        dense_foreground = len(by_bar[bar]) >= 6
        if dense_foreground:
            # When P1 is busy, P2 yields onset density and uses only two anchors.
            output.extend(
                [
                    Event(root + 24, base, 1.5, 0.54),
                    Event(root + 31, base + 2.0, 1.5, 0.52),
                ]
            )
        else:
            # When P1 is sparse, P2 fills the holes with a compact chip-like cell.
            pitches = (root + 24, root + 28, root + 31, root + 36)
            for step in range(8):
                output.append(Event(pitches[step % 4], base + step * 0.5, 0.42, 0.48))
    return output


def build_variants() -> dict[str, dict[str, list[Event]]]:
    p1 = _flatten_melody()
    triangle = _triangle_bass()
    noise = _noise_groove()
    p2_builders = {
        "00_plain": lambda: _plain_p2(),
        "01_interval_lock": lambda: _interval_lock_p2(p1),
        "02_block_switch": lambda: _block_switch_p2(p1),
        "03_phase_interlock": lambda: _phase_interlock_p2(p1),
        "04_density_tradeoff": lambda: _density_tradeoff_p2(p1),
    }
    return {
        name: {
            "pulse_1": list(p1),
            "pulse_2": builder(),
            "triangle": list(triangle),
            "noise": list(noise),
        }
        for name, builder in p2_builders.items()
    }


def _assert_monophonic(events: list[Event], voice: str) -> None:
    ordered = sorted(events, key=lambda event: (event.start_beat, event.end_beat))
    previous_end = -1.0
    for event in ordered:
        if event.start_beat < previous_end - 1e-9:
            raise ValueError(f"{voice} overlaps at beat {event.start_beat}")
        previous_end = max(previous_end, event.end_beat)


def validate_variant(tracks: dict[str, list[Event]]) -> None:
    for voice in ("pulse_1", "pulse_2", "triangle", "noise"):
        _assert_monophonic(tracks[voice], voice)
    for voice in ("pulse_1", "pulse_2", "triangle"):
        for event in tracks[voice]:
            if not 0 <= event.pitch <= 127:
                raise ValueError(f"{voice} MIDI pitch out of range: {event.pitch}")


def _midi_track(name: str, events: list[Event], *, channel: int, program: int | None) -> mido.MidiTrack:
    track = mido.MidiTrack()
    track.append(mido.MetaMessage("track_name", name=name, time=0))
    if program is not None:
        track.append(mido.Message("program_change", channel=channel, program=program, time=0))

    timeline: list[tuple[int, int, mido.Message]] = []
    for event in events:
        start_tick = round(event.start_beat * TICKS_PER_BEAT)
        end_tick = round(event.end_beat * TICKS_PER_BEAT)
        velocity = max(1, min(127, round(event.velocity * 127)))
        note = event.pitch
        # Sort note-offs before note-ons when they share a tick.
        timeline.append((start_tick, 1, mido.Message("note_on", channel=channel, note=note, velocity=velocity, time=0)))
        timeline.append((end_tick, 0, mido.Message("note_off", channel=channel, note=note, velocity=0, time=0)))

    previous_tick = 0
    for tick, _, message in sorted(timeline, key=lambda item: (item[0], item[1])):
        message.time = tick - previous_tick
        track.append(message)
        previous_tick = tick
    return track


def write_midi(path: str | Path, tracks: dict[str, list[Event]]) -> Path:
    validate_variant(tracks)
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    midi = mido.MidiFile(type=1, ticks_per_beat=TICKS_PER_BEAT)
    meta = mido.MidiTrack()
    meta.append(mido.MetaMessage("track_name", name="meta", time=0))
    meta.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(TEMPO_BPM), time=0))
    meta.append(mido.MetaMessage("time_signature", numerator=4, denominator=4, time=0))
    midi.tracks.append(meta)
    midi.tracks.append(_midi_track("P1", tracks["pulse_1"], channel=0, program=80))
    midi.tracks.append(_midi_track("P2", tracks["pulse_2"], channel=1, program=80))
    midi.tracks.append(_midi_track("TR", tracks["triangle"], channel=2, program=38))
    midi.tracks.append(_midi_track("NO", tracks["noise"], channel=9, program=None))
    midi.save(output)
    return output


def _midi_frequency(note: int) -> float:
    return 440.0 * (2.0 ** ((note - 69) / 12.0))


def _envelope(position: int, length: int, attack: int, release: int) -> float:
    if length <= 0:
        return 0.0
    if attack > 0 and position < attack:
        return position / attack
    remaining = length - position - 1
    if release > 0 and remaining < release:
        return max(0.0, remaining / release)
    return 1.0


def _add_square(buffer: array, event: Event, *, duty: float, gain: float) -> None:
    seconds_per_beat = 60.0 / TEMPO_BPM
    start = round(event.start_beat * seconds_per_beat * SAMPLE_RATE)
    length = max(1, round(event.duration_beats * seconds_per_beat * SAMPLE_RATE))
    end = min(len(buffer), start + length)
    freq = _midi_frequency(event.pitch)
    phase = 0.0
    increment = freq / SAMPLE_RATE
    attack = max(1, round(0.002 * SAMPLE_RATE))
    release = max(1, round(0.018 * SAMPLE_RATE))
    for sample_index in range(start, end):
        local = sample_index - start
        env = _envelope(local, end - start, attack, release)
        value = 1.0 if phase < duty else -1.0
        buffer[sample_index] += value * gain * event.velocity * env
        phase = (phase + increment) % 1.0


def _add_triangle(buffer: array, event: Event, *, gain: float) -> None:
    seconds_per_beat = 60.0 / TEMPO_BPM
    start = round(event.start_beat * seconds_per_beat * SAMPLE_RATE)
    length = max(1, round(event.duration_beats * seconds_per_beat * SAMPLE_RATE))
    end = min(len(buffer), start + length)
    freq = _midi_frequency(event.pitch)
    phase = 0.0
    increment = freq / SAMPLE_RATE
    attack = max(1, round(0.003 * SAMPLE_RATE))
    release = max(1, round(0.025 * SAMPLE_RATE))
    for sample_index in range(start, end):
        local = sample_index - start
        env = _envelope(local, end - start, attack, release)
        tri = 4.0 * abs(phase - 0.5) - 1.0
        buffer[sample_index] += tri * gain * event.velocity * env
        phase = (phase + increment) % 1.0


def _add_noise(buffer: array, event: Event, *, seed: int, gain: float) -> None:
    seconds_per_beat = 60.0 / TEMPO_BPM
    start = round(event.start_beat * seconds_per_beat * SAMPLE_RATE)
    requested = 0.115 if event.pitch == 38 else 0.045
    length = max(1, round(requested * SAMPLE_RATE))
    end = min(len(buffer), start + length)
    state = seed & 0xFFFFFFFF
    previous = 0.0
    for sample_index in range(start, end):
        local = sample_index - start
        state = (1664525 * state + 1013904223) & 0xFFFFFFFF
        white = ((state / 0xFFFFFFFF) * 2.0) - 1.0
        # A tiny one-pole blend keeps it crunchy instead of painfully white.
        previous = 0.42 * previous + 0.58 * white
        decay = (1.0 - local / max(1, end - start)) ** (2.8 if event.pitch == 42 else 1.7)
        buffer[sample_index] += previous * gain * event.velocity * decay


def write_wav(path: str | Path, tracks: dict[str, list[Event]]) -> Path:
    validate_variant(tracks)
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    total_seconds = TOTAL_BEATS * (60.0 / TEMPO_BPM) + 0.35
    sample_count = math.ceil(total_seconds * SAMPLE_RATE)
    buffer = array("f", [0.0]) * sample_count

    for event in tracks["pulse_1"]:
        _add_square(buffer, event, duty=0.25, gain=0.19)
    for event in tracks["pulse_2"]:
        _add_square(buffer, event, duty=0.50, gain=0.135)
    for event in tracks["triangle"]:
        _add_triangle(buffer, event, gain=0.22)
    for index, event in enumerate(tracks["noise"]):
        _add_noise(buffer, event, seed=0xC0FFEE + index * 7919, gain=0.13)

    peak = max((abs(value) for value in buffer), default=1.0)
    scale = 0.92 / peak if peak > 0 else 1.0
    pcm = array("h", (max(-32767, min(32767, round(value * scale * 32767))) for value in buffer))

    with wave.open(str(output), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(pcm.tobytes())
    return output


def export_ab_pack(directory: str | Path) -> dict[str, object]:
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    variants = build_variants()
    manifest: dict[str, object] = {
        "experiment": "pulse_recipe_ab_v1",
        "constraint_mode": "hardware_inspired",
        "tempo_bpm": TEMPO_BPM,
        "bars": BARS,
        "fixed_tracks": ["pulse_1", "triangle", "noise"],
        "variable_track": "pulse_2",
        "variants": {},
        "listening_rule": "Compare arrangement behavior, not mastering. P1/TR/NO are byte-for-byte event-identical across variants.",
    }

    descriptions = {
        "00_plain": "Baseline: two sparse chord anchors per bar; no corpus-derived P1/P2 relationship recipe.",
        "01_interval_lock": "P2 copies P1 one octave lower for exact synchronized interval locking.",
        "02_block_switch": "P2 copies P1 while the exact interval changes by four-bar phrase: -12, -5, +7, +12 semitones.",
        "03_phase_interlock": "P2 copies P1 pitch identity with a stable +0.25 beat phase offset.",
        "04_density_tradeoff": "P2 yields to two anchors in dense P1 bars and becomes an 8th-note fill cell in sparse P1 bars.",
    }

    for name, tracks in variants.items():
        validate_variant(tracks)
        midi_path = write_midi(root / f"{name}.mid", tracks)
        wav_path = write_wav(root / f"{name}.wav", tracks)
        manifest["variants"][name] = {
            "description": descriptions[name],
            "p2_note_count": len(tracks["pulse_2"]),
            "midi": midi_path.name,
            "wav": wav_path.name,
        }

    (root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (root / "README.txt").write_text(
        "Pulse Recipe A/B v1\n\n"
        "Listen in filename order. Every version keeps P1 melody, Triangle bass, Noise groove, tempo, form, and renderer fixed.\n"
        "Only Pulse 2 arrangement changes.\n\n"
        + "\n".join(f"{name}: {descriptions[name]}" for name in descriptions)
        + "\n",
        encoding="utf-8",
    )
    return manifest
