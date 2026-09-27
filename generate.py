"""
Batch fight video generator for automated short-form video content creation.
Generates complete stick fight videos using procedural choreography.
"""

from __future__ import annotations
import os
import sys
import argparse
import random

from stickfight import generate_fight

ARCHETYPES = ["ninja", "samurai", "brawler", "monk", "cyborg"]
ENVIRONMENTS = ["dojo", "city", "cyberpunk", "plain"]


def main():
    parser = argparse.ArgumentParser(description="Batch Stick Fight Video Generator")
    parser.add_argument("--count", "-c", type=int, default=1, help="Number of videos to generate (default: 1)")
    parser.add_argument("--duration", "-d", type=float, default=10.0, help="Duration of each fight in seconds (default: 10.0)")
    parser.add_argument("--env", "--environment", default="random", choices=ENVIRONMENTS + ["random"], help="Environment background")
    parser.add_argument("--fighter-a", default="random", help="Fighter A archetype (ninja, samurai, brawler, monk, cyborg, random)")
    parser.add_argument("--fighter-b", default="random", help="Fighter B archetype (ninja, samurai, brawler, monk, cyborg, random)")
    parser.add_argument("--output-dir", "-o", default="output/videos", help="Output directory (default: output/videos)")
    parser.add_argument("--seed", type=int, default=None, help="Base random seed for reproducibility")

    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    print(f"🎬 Generating {args.count} stick fight video(s)...")

    for i in range(1, args.count + 1):
        file_name = f"fight{i:03d}.mp4"
        out_path = os.path.join(args.output_dir, file_name)

        item_seed = (args.seed + i) if args.seed is not None else random.randint(1, 1_000_000)
        rng = random.Random(item_seed)

        env = args.env if args.env != "random" else rng.choice(ENVIRONMENTS)
        f_a = args.fighter_a if args.fighter_a != "random" else rng.choice(ARCHETYPES)
        f_b = args.fighter_b if args.fighter_b != "random" else rng.choice([a for a in ARCHETYPES if a != f_a] or ARCHETYPES)

        print(f"\n[{i}/{args.count}] Generating {file_name}: {f_a.upper()} vs {f_b.upper()} in {env.upper()} ({args.duration}s)...")

        scene = generate_fight(
            duration=args.duration,
            fighter_a_type=f_a,
            fighter_b_type=f_b,
            environment=env,
            seed=item_seed,
        )

        scene.render(output_path=out_path)

    print(f"\n🎉 All {args.count} video(s) generated in {args.output_dir}/")


if __name__ == "__main__":
    main()
