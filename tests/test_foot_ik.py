from math import isclose

from stickfight.engine.fighter import Fighter


def test_grounded_foot_ik_keeps_feet_on_ground():
    fighter = Fighter("A", x=400, y=1500)
    fighter.set_animation("kick", loop=False)
    fighter.update_animation(0.20)

    joints = fighter.get_world_joints()
    assert isclose(joints["left_foot"][1], fighter.y, abs_tol=1e-4)
    assert isclose(joints["right_foot"][1], fighter.y, abs_tol=1e-4)


def test_airborne_fighter_does_not_force_feet_to_ground():
    fighter = Fighter("A", x=400, y=1500)
    fighter.physics.apply_impulse(0.0, -500.0)
    fighter.set_animation("jump", loop=False)
    fighter.update_animation(0.10)

    joints = fighter.get_world_joints()
    assert joints["left_foot"][1] < fighter.y
    assert joints["right_foot"][1] < fighter.y
