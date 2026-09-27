"""Integration tests for the fighter physics bridge."""

from stickfight.engine.scene import FightScene


def test_jump_uses_physics_and_lands():
    scene = FightScene(width=360, height=640, fps=30, ground_y=500)
    fighter = scene.add_fighter("A", x=120, y=500)
    scene.at(0.0, fighter.jump(height=100, duration=0.65))

    scene.update(1.0 / scene.fps)
    assert fighter.physics.is_grounded is False
    assert fighter.y < 500

    for _ in range(60):
        scene.update(1.0 / scene.fps)

    assert fighter.physics.is_grounded is True
    assert fighter.y == 500


def test_heavy_hit_applies_physical_impulse():
    scene = FightScene(width=600, height=800, fps=30, ground_y=500)
    attacker = scene.add_fighter("A", x=220, y=500, facing=1)
    defender = scene.add_fighter("B", x=300, y=500, facing=-1)
    initial_x = defender.x
    scene.at(0.0, attacker.kick(defender))

    for _ in range(20):
        scene.update(1.0 / scene.fps)

    assert defender.health < defender.max_health
    assert defender.x > initial_x


def test_reset_clears_physics_and_audio():
    scene = FightScene(width=360, height=640, fps=30, ground_y=500)
    fighter = scene.add_fighter("A", x=120, y=500)
    scene.at(0.0, fighter.jump(height=100))
    scene.update(1.0 / scene.fps)
    scene.audio.schedule_sound(0.1, "whoosh")

    scene.reset()

    assert scene.current_time == 0.0
    assert scene.audio.scheduled_events == []
    assert fighter.x == 120
    assert fighter.y == 500
    assert fighter.physics.is_grounded is True
    assert fighter.physics.vx == 0.0
    assert fighter.physics.vy == 0.0
