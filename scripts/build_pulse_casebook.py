from __future__ import annotations

import argparse
import json
from pathlib import Path

from chiptune_agent_kit.analysis.casebook import render_casebook_markdown, select_pulse_cases


def main() -> None:
    parser = argparse.ArgumentParser(description="Build interpretable P1/P2 discovery casebook from an analysis report.")
    parser.add_argument("report", type=Path, help="NES-MDB batch analysis JSON")
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    parser.add_argument("--count", type=int, default=5, help="Cases per discovery bucket")
    args = parser.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8"))
    casebook = select_pulse_cases(report, count_per_group=args.count)

    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(casebook, indent=2), encoding="utf-8")
    args.markdown_output.write_text(render_casebook_markdown(casebook), encoding="utf-8")

    print(f"songs with both pulses: {casebook['population']['songs_with_both_pulses']}")
    for name, items in casebook["groups"].items():
        print(f"{name}: {len(items)}")
        for item in items:
            corr = item['density_correlation']
            corr_text = 'n/a' if corr is None else f"{corr:.3f}"
            print(f"  {item['name']} sync={item['sync']:.3f} overlap={item['overlap']:.3f} corr={corr_text}")


if __name__ == "__main__":
    main()
