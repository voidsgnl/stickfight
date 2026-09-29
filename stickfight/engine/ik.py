"""Lightweight 2D two-bone inverse kinematics helpers for the stick-fight rig."""

from __future__ import annotations

import math
from typing import Tuple

from stickfight.engine.skeleton import Pose


def solve_two_bone(root: Tuple[float, float], target: Tuple[float, float], upper_length: float, lower_length: float, bend_sign: float = 1.0):
    """Return elbow and hand positions for a planar two-bone chain."""
    rx, ry = root
    tx, ty = target
    dx, dy = tx - rx, ty - ry
    raw_distance = max(1e-6, math.hypot(dx, dy))
    distance = max(abs(upper_length - lower_length), min(upper_length + lower_length, raw_distance))
    base_angle = math.atan2(dy, dx)
    cos_angle = (upper_length**2 + distance**2 - lower_length**2) / (2.0 * upper_length * distance)
    offset = math.acos(max(-1.0, min(1.0, cos_angle)))
    elbow_angle = base_angle + (offset if bend_sign >= 0 else -offset)
    elbow = (rx + math.cos(elbow_angle) * upper_length, ry + math.sin(elbow_angle) * upper_length)
    scale = distance / raw_distance
    hand = (rx + dx * scale, ry + dy * scale)
    return elbow, hand


def apply_two_bone_ik(pose: Pose, shoulder: str, elbow: str, hand: str, target: Tuple[float, float], bend_sign: float = 1.0) -> Pose:
    """Apply IK to an arm while preserving its authored bone lengths."""
    result = pose.copy()
    root = result.get(shoulder)
    elbow_pos = result.get(elbow)
    hand_pos = result.get(hand)
    upper = math.hypot(elbow_pos[0] - root[0], elbow_pos[1] - root[1])
    lower = math.hypot(hand_pos[0] - elbow_pos[0], hand_pos[1] - elbow_pos[1])
    if upper < 1e-6 or lower < 1e-6:
        return result
    solved_elbow, solved_hand = solve_two_bone(root, target, upper, lower, bend_sign)
    return result.set(elbow, solved_elbow).set(hand, solved_hand)
