# Chiptune composition notes

This document collects composition-level guidance that is useful before any renderer exists.

## 1. Treat polyphony as a budget

The central arrangement problem is not "which synth patch should play this part?" It is "which musical information deserves one of the available voices right now?"

For each phrase, rank the information:

1. foreground identity, usually the motif or melody;
2. pulse/energy information, such as rhythmic comping or repeated-note drive;
3. harmonic implication;
4. bass/root motion;
5. transient/percussion information.

A low-priority role may disappear temporarily when a more important gesture needs the channel.

## 2. Imply harmony instead of spelling every chord

With limited melodic voices, harmony can be communicated through:

- alternating chord tones over time;
- rapid arpeggiation;
- bass note + melody note combinations;
- parallel thirds/sixths used selectively;
- counter-lines that touch structural chord tones;
- phrase endings that make the harmony explicit after a sparse interior.

The goal is perceptual harmony, not maximum simultaneous chord density.

## 3. Separate roles by register and rhythm

When two pulse voices live in the same register and use the same rhythm continuously, they flatten into one block. Contrast can come from:

- different registers;
- different note lengths;
- alternating activity;
- call and response;
- sustained vs. articulated motion;
- foreground/background density changes.

## 4. Leave deliberate holes

Silence is useful because every active channel competes for attention. Rests can create:

- phrase boundaries;
- anticipation before a hook;
- room for a counter-line;
- room for noise percussion;
- clearer bass attacks;
- stronger re-entry of the lead.

## 5. Prefer motifs over note soup

A chiptune lead benefits from a recognizable cell that can be varied by:

- transposition;
- rhythmic displacement;
- truncation;
- extension;
- octave displacement;
- answer phrases;
- altered cadence notes.

Short hardware-friendly notes do not require short musical ideas.

## 6. Sound design can behave like articulation

Pulse duty, envelope shape, pitch ornaments, note cuts, and register shifts can mark phrase function. They should be attached to musical intent rather than changed randomly for novelty.

## 7. Complexity modes

A future arranger should expose musical complexity separately from hardware strictness.

Possible composition complexity levels:

- `simple`: one clear motif, sparse support, obvious repetition;
- `standard`: counter-lines, variation, selective arpeggiation;
- `dense`: frequent role exchange, ornaments, faster harmonic implication.

Do not equate "more 8-bit" with "more notes".
