---
name: chiptune-agent-kit
summary: Compose, study, validate, and later render chiptune music by treating hardware constraints as arrangement grammar rather than merely swapping ordinary MIDI instruments for square waves.
status: experimental
---

# Chiptune Agent Kit

## Purpose

Use this repository when a task asks for 8-bit, chiptune, chip-music, NES-style, Game-Boy-like, pulse-wave, tracker-inspired, or limited-voice game music.

The project is deliberately split into three concerns:

1. **Composition**: musical form, motifs, harmony, bass motion, rhythmic density, role exchange.
2. **Chip performance**: voice allocation, duty/waveform state, noise behavior, pitch ornaments, channel-specific constraints.
3. **Rendering/export**: synthesis, tracker export, audio generation, and compatibility adapters.

Do not collapse those layers into one opaque `generate_chiptune()` step.

## First decision: constraint mode

Choose one mode before composing:

- `8bit_aesthetic`: chip-like sound, flexible voice count, no claim of hardware authenticity.
- `hardware_inspired`: explicit limited voice budget based on a target profile, but no cycle-accurate claim.
- `strict_platform`: only use verified platform behavior and validated constraints. Do not invent unsupported hardware facts.

For the current v0.1 code, `nes_2a03` validation means the four non-DPCM voices modeled by this project: two pulse voices, one triangle voice, and one noise voice. DPCM is intentionally deferred.

## Mandatory composition principle

Do **not** arrange a normal pop/rock/orchestral MIDI first and then replace every instrument with a square wave.

Limited polyphony is a compositional resource. Before writing notes, decide:

- which voice owns the foreground;
- which voice implies harmony;
- which voice owns the low register;
- which voice carries transient/percussion information;
- when a role must yield to another role;
- where silence is more useful than another simultaneous note.

Voice roles are defaults, not permanent identities.

## NES-style starting map

A useful initial assignment is:

```text
Pulse 1   foreground melody / lead
Pulse 2   counter-line / harmony implication / rhythmic comping
Triangle  bass / low-register motion
Noise     percussion / transient rhythm
```

Do not hard-code this map into composition logic. Reassign roles when the phrase requires it.

## Reference-first workflow

When learning a new style or technique:

1. Read `references/reference-analysis.md`.
2. Analyze representative source material with `chiptune-analyze`.
3. Separate observations from conclusions.
4. Promote only repeated, musically useful observations into reference/material documents.
5. Compose a small controlled example.
6. Validate it with `chiptune-validate`.
7. Only then generalize the rule.

Do not copy a single game's exact melody, bass line, or arpeggio pattern into the Skill as a universal rule.

## Chiptune vocabulary to investigate

Useful phenomena include:

- fast arpeggiation used to imply harmony;
- counter-melody instead of continuous chord pads;
- octave displacement and register sharing;
- repeated-note drive;
- short pickup ornaments;
- sparse phrases with explicit rests;
- duty changes as articulation/timbre motion;
- pitch slides and vibrato-like motion;
- triangle bass patterns;
- noise-based kick/snare/hat roles;
- voice stealing and role priority under a strict channel budget.

These are research targets, not permission to apply every technique everywhere.

## Data policy

Keep source datasets out of Git by default. Put local corpora under `datasets/`, which is ignored.

For every external corpus or reference collection, record:

- source URL;
- license or usage notes;
- extraction assumptions;
- whether timing is musical-beat based or absolute-time based;
- which fields are authoritative and which are derived.

## Current commands

```powershell
pip install -e ".[dev]"

chiptune-analyze path\to\song.mid
chiptune-validate examples\nes_basic_project.json
pytest
```

## Failure modes

Revise the result when:

- it is an ordinary full-band arrangement wearing square-wave patches;
- all melodic voices are continuously busy;
- every harmony is represented as simultaneous chord tones;
- a strict console is claimed without verified platform rules;
- chip-specific state is forced into generic MIDI and silently lost;
- reference analysis treats an arbitrary stored MIDI tempo as the original musical BPM;
- a renderer-specific parameter leaks into general composition rules;
- one reference track becomes a fixed template copied into every composition.

## Growth rule

Grow this repository in this order:

```text
reference study
-> reusable observation
-> explicit representation
-> validator / transformation
-> controlled composition test
-> renderer/export backend
```

The representation should earn complexity from evidence. Do not pre-build a giant chip engine around assumptions.
