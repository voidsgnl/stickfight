"""Animation-driven combat impact events.

The event is intentionally small and engine-neutral: systems such as camera,
effects, and audio can subscribe without the animation system knowing about
their implementations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional


@dataclass(frozen=True)
class CombatImpactEvent:
    attacker: object
    defender: Optional[object]
    attack_type: str
    x: float
    y: float
    damage: float
    blocked: bool = False


class CombatEventBus:
    """Synchronous one-shot event bus for combat impacts."""

    def __init__(self) -> None:
        self._impact_listeners: List[Callable[[CombatImpactEvent], None]] = []

    def subscribe_impact(self, listener: Callable[[CombatImpactEvent], None]) -> None:
        if listener not in self._impact_listeners:
            self._impact_listeners.append(listener)

    def emit_impact(self, event: CombatImpactEvent) -> None:
        for listener in tuple(self._impact_listeners):
            listener(event)
