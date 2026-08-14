# chiptune-agent-kit

Agent-friendly composition, analysis, validation, and rendering tools for chiptune music.

The project starts with an NES / 2A03-oriented workflow and is designed to grow toward Game Boy, SID, and modern chiptune targets without forcing chip-specific state into a generic composition schema.

## Core idea

Chiptune is not ordinary MIDI with square-wave instruments. Hardware constraints are part of the arrangement language.

The initial NES-style target models these musical roles:

- Pulse 1: lead or foreground voice
- Pulse 2: counter-melody, harmony implication, rhythmic comping, or alternate lead
- Triangle: bass and low-register motion
- Noise: percussion and transient rhythm
- DPCM: optional sampled accents, planned for a later milestone

Voice roles are conventions, not hard-coded identities. The arranger should be able to reassign them when the musical context requires it.

## v0.1 goals

1. Analyze NES-MDB-style MIDI reference material.
2. Extract reusable composition and performance observations.
3. Validate structured NES 2A03 voice projects against useful musical/hardware constraints.
4. Keep composition, chip performance, and rendering as separate layers.
5. Give a general-purpose coding/music agent a small, explicit SKILL.md to follow.

## Planned flow

```text
reference MIDI / NES-MDB
        |
        v
reference analyzer
        |
        v
analysis artifacts + distilled materials
        |
        v
LLM / agent composition
        |
        v
chip arrangement / performance IR
        |
        v
2A03 validator
        |
        v
renderer / exporter
```

## Repository layout

```text
SKILL.md
references/
  composition.md
  nes-2a03.md
  reference-analysis.md
src/chiptune_agent_kit/
  analysis/
  ir/
  validation/
scripts/
tests/
examples/
```

## Status

Early experimental project. The first implementation target is analysis + validation. Rendering comes after the musical representation and rules have been tested against real NES music.
