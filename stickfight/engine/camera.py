"""
Camera system: dynamic tracking, auto-framing, zoom, pan, and screen shake.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple, List, Optional
import math
import random


class Camera:
    def __init__(self, viewport_width: int = 1080, viewport_height: int = 1920):
        self.width = viewport_width
        self.height = viewport_height

        self.x: float = viewport_width / 2.0
        self.y: float = 1250.0  # Focus slightly above ground (y=1500)
        self.zoom: float = 1.0

        self.target_x: float = self.x
        self.target_y: float = self.y
        self.target_zoom: float = 1.0

        # Camera Shake
        self.shake_intensity: float = 0.0
        self.shake_timer: float = 0.0
        self.shake_offset_x: float = 0.0
        self.shake_offset_y: float = 0.0

        # Tracking bounds
        self.min_zoom: float = 0.9
        self.max_zoom: float = 2.0

    def shake(self, intensity: float = 12.0, duration: float = 0.25):
        """Triggers a camera shake effect."""
        self.shake_intensity = max(self.shake_intensity, intensity)
        self.shake_timer = max(self.shake_timer, duration)

    def set_target(self, x: float, y: float, zoom: Optional[float] = None):
        self.target_x = x
        self.target_y = y
        if zoom is not None:
            self.target_zoom = max(self.min_zoom, min(self.max_zoom, zoom))

    def frame_fighters(self, fighters: List, padding: float = 280.0):
        """Automatically centers on and dynamically frames all active fighters."""
        if not fighters:
            return

        xs = [f.x for f in fighters]
        # Frame torso/upper body height
        ys = [f.y - 140.0 * getattr(f, "scale", 1.0) for f in fighters]

        center_x = sum(xs) / len(xs)
        center_y = sum(ys) / len(ys)

        span_x = max(xs) - min(xs) + padding
        span_y = max(ys) - min(ys) + padding

        # Calculate desired zoom so fighters occupy a prominent portion of vertical frame
        zoom_x = (self.width * 0.82) / max(span_x, 320.0)
        zoom_y = (self.height * 0.48) / max(span_y, 420.0)
        desired_zoom = min(zoom_x, zoom_y)
        desired_zoom = max(self.min_zoom, min(self.max_zoom, desired_zoom))

        self.set_target(center_x, center_y, desired_zoom)

    def update(self, dt: float):
        # Smooth camera movement lerp
        smoothing = 6.0
        t = 1.0 - math.exp(-smoothing * dt)
        self.x += (self.target_x - self.x) * t
        self.y += (self.target_y - self.y) * t
        self.zoom += (self.target_zoom - self.zoom) * t

        # Update screen shake
        if self.shake_timer > 0:
            self.shake_timer -= dt
            decay = max(0.0, self.shake_timer)
            mag = self.shake_intensity * (decay / 0.25 if decay < 0.25 else 1.0)
            angle = random.uniform(0, 2 * math.pi)
            self.shake_offset_x = math.cos(angle) * mag
            self.shake_offset_y = math.sin(angle) * mag
            if self.shake_timer <= 0:
                self.shake_intensity = 0.0
                self.shake_offset_x = 0.0
                self.shake_offset_y = 0.0
        else:
            self.shake_offset_x = 0.0
            self.shake_offset_y = 0.0

    def world_to_screen(self, wx: float, wy: float) -> Tuple[float, float]:
        """Converts world space coordinates into screen space pixels."""
        # Screen center
        cx = self.width / 2.0
        cy = self.height / 2.0

        # Transform
        sx = cx + (wx - self.x) * self.zoom + self.shake_offset_x
        sy = cy + (wy - self.y) * self.zoom + self.shake_offset_y
        return sx, sy
