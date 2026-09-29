"""Integration tests for scene-level combat impact responses."""

from stickfight.engine.scene import FightScene
from stickfight.engine.collision import Hitbox
from stickfight.scripting.actions import KnockbackAction


def test_scene_routes_resolved_hit_through_impact_system():
    scene = FightScene(width=1080, height=1920)
    attacker = scene.add_fighter("A", x=400, y=1500)
    defender = scene.add_fighter("B", x=420, y=1500)

    # Keep the test independent of animation timing: resolve_attack consumes
    # an already-authored hitbox, exactly as the action layer does.
    hitbox = Hitbox(
        x=420.0,
        y=1370.0,
        radius=80.0,
        damage=24.0,
        knockback_x=120.0,
        attacker_name="A",
        attack_type="punch",
    )

    scene.resolve_attack(attacker, defender, hitbox)

    assert defender.health == 76.0
    assert defender.state == "knockback"
    assert scene.effects.shockwaves
    assert scene.effects.particles
    assert scene.camera.shake_timer > 0.0
    assert scene.audio.scheduled_events


def test_attack_specific_impact_profiles_change_response():
    scene = FightScene(width=1080, height=1920)
    attacker = scene.add_fighter("A", x=400, y=1500)
    defender = scene.add_fighter("B", x=420, y=1500)

    hitbox = Hitbox(
        x=420.0, y=1370.0, radius=80.0, damage=10.0,
        knockback_x=100.0, attacker_name="A", attack_type="jab",
    )
    scene.resolve_attack(attacker, defender, hitbox)
    jab_shake = scene.camera.shake_intensity
    jab_sound = scene.audio.scheduled_events[-1][1]

    scene.reset()
    hitbox.attack_type = "kick"
    hitbox.damage = 10.0
    scene.resolve_attack(attacker, defender, hitbox)
    kick_shake = scene.camera.shake_intensity
    kick_sound = scene.audio.scheduled_events[-1][1]

    assert jab_sound == "punch"
    assert kick_sound == "kick"
    assert kick_shake > jab_shake



def test_fighter_physics_update_keeps_world_position_in_sync():
    fighter = Fighter("A", x=400, y=1500)
    fighter.apply_impulse(120.0, -300.0)
    fighter.update_physics(0.05)

    assert fighter.x == fighter.physics.x
    assert fighter.y == fighter.physics.y
    assert fighter.is_airborne is True


def test_knockback_action_uses_physics_velocity():
    scene = FightScene(width=1080, height=1920)
    fighter = scene.add_fighter("A", x=400, y=1500)
    action = KnockbackAction(fighter, distance=140.0, duration=0.7)

    action.on_start(scene)

    assert fighter.physics.vx < 0.0
    assert fighter.physics.x == fighter.x

    action.update(scene, 0.35, 0.35)
    assert fighter.physics.x != 400.0
