"""
Renderer: stick figure geometry rasterizer, environment backgrounds,
text captions, and headless frame encoding to MP4 via FFmpeg.
"""

from __future__ import annotations
import os
import math
import subprocess
from typing import Dict, Tuple, List, Optional, TYPE_CHECKING
import pygame

if TYPE_CHECKING:
    from stickfight.engine.fighter import Fighter
    from stickfight.engine.camera import Camera
    from stickfight.engine.effects import EffectsManager


class Renderer:
    def __init__(self, width: int = 1080, height: int = 1920):
        self.width = width
        self.height = height
        self._font: Optional[pygame.font.Font] = None
        self._title_font: Optional[pygame.font.Font] = None

    def _ensure_fonts(self):
        if self._font is None:
            if not pygame.font.get_init():
                pygame.font.init()
            self._font = pygame.font.Font(None, 36)
            self._title_font = pygame.font.Font(None, 56)

    def draw_background(self, surface: pygame.Surface, style: str, camera: Camera, ground_y: float = 1500.0):
        """Renders dynamic environment background, architecture, and ground plane."""
        z = camera.zoom
        # Ground level on screen
        gx_dummy, gy_screen = camera.world_to_screen(0, ground_y)

        if style == "dojo":
            # Warm wooden martial arts temple
            surface.fill((28, 22, 18))
            # Large circular background crest / rising sun disc
            cx, cy = camera.world_to_screen(self.width / 2, ground_y - 500)
            sun_r = int(220 * z)
            if sun_r > 10:
                sun_surf = pygame.Surface((sun_r * 2 + 4, sun_r * 2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(sun_surf, (180, 50, 40, 110), (sun_r + 2, sun_r + 2), sun_r)
                surface.blit(sun_surf, (cx - sun_r - 2, cy - sun_r - 2))

            # Shoji screens & vertical pillars
            for x_line in range(-2500, 4500, 260):
                sx1, sy1 = camera.world_to_screen(x_line, -500)
                sx2, sy2 = camera.world_to_screen(x_line, ground_y)
                # Wood pillar
                pygame.draw.line(surface, (45, 34, 26), (sx1, sy1), (sx2, sy2), max(2, int(8 * z)))
                # Inner paper lattice crossbeams
                for y_grid in range(200, int(ground_y), 180):
                    px1, py1 = camera.world_to_screen(x_line - 130, y_grid)
                    px2, py2 = camera.world_to_screen(x_line + 130, y_grid)
                    pygame.draw.line(surface, (38, 28, 22), (px1, py1), (px2, py2), 2)

            # Polished wooden floor
            ground_rect = pygame.Rect(0, int(gy_screen), self.width, self.height - int(gy_screen) + 50)
            surface.fill((44, 32, 24), ground_rect)
            # Floorboard plank seams
            for seam_y in range(int(ground_y) + 60, int(ground_y) + 900, 70):
                bx1, by1 = camera.world_to_screen(-3000, seam_y)
                bx2, by2 = camera.world_to_screen(5000, seam_y)
                pygame.draw.line(surface, (32, 22, 16), (bx1, by1), (bx2, by2), 2)

            # Ground boundary
            gx1, gy1 = camera.world_to_screen(-3000, ground_y)
            gx2, gy2 = camera.world_to_screen(5000, ground_y)
            pygame.draw.line(surface, (210, 165, 80), (gx1, gy1), (gx2, gy2), max(3, int(6 * z)))

        elif style == "city" or style == "street":
            # Night city skyline
            surface.fill((12, 14, 24))
            # Distant moon
            mx, my = camera.world_to_screen(250, 400)
            moon_r = int(55 * z)
            if moon_r > 5:
                moon_surf = pygame.Surface((moon_r * 2 + 4, moon_r * 2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(moon_surf, (240, 245, 255, 180), (moon_r + 2, moon_r + 2), moon_r)
                surface.blit(moon_surf, (mx - moon_r, my - moon_r))

            # Skyscraper silhouettes
            buildings = [
                (-800, 350, 260), (-500, 200, 320), (-120, 280, 280),
                (200, 180, 340), (600, 300, 250), (900, 220, 310), (1300, 260, 290)
            ]
            for bx, b_top, b_w in buildings:
                sx, sy = camera.world_to_screen(bx, b_top)
                sw = int(b_w * z)
                sh = int((ground_y - b_top) * z)
                pygame.draw.rect(surface, (20, 24, 38), (int(sx), int(sy), sw, sh))
                # Window lights
                for wy in range(int(b_top) + 40, int(ground_y) - 60, 50):
                    for wx in range(bx + 30, bx + b_w - 30, 40):
                        if (wx * 17 + wy * 31) % 5 == 0:
                            wsx, wsy = camera.world_to_screen(wx, wy)
                            pygame.draw.rect(surface, (255, 230, 110), (int(wsx), int(wsy), max(2, int(8 * z)), max(2, int(12 * z))))

            # Asphalt road floor
            ground_rect = pygame.Rect(0, int(gy_screen), self.width, self.height - int(gy_screen) + 50)
            surface.fill((25, 27, 34), ground_rect)

            # Dashed yellow centerline
            for dash_x in range(-2500, 4500, 160):
                dx1, dy1 = camera.world_to_screen(dash_x, ground_y + 110)
                dx2, dy2 = camera.world_to_screen(dash_x + 90, ground_y + 110)
                pygame.draw.line(surface, (235, 195, 45), (dx1, dy1), (dx2, dy2), max(2, int(5 * z)))

            # Curb line
            gx1, gy1 = camera.world_to_screen(-3000, ground_y)
            gx2, gy2 = camera.world_to_screen(5000, ground_y)
            pygame.draw.line(surface, (200, 205, 215), (gx1, gy1), (gx2, gy2), max(3, int(5 * z)))

        elif style == "cyberpunk" or style == "grid":
            # Neon synthwave digital arena
            surface.fill((14, 10, 26))
            # Neon horizon glow
            gx1, gy1 = camera.world_to_screen(-3000, ground_y)
            gx2, gy2 = camera.world_to_screen(5000, ground_y)

            # Perspective floor grid
            for x_line in range(-2000, 4000, 180):
                sx1, sy1 = camera.world_to_screen(x_line, ground_y)
                sx2, sy2 = camera.world_to_screen(x_line * 1.5, ground_y + 900)
                pygame.draw.line(surface, (60, 200, 255), (sx1, sy1), (sx2, sy2), 1)

            for y_line in range(int(ground_y) + 40, int(ground_y) + 900, 70):
                bx1, by1 = camera.world_to_screen(-3000, y_line)
                bx2, by2 = camera.world_to_screen(5000, y_line)
                pygame.draw.line(surface, (240, 50, 180), (bx1, by1), (bx2, by2), 1)

            # Glowing neon ground line
            pygame.draw.line(surface, (60, 220, 255), (gx1, gy1), (gx2, gy2), max(4, int(7 * z)))

        else:
            # Plain / Dark minimalist aesthetic
            surface.fill((18, 18, 22))
            ground_rect = pygame.Rect(0, int(gy_screen), self.width, self.height - int(gy_screen) + 50)
            surface.fill((26, 26, 32), ground_rect)
            gx1, gy1 = camera.world_to_screen(-3000, ground_y)
            gx2, gy2 = camera.world_to_screen(5000, ground_y)
            pygame.draw.line(surface, (215, 220, 230), (gx1, gy1), (gx2, gy2), max(2, int(4 * z)))

    def draw_fighter_shadow(self, surface: pygame.Surface, fighter: Fighter, camera: Camera):
        """Draws subtle ground contact shadow."""
        sx, sy = camera.world_to_screen(fighter.x, fighter.y)
        rx = int(45 * fighter.scale * camera.zoom)
        ry = int(14 * fighter.scale * camera.zoom)
        if rx > 2 and ry > 1:
            shadow_surf = pygame.Surface((rx * 2 + 4, ry * 2 + 4), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow_surf, (0, 0, 0, 80), (2, 2, rx * 2, ry * 2))
            surface.blit(shadow_surf, (sx - rx - 2, sy - ry - 2))

    def draw_fighter(self, surface: pygame.Surface, fighter: Fighter, camera: Camera):
        """Draws a stylized fighter from the animation skeleton.

        The renderer is deliberately style-driven: choreography, physics, collision,
        and animation remain unchanged while the same joints can produce different
        visual identities.
        """
        self.draw_fighter_shadow(surface, fighter, camera)

        joints = fighter.get_world_joints()
        screen_joints: Dict[str, Tuple[float, float]] = {
            name: camera.world_to_screen(pt[0], pt[1])
            for name, pt in joints.items()
        }

        z = camera.zoom
        s = fighter.scale
        style = getattr(fighter, "render_style", "segmented")
        base = fighter.color

        def shade(color: Tuple[int, int, int], factor: float) -> Tuple[int, int, int]:
            return tuple(max(0, min(255, int(c * factor))) for c in color)

        dark = shade(base, 0.42)
        mid = shade(base, 0.72)
        light = tuple(min(255, int(c * 1.15 + 12)) for c in base)

        def point(name: str):
            return screen_joints.get(name)

        def limb(a: str, b: str, color: Tuple[int, int, int], width: int, outline: bool = True):
            p1, p2 = point(a), point(b)
            if not p1 or not p2:
                return
            w = max(2, int(width * s * z))
            if outline:
                ow = w + max(2, int(5 * z))
                pygame.draw.line(surface, dark, p1, p2, ow)
                r = max(2, ow // 2)
                pygame.draw.circle(surface, dark, (int(p1[0]), int(p1[1])), r)
                pygame.draw.circle(surface, dark, (int(p2[0]), int(p2[1])), r)
            pygame.draw.line(surface, color, p1, p2, w)
            r = max(2, w // 2)
            pygame.draw.circle(surface, color, (int(p1[0]), int(p1[1])), r)
            pygame.draw.circle(surface, color, (int(p2[0]), int(p2[1])), r)

        def joint(name: str, radius: float, color: Tuple[int, int, int] = base):
            p = point(name)
            if not p:
                return
            r = max(2, int(radius * s * z))
            pygame.draw.circle(surface, dark, (int(p[0]), int(p[1])), r + max(2, int(3 * z)))
            pygame.draw.circle(surface, color, (int(p[0]), int(p[1])), r)

        def torso():
            pelvis, chest, neck = point("pelvis"), point("chest"), point("neck")
            if not pelvis or not chest or not neck:
                return
            px, py = pelvis
            cx, cy = chest
            nx, ny = neck
            # A tapered torso gives the character an actual body silhouette.
            vx, vy = nx - py * 0 + nx - cx, ny - cy
            length = max(1.0, math.hypot(vx, vy))
            pxn, pyn = -vy / length, vx / length
            top_w = 15 * s * z
            bot_w = 20 * s * z
            poly = [
                (cx + pxn * top_w, cy + pyn * top_w),
                (cx - pxn * top_w, cy - pyn * top_w),
                (px - pxn * bot_w, py - pyn * bot_w),
                (px + pxn * bot_w, py + pyn * bot_w),
            ]
            pygame.draw.polygon(surface, dark, [(int(x), int(y)) for x, y in poly])
            inset = max(1, int(3 * z))
            poly2 = [
                (cx + pxn * max(1, top_w - inset), cy + pyn * max(1, top_w - inset)),
                (cx - pxn * max(1, top_w - inset), cy - pyn * max(1, top_w - inset)),
                (px - pxn * max(1, bot_w - inset), py - pyn * max(1, bot_w - inset)),
                (px + pxn * max(1, bot_w - inset), py + pyn * max(1, bot_w - inset)),
            ]
            pygame.draw.polygon(surface, base, [(int(x), int(y)) for x, y in poly2])

        # Back limbs first creates readable depth.
        limb("left_hip", "left_knee", mid, 13 if style != "classic" else 7)
        limb("left_knee", "left_foot", mid, 13 if style != "classic" else 7)
        limb("neck", "left_shoulder", mid, 12 if style != "classic" else 7)
        limb("left_shoulder", "left_elbow", mid, 13 if style != "classic" else 7)
        limb("left_elbow", "left_hand", mid, 13 if style != "classic" else 7)

        if style != "classic":
            torso()

        # Front limbs.
        limb("right_hip", "right_knee", base, 15 if style != "classic" else 8)
        limb("right_knee", "right_foot", base, 15 if style != "classic" else 8)
        limb("neck", "right_shoulder", base, 14 if style != "classic" else 8)
        limb("right_shoulder", "right_elbow", base, 15 if style != "classic" else 8)
        limb("right_elbow", "right_hand", base, 15 if style != "classic" else 8)

        # Hands/feet read as intentional combat extremities rather than line endpoints.
        joint("left_hand", 8 if style != "classic" else 5, mid)
        joint("right_hand", 9 if style != "classic" else 5, base)
        joint("left_foot", 9 if style != "classic" else 5, mid)
        joint("right_foot", 10 if style != "classic" else 5, base)

        # Head: silhouette/segmented styles use a stronger graphic shape.
        hp = point("head")
        if hp:
            hx, hy = hp
            hr = max(5, int(fighter.head_radius * z))
            if style == "silhouette":
                pygame.draw.circle(surface, dark, (int(hx), int(hy)), hr + max(2, int(3 * z)))
                pygame.draw.circle(surface, base, (int(hx), int(hy)), hr)
                # Single directional eye slit.
                eye_x = int(hx + fighter.facing * hr * 0.42)
                pygame.draw.line(
                    surface, light,
                    (eye_x - fighter.facing * hr * 0.08, int(hy - hr * 0.12)),
                    (eye_x + fighter.facing * hr * 0.18, int(hy - hr * 0.12)),
                    max(2, int(3 * z)),
                )
            else:
                pygame.draw.circle(surface, dark, (int(hx), int(hy)), hr + max(2, int(3 * z)))
                pygame.draw.circle(surface, base, (int(hx), int(hy)), hr)
                eye_x = int(hx + fighter.facing * hr * 0.42)
                eye_y = int(hy - hr * 0.10)
                eye_r = max(2, int(hr * 0.20))
                pygame.draw.circle(surface, (255, 255, 255), (eye_x, eye_y), eye_r)
                pygame.draw.circle(surface, (18, 18, 24), (eye_x + fighter.facing, eye_y), max(1, eye_r // 2))

            # Neck is rendered after the head so it visually connects to the torso.
            np = point("neck")
            if np:
                pygame.draw.line(surface, dark, (hx, hy + hr * 0.55), np, max(3, int(11 * s * z)))
                pygame.draw.line(surface, base, (hx, hy + hr * 0.55), np, max(2, int(7 * s * z)))

        # Style-specific identity details.
        if style in ("silhouette", "segmented") and fighter.headband_color:
            hb = fighter.headband_color
            if hp:
                hx, hy = hp
                hr = max(5, int(fighter.head_radius * z))
                pygame.draw.line(surface, hb,
                    (hx - hr, hy - hr * 0.12),
                    (hx + hr, hy - hr * 0.12),
                    max(3, int(5 * z)))
                opp = -fighter.facing
                wave = math.sin(fighter.clip_time * 8.0) * 7.0 * z
                tail = (hx + opp * 48 * z + wave, hy + 18 * z)
                pygame.draw.line(surface, hb, (hx + opp * hr, hy), tail, max(2, int(4 * z)))
                pygame.draw.line(surface, hb, (hx + opp * hr, hy + 5 * z),
                    (tail[0] + opp * 12 * z, tail[1] + 10 * z), max(2, int(3 * z)))

        if style == "tech":
            # Compact cyan/white mechanical accents for cybernetic fighters.
            for name in ("chest", "right_elbow", "right_knee"):
                p = point(name)
                if p:
                    pygame.draw.circle(surface, light, (int(p[0]), int(p[1])), max(2, int(4 * z)))
            if point("chest") and point("neck"):
                pygame.draw.line(surface, light, point("chest"), point("neck"), max(1, int(2 * z)))

        # Weapon rendering remains compatible with the existing combat system.
        if fighter.weapon == "sword" and point("right_hand") and point("right_elbow"):
            hx, hy = point("right_hand")
            ex, ey = point("right_elbow")
            dx, dy = hx - ex, hy - ey
            length = max(1e-4, math.hypot(dx, dy))
            ux, uy = dx / length, dy / length
            blade_len = 105.0 * s * z
            tip = (hx + ux * blade_len, hy + uy * blade_len)
            guard = 15.0 * z
            pygame.draw.line(surface, (225, 180, 55),
                (hx - uy * guard, hy + ux * guard),
                (hx + uy * guard, hy - ux * guard), max(2, int(4 * z)))
            pygame.draw.line(surface, dark, (hx, hy), tip, max(4, int(8 * z)))
            pygame.draw.line(surface, (235, 240, 250), (hx, hy), tip, max(2, int(5 * z)))
            pygame.draw.line(surface, (255, 255, 255), (hx, hy), tip, max(1, int(2 * z)))

        elif fighter.weapon == "staff" and point("right_hand"):
            hx, hy = point("right_hand")
            staff_len = 170.0 * s * z
            a = (hx - fighter.facing * 28 * z, hy - staff_len * 0.5)
            b = (hx + fighter.facing * 28 * z, hy + staff_len * 0.5)
            pygame.draw.line(surface, dark, a, b, max(5, int(9 * z)))
            pygame.draw.line(surface, (155, 105, 65), a, b, max(2, int(5 * z)))
            pygame.draw.circle(surface, (235, 190, 65), (int(a[0]), int(a[1])), max(2, int(4 * z)))
            pygame.draw.circle(surface, (235, 190, 65), (int(b[0]), int(b[1])), max(2, int(4 * z)))

    def draw_captions(self, surface: pygame.Surface, captions: List[Tuple[str, float, float]], current_time: float):
        """Renders active captions at the bottom or top of screen."""
        self._ensure_fonts()
        for text, start_t, end_t in captions:
            if start_t <= current_time <= end_t:
                rendered = self._title_font.render(text, True, (255, 255, 255))
                rect = rendered.get_rect(center=(self.width // 2, 280))
                # Background banner
                pad_x, pad_y = 20, 10
                bg_rect = rect.inflate(pad_x * 2, pad_y * 2)
                bg_surf = pygame.Surface(bg_rect.size, pygame.SRCALPHA)
                bg_surf.fill((0, 0, 0, 140))
                surface.blit(bg_surf, bg_rect.topleft)
                surface.blit(rendered, rect)

    def draw_health_bars(self, surface: pygame.Surface, fighters: List[Fighter]):
        """Renders stylized top fighting game health bars."""
        if len(fighters) < 2:
            return
        self._ensure_fonts()
        f1, f2 = fighters[0], fighters[1]

        bar_w = 380
        bar_h = 24
        y_top = 80

        # Fighter 1 (Left)
        p1 = max(0.0, f1.health / max(1.0, f1.max_health))
        pygame.draw.rect(surface, (60, 60, 70), (60, y_top, bar_w, bar_h), border_radius=4)
        pygame.draw.rect(surface, (230, 60, 60), (60 + int(bar_w * (1 - p1)), y_top, int(bar_w * p1), bar_h), border_radius=4)
        lbl1 = self._font.render(f1.name, True, (240, 240, 240))
        surface.blit(lbl1, (60, y_top - 38))

        # Fighter 2 (Right)
        p2 = max(0.0, f2.health / max(1.0, f2.max_health))
        x2 = self.width - 60 - bar_w
        pygame.draw.rect(surface, (60, 60, 70), (x2, y_top, bar_w, bar_h), border_radius=4)
        pygame.draw.rect(surface, (60, 160, 240), (x2, y_top, int(bar_w * p2), bar_h), border_radius=4)
        lbl2 = self._font.render(f2.name, True, (240, 240, 240))
        surface.blit(lbl2, (self.width - 60 - lbl2.get_width(), y_top - 38))


class VideoExporter:
    """Encodes rendered frames and synchronized audio into MP4 using FFmpeg pipe."""
    def __init__(self, output_path: str, width: int = 1080, height: int = 1920, fps: int = 30, audio_path: Optional[str] = None):
        self.output_path = output_path
        self.width = width
        self.height = height
        self.fps = fps
        self.audio_path = audio_path
        self.process: Optional[subprocess.Popen] = None

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    def start(self):
        cmd = [
            "ffmpeg",
            "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{self.width}x{self.height}",
            "-pix_fmt", "rgb24",
            "-r", str(self.fps),
            "-i", "-",
        ]

        if self.audio_path and os.path.exists(self.audio_path):
            cmd.extend([
                "-i", self.audio_path,
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
            ])

        cmd.extend([
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            self.output_path
        ])

        self.process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    def write_frame(self, surface: pygame.Surface):
        if self.process and self.process.stdin:
            frame_bytes = pygame.image.tobytes(surface, "RGB")
            self.process.stdin.write(frame_bytes)

    def finish(self) -> int:
        if self.process:
            if self.process.stdin:
                self.process.stdin.close()
            stderr_out = self.process.stderr.read() if self.process.stderr else b""
            ret = self.process.wait()
            if ret != 0:
                print(f"[FFmpeg Error]: {stderr_out.decode('utf-8', errors='ignore')}")
            return ret
        return -1
