"""
Procedural fight generator: creates dynamic, logically consistent stick fights
with realistic combat exchanges, reactions, combos, and cinematic climaxes.
"""

from __future__ import annotations
import random
from typing import Optional, Tuple, List

from stickfight.engine.scene import FightScene
from stickfight.engine.characters import (
    create_ninja,
    create_samurai,
    create_brawler,
    create_monk,
    create_cyborg,
)


ARCHETYPE_BUILDERS = {
    "ninja": create_ninja,
    "samurai": create_samurai,
    "brawler": create_brawler,
    "monk": create_monk,
    "cyborg": create_cyborg,
}


def generate_fight(
    duration: float = 12.0,
    fighter_a_type: str = "ninja",
    fighter_b_type: str = "samurai",
    environment: str = "dojo",
    seed: Optional[int] = None,
) -> FightScene:
    """Procedurally generates a complete scripted fight scene."""
    rng = random.Random(seed)

    scene = FightScene(width=1080, height=1920, fps=30, ground_y=1500.0)
    scene.background(environment)

    # 1. Spawn fighters
    builder_a = ARCHETYPE_BUILDERS.get(fighter_a_type.lower(), create_ninja)
    builder_b = ARCHETYPE_BUILDERS.get(fighter_b_type.lower(), create_samurai)

    A = builder_a(scene, name="FIGHTER A", x=340, facing=1)
    B = builder_b(scene, name="FIGHTER B", x=740, facing=-1)

    scene.caption("ROUND 1", 0.0, 1.6)

    # 2. Approach Phase
    t = 0.0
    scene.at(t, A.walk_to(480, duration=1.0))
    scene.at(t + 0.3, B.walk_to(640, duration=1.0))
    t += 1.5

    scene.caption("FIGHT!", t, t + 1.0)
    t += 0.4

    # 3. Combat Exchanges Loop
    current_attacker = A if rng.random() < 0.5 else B
    target_end_time = max(6.0, duration - 2.5)

    while t < target_end_time:
        defender = B if current_attacker == A else A

        # Choose attack style
        attack_roll = rng.random()

        if current_attacker.weapon == "staff" and attack_roll < 0.45:
            atk = current_attacker.staff_strike(defender, duration=0.45)
            atk_dur = 0.45
            strike_offset = 0.20
        elif current_attacker.weapon == "sword" and attack_roll < 0.45:
            # Sword slash
            atk = current_attacker.slash(defender, duration=0.45)
            atk_dur = 0.45
            strike_offset = 0.20
        elif attack_roll < 0.30:
            # Uppercut launcher
            atk = current_attacker.uppercut(defender, duration=0.50)
            atk_dur = 0.50
            strike_offset = 0.22
        elif attack_roll < 0.60:
            # High kick
            atk = current_attacker.kick(defender, duration=0.50)
            atk_dur = 0.50
            strike_offset = 0.24
        elif attack_roll < 0.85:
            # Fast punch
            atk = current_attacker.punch(defender, duration=0.40)
            atk_dur = 0.40
            strike_offset = 0.18
        else:
            # 2-hit quick combo
            if current_attacker.weapon == "staff":
                combo_name = "staff_combo"
            elif current_attacker.weapon == "sword":
                combo_name = "ninja_rush"
            else:
                combo_name = "boxing_flurry"
            atk = current_attacker.combo(combo_name, target=defender)
            atk_dur = atk.duration
            strike_offset = 0.20

        scene.at(t, atk)

        # Defender Reaction
        defense_roll = rng.random()
        if defense_roll < 0.35:
            # Block
            scene.at(t + strike_offset - 0.08, defender.block(duration=0.45))
        elif defense_roll < 0.60:
            # Dodge
            scene.at(t + strike_offset - 0.08, defender.dodge(duration=0.45))
        else:
            # Clean direct hit (handled automatically by resolve_attack)
            pass

        t += atk_dur + rng.uniform(0.15, 0.40)

        # Reposition if needed
        dist = abs(A.x - B.x)
        if dist > 260.0:
            closer = A if A.x < B.x else B
            scene.at(t, closer.walk_to(closer.x + (60 if closer == A else -60), duration=0.4))
            t += 0.45

        # Alternate initiative with chance of combo flurry
        if rng.random() < 0.75:
            current_attacker = defender

    # 4. Climactic Finisher (K.O.)
    winner = A if rng.random() < 0.5 else B
    loser = B if winner == A else A

    # Decisive strike
    if winner.weapon:
        finisher = winner.slash(loser, duration=0.55, damage=35.0)
    else:
        finisher = winner.uppercut(loser, duration=0.55, damage=35.0)

    scene.at(t, finisher)
    t += 0.35

    # Loser gets launched / knocked back and collapses
    scene.at(t, loser.fall(duration=1.4))

    # K.O. banner
    scene.caption("K.O.", t + 0.3, t + 2.5)

    return scene
