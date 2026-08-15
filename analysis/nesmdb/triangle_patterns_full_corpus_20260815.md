# NES-MDB Triangle Pattern Discovery Snapshot

- workflow run: `31859230404`
- workflow head: `abc76c8f7b19681c98891be8744d9faaefa96b23`
- artifact id: `9240025736`
- corpus files: `5278`
- songs with clean Triangle notes: `4676`
- windows scanned: `36611`
- composition micro-note floor: `<= 0.001 s`
- window / step: `8 s / 4 s`
- status: exploratory, not yet SKILL rules

## First-pass discovery buckets

| pattern | songs | prevalence among Triangle songs | episodes | median episode |
|---|---:|---:|---:|---:|
| repeated_note_drive | 967 | 20.680% | 1282 | 12.53s |
| octave_pump | 250 | 5.346% | 304 | 12.00s |
| dominant_pitch_pedal | 663 | 14.179% | 944 | 8.67s |
| stepwise_motion | 1038 | 22.198% | 1322 | 10.34s |

## Co-occurrence observation

`dominant_pitch_pedal + repeated_note_drive` occurs in 524 songs. This is 79.0% of pedal songs and 54.2% of repeated-drive songs, so the two phenomena are related but not identical. The casebook therefore includes a special pedal-with-excursions lens that excludes windows with repeated-transition ratio >= 0.70.

## Casebook observations

### Repeated-note drive

Representative windows are extremely literal: one Triangle pitch is retriggered many times with no pitch change. Examples include 35 repeated C3 notes in Bubble Bobble Real Ending and 54 repeated C#3 notes in Megami Tensei Title. This looks like a strong candidate for a rhythm-drive operator rather than a harmonic operator.

### Octave behavior

The first-pass `octave_pump` bucket contains at least two distinct structures:

1. two-register alternation such as `G2 G3 G2 G3 ...` or `C3 C4 C3 C4 ...`;
2. multi-register cycles such as `F3 F4 F5 F4 F3 ...`.

These should be separated before promotion to recipes.

### Pedal with excursions

After excluding heavy repeated-note windows, representative sequences often return to an anchor pitch after short excursions:

- `A2 C3 A2 B2 A2 A2`
- `D3 F#3 D3 D3 F#3 D3`
- `G#2 B2 G#2 G#2 B2 G#2`
- `C4 B3 C4 C#4 C4 C4`

This suggests a more actionable candidate concept than generic pedal tone: `anchor -> excursion -> return`.

### Stepwise motion

The first-pass stepwise bucket also contains multiple structures:

1. directional scalar runs, e.g. `G#2 A2 A#2 B2 C3 C#3 D3 D#3`;
2. neighbor oscillation, e.g. `E3 F3 E3 F3 ...`;
3. turning/ornamental cells around a center pitch.

These should be separated before recipe promotion.

## Next refinement

Refine the coarse buckets into neutral, executable candidates:

- `two_register_octave_pump`
- `multi_register_octave_cycle`
- `anchor_return_pattern`
- `directional_step_run`
- `neighbor_oscillation`
- retain `repeated_note_drive`

Then rerun the full corpus, inspect representative windows, and only after listening/A-B composition tests decide which become durable arranging recipes.
