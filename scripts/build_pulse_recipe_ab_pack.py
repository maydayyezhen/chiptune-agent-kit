from __future__ import annotations

import argparse
from pathlib import Path

from chiptune_agent_kit.experiments.pulse_recipe_ab import export_ab_pack


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the controlled NES pulse-recipe A/B listening pack.")
    parser.add_argument("--output", type=Path, default=Path("out/pulse_recipe_ab_v1"))
    args = parser.parse_args()
    manifest = export_ab_pack(args.output)
    print(args.output)
    for name, item in manifest["variants"].items():
        print(f"{name}: P2 notes={item['p2_note_count']} -> {item['wav']}")


if __name__ == "__main__":
    main()
