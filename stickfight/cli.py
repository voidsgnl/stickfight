"""
CLI entry point for Stick Fight Video Engine.
Run fights in preview mode or render full HD vertical video MP4s.
"""

from __future__ import annotations
import argparse
import importlib.util
import os
import sys
from typing import List, Optional

from stickfight.engine.renderer import FFmpegNotFoundError
from stickfight.engine.scene import ChoreographyError, FightScene


def load_scene_from_file(file_path: str) -> FightScene:
    abs_path = os.path.abspath(file_path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"Scene file not found: {abs_path}")

    spec = importlib.util.spec_from_file_location("dynamic_scene", abs_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load scene module from {abs_path}")

    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    if hasattr(mod, "build_scene"):
        return mod.build_scene()
    elif hasattr(mod, "scene"):
        return mod.scene
    else:
        raise AttributeError(f"Scene module {abs_path} must define 'build_scene()' or 'scene'")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Stick Fight Video Engine")
    parser.add_argument(
        "scene",
        nargs="?",
        default="scenes/fight001.py",
        help="Path to Python scene file (default: scenes/fight001.py)",
    )
    parser.add_argument("--render", action="store_true", help="Render fight to MP4 video using FFmpeg (default)")
    parser.add_argument("--preview", action="store_true", help="Open interactive real-time Pygame preview window")
    parser.add_argument(
        "--output", "-o", default="output/videos/fight001.mp4",
        help="Output video path (default: output/videos/fight001.mp4)",
    )
    parser.add_argument("--duration", type=float, default=None, help="Optional override for total scene duration in seconds")
    parser.add_argument(
        "--strict", action="store_true",
        help="Fail on impossible choreography (attacks that can't reach, overlapping actions, acting while down)",
    )

    args = parser.parse_args(argv)

    print(f"🥊 Loading fight scene: {args.scene}")
    try:
        scene = load_scene_from_file(args.scene)
        scene.strict = args.strict or scene.strict
        if args.preview:
            scene.preview()
            return 0
        return 0 if scene.render(output_path=args.output, duration=args.duration) else 1
    except ChoreographyError as exc:
        print(f"❌ Choreography error (--strict): {exc}", file=sys.stderr)
        return 2
    except (FFmpegNotFoundError, FileNotFoundError) as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
