"""
Fighter representation: stick figure anatomy, health, states, animation playback, and choreography factory.
"""

from __future__ import annotations
from typing import Dict, Tuple, Optional, List
import math

from stickfight.engine.skeleton import (
    Pose,
    make_idle_pose,
)
from stickfight.engine.animation import (
    AnimationClip,
    create_idle_clip,
    create_walk_clip,
    create_punch_clip,
    create_kick_clip,
    create_block_clip,
    create_dodge_clip,
    create_hit_clip,
    create_knockback_clip,
    create_fall_clip,
    create_jump_clip,
)
from stickfight.engine.collision import Hitbox, Hurtbox
from stickfight.scripting.actions import (
    Action,
    WalkToAction,
    RunToAction,
    PunchAction,
    KickAction,
    BlockAction,
    DodgeAction,
    HitAction,
    KnockbackAction,
    FallAction,
    JumpAction,
    CounterAction,
)


class Fighter:
    def __init__(
        self,
        name: str,
        x: float = 400.0,
        y: float = 1500.0,
        facing: int = 1,
        color: Tuple[int, int, int] = (240, 240, 240),
        head_radius: float = 26.0,
        line_width: int = 10,
        scale: float = 1.0,
        health: float = 100.0,
    ):
        self.name = name
        self.x = float(x)
        self.y = float(y)  # Base contact / ground level
        self.facing = 1 if facing >= 0 else -1
        self.color = color
        self.head_radius = head_radius * scale
        self.line_width = line_width
        self.scale = scale
        self.health = health
        self.max_health = health
        self.state = "idle"  # idle, walking, attacking, blocking, dodging, hit, knockback, fallen

        # Animation library
        self.clips: Dict[str, AnimationClip] = {
            "idle": create_idle_clip(),
            "walk": create_walk_clip(),
            "punch": create_punch_clip(),
            "kick": create_kick_clip(),
            "block": create_block_clip(),
            "dodge": create_dodge_clip(),
            "hit": create_hit_clip(),
            "knockback": create_knockback_clip(),
            "fall": create_fall_clip(),
            "jump": create_jump_clip(),
        }

        self.active_clip: AnimationClip = self.clips["idle"]
        self.clip_time: float = 0.0
        self.current_pose: Pose = make_idle_pose()
        self.root_dx: float = 0.0
        self.root_dy: float = 0.0

    def set_animation(self, clip_name: str, loop: Optional[bool] = None):
        """Switches active animation clip and resets time."""
        if clip_name in self.clips:
            self.active_clip = self.clips[clip_name]
            if loop is not None:
                self.active_clip.loop = loop
            self.clip_time = 0.0

    def update_animation(self, dt: float):
        """Advances active animation clip by dt seconds."""
        self.clip_time += dt
        pose, rdx, rdy = self.active_clip.evaluate(self.clip_time)
        self.current_pose = pose
        self.root_dx = rdx
        self.root_dy = rdy

    def face_target(self, target_x: float):
        """Orient facing toward target coordinate."""
        if target_x > self.x:
            self.facing = 1
        elif target_x < self.x:
            self.facing = -1

    def face_fighter(self, other: Fighter):
        """Orient facing toward another fighter."""
        self.face_target(other.x)

    def get_world_joints(self) -> Dict[str, Tuple[float, float]]:
        """Calculates absolute world coordinates for all joints."""
        # Pelvis base height is ~140px above ground
        pelvis_world_x = self.x + self.root_dx * self.facing
        pelvis_world_y = (self.y - 140.0 * self.scale) + self.root_dy
        return self.current_pose.to_world(pelvis_world_x, pelvis_world_y, facing=self.facing, scale=self.scale)

    def get_hurtbox(self) -> Hurtbox:
        """Returns head circle and torso line segment hurtbox."""
        joints = self.get_world_joints()
        head_pos = joints.get("head", (self.x, self.y - 260.0 * self.scale))
        neck_pos = joints.get("neck", (self.x, self.y - 230.0 * self.scale))
        pelvis_pos = joints.get("pelvis", (self.x, self.y - 140.0 * self.scale))

        return Hurtbox(
            head_pos=head_pos,
            head_radius=self.head_radius + 4.0,
            neck_pos=neck_pos,
            pelvis_pos=pelvis_pos,
            torso_radius=22.0 * self.scale,
        )

    def get_hitbox(self) -> Optional[Hitbox]:
        """Calculates the active strike hitbox based on current attack animation."""
        joints = self.get_world_joints()
        clip_name = self.active_clip.name

        if clip_name == "punch":
            # Right hand (leading strike limb)
            fist_pos = joints.get("right_hand")
            if fist_pos:
                return Hitbox(
                    x=fist_pos[0],
                    y=fist_pos[1],
                    radius=28.0 * self.scale,
                    damage=15.0,
                    knockback_x=120.0 * self.facing,
                    attacker_name=self.name,
                    attack_type="punch",
                )
        elif clip_name == "kick":
            # Right foot (leading strike limb)
            foot_pos = joints.get("right_foot")
            if foot_pos:
                return Hitbox(
                    x=foot_pos[0],
                    y=foot_pos[1],
                    radius=32.0 * self.scale,
                    damage=22.0,
                    knockback_x=180.0 * self.facing,
                    attacker_name=self.name,
                    attack_type="kick",
                )
        return None

    # ========================================================================
    # HIGH-LEVEL CHOREOGRAPHY API BUILDERS
    # ========================================================================

    def walk_to(self, target_x: float, duration: Optional[float] = None, speed: float = 240.0) -> WalkToAction:
        return WalkToAction(self, target_x, speed=speed, duration=duration)

    def run_to(self, target_x: float, duration: Optional[float] = None, speed: float = 450.0) -> RunToAction:
        return RunToAction(self, target_x, speed=speed, duration=duration)

    def punch(self, target_fighter: Optional[Fighter] = None, duration: float = 0.45, damage: float = 15.0) -> PunchAction:
        return PunchAction(self, target_fighter, duration=duration, damage=damage)

    def kick(self, target_fighter: Optional[Fighter] = None, duration: float = 0.55, damage: float = 22.0) -> KickAction:
        return KickAction(self, target_fighter, duration=duration, damage=damage)

    def block(self, duration: float = 0.5) -> BlockAction:
        return BlockAction(self, duration=duration)

    def dodge(self, duration: float = 0.5) -> DodgeAction:
        return DodgeAction(self, duration=duration)

    def hit(self, duration: float = 0.4) -> HitAction:
        return HitAction(self, duration=duration)

    def knockback(self, distance: float = 140.0, duration: float = 0.7) -> KnockbackAction:
        return KnockbackAction(self, distance=distance, duration=duration)

    def fall(self, duration: float = 1.2) -> FallAction:
        return FallAction(self, duration=duration)

    def jump(self, height: float = 160.0, duration: float = 0.65) -> JumpAction:
        return JumpAction(self, height=height, duration=duration)

    def counter(self, target_fighter: Fighter, duration: float = 0.7) -> CounterAction:
        return CounterAction(self, target_fighter, duration=duration)
