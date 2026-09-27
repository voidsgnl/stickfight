"""
Stick Fight Video Engine
Code-driven 2D animation engine for automated vertical stick fight videos.
"""

from stickfight.engine.scene import FightScene
from stickfight.engine.fighter import Fighter
from stickfight.engine.skeleton import Pose
from stickfight.engine.camera import Camera
from stickfight.engine.renderer import Renderer
from stickfight.engine.animation import AnimationClip

__all__ = [
    "FightScene",
    "Fighter",
    "Pose",
    "Camera",
    "Renderer",
    "AnimationClip",
]
