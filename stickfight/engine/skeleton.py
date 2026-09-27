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
