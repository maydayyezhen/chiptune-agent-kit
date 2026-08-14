# NES-MDB Pulse Casebook Snapshot

- corpus files found: 5278
- sampled songs: 96
- sampling: fixed random sample
- seed: `20260814`
- P1/P2 onset tolerance for primary casebook metrics: `0.005 s`
- status: exploratory measurement, **not** a composition rule set

This file records one reproducible experiment snapshot. The discovery buckets below are transparent heuristics used to locate contrasting examples for later note-level inspection and listening.

# Pulse Relationship Casebook

> Discovery cases only. These buckets are not ground-truth musical genres or labels.

## locked

High overlap + high synchronized-onset ratio; candidate tightly coupled pulse writing.

| file | sync | overlap | density corr | thirds | sixths | unison/oct | parallel |
|---|---:|---:|---:|---:|---:|---:|---:|
| `164_Hogan_sAlley_06_07GameOver.mid` | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 1.000 | 1.000 |
| `379_WardnernoMori_05_06GameOver.mid` | 1.000 | 0.928 | 1.000 | 0.000 | 1.000 | 0.000 | 1.000 |
| `183_Karnov_06_07AllCleared.mid` | 0.978 | 0.989 | 0.985 | 0.360 | 0.022 | 0.596 | 0.625 |
| `031_BioMiracleBokutteUpa_10_11Ending.mid` | 0.987 | 0.997 | 0.353 | 0.251 | 0.004 | 0.641 | 0.557 |
| `383_Wily_amp_RightnoRockBoard_That_sParadise_00_01Title.mid` | 1.000 | 0.996 | 1.000 | 0.333 | 0.095 | 0.476 | 0.482 |

## interlocking

High overlap + low synchronized-onset ratio; candidate independent/interlocking pulse writing.

| file | sync | overlap | density corr | thirds | sixths | unison/oct | parallel |
|---|---:|---:|---:|---:|---:|---:|---:|
| `392_Yo_Noid_13_14HauntedHouseHauntedCastle.mid` | 0.000 | 0.992 | 0.773 | 0.000 | 0.000 | 0.000 | 0.000 |
| `217_MajouDensetsuII_DaimashikyouGalious_07_08GreatDemon.mid` | 0.065 | 0.984 | 0.984 | 0.000 | 0.125 | 0.125 | 0.000 |
| `335_TecmoCupSoccerGame_08_09Memo.mid` | 0.000 | 0.919 | 0.557 | 0.000 | 0.000 | 0.000 | 0.000 |
| `283_Robocop_04_05BossBGM.mid` | 0.167 | 1.000 | -0.700 | 0.667 | 0.000 | 0.000 | 0.000 |
| `366_Ufouria_TheSaga_02_03DecisiveBattleBoss.mid` | 0.185 | 0.977 | 0.921 | 0.273 | 0.000 | 0.000 | 0.143 |

## density_compensation

Negative onset-density correlation; candidate one-busy-while-the-other-relaxes behavior.

| file | sync | overlap | density corr | thirds | sixths | unison/oct | parallel |
|---|---:|---:|---:|---:|---:|---:|---:|
| `283_Robocop_04_05BossBGM.mid` | 0.167 | 1.000 | -0.700 | 0.667 | 0.000 | 0.000 | 0.000 |
| `336_TenchioKurauII_ShokatsuKoumeiDen_15_16Ship.mid` | 0.000 | 0.710 | -0.503 | 0.000 | 0.000 | 0.000 | 0.000 |
| `116_FelixtheCat_08_09Northpole.mid` | 0.971 | 1.000 | -0.327 | 0.149 | 0.149 | 0.239 | 0.030 |
| `119_FinalFantasyIII_13_14ShrineofNept.mid` | 0.368 | 0.690 | -0.428 | 0.062 | 0.125 | 0.125 | 0.000 |
| `114_Faxanadu_04_05Church.mid` | 0.421 | 0.978 | -0.290 | 0.250 | 0.250 | 0.000 | 0.143 |

## middle

Near corpus medians; useful control cases rather than an intended style label.

| file | sync | overlap | density corr | thirds | sixths | unison/oct | parallel |
|---|---:|---:|---:|---:|---:|---:|---:|
| `378_WaiWaiWorld2_SOS__ParsleyJou_22_23SweetsDance3.mid` | 0.750 | 0.960 | 0.686 | 0.556 | 0.000 | 0.000 | 0.059 |
| `287_S_C_A_T__SpecialCyberneticAttackTeam_04_05StageClear.mid` | 0.756 | 1.000 | 0.742 | 0.176 | 0.118 | 0.029 | 0.394 |
| `226_MegaMan3_20_21DrWilyStageBoss.mid` | 0.801 | 1.000 | 0.638 | 0.264 | 0.120 | 0.056 | 0.008 |
| `342_TheFlintstones_TheSurpriseatDinosaurPeak__10_11Castle.mid` | 0.797 | 0.848 | 0.565 | 0.737 | 0.136 | 0.000 | 0.282 |
| `195_KonamiWaiWaiWorld_17_18FinalStageBGM.mid` | 0.777 | 0.996 | 0.874 | 0.283 | 0.126 | 0.309 | 0.272 |

## Next validation step

For each bucket, inspect representative MIDI note sequences and local windows rather than promoting the bucket name directly to a composition rule. In particular, compare exact P1/P2 rhythm grids, signed harmonic intervals, motion sequences, rests, and section-level changes.
