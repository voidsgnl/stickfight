"""
Fighter representation: stick figure anatomy, health, states, animation playback, and choreography factory.
"""

from __future__ import annotations
from typing import Dict, Tuple, Optional, List
import math

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
from stickfight.engine.collision import (
    Hitbox,
    Hurtbox,
    HurtRegion,
    ARM_MULTIPLIER,
    LEG_MULTIPLIER,
)
from stickfight.engine.stats import FighterStats, STATS_DEFAULT, stats_for_design
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
    ApproachAction,
)

PROPORTIONS_BY_DESIGN = {
    "ninja": PROPORTIONS_NINJA,
    "samurai": PROPORTIONS_SAMURAI,
    "warrior": PROPORTIONS_SAMURAI,
    "brawler": PROPORTIONS_BRAWLER,
    "monk": PROPORTIONS_MONK,
    "cyborg": PROPORTIONS_CYBORG,
    "cyber": PROPORTIONS_CYBORG,
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
        health: Optional[float] = None,
        weapon: Optional[str] = None,
        headband_color: Optional[Tuple[int, int, int]] = None,
        render_style: str = "segmented",
        proportions: Optional[BodyProportions] = None,
        design: Optional[str] = None,
        stats: Optional[FighterStats] = None,
    ):
        self.name = name
        self.x = float(x)
        self.y = float(y)  # Base contact / ground level
        self.facing = 1 if facing >= 0 else -1
        self.spawn = (self.x, self.y, self.facing)  # where reset() puts the fighter back
        self.color = color
        self.head_radius = head_radius * scale
        self.line_width = line_width
        self.scale = scale
        # `design` is an archetype name ("ninja", "brawler", ...). It picks
        # default proportions and stats unless given explicitly.
        self.design = design
        self.stats = stats or stats_for_design(design)
        if proportions is None and design:
            proportions = PROPORTIONS_BY_DESIGN.get(design.lower())
        start_health = health if health is not None else self.stats.health
        self.health = start_health
        self.max_health = start_health
        self.min_health = 0.0  # non-lethal floor (the generator keeps fights alive until the finisher)
        self.ko = False
        self.block_started_at = float("-inf")
        self.dodge_started_at = float("-inf")
        self.weapon = weapon  # "sword", "staff", None
        self.headband_color = headband_color  # Optional ninja ribbon
        self.render_style = render_style  # segmented, silhouette, classic, tech, ink_fight
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
        }

        self.active_clip: AnimationClip = self.clips["idle"]
        self.clip_time: float = 0.0
        self.current_pose: Pose = apply_proportions(make_idle_pose(), self.proportions)
        self.root_dx: float = 0.0
        self.root_dy: float = 0.0

    @property
    def body_x(self) -> float:
        """Where the body is actually drawn (x plus the animation's root offset)."""
        return self.x + self.root_dx * self.facing

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

    def reset_physics(self):
        """Restores the body to the fighter's spawn position and grounded state."""
        self.physics.x = self.x
        self.physics.y = self.y
        self.physics.vx = 0.0
        self.physics.vy = 0.0
        self.physics.ax = 0.0
        self.physics.ay = 0.0
        self.physics.is_grounded = True

    def reset(self):
        """Restores position, health, state, timers, animation and physics to spawn values."""
        self.x, self.y, self.facing = self.spawn
        self.health = self.max_health
        self.ko = False
        self.state = "idle"
        self.block_started_at = float("-inf")
        self.dodge_started_at = float("-inf")
        self.set_animation("idle")
        self.reset_physics()

    def take_damage(self, amount: float, lethal: bool = False) -> float:
        """Applies damage respecting min_health (unless lethal). Returns damage dealt."""
        floor = 0.0 if lethal else self.min_health
        new_health = max(floor, self.health - amount)
        dealt = self.health - new_health
        self.health = new_health
        return max(0.0, dealt)

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
        self.clip_time += dt * self.stats.speed
        clip = self.active_clip
        if clip.name == "knockback" and not clip.loop and self.clip_time >= clip.duration:
            # The skid ends here: fold the clip's root offset into the real
            # position (otherwise the body renders ~120px from where the
            # fighter "is") and recover to idle.
            _, rdx, _ = clip.evaluate(clip.duration)
            self.x += rdx * self.facing
            self.sync_to_physics()
            if self.state == "knockback":
                self.state = "idle"
            self.set_animation("idle")
            self.clip_time = 0.0
        pose, rdx, rdy = self.active_clip.evaluate(self.clip_time)
        # Apply this fighter's archetype rig scaling on top of the shared
        # canonical pose so every clip renders on the correct body type.
        self.current_pose = apply_proportions(pose, self.proportions)
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
        """Returns head circle, torso segment and limb capsules."""
        joints = self.get_world_joints()
        head_pos = joints.get("head", (self.x, self.y - 260.0 * self.scale))
        neck_pos = joints.get("neck", (self.x, self.y - 230.0 * self.scale))
        pelvis_pos = joints.get("pelvis", (self.x, self.y - 140.0 * self.scale))

        limbs: List[HurtRegion] = []
        for side in ("left", "right"):
            tag = side[0]
            for name, chain, radius, mult in (
                ("arm", ("shoulder", "elbow", "hand"), 9.0, ARM_MULTIPLIER),
                ("leg", ("hip", "knee", "foot"), 11.0, LEG_MULTIPLIER),
            ):
                pts = [joints.get(f"{side}_{j}") for j in chain]
                if any(p is None for p in pts):
                    continue
                for a, b in zip(pts, pts[1:]):
                    limbs.append(HurtRegion(f"{name}_{tag}", a, b, radius * self.scale, mult))

        return Hurtbox(
            head_pos=head_pos,
            head_radius=self.head_radius + 4.0,
            neck_pos=neck_pos,
            pelvis_pos=pelvis_pos,
            torso_radius=22.0 * self.scale,
            limbs=limbs,
        )

    def get_hitbox(self) -> Optional[Hitbox]:
        """Calculates the active strike hitbox based on current attack animation."""
        return self._hitbox_from_joints(self.get_world_joints(), self.active_clip.name)

    def hitbox_at(self, clip_time: float) -> Optional[Hitbox]:
        """Hitbox the active attack clip would have at `clip_time`, assuming
        the fighter stays where it is. Lets attacks be sampled *between*
        frames so fast strikes cannot skip past a target."""
        pose, rdx, rdy = self.active_clip.evaluate(clip_time)
        pose = apply_proportions(pose, self.proportions)
        joints = pose.to_world(
            self.x + rdx * self.facing,
            (self.y - 140.0 * self.scale) + rdy,
            facing=self.facing,
            scale=self.scale,
        )
        return self._hitbox_from_joints(joints, self.active_clip.name)

    def _hitbox_from_joints(self, joints, clip_name: str) -> Optional[Hitbox]:
        reach = self.stats.reach
        hb: Optional[Hitbox] = None

        if clip_name == "punch":
            fist_pos = joints.get("right_hand")
            if fist_pos:
                hb = Hitbox(x=fist_pos[0], y=fist_pos[1], radius=28.0 * self.scale, damage=15.0,
                            knockback_x=120.0 * self.facing, attacker_name=self.name, attack_type="punch")
        elif clip_name == "kick":
            foot_pos = joints.get("right_foot")
            if foot_pos:
                hb = Hitbox(x=foot_pos[0], y=foot_pos[1], radius=32.0 * self.scale, damage=22.0,
                            knockback_x=180.0 * self.facing, attacker_name=self.name, attack_type="kick")
        elif clip_name == "uppercut":
            fist_pos = joints.get("right_hand")
            if fist_pos:
                hb = Hitbox(x=fist_pos[0], y=fist_pos[1], radius=32.0 * self.scale, damage=26.0,
                            knockback_x=90.0 * self.facing, knockback_y=-350.0,
                            attacker_name=self.name, attack_type="uppercut")
        elif clip_name == "slash":
            fist_pos = joints.get("right_hand")
            if fist_pos:
                is_staff = self.weapon == "staff"
                blade_y = fist_pos[1] if is_staff else fist_pos[1] - 25.0 * self.scale
                hb = Hitbox(x=fist_pos[0], y=blade_y, radius=(34.0 if is_staff else 42.0) * self.scale,
                            damage=21.0 if is_staff else 28.0,
                            knockback_x=(135.0 if is_staff else 160.0) * self.facing,
                            attacker_name=self.name, attack_type="staff" if is_staff else "slash")
        elif clip_name == "sweep":
            foot_pos = joints.get("right_foot")
            if foot_pos:
                # The sweep pose dips the foot under the floor; a foot can't go
                # through the ground, so keep the hitbox at floor level.
                foot_y = min(foot_pos[1], self.y - 6.0 * self.scale)
                hb = Hitbox(x=foot_pos[0], y=foot_y, radius=35.0 * self.scale, damage=16.0,
                            knockback_x=120.0 * self.facing, attacker_name=self.name,
                            attack_type="sweep", aim="legs")
        if hb is not None:
            hb.radius *= reach
        return hb

    # ========================================================================
    # HIGH-LEVEL CHOREOGRAPHY API BUILDERS
    # ========================================================================

    def _dur(self, base: float, duration: Optional[float]) -> float:
        """Default action length shrinks for fast fighters and grows for slow ones."""
        return duration if duration is not None else base / max(0.1, self.stats.speed)

    def walk_to(self, target_x: float, duration: Optional[float] = None, speed: Optional[float] = None) -> WalkToAction:
        return WalkToAction(self, target_x, speed=speed if speed is not None else 240.0 * self.stats.speed, duration=duration)

    def run_to(self, target_x: float, duration: Optional[float] = None, speed: Optional[float] = None) -> RunToAction:
        return RunToAction(self, target_x, speed=speed if speed is not None else 450.0 * self.stats.speed, duration=duration)

    def approach(self, target_fighter: Fighter, gap: float = 135.0, duration: float = 0.4) -> ApproachAction:
        """Walks until `gap` px from `target_fighter`, measured when the action starts."""
        return ApproachAction(self, target_fighter, gap=gap, duration=duration)

    def punch(self, target_fighter: Optional[Fighter] = None, duration: Optional[float] = None, damage: float = 15.0, finisher: bool = False) -> PunchAction:
        return PunchAction(self, target_fighter, duration=self._dur(0.45, duration), damage=damage, finisher=finisher)

    def kick(self, target_fighter: Optional[Fighter] = None, duration: Optional[float] = None, damage: float = 22.0, finisher: bool = False) -> KickAction:
        return KickAction(self, target_fighter, duration=self._dur(0.55, duration), damage=damage, finisher=finisher)

    def uppercut(self, target_fighter: Optional[Fighter] = None, duration: Optional[float] = None, damage: float = 26.0, finisher: bool = False) -> UppercutAction:
        return UppercutAction(self, target_fighter, duration=self._dur(0.55, duration), damage=damage, finisher=finisher)

    def sweep(self, target_fighter: Optional[Fighter] = None, duration: Optional[float] = None, damage: float = 16.0, finisher: bool = False) -> SweepAction:
        return SweepAction(self, target_fighter, duration=self._dur(0.50, duration), damage=damage, finisher=finisher)

    def slash(self, target_fighter: Optional[Fighter] = None, duration: Optional[float] = None, damage: float = 28.0, finisher: bool = False) -> SlashAction:
        return SlashAction(self, target_fighter, duration=self._dur(0.48, duration), damage=damage, finisher=finisher)

    def staff_strike(self, target_fighter: Optional[Fighter] = None, duration: Optional[float] = None, damage: float = 21.0, finisher: bool = False) -> StaffStrikeAction:
        return StaffStrikeAction(self, target_fighter, duration=self._dur(0.48, duration), damage=damage, finisher=finisher)

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

    def counter(self, target_fighter: Fighter, duration: Optional[float] = None) -> CounterAction:
        return CounterAction(self, target_fighter, duration=self._dur(0.7, duration))

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
