"""
Fighter representation: stick figure anatomy, health, states, animation playback, and choreography factory.
"""

from __future__ import annotations
from typing import Dict, Tuple, Optional, List
import math

from stickfight.engine.ik import apply_two_bone_ik
from stickfight.engine.skeleton import (
    Pose,
    make_idle_pose,
    BodyProportions,
    apply_proportions,
    PROPORTIONS_DEFAULT,
    PROPORTIONS_NINJA,
    PROPORTIONS_SAMURAI,
    PROPORTIONS_BRAWLER,
    PROPORTIONS_MONK,
    PROPORTIONS_CYBORG,
)
from stickfight.engine.animation_player import AnimationPlayer
from stickfight.engine.animation_state import AnimationStateMachine
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
    create_jab_clip,
    create_cross_clip,
    create_hook_clip,
    create_low_kick_clip,
    create_check_kick_clip,
    create_slip_clip,
    create_bob_weave_clip,
    create_clinch_knee_clip,
    create_takedown_clip,
    create_ground_pound_clip,
    create_stagger_clip,
    create_grounded_guard_clip,
)
from stickfight.engine.collision import Hitbox, Hurtbox
from stickfight.engine.combat_timing import ATTACK_TIMINGS, AttackTiming
from stickfight.engine.combat_events import CombatEventBus, CombatImpactEvent
from stickfight.engine.physics import PhysicsBody
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
    JabAction,
    CrossAction,
    HookAction,
    LowKickAction,
    CheckKickAction,
    SlipAction,
    BobWeaveAction,
    ClinchKneeAction,
    TakedownAction,
    GroundPoundAction,
    StaggerAction,
)


DESIGN_PRESETS = {
    "classic": {
        "color": (240, 240, 240),
        "line_width": 10,
        "scale": 1.0,
        "render_style": "segmented",
    },
    "ninja": {
        "color": (45, 48, 56),
        "line_width": 10,
        "scale": 1.0,
        "render_style": "silhouette",
        "headband_color": (235, 45, 45),
        "proportions": PROPORTIONS_NINJA,
    },
    "samurai": {
        "color": (230, 235, 245),
        "line_width": 10,
        "scale": 1.0,
        "render_style": "segmented",
        "headband_color": (235, 190, 45),
        "proportions": PROPORTIONS_SAMURAI,
    },
    "brawler": {
        "color": (235, 60, 60),
        "line_width": 12,
        "scale": 1.1,
        "render_style": "segmented",
        "proportions": PROPORTIONS_BRAWLER,
    },
    "monk": {
        "color": (245, 140, 35),
        "line_width": 10,
        "scale": 1.0,
        "render_style": "segmented",
        "headband_color": (245, 200, 70),
        "proportions": PROPORTIONS_MONK,
    },
    "cyborg": {
        "color": (50, 220, 255),
        "line_width": 10,
        "scale": 1.0,
        "render_style": "tech",
        "proportions": PROPORTIONS_CYBORG,
    },
}


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
        render_style: str = "segmented",
        proportions: Optional[BodyProportions] = None,
        style: str = "arcade",
        design: Optional[str] = None,
    ):
        # Character design preset ("classic", "ninja", "samurai"/"warrior",
        # "brawler", "monk", "cyber"/"cyborg"). Applied first so any explicit
        # keyword arguments below override the preset's look.
        self.design = (design or "classic").lower()
        if self.design in ("cyber", "cyborg"):
            self.design = "cyborg"
        elif self.design == "warrior":
            self.design = "samurai"
        preset = DESIGN_PRESETS.get(self.design)
        if preset is not None:
            color = preset.get("color", color)
            line_width = preset.get("line_width", line_width)
            scale = preset.get("scale", scale)
            render_style = preset.get("render_style", render_style)
            headband_color = preset.get("headband_color", headband_color)
            if proportions is None and "proportions" in preset:
                proportions = preset["proportions"]
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
        self.render_style = render_style  # segmented, silhouette, classic, tech, ink_fight
        # Combat choreography style: "arcade" (default weapon/flash fights)
        # or "realistic" (boxing / Muay Thai / MMA mechanics).
        self.style = style
        # Per-archetype rig scaling (stance width, limb length, etc.) applied
        # on top of every shared animation clip. Defaults to the canonical
        # proportions used by the original pose library.
        self.proportions = proportions or PROPORTIONS_DEFAULT
        self.state = "idle"  # idle, walking, attacking, blocking, dodging, hit, knockback, fallen

        # Physics body. Horizontal scripted movement may still set x directly,
        # but vertical motion and combat impulses are simulated here.
        self.physics = PhysicsBody(
            x=self.x,
            y=self.y,
            ground_y=self.y,
            gravity=1800.0,
        )

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
            # Realistic martial arts library (boxing / Muay Thai / MMA)
            "jab": create_jab_clip(),
            "cross": create_cross_clip(),
            "hook": create_hook_clip(),
            "low_kick": create_low_kick_clip(),
            "check_kick": create_check_kick_clip(),
            "slip": create_slip_clip(),
            "bob_weave": create_bob_weave_clip(),
            "clinch_knee": create_clinch_knee_clip(),
            "takedown": create_takedown_clip(),
            "ground_pound": create_ground_pound_clip(),
            "stagger": create_stagger_clip(),
            "grounded_guard": create_grounded_guard_clip(),
        }

        # Runtime playback is separated from clip definitions so animation
        # timing/blending can evolve without coupling it to Fighter physics.
        self.animation_player = AnimationPlayer(self.clips, initial="idle")
        self.animation_state = AnimationStateMachine(initial="idle")
        self.active_clip: AnimationClip = self.animation_player.active_clip
        self.clip_time: float = self.animation_player.clip_time
        self.current_pose: Pose = apply_proportions(make_idle_pose(), self.proportions)
        self.root_dx: float = 0.0
        self.root_dy: float = 0.0
        self.combat_events = CombatEventBus()
        self._impact_event_key: Optional[tuple] = None
        self._impact_consumed_key: Optional[tuple] = None
        self._previous_clip_name: str = self.active_clip.name
        self._previous_clip_time: float = self.clip_time
        self.ik_target: Optional[Tuple[str, Tuple[float, float], float]] = None
        self.weapon_ik_targets: Dict[str, Tuple[Tuple[float, float], float]] = {}
        self._grapple_attacker: Optional["Fighter"] = None
        self._grapple_mode: Optional[str] = None
        self._grapple_target: Optional["Fighter"] = None
        self._ground_control_target: Optional["Fighter"] = None
        self._ground_control_mode: Optional[str] = None
        self._ground_control = None
        self._ground_control_blend: float = 0.0

    def sync_from_physics(self):
        """Copies the simulated world position into the fighter."""
        self.x = self.physics.x
        self.y = self.physics.y

    def sync_to_physics(self):
        """Keeps the physics body aligned after scripted position changes."""
        self.physics.x = self.x
        self.physics.y = self.y

    def apply_impulse(self, ix: float, iy: float = 0.0):
        """Applies a combat/jump impulse to the fighter's physics body."""
        self.sync_to_physics()
        self.physics.apply_impulse(ix, iy)

    @property
    def is_airborne(self) -> bool:
        """Whether the physics body is currently off the ground."""
        return not self.physics.is_grounded

    def update_physics(self, dt: float):
        """Advance physics and synchronize the fighter's world position."""
        self.physics.update(dt)
        self.sync_from_physics()

    def reset_physics(self):
        """Restores the body to the fighter's spawn position and grounded state."""
        self.physics.x = self.x
        self.physics.y = self.y
        self.physics.vx = 0.0
        self.physics.vy = 0.0
        self.physics.ax = 0.0
        self.physics.ay = 0.0
        self.physics.is_grounded = True

    def equip(self, weapon_name: Optional[str]):
        """Equips weapon on fighter ('sword', 'staff', None)."""
        self.weapon = weapon_name

    def set_animation(
        self,
        clip_name: str,
        loop: Optional[bool] = None,
        blend: float = 0.0,
    ):
        """Switch animation with an optional cross-fade in seconds."""
        if self.animation_player.play(clip_name, loop=loop, blend=blend):
            self.active_clip = self.animation_player.active_clip
            self.clip_time = self.animation_player.clip_time
            self._previous_clip_name = self.active_clip.name
            self._previous_clip_time = self.clip_time
            self._impact_event_key = None
            self._impact_consumed_key = None

    def set_state(
        self,
        state_name: str,
        blend: Optional[float] = None,
        clip_name: Optional[str] = None,
    ) -> bool:
        """Enter a validated animation state, optionally selecting its clip."""
        if not self.animation_state.transition_to(state_name):
            return False
        state = self.animation_state.states[state_name]
        clip = clip_name or state.clip
        transition_blend = state.blend if blend is None else blend
        if clip not in self.clips:
            return False
        self.set_animation(clip, loop=state.loop, blend=transition_blend)
        return True

    def update_animation(self, dt: float):
        """Advance animation playback and apply the current rig proportions."""
        self.animation_state.update(dt)
        previous_clip = self.active_clip
        previous_time = self.clip_time
        pose, rdx, rdy = self.animation_player.update(dt)
        self._previous_clip_name = previous_clip.name
        self._previous_clip_time = previous_time
        self.active_clip = self.animation_player.active_clip
        self.clip_time = self.animation_player.clip_time
        # Apply this fighter's archetype rig scaling on top of the shared
        # canonical pose so every clip renders on the correct body type.
        self.current_pose = apply_proportions(pose, self.proportions)
        self.root_dx = rdx
        self.root_dy = rdy
        self._apply_grapple_deformation()
        self._apply_ground_control_deformation()
        self._apply_ground_foot_ik()
        self._apply_ik_target()
        self._apply_weapon_ik()

    def set_ik_target(self, joint: str, target_world: Tuple[float, float], bend_sign: float = 1.0):
        """Set a world-space hand/foot target for the current pose."""
        self.ik_target = (joint, target_world, bend_sign)
        self.weapon_ik_targets.clear()

    def clear_ik_target(self):
        self.ik_target = None
        self.weapon_ik_targets.clear()
        self.clear_grapple_reaction()

    def _apply_weapon_ik(self):
        """Keep secondary weapon grips attached to the primary hand target."""
        if not self.weapon_ik_targets:
            return
        for joint, (target_world, bend_sign) in self.weapon_ik_targets.items():
            pelvis_world_x = self.x + self.root_dx * self.facing
            pelvis_world_y = self.y - 140.0 * self.scale + self.root_dy
            tx = (target_world[0] - pelvis_world_x) / max(1e-6, self.scale)
            ty = (target_world[1] - pelvis_world_y) / max(1e-6, self.scale)
            if self.facing < 0:
                tx = -tx
            if joint == "left_hand":
                self.current_pose = apply_two_bone_ik(
                    self.current_pose, "left_shoulder", "left_elbow", "left_hand",
                    (tx, ty), bend_sign,
                )
            elif joint == "right_hand":
                self.current_pose = apply_two_bone_ik(
                    self.current_pose, "right_shoulder", "right_elbow", "right_hand",
                    (tx, ty), bend_sign,
                )

    def set_grapple_targets(self, other: "Fighter", mode: str = "takedown"):
        """Create world-space contact targets for close-range grappling."""
        if other is None:
            return
        target = other.get_hurtbox()
        self.weapon_ik_targets.clear()
        self._grapple_target = other
        self._grapple_mode = mode
        bend = 1.0 if self.facing >= 0 else -1.0
        if mode == "clinch":
            chest = target.pelvis_pos
            self.ik_target = ("right_hand", (chest[0] - self.facing * 12.0, chest[1] - 28.0), bend)
            self.weapon_ik_targets["left_hand"] = ((chest[0] - self.facing * 12.0, chest[1] + 18.0), bend)
        else:
            hips = target.pelvis_pos
            if mode == "ground_pound":
                grip = (hips[0] - self.facing * 12.0, hips[1] - 8.0)
                self.ik_target = ("right_hand", grip, bend)
                self.weapon_ik_targets["left_hand"] = ((hips[0] + self.facing * 10.0, hips[1] + 18.0), bend)
            else:
                grip = (hips[0] - self.facing * 18.0, hips[1] + 38.0)
                self.ik_target = ("right_hand", grip, bend)
                self.weapon_ik_targets["left_hand"] = ((grip[0], grip[1] + 28.0), bend)

    def _apply_ground_control_deformation(self):
        """Procedurally maintain top-control positioning over a grounded target."""
        target = self._ground_control_target
        if target is None or target.state not in {"grounded", "fallen"}:
            return
        self._ground_control_blend = min(1.0, self._ground_control_blend + 0.12)
        blend = self._ground_control_blend * self._ground_control_blend * (3.0 - 2.0 * self._ground_control_blend)
        pelvis = target.get_hurtbox().pelvis_pos
        direction = 1.0 if target.x >= self.x else -1.0
        # Keep the attacker close to the defender while preserving a stable base.
        self.x += max(-2.0, min(2.0, (target.x - self.x) * 0.04))
        self.sync_to_physics()
        if self._ground_control_mode == "guard":
            pelvis_drop, chest_lean, head_drop = 16.0, 14.0, 62.0
        else:
            pelvis_drop, chest_lean, head_drop = 24.0, 22.0, 76.0
        self.current_pose.set("pelvis", (direction * 12.0 * blend, pelvis_drop * blend))
        self.current_pose.set("chest", (direction * chest_lean * blend, -20.0 * blend))
        self.current_pose.set("neck", (direction * 30.0 * blend, -48.0 * blend))
        self.current_pose.set("head", (direction * 34.0 * blend, -head_drop * blend))
        for side, offset in (("left", -1.0), ("right", 1.0)):
            hip = self.current_pose.get(side + "_hip")
            knee = self.current_pose.get(side + "_knee")
            self.current_pose.set(side + "_hip", (hip[0] + direction * 10.0 * blend * offset, hip[1] + 18.0 * blend))
            self.current_pose.set(side + "_knee", (knee[0] + direction * 24.0 * blend * offset, knee[1] + 30.0 * blend))
        grip = (pelvis[0] - direction * 8.0, pelvis[1] - 12.0)
        bend = 1.0 if self.facing >= 0 else -1.0
        self.ik_target = ("right_hand", grip, bend)
        self.weapon_ik_targets["left_hand"] = ((pelvis[0] + direction * 14.0, pelvis[1] + 12.0), bend)

    def _apply_grapple_deformation(self):
        """Deform the defender around a live grappling interaction."""
        if self._grapple_attacker is None or self._grapple_mode is None:
            return
        duration = max(1e-6, self.active_clip.duration)
        progress = max(0.0, min(1.0, self.clip_time / duration))
        blend = progress * progress * (3.0 - 2.0 * progress)
        attacker = self._grapple_attacker
        target = self._grapple_target
        direction = 1.0 if attacker.x >= self.x else -1.0
        if self._grapple_mode in {"bottom_guard", "bottom_mount"}:
            self.current_pose.set("pelvis", (0.0, 18.0))
            self.current_pose.set("chest", (direction * 10.0, -32.0))
            self.current_pose.set("neck", (direction * 14.0, -58.0))
            self.current_pose.set("head", (direction * 18.0, -82.0))
            return
        if target is not None and self._grapple_mode == "takedown":
            target_pelvis = target.get_hurtbox().pelvis_pos
            distance = target.x - self.x
            close = max(0.0, min(1.0, 1.0 - abs(distance) / 180.0))
            drive = close * blend
            crouch = 18.0 * drive
            self.current_pose.set("pelvis", (self.current_pose.get("pelvis")[0], crouch))
            self.current_pose.set("chest", (self.current_pose.get("chest")[0] + direction * 8.0 * drive, -50.0 + crouch * 0.45))
            for side, offset in (("left", -1.0), ("right", 1.0)):
                knee = self.current_pose.get(side + "_knee")
                self.current_pose.set(side + "_knee", (knee[0] + direction * 7.0 * drive * offset, knee[1] + 18.0 * drive))
            grip = (target_pelvis[0] - self.facing * 18.0, target_pelvis[1] + 38.0)
            bend = 1.0 if self.facing >= 0 else -1.0
            self.ik_target = ("right_hand", grip, bend)
            self.weapon_ik_targets["left_hand"] = ((grip[0], grip[1] + 28.0), bend)
            return
        if self._grapple_mode == "takedown":
            lean = 24.0 * blend * direction
            drop = 24.0 * blend
            ground_phase = max(0.0, min(1.0, (progress - 0.58) / 0.42))
            ground_ease = ground_phase * ground_phase * (3.0 - 2.0 * ground_phase)
            settle = 68.0 * ground_ease

            self.current_pose.set("pelvis", (lean * 0.35, drop + settle))
            self.current_pose.set("chest", (lean + direction * 12.0 * ground_ease, -50.0 + drop * 0.55 + settle * 0.70))
            self.current_pose.set("neck", (lean * 1.25 + direction * 16.0 * ground_ease, -84.0 + drop * 0.65 + settle * 0.78))
            self.current_pose.set("head", (lean * 1.55 + direction * 22.0 * ground_ease, -112.0 + drop * 0.75 + settle * 0.82))

            for side, offset in (("left", -1.0), ("right", 1.0)):
                hip = self.current_pose.get(f"{side}_hip")
                knee = self.current_pose.get(f"{side}_knee")
                foot = self.current_pose.get(f"{side}_foot")
                self.current_pose.set(
                    f"{side}_hip",
                    (hip[0] + lean * 0.35, hip[1] + drop + settle * 0.85),
                )
                self.current_pose.set(
                    f"{side}_knee",
                    (knee[0] + lean * 0.65 + direction * 8.0 * offset * blend,
                     knee[1] + drop * 0.35 + settle * 0.35),
                )
                self.current_pose.set(
                    f"{side}_foot",
                    (foot[0] + direction * 14.0 * offset * ground_ease, foot[1]),
                )

    def enter_ground_control(self, defender: "Fighter", mode: str = "mount") -> bool:
        """Place the attacker into persistent top control over a grounded defender."""
        if defender is None:
            return False
        self._ground_control_target = defender
        if mode not in {"mount", "guard"}:
            raise ValueError("ground control mode must be 'mount' or 'guard'")
        self._ground_control_mode = mode
        self._ground_control_blend = 0.0
        defender._grapple_attacker = self
        defender._grapple_mode = "bottom_guard" if mode == "mount" else "bottom_mount"
        self.state = "grounded"
        self.physics.vx = 0.0
        self.physics.vy = 0.0
        self.physics.is_grounded = True
        return self.set_state("grounded", blend=0.10)

    def clear_ground_control(self) -> None:
        self._ground_control = None
        self._ground_control_target = None
        self._ground_control_mode = None
        self._ground_control_blend = 0.0

    def enter_grounded_control(self) -> bool:
        """Enter persistent grounded combat after a takedown settles."""
        self.state = "grounded"
        self.physics.vx = 0.0
        self.physics.vy = 0.0
        self.physics.is_grounded = True
        return self.set_state("grounded", blend=0.10)

    def apply_grapple_reaction(self, attacker: "Fighter", mode: str = "takedown"):
        """Orient and pose a defender in response to a close-range grapple."""
        dx = attacker.x - self.x
        self.facing = 1 if dx >= 0 else -1
        self._grapple_attacker = attacker
        self._grapple_mode = mode
        self.set_state("fallen" if mode == "takedown" else "hit")

    def clear_grapple_reaction(self):
        """Stop procedural grappling deformation."""
        self._grapple_attacker = None
        self._grapple_mode = None
        self._grapple_target = None

        """Orient and pose a defender in response to a close-range grapple."""
        dx = attacker.x - self.x
        self.facing = 1 if dx >= 0 else -1
        self.set_animation("fall" if mode == "takedown" else "hit", loop=False)

    def aim_attack_at(self, other: "Fighter"):
        """Aim the active striking hand at the opponent's head using IK."""
        hurtbox = other.get_hurtbox()
        target = hurtbox.head_pos
        joint = "left_hand" if self.active_clip.name in {"jab", "hook"} else "right_hand"
        bend = 1.0 if self.facing >= 0 else -1.0
        self.set_ik_target(joint, target, bend_sign=bend)
        if self.weapon in {"sword", "staff"}:
            offset = 34.0 if self.weapon == "sword" else 55.0
            secondary = (
                target[0] - self.facing * offset,
                target[1] + (12.0 if self.weapon == "sword" else 22.0),
            )
            secondary_joint = "left_hand" if joint == "right_hand" else "right_hand"
            self.weapon_ik_targets[secondary_joint] = (secondary, bend)

    def _apply_ground_foot_ik(self):
        """Keep grounded feet planted on the physical ground plane."""
        if not self.physics.is_grounded:
            return
        pelvis_world_x = self.x + self.root_dx * self.facing
        pelvis_world_y = self.y - 140.0 * self.scale + self.root_dy
        ground_local_y = (self.y - pelvis_world_y) / max(1e-6, self.scale)
        for hip, knee, foot in (
            ("left_hip", "left_knee", "left_foot"),
            ("right_hip", "right_knee", "right_foot"),
        ):
            authored = self.current_pose.get(foot)
            target = (authored[0], ground_local_y)
            self.current_pose = apply_two_bone_ik(
                self.current_pose, hip, knee, foot, target, bend_sign=1.0
            )

    def _apply_ik_target(self):
        if self.ik_target is None:
            return
        joint, target_world, bend_sign = self.ik_target
        pelvis_world_x = self.x + self.root_dx * self.facing
        pelvis_world_y = self.y - 140.0 * self.scale + self.root_dy
        tx = (target_world[0] - pelvis_world_x) / max(1e-6, self.scale)
        ty = (target_world[1] - pelvis_world_y) / max(1e-6, self.scale)
        if self.facing < 0:
            tx = -tx
        if joint == "right_hand":
            self.current_pose = apply_two_bone_ik(
                self.current_pose, "right_shoulder", "right_elbow", "right_hand", (tx, ty), bend_sign
            )
        elif joint == "left_hand":
            self.current_pose = apply_two_bone_ik(
                self.current_pose, "left_shoulder", "left_elbow", "left_hand", (tx, ty), bend_sign
            )

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

        hip_pos = joints.get("pelvis", pelvis_pos)
        knee_pos = joints.get("left_knee", (self.x, self.y - 75.0 * self.scale))
        foot_pos = joints.get("left_foot", (self.x, self.y))

        return Hurtbox(
            head_pos=head_pos,
            head_radius=self.head_radius + 4.0,
            neck_pos=neck_pos,
            pelvis_pos=pelvis_pos,
            torso_radius=22.0 * self.scale,
            hip_pos=hip_pos,
            knee_pos=knee_pos,
            foot_pos=foot_pos,
        )

    @property
    def attack_timing(self) -> Optional[AttackTiming]:
        """Timing metadata for the currently playing attack clip."""
        return ATTACK_TIMINGS.get(self.active_clip.name)

    @property
    def attack_phase(self) -> Optional[str]:
        """Current combat phase: anticipation/action/contact/follow_through/recovery."""
        timing = self.attack_timing
        if timing is None:
            return None
        return timing.phase(self.clip_time, self.active_clip.duration)

    def is_attack_active(self) -> bool:
        """Whether the current animation is inside its damaging contact window."""
        timing = self.attack_timing
        return timing is not None and timing.is_active(self.clip_time, self.active_clip.duration)

    def is_attack_impact(self, tolerance: float = 0.03) -> bool:
        """Whether playback is at the authored impact marker."""
        timing = self.attack_timing
        return timing is not None and timing.is_impact_frame(self.clip_time, self.active_clip.duration, tolerance=tolerance)

    def consume_attack_impact(self) -> bool:
        """Consume the authored impact once when playback crosses its marker."""
        timing = self.attack_timing
        if timing is None or self._previous_clip_name != self.active_clip.name:
            return False
        crossed = timing.crossed_impact(
            self._previous_clip_time,
            self.clip_time,
            self.active_clip.duration,
        )
        if not crossed:
            return False
        key = (self.active_clip.name, timing.impact)
        if self._impact_consumed_key == key:
            return False
        self._impact_consumed_key = key
        return True

    def emit_impact(
        self,
        defender: Optional[Fighter] = None,
        damage: float = 0.0,
        blocked: bool = False,
    ) -> bool:
        """Emit the current animation's impact marker at most once per clip."""
        if not self.consume_attack_impact():
            return False
        key = self._impact_event_key
        joints = self.get_world_joints()
        hand = joints.get("right_hand", (self.x, self.y - 120.0))
        event = CombatImpactEvent(
            attacker=self,
            defender=defender,
            attack_type=self.active_clip.name,
            x=hand[0],
            y=hand[1],
            damage=damage,
            blocked=blocked,
        )
        self.combat_events.emit_impact(event)
        self._impact_event_key = key
        return True

    def get_hitbox(self) -> Optional[Hitbox]:
        """Calculates a strike hitbox only during the active contact window."""
        timing = self.attack_timing
        if timing is None or not timing.is_active(self.clip_time, self.active_clip.duration):
            return None

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
        elif clip_name in ("jab", "cross", "hook"):
            fist_pos = joints.get("right_hand")
            if fist_pos:
                damage = {"jab": 12.0, "cross": 18.0, "hook": 24.0}[clip_name]
                return Hitbox(
                    x=fist_pos[0],
                    y=fist_pos[1],
                    radius=27.0 * self.scale,
                    damage=damage,
                    knockback_x=(105.0 if clip_name == "jab" else 145.0) * self.facing,
                    attacker_name=self.name,
                    attack_type=clip_name,
                )
        elif clip_name == "low_kick":
            foot_pos = joints.get("right_foot")
            if foot_pos:
                return Hitbox(
                    x=foot_pos[0],
                    y=foot_pos[1],
                    radius=30.0 * self.scale,
                    damage=16.0,
                    knockback_x=135.0 * self.facing,
                    attacker_name=self.name,
                    attack_type="low_kick",
                )
        elif clip_name == "clinch_knee":
            knee_pos = joints.get("right_knee")
            if knee_pos:
                return Hitbox(
                    x=knee_pos[0],
                    y=knee_pos[1],
                    radius=30.0 * self.scale,
                    damage=25.0,
                    knockback_x=90.0 * self.facing,
                    attacker_name=self.name,
                    attack_type="clinch_knee",
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

    # --- Realistic martial arts builders (Boxing / Muay Thai / MMA) ---

    def jab(self, target_fighter: Optional[Fighter] = None, duration: float = 0.35, damage: float = 12.0) -> JabAction:
        return JabAction(self, target_fighter, duration=duration, damage=damage)

    def cross(self, target_fighter: Optional[Fighter] = None, duration: float = 0.40, damage: float = 18.0) -> CrossAction:
        return CrossAction(self, target_fighter, duration=duration, damage=damage)

    def hook(self, target_fighter: Optional[Fighter] = None, duration: float = 0.42, damage: float = 24.0) -> HookAction:
        return HookAction(self, target_fighter, duration=duration, damage=damage)

    def low_kick(self, target_fighter: Optional[Fighter] = None, duration: float = 0.42, damage: float = 16.0) -> LowKickAction:
        return LowKickAction(self, target_fighter, duration=duration, damage=damage)

    def check_kick(self, duration: float = 0.45) -> CheckKickAction:
        return CheckKickAction(self, duration=duration)

    def slip(self, duration: float = 0.40) -> SlipAction:
        return SlipAction(self, duration=duration)

    def bob_weave(self, duration: float = 0.45) -> BobWeaveAction:
        return BobWeaveAction(self, duration=duration)

    def clinch_knee(self, target_fighter: Optional[Fighter] = None, duration: float = 0.50, damage: float = 25.0) -> ClinchKneeAction:
        return ClinchKneeAction(self, target_fighter, duration=duration, damage=damage)

    def takedown(self, target_fighter: Optional[Fighter] = None, duration: float = 0.70, damage: float = 22.0) -> TakedownAction:
        return TakedownAction(self, target_fighter, duration=duration, damage=damage)

    def ground_pound(self, target_fighter: Optional[Fighter] = None, duration: float = 0.55, damage: float = 28.0) -> GroundPoundAction:
        return GroundPoundAction(self, target_fighter, duration=duration, damage=damage)

    def stagger(self, duration: float = 0.50) -> StaggerAction:
        return StaggerAction(self, duration=duration)

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
            elif combo_name == "one_two":
                # Classic boxing 1-2: lead jab followed by the rear straight.
                actions = [
                    self.jab(tgt, duration=0.35, damage=12.0),
                    self.cross(tgt, duration=0.40, damage=18.0),
                ]
            elif combo_name == "dutch_kickboxing":
                # Dutch-style sequence: punches set up the low kick, knee ends it.
                actions = [
                    self.jab(tgt, duration=0.35, damage=12.0),
                    self.cross(tgt, duration=0.40, damage=18.0),
                    self.hook(tgt, duration=0.42, damage=24.0),
                    self.low_kick(tgt, duration=0.42, damage=16.0),
                ]
            elif combo_name == "mma_clinch_takedown":
                # Strike into the clinch, land the knee, then finish the takedown.
                actions = [
                    self.cross(tgt, duration=0.40, damage=18.0),
                    self.clinch_knee(tgt, duration=0.50, damage=25.0),
                    self.takedown(tgt, duration=0.70, damage=22.0),
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
