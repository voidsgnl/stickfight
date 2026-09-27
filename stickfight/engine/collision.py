"""
Collision detection and combat resolution between Hitboxes and Hurtboxes.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple, Optional
import math


def point_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def dist_point_to_segment(p: Tuple[float, float], a: Tuple[float, float], b: Tuple[float, float]) -> float:
    """Calculates Euclidean distance from point p to segment ab."""
    px, py = p
    ax, ay = a
    bx, by = b
    abx = bx - ax
    aby = by - ay
    d2 = abx * abx + aby * aby
    if d2 <= 1e-6:
        return math.hypot(px - ax, py - ay)
    # Project point onto line segment, clamped to [0, 1]
    t = max(0.0, min(1.0, ((px - ax) * abx + (py - ay) * aby) / d2))
    proj_x = ax + t * abx
    proj_y = ay + t * aby
    return math.hypot(px - proj_x, py - proj_y)


@dataclass
class Hitbox:
    x: float
    y: float
    radius: float
    damage: float
    knockback_x: float = 0.0
    knockback_y: float = 0.0
    attacker_name: str = ""
    attack_type: str = "punch"  # "punch", "kick", etc.


@dataclass
class Hurtbox:
    head_pos: Tuple[float, float]
    head_radius: float
    neck_pos: Tuple[float, float]
    pelvis_pos: Tuple[float, float]
    torso_radius: float


def check_hit(hitbox: Hitbox, hurtbox: Hurtbox) -> bool:
    """Checks if a circular hitbox intersects either the head or the torso capsule."""
    hp = (hitbox.x, hitbox.y)
    # Check head circle intersection
    if point_distance(hp, hurtbox.head_pos) <= (hitbox.radius + hurtbox.head_radius):
        return True

    # Check torso capsule intersection
    d_torso = dist_point_to_segment(hp, hurtbox.neck_pos, hurtbox.pelvis_pos)
    if d_torso <= (hitbox.radius + hurtbox.torso_radius):
        return True

    return False
