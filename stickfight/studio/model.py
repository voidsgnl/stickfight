"""Serializable data model for the Story Animation Studio.

The model is deliberately renderer/physics agnostic.  A scene can contain
unlimited character instances, and each character asset can select its own
visual style without changing the fighter/combat engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class VisualStyle:
    """A named visual identity, e.g. ink, anime, cartoon, or custom."""

    id: str
    renderer: str = "segmented"
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CharacterAsset:
    """Reusable character definition independent of a scene instance."""

    id: str
    name: str
    visual_style: VisualStyle = field(
        default_factory=lambda: VisualStyle("classic", "segmented")
    )
    archetype: str = "classic"
    proportions: str = "default"
    palette: Dict[str, Any] = field(default_factory=dict)
    animation_library: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CharacterInstance:
    """A placed character that references an asset instead of duplicating it."""

    id: str
    asset_id: str
    name: Optional[str] = None
    x: float = 0.0
    y: float = 0.0
    rotation: float = 0.0
    scale: float = 1.0
    visible: bool = True
    layer: int = 0
    overrides: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Keyframe:
    frame: int
    values: Dict[str, Any] = field(default_factory=dict)
    easing: str = "linear"


@dataclass
class TimelineEvent:
    id: str
    start_frame: int
    end_frame: int
    action: str
    target_id: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TimelineTrack:
    id: str
    name: str
    kind: str
    target_id: Optional[str] = None
    keyframes: List[Keyframe] = field(default_factory=list)
    events: List[TimelineEvent] = field(default_factory=list)
    muted: bool = False
    locked: bool = False


@dataclass
class AnimationScene:
    id: str
    name: str
    duration_frames: int = 180
    fps: int = 30
    characters: List[CharacterInstance] = field(default_factory=list)
    tracks: List[TimelineTrack] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_character(self, instance: CharacterInstance) -> None:
        if any(c.id == instance.id for c in self.characters):
            raise ValueError(f"duplicate character instance: {instance.id}")
        self.characters.append(instance)

    def add_track(self, track: TimelineTrack) -> None:
        if any(t.id == track.id for t in self.tracks):
            raise ValueError(f"duplicate timeline track: {track.id}")
        self.tracks.append(track)


@dataclass
class AnimationProject:
    """Top-level document.

    Assets are reusable across scenes. Scenes only hold lightweight instances,
    which prevents a large project from becoming a collection of copied
    character definitions.
    """

    name: str
    version: int = 1
    assets: Dict[str, CharacterAsset] = field(default_factory=dict)
    scenes: List[AnimationScene] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_asset(self, asset: CharacterAsset) -> None:
        if asset.id in self.assets:
            raise ValueError(f"duplicate character asset: {asset.id}")
        self.assets[asset.id] = asset

    def add_scene(self, scene: AnimationScene) -> None:
        if any(s.id == scene.id for s in self.scenes):
            raise ValueError(f"duplicate scene: {scene.id}")
        self.scenes.append(scene)

    def validate(self) -> List[str]:
        """Return structural problems without touching the runtime engine."""

        errors: List[str] = []
        scene_ids = set()
        for scene in self.scenes:
            if scene.id in scene_ids:
                errors.append(f"duplicate scene: {scene.id}")
            scene_ids.add(scene.id)
            for character in scene.characters:
                if character.asset_id not in self.assets:
                    errors.append(
                        f"scene {scene.id}: missing character asset "
                        f"{character.asset_id}"
                    )
            for track in scene.tracks:
                if track.target_id and not any(
                    c.id == track.target_id for c in scene.characters
                ):
                    errors.append(
                        f"scene {scene.id}: track {track.id} targets "
                        f"missing instance {track.target_id}"
                    )
        return errors
