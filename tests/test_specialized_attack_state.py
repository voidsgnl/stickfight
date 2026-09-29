from stickfight.engine.fighter import Fighter


def test_attack_state_selects_specialized_clip():
    fighter = Fighter("A")
    assert fighter.set_state("attack", clip_name="jab") is True
    assert fighter.animation_state.current == "attack"
    assert fighter.active_clip.name == "jab"
    assert fighter.attack_timing is not None
