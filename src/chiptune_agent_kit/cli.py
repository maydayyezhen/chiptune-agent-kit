from __future__ import annotations

import argparse
import json
from pathlib import Path

from chiptune_agent_kit.analysis import analyze_nes_midi
from chiptune_agent_kit.ir import ChipProject
from chiptune_agent_kit.validation import validate_nes2a03


def analyze_main() -> None:
    parser = argparse.ArgumentParser(description="Analyze separated NES-style MIDI reference material.")
    parser.add_argument("midi", type=Path)
    parser.add_argument("--output", "-o", type=Path)
    args = parser.parse_args()

    result = analyze_nes_midi(args.midi)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


def validate_main() -> None:
    parser = argparse.ArgumentParser(description="Validate a NES 2A03 chip-performance project.")
    parser.add_argument("project", type=Path)
    args = parser.parse_args()

    data = json.loads(args.project.read_text(encoding="utf-8"))
    project = ChipProject.from_dict(data)
    result = validate_nes2a03(project)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(1 if result["errors"] else 0)
