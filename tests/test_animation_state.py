"""Tests for combat animation state transitions."""

from stickfight.engine.animation_state import AnimationStateMachine


def test_state_machine_starts_idle():
    machine = AnimationStateMachine()
    assert machine.current == "idle"
    assert machine.state_time == 0.0


def test_state_machine_allows_attack_from_idle():
    machine = AnimationStateMachine()
    assert machine.transition_to("attack")
    assert machine.current == "attack"
    assert machine.previous == "idle"


def test_state_machine_rejects_invalid_transition():
    machine = AnimationStateMachine()
    assert not machine.transition_to("knockback")
    assert machine.current == "idle"


def test_state_machine_tracks_state_time():
    machine = AnimationStateMachine()
    machine.transition_to("attack")
    machine.update(0.25)
    assert machine.state_time == 0.25


def test_state_machine_supports_recovery_after_attack():
    machine = AnimationStateMachine()
    machine.transition_to("attack")
    assert machine.transition_to("recovery")
    assert machine.current == "recovery"
