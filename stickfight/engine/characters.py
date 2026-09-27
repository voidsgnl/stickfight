"""
Character templates and archetypes: Ninja, Samurai, Brawler, Monk, and Cyborg.
"""

from __future__ import annotations
from typing import Optional, Tuple, TYPE_CHECKING
from stickfight.engine.fighter import Fighter
from stickfight.engine.skeleton import (
    PROPORTIONS_NINJA,
    PROPORTIONS_SAMURAI,
    PROPORTIONS_BRAWLER,
    PROPORTIONS_MONK,
    PROPORTIONS_CYBORG,
)

if TYPE_CHECKING:
    from stickfight.engine.scene import FightScene


def create_ninja(
    scene: FightScene,
    name: str = "Shadow",
    x: float = 380.0,
    y: Optional[float] = None,
    facing: int = 1,
) -> Fighter:
    """Swift assassin: dark suit, red flowing headband ribbons, katana blade.

    Lean, narrow-stance rig with slightly longer arms/legs for a quick,
    agile silhouette distinct from the other archetypes.
    """
    f = scene.add_fighter(
        name=name,
        x=x,
        y=y,
        facing=facing,
        color=(45, 48, 56),
        line_width=10,
        scale=1.0,
        render_style="silhouette",
        proportions=PROPORTIONS_NINJA,
    )
    f.headband_color = (235, 45, 45)
    f.equip("sword")
    return f


def create_samurai(
    scene: FightScene,
    name: str = "Kensei",
    x: float = 700.0,
    y: Optional[float] = None,
    facing: int = -1,
) -> Fighter:
    """Disciplined swordmaster: silver armor suit, golden headband, katana.

    Balanced, canonical body proportions — the reference rig other
    archetypes are scaled relative to.
    """
    f = scene.add_fighter(
        name=name,
        x=x,
        y=y,
        facing=facing,
        color=(230, 235, 245),
        line_width=10,
        scale=1.0,
        render_style="segmented",
        proportions=PROPORTIONS_SAMURAI,
    )
    f.headband_color = (235, 190, 45)
    f.equip("sword")
    return f


def create_brawler(
    scene: FightScene,
    name: str = "Titan",
    x: float = 380.0,
    y: Optional[float] = None,
    facing: int = 1,
) -> Fighter:
    """Heavyweight bare-knuckle powerhouse: bold red, thicker frame.

    Wide-shouldered, wide-stance, shorter-limbed rig for a stocky,
    grounded power silhouette.
    """
    return scene.add_fighter(
        name=name,
        x=x,
        y=y,
        facing=facing,
        color=(235, 60, 60),
        line_width=12,
        scale=1.1,
        render_style="segmented",
        proportions=PROPORTIONS_BRAWLER,
    )


def create_monk(
    scene: FightScene,
    name: str = "Shaolin",
    x: float = 700.0,
    y: Optional[float] = None,
    facing: int = -1,
) -> Fighter:
    """Acrobatic martial artist equipped with wooden Bo staff.

    Tall, long-limbed rig suited to sweeping staff-range reach and
    acrobatic poses.
    """
    f = scene.add_fighter(
        name=name,
        x=x,
        y=y,
        facing=facing,
        color=(245, 140, 35),
        line_width=10,
        scale=1.0,
        render_style="segmented",
        proportions=PROPORTIONS_MONK,
    )
    f.headband_color = (245, 200, 70)
    f.equip("staff")
    return f


def create_cyborg(
    scene: FightScene,
    name: str = "Unit-01",
    x: float = 700.0,
    y: Optional[float] = None,
    facing: int = -1,
) -> Fighter:
    """Futuristic combat android: neon cyan glow aesthetic.

    Compact head with long, mechanical-reach limbs for an inhuman,
    angular silhouette.
    """
    return scene.add_fighter(
        name=name,
        x=x,
        y=y,
        facing=facing,
        color=(50, 220, 255),
        line_width=10,
        scale=1.0,
        render_style="tech",
        proportions=PROPORTIONS_CYBORG,
    )
