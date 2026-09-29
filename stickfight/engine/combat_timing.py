"""Combat timing metadata for animation-driven attacks.

Attack timing is normalized to each clip's 0..1 progress so custom clip
durations keep the same anticipation/active/recovery proportions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class AttackTiming:
    """Normalized timing windows for a combat animation."""

    anticipation_end: float
    active_start: float
    active_end: float
    follow_through_end: float
    impact: float

    def __post_init__(self) -> None:
        values = (
            self.anticipation_end,
            self.active_start,
            self.active_end,
            self.follow_through_end,
            self.impact,
        )
        if any(not 0.0 <= value <= 1.0 for value in values):
            raise ValueError("Attack timing markers must be normalized to 0..1")
        if not (
            self.anticipation_end
            <= self.active_start
            <= self.active_end
            <= self.follow_through_end
        ):
            raise ValueError("Attack timing phases must be ordered")

    def progress(self, elapsed: float, duration: float) -> float:
        """Return normalized clip progress for elapsed seconds."""
        if duration <= 0.0:
            return 1.0
        return max(0.0, min(1.0, elapsed / duration))

    def phase(self, elapsed: float, duration: float) -> str:
        """Return the named combat phase at the supplied playback time."""
        p = self.progress(elapsed, duration)
        if p < self.anticipation_end:
            return "anticipation"
        if p < self.active_start:
            return "action"
        if p <= self.active_end:
            return "contact"
        if p <= self.follow_through_end:
            return "follow_through"
        return "recovery"

    def is_active(self, elapsed: float, duration: float) -> bool:
        p = self.progress(elapsed, duration)
        return self.active_start <= p <= self.active_end

    def is_impact_frame(self, elapsed: float, duration: float, tolerance: float = 0.03) -> bool:
        p = self.progress(elapsed, duration)
        return abs(p - self.impact) <= max(0.0, tolerance)

    def crossed_impact(self, previous_elapsed: float, elapsed: float, duration: float) -> bool:
        """Return True when playback crosses the authored impact marker.
        if duration <= 0.0:
            return False
        previous = self.progress(previous_elapsed, duration)
        current = self.progress(elapsed, duration)
        return previous < self.impact <= current


# One timing definition per attack clip. Values are normalized so the same
# choreography remains correct when an action overrides its duration.
ATTACK_TIMINGS: Dict[str, AttackTiming] = {
    "punch": AttackTiming(0.20, 0.36, 0.62, 0.78, 0.40),
    "kick": AttackTiming(0.22, 0.42, 0.68, 0.82, 0.45),
    "uppercut": AttackTiming(0.20, 0.40, 0.68, 0.82, 0.45),
    "sweep": AttackTiming(0.25, 0.40, 0.72, 0.84, 0.46),
    "slash": AttackTiming(0.22, 0.40, 0.66, 0.82, 0.44),
    "jab": AttackTiming(0.20, 0.32, 0.58, 0.76, 0.36),
    "cross": AttackTiming(0.18, 0.40, 0.66, 0.82, 0.45),
    "hook": AttackTiming(0.20, 0.40, 0.66, 0.82, 0.45),
    "low_kick": AttackTiming(0.22, 0.42, 0.68, 0.84, 0.48),
    "clinch_knee": AttackTiming(0.24, 0.46, 0.72, 0.86, 0.50),
    "takedown": AttackTiming(0.25, 0.58, 0.76, 0.90, 0.64),
    "ground_pound": AttackTiming(0.22, 0.50, 0.76, 0.88, 0.58),
}
