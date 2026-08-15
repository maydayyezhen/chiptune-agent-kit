from __future__ import annotations

import argparse
import json
from pathlib import Path

from chiptune_agent_kit.experiments.pulse_recipe_integrated import export_integrated_song


def main() -> None:
    parser = argparse.ArgumentParser(description="Build one integrated NES-style pulse recipe listening piece.")
    parser.add_argument("--output", type=Path, default=Path("out/pulse_recipe_integrated_v1"))
    args = parser.parse_args()
    manifest = export_integrated_song(args.output)
    print(args.output)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
