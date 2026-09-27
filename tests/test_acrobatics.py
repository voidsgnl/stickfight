import pytest
from stickfight.engine.fighter import Fighter
from stickfight.engine.scene import FightScene
from stickfight.scripting.generator import generate_fight


def test_throw_action_mechanics():
    scene = FightScene(width=1080, height=1920)
    attacker = scene.add_fighter("Brawler", x=400, y=1500)
    defender = scene.add_fighter("Target", x=540, y=1500)

    throw = attacker.throw(defender, duration=0.75, damage=32.0)
    throw.on_start(scene)

    # 1. Before grab
    throw.update(scene, 0.10, 0.10)
    assert not throw.grabbed
    assert defender.health == 100.0

    # 2. Grab latch
    throw.update(scene, 0.20, 0.10)
    assert throw.grabbed
    assert defender.state == "hit"
    assert defender.active_clip.name == "thrown_slam"

    # 3. Ground slam impact
    throw.update(scene, 0.55, 0.35)
    assert throw.slammed
    assert defender.health == pytest.approx(68.0)
    assert defender.state == "fallen"


def test_dive_kick_hitbox_and_strike():
    scene = FightScene(width=1080, height=1920)
    attacker = scene.add_fighter("Ninja", x=350, y=1500)
    defender = scene.add_fighter("Opponent", x=500, y=1500)

    # Check hitbox during dive kick animation
    attacker.set_animation("dive_kick")
    attacker.update_animation(0.28)
    hitbox = attacker.get_hitbox()
    assert hitbox is not None
    assert hitbox.damage == 25.0
    assert hitbox.knockback_x > 0

    # Execute DiveKickAction
    dive = attacker.dive_kick(defender, duration=0.65, damage=25.0)
    dive.on_start(scene)
    dive.update(scene, 0.30, 0.30)
    assert dive.hit_registered
    assert defender.health == pytest.approx(75.0)



def test_air_juggle_action():
    scene = FightScene(width=1080, height=1920)
    attacker = scene.add_fighter("MartialArtist", x=400, y=1500)
    defender = scene.add_fighter("AirborneTarget", x=480, y=1500)

    # Air juggle strike
    juggle = attacker.air_juggle(defender, duration=0.55, damage=22.0)
    juggle.on_start(scene)
    juggle.update(scene, 0.30, 0.30)

    assert juggle.hit_registered
    assert defender.health == pytest.approx(78.0)
    assert defender.active_clip.name == "juggle_hit"


def test_wall_bounce_action():
    scene = FightScene(width=1080, height=1920)
    defender = scene.add_fighter("Opponent", x=980, y=1500, facing=1)

    initial_facing = defender.facing
    bounce = defender.wall_bounce(wall_x=1020.0, duration=0.65)
    bounce.on_start(scene)

    bounce.update(scene, 0.25, 0.25)
    assert bounce.bounced
    assert defender.facing == -initial_facing  # Rebounds in opposite direction

    bounce.on_finish(scene)
    assert defender.state == "fallen"


def test_acrobatic_combo_presets():
    scene = FightScene(width=1080, height=1920)
    attacker = scene.add_fighter("A", x=400, y=1500)
    defender = scene.add_fighter("B", x=520, y=1500)

    # Acrobatic slam combo
    combo = attacker.combo("acrobatic_slam", target=defender)
    assert len(combo.actions) == 3

    # Juggle master combo
    juggle_combo = attacker.combo("juggle_master", target=defender)
    assert len(juggle_combo.actions) == 3


def test_procedural_generator_with_acrobatics():
    scene = generate_fight(duration=6.0, fighter_a_type="ninja", fighter_b_type="brawler", seed=42)
    assert len(scene.fighters) == 2
    assert scene.timeline.duration > 0.0
