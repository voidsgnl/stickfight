from stickfight.studio.combat import (
    STUDIO_FIGHT_ACTIONS,
    action_label,
    normalize_action,
)


def test_studio_fight_actions_include_core_combat_moves():
    for action in ("jab", "cross", "hook", "low_kick", "block", "dodge", "takedown", "ground_pound"):
        assert action in STUDIO_FIGHT_ACTIONS


def test_unknown_studio_action_falls_back_to_idle():
    assert normalize_action("not_a_fight_move") == "idle"
    assert normalize_action("Ground Pound") == "ground_pound"


def test_action_labels_are_fight_specific():
    assert action_label("cross") == "Cross"
    assert action_label("ground_pound") == "Ground Pound"
