"""
Fight 003: Aerial Acrobatics & Grappling Slams
High-flying dive kicks, mid-air juggles, wall bounces, and seismic grappling slams.
"""

from __future__ import annotations
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from stickfight import FightScene, create_ninja, create_brawler


def build_scene() -> FightScene:
    scene = FightScene(
        width=1080,
        height=1920,
        fps=30,
        ground_y=1500.0,
    )

    scene.background("dojo")
    scene.caption("AERIAL ACROBATICS", 0.0, 1.8)

    ninja = create_ninja(scene, name="Hayabusa", x=340, facing=1)
    brawler = create_brawler(scene, name="Goliath", x=740, facing=-1)

    # 0.0s: Approach
    scene.at(0.0, ninja.run_to(440, duration=0.8))
    scene.at(0.0, brawler.walk_to(640, duration=0.9))

    # 1.1s: Ninja leaps high into the air and delivers a bullet dive kick
    scene.at(1.1, ninja.dive_kick(brawler, duration=0.65, damage=22.0))

    # 1.8s: Goliath grabs the landing ninja and performs a devastating seismic throw
    scene.at(1.8, brawler.throw(ninja, duration=0.75, damage=28.0))

    # 2.8s: Ninja rebounds off the wall boundary
    scene.at(2.8, ninja.wall_bounce(wall_x=120.0, duration=0.65))

    # 3.6s: Ninja springs forward and executes an aerial uppercut launcher
    scene.at(3.6, ninja.uppercut(brawler, duration=0.50, damage=20.0))

    # 4.1s: Ninja follows up with an air juggle spinning strike in mid-air
    scene.at(4.1, ninja.air_juggle(brawler, duration=0.55, damage=22.0))

    # 4.8s: Ninja finishes with an overhead grappling slam
    scene.at(4.8, ninja.throw(brawler, duration=0.80, damage=35.0))

    # 5.8s: Final Victory Caption
    scene.caption("K.O. - HAYABUSA WINS", 5.8, 8.0)

    return scene


if __name__ == "__main__":
    scene = build_scene()
    os.makedirs("output/videos", exist_ok=True)
    out_path = "output/videos/fight003_acrobatics.mp4"
    if "--preview" in sys.argv:
        scene.preview()
    else:
        print(f"Rendering {out_path}...")
        scene.render(out_path)
        print(f"Render complete: {out_path}")

