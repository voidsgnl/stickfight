"""
Animation system for stick fighters.
Provides easing functions, keyframe evaluation, clip sequencing, and procedural combat clips.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Callable
import math

from stickfight.engine.skeleton import (
    Pose,
    make_idle_pose,
    make_walk_poses,
    make_punch_windup,
    make_punch_strike,
    make_kick_windup,
    make_kick_strike,
    make_block_pose,
    make_dodge_pose,
    make_hit_reaction_pose,
    make_knockback_air_pose,
    make_fall_pose,
    make_jump_pose,
    make_uppercut_windup,
    make_uppercut_strike,
    make_sweep_pose,
    make_sword_ready,
    make_sword_slash_windup,
    make_sword_slash_strike,
)


# Easing Functions
def linear(t: float) -> float:
    return max(0.0, min(1.0, t))


def ease_in_quad(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t


def ease_out_quad(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * (2.0 - t)


def ease_in_out_quad(t: float) -> float:
    t = max(0.0, min(1.0, t))
    if t < 0.5:
        return 2.0 * t * t
    return -1.0 + (4.0 - 2.0 * t) * t


def ease_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    t -= 1.0
    return t * t * t + 1.0


def ease_out_back(t: float, overshoot: float = 1.70158) -> float:
    t = max(0.0, min(1.0, t)) - 1.0
    return t * t * ((overshoot + 1.0) * t + overshoot) + 1.0


@dataclass
class Keyframe:
    time: float  # 0.0 to 1.0 normalized progress along clip
    pose: Pose
    root_dx: float = 0.0  # Horizontal root displacement
    root_dy: float = 0.0  # Vertical root displacement
    easing: Callable[[float], float] = ease_in_out_quad


@dataclass
class AnimationClip:
    name: str
    duration: float  # Duration in seconds
    keyframes: List[Keyframe] = field(default_factory=list)
    loop: bool = False

    def evaluate(self, time_in_sec: float) -> Tuple[Pose, float, float]:
        """
        Evaluates the clip at the given timestamp.
        Returns: (Pose, root_dx, root_dy)
        """
        if not self.keyframes:
            return make_idle_pose(), 0.0, 0.0

        if self.duration <= 0.0:
            kf = self.keyframes[0]
            return kf.pose, kf.root_dx, kf.root_dy

        if self.loop:
            t_norm = (time_in_sec % self.duration) / self.duration
        else:
            t_norm = max(0.0, min(1.0, time_in_sec / self.duration))

        # Boundary checks
        if t_norm <= self.keyframes[0].time:
            kf = self.keyframes[0]
            return kf.pose, kf.root_dx, kf.root_dy
        if t_norm >= self.keyframes[-1].time:
            kf = self.keyframes[-1]
            return kf.pose, kf.root_dx, kf.root_dy

        # Find enclosing keyframes
        k1 = self.keyframes[0]
        k2 = self.keyframes[-1]
        for i in range(len(self.keyframes) - 1):
            if self.keyframes[i].time <= t_norm <= self.keyframes[i + 1].time:
                k1 = self.keyframes[i]
                k2 = self.keyframes[i + 1]
                break

        segment_duration = k2.time - k1.time
        if segment_duration <= 1e-6:
            local_t = 0.0
        else:
            local_t = (t_norm - k1.time) / segment_duration

        eased_t = k2.easing(local_t)
        pose = k1.pose.lerp(k2.pose, eased_t)
        dx = k1.root_dx + (k2.root_dx - k1.root_dx) * eased_t
        dy = k1.root_dy + (k2.root_dy - k1.root_dy) * eased_t

        return pose, dx, dy


# ============================================================================
# PROCEDURAL COMBAT CLIPS
# ============================================================================

def create_idle_clip(duration: float = 1.6) -> AnimationClip:
    """Breathing and subtle guard movement."""
    p_base = make_idle_pose()
    p_up = p_base.copy()
    # Subtle bobbing up and down
    p_up.set("head", -8.0, -128.0)
    p_up.set("neck", -6.0, -93.0)
    p_up.set("chest", -4.0, -53.0)

    keyframes = [
        Keyframe(time=0.0, pose=p_base, root_dx=0.0, root_dy=0.0, easing=ease_in_out_quad),
        Keyframe(time=0.5, pose=p_up, root_dx=0.0, root_dy=-4.0, easing=ease_in_out_quad),
        Keyframe(time=1.0, pose=p_base, root_dx=0.0, root_dy=0.0, easing=ease_in_out_quad),
    ]
    return AnimationClip(name="idle", duration=duration, keyframes=keyframes, loop=True)


def create_walk_clip(duration: float = 0.8) -> AnimationClip:
    """Full 4-phase walking cycle."""
    w_poses = make_walk_poses()
    keyframes = [
        Keyframe(time=0.0, pose=w_poses[0], root_dx=0.0, root_dy=0.0, easing=linear),
        Keyframe(time=0.25, pose=w_poses[1], root_dx=0.0, root_dy=0.0, easing=linear),
        Keyframe(time=0.50, pose=w_poses[2], root_dx=0.0, root_dy=0.0, easing=linear),
        Keyframe(time=0.75, pose=w_poses[3], root_dx=0.0, root_dy=0.0, easing=linear),
        Keyframe(time=1.0, pose=w_poses[0], root_dx=0.0, root_dy=0.0, easing=linear),
    ]
    return AnimationClip(name="walk", duration=duration, keyframes=keyframes, loop=True)


def create_punch_clip(duration: float = 0.45) -> AnimationClip:
    """
    Punch choreography:
    0.0 -> 0.20: Windup anticipation (pull back)
    0.20 -> 0.40: Explosive snap forward into strike
    0.40 -> 0.65: Impact extension / follow through
    0.65 -> 1.00: Return smoothly to idle stance
    """
    idle = make_idle_pose()
    windup = make_punch_windup()
    strike = make_punch_strike()

    keyframes = [
        Keyframe(time=0.0, pose=idle, root_dx=0.0, root_dy=0.0, easing=ease_in_quad),
        Keyframe(time=0.20, pose=windup, root_dx=-15.0, root_dy=0.0, easing=ease_out_cubic),
        Keyframe(time=0.40, pose=strike, root_dx=35.0, root_dy=0.0, easing=linear),
        Keyframe(time=0.60, pose=strike, root_dx=30.0, root_dy=0.0, easing=ease_out_quad),
        Keyframe(time=1.0, pose=idle, root_dx=0.0, root_dy=0.0, easing=ease_in_out_quad),
    ]
    return AnimationClip(name="punch", duration=duration, keyframes=keyframes, loop=False)


def create_kick_clip(duration: float = 0.55) -> AnimationClip:
    """
    Kick choreography:
    Chamber knee up, whip leg straight out, quick retract.
    """
    idle = make_idle_pose()
    windup = make_kick_windup()
    strike = make_kick_strike()

    keyframes = [
        Keyframe(time=0.0, pose=idle, root_dx=0.0, root_dy=0.0, easing=ease_in_quad),
        Keyframe(time=0.22, pose=windup, root_dx=-10.0, root_dy=-5.0, easing=ease_out_cubic),
        Keyframe(time=0.45, pose=strike, root_dx=25.0, root_dy=-8.0, easing=linear),
        Keyframe(time=0.65, pose=strike, root_dx=20.0, root_dy=-5.0, easing=ease_out_quad),
        Keyframe(time=1.0, pose=idle, root_dx=0.0, root_dy=0.0, easing=ease_in_out_quad),
    ]
    return AnimationClip(name="kick", duration=duration, keyframes=keyframes, loop=False)


def create_block_clip(duration: float = 0.5) -> AnimationClip:
    """Raise guard, brace for impact, lower guard."""
    idle = make_idle_pose()
    block = make_block_pose()

    keyframes = [
        Keyframe(time=0.0, pose=idle, root_dx=0.0, root_dy=0.0, easing=ease_out_quad),
        Keyframe(time=0.15, pose=block, root_dx=-5.0, root_dy=0.0, easing=linear),
        Keyframe(time=0.80, pose=block, root_dx=-5.0, root_dy=0.0, easing=ease_in_out_quad),
        Keyframe(time=1.0, pose=idle, root_dx=0.0, root_dy=0.0, easing=ease_in_out_quad),
    ]
    return AnimationClip(name="block", duration=duration, keyframes=keyframes, loop=False)


def create_dodge_clip(duration: float = 0.5) -> AnimationClip:
    """Lean back dodge, hold briefly, return to guard."""
    idle = make_idle_pose()
    dodge = make_dodge_pose()

    keyframes = [
        Keyframe(time=0.0, pose=idle, root_dx=0.0, root_dy=0.0, easing=ease_out_cubic),
        Keyframe(time=0.25, pose=dodge, root_dx=-40.0, root_dy=10.0, easing=linear),
        Keyframe(time=0.65, pose=dodge, root_dx=-35.0, root_dy=10.0, easing=ease_in_out_quad),
        Keyframe(time=1.0, pose=idle, root_dx=0.0, root_dy=0.0, easing=ease_in_out_quad),
    ]
    return AnimationClip(name="dodge", duration=duration, keyframes=keyframes, loop=False)


def create_hit_clip(duration: float = 0.4) -> AnimationClip:
    """Violent head/torso snap back on hit, recovery."""
    idle = make_idle_pose()
    hit = make_hit_reaction_pose()

    keyframes = [
        Keyframe(time=0.0, pose=idle, root_dx=0.0, root_dy=0.0, easing=linear),
        Keyframe(time=0.10, pose=hit, root_dx=-25.0, root_dy=-5.0, easing=ease_out_quad),
        Keyframe(time=0.45, pose=hit, root_dx=-20.0, root_dy=0.0, easing=ease_in_out_quad),
        Keyframe(time=1.0, pose=idle, root_dx=0.0, root_dy=0.0, easing=ease_in_out_quad),
    ]
    return AnimationClip(name="hit", duration=duration, keyframes=keyframes, loop=False)


def create_knockback_clip(duration: float = 0.7, knockback_dist: float = 120.0) -> AnimationClip:
    """Blown backwards through air, skids on feet."""
    idle = make_idle_pose()
    air = make_knockback_air_pose()
    recoil = make_hit_reaction_pose()

    keyframes = [
        Keyframe(time=0.0, pose=idle, root_dx=0.0, root_dy=0.0, easing=linear),
        Keyframe(time=0.25, pose=air, root_dx=-knockback_dist * 0.6, root_dy=-35.0, easing=ease_out_quad),
        Keyframe(time=0.60, pose=recoil, root_dx=-knockback_dist * 0.9, root_dy=0.0, easing=ease_out_quad),
        Keyframe(time=1.0, pose=idle, root_dx=-knockback_dist, root_dy=0.0, easing=ease_in_out_quad),
    ]
    return AnimationClip(name="knockback", duration=duration, keyframes=keyframes, loop=False)


def create_fall_clip(duration: float = 0.9) -> AnimationClip:
    """Knocked off feet, hits ground, stays down."""
    recoil = make_hit_reaction_pose()
    air = make_knockback_air_pose()
    ground = make_fall_pose()

    keyframes = [
        Keyframe(time=0.0, pose=recoil, root_dx=0.0, root_dy=0.0, easing=linear),
        Keyframe(time=0.25, pose=air, root_dx=-50.0, root_dy=-40.0, easing=ease_in_quad),
        Keyframe(time=0.55, pose=ground, root_dx=-90.0, root_dy=0.0, easing=ease_out_back),
        Keyframe(time=1.0, pose=ground, root_dx=-90.0, root_dy=0.0, easing=linear),
    ]
    return AnimationClip(name="fall", duration=duration, keyframes=keyframes, loop=False)


def create_jump_clip(duration: float = 0.65, height: float = 160.0) -> AnimationClip:
    """Crouch -> leap into air -> descend -> landing crouch -> recover."""
    idle = make_idle_pose()
    crouch = idle.copy()
    crouch.set("pelvis", 0.0, 25.0)
    peak = make_jump_pose()

    keyframes = [
        Keyframe(time=0.0, pose=idle, root_dx=0.0, root_dy=0.0, easing=ease_in_quad),
        Keyframe(time=0.15, pose=crouch, root_dx=0.0, root_dy=20.0, easing=ease_out_quad),
        Keyframe(time=0.50, pose=peak, root_dx=0.0, root_dy=-height, easing=ease_in_out_quad),
        Keyframe(time=0.85, pose=crouch, root_dx=0.0, root_dy=15.0, easing=ease_out_quad),
        Keyframe(time=1.0, pose=idle, root_dx=0.0, root_dy=0.0, easing=ease_in_out_quad),
    ]
    return AnimationClip(name="jump", duration=duration, keyframes=keyframes, loop=False)


def create_uppercut_clip(duration: float = 0.55) -> AnimationClip:
    """Dip down into coiled crouch, then launch vertically with skyward fist."""
    idle = make_idle_pose()
    windup = make_uppercut_windup()
    strike = make_uppercut_strike()

    keyframes = [
        Keyframe(time=0.0, pose=idle, root_dx=0.0, root_dy=0.0, easing=ease_in_quad),
        Keyframe(time=0.20, pose=windup, root_dx=10.0, root_dy=25.0, easing=ease_out_cubic),
        Keyframe(time=0.45, pose=strike, root_dx=25.0, root_dy=-50.0, easing=linear),
        Keyframe(time=0.70, pose=strike, root_dx=20.0, root_dy=-25.0, easing=ease_out_quad),
        Keyframe(time=1.0, pose=idle, root_dx=0.0, root_dy=0.0, easing=ease_in_out_quad),
    ]
    return AnimationClip(name="uppercut", duration=duration, keyframes=keyframes, loop=False)


def create_sweep_clip(duration: float = 0.50) -> AnimationClip:
    """Drop low to the ground and sweep lead leg in full circle."""
    idle = make_idle_pose()
    sweep = make_sweep_pose()

    keyframes = [
        Keyframe(time=0.0, pose=idle, root_dx=0.0, root_dy=0.0, easing=ease_in_quad),
        Keyframe(time=0.25, pose=sweep, root_dx=20.0, root_dy=40.0, easing=linear),
        Keyframe(time=0.65, pose=sweep, root_dx=40.0, root_dy=40.0, easing=ease_out_quad),
        Keyframe(time=1.0, pose=idle, root_dx=0.0, root_dy=0.0, easing=ease_in_out_quad),
    ]
    return AnimationClip(name="sweep", duration=duration, keyframes=keyframes, loop=False)


def create_slash_clip(duration: float = 0.48) -> AnimationClip:
    """Fast diagonal katana/sword slash with broad weapon arc."""
    ready = make_sword_ready()
    windup = make_sword_slash_windup()
    strike = make_sword_slash_strike()

    keyframes = [
        Keyframe(time=0.0, pose=ready, root_dx=0.0, root_dy=0.0, easing=ease_in_quad),
        Keyframe(time=0.22, pose=windup, root_dx=-20.0, root_dy=-10.0, easing=ease_out_cubic),
        Keyframe(time=0.42, pose=strike, root_dx=45.0, root_dy=10.0, easing=linear),
        Keyframe(time=0.68, pose=strike, root_dx=35.0, root_dy=5.0, easing=ease_out_quad),
        Keyframe(time=1.0, pose=ready, root_dx=0.0, root_dy=0.0, easing=ease_in_out_quad),
    ]
    return AnimationClip(name="slash", duration=duration, keyframes=keyframes, loop=False)


def create_sword_guard_clip(duration: float = 0.50) -> AnimationClip:
    """Sword parry and guard stance."""
    ready = make_sword_ready()
    parry = make_block_pose()

    keyframes = [
        Keyframe(time=0.0, pose=ready, root_dx=0.0, root_dy=0.0, easing=ease_out_quad),
        Keyframe(time=0.15, pose=parry, root_dx=-5.0, root_dy=0.0, easing=linear),
        Keyframe(time=0.80, pose=parry, root_dx=-5.0, root_dy=0.0, easing=ease_in_out_quad),
        Keyframe(time=1.0, pose=ready, root_dx=0.0, root_dy=0.0, easing=ease_in_out_quad),
    ]
    return AnimationClip(name="sword_guard", duration=duration, keyframes=keyframes, loop=False)
