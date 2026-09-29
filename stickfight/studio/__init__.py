"""Story Animation Studio authoring layer.

This package owns project/scene/timeline data. It intentionally does not own
combat physics or rendering so the existing engine remains reusable.
"""

from .combat import STUDIO_FIGHT_ACTIONS, action_label, normalize_action

from .model import (
    AnimationProject,
    AnimationScene,
    CharacterAsset,
    CharacterInstance,
    Keyframe,
    TimelineTrack,
    TimelineEvent,
    VisualStyle,
)

__all__ = [
    "AnimationProject",
    "AnimationScene",
    "CharacterAsset",
    "CharacterInstance",
    "Keyframe",
    "TimelineTrack",
    "TimelineEvent",
    "VisualStyle",
    "STUDIO_FIGHT_ACTIONS",
    "action_label",
    "normalize_action",
]
