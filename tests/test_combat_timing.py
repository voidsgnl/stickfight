"""Tests for normalized combat timing and hitbox activation."""

from stickfight.engine.combat_timing import ATTACK_TIMINGS
from stickfight.engine.fighter import Fighter


def test_punch_has_ordered_combat_phases():
    timing = ATTACK_TIMINGS["punch"]
    assert timing.phase(0.05, 0.45) == "anticipation"
    assert timing.phase(0.18, 0.45) == "contact"
    assert timing.phase(0.30, 0.45) == "recovery"


def test_attack_timing_scales_with_clip_duration():
    timing = ATTACK_TIMINGS["punch"]
    assert timing.is_active(0.18, 0.45)
    assert timing.is_active(0.36, 0.90)
    assert not timing.is_active(0.10, 0.45)


def test_fighter_hitbox_only_exists_during_contact_window():
    fighter = Fighter("A", x=400, y=1500)
    fighter.set_animation("punch", loop=False)

    fighter.update_animation(0.10)
    assert fighter.attack_phase == "anticipation"
    assert fighter.get_hitbox() is None

    fighter.update_animation(0.08)
    assert fighter.attack_phase == "contact"
    assert fighter.get_hitbox() is not None

    fighter.update_animation(0.18)
    assert fighter.get_hitbox() is None


def test_fighter_exposes_impact_marker():
    fighter = Fighter("A", x=400, y=1500)
    fighter.set_animation("punch", loop=False)
    fighter.update_animation(0.18)
    assert fighter.is_attack_impact()
