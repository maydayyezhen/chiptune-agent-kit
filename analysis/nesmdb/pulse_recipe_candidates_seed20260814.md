# NES-MDB Pulse Recipe Candidate Snapshot

- corpus files found: `5278`
- sampled songs: `96`
- sampling: fixed random sample
- seed: `20260814`
- analysis view: `composition`
- micro-note hygiene floor: remove note states `<= 0.001 s`
- P1/P2 onset tolerance: `0.005 s`
- representative window: `6 s`
- window search step: `1 s`
- status: **exploratory hypotheses, not SKILL rules**

This snapshot records the first reproducible pass from corpus measurements to concrete pulse-arrangement recipe candidates. Raw sample-accurate MIDI remains the source for performance/timbre analysis; the recipe extraction below uses the cleaned composition view.

# Pulse Recipe Candidates

> Automatically extracted hypotheses from the cleaned composition view. Not final rules.

- `density_tradeoff_texture`: 5 unique evidence cases
- `parallel_interval_block_switch`: 1 unique evidence cases
- `parallel_interval_lock`: 5 unique evidence cases
- `phase_shifted_riff_interlock`: 4 unique evidence cases

## parallel_interval_lock

Give P2 the same onset grid as P1 and preserve one harmonic interval for a phrase-sized run; change the interval only at a deliberate boundary.

- `164_Hogan_sAlley_06_07GameOver.mid` `0.000–4.672s` status=`candidate` discovery=`locked`
  - sync=1.000, overlap=1.000, dominant=-12st (1.000), longest run=-12st × 12
- `379_WardnernoMori_05_06GameOver.mid` `0.000–1.800s` status=`candidate` discovery=`locked`
  - sync=1.000, overlap=0.928, dominant=+9st (1.000), longest run=+9st × 13
- `031_BioMiracleBokutteUpa_10_11Ending.mid` `14.000–20.000s` status=`candidate` discovery=`locked`
  - sync=1.000, overlap=1.000, dominant=+0st (0.857), longest run=+0st × 18
- `183_Karnov_06_07AllCleared.mid` `10.607–16.607s` status=`candidate` discovery=`locked`
  - sync=1.000, overlap=0.998, dominant=+0st (0.565), longest run=+0st × 13
- `383_Wily_amp_RightnoRockBoard_That_sParadise_00_01Title.mid` `13.000–19.000s` status=`candidate` discovery=`locked`
  - sync=1.000, overlap=0.997, dominant=-4st (0.667), longest run=-4st × 12

## parallel_interval_block_switch

Keep the pulse pair rhythmically locked, but switch the fixed interval between phrase blocks instead of transposing P2 by one interval forever.

- `383_Wily_amp_RightnoRockBoard_That_sParadise_00_01Title.mid` `13.000–19.000s` status=`candidate` discovery=`locked`
  - long runs: -5st×6, -4st×12

## phase_shifted_riff_interlock

Reuse or closely imitate the same riff in both pulse voices, but offset one voice by a stable rhythmic phase so their onsets interleave.

- `392_Yo_Noid_13_14HauntedHouseHauntedCastle.mid` `1.000–7.000s` status=`candidate` discovery=`interlocking`
  - sync=0.000, overlap=1.000, pitch match=1.000 over 18 pairs, event lag=+0, median P1-P2 offset=+0.133016s, spread=0.000023s
- `217_MajouDensetsuII_DaimashikyouGalious_07_08GreatDemon.mid` `4.000–10.000s` status=`candidate` discovery=`interlocking`
  - sync=0.000, overlap=1.000, pitch match=1.000 over 17 pairs, event lag=-1, median P1-P2 offset=+0.249433s, spread=0.000023s
- `335_TecmoCupSoccerGame_08_09Memo.mid` `1.000–7.000s` status=`candidate` discovery=`interlocking`
  - sync=0.000, overlap=0.955, pitch match=1.000 over 16 pairs, event lag=+2, median P1-P2 offset=-0.266338s, spread=0.000839s
- `366_Ufouria_TheSaga_02_03DecisiveBattleBoss.mid` `1.000–7.000s` status=`candidate` discovery=`interlocking`
  - sync=0.100, overlap=0.978, pitch match=1.000 over 17 pairs, event lag=+2, median P1-P2 offset=-0.166236s, spread=0.000272s

## density_tradeoff_texture

Candidate behavior: raise one pulse voice's onset density while the other relaxes. Validate at several window sizes before using as a durable rule.

- `283_Robocop_04_05BossBGM.mid` `5.000–11.000s` status=`needs_multiscale_validation` discovery=`density_compensation, interlocking`
  - local density correlation=-0.667, sync=0.167, overlap=1.000
- `336_TenchioKurauII_ShokatsuKoumeiDen_15_16Ship.mid` `32.000–38.000s` status=`needs_multiscale_validation` discovery=`density_compensation`
  - local density correlation=-0.554, sync=0.000, overlap=0.715
- `114_Faxanadu_04_05Church.mid` `9.000–15.000s` status=`needs_multiscale_validation` discovery=`density_compensation`
  - local density correlation=-0.460, sync=0.000, overlap=1.000
- `261_Parodius_06_07EventhePatienceofaPierrotHasLimits.mid` `41.000–47.000s` status=`needs_multiscale_validation` discovery=`density_compensation`
  - local density correlation=-0.460, sync=0.188, overlap=0.992
- `168_Hydlide3_YamiKaranoHoumonsha_00_01TheSpaceMemoriesMainTheme.mid` `77.000–83.000s` status=`needs_multiscale_validation` discovery=`density_compensation`
  - local density correlation=-0.972, sync=0.333, overlap=0.644

## Promotion gate

Do not promote a candidate to `references/` or `SKILL.md` from this snapshot alone. A candidate should first survive broader-corpus prevalence measurement, detector sensitivity checks, and listening/composition A/B tests. `density_tradeoff_texture` additionally requires multi-scale window validation before recipe-level use.
