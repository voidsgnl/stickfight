"""Integration tests for scene-level combat impact responses."""

from stickfight.engine.scene import FightScene
from stickfight.engine.collision import Hitbox


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
