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
