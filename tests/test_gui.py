"""
Tests for the Stick Fight Video Studio GUI backend and preview generator.
"""

import os
import json
import pytest
from stickfight.gui.app import hex_to_rgb, create_preview_surface, PRESETS, STATIC_DIR


def test_hex_to_rgb():
    assert hex_to_rgb("#ff0000") == (255, 0, 0)
    assert hex_to_rgb("#00ff00") == (0, 255, 0)
    assert hex_to_rgb("#0000ff") == (0, 0, 255)
    assert hex_to_rgb("invalid") == (240, 240, 240)
    assert hex_to_rgb(None) == (240, 240, 240)


def test_presets_exist():
    assert len(PRESETS) >= 4
    for p in PRESETS:
        assert "id" in p
        assert "title" in p
        assert "fighter_a" in p
        assert "fighter_b" in p
        assert "environment" in p


def test_index_html_exists():
    index_path = os.path.join(STATIC_DIR, "index.html")
    assert os.path.exists(index_path)
    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "STICK FIGHT STUDIO" in content
    assert "GENERATE FIGHT VIDEO" in content


def test_create_preview_surface():
    cfg = {
        "fighter_a": {"name": "Shadow", "archetype": "ninja", "color": "#2d3038", "weapon": "sword"},
        "fighter_b": {"name": "Unit-01", "archetype": "cyber", "color": "#32dcff", "weapon": "none"},
        "environment": "cyberpunk",
        "format": "vertical",
    }
    surf = create_preview_surface(cfg)
    assert surf.get_width() == 540
    assert surf.get_height() == 960


def test_build_custom_timeline_scene():
    from stickfight.gui.app import build_custom_timeline_scene
    cfg = {
        "fighter_a": {"name": "Shadow", "archetype": "ninja", "weapon": "sword"},
        "fighter_b": {"name": "Kensei", "archetype": "warrior", "weapon": "sword"},
        "environment": "dojo",
        "timeline": [
            {"time": 0.0, "actor": "A", "action": "walk_to", "target_x": 450},
            {"time": 1.0, "actor": "A", "action": "slash", "target": "B"},
            {"time": 1.2, "actor": "B", "action": "block"},
            {"time": 1.8, "actor": "B", "action": "fall"},
            {"time": 2.0, "actor": "scene", "action": "caption", "text": "K.O."},
        ],
    }
    scene = build_custom_timeline_scene(cfg, width=1080, height=1920, fps=30, ground_y=1500.0)
    assert len(scene.fighters) == 2
    assert scene.fighters[0].name == "Shadow"
    assert scene.fighters[1].name == "Kensei"
    assert scene.fighters[0].weapon == "sword"
    assert scene.timeline.get_total_duration() > 1.8

