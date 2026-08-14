from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Voice:
    voice_type: str
    events: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Voice":
        return cls(
            voice_type=str(data.get("type", "")),
            events=list(data.get("events", [])),
        )


@dataclass
class ChipProject:
    target: str
    tempo_bpm: float
    voices: dict[str, Voice]
    constraint_mode: str = "hardware_inspired"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChipProject":
        voices_raw = data.get("voices", {})
        voices = {
            str(name): Voice.from_dict(voice_data)
            for name, voice_data in voices_raw.items()
            if isinstance(voice_data, dict)
        }
        return cls(
            target=str(data.get("target", "")),
            tempo_bpm=float(data.get("tempo_bpm", 120.0)),
            voices=voices,
            constraint_mode=str(data.get("constraint_mode", "hardware_inspired")),
        )
