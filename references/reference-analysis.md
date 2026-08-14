# Reference analysis workflow

## Why analyze references

The goal is not to clone songs. It is to discover reusable arrangement behavior that an agent can apply under similar constraints.

A good observation looks like:

> The secondary pulse becomes sparser while the foreground pulse is rhythmically dense, then answers in the lead's rests.

A bad observation looks like:

> Copy these eight notes because they sound like an NES game.

## NES-MDB as a useful corpus

NES-MDB provides thousands of NES tracks converted into symbolic representations. Its MIDI-oriented representation is especially useful for automated study because voices are separated.

Project/paper references:

- Repository: https://github.com/chrisdonahue/nesmdb
- Paper: https://arxiv.org/abs/1806.04278

The corpus distinguishes the NES voices commonly named `p1`, `p2`, `tr`, and `no`. Expressive information can include controller data for dynamics/timbre.

## Important timing warning

Do not assume the MIDI file's stored tempo is the original musical BPM.

NES-MDB uses MIDI as an event container with high temporal resolution. Analyze absolute onset times, durations, inter-onset intervals, repetition, and cross-voice relationships first. Estimate a musical grid separately when a bar/beat interpretation is needed.

## First-pass metrics

The v0.1 analyzer extracts per recognized voice:

- note count;
- pitch range;
- mean/median note duration;
- mean inter-onset interval;
- active-time ratio;
- controller 11 change count;
- controller 12 change count.

These metrics are descriptive, not composition rules by themselves.

## Phenomena worth detecting later

Future analyzers should investigate:

- rapid chord-tone cycling;
- repeated-note drive;
- octave bass motion;
- pedal bass;
- call/response between pulse voices;
- parallel intervals;
- phrase-rest placement;
- motif repetition and variation;
- noise rhythm families;
- timbre/duty changes near phrase boundaries;
- pitch-slide and vibrato-like gestures;
- voice stealing / temporary role reassignment.

Any heuristic detector should expose its confidence and thresholds. Do not turn a fuzzy musical guess into a fake ground-truth label.
