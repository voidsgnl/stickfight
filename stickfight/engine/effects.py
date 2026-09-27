"""
Visual effects system: hit sparks, shockwaves, dust bursts, flash frames, and impact text.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple
import math
import random
import pygame


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: Tuple[int, int, int]
    radius: float
    life: float
    max_life: float

    @property
    def is_alive(self) -> bool:
        return self.life > 0.0

    def update(self, dt: float):
        self.life -= dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 300.0 * dt  # subtle gravity on sparks/dust
        self.vx *= max(0.0, 1.0 - 2.0 * dt)


@dataclass
class Shockwave:
    x: float
    y: float
    current_radius: float = 5.0
    max_radius: float = 65.0
    color: Tuple[int, int, int] = (255, 255, 255)
    life: float = 0.25
    max_life: float = 0.25

    @property
    def is_alive(self) -> bool:
        return self.life > 0.0

    def update(self, dt: float):
        self.life -= dt
        progress = 1.0 - max(0.0, self.life / self.max_life)
        self.current_radius = 5.0 + (self.max_radius - 5.0) * progress


@dataclass
class ImpactText:
    text: str
    x: float
    y: float
    color: Tuple[int, int, int] = (255, 220, 60)
    life: float = 0.4
    max_life: float = 0.4
    scale: float = 1.0

    @property
    def is_alive(self) -> bool:
        return self.life > 0.0

    def update(self, dt: float):
        self.life -= dt
        self.y -= 25.0 * dt  # float upwards


@dataclass
class SlashArc:
    x: float
    y: float
    radius: float
    start_angle: float
    end_angle: float
    color: Tuple[int, int, int] = (240, 245, 255)
    life: float = 0.18
    max_life: float = 0.18
    width: int = 6

    @property
    def is_alive(self) -> bool:
        return self.life > 0.0

    def update(self, dt: float):
        self.life -= dt


class EffectsManager:
    def __init__(self):
        self.particles: List[Particle] = []
        self.shockwaves: List[Shockwave] = []
        self.impact_texts: List[ImpactText] = []
        self.slash_arcs: List[SlashArc] = []
        self.flash_alpha: float = 0.0
        self.flash_color: Tuple[int, int, int] = (255, 255, 255)

    def trigger_slash_arc(self, x: float, y: float, start_angle: float, end_angle: float, radius: float = 120.0, color: Tuple[int, int, int] = (240, 245, 255)):
        """Adds a glowing curved blade slash trail."""
        self.slash_arcs.append(SlashArc(
            x=x, y=y, radius=radius, start_angle=start_angle, end_angle=end_angle, color=color
        ))

    def trigger_weapon_clash(self, x: float, y: float):
        """Weapon on weapon clash with high-density steel sparks."""
        self.shockwaves.append(Shockwave(x=x, y=y, max_radius=75.0, color=(255, 255, 220)))
        for _ in range(28):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(220, 550)
            self.particles.append(Particle(
                x=x,
                y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                color=(255, 245, 140),
                radius=random.uniform(2.5, 5.5),
                life=random.uniform(0.18, 0.4),
                max_life=0.4
            ))
        self.flash_alpha = 95.0
        self.impact_texts.append(ImpactText(text="CLANG!", x=x, y=y - 45.0, color=(255, 240, 100)))

    def trigger_hit_effect(self, x: float, y: float, is_blocked: bool = False, is_heavy: bool = False):
        """Spawns particles, shockwave, and flash for an impact."""
        # 1. Shockwave
        ring_color = (180, 220, 255) if is_blocked else (255, 240, 150)
        self.shockwaves.append(Shockwave(x=x, y=y, max_radius=85.0 if is_heavy else 55.0, color=ring_color))

        # 2. Sparks
        spark_count = 12 if is_blocked else (24 if is_heavy else 16)
        spark_color = (100, 200, 255) if is_blocked else (255, 220, 60)
        for _ in range(spark_count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(150, 450 if is_heavy else 300)
            self.particles.append(Particle(
                x=x,
                y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                color=spark_color,
                radius=random.uniform(2.5, 5.0),
                life=random.uniform(0.15, 0.35),
                max_life=0.35
            ))

        # 3. Flash
        if is_heavy:
            self.flash_alpha = 110.0
        elif not is_blocked:
            self.flash_alpha = 50.0

        # 4. Comic impact popup text
        text_label = "BLOCKED!" if is_blocked else ("CRACK!" if is_heavy else "POW!")
        text_col = (130, 210, 255) if is_blocked else ((255, 230, 70) if is_heavy else (255, 170, 60))
        self.impact_texts.append(ImpactText(text=text_label, x=x, y=y - 45.0, color=text_col))

    def trigger_dust_puff(self, x: float, y: float, count: int = 10):
        """Spawns dust particles near the ground."""
        for _ in range(count):
            vx = random.uniform(-120, 120)
            vy = random.uniform(-60, -10)
            self.particles.append(Particle(
                x=x + random.uniform(-15, 15),
                y=y,
                vx=vx,
                vy=vy,
                color=(180, 180, 180),
                radius=random.uniform(3.0, 7.0),
                life=random.uniform(0.2, 0.4),
                max_life=0.4
            ))

    def update(self, dt: float):
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.is_alive]

        for s in self.shockwaves:
            s.update(dt)
        self.shockwaves = [s for s in self.shockwaves if s.is_alive]

        for t in self.impact_texts:
            t.update(dt)
        self.impact_texts = [t for t in self.impact_texts if t.is_alive]

        for a in self.slash_arcs:
            a.update(dt)
        self.slash_arcs = [a for a in self.slash_arcs if a.is_alive]

        if self.flash_alpha > 0:
            self.flash_alpha = max(0.0, self.flash_alpha - 350.0 * dt)

    def draw(self, surface: pygame.Surface, camera_to_screen_fn):
        """Renders particles, shockwaves, impact texts, and flash overlay."""
        # Draw slash arcs (glowing weapon trails)
        for sa in self.slash_arcs:
            sx, sy = camera_to_screen_fn(sa.x, sa.y)
            progress = sa.life / sa.max_life
            alpha = int(255 * progress)
            r = int(sa.radius)
            if r > 4 and alpha > 0:
                arc_surf = pygame.Surface((r * 2 + 10, r * 2 + 10), pygame.SRCALPHA)
                rect = pygame.Rect(5, 5, r * 2, r * 2)
                pygame.draw.arc(arc_surf, (*sa.color, alpha), rect, sa.start_angle, sa.end_angle, sa.width)
                surface.blit(arc_surf, (sx - r - 5, sy - r - 5))

        # Draw shockwaves
        for sw in self.shockwaves:
            sx, sy = camera_to_screen_fn(sw.x, sw.y)
            progress = 1.0 - (sw.life / sw.max_life)
            alpha = int(255 * (1.0 - progress))
            if alpha > 0 and sw.current_radius > 1:
                # Pygame circles with alpha via temporary surface
                radius = int(sw.current_radius)
                temp = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(temp, (*sw.color, alpha), (radius + 2, radius + 2), radius, width=3)
                surface.blit(temp, (sx - radius - 2, sy - radius - 2))

        # Draw particles
        for p in self.particles:
            sx, sy = camera_to_screen_fn(p.x, p.y)
            progress = p.life / p.max_life
            rad = max(1, int(p.radius * progress))
            pygame.draw.circle(surface, p.color, (int(sx), int(sy)), rad)

        # Draw impact texts
        if self.impact_texts:
            if not pygame.font.get_init():
                pygame.font.init()
            impact_font = pygame.font.Font(None, 42)
            for it in self.impact_texts:
                sx, sy = camera_to_screen_fn(it.x, it.y)
                txt_surf = impact_font.render(it.text, True, it.color)
                rect = txt_surf.get_rect(center=(int(sx), int(sy)))
                surface.blit(txt_surf, rect)

        # Draw flash overlay
        if self.flash_alpha > 0:
            flash_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            flash_surf.fill((*self.flash_color, int(self.flash_alpha)))
            surface.blit(flash_surf, (0, 0))
