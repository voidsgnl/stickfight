"""
Animation playback runtime.

AnimationClip describes poses; AnimationPlayer owns playback state and transitions.
This keeps animation timing/blending separate from Fighter, while preserving the
existing clip API used by the choreography and renderer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from stickfight.engine.animation import AnimationClip
from stickfight.engine.skeleton import Pose


@dataclass
class AnimationTransition:
    """Cross-fade from one clip into another over a short duration."""

    source_pose: Pose
    source_root_dx: float
    source_root_dy: float
    duration: float
    elapsed: float = 0.0


class AnimationPlayer:
    """Runtime controller for an animation clip library.

    The player owns clip selection, local time, looping, and cross-fade state.
    It deliberately does not know about Fighter, physics, or rendering.
    """

    def __init__(self, clips: dict[str, AnimationClip], initial: str = "idle"):
        if initial not in clips:
            raise KeyError(f"Unknown initial animation: {initial}")
        self.clips = clips
        self.active_clip: AnimationClip = clips[initial]
        self.clip_time: float = 0.0
        self.previous_clip: Optional[AnimationClip] = None
        self.transition: Optional[AnimationTransition] = None

    @property
    def current_name(self) -> str:
        return self.active_clip.name

    @property
    def finished(self) -> bool:
        return not self.active_clip.loop and self.clip_time >= self.active_clip.duration

    def play(
        self,
        clip_name: str,
        *,
        loop: Optional[bool] = None,
        blend: float = 0.0,
        restart: bool = True,
    ) -> bool:
        """Play a named clip, optionally blending from the current pose.

        Returns False for an unknown clip so callers can handle invalid
        choreography without corrupting the current animation.
        """
        clip = self.clips.get(clip_name)
        if clip is None:
            return False

        if not restart and clip is self.active_clip:
            return True

        source_pose, source_dx, source_dy = self.evaluate()
        self.previous_clip = self.active_clip
        self.active_clip = clip
        if loop is not None:
            self.active_clip.loop = loop
        self.clip_time = 0.0

        blend = max(0.0, float(blend))
        if blend > 0.0:
            self.transition = AnimationTransition(
                source_pose=source_pose,
                source_root_dx=source_dx,
                source_root_dy=source_dy,
                duration=blend,
            )
        else:
            self.transition = None
        return True

    def evaluate(self) -> Tuple[Pose, float, float]:
        """Evaluate the active clip at its current local time."""
        return self.active_clip.evaluate(self.clip_time)

    def update(self, dt: float) -> Tuple[Pose, float, float]:
        """Advance playback and return the blended pose/root offsets."""
        dt = max(0.0, float(dt))
        self.clip_time += dt
        target_pose, target_dx, target_dy = self.evaluate()

        if self.transition is None:
            return target_pose, target_dx, target_dy

        self.transition.elapsed += dt
        progress = min(1.0, self.transition.elapsed / self.transition.duration)

        # Smoothstep avoids a visible velocity discontinuity at the blend edge.
        blend = progress * progress * (3.0 - 2.0 * progress)
        pose = self.transition.source_pose.lerp(target_pose, blend)
        dx = self.transition.source_root_dx + (
            target_dx - self.transition.source_root_dx
        ) * blend
        dy = self.transition.source_root_dy + (
            target_dy - self.transition.source_root_dy
        ) * blend

        if progress >= 1.0:
            self.transition = None

        return pose, dx, dy

    def reset(self) -> None:
        """Restart the current clip from its first frame."""
        self.clip_time = 0.0
        self.transition = None
        self.previous_clip = None
