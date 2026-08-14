# NES-MDB Full-Corpus Pulse Recipe Scan, Refined

- workflow run: `31805467871`
- workflow head: `b92ee8c0469e5205b9f76ff37a63702be17c7813`
- artifact id: `9221028455`
- scan date: `2026-08-14`

> Full-corpus measurements from the cleaned composition view. Detector hits are evidence, not universal composition laws.

- files found: `5278`
- songs scanned: `5278`
- songs with both clean pulse voices: `4828`
- windows scanned: `50512`
- micro-note floor: `<= 0.001 s` removed from composition view
- base window / step: `6.0 s / 3.0 s`
- synchronized-onset tolerance: `0.005 s`
- density validation scales: `[4.0, 8.0, 16.0]`
- phase stability gate: spread / median voice IOI `<= 0.1`
- phase simple-fraction label tolerance: `<= 0.03 IOI`

## Prevalence

| recipe | songs | prevalence among two-pulse songs | episodes | median episode |
|---|---:|---:|---:|---:|
| `parallel_interval_lock` | 1496 | 30.986% | 1952 | 9.00s |
| `parallel_interval_block_switch` | 623 | 12.904% | 821 | 6.00s |
| `phase_shifted_riff_interlock` | 217 | 4.495% | 269 | 9.00s |
| `density_tradeoff_texture` | 676 | 14.002% | 934 | 6.00s |

## Parallel interval lock

Harmonic-family prevalence. A song may contribute to more than one family:

- `fourth_fifth_family`: 605 songs
- `unison_octave`: 601 songs
- `third_family`: 389 songs
- `sixth_family`: 154 songs
- `tritone`: 46 songs
- `second_family`: 43 songs
- `seventh_family`: 11 songs

Most common exact signed intervals:

- `+0 st`: 279 songs
- `-5 st`: 254 songs
- `+5 st`: 242 songs
- `-12 st`: 191 songs
- `-3 st`: 134 songs
- `+12 st`: 124 songs
- `+3 st`: 110 songs
- `-4 st`: 94 songs
- `-7 st`: 74 songs
- `+4 st`: 67 songs
- `+7 st`: 55 songs
- `-9 st`: 48 songs
- `-8 st`: 43 songs
- `+9 st`: 37 songs
- `+24 st`: 37 songs
- `+8 st`: 31 songs

## Interval block switches

Same-to-same long-run pairs are excluded from this transition table.

- `+4->+3 st`: 135 window transitions
- `-4->-3 st`: 117 window transitions
- `+3->+4 st`: 113 window transitions
- `-3->-4 st`: 106 window transitions
- `+5->+4 st`: 88 window transitions
- `+3->+5 st`: 86 window transitions
- `+5->+3 st`: 83 window transitions
- `+4->+5 st`: 64 window transitions
- `-3->-5 st`: 45 window transitions
- `+0->-1 st`: 44 window transitions
- `+5->+0 st`: 42 window transitions
- `-1->+0 st`: 41 window transitions
- `-5->-4 st`: 37 window transitions
- `+0->+5 st`: 35 window transitions
- `-5->-3 st`: 35 window transitions
- `-5->-7 st`: 33 window transitions

## Phase-shifted riff interlock

Whole-IOI event displacement is removed before classifying the remaining phase residue. Only stable windows pass the spread/IOI gate.

- `1/2` residue: 350 window hits
- `1/4` residue: 134 window hits
- `1/6` residue: 104 window hits
- `1/3` residue: 94 window hits
- `other` residue: 82 window hits
- `1/8` residue: 60 window hits
- `3/8` residue: 59 window hits
- `2/5` residue: 40 window hits
- `0` residue: 11 window hits

Median absolute residual phase: `0.35771645495692417` IOI

Median spread / IOI: `0.0009539384028804452`

Rejected unstable phase windows during refinement: `121`

## Density tradeoff

Counted only after multi-scale validation: at least two usable scales <= -0.30 correlation and at least one <= -0.45.

Median base density correlation: `-0.6324555320336759`

Median multi-scale correlation: `-0.5483680842805889`

## Recipe co-occurrence

- `parallel_interval_block_switch + parallel_interval_lock`: 536 songs
- `density_tradeoff_texture + parallel_interval_lock`: 184 songs
- `density_tradeoff_texture + parallel_interval_block_switch`: 79 songs
- `density_tradeoff_texture + phase_shifted_riff_interlock`: 42 songs
- `parallel_interval_lock + phase_shifted_riff_interlock`: 20 songs
- `parallel_interval_block_switch + phase_shifted_riff_interlock`: 10 songs

## Representative songs

### parallel_interval_lock

- `329_SwordMaster_04_05MapScreen.mid`: 1 episode(s), total `591.00s`, max `591.00s`
- `298_SolarJetman_HuntfortheGoldenWarpship_09_10MexomorfGameplay.mid`: 1 episode(s), total `252.98s`, max `252.98s`
- `215_Magician_11_12MazeofDoom.mid`: 1 episode(s), total `185.24s`, max `185.24s`
- `314_SummerCarnival_92_Recca_02_03JetterStage1FirstHalfArea5.mid`: 4 episode(s), total `175.97s`, max `58.97s`
- `298_SolarJetman_HuntfortheGoldenWarpship_26_27ShammyGenGameplay.mid`: 1 episode(s), total `164.33s`, max `164.33s`
- `314_SummerCarnival_92_Recca_12_13HienerScoreAttackFirstHalf.mid`: 4 episode(s), total `157.79s`, max `60.00s`
- `141_Ghostbusters_01_02MainBGM.mid`: 4 episode(s), total `153.00s`, max `69.00s`
- `043_Castelian_03_04BonusRoad.mid`: 1 episode(s), total `141.23s`, max `141.23s`

### parallel_interval_block_switch

- `298_SolarJetman_HuntfortheGoldenWarpship_09_10MexomorfGameplay.mid`: 6 episode(s), total `237.00s`, max `186.00s`
- `298_SolarJetman_HuntfortheGoldenWarpship_26_27ShammyGenGameplay.mid`: 6 episode(s), total `84.00s`, max `18.00s`
- `314_SummerCarnival_92_Recca_04_05MOMStage1SecondHalfArea3.mid`: 2 episode(s), total `69.00s`, max `36.00s`
- `033_Blackjack_00_01TitleScreen.mid`: 5 episode(s), total `66.00s`, max `15.00s`
- `193_Klax_04_05CavernsofCthulu.mid`: 8 episode(s), total `66.00s`, max `12.00s`
- `053_ChoujinSentaiJetman_13_14FinalBoss.mid`: 3 episode(s), total `64.54s`, max `30.00s`
- `292_Shatterhand_08_09AreaCAreaFJP.mid`: 1 episode(s), total `64.11s`, max `64.11s`
- `292_Shatterhand_07_08AreaC.mid`: 1 episode(s), total `57.00s`, max `57.00s`

### phase_shifted_riff_interlock

- `179_JourneytoSilius_03_04Stage2.mid`: 4 episode(s), total `162.04s`, max `45.00s`
- `257_OverHorizon_08_09Stage61.mid`: 1 episode(s), total `79.03s`, max `79.03s`
- `071_DigitalDevilStory_MegamiTensei_16_17AnfiniAnfiniPalace.mid`: 1 episode(s), total `77.40s`, max `77.40s`
- `250_NinjaGaiden_04_05BraveryOntheClutches.mid`: 4 episode(s), total `69.00s`, max `21.00s`
- `298_SolarJetman_HuntfortheGoldenWarpship_28_29ShankooGameplay.mid`: 6 episode(s), total `63.00s`, max `18.00s`
- `257_OverHorizon_06_07Stage4.mid`: 1 episode(s), total `51.17s`, max `51.17s`
- `154_HappilyEverAfter_06_07Stage22Stage32.mid`: 1 episode(s), total `45.13s`, max `45.13s`
- `130_Fridaythe13th_01_02PlayerSelectInsideaCabin.mid`: 1 episode(s), total `45.13s`, max `45.13s`

### density_tradeoff_texture

- `215_Magician_15_16EpiloguePart1.mid`: 29 episode(s), total `421.29s`, max `48.00s`
- `091_DragonWarriorIV_43_44FinaleGuidingPeople.mid`: 11 episode(s), total `99.00s`, max `24.00s`
- `151_Gumshoe_02_03DiamondAppears.mid`: 2 episode(s), total `81.00s`, max `42.00s`
- `071_DigitalDevilStory_MegamiTensei_16_17AnfiniAnfiniPalace.mid`: 1 episode(s), total `74.40s`, max `74.40s`
- `255_NobunaganoYabou_BushouFuunroku_24_25AsEternalasHeavenandEarthEnding.mid`: 4 episode(s), total `66.00s`, max `33.00s`
- `212_MTV_RemoteControl_00_01TitleScreen.mid`: 3 episode(s), total `63.00s`, max `51.00s`
- `008_AfterBurnerII_02_03RedOut.mid`: 3 episode(s), total `54.00s`, max `39.00s`
- `393_Yoshi_08_092PBattleMode.mid`: 4 episode(s), total `54.00s`, max `21.00s`

## Interpretation guardrail

Prevalence means at least one qualifying detector window occurs in a song. It does not mean the recipe dominates the whole piece. Exact signed intervals far outside a normal harmonic register can reflect wide register separation, so harmonic-family summaries should be preferred for recipe design. Promotion to SKILL still requires sensitivity checks and listening/composition A/B tests.
