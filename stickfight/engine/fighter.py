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
    create_uppercut_clip,
    create_sweep_clip,
    create_slash_clip,
    create_sword_guard_clip,
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
    UppercutAction,
    SweepAction,
    SlashAction,
    StaffStrikeAction,
    ComboAction,
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
        weapon: Optional[str] = None,
        headband_color: Optional[Tuple[int, int, int]] = None,
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
        self.weapon = weapon  # "sword", "staff", None
        self.headband_color = headband_color  # Optional ninja ribbon
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
            "uppercut": create_uppercut_clip(),
            "sweep": create_sweep_clip(),
            "slash": create_slash_clip(),
            "sword_guard": create_sword_guard_clip(),
        }

        self.active_clip: AnimationClip = self.clips["idle"]
        self.clip_time: float = 0.0
        self.current_pose: Pose = make_idle_pose()
        self.root_dx: float = 0.0
        self.root_dy: float = 0.0

    def equip(self, weapon_name: Optional[str]):
        """Equips weapon on fighter ('sword', 'staff', None)."""
        self.weapon = weapon_name

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
        elif clip_name == "uppercut":
            fist_pos = joints.get("right_hand")
            if fist_pos:
                return Hitbox(
                    x=fist_pos[0],
                    y=fist_pos[1],
                    radius=32.0 * self.scale,
                    damage=26.0,
                    knockback_x=90.0 * self.facing,
                    knockback_y=-350.0,
                    attacker_name=self.name,
                    attack_type="uppercut",
                )
        elif clip_name == "slash":
            fist_pos = joints.get("right_hand")
            if fist_pos:
                is_staff = self.weapon == "staff"
                blade_y = fist_pos[1] if is_staff else fist_pos[1] - 25.0 * self.scale
                return Hitbox(
                    x=fist_pos[0],
                    y=blade_y,
                    radius=(34.0 if is_staff else 42.0) * self.scale,
                    damage=21.0 if is_staff else 28.0,
                    knockback_x=(135.0 if is_staff else 160.0) * self.facing,
                    attacker_name=self.name,
                    attack_type="staff" if is_staff else "slash",
                )
        elif clip_name == "sweep":
            foot_pos = joints.get("right_foot")
            if foot_pos:
                return Hitbox(
                    x=foot_pos[0],
                    y=foot_pos[1],
                    radius=35.0 * self.scale,
                    damage=16.0,
                    knockback_x=120.0 * self.facing,
                    attacker_name=self.name,
                    attack_type="sweep",
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

    def uppercut(self, target_fighter: Optional[Fighter] = None, duration: float = 0.55, damage: float = 26.0) -> UppercutAction:
        return UppercutAction(self, target_fighter, duration=duration, damage=damage)

    def sweep(self, target_fighter: Optional[Fighter] = None, duration: float = 0.50, damage: float = 16.0) -> SweepAction:
        return SweepAction(self, target_fighter, duration=duration, damage=damage)

    def slash(self, target_fighter: Optional[Fighter] = None, duration: float = 0.48, damage: float = 28.0) -> SlashAction:
        return SlashAction(self, target_fighter, duration=duration, damage=damage)

    def staff_strike(self, target_fighter: Optional[Fighter] = None, duration: float = 0.48, damage: float = 21.0) -> StaffStrikeAction:
        return StaffStrikeAction(self, target_fighter, duration=duration, damage=damage)

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

    def combo(self, *actions_or_name, target: Optional[Fighter] = None) -> ComboAction:
        """
        Creates a sequential combo action.
        Can pass a list of actions: A.combo(A.punch(B), A.kick(B), A.uppercut(B))
        Or preset name: A.combo("triple_strike", target=B)
        """
        if actions_or_name and isinstance(actions_or_name[0], str):
            combo_name = actions_or_name[0]
            tgt = target or (actions_or_name[1] if len(actions_or_name) > 1 else None)
            if combo_name == "ninja_rush":
                actions = [
                    self.slash(tgt, duration=0.35, damage=18.0),
                    self.slash(tgt, duration=0.35, damage=20.0),
                    self.uppercut(tgt, duration=0.45, damage=28.0),
                ]
            elif combo_name == "staff_combo":
                actions = [
                    self.staff_strike(tgt, duration=0.32, damage=15.0),
                    self.staff_strike(tgt, duration=0.32, damage=17.0),
                    self.sweep(tgt, duration=0.42, damage=22.0),
                ]
            elif combo_name == "boxing_flurry":
                actions = [
                    self.punch(tgt, duration=0.28, damage=12.0),
                    self.punch(tgt, duration=0.28, damage=14.0),
                    self.uppercut(tgt, duration=0.45, damage=25.0),
                ]
            else:
                # Default 1-2 combo
                actions = [
                    self.punch(tgt, duration=0.35, damage=14.0),
                    self.kick(tgt, duration=0.45, damage=20.0),
                ]
        else:
            actions = list(actions_or_name)

        return ComboAction(self, actions)
