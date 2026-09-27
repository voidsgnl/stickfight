"""
Showcase Scene 004: Realistic MMA & Boxing Championship Bout.
Demonstrates realistic combat physics, boxing combinations, slips, checks, clinch knees,
takedowns, and ground & pound.
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["SDL_VIDEODRIVER"] = "dummy"

from stickfight import FightScene

def create_realistic_fight():
    # 9:16 Vertical Video for TikTok / Shorts / Reels
    scene = FightScene(
        width=1080,
        height=1920,
        fps=30,
        ground_y=1500.0,
        style="realistic",  # Configurable option: Realistic martial arts physics
    )
    scene.background("dojo")

    # Fighter A: Striker / Dutch Kickboxer
    f1 = scene.add_fighter(
        name="Alex 'Poatan'",
        x=340,
        y=1500.0,
        facing=1,
        color=(30, 41, 59),
        headband_color=(0, 210, 255),
        scale=1.02,
        line_width=11,
        design="warrior",
    )

    # Fighter B: Wrestler / Heavyweight Brawler
    f2 = scene.add_fighter(
        name="Francis 'Predator'",
        x=740,
        y=1500.0,
        facing=-1,
        color=(220, 38, 38),
        headband_color=(250, 204, 21),
        scale=1.08,
        line_width=12,
        design="brawler",
    )

    # Round Introduction
    scene.caption("ROUND 1 - MMA TITLE FIGHT", 0.0, 1.3)
    scene.at(0.0, f1.walk_to(450, duration=0.9))
    scene.at(0.0, f2.walk_to(630, duration=0.9))

    # Exchange 1: Low kick vs Shin Check
    scene.at(1.1, f2.low_kick(f1, duration=0.42, damage=16.0))
    scene.at(1.15, f1.check_kick(duration=0.45))
    scene.caption("SHIN CHECK!", 1.25, 1.8)

    # Exchange 2: Boxing combination with head movement
    scene.at(1.8, f1.jab(f2, duration=0.32, damage=12.0))
    scene.at(2.15, f2.slip(duration=0.38))
    scene.at(2.25, f2.cross(f1, duration=0.40, damage=18.0))
    scene.at(2.35, f1.bob_weave(duration=0.45))

    # Exchange 3: Counter hook & Stagger
    scene.at(2.85, f1.hook(f2, duration=0.40, damage=22.0))
    scene.at(3.1, f2.stagger(duration=0.55))

    # Exchange 4: Thai Clinch & Knee
    scene.at(3.7, f1.clinch_knee(f2, duration=0.52, damage=25.0))

    # Exchange 5: Double-Leg Takedown & Ground-and-Pound
    scene.caption("DOUBLE-LEG TAKEDOWN!", 4.3, 5.0)
    scene.at(4.3, f1.takedown(f2, duration=0.70, damage=22.0))
    scene.at(5.1, f1.ground_pound(f2, duration=0.50, damage=24.0))
    scene.at(5.7, f1.ground_pound(f2, duration=0.50, damage=28.0))

    # Finish & Stoppage
    scene.caption("T.K.O. - REFEREE STOPS THE CONTEST", 6.3, 8.0)

    return scene

if __name__ == "__main__":
    os.makedirs("output/videos", exist_ok=True)
    out_path = "output/videos/fight004_realistic_mma.mp4"
    print(f"🎬 Rendering Realistic MMA Championship video to {out_path}...")
    scene = create_realistic_fight()
    scene.render(output_path=out_path, duration=7.5)
    print("✅ Render complete!")
