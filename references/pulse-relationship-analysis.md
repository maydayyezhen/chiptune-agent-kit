# Pulse 1 / Pulse 2 relationship analysis

This first relationship-analysis pass measures observable behavior before assigning musical intent.

## Metrics

- `overlap_ratio_of_active_union`: how often both pulse voices sound at the same time relative to the union of their active time.
- `synchronized_onset_ratio`: one-to-one near-simultaneous onsets, with a default 30 ms tolerance.
- `third_like_ratio` / `sixth_like_ratio`: pitch-class interval families at synchronized onsets. These do not prove harmonic function.
- motion ratios: similar direction, contrary motion, oblique motion, and interval-preserving parallel motion across consecutive synchronized onset pairs.
- `exclusive_activity_ratio`: fraction of active 250 ms windows in which only one pulse voice is sounding.
- `adjacent_exclusive_switch_rate`: how often adjacent exclusive windows switch between P1-only and P2-only.
- onset-density correlation: Pearson correlation of note-on counts in 1 s windows.
- `density_compensation_score`: `max(0, -correlation)`, retained as a descriptive candidate signal only.

## Interpretation policy

Do not rename `exclusive_activity_ratio` to `call_response_score`.

Do not interpret negative density correlation as intentional accompaniment compensation without inspecting individual tracks.

Do not promote corpus means directly into `SKILL.md`.

Use this loop:

```text
corpus signal
→ inspect examples and counterexamples
→ listen
→ formulate a candidate musical rule
→ compose an A/B test
→ promote only if the rule survives
```

The fixed windows and 30 ms onset tolerance are analysis parameters, not hardware facts. They should be varied in sensitivity tests before broad claims are made.
