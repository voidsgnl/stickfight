"""
Physics simulation for stick fighters: gravity, velocities, ground constraints, and knockback dynamics.
"""

from __future__ import annotations
from dataclasses import dataclass
import math


@dataclass
class PhysicsBody:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    ax: float = 0.0
    ay: float = 0.0
    ground_y: float = 1500.0
    gravity: float = 1800.0
    friction: float = 8.0
    is_grounded: bool = True

    def apply_force(self, fx: float, fy: float):
        self.ax += fx
        self.ay += fy

    def apply_impulse(self, ix: float, iy: float):
        self.vx += ix
        self.vy += iy
        if iy < 0:
            self.is_grounded = False

    def update(self, dt: float):
        if not self.is_grounded:
            self.vy += self.gravity * dt

        self.vx += self.ax * dt
        self.vy += self.ay * dt

        # Apply ground friction if grounded
        if self.is_grounded:
            # Exponential damping is frame-rate independent (unlike 1 - k*dt,
            # which goes wrong at large timesteps).
            self.vx *= math.exp(-self.friction * dt)

        self.x += self.vx * dt
        self.y += self.vy * dt

        # Ground collision
        if self.y >= self.ground_y:
            self.y = self.ground_y
            self.vy = 0.0
            self.is_grounded = True

        # Reset frame accelerations
        self.ax = 0.0
        self.ay = 0.0
