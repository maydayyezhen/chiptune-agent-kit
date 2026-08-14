from __future__ import annotations

from typing import Any

from chiptune_agent_kit.ir import ChipProject


VOICE_TYPES = {
    "pulse_1": "pulse",
    "pulse_2": "pulse",
    "triangle": "triangle",
    "noise": "noise",
}
SUPPORTED_DUTIES = {0.125, 0.25, 0.5, 0.75}


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_nes2a03(project: ChipProject) -> dict[str, list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if project.target != "nes_2a03":
        errors.append(f"target must be 'nes_2a03', got {project.target!r}")

    if project.tempo_bpm <= 0:
        errors.append("tempo_bpm must be positive")

    if project.constraint_mode not in {"8bit_aesthetic", "hardware_inspired", "strict_platform"}:
        errors.append(f"unknown constraint_mode: {project.constraint_mode!r}")

    for voice_name, required_type in VOICE_TYPES.items():
        voice = project.voices.get(voice_name)
        if voice is None:
            errors.append(f"missing required voice: {voice_name}")
            continue
        if voice.voice_type != required_type:
            errors.append(
                f"{voice_name}.type must be {required_type!r}, got {voice.voice_type!r}"
            )
            continue

        normalized_events: list[tuple[float, float, int]] = []
        for index, event in enumerate(voice.events):
            prefix = f"{voice_name}.events[{index}]"
            if not isinstance(event, dict):
                errors.append(f"{prefix} must be an object")
                continue

            start = event.get("start_beat")
            duration = event.get("duration_beats")
            if not _number(start) or start < 0:
                errors.append(f"{prefix}.start_beat must be a non-negative number")
                continue
            if not _number(duration) or duration <= 0:
                errors.append(f"{prefix}.duration_beats must be a positive number")
                continue

            end = float(start) + float(duration)
            normalized_events.append((float(start), end, index))

            if required_type in {"pulse", "triangle"}:
                midi_note = event.get("midi_note")
                if not isinstance(midi_note, int) or isinstance(midi_note, bool) or not 0 <= midi_note <= 127:
                    errors.append(f"{prefix}.midi_note must be an integer from 0 to 127")

            if required_type == "pulse" and "duty" in event:
                duty = event["duty"]
                if duty not in SUPPORTED_DUTIES:
                    errors.append(
                        f"{prefix}.duty must be one of {sorted(SUPPORTED_DUTIES)}, got {duty!r}"
                    )

            if required_type == "triangle" and "duty" in event:
                errors.append(f"{prefix}: triangle events do not support pulse duty")

            if required_type == "noise":
                period = event.get("noise_period")
                mode = event.get("mode", "long")
                if not isinstance(period, int) or isinstance(period, bool) or not 0 <= period <= 15:
                    errors.append(f"{prefix}.noise_period must be an integer from 0 to 15")
                if mode not in {"long", "short"}:
                    errors.append(f"{prefix}.mode must be 'long' or 'short'")
                if "midi_note" in event:
                    warnings.append(f"{prefix}.midi_note is ignored for the noise voice")

        normalized_events.sort(key=lambda item: (item[0], item[1]))
        for previous, current in zip(normalized_events, normalized_events[1:]):
            previous_start, previous_end, previous_index = previous
            current_start, _, current_index = current
            if current_start < previous_end:
                errors.append(
                    f"{voice_name} is monophonic: events[{previous_index}] overlaps events[{current_index}]"
                )

    extra = sorted(set(project.voices) - set(VOICE_TYPES) - {"dpcm"})
    for voice_name in extra:
        warnings.append(f"unrecognized extra voice {voice_name!r} is not validated")

    if "dpcm" in project.voices:
        warnings.append("dpcm is present but v0.1 does not validate DPCM behavior yet")

    return {"errors": errors, "warnings": warnings}
