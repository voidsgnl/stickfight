from stickfight.engine.fighter import Fighter


def test_clinch_creates_two_contact_hand_targets():
    attacker = Fighter("A", x=500, y=1500)
    defender = Fighter("B", x=560, y=1500)

    attacker.set_grapple_targets(defender, mode="clinch")
    attacker.set_animation("clinch_knee", loop=False)
    attacker.update_animation(0.18)

    joints = attacker.get_world_joints()
    pelvis = defender.get_hurtbox().pelvis_pos

    right_error = ((joints["right_hand"][0] - pelvis[0]) ** 2 + (joints["right_hand"][1] - (pelvis[1] - 28.0)) ** 2) ** 0.5
    left_error = ((joints["left_hand"][0] - pelvis[0]) ** 2 + (joints["left_hand"][1] - (pelvis[1] + 18.0)) ** 2) ** 0.5

    assert right_error < 45.0
    assert left_error < 55.0


def test_takedown_reaction_orients_defender_to_attacker():
    attacker = Fighter("A", x=700, y=1500)
    defender = Fighter("B", x=600, y=1500)

    defender.apply_grapple_reaction(attacker, mode="takedown")

    assert defender.facing == 1
    assert defender.active_clip.name == "fall"
