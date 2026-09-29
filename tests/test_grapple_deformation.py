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


def test_ground_escape_returns_fighter_to_standing_state():
    from stickfight.scripting.actions import GroundEscapeAction

    fighter = Fighter("B", x=600, y=1500)
    fighter.enter_grounded_control()
    action = GroundEscapeAction(fighter, duration=0.65)
    assert fighter.state == "grounded"

    class Scene:
        pass

    scene = Scene()
    action.on_start(scene)
    action.update(scene, 0.65, 0.65)

    assert fighter.state == "idle"
    assert fighter.animation_state.current == "idle"


def test_ground_reversal_releases_attacker():
    from stickfight.scripting.actions import GroundReversalAction

    defender = Fighter("B", x=600, y=1500)
    attacker = Fighter("A", x=540, y=1500)
    defender.enter_grounded_control()

    action = GroundReversalAction(defender, attacker, duration=0.75)
    action.on_start(None)
    action.update(None, 0.50, 0.50)

    assert defender.state == "idle"
    assert attacker.state == "fallen"
    assert attacker.physics.vx != 0.0


def test_ground_control_positions_attacker_over_grounded_defender():
    attacker = Fighter("A", x=500, y=1500)
    defender = Fighter("B", x=560, y=1500)
    defender.enter_grounded_control()

    assert attacker.enter_ground_control(defender)
    attacker.set_animation("grounded_guard", loop=True)
    attacker.update_animation(0.10)

    assert attacker._ground_control_target is defender
    assert attacker._ground_control_mode == "top"
    assert attacker.ik_target is not None
    assert "left_hand" in attacker.weapon_ik_targets
    assert abs(attacker.x - defender.x) < 60.0


def test_top_control_blends_in_and_sets_bottom_guard_relationship():
    attacker = Fighter("A", x=500, y=1500)
    defender = Fighter("B", x=560, y=1500)
    defender.enter_grounded_control()

    attacker.enter_ground_control(defender, mode="top")
    attacker.set_animation("grounded_guard", loop=True)
    before = attacker.current_pose.get("chest")
    attacker.update_animation(0.10)
    after = attacker.current_pose.get("chest")

    assert attacker._ground_control_blend > 0.0
    assert after != before
    assert defender._grapple_attacker is attacker
    assert defender._grapple_mode == "ground_control"
