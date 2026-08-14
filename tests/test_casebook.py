from chiptune_agent_kit.analysis.casebook import select_pulse_cases


def _song(name: str, *, sync: float, overlap: float, corr: float, consonance: float = 0.0):
    third = consonance / 3.0
    sixth = consonance / 3.0
    unison = consonance / 3.0
    return {
        "source": name,
        "relationships": {
            "pulse_1_pulse_2": {
                "note_counts": {"pulse_1": 32, "pulse_2": 32},
                "time_relationship": {
                    "overlap_ratio_of_active_union": overlap,
                    "overlap_ratio_of_song": overlap,
                },
                "onset_relationship": {
                    "synchronized_pairs": 16,
                    "synchronized_onset_ratio": sync,
                    "third_like_ratio": third,
                    "sixth_like_ratio": sixth,
                    "unison_octave_like_ratio": unison,
                },
                "motion_relationship": {
                    "similar_direction_ratio": 0.5,
                    "contrary_ratio": 0.25,
                    "interval_preserving_parallel_ratio": 0.25,
                },
                "activity_relationship": {
                    "exclusive_activity_ratio": 0.0,
                    "adjacent_exclusive_switch_rate": 0.0,
                },
                "density_relationship": {
                    "pearson_onset_density_correlation": corr,
                    "density_compensation_score": max(0.0, -corr),
                },
            }
        },
    }


def test_casebook_finds_interpretable_extremes():
    report = {
        "songs": [
            _song("locked.mid", sync=0.98, overlap=0.99, corr=0.9, consonance=0.7),
            _song("interlocking.mid", sync=0.05, overlap=0.98, corr=0.5),
            _song("comp.mid", sync=0.4, overlap=0.8, corr=-0.7),
            _song("middle.mid", sync=0.5, overlap=0.7, corr=0.1),
        ]
    }

    casebook = select_pulse_cases(report, count_per_group=1)

    assert casebook["groups"]["locked"][0]["name"] == "locked.mid"
    assert casebook["groups"]["interlocking"][0]["name"] == "interlocking.mid"
    assert casebook["groups"]["density_compensation"][0]["name"] == "comp.mid"
    assert casebook["population"]["songs_with_both_pulses"] == 4
