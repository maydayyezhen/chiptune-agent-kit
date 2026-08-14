from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median
from typing import Any

import mido


VOICE_ALIASES = {
    "p1": "pulse_1",
    "pulse1": "pulse_1",
    "pulse_1": "pulse_1",
    "p2": "pulse_2",
    "pulse2": "pulse_2",
    "pulse_2": "pulse_2",
    "tr": "triangle",
    "tri": "triangle",
    "triangle": "triangle",
    "no": "noise",
    "noise": "noise",
}


@dataclass(frozen=True)
class NoteSpan:
    pitch: int
    start_seconds: float
    end_seconds: float

    @property
    def duration_seconds(self) -> float:
        return max(0.0, self.end_seconds - self.start_seconds)


def _normalize_name(name: str) -> str | None:
    compact = name.strip().lower().replace("-", "_").replace(" ", "_")
    return VOICE_ALIASES.get(compact)


def _tempo_map(mid: mido.MidiFile) -> list[tuple[int, int]]:
    changes: list[tuple[int, int]] = [(0, 500000)]
    for track in mid.tracks:
        tick = 0
        for msg in track:
            tick += msg.time
            if msg.type == "set_tempo":
                changes.append((tick, msg.tempo))
    changes.sort(key=lambda item: item[0])

    collapsed: list[tuple[int, int]] = []
    for tick, tempo in changes:
        if collapsed and collapsed[-1][0] == tick:
            collapsed[-1] = (tick, tempo)
        else:
            collapsed.append((tick, tempo))
    return collapsed


def _tick_to_seconds(tick: int, ticks_per_beat: int, tempo_map: list[tuple[int, int]]) -> float:
    seconds = 0.0
    previous_tick = 0
    current_tempo = 500000

    for change_tick, new_tempo in tempo_map:
        if change_tick > tick:
            break
        if change_tick > previous_tick:
            seconds += mido.tick2second(change_tick - previous_tick, ticks_per_beat, current_tempo)
            previous_tick = change_tick
        current_tempo = new_tempo

    if tick > previous_tick:
        seconds += mido.tick2second(tick - previous_tick, ticks_per_beat, current_tempo)
    return seconds


def _active_time_ratio(spans: list[NoteSpan], total_seconds: float) -> float:
    if not spans or total_seconds <= 0:
        return 0.0

    intervals = sorted((s.start_seconds, s.end_seconds) for s in spans if s.end_seconds > s.start_seconds)
    if not intervals:
        return 0.0

    active = 0.0
    start, end = intervals[0]
    for next_start, next_end in intervals[1:]:
        if next_start <= end:
            end = max(end, next_end)
        else:
            active += end - start
            start, end = next_start, next_end
    active += end - start
    return min(1.0, active / total_seconds)


def _voice_stats(spans: list[NoteSpan], total_seconds: float, cc11_changes: int, cc12_changes: int) -> dict[str, Any]:
    if not spans:
        return {
            "note_count": 0,
            "pitch_range": None,
            "mean_duration_seconds": None,
            "median_duration_seconds": None,
            "mean_inter_onset_seconds": None,
            "active_time_ratio": 0.0,
            "cc11_changes": cc11_changes,
            "cc12_changes": cc12_changes,
        }

    durations = [span.duration_seconds for span in spans]
    onsets = sorted(span.start_seconds for span in spans)
    iois = [b - a for a, b in zip(onsets, onsets[1:]) if b >= a]
    pitches = [span.pitch for span in spans]

    return {
        "note_count": len(spans),
        "pitch_range": [min(pitches), max(pitches)],
        "mean_duration_seconds": mean(durations),
        "median_duration_seconds": median(durations),
        "mean_inter_onset_seconds": mean(iois) if iois else None,
        "active_time_ratio": _active_time_ratio(spans, total_seconds),
        "cc11_changes": cc11_changes,
        "cc12_changes": cc12_changes,
    }


def analyze_nes_midi(path: str | Path) -> dict[str, Any]:
    """Analyze separated NES-style MIDI tracks without assuming stored BPM is musical truth."""

    midi_path = Path(path)
    mid = mido.MidiFile(midi_path)
    tempo_map = _tempo_map(mid)

    spans: dict[str, list[NoteSpan]] = {name: [] for name in ("pulse_1", "pulse_2", "triangle", "noise")}
    controller_counts = {
        name: {11: 0, 12: 0}
        for name in spans
    }
    total_ticks = 0

    for track in mid.tracks:
        abs_tick = 0
        voice_name: str | None = None
        active: dict[tuple[int, int], list[int]] = {}

        for msg in track:
            abs_tick += msg.time
            total_ticks = max(total_ticks, abs_tick)

            if msg.type == "track_name":
                voice_name = _normalize_name(msg.name)
                continue

            if voice_name is None:
                continue

            if msg.type == "control_change" and msg.control in (11, 12):
                controller_counts[voice_name][msg.control] += 1
                continue

            if msg.type == "note_on" and msg.velocity > 0:
                active.setdefault((msg.channel, msg.note), []).append(abs_tick)
                continue

            is_note_off = msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0)
            if not is_note_off:
                continue

            key = (msg.channel, msg.note)
            starts = active.get(key)
            if not starts:
                continue

            start_tick = starts.pop(0)
            if not starts:
                active.pop(key, None)

            spans[voice_name].append(
                NoteSpan(
                    pitch=msg.note,
                    start_seconds=_tick_to_seconds(start_tick, mid.ticks_per_beat, tempo_map),
                    end_seconds=_tick_to_seconds(abs_tick, mid.ticks_per_beat, tempo_map),
                )
            )

    total_seconds = _tick_to_seconds(total_ticks, mid.ticks_per_beat, tempo_map)

    return {
        "source": str(midi_path),
        "ticks_per_beat": mid.ticks_per_beat,
        "stored_initial_tempo_bpm": mido.tempo2bpm(tempo_map[0][1]),
        "duration_seconds": total_seconds,
        "timing_note": "Stored MIDI tempo is descriptive container metadata; do not assume it is the original musical BPM.",
        "voices": {
            name: _voice_stats(
                voice_spans,
                total_seconds,
                controller_counts[name][11],
                controller_counts[name][12],
            )
            for name, voice_spans in spans.items()
        },
    }
