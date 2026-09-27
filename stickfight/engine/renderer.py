"""
Renderer: stick figure geometry rasterizer, environment backgrounds,
text captions, and headless frame encoding to MP4 via FFmpeg.
"""

from __future__ import annotations
import os
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
        """Renders dynamic environment background and ground plane."""
        # Sky / Back wall
        if style == "plain" or style == "dark":
            surface.fill((18, 18, 22))
        elif style == "dojo":
            surface.fill((30, 24, 20))
            # Background sliding screen lines
            for x_line in range(-2000, 4000, 280):
                sx1, sy1 = camera.world_to_screen(x_line, 200)
                sx2, sy2 = camera.world_to_screen(x_line, ground_y)
                pygame.draw.line(surface, (45, 36, 30), (sx1, sy1), (sx2, sy2), 2)
        elif style == "grid":
            surface.fill((10, 10, 20))
            # Perspective floor grid
            for x_line in range(-2000, 4000, 200):
                sx1, sy1 = camera.world_to_screen(x_line, ground_y)
                sx2, sy2 = camera.world_to_screen(x_line, ground_y + 800)
                pygame.draw.line(surface, (30, 45, 80), (sx1, sy1), (sx2, sy2), 1)
        else:
            surface.fill((20, 20, 24))

        # Ground Plane & Baseline
        gx1, gy1 = camera.world_to_screen(-3000, ground_y)
        gx2, gy2 = camera.world_to_screen(5000, ground_y)

        # Ground fill under floor
        ground_rect = pygame.Rect(0, int(gy1), self.width, self.height - int(gy1) + 20)
        floor_color = (25, 25, 32) if style != "dojo" else (48, 38, 28)
        surface.fill(floor_color, ground_rect)

        # Crisp ground boundary line
        line_color = (210, 215, 225) if style != "dojo" else (160, 120, 80)
        pygame.draw.line(surface, line_color, (gx1, gy1), (gx2, gy2), max(2, int(4 * camera.zoom)))

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
        """Draws a stick fighter with antialiased joint capsules and head."""
        self.draw_fighter_shadow(surface, fighter, camera)

        joints = fighter.get_world_joints()
        screen_joints: Dict[str, Tuple[float, float]] = {}
        for name, pt in joints.items():
            screen_joints[name] = camera.world_to_screen(pt[0], pt[1])

        z = camera.zoom
        stroke_width = max(2, int(fighter.line_width * fighter.scale * z))
        joint_radius = max(2, stroke_width // 2)

        def draw_segment(j1_name: str, j2_name: str, color: Tuple[int, int, int]):
            if j1_name in screen_joints and j2_name in screen_joints:
                p1 = screen_joints[j1_name]
                p2 = screen_joints[j2_name]
                pygame.draw.line(surface, color, p1, p2, stroke_width)
                pygame.draw.circle(surface, color, (int(p1[0]), int(p1[1])), joint_radius)
                pygame.draw.circle(surface, color, (int(p2[0]), int(p2[1])), joint_radius)

        base_color = fighter.color
        # Slightly darker shade for back limbs to provide visual depth
        back_color = (
            max(0, int(base_color[0] * 0.75)),
            max(0, int(base_color[1] * 0.75)),
            max(0, int(base_color[2] * 0.75)),
        )

        # 1. Back leg
        draw_segment("left_hip", "left_knee", back_color)
        draw_segment("left_knee", "left_foot", back_color)

        # 2. Back arm
        draw_segment("neck", "left_shoulder", back_color)
        draw_segment("left_shoulder", "left_elbow", back_color)
        draw_segment("left_elbow", "left_hand", back_color)

        # 3. Torso (pelvis to neck)
        draw_segment("pelvis", "chest", base_color)
        draw_segment("chest", "neck", base_color)

        # 4. Front leg
        draw_segment("right_hip", "right_knee", base_color)
        draw_segment("right_knee", "right_foot", base_color)

        # 5. Front arm
        draw_segment("neck", "right_shoulder", base_color)
        draw_segment("right_shoulder", "right_elbow", base_color)
        draw_segment("right_elbow", "right_hand", base_color)

        # 6. Head
        if "head" in screen_joints:
            hx, hy = screen_joints["head"]
            hr = max(4, int(fighter.head_radius * z))
            pygame.draw.circle(surface, base_color, (int(hx), int(hy)), hr)
            # Neck connector
            if "neck" in screen_joints:
                nx, ny = screen_joints["neck"]
                pygame.draw.line(surface, base_color, (hx, hy), (nx, ny), stroke_width)

            # Directional eye dot
            eye_x = int(hx + fighter.facing * hr * 0.42)
            eye_y = int(hy - hr * 0.12)
            eye_r = max(2, int(hr * 0.22))
            pygame.draw.circle(surface, (255, 255, 255), (eye_x, eye_y), eye_r)
            pupil_r = max(1, eye_r // 2)
            pygame.draw.circle(surface, (20, 20, 26), (eye_x + fighter.facing * 1, eye_y), pupil_r)

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
