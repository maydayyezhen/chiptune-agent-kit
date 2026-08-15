# Refined Triangle Recipe Candidate Snapshot

- workflow run: `31859416017`
- workflow head: `fb68072b58588b96826920940f323be00e81ddb1`
- artifact id: `9240081114`
- corpus files: `5278`
- songs with clean Triangle: `4676`
- windows scanned: `36611`
- composition floor: `<= 0.001 s`
- window / step: `8 s / 4 s`
- status: candidate recipes, awaiting listening/A-B validation

## Refined prevalence

| candidate | songs | prevalence | episodes | median episode |
|---|---:|---:|---:|---:|
| directional_step_run | 1239 | 26.497% | 1585 | 12.00s |
| repeated_note_drive | 1013 | 21.664% | 1337 | 12.40s |
| anchor_return_pattern | 405 | 8.661% | 608 | 12.00s |
| two_register_octave_pump | 27 | 0.577% | 30 | 8.00s |
| neighbor_oscillation | 26 | 0.556% | 33 | 12.00s |
| multi_register_octave_cycle | 2 | 0.043% | 4 | 10.00s |

## Interpretation

### Core listening candidates

`directional_step_run`, `repeated_note_drive`, and `anchor_return_pattern` have enough corpus support to justify controlled composition tests. They should be treated as local Triangle arrangement operations, not whole-song styles.

### Specialty candidates

`two_register_octave_pump` and `neighbor_oscillation` are much rarer under the strict refined definitions. They may still be useful as specialty gestures, but prevalence does not support treating them as default Triangle behavior.

`multi_register_octave_cycle` appears in only two songs under the strict detector and should remain a reference curiosity unless broader sensitivity analysis shows the detector is too strict.

## Candidate semantics

- `repeated_note_drive`: retrigger one pitch to create rhythmic propulsion while harmonic pitch remains stable.
- `anchor_return_pattern`: repeatedly leave a dominant anchor for a short excursion and return, e.g. `A -> C -> A -> B -> A`.
- `directional_step_run`: move for at least five notes in one direction using semitone/whole-tone steps.
- `two_register_octave_pump`: alternate one pitch class between two registers separated by an octave.
- `neighbor_oscillation`: alternate two adjacent pitches one or two semitones apart.
- `multi_register_octave_cycle`: cycle one pitch class across three or more registers; currently too rare for promotion.

## Next gate

Build a controlled listening pack with Pulse 1, Pulse 2, Noise, tempo, form, harmony, and renderer held fixed. Vary only Triangle writing. Compare baseline root support against repeated drive, anchor-return, directional runs, and the rarer two-register octave pump. Use listening feedback to add applicability/avoidance rules before any promotion into the durable SKILL.
