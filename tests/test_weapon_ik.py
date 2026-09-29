from stickfight.engine.fighter import Fighter


def test_two_handed_sword_attack_tracks_both_grips():
    attacker = Fighter("A", x=400, y=1500, weapon="sword")
    defender = Fighter("B", x=620, y=1500)
    attacker.set_animation("slash", loop=False)
    attacker.aim_attack_at(defender)
    attacker.update_animation(0.22)

    joints = attacker.get_world_joints()
    target = defender.get_hurtbox().head_pos

    primary_error = ((joints["right_hand"][0] - target[0]) ** 2 + (joints["right_hand"][1] - target[1]) ** 2) ** 0.5
    secondary = joints["left_hand"]
    grip_distance = ((secondary[0] - joints["right_hand"][0]) ** 2 + (secondary[1] - joints["right_hand"][1]) ** 2) ** 0.5

    assert primary_error < 35.0
    assert 15.0 < grip_distance < 90.0


def test_clear_ik_removes_weapon_targets():
    fighter = Fighter("A", weapon="staff")
    defender = Fighter("B")
    fighter.set_animation("slash", loop=False)
    fighter.aim_attack_at(defender)

    assert fighter.ik_target is not None
    assert fighter.weapon_ik_targets

    fighter.clear_ik_target()

    assert fighter.ik_target is None
    assert not fighter.weapon_ik_targets
