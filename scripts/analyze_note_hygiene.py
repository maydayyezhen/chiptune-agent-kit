from __future__ import annotations

import argparse
import json
from pathlib import Path

from chiptune_agent_kit.analysis.note_hygiene import (
    SAMPLE_RATE,
    analyze_note_hygiene_sensitivity,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Measure how sample-level note filtering changes NES composition statistics."
    )
    parser.add_argument("report", type=Path, help="NES-MDB sample report JSON")
    parser.add_argument("--root", type=Path, required=True, help="Root containing NES-MDB MIDI files")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8"))
    thresholds = [0.0, 1.0 / SAMPLE_RATE, 0.001, 0.002, 0.005, 0.010]
    result = analyze_note_hygiene_sensitivity(
        report,
        root=args.root,
        thresholds_seconds=thresholds,
        onset_tolerance_seconds=0.005,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(f"sample_songs={result['sample_songs']}")
    print(f"one_sample_seconds={result['one_sample_seconds']:.9f}")
    for key, row in result["thresholds"].items():
        rel = row["pulse_1_pulse_2"]
        p1 = row["voices"]["pulse_1"]
        p2 = row["voices"]["pulse_2"]
        print(
            f"threshold={key} "
            f"removed_p1={p1['removed_ratio']:.4f} "
            f"removed_p2={p2['removed_ratio']:.4f} "
            f"sync={rel['mean_synchronized_onset_ratio']:.4f} "
            f"overlap={rel['mean_overlap_ratio_of_active_union']:.4f} "
            f"density_corr={rel['mean_onset_density_correlation']}"
        )


if __name__ == "__main__":
    main()
