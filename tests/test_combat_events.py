"""Tests for animation-driven combat impact events."""

from stickfight.engine.combat_events import CombatEventBus, CombatImpactEvent
from stickfight.engine.fighter import Fighter


def test_impact_event_bus_notifies_subscribers():
    bus = CombatEventBus()
    events = []
    bus.subscribe_impact(events.append)

    event = CombatImpactEvent(
        attacker=object(),
        defender=None,
        attack_type="punch",
        x=10.0,
        y=20.0,
        damage=15.0,
    )
    bus.emit_impact(event)

    assert events == [event]


def test_fighter_only_emits_impact_at_marker():
    fighter = Fighter("A", x=400, y=1500)
    fighter.set_animation("punch", loop=False)
    events = []
    fighter.combat_events.subscribe_impact(events.append)

    fighter.update_animation(0.10)
    assert fighter.emit_impact(damage=15.0) is False
    assert events == []

    fighter.update_animation(0.08)
    assert fighter.is_attack_impact()
    assert fighter.emit_impact(damage=15.0) is True
    assert fighter.emit_impact(damage=15.0) is False
    assert len(events) == 1
    assert events[0].attack_type == "punch"


def test_impact_event_crossing_survives_large_frame_step():
    fighter = Fighter("A", x=400, y=1500)
    fighter.set_animation("punch", loop=False)

    # Jump from before the marker to after it. The event must still be
    # consumable even though playback did not land inside the old tolerance.
    fighter.update_animation(0.10)
    assert fighter.consume_attack_impact() is False

    fighter.update_animation(0.15)
    assert fighter.consume_attack_impact() is True
    assert fighter.consume_attack_impact() is False
