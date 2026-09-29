"""
Animation state machine for combat characters.

The state machine sits above AnimationPlayer. It decides which animation state
is allowed next; AnimationPlayer remains responsible for timing and blending.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Set


DEFAULT_TRANSITIONS: Dict[str, Set[str]] = {
    "idle": {"walk", "run", "attack", "block", "dodge", "hit", "airborne", "fallen"},
    "walk": {"idle", "run", "attack", "block", "dodge", "hit", "airborne", "fallen"},
    "run": {"idle", "walk", "attack", "dodge", "hit", "airborne", "fallen"},
    "attack": {"idle", "recovery", "attack", "hit", "knockback", "airborne", "fallen"},
    "recovery": {"idle", "attack", "block", "dodge", "hit", "walk"},
    "block": {"idle", "attack", "dodge", "hit", "recovery"},
    "dodge": {"idle", "attack", "walk", "run", "hit", "recovery"},
    "hit": {"knockback", "idle", "attack", "fallen", "recovery"},
    "knockback": {"idle", "hit", "fallen", "recovery"},
    "airborne": {"attack", "hit", "fallen", "idle"},
    "fallen": {"idle", "hit", "grounded"},
    "grounded": {"idle", "attack", "hit", "fallen"},
}


@dataclass
class AnimationState:
    name: str
    clip: str
    loop: bool = False
    blend: float = 0.06


class AnimationStateMachine:
    """Validates state transitions and maps states to animation clips."""

    def __init__(
        self,
        states: Optional[Dict[str, AnimationState]] = None,
        transitions: Optional[Dict[str, Set[str]]] = None,
        initial: str = "idle",
    ):
        self.states = states or self._default_states()
        self.transitions = transitions or DEFAULT_TRANSITIONS
        if initial not in self.states:
            raise KeyError(f"Unknown initial state: {initial}")
        self.current = initial
        self.previous: Optional[str] = None
        self.state_time = 0.0

    @staticmethod
    def _default_states() -> Dict[str, AnimationState]:
        return {
            "idle": AnimationState("idle", "idle", loop=True, blend=0.10),
            "walk": AnimationState("walk", "walk", loop=True, blend=0.08),
            "run": AnimationState("run", "walk", loop=True, blend=0.06),
            "attack": AnimationState("attack", "punch", loop=False, blend=0.04),
            "recovery": AnimationState("recovery", "idle", loop=True, blend=0.08),
            "block": AnimationState("block", "block", loop=True, blend=0.06),
            "dodge": AnimationState("dodge", "dodge", loop=False, blend=0.04),
            "hit": AnimationState("hit", "hit", loop=False, blend=0.03),
            "knockback": AnimationState("knockback", "knockback", loop=False, blend=0.03),
            "airborne": AnimationState("airborne", "jump", loop=False, blend=0.05),
            "fallen": AnimationState("fallen", "fall", loop=False, blend=0.04),
            "grounded": AnimationState("grounded", "grounded_guard", loop=True, blend=0.08),
        }

    def can_transition(self, target: str) -> bool:
        if target not in self.states:
            return False
        if target == self.current:
            return True
        return target in self.transitions.get(self.current, set())

    def transition_to(self, target: str) -> bool:
        if not self.can_transition(target):
            return False
        if target != self.current:
            self.previous = self.current
            self.current = target
            self.state_time = 0.0
        return True

    def update(self, dt: float) -> None:
        self.state_time += max(0.0, float(dt))

    def reset(self) -> None:
        self.current = "idle"
        self.previous = None
        self.state_time = 0.0
