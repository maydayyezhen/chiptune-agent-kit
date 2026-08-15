from __future__ import annotations

import argparse
import json
from pathlib import Path

from chiptune_agent_kit.experiments.triangle_recipe_ab import export_triangle_ab_pack


def main() -> None:
    parser = argparse.ArgumentParser(description="Build controlled Triangle recipe A/B MIDI/WAV pack.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = export_triangle_ab_pack(args.output)
    print(args.output)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
