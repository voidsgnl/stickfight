"""
Stick Fight Video Engine
Code-driven 2D animation engine for automated vertical stick fight videos.
"""

from stickfight.engine.scene import FightScene, ChoreographyError
from stickfight.engine.stats import FighterStats
from stickfight.engine.fighter import Fighter
from stickfight.engine.skeleton import Pose
from stickfight.engine.camera import Camera
from stickfight.engine.renderer import Renderer
from stickfight.engine.animation import AnimationClip
from stickfight.engine.characters import (
    create_ninja,
    create_samurai,
    create_brawler,
    create_monk,
    create_cyborg,
)
from stickfight.scripting.generator import generate_fight, generate_best_fight, score_fight

__all__ = [
    "FightScene",
    "ChoreographyError",
    "FighterStats",
    "Fighter",
    "Pose",
    "Camera",
    "Renderer",
    "AnimationClip",
    "create_ninja",
    "create_samurai",
    "create_brawler",
    "create_monk",
    "create_cyborg",
    "generate_fight",
    "generate_best_fight",
    "score_fight",
]
