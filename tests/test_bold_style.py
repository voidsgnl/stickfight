import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest

from stickfight import FightScene
from stickfight.engine.bold_style import BODY_PATHS, _lighten
from stickfight.engine.camera import Camera
from stickfight.engine.renderer import Renderer

COLOR = (232, 68, 58)


def _setup(clip=None):
    scene = FightScene(width=640, height=960)
    fighter = scene.add_fighter("A", x=320, color=COLOR, render_style="bold")
    if clip:
        fighter.set_animation(clip)
        fighter.update_animation(0.18)
    return fighter, Camera(640, 960)


def test_bold_is_a_configurable_render_style():
    scene = FightScene(width=640, height=960)
    fighter = scene.add_fighter("Styled", render_style="bold")
    assert fighter.render_style == "bold"


@pytest.mark.parametrize("clip", [None, "punch", "kick"])
def test_bold_style_draws_without_error(clip):
    fighter, camera = _setup(clip)
    renderer = Renderer(640, 960)
    surface = pygame.Surface((640, 960))
    surface.fill((0, 0, 0))
    for _ in range(8):
        renderer.draw_fighter(surface, fighter, camera)
        fighter.update_animation(0.03)


def test_bold_body_has_no_internal_outline_seams():
    """Points on the body curves must be body colour, never the dark outline."""
    fighter, camera = _setup()
    renderer = Renderer(640, 960)
    surface = pygame.Surface((640, 960))
    surface.fill((0, 0, 0))
    renderer.draw_fighter(surface, fighter, camera)

    joints = {n: camera.world_to_screen(*p) for n, p in fighter.get_world_joints().items()}
    allowed = {COLOR, _lighten(COLOR, 0.30)}
    for names in BODY_PATHS:
        pts = [joints[n] for n in names]
        # Segment midpoints between interior joints lie exactly on the smoothed curve.
        for a, b in zip(pts[1:-1], pts[2:]):
            mx, my = int(round((a[0] + b[0]) / 2)), int(round((a[1] + b[1]) / 2))
            assert tuple(surface.get_at((mx, my))[:3]) in allowed
