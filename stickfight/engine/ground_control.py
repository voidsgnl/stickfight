from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from stickfight.engine.fighter import Fighter


@dataclass
class GroundControl:
    """Shared relationship driving both fighters in grounded combat."""
    attacker: "Fighter"
    defender: "Fighter"
    position: str = "mount"
    transition: float = 1.0
    from_position: str | None = None

    VALID_POSITIONS = {"mount", "guard"}

    def __post_init__(self) -> None:
        if self.position not in self.VALID_POSITIONS:
            raise ValueError("position must be 'mount' or 'guard'")
        self.sync()

    @property
    def dominant(self) -> "Fighter":
        return self.attacker

    def set_position(self, position: str, transition: float = 0.0) -> None:
        if position not in self.VALID_POSITIONS:
            raise ValueError("position must be 'mount' or 'guard'")
        self.from_position = self.position
        self.position = position
        self.transition = max(0.0, min(1.0, transition))
        self.sync()

    def sync(self) -> None:
        self.attacker._ground_control_target = self.defender
        self.attacker._ground_control_mode = self.position
        self.attacker._ground_control_blend = self.transition
        self.defender._grapple_attacker = self.attacker
        self.defender._grapple_mode = (
            "bottom_guard" if self.position == "mount" else "bottom_mount"
        )

    def reverse(self, position: str = "mount") -> None:
        """Transfer top control from the current attacker to the defender."""
        if position not in self.VALID_POSITIONS:
            raise ValueError("position must be 'mount' or 'guard'")
        self.attacker, self.defender = self.defender, self.attacker
        self.from_position = None
        self.position = position
        self.transition = 0.0
        self.sync()

    def release(self) -> None:
        self.attacker.clear_ground_control()
        self.defender.clear_grapple_reaction()
