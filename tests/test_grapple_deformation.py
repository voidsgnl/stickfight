from stickfight.engine.fighter import Fighter


def test_takedown_deformation_changes_defender_body_with_progress():
    attacker = Fighter("A", x=700, y=1500)
    defender = Fighter("B", x=600, y=1500)

    defender.apply_grapple_reaction(attacker, mode="takedown")
    defender.update_animation(0.05)
    early = defender.current_pose.copy()

    defender.update_animation(0.20)
    late = defender.current_pose.copy()

    assert late.get("chest") != early.get("chest")
    assert late.get("head") != early.get("head")
    assert late.get("left_knee") != early.get("left_knee")


def test_clear_grapple_reaction_stops_procedural_deformation():
    attacker = Fighter("A", x=700, y=1500)
    defender = Fighter("B", x=600, y=1500)

    defender.apply_grapple_reaction(attacker, mode="takedown")
    assert defender._grapple_attacker is attacker

    defender.clear_grapple_reaction()

    assert defender._grapple_attacker is None
    assert defender._grapple_mode is None


def test_takedown_reaches_ground_settlement_phase():
    attacker = Fighter("A", x=700, y=1500)
    defender = Fighter("B", x=600, y=1500)

    defender.apply_grapple_reaction(attacker, mode="takedown")
    defender.update_animation(0.80)

    pose = defender.current_pose
    assert pose.get("pelvis")[1] > 40.0
    assert pose.get("chest")[1] > -10.0


def test_takedown_attacker_follow_through_crouches_and_tracks_contact():
    attacker = Fighter("A", x=500, y=1500)
    defender = Fighter("B", x=580, y=1500)

    attacker.set_grapple_targets(defender, mode="takedown")
    attacker.set_animation("takedown", loop=False)
    attacker.update_animation(0.45)

    assert attacker.current_pose.get("pelvis")[1] > 0.0
    assert "left_hand" in attacker.weapon_ik_targets
    assert attacker.ik_target is not None


def test_takedown_enters_persistent_grounded_state_after_settlement():
    attacker = Fighter("A", x=700, y=1500)
    defender = Fighter("B", x=600, y=1500)

    defender.apply_grapple_reaction(attacker, mode="takedown")
    assert defender.animation_state.current == "fallen"

    defender.enter_grounded_control()

    assert defender.state == "grounded"
    assert defender.animation_state.current == "grounded"
    assert defender.physics.is_grounded is True


def test_ground_pound_targets_grounded_opponent():
    attacker = Fighter("A", x=500, y=1500)
    defender = Fighter("B", x=560, y=1500)
    defender.enter_grounded_control()

    attacker.set_grapple_targets(defender, mode="ground_pound")

    assert attacker.ik_target is not None
    assert "left_hand" in attacker.weapon_ik_targets
    assert attacker._grapple_target is defender
    assert attacker._grapple_mode == "ground_pound"
