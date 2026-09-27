"""
Fight 002: Blade & Shadow
A cinematic ninja vs samurai katana duel in a traditional dojo.
"""

from __future__ import annotations
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from stickfight import FightScene, create_ninja, create_samurai


def build_scene() -> FightScene:
    scene = FightScene(
        width=1080,
        height=1920,
        fps=30,
        ground_y=1500.0,
    )

    scene.background("dojo")
    scene.caption("DUEL OF THE BLADES", 0.0, 1.8)

    ninja = create_ninja(scene, name="Shadow", x=340, facing=1)
    samurai = create_samurai(scene, name="Kensei", x=740, facing=-1)

    # 0.0s: Approach
    scene.at(0.0, ninja.walk_to(480, duration=1.0))
    scene.at(0.0, samurai.walk_to(640, duration=1.0))

    # 1.4s: Ninja strikes with first slash
    scene.at(1.4, ninja.slash(samurai, duration=0.45))

    # 1.55s: Samurai parries with blade clash
    scene.at(1.55, samurai.block(duration=0.45))

    # 2.2s: Samurai retaliates with a fierce counter slash
    scene.at(2.2, samurai.slash(ninja, duration=0.48))

    # 2.35s: Ninja matrix-dodges underneath the blade
    scene.at(2.35, ninja.dodge(duration=0.50))

    # 3.2s: Ninja sweep trips Samurai
    scene.at(3.2, ninja.sweep(samurai, duration=0.45))

    # 4.0s: Ninja leaps up and delivers finishing aerial uppercut
    scene.at(4.0, ninja.uppercut(samurai, duration=0.55, damage=32.0))

    # 4.5s: Samurai collapses
    scene.at(4.5, samurai.fall(duration=1.4))

    scene.caption("K.O. - SHADOW WINS", 4.9, 7.0)

    return scene


if __name__ == "__main__":
    scene = build_scene()
    out = "output/videos/fight002.mp4"
    if "--preview" in sys.argv:
        scene.preview()
    else:
        scene.render(out)
