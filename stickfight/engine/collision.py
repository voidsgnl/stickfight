"""
Collision detection and combat resolution between Hitboxes and Hurtboxes.

Hits are *swept*: a Hitbox may carry the position it had a moment ago
(prev_x/prev_y) and the whole path is tested, so a fast punch cannot
tunnel through a target between two frames.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import math

Point = Tuple[float, float]

# Damage multipliers by body region (torso is the reference).
HEAD_MULTIPLIER = 1.0
TORSO_MULTIPLIER = 1.0
ARM_MULTIPLIER = 0.6
LEG_MULTIPLIER = 0.7


def point_distance(p1: Point, p2: Point) -> float:
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def dist_point_to_segment(p: Point, a: Point, b: Point) -> float:
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
    prev_x: Optional[float] = None  # where the hitbox was a moment ago (swept test)
    prev_y: Optional[float] = None
    aim: str = "body"  # "legs" = leg hits count at full damage (sweeps)
    finisher: bool = False  # a finisher always deals at least the target's remaining health

    def path_points(self) -> List[Point]:
        """Points from the previous to the current position, spaced so no
        gap is wider than half the hitbox radius (oldest first)."""
        if self.prev_x is None or self.prev_y is None:
            return [(self.x, self.y)]
        dx, dy = self.x - self.prev_x, self.y - self.prev_y
        dist = math.hypot(dx, dy)
        n = max(1, min(64, int(math.ceil(dist / max(4.0, self.radius * 0.5)))))
        return [(self.prev_x + dx * i / n, self.prev_y + dy * i / n) for i in range(n + 1)]


@dataclass
class HurtRegion:
    """A capsule (segment + radius) on a limb."""
    name: str
    a: Point
    b: Point
    radius: float
    multiplier: float = 1.0


@dataclass
class Hurtbox:
    head_pos: Point
    head_radius: float
    neck_pos: Point
    pelvis_pos: Point
    torso_radius: float
    limbs: List[HurtRegion] = field(default_factory=list)
    head_multiplier: float = HEAD_MULTIPLIER
    torso_multiplier: float = TORSO_MULTIPLIER


@dataclass
class HitResult:
    region: str  # "head", "torso", "arm_l", "leg_r", ...
    multiplier: float
    point: Point


def _test_point(p: Point, radius: float, hurtbox: Hurtbox, aim: str) -> Optional[HitResult]:
    """Checks one hitbox position. Priority: head, torso, then nearest limb."""
    if point_distance(p, hurtbox.head_pos) <= radius + hurtbox.head_radius:
        return HitResult("head", hurtbox.head_multiplier, p)
    if dist_point_to_segment(p, hurtbox.neck_pos, hurtbox.pelvis_pos) <= radius + hurtbox.torso_radius:
        return HitResult("torso", hurtbox.torso_multiplier, p)
    best: Optional[Tuple[float, HurtRegion]] = None
    for limb in hurtbox.limbs:
        gap = dist_point_to_segment(p, limb.a, limb.b) - (radius + limb.radius)
        if gap <= 0.0 and (best is None or gap < best[0]):
            best = (gap, limb)
    if best is not None:
        limb = best[1]
        mult = 1.0 if (aim == "legs" and limb.name.startswith("leg")) else limb.multiplier
        return HitResult(limb.name, mult, p)
    return None


def find_hit(hitbox: Hitbox, hurtbox: Hurtbox) -> Optional[HitResult]:
    """Returns where the (swept) hitbox lands, or None.

    A strike that reaches the head or torso always counts as a head/torso
    hit, even if it grazed a guarding arm on the way in. Limb multipliers
    only apply when the strike touches nothing but limbs.
    """
    first_limb: Optional[HitResult] = None
    for p in hitbox.path_points():
        res = _test_point(p, hitbox.radius, hurtbox, hitbox.aim)
        if res is None:
            continue
        if res.region in ("head", "torso"):
            return res
        if first_limb is None:
            first_limb = res
    return first_limb


def check_hit(hitbox: Hitbox, hurtbox: Hurtbox) -> bool:
    """True if the (swept) hitbox touches any part of the hurtbox."""
    return find_hit(hitbox, hurtbox) is not None
