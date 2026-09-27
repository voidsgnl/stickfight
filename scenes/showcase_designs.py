"""
Generates a visual showcase of all character designs side-by-side.
Designs: Classic, Ninja, Warrior, Monk, Cyber, and Brawler.
"""

from __future__ import annotations
import os
import sys
import pygame

# Headless video driver
os.environ["SDL_VIDEODRIVER"] = "dummy"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from stickfight import FightScene, Fighter
from stickfight.engine.characters import (
    create_ninja,
    create_samurai,
    create_brawler,
    create_monk,
    create_cyborg,
)
from stickfight.engine.camera import Camera
from stickfight.engine.renderer import Renderer


def generate_showcase_image(output_path: str = "output/character_designs.png"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    width, height = 1200, 700
    pygame.init()
    surface = pygame.Surface((width, height))
    camera = Camera(viewport_width=width, viewport_height=height)
    camera.target_x = 600.0
    camera.target_y = 350.0
    camera.x = 600.0
    camera.y = 350.0
    camera.zoom = 1.05

    renderer = Renderer(width=width, height=height)
    # Draw stylish dojo background
    renderer.draw_background(surface, "dojo", camera, ground_y=540.0)

    # Create dummy scene for adding fighters
    scene = FightScene(width=width, height=height, ground_y=540.0)

    # 1. Classic Stick
    f_classic = scene.add_fighter("Classic", x=130, y=540, facing=1, color=(240, 240, 240), design="classic")

    # 2. Ninja
    f_ninja = create_ninja(scene, name="Ninja", x=320, y=540, facing=1)

    # 3. Warrior / Samurai
    f_warrior = create_samurai(scene, name="Warrior", x=510, y=540, facing=1)

    # 4. Monk
    f_monk = create_monk(scene, name="Monk", x=700, y=540, facing=1)

    # 5. Cyber
    f_cyber = create_cyborg(scene, name="Cyber", x=890, y=540, facing=-1)

    # 6. Brawler
    f_brawler = create_brawler(scene, name="Brawler", x=1070, y=540, facing=-1)

    fighters = [f_classic, f_ninja, f_warrior, f_monk, f_cyber, f_brawler]

    # Title Banner
    font_title = pygame.font.Font(None, 48)
    font_label = pygame.font.Font(None, 28)
    font_sub = pygame.font.Font(None, 20)

    title_surf = font_title.render("STICK FIGHT VIDEO ENGINE - CHARACTER DESIGNS", True, (255, 255, 255))
    surface.blit(title_surf, (width // 2 - title_surf.get_width() // 2, 40))

    # Animate slight dynamic stances
    for f in fighters:
        f.clip_time = 0.2
        f.update_animation(0.0)
        renderer.draw_fighter(surface, f, camera)

        # Label underneath
        lbl_surf = font_label.render(f.design.upper(), True, (240, 220, 160))
        surface.blit(lbl_surf, (int(f.x) - lbl_surf.get_width() // 2, int(f.y) + 25))

        # Subtitle / Name
        sub_surf = font_sub.render(f.name, True, (180, 180, 190))
        surface.blit(sub_surf, (int(f.x) - sub_surf.get_width() // 2, int(f.y) + 52))

    pygame.image.save(surface, output_path)
    print(f"✅ Saved character designs showcase to {output_path}")


if __name__ == "__main__":
    generate_showcase_image()
