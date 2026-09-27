import pytest
from stickfight.engine.fighter import Fighter
from stickfight.engine.collision import check_hit


def test_fighter_initialization():
    f = Fighter("A", x=300, y=1500, facing=1)
    assert f.name == "A"
    assert f.x == 300
    assert f.y == 1500
    assert f.facing == 1
    assert f.health == 100.0


def test_fighter_hurtbox():
    f = Fighter("B", x=600, y=1500)
    hb = f.get_hurtbox()
    assert hb.head_radius > 0
    assert hb.torso_radius > 0
    assert hb.head_pos[1] < hb.pelvis_pos[1]  # head is above pelvis


def test_fighter_punch_hitbox():
    f = Fighter("A", x=400, y=1500, facing=1)
    f.set_animation("punch")
    f.update_animation(0.18)  # Advance to punch strike frame
    hitbox = f.get_hitbox()
    assert hitbox is not None
    assert hitbox.damage > 0
    assert hitbox.attack_type == "punch"
