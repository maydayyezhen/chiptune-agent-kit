from pathlib import Path

import mido

from chiptune_agent_kit.analysis import analyze_nes_midi


def test_analyzer_recognizes_nes_voice_tracks(tmp_path: Path) -> None:
    path = tmp_path / "tiny.mid"
    mid = mido.MidiFile(ticks_per_beat=480)

    meta = mido.MidiTrack()
    meta.append(mido.MetaMessage("set_tempo", tempo=500000, time=0))
    mid.tracks.append(meta)

    pulse = mido.MidiTrack()
    pulse.append(mido.MetaMessage("track_name", name="p1", time=0))
    pulse.append(mido.Message("control_change", control=11, value=100, time=0))
    pulse.append(mido.Message("control_change", control=12, value=2, time=0))
    pulse.append(mido.Message("note_on", note=72, velocity=100, time=0))
    pulse.append(mido.Message("note_off", note=72, velocity=0, time=480))
    mid.tracks.append(pulse)

    triangle = mido.MidiTrack()
    triangle.append(mido.MetaMessage("track_name", name="tr", time=0))
    triangle.append(mido.Message("note_on", note=36, velocity=100, time=0))
    triangle.append(mido.Message("note_off", note=36, velocity=0, time=480))
    mid.tracks.append(triangle)

    mid.save(path)

    result = analyze_nes_midi(path)
    assert result["voices"]["pulse_1"]["note_count"] == 1
    assert result["voices"]["pulse_1"]["pitch_range"] == [72, 72]
    assert result["voices"]["pulse_1"]["cc11_changes"] == 1
    assert result["voices"]["pulse_1"]["cc12_changes"] == 1
    assert result["voices"]["triangle"]["note_count"] == 1
