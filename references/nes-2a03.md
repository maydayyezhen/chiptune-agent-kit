# NES / 2A03 target notes

The NES APU provides a useful first strict-platform target because its limited voices strongly shape arrangement decisions.

## Voice model used by this project

The v0.1 validator models:

- `pulse_1`: pulse voice
- `pulse_2`: pulse voice
- `triangle`: triangle voice
- `noise`: noise voice

The real APU also includes a DMC/DPCM sample channel. This toolkit intentionally postpones DPCM modeling until its data representation and renderer behavior are designed explicitly.

## Pulse voices

For the current project representation, pulse events may optionally specify one of the familiar duty proportions:

- `0.125`
- `0.25`
- `0.5`
- `0.75`

A pulse voice is monophonic in the v0.1 IR, so overlapping note events on the same voice are validation errors.

## Triangle voice

The triangle voice is modeled as a monophonic pitched voice. It is a natural bass candidate, but the toolkit does not make "triangle = bass" a permanent semantic rule.

## Noise voice

Noise events use a `noise_period` index from `0` through `15` plus a `mode` of `long` or `short` in the current IR. Noise is treated as transient/percussion information rather than a pitched MIDI note stream.

## Provenance

Primary references to consult before expanding strict behavior:

- NESdev APU overview: https://www.nesdev.org/wiki/APU
- NESdev pulse channel: https://www.nesdev.org/wiki/APU_Pulse
- NESdev triangle channel: https://www.nesdev.org/wiki/APU_Triangle
- NESdev noise channel: https://www.nesdev.org/wiki/APU_Noise
- FamiStudio documentation: https://famistudio.org/doc/
- Furnace NES instrument documentation: https://tildearrow.org/furnace/doc/latest/4-instrument/nes.html

When code and documentation disagree, do not silently pick whichever behavior is convenient. Record the discrepancy and keep strict-platform claims conservative.
