"""
Fight 001: The First Duel
Choreography based on README specification.
"""

from __future__ import annotations
import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from stickfight import FightScene


def build_scene() -> FightScene:
    scene = FightScene(
        width=1080,
        height=1920,
        fps=30,
        ground_y=1500.0,
    )

    scene.background("plain")
    scene.caption("ROUND 1", 0.0, 1.8)

    # Add fighters: A (Red) and B (Blue)
    A = scene.add_fighter("A", x=350, y=1500, color=(240, 70, 70))
    B = scene.add_fighter("B", x=730, y=1500, color=(70, 170, 255))

    # Choreography sequence
    # 0.0s - 1.0s: A approaches
    scene.at(0.0, A.walk_to(500))

    # 1.0s - 2.0s: B steps forward into engagement distance
    scene.at(1.0, B.walk_to(600))

    # 2.0s: A strikes with a quick jab
    scene.at(2.0, A.punch(B))

    # 2.6s: B raises guard and blocks
    scene.at(2.6, B.block(duration=0.5))

    # 3.4s: B retaliates with a high kick
    scene.at(3.4, B.kick(A))

    # 4.0s: A dodges underneath the kick
    scene.at(4.0, A.dodge(duration=0.5))

    # 4.9s: A counters with a heavy decisive strike
    scene.at(4.9, A.punch(B, damage=30.0))

    # 5.4s: B stumbles into knockback
    scene.at(5.4, B.knockback(distance=150.0, duration=0.7))

    # 6.2s: B collapses to the ground
    scene.at(6.2, B.fall(duration=1.4))

    scene.caption("K.O.", 6.6, 8.5)

    return scene


if __name__ == "__main__":
    scene = build_scene()

    output_file = "output/videos/fight001.mp4"
    if "--preview" in sys.argv:
        scene.preview()
    elif "--render" in sys.argv:
        scene.render(output_file)
    else:
        # Default action: render video
        scene.render(output_file)
