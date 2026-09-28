"""
Bold seamless line render style ("bold").

Presentation-only: it reads the same skeleton joints, animation clips and weapon
attachment points as every other style. The figure is drawn as ONE continuous
silhouette (all outlines first, then all fills in a single colour) with smooth
curves through the joints, so the body never looks segmented.

Extras: soft glow, top-edge highlight, and motion smear on strikes.
"""

from __future__ import annotations

import math
from collections import deque
from typing import Dict, List, Optional, Sequence, Tuple, TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from stickfight.engine.fighter import Fighter
    from stickfight.engine.camera import Camera
    from stickfight.engine.renderer import Renderer

Point = Tuple[float, float]
Color = Tuple[int, int, int]

# Each path is drawn as one smooth stroke. Order matters only for readability;
# every path uses the same colour so no internal seams appear.
BODY_PATHS: Tuple[Tuple[str, ...], ...] = (
    ("head", "neck", "chest", "pelvis"),
    ("pelvis", "left_hip", "left_knee", "left_foot"),
    ("pelvis", "right_hip", "right_knee", "right_foot"),
    ("neck", "left_shoulder", "left_elbow", "left_hand"),
    ("neck", "right_shoulder", "right_elbow", "right_hand"),
)

ARM_CHAIN = ("neck", "right_shoulder", "right_elbow", "right_hand")
LEG_CHAIN = ("pelvis", "right_hip", "right_knee", "right_foot")
TRAIL_JOINTS = ARM_CHAIN + LEG_CHAIN

ATTACK_ARM_CLIPS = {"punch", "uppercut", "slash", "jab", "cross", "hook"}
ATTACK_LEG_CLIPS = {"kick", "sweep", "low_kick"}

# (frames ago, alpha): older ghosts are fainter.
TRAIL_GHOSTS = ((6, 30), (4, 55), (2, 80))
TRAIL_HISTORY = 7

BASE_LINE_WIDTH = 16.0   # in rig units; scaled by fighter.scale * camera.zoom
OUTLINE_EXTRA = 6.0      # extra outline thickness (rig units * zoom)


def _shade(color: Sequence[int], factor: float) -> Color:
    return tuple(max(0, min(255, int(c * factor))) for c in color[:3])  # type: ignore[return-value]


def _lighten(color: Sequence[int], amount: float) -> Color:
    return tuple(int(c + (255 - c) * amount) for c in color[:3])  # type: ignore[return-value]


def _quad(p0: Point, c: Point, p1: Point, t: float) -> Point:
    u = 1.0 - t
    return (
        u * u * p0[0] + 2 * u * t * c[0] + t * t * p1[0],
        u * u * p0[1] + 2 * u * t * c[1] + t * t * p1[1],
    )


def _sample_path(pts: Sequence[Point], spacing: float) -> List[Point]:
    """Densely sample a smooth curve through the joints.

    Uses quadratic curves with each joint as a control point and segment
    midpoints as anchors, so bends at elbows, knees and shoulders are rounded.
    """
    if not pts:
        return []
    if len(pts) == 1:
        return [pts[0]]

    spacing = max(1.0, spacing)
    out: List[Point] = [pts[0]]
    cur = pts[0]

    for i in range(1, len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        end = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
        est = math.hypot(a[0] - cur[0], a[1] - cur[1]) + math.hypot(end[0] - a[0], end[1] - a[1])
        n = max(2, int(est / spacing))
        for k in range(1, n + 1):
            out.append(_quad(cur, a, end, k / n))
        cur = end

    last = pts[-1]
    n = max(1, int(math.hypot(last[0] - cur[0], last[1] - cur[1]) / spacing))
    for k in range(1, n + 1):
        t = k / n
        out.append((cur[0] + (last[0] - cur[0]) * t, cur[1] + (last[1] - cur[1]) * t))
    return out


def _stroke(surface: pygame.Surface, pts: Sequence[Point], color, width: float) -> None:
    """Round-capped smooth stroke, stamped as overlapping discs (no seams)."""
    radius = max(1, int(round(width / 2.0)))
    for x, y in _sample_path(pts, radius * 0.5):
        pygame.draw.circle(surface, color, (int(round(x)), int(round(y))), radius)


def _disc(surface: pygame.Surface, p: Point, radius: float, color) -> None:
    pygame.draw.circle(surface, color, (int(round(p[0])), int(round(p[1]))), max(1, int(round(radius))))


def _draw_glow(surface: pygame.Surface, paths: List[List[Point]], head: Optional[Point],
               head_r: float, color: Color, width: float, z: float) -> None:
    """Soft halo: draw the silhouette small, then smooth-scale it up (cheap blur)."""
    xs = [p[0] for path in paths for p in path]
    ys = [p[1] for path in paths for p in path]
    if not xs:
        return
    pad = int(width * 2.5 + head_r)
    ox, oy = int(min(xs)) - pad, int(min(ys)) - pad
    w, h = int(max(xs)) + pad - ox, int(max(ys)) + pad - oy
    if w < 8 or h < 8 or w * h > 4_000_000:
        return
    scale = 4
    small = pygame.Surface((max(1, w // scale), max(1, h // scale)), pygame.SRCALPHA)
    rgba = (color[0], color[1], color[2], 95)
    halo = (width + 12.0 * z) / scale
    for path in paths:
        _stroke(small, [((x - ox) / scale, (y - oy) / scale) for x, y in path], rgba, halo)
    if head is not None:
        _disc(small, ((head[0] - ox) / scale, (head[1] - oy) / scale), (head_r + 6.0 * z) / scale, rgba)
    big = pygame.transform.smoothscale(small, (small.get_width() * scale, small.get_height() * scale))
    surface.blit(big, (ox, oy))


def _draw_smear(renderer: "Renderer", surface: pygame.Surface, fighter: "Fighter",
                joints: Dict[str, Point], camera: "Camera", color: Color, width: float,
                clip: str, z: float) -> None:
    """Ghost copies of the striking limb from recent frames, plus speed lines."""
    trails = renderer.__dict__.setdefault("_bold_trails", {})
    hist: deque = trails.setdefault(id(fighter), deque(maxlen=TRAIL_HISTORY))
    hist.append({n: joints[n] for n in TRAIL_JOINTS if n in joints})

    if clip in ATTACK_ARM_CLIPS:
        chain = ARM_CHAIN
    elif clip in ATTACK_LEG_CLIPS:
        chain = LEG_CHAIN
    else:
        return

    for frames_ago, alpha in TRAIL_GHOSTS:
        if len(hist) <= frames_ago:
            continue
        snap = hist[-1 - frames_ago]
        if not all(n in snap for n in chain):
            continue
        pts = [camera.world_to_screen(snap[n][0], snap[n][1]) for n in chain]
        pad = int(width * 2)
        ox = int(min(p[0] for p in pts)) - pad
        oy = int(min(p[1] for p in pts)) - pad
        w = int(max(p[0] for p in pts)) + pad - ox
        h = int(max(p[1] for p in pts)) + pad - oy
        if w < 4 or h < 4 or w * h > 4_000_000:
            continue
        layer = pygame.Surface((w, h), pygame.SRCALPHA)
        _stroke(layer, [(x - ox, y - oy) for x, y in pts], (color[0], color[1], color[2], alpha), width)
        surface.blit(layer, (ox, oy))

    tip_name = chain[-1]
    if tip_name in joints:
        tx, ty = camera.world_to_screen(joints[tip_name][0], joints[tip_name][1])
        f = fighter.facing
        for i in range(3):
            y = ty + (i - 1) * 9 * z
            pygame.draw.line(
                surface, color,
                (tx - f * (22 + i * 8) * z, y),
                (tx - f * (46 + i * 8) * z, y),
                max(2, int(2 * z)),
            )


def _draw_headband(surface: pygame.Surface, fighter: "Fighter", head: Point, hr: int, z: float) -> None:
    hb = fighter.headband_color
    if not hb:
        return
    hx, hy = head
    pygame.draw.line(surface, hb, (hx - hr, hy - hr * 0.12), (hx + hr, hy - hr * 0.12), max(3, int(5 * z)))
    opp = -fighter.facing
    wave = math.sin(fighter.clip_time * 8.0) * 7.0 * z
    tail = (hx + opp * 48 * z + wave, hy + 18 * z)
    pygame.draw.line(surface, hb, (hx + opp * hr, hy), tail, max(2, int(4 * z)))
    pygame.draw.line(surface, hb, (hx + opp * hr, hy + 5 * z), (tail[0] + opp * 12 * z, tail[1] + 10 * z), max(2, int(3 * z)))


def _draw_weapon(surface: pygame.Surface, fighter: "Fighter", screen: Dict[str, Point], z: float, dark: Color) -> None:
    s = fighter.scale
    hand, elbow = screen.get("right_hand"), screen.get("right_elbow")
    if fighter.weapon == "sword" and hand and elbow:
        hx, hy = hand
        dx, dy = hx - elbow[0], hy - elbow[1]
        length = max(1e-4, math.hypot(dx, dy))
        ux, uy = dx / length, dy / length
        tip = (hx + ux * 105.0 * s * z, hy + uy * 105.0 * s * z)
        guard = 15.0 * z
        pygame.draw.line(surface, (225, 180, 55), (hx - uy * guard, hy + ux * guard), (hx + uy * guard, hy - ux * guard), max(2, int(4 * z)))
        pygame.draw.line(surface, dark, (hx, hy), tip, max(4, int(8 * z)))
        pygame.draw.line(surface, (235, 240, 250), (hx, hy), tip, max(2, int(5 * z)))
        pygame.draw.line(surface, (255, 255, 255), (hx, hy), tip, max(1, int(2 * z)))
    elif fighter.weapon == "staff" and hand:
        hx, hy = hand
        staff_len = 170.0 * s * z
        a = (hx - fighter.facing * 28 * z, hy - staff_len * 0.5)
        b = (hx + fighter.facing * 28 * z, hy + staff_len * 0.5)
        pygame.draw.line(surface, dark, a, b, max(5, int(9 * z)))
        pygame.draw.line(surface, (155, 105, 65), a, b, max(2, int(5 * z)))
        pygame.draw.circle(surface, (235, 190, 65), (int(a[0]), int(a[1])), max(2, int(4 * z)))
        pygame.draw.circle(surface, (235, 190, 65), (int(b[0]), int(b[1])), max(2, int(4 * z)))


def draw_bold_fighter(renderer: "Renderer", surface: pygame.Surface, fighter: "Fighter",
                      joints: Dict[str, Point], screen: Dict[str, Point], camera: "Camera") -> None:
    """Draw one fighter in the bold seamless style."""
    z = camera.zoom
    s = fighter.scale
    base = tuple(int(c) for c in fighter.color[:3])
    dark = _shade(base, 0.45)
    light = _lighten(base, 0.30)

    width = BASE_LINE_WIDTH * s * z
    outline_w = width + OUTLINE_EXTRA * z

    paths: List[List[Point]] = []
    for names in BODY_PATHS:
        pts = [screen[n] for n in names if n in screen]
        if len(pts) >= 2:
            paths.append(pts)

    head = screen.get("head")
    hr = max(5, int(fighter.head_radius * z))
    clip = getattr(getattr(fighter, "active_clip", None), "name", "")

    _draw_smear(renderer, surface, fighter, joints, camera, base, width, clip, z)
    _draw_glow(surface, paths, head, hr, base, width, z)

    # Pass 1: every outline, so overlapping parts never draw a border across each other.
    for pts in paths:
        _stroke(surface, pts, dark, outline_w)
    if head:
        _disc(surface, head, hr + OUTLINE_EXTRA * z / 2.0, dark)

    # Pass 2: every fill in one colour, giving a single continuous silhouette.
    for pts in paths:
        _stroke(surface, pts, base, width)
    if head:
        _disc(surface, head, hr, base)

    # Pass 3: top-edge highlight so the line reads as a rounded tube.
    off = 2.0 * z
    for pts in paths:
        _stroke(surface, [(x - off, y - off) for x, y in pts], light, max(2.0, 2.5 * z))
    if head:
        rect = pygame.Rect(0, 0, 0, 0)
        inner = max(2, hr - int(4 * z))
        rect.size = (inner * 2, inner * 2)
        rect.center = (int(head[0]), int(head[1]))
        pygame.draw.arc(surface, light, rect, 1.9, 2.7, max(2, int(2.5 * z)))
        _draw_headband(surface, fighter, head, hr, z)

    _draw_weapon(surface, fighter, screen, z, dark)
