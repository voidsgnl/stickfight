"""
Skeleton and pose representation for 2D stick fighters.
Defines joints, bone hierarchies, pose interpolation, and canonical stances.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Tuple, List, Optional
import math


JointMap = Dict[str, Tuple[float, float]]


@dataclass
class Pose:
    """
    Joint offsets relative to root (pelvis at 0, 0).
    Coordinates follow screen conventions: +x is right, +y is down.
    """
    joints: JointMap = field(default_factory=dict)

    def copy(self) -> Pose:
        return Pose(joints={k: (v[0], v[1]) for k, v in self.joints.items()})

    def get(self, joint_name: str, default: Tuple[float, float] = (0.0, 0.0)) -> Tuple[float, float]:
        return self.joints.get(joint_name, default)

    def set(self, joint_name: str, x: float, y: float) -> Pose:
        self.joints[joint_name] = (float(x), float(y))
        return self

    def lerp(self, target: Pose, t: float) -> Pose:
        """Linear interpolation between two poses at parameter t (0.0 to 1.0)."""
        t = max(0.0, min(1.0, t))
        res_joints: JointMap = {}
        all_keys = set(self.joints.keys()) | set(target.joints.keys())
        for k in all_keys:
            p1 = self.joints.get(k, (0.0, 0.0))
            p2 = target.joints.get(k, (0.0, 0.0))
            rx = p1[0] + (p2[0] - p1[0]) * t
            ry = p1[1] + (p2[1] - p1[1]) * t
            res_joints[k] = (rx, ry)
        return Pose(joints=res_joints)

    def flip_horizontal(self) -> Pose:
        """Mirrors the pose horizontally and swaps left/right limb pairings."""
        swap_map = {
            "left_shoulder": "right_shoulder",
            "right_shoulder": "left_shoulder",
            "left_elbow": "right_elbow",
            "right_elbow": "left_elbow",
            "left_hand": "right_hand",
            "right_hand": "left_hand",
            "left_hip": "right_hip",
            "right_hip": "left_hip",
            "left_knee": "right_knee",
            "right_knee": "left_knee",
            "left_foot": "right_foot",
            "right_foot": "left_foot",
        }
        res: JointMap = {}
        for k, (x, y) in self.joints.items():
            target_key = swap_map.get(k, k)
            res[target_key] = (-x, y)
        return Pose(joints=res)

    def to_world(self, root_x: float, root_y: float, facing: int = 1, scale: float = 1.0) -> JointMap:
        """
        Calculates absolute world joint coordinates.
        facing: 1 for right, -1 for left.
        """
        world: JointMap = {}
        sign = 1.0 if facing >= 0 else -1.0
        for k, (jx, jy) in self.joints.items():
            if sign < 0:
                # Mirror x relative to root
                wx = root_x - (jx * scale)
            else:
                wx = root_x + (jx * scale)
            wy = root_y + (jy * scale)
            world[k] = (wx, wy)
        return world


# ============================================================================
# BODY PROPORTIONS
# Per-archetype rig scaling applied on top of the canonical poses below.
# This lets every archetype share the same animation clips (punch, kick,
# slash, etc.) while still reading as structurally distinct body types
# (e.g. a stocky brawler vs. a lean ninja) rather than uniform palette-swaps.
# ============================================================================

@dataclass
class BodyProportions:
    """Per-archetype rig scaling applied on top of the canonical poses."""
    head_scale: float = 1.0
    torso_length: float = 1.0      # neck/chest distance from pelvis
    shoulder_width: float = 1.0    # arm socket x-offset
    arm_length: float = 1.0        # elbow/hand reach
    stance_width: float = 1.0      # hip x-offset
    leg_length: float = 1.0        # knee/foot y-offset

    def scale_for(self, joint: str) -> Tuple[float, float]:
        """Returns (x_scale, y_scale) for a given joint name."""
        if joint == "head":
            return (self.head_scale, self.head_scale)
        if joint in ("neck", "chest"):
            return (self.shoulder_width, self.torso_length)
        if joint in ("left_shoulder", "right_shoulder"):
            return (self.shoulder_width, self.torso_length)
        if joint in ("left_elbow", "right_elbow", "left_hand", "right_hand"):
            return (self.arm_length, self.arm_length)
        if joint in ("left_hip", "right_hip"):
            return (self.stance_width, 1.0)
        if joint in ("left_knee", "right_knee", "left_foot", "right_foot"):
            return (self.stance_width, self.leg_length)
        return (1.0, 1.0)


def apply_proportions(pose: Pose, proportions: BodyProportions) -> Pose:
    """Returns a new Pose with joint offsets scaled per-group by proportions."""
    scaled: JointMap = {}
    for name, (x, y) in pose.joints.items():
        sx, sy = proportions.scale_for(name)
        scaled[name] = (x * sx, y * sy)
    return Pose(joints=scaled)


# Preset rigs. Values are intentionally subtle multipliers on top of the
# canonical poses so hitboxes, physics, and choreography timing remain valid
# for every archetype without per-archetype pose duplication.
PROPORTIONS_DEFAULT = BodyProportions()
PROPORTIONS_NINJA = BodyProportions(
    head_scale=0.92, torso_length=0.95, shoulder_width=0.9,
    arm_length=1.05, stance_width=0.9, leg_length=1.08,
)
PROPORTIONS_SAMURAI = BodyProportions()  # balanced, canonical proportions
PROPORTIONS_BRAWLER = BodyProportions(
    head_scale=1.05, torso_length=0.88, shoulder_width=1.25,
    arm_length=0.92, stance_width=1.2, leg_length=0.9,
)
PROPORTIONS_MONK = BodyProportions(
    head_scale=0.95, torso_length=1.05, shoulder_width=0.95,
    arm_length=1.1, stance_width=0.95, leg_length=1.1,
)
PROPORTIONS_CYBORG = BodyProportions(
    head_scale=0.85, torso_length=1.0, shoulder_width=1.05,
    arm_length=1.15, stance_width=1.0, leg_length=1.05,
)


# ============================================================================
# CANONICAL POSES
# Pelvis is at (0, 0). Up is negative y, down is positive y.
# Normal standing height: pelvis at y=0, feet at y=+140, head at y=-140.
# ============================================================================

def make_idle_pose() -> Pose:
    """Fighting stance: knees slightly bent, hands up guarding."""
    return Pose({
        "pelvis": (0.0, 0.0),
        "chest": (-4.0, -50.0),
        "neck": (-6.0, -90.0),
        "head": (-8.0, -125.0),
        # Back arm (left when facing right)
        "left_shoulder": (-16.0, -85.0),
        "left_elbow": (-2.0, -55.0),
        "left_hand": (15.0, -75.0),
        # Front arm (right when facing right)
        "right_shoulder": (10.0, -85.0),
        "right_elbow": (28.0, -60.0),
        "right_hand": (42.0, -85.0),
        # Back leg
        "left_hip": (-15.0, 5.0),
        "left_knee": (-32.0, 72.0),
        "left_foot": (-28.0, 140.0),
        # Front leg
        "right_hip": (12.0, 5.0),
        "right_knee": (24.0, 70.0),
        "right_foot": (28.0, 140.0),
    })


def make_walk_poses() -> List[Pose]:
    """4-step walk cycle poses."""
    # 1. Right leg forward, left leg back (Contact)
    p1 = Pose({
        "pelvis": (0.0, -5.0),
        "chest": (5.0, -52.0),
        "neck": (8.0, -92.0),
        "head": (10.0, -125.0),
        "left_shoulder": (-12.0, -87.0),
        "left_elbow": (15.0, -65.0),
        "left_hand": (35.0, -60.0),
        "right_shoulder": (12.0, -87.0),
        "right_elbow": (-15.0, -65.0),
        "right_hand": (-35.0, -60.0),
        "left_hip": (-12.0, 0.0),
        "left_knee": (-35.0, 68.0),
        "left_foot": (-45.0, 138.0),
        "right_hip": (12.0, 0.0),
        "right_knee": (30.0, 68.0),
        "right_foot": (45.0, 140.0),
    })

    # 2. Left leg passing forward (Passing 1)
    p2 = Pose({
        "pelvis": (0.0, -12.0),
        "chest": (4.0, -60.0),
        "neck": (6.0, -100.0),
        "head": (8.0, -133.0),
        "left_shoulder": (-10.0, -95.0),
        "left_elbow": (-5.0, -70.0),
        "left_hand": (10.0, -60.0),
        "right_shoulder": (10.0, -95.0),
        "right_elbow": (5.0, -70.0),
        "right_hand": (-10.0, -60.0),
        "left_hip": (-10.0, -7.0),
        "left_knee": (0.0, 55.0),
        "left_foot": (5.0, 110.0),
        "right_hip": (10.0, -7.0),
        "right_knee": (5.0, 65.0),
        "right_foot": (0.0, 140.0),
    })

    # 3. Left leg forward, right leg back (Contact 2)
    p3 = Pose({
        "pelvis": (0.0, -5.0),
        "chest": (5.0, -52.0),
        "neck": (8.0, -92.0),
        "head": (10.0, -125.0),
        "left_shoulder": (-12.0, -87.0),
        "left_elbow": (-15.0, -65.0),
        "left_hand": (-35.0, -60.0),
        "right_shoulder": (12.0, -87.0),
        "right_elbow": (15.0, -65.0),
        "right_hand": (35.0, -60.0),
        "left_hip": (-12.0, 0.0),
        "left_knee": (30.0, 68.0),
        "left_foot": (45.0, 140.0),
        "right_hip": (12.0, 0.0),
        "right_knee": (-35.0, 68.0),
        "right_foot": (-45.0, 138.0),
    })

    # 4. Right leg passing forward (Passing 2)
    p4 = Pose({
        "pelvis": (0.0, -12.0),
        "chest": (4.0, -60.0),
        "neck": (6.0, -100.0),
        "head": (8.0, -133.0),
        "left_shoulder": (-10.0, -95.0),
        "left_elbow": (5.0, -70.0),
        "left_hand": (-10.0, -60.0),
        "right_shoulder": (10.0, -95.0),
        "right_elbow": (-5.0, -70.0),
        "right_hand": (10.0, -60.0),
        "left_hip": (-10.0, -7.0),
        "left_knee": (5.0, 65.0),
        "left_foot": (0.0, 140.0),
        "right_hip": (10.0, -7.0),
        "right_knee": (0.0, 55.0),
        "right_foot": (5.0, 110.0),
    })

    return [p1, p2, p3, p4]


def make_punch_windup() -> Pose:
    """Torso pulls back, rear fist cocked."""
    return Pose({
        "pelvis": (-10.0, 5.0),
        "chest": (-25.0, -45.0),
        "neck": (-35.0, -85.0),
        "head": (-30.0, -120.0),
        "left_shoulder": (-45.0, -80.0),
        "left_elbow": (-65.0, -70.0),
        "left_hand": (-55.0, -90.0),
        "right_shoulder": (-15.0, -80.0),
        "right_elbow": (5.0, -65.0),
        "right_hand": (20.0, -80.0),
        "left_hip": (-25.0, 10.0),
        "left_knee": (-45.0, 75.0),
        "left_foot": (-50.0, 140.0),
        "right_hip": (5.0, 10.0),
        "right_knee": (15.0, 75.0),
        "right_foot": (25.0, 140.0),
    })


def make_punch_strike() -> Pose:
    """Explosive extension forward, right fist fully thrust out."""
    return Pose({
        "pelvis": (20.0, 5.0),
        "chest": (50.0, -45.0),
        "neck": (65.0, -85.0),
        "head": (70.0, -120.0),
        "left_shoulder": (45.0, -80.0),
        "left_elbow": (15.0, -65.0),
        "left_hand": (5.0, -80.0),
        "right_shoulder": (75.0, -80.0),
        "right_elbow": (125.0, -78.0),
        "right_hand": (175.0, -76.0),  # punch reach!
        "left_hip": (5.0, 10.0),
        "left_knee": (-20.0, 75.0),
        "left_foot": (-35.0, 140.0),
        "right_hip": (35.0, 10.0),
        "right_knee": (65.0, 75.0),
        "right_foot": (60.0, 140.0),
    })


def make_kick_windup() -> Pose:
    """Weight shifts back onto left leg, right knee chambers up high."""
    return Pose({
        "pelvis": (-15.0, -10.0),
        "chest": (-30.0, -60.0),
        "neck": (-35.0, -100.0),
        "head": (-30.0, -135.0),
        "left_shoulder": (-45.0, -95.0),
        "left_elbow": (-30.0, -75.0),
        "left_hand": (-10.0, -85.0),
        "right_shoulder": (-15.0, -95.0),
        "right_elbow": (5.0, -80.0),
        "right_hand": (20.0, -95.0),
        "left_hip": (-20.0, -5.0),
        "left_knee": (-25.0, 68.0),
        "left_foot": (-25.0, 140.0),
        "right_hip": (0.0, -10.0),
        "right_knee": (35.0, 10.0),
        "right_foot": (15.0, 45.0),
    })


def make_kick_strike() -> Pose:
    """Torso leans back for counter-balance, right leg whips straight forward."""
    return Pose({
        "pelvis": (-10.0, -5.0),
        "chest": (-45.0, -50.0),
        "neck": (-60.0, -85.0),
        "head": (-65.0, -120.0),
        "left_shoulder": (-70.0, -80.0),
        "left_elbow": (-85.0, -60.0),
        "left_hand": (-70.0, -45.0),
        "right_shoulder": (-35.0, -80.0),
        "right_elbow": (-15.0, -65.0),
        "right_hand": (5.0, -80.0),
        "left_hip": (-15.0, 0.0),
        "left_knee": (-20.0, 70.0),
        "left_foot": (-20.0, 140.0),
        "right_hip": (10.0, -5.0),
        "right_knee": (95.0, -45.0),
        "right_foot": (180.0, -65.0),  # kick reach at head/torso height!
    })


def make_block_pose() -> Pose:
    """Sturdy defensive posture, forearms crossed in front of head/chest."""
    return Pose({
        "pelvis": (-10.0, 15.0),
        "chest": (-15.0, -35.0),
        "neck": (-15.0, -75.0),
        "head": (-20.0, -110.0),
        "left_shoulder": (-25.0, -70.0),
        "left_elbow": (10.0, -65.0),
        "left_hand": (25.0, -90.0),
        "right_shoulder": (0.0, -70.0),
        "right_elbow": (22.0, -68.0),
        "right_hand": (25.0, -95.0),
        "left_hip": (-25.0, 20.0),
        "left_knee": (-40.0, 80.0),
        "left_foot": (-45.0, 140.0),
        "right_hip": (5.0, 20.0),
        "right_knee": (15.0, 80.0),
        "right_foot": (25.0, 140.0),
    })


def make_dodge_pose() -> Pose:
    """Matrix-style lean back dodging a blow."""
    return Pose({
        "pelvis": (-15.0, 20.0),
        "chest": (-65.0, -25.0),
        "neck": (-105.0, -55.0),
        "head": (-135.0, -80.0),
        "left_shoulder": (-110.0, -50.0),
        "left_elbow": (-80.0, -40.0),
        "left_hand": (-50.0, -55.0),
        "right_shoulder": (-90.0, -50.0),
        "right_elbow": (-65.0, -40.0),
        "right_hand": (-35.0, -55.0),
        "left_hip": (-25.0, 25.0),
        "left_knee": (-50.0, 85.0),
        "left_foot": (-60.0, 140.0),
        "right_hip": (0.0, 25.0),
        "right_knee": (25.0, 85.0),
        "right_foot": (30.0, 140.0),
    })


def make_hit_reaction_pose() -> Pose:
    """Staggering from impact: head snaps back, chest thrust backwards."""
    return Pose({
        "pelvis": (-15.0, 10.0),
        "chest": (-55.0, -40.0),
        "neck": (-80.0, -70.0),
        "head": (-105.0, -95.0),
        "left_shoulder": (-85.0, -65.0),
        "left_elbow": (-100.0, -35.0),
        "left_hand": (-85.0, -5.0),
        "right_shoulder": (-65.0, -65.0),
        "right_elbow": (-45.0, -45.0),
        "right_hand": (-25.0, -25.0),
        "left_hip": (-25.0, 15.0),
        "left_knee": (-55.0, 78.0),
        "left_foot": (-65.0, 140.0),
        "right_hip": (-5.0, 15.0),
        "right_knee": (10.0, 78.0),
        "right_foot": (15.0, 140.0),
    })


def make_knockback_air_pose() -> Pose:
    """Airborne horizontal recoil."""
    return Pose({
        "pelvis": (-30.0, -60.0),
        "chest": (-80.0, -75.0),
        "neck": (-120.0, -85.0),
        "head": (-155.0, -90.0),
        "left_shoulder": (-125.0, -80.0),
        "left_elbow": (-150.0, -55.0),
        "left_hand": (-175.0, -35.0),
        "right_shoulder": (-105.0, -80.0),
        "right_elbow": (-125.0, -55.0),
        "right_hand": (-145.0, -35.0),
        "left_hip": (-35.0, -55.0),
        "left_knee": (15.0, -45.0),
        "left_foot": (65.0, -20.0),
        "right_hip": (-15.0, -55.0),
        "right_knee": (35.0, -45.0),
        "right_foot": (85.0, -25.0),
    })


def make_fall_pose() -> Pose:
    """Flat on the ground."""
    return Pose({
        "pelvis": (0.0, 135.0),
        "chest": (-45.0, 133.0),
        "neck": (-80.0, 132.0),
        "head": (-110.0, 130.0),
        "left_shoulder": (-85.0, 132.0),
        "left_elbow": (-70.0, 120.0),
        "left_hand": (-50.0, 120.0),
        "right_shoulder": (-75.0, 132.0),
        "right_elbow": (-60.0, 138.0),
        "right_hand": (-40.0, 138.0),
        "left_hip": (10.0, 135.0),
        "left_knee": (55.0, 132.0),
        "left_foot": (95.0, 135.0),
        "right_hip": (15.0, 135.0),
        "right_knee": (60.0, 136.0),
        "right_foot": (105.0, 137.0),
    })


def make_jump_pose(phase: float = 0.5) -> Pose:
    """Airborne jumping stance."""
    return Pose({
        "pelvis": (0.0, -100.0),
        "chest": (5.0, -150.0),
        "neck": (8.0, -190.0),
        "head": (10.0, -225.0),
        "left_shoulder": (-10.0, -185.0),
        "left_elbow": (-25.0, -155.0),
        "left_hand": (-15.0, -125.0),
        "right_shoulder": (15.0, -185.0),
        "right_elbow": (30.0, -155.0),
        "right_hand": (20.0, -125.0),
        "left_hip": (-12.0, -95.0),
        "left_knee": (-25.0, -45.0),
        "left_foot": (-15.0, 10.0),
        "right_hip": (12.0, -95.0),
        "right_knee": (25.0, -45.0),
        "right_foot": (15.0, 10.0),
    })


def make_uppercut_windup() -> Pose:
    """Deep crouch, right fist dropped low and coiled for upward drive."""
    return Pose({
        "pelvis": (-10.0, 25.0),
        "chest": (-15.0, -15.0),
        "neck": (-15.0, -55.0),
        "head": (-12.0, -90.0),
        "left_shoulder": (-25.0, -50.0),
        "left_elbow": (5.0, -45.0),
        "left_hand": (15.0, -70.0),
        "right_shoulder": (5.0, -50.0),
        "right_elbow": (15.0, 5.0),
        "right_hand": (25.0, -15.0),  # Dropped low near hip
        "left_hip": (-20.0, 25.0),
        "left_knee": (-40.0, 85.0),
        "left_foot": (-45.0, 140.0),
        "right_hip": (10.0, 25.0),
        "right_knee": (25.0, 90.0),
        "right_foot": (30.0, 140.0),
    })


def make_uppercut_strike() -> Pose:
    """Explosive upward leap, right fist driving high into the sky."""
    return Pose({
        "pelvis": (15.0, -40.0),
        "chest": (25.0, -100.0),
        "neck": (28.0, -145.0),
        "head": (25.0, -180.0),
        "left_shoulder": (15.0, -140.0),
        "left_elbow": (-10.0, -110.0),
        "left_hand": (-20.0, -90.0),
        "right_shoulder": (40.0, -140.0),
        "right_elbow": (85.0, -125.0),
        "right_hand": (130.0, -155.0),  # Drives forward through the opponent's guard
        "left_hip": (5.0, -35.0),
        "left_knee": (-5.0, 25.0),
        "left_foot": (-10.0, 85.0),
        "right_hip": (25.0, -35.0),
        "right_knee": (45.0, 10.0),
        "right_foot": (50.0, 70.0),
    })


def make_sweep_pose() -> Pose:
    """Low crouched leg sweep rotating along the floor."""
    return Pose({
        "pelvis": (-10.0, 60.0),
        "chest": (-15.0, 25.0),
        "neck": (-10.0, 0.0),
        "head": (-5.0, -35.0),
        "left_shoulder": (-20.0, 5.0),
        "left_elbow": (-35.0, 50.0),
        "left_hand": (-40.0, 95.0),  # Hand bracing on floor
        "right_shoulder": (10.0, 5.0),
        "right_elbow": (25.0, -15.0),
        "right_hand": (35.0, -35.0),
        "left_hip": (-25.0, 65.0),
        "left_knee": (-55.0, 100.0),
        "left_foot": (-35.0, 140.0),
        "right_hip": (5.0, 65.0),
        "right_knee": (75.0, 120.0),
        "right_foot": (155.0, 138.0),  # Sweeping foot extended low along ground
    })


def make_sword_ready() -> Pose:
    """Classic 2-handed samurai / ninja ready stance."""
    return Pose({
        "pelvis": (0.0, 5.0),
        "chest": (5.0, -48.0),
        "neck": (8.0, -88.0),
        "head": (10.0, -122.0),
        "left_shoulder": (-10.0, -84.0),
        "left_elbow": (15.0, -65.0),
        "left_hand": (35.0, -65.0),
        "right_shoulder": (15.0, -84.0),
        "right_elbow": (30.0, -68.0),
        "right_hand": (45.0, -68.0),  # Both hands gripping hilt
        "left_hip": (-15.0, 5.0),
        "left_knee": (-30.0, 72.0),
        "left_foot": (-28.0, 140.0),
        "right_hip": (12.0, 5.0),
        "right_knee": (25.0, 70.0),
        "right_foot": (32.0, 140.0),
    })


def make_sword_slash_windup() -> Pose:
    """Blade raised high above shoulder/head, coiling for diagonal slash."""
    return Pose({
        "pelvis": (-15.0, 10.0),
        "chest": (-30.0, -45.0),
        "neck": (-40.0, -85.0),
        "head": (-35.0, -120.0),
        "left_shoulder": (-45.0, -85.0),
        "left_elbow": (-60.0, -125.0),
        "left_hand": (-45.0, -165.0),
        "right_shoulder": (-20.0, -85.0),
        "right_elbow": (-35.0, -135.0),
        "right_hand": (-25.0, -175.0),  # Hands raised high behind head
        "left_hip": (-25.0, 10.0),
        "left_knee": (-45.0, 75.0),
        "left_foot": (-50.0, 140.0),
        "right_hip": (5.0, 10.0),
        "right_knee": (15.0, 75.0),
        "right_foot": (25.0, 140.0),
    })


def make_sword_slash_strike() -> Pose:
    """Full-extension downward diagonal slash."""
    return Pose({
        "pelvis": (20.0, 15.0),
        "chest": (55.0, -35.0),
        "neck": (75.0, -70.0),
        "head": (80.0, -105.0),
        "left_shoulder": (55.0, -68.0),
        "left_elbow": (85.0, -45.0),
        "left_hand": (120.0, -35.0),
        "right_shoulder": (80.0, -68.0),
        "right_elbow": (115.0, -45.0),
        "right_hand": (145.0, -30.0),  # Thrust forward follow-through
        "left_hip": (5.0, 15.0),
        "left_knee": (-20.0, 80.0),
        "left_foot": (-35.0, 140.0),
        "right_hip": (35.0, 15.0),
        "right_knee": (70.0, 80.0),
        "right_foot": (65.0, 140.0),
    })


# ============================================================================
# REALISTIC MARTIAL ARTS POSES (Boxing / Muay Thai / MMA)
# Same pelvis-rooted convention as the canonical poses above: facing right,
# left limb is the lead (jab) side, right limb is the rear (power) side.
# ============================================================================

def _guard_hands(pose: Pose) -> Pose:
    """Apply a tight boxing guard to both arms of an otherwise rooted pose."""
    pose.set("left_shoulder", -16.0, -85.0)
    pose.set("left_elbow", -2.0, -58.0)
    pose.set("left_hand", 18.0, -80.0)
    pose.set("right_shoulder", 10.0, -85.0)
    pose.set("right_elbow", 26.0, -60.0)
    pose.set("right_hand", 40.0, -88.0)
    return pose


def _legs_stance(pose: Pose, bl_x: float, bk_x: float) -> Pose:
    """Standard fight stance legs with slight lead/back foot slide offsets."""
    pose.set("left_hip", -15.0, 5.0)
    pose.set("left_knee", -32.0 + bl_x, 72.0)
    pose.set("left_foot", -28.0 + bl_x, 140.0)
    pose.set("right_hip", 12.0, 5.0)
    pose.set("right_knee", 24.0 + bk_x, 70.0)
    pose.set("right_foot", 28.0 + bk_x, 140.0)
    return pose


def make_jab_strike() -> Pose:
    """Quick straight lead-hand punch: shoulder turns over, fist fully extended."""
    p = Pose({"pelvis": (5.0, 0.0)})
    p.set("chest", (8.0, -50.0))
    p.set("neck", (10.0, -90.0))
    p.set("head", (8.0, -125.0))
    # Lead arm snapped straight out at head height
    p.set("left_shoulder", (12.0, -88.0))
    p.set("left_elbow", (75.0, -86.0))
    p.set("left_hand", (140.0, -84.0))  # jab reach!
    # Rear hand stays glued to the chin
    p.set("right_shoulder", (-2.0, -86.0))
    p.set("right_elbow", (14.0, -64.0))
    p.set("right_hand", (22.0, -92.0))
    _legs_stance(p, bl_x=8.0, bk_x=-2.0)
    return p


def make_cross_strike() -> Pose:
    """Rear-hand straight power punch: full hip/torso rotation into the shot."""
    p = Pose({"pelvis": (15.0, 3.0)})
    p.set("chest", (35.0, -48.0))
    p.set("neck", (48.0, -88.0))
    p.set("head", (45.0, -122.0))
    # Rear arm fully extended through target
    p.set("right_shoulder", (35.0, -85.0))
    p.set("right_elbow", (95.0, -82.0))
    p.set("right_hand", (160.0, -80.0))  # cross reach!
    # Lead hand pulled back protecting the jaw
    p.set("left_shoulder", (5.0, -85.0))
    p.set("left_elbow", (-8.0, -62.0))
    p.set("left_hand", (8.0, -85.0))
    _legs_stance(p, bl_x=14.0, bk_x=6.0)
    return p


def make_hook_strike() -> Pose:
    """Lead hook thrown on a bent arm, elbow level, torso pivoting over it."""
    p = Pose({"pelvis": (10.0, 3.0)})
    p.set("chest", (28.0, -48.0))
    p.set("neck", (35.0, -88.0))
    p.set("head", (30.0, -123.0))
    # Hooked lead arm: elbow out to the side, fist arcing in at head height
    p.set("left_shoulder", (18.0, -86.0))
    p.set("left_elbow", (62.0, -78.0))
    p.set("left_hand", (105.0, -100.0))  # hook apex around temple height
    # Rear hand tight on the chin
    p.set("right_shoulder", (8.0, -85.0))
    p.set("right_elbow", (24.0, -62.0))
    p.set("right_hand", (30.0, -90.0))
    _legs_stance(p, bl_x=12.0, bk_x=2.0)
    return p


def make_low_kick_pose() -> Pose:
    """Rear-leg roundhouse aimed at the opponent's lead thigh/calf."""
    p = Pose({"pelvis": (-12.0, -5.0)})
    p.set("chest", (-30.0, -55.0))
    p.set("neck", (-38.0, -95.0))
    p.set("head", (-35.0, -130.0))
    # Arms swing for counter-balance and cover
    p.set("left_shoulder", (-48.0, -90.0))
    p.set("left_elbow", (-62.0, -70.0))
    p.set("left_hand", (-50.0, -50.0))
    p.set("right_shoulder", (-18.0, -90.0))
    p.set("right_elbow", (2.0, -72.0))
    p.set("right_hand", (18.0, -88.0))
    # Pivot (lead) leg planted, toe out
    p.set("left_hip", (-18.0, 0.0))
    p.set("left_knee", (-30.0, 70.0))
    p.set("left_foot", (-42.0, 140.0))
    # Rear leg swings low: knee leads, shin lands on the target's leg
    p.set("right_hip", (5.0, -2.0))
    p.set("right_knee", (75.0, 62.0))
    p.set("right_foot", (150.0, 95.0))  # low kick contact height (leg level)
    return p


def make_check_kick_pose() -> Pose:
    """Lead shin raised vertically to bone-on-bone block an incoming low kick."""
    p = Pose({"pelvis": (-8.0, 0.0)})
    p.set("chest", (-18.0, -52.0))
    p.set("neck", (-22.0, -92.0))
    p.set("head", (-20.0, -127.0))
    _guard_hands(p)
    # Rear leg planted, holding the line
    p.set("right_hip", (12.0, 5.0))
    p.set("right_knee", (20.0, 72.0))
    p.set("right_foot", (24.0, 140.0))
    # Lead leg lifts: knee up, shin vertical, foot tucked
    p.set("left_hip", (-14.0, 2.0))
    p.set("left_knee", (-6.0, 55.0))
    p.set("left_foot", (2.0, 120.0))
    return p


def make_slip_pose() -> Pose:
    """Small lateral head slip off the punch's centerline, hands home."""
    p = Pose({"pelvis": (-4.0, 2.0)})
    p.set("chest", (-10.0, -48.0))
    p.set("neck", (-14.0, -88.0))
    p.set("head", (-26.0, -118.0))  # head shifted back/aside
    _guard_hands(p)
    _legs_stance(p, bl_x=-4.0, bk_x=0.0)
    return p


def make_bob_weave_pose() -> Pose:
    """Deep U-shaped duck: knees bent, head dropped below the punch line."""
    p = Pose({"pelvis": (-6.0, 30.0)})
    p.set("chest", (-8.0, -25.0))
    p.set("neck", (-10.0, -62.0))
    p.set("head", (-12.0, -92.0))  # head well below standing guard height
    # Hands stay up by the temples while weaving
    p.set("left_shoulder", (-20.0, -58.0))
    p.set("left_elbow", (-8.0, -38.0))
    p.set("left_hand", (8.0, -58.0))
    p.set("right_shoulder", (6.0, -58.0))
    p.set("right_elbow", (20.0, -38.0))
    p.set("right_hand", (30.0, -58.0))
    # Wide squat
    p.set("left_hip", (-18.0, 32.0))
    p.set("left_knee", (-45.0, 92.0))
    p.set("left_foot", (-40.0, 140.0))
    p.set("right_hip", (16.0, 32.0))
    p.set("right_knee", (42.0, 92.0))
    p.set("right_foot", (40.0, 140.0))
    return p


def make_clinch_knee_pose() -> Pose:
    """Thai plum clinch: both hands overhook the rival's neck, rear knee drives up."""
    p = Pose({"pelvis": (8.0, -5.0)})
    p.set("chest", (18.0, -52.0))
    p.set("neck", (24.0, -92.0))
    p.set("head", (26.0, -126.0))
    # Both arms reaching forward-and-down over the opponent's shoulders
    p.set("left_shoulder", (10.0, -88.0))
    p.set("left_elbow", (55.0, -100.0))
    p.set("left_hand", (95.0, -118.0))
    p.set("right_shoulder", (26.0, -86.0))
    p.set("right_elbow", (68.0, -96.0))
    p.set("right_hand", (105.0, -112.0))
    # Support leg planted
    p.set("left_hip", (-14.0, 5.0))
    p.set("left_knee", (-28.0, 72.0))
    p.set("left_foot", (-26.0, 140.0))
    # Rear leg drives the knee forward and high into the body
    p.set("right_hip", (14.0, 0.0))
    p.set("right_knee", (70.0, 30.0))
    p.set("right_foot", (55.0, 85.0))
    return p


def make_takedown_shoot_pose() -> Pose:
    """Double-leg wrestling shot: level changed low, driving forward, arms through."""
    p = Pose({"pelvis": (25.0, 55.0)})
    p.set("chest", (45.0, 15.0))
    p.set("neck", (62.0, -12.0))
    p.set("head", (78.0, -22.0))  # head tucked beside the opponent's hip
    # Arms shot low and through for the double-leg grip
    p.set("left_shoulder", (52.0, 2.0))
    p.set("left_elbow", (88.0, 22.0))
    p.set("left_hand", (120.0, 40.0))
    p.set("right_shoulder", (58.0, 8.0))
    p.set("right_elbow", (95.0, 30.0))
    p.set("right_hand", (128.0, 50.0))
    # Lead leg deep under the body
    p.set("left_hip", (10.0, 58.0))
    p.set("left_knee", (55.0, 105.0))
    p.set("left_foot", (85.0, 140.0))
    # Rear leg trailing, toe dragging for the drive
    p.set("right_hip", (-12.0, 55.0))
    p.set("right_knee", (-55.0, 100.0))
    p.set("right_foot", (-95.0, 138.0))
    return p


def make_ground_and_pound_top_pose() -> Pose:
    """Top position: posture up high over grounded rival, fists raining down."""
    p = Pose({"pelvis": (0.0, 40.0)})
    p.set("chest", (12.0, -5.0))
    p.set("neck", (20.0, -42.0))
    p.set("head", (24.0, -76.0))
    # Both fists hammering downward toward the grounded opponent
    p.set("left_shoulder", (18.0, -38.0))
    p.set("left_elbow", (48.0, -10.0))
    p.set("left_hand", (72.0, 45.0))
    p.set("right_shoulder", (28.0, -35.0))
    p.set("right_elbow", (60.0, -5.0))
    p.set("right_hand", (88.0, 52.0))
    # Knees tucked in base position near the ground
    p.set("left_hip", (-10.0, 45.0))
    p.set("left_knee", (-45.0, 95.0))
    p.set("left_foot", (-25.0, 138.0))
    p.set("right_hip", (8.0, 45.0))
    p.set("right_knee", (35.0, 100.0))
    p.set("right_foot", (60.0, 138.0))
    return p


def make_stagger_pose() -> Pose:
    """Wobbled and hurt after a clean power shot: reeling back, guard dropping."""
    p = Pose({"pelvis": (-18.0, 8.0)})
    p.set("chest", (-38.0, -42.0))
    p.set("neck", (-52.0, -80.0))
    p.set("head", (-60.0, -112.0))  # head lolling backward
    # Arms flailing out trying to find balance
    p.set("left_shoulder", (-52.0, -76.0))
    p.set("left_elbow", (-78.0, -60.0))
    p.set("left_hand", (-95.0, -38.0))
    p.set("right_shoulder", (-25.0, -78.0))
    p.set("right_elbow", (-5.0, -58.0))
    p.set("right_hand", (15.0, -40.0))
    # Feet staggering backward
    p.set("left_hip", (-28.0, 12.0))
    p.set("left_knee", (-52.0, 78.0))
    p.set("left_foot", (-70.0, 140.0))
    p.set("right_hip", (0.0, 12.0))
    p.set("right_knee", (18.0, 76.0))
    p.set("right_foot", (40.0, 140.0))
    return p


def make_grounded_guard_pose() -> Pose:
    """On the back with knees tucked and hands up — defensive bottom position."""
    p = Pose({"pelvis": (-10.0, 128.0)})
    p.set("chest", (-48.0, 118.0))
    p.set("neck", (-75.0, 112.0))
    p.set("head", (-100.0, 116.0))
    # Forearms raised in framing guard
    p.set("left_shoulder", (-72.0, 108.0))
    p.set("left_elbow", (-58.0, 82.0))
    p.set("left_hand", (-38.0, 62.0))
    p.set("right_shoulder", (-64.0, 114.0))
    p.set("right_elbow", (-46.0, 88.0))
    p.set("right_hand", (-24.0, 68.0))
    # Hips on the mat, knees between chest and adversary
    p.set("left_hip", (5.0, 130.0))
    p.set("left_knee", (52.0, 98.0))
    p.set("left_foot", (75.0, 130.0))
    p.set("right_hip", (10.0, 132.0))
    p.set("right_knee", (60.0, 108.0))
    p.set("right_foot", (88.0, 138.0))
    return p
