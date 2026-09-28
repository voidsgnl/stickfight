"""Per-archetype gameplay stats. These change behaviour, not just looks."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional


def _weights(**kw: float) -> Dict[str, float]:
    return dict(kw)


@dataclass(frozen=True)
class FighterStats:
    """Numeric traits applied by the combat engine and the fight generator.

    health      starting/maximum health
    power       outgoing damage multiplier
    defense     incoming damage divisor (>1 = tougher)
    speed       animation + default action speed multiplier
    reach       hitbox radius multiplier
    block_bias / dodge_bias   how often the generator has this fighter defend
    attack_weights            relative move preference used by the generator
    """
    health: float = 100.0
    power: float = 1.0
    defense: float = 1.0
    speed: float = 1.0
    reach: float = 1.0
    block_bias: float = 0.35
    dodge_bias: float = 0.25
    attack_weights: Dict[str, float] = field(default_factory=lambda: _weights(
        punch=1.0, kick=1.0, uppercut=1.0, weapon=1.0, combo=0.5))


STATS_DEFAULT = FighterStats()
STATS_NINJA = FighterStats(
    health=85.0, power=0.95, speed=1.25, dodge_bias=0.40, block_bias=0.15,
    attack_weights=_weights(punch=0.6, kick=1.0, uppercut=0.5, weapon=1.6, combo=1.0))
STATS_SAMURAI = FighterStats(
    health=100.0, power=1.15, speed=1.0, block_bias=0.40, dodge_bias=0.20,
    attack_weights=_weights(punch=0.4, kick=0.6, uppercut=0.6, weapon=2.0, combo=0.7))
STATS_BRAWLER = FighterStats(
    health=130.0, power=1.25, defense=1.2, speed=0.85, reach=0.95, block_bias=0.30, dodge_bias=0.10,
    attack_weights=_weights(punch=1.6, kick=0.8, uppercut=1.6, weapon=1.0, combo=0.8))
STATS_MONK = FighterStats(
    health=95.0, power=0.9, speed=1.1, reach=1.2, block_bias=0.25, dodge_bias=0.35,
    attack_weights=_weights(punch=0.5, kick=1.4, uppercut=0.6, weapon=1.8, combo=1.0))
STATS_CYBORG = FighterStats(
    health=110.0, power=1.0, defense=1.1, speed=1.0, reach=1.1, block_bias=0.45, dodge_bias=0.15,
    attack_weights=_weights(punch=1.0, kick=1.2, uppercut=0.8, weapon=1.0, combo=1.5))

STATS_BY_DESIGN: Dict[str, FighterStats] = {
    "ninja": STATS_NINJA, "samurai": STATS_SAMURAI, "warrior": STATS_SAMURAI,
    "brawler": STATS_BRAWLER, "monk": STATS_MONK,
    "cyborg": STATS_CYBORG, "cyber": STATS_CYBORG,
}


def stats_for_design(design: Optional[str]) -> FighterStats:
    return STATS_BY_DESIGN.get((design or "").lower(), STATS_DEFAULT)
