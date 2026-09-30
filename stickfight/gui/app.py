"""
Local HTTP Server and API backend for the Stick Fight Video Engine GUI.
"""

from __future__ import annotations
import os
import io
import sys
import json
import time
import uuid
import random
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from typing import Dict, Any, Optional, Tuple
# Headless rendering for Pygame must be configured before importing pygame.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame

from stickfight import FightScene, Fighter
from stickfight.scripting.generator import generate_fight
from stickfight.engine.camera import Camera
from stickfight.engine.renderer import Renderer
from stickfight.engine.combat_timing import ATTACK_TIMINGS
from stickfight.studio.combat import normalize_action


STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../output"))
os.makedirs(os.path.join(OUTPUT_DIR, "videos"), exist_ok=True)

# Global Job State for async renders
active_job: Dict[str, Any] = {
    "id": None,
    "status": "idle",  # idle, rendering, done, error
    "progress": 0.0,
    "frame": 0,
    "total_frames": 0,
    "fps": 0.0,
    "video_url": None,
    "error": None,
}
job_lock = threading.Lock()


def hex_to_rgb(hex_str: Optional[str], default: Tuple[int, int, int] = (240, 240, 240)) -> Tuple[int, int, int]:
    if not hex_str or not isinstance(hex_str, str):
        return default
    hex_str = hex_str.lstrip("#")
    if len(hex_str) == 6:
        try:
            return (int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16))
        except ValueError:
            return default
    return default


PRESETS = [
    {
        "id": "ninja_vs_samurai",
        "title": "🗡️ Blade & Shadow",
        "description": "Stealth assassin vs honorable swordmaster in an ancient temple.",
        "fighter_a": {
            "name": "Shadow",
            "archetype": "ninja",
            "weapon": "sword",
            "color": "#2d3038",
            "headband_color": "#eb2d2d",
            "scale": 1.0,
            "line_width": 10,
            "health": 100,
        },
        "fighter_b": {
            "name": "Kensei",
            "archetype": "warrior",
            "weapon": "sword",
            "color": "#e6ebf5",
            "headband_color": "#ebbe2d",
            "scale": 1.0,
            "line_width": 10,
            "health": 100,
        },
        "environment": "dojo",
        "duration": 6.5,
        "format": "vertical",
        "aggression": "high",
        "timeline": [
            {"time": 0.0, "actor": "A", "action": "walk_to", "target_x": 480, "duration": 1.0},
            {"time": 0.0, "actor": "B", "action": "walk_to", "target_x": 640, "duration": 1.0},
            {"time": 0.0, "actor": "scene", "action": "caption", "text": "DUEL OF THE BLADES", "duration": 1.5},
            {"time": 1.4, "actor": "A", "action": "slash", "target": "B", "duration": 0.45},
            {"time": 1.55, "actor": "B", "action": "block", "duration": 0.45},
            {"time": 2.2, "actor": "B", "action": "slash", "target": "A", "duration": 0.48},
            {"time": 2.35, "actor": "A", "action": "dodge", "duration": 0.50},
            {"time": 3.2, "actor": "A", "action": "sweep", "target": "B", "duration": 0.45},
            {"time": 4.0, "actor": "A", "action": "uppercut", "target": "B", "duration": 0.55},
            {"time": 4.5, "actor": "B", "action": "fall", "duration": 1.4},
            {"time": 4.8, "actor": "scene", "action": "caption", "text": "K.O. - SHADOW WINS", "duration": 2.0},
        ],
    },
    {
        "id": "cyborg_vs_ninja",
        "title": "⚡ Cyber Grid Clash",
        "description": "High-tech android with Arc Reactor vs cyber shinobi.",
        "fighter_a": {
            "name": "Unit-01",
            "archetype": "cyber",
            "weapon": "none",
            "color": "#32dcff",
            "headband_color": "#00f0ff",
            "scale": 1.0,
            "line_width": 10,
            "health": 120,
        },
        "fighter_b": {
            "name": "Ghost",
            "archetype": "ninja",
            "weapon": "sword",
            "color": "#24262e",
            "headband_color": "#ff0055",
            "scale": 1.0,
            "line_width": 10,
            "health": 100,
        },
        "environment": "cyberpunk",
        "duration": 6.5,
        "format": "vertical",
        "aggression": "extreme",
        "timeline": [
            {"time": 0.0, "actor": "A", "action": "run_to", "target_x": 460, "duration": 0.8},
            {"time": 0.0, "actor": "B", "action": "run_to", "target_x": 620, "duration": 0.8},
            {"time": 0.0, "actor": "scene", "action": "caption", "text": "CYBER MATRIX CLASH", "duration": 1.4},
            {"time": 1.2, "actor": "B", "action": "slash", "target": "A", "duration": 0.45},
            {"time": 1.3, "actor": "A", "action": "dodge", "duration": 0.50},
            {"time": 1.8, "actor": "A", "action": "combo", "combo_name": "boxing_flurry", "target": "B", "duration": 1.0},
            {"time": 2.8, "actor": "B", "action": "knockback", "distance": 130, "duration": 0.6},
            {"time": 3.4, "actor": "B", "action": "uppercut", "target": "A", "duration": 0.5},
            {"time": 3.55, "actor": "A", "action": "block", "duration": 0.45},
            {"time": 4.1, "actor": "A", "action": "counter", "target": "B", "duration": 0.7},
            {"time": 4.8, "actor": "B", "action": "fall", "duration": 1.3},
            {"time": 5.0, "actor": "scene", "action": "caption", "text": "UNIT-01 VICTORIOUS", "duration": 2.0},
        ],
    },
    {
        "id": "brawler_vs_monk",
        "title": "🥊 Street vs Shaolin",
        "description": "Heavyweight bare-knuckle powerhouse vs acrobatic staff master.",
        "fighter_a": {
            "name": "Titan",
            "archetype": "brawler",
            "weapon": "none",
            "color": "#eb3c3c",
            "headband_color": "#3c3c45",
            "scale": 1.1,
            "line_width": 13,
            "health": 130,
        },
        "fighter_b": {
            "name": "Shaolin",
            "archetype": "monk",
            "weapon": "staff",
            "color": "#f58c23",
            "headband_color": "#f5c846",
            "scale": 1.0,
            "line_width": 10,
            "health": 100,
        },
        "environment": "city",
        "duration": 6.5,
        "format": "vertical",
        "aggression": "high",
        "timeline": [
            {"time": 0.0, "actor": "A", "action": "walk_to", "target_x": 460, "duration": 1.0},
            {"time": 0.0, "actor": "B", "action": "walk_to", "target_x": 620, "duration": 1.0},
            {"time": 0.0, "actor": "scene", "action": "caption", "text": "STREET VS SHAOLIN", "duration": 1.4},
            {"time": 1.2, "actor": "A", "action": "punch", "target": "B", "duration": 0.4},
            {"time": 1.35, "actor": "B", "action": "block", "duration": 0.45},
            {"time": 1.8, "actor": "B", "action": "combo", "combo_name": "staff_combo", "target": "A", "duration": 1.0},
            {"time": 2.9, "actor": "A", "action": "knockback", "distance": 140, "duration": 0.6},
            {"time": 3.6, "actor": "A", "action": "uppercut", "target": "B", "duration": 0.55},
            {"time": 4.2, "actor": "B", "action": "dodge", "duration": 0.50},
            {"time": 4.8, "actor": "B", "action": "sweep", "target": "A", "duration": 0.45},
            {"time": 5.3, "actor": "A", "action": "fall", "duration": 1.3},
            {"time": 5.5, "actor": "scene", "action": "caption", "text": "SHAOLIN MASTERY", "duration": 2.0},
        ],
    },
    {
        "id": "classic_showdown",
        "title": "⚪ Pure Classic Duel",
        "description": "Iconic minimalist stick fight animation in the style of Xiao Xiao.",
        "fighter_a": {
            "name": "Red",
            "archetype": "classic",
            "weapon": "none",
            "color": "#e63946",
            "headband_color": None,
            "scale": 1.0,
            "line_width": 10,
            "health": 100,
        },
        "fighter_b": {
            "name": "Blue",
            "archetype": "classic",
            "weapon": "none",
            "color": "#457b9d",
            "headband_color": None,
            "scale": 1.0,
            "line_width": 10,
            "health": 100,
        },
        "environment": "plain",
        "duration": 5.5,
        "format": "vertical",
        "aggression": "medium",
        "timeline": [
            {"time": 0.0, "actor": "A", "action": "walk_to", "target_x": 480, "duration": 1.0},
            {"time": 0.0, "actor": "B", "action": "walk_to", "target_x": 640, "duration": 1.0},
            {"time": 0.0, "actor": "scene", "action": "caption", "text": "ROUND 1", "duration": 1.2},
            {"time": 1.2, "actor": "A", "action": "punch", "target": "B", "duration": 0.45},
            {"time": 1.35, "actor": "B", "action": "block", "duration": 0.45},
            {"time": 1.8, "actor": "B", "action": "kick", "target": "A", "duration": 0.5},
            {"time": 1.95, "actor": "A", "action": "dodge", "duration": 0.5},
            {"time": 2.5, "actor": "A", "action": "sweep", "target": "B", "duration": 0.45},
            {"time": 3.2, "actor": "A", "action": "uppercut", "target": "B", "duration": 0.55},
            {"time": 3.8, "actor": "B", "action": "fall", "duration": 1.2},
            {"time": 4.0, "actor": "scene", "action": "caption", "text": "K.O.", "duration": 1.8},
        ],
    },
    {
        "id": "acrobatic_aerial",
        "title": "🌪️ Aerial Acrobatics & Throws",
        "description": "High-flying dive kicks, mid-air juggles, wall bounces, and seismic grappling slams.",
        "fighter_a": {
            "name": "Hayabusa",
            "archetype": "ninja",
            "weapon": "none",
            "color": "#1f222e",
            "headband_color": "#00ffaa",
            "scale": 1.0,
            "line_width": 10,
            "health": 100,
        },
        "fighter_b": {
            "name": "Goliath",
            "archetype": "brawler",
            "weapon": "none",
            "color": "#e04040",
            "headband_color": "#ffaa00",
            "scale": 1.1,
            "line_width": 12,
            "health": 140,
        },
        "environment": "dojo",
        "duration": 6.8,
        "format": "vertical",
        "aggression": "extreme",
        "timeline": [
            {"time": 0.0, "actor": "A", "action": "run_to", "target_x": 440, "duration": 0.8},
            {"time": 0.0, "actor": "B", "action": "walk_to", "target_x": 640, "duration": 0.9},
            {"time": 0.0, "actor": "scene", "action": "caption", "text": "AERIAL ACROBATICS", "duration": 1.4},
            {"time": 1.1, "actor": "A", "action": "dive_kick", "target": "B", "duration": 0.65},
            {"time": 1.8, "actor": "B", "action": "throw", "target": "A", "duration": 0.75},
            {"time": 2.8, "actor": "A", "action": "wall_bounce", "duration": 0.65},
            {"time": 3.6, "actor": "A", "action": "uppercut", "target": "B", "duration": 0.50},
            {"time": 4.1, "actor": "A", "action": "air_juggle", "target": "B", "duration": 0.55},
            {"time": 4.8, "actor": "A", "action": "throw", "target": "B", "duration": 0.80},
            {"time": 5.8, "actor": "scene", "action": "caption", "text": "SEISMIC K.O.", "duration": 2.0},
        ],
    },
    {
        "id": "realistic_boxing",
        "title": "🥊 Heavyweight Boxing",
        "description": "Tactical sweet science: Jabs, crosses, hooks, slips, bob & weaves, and liver shots.",
        "fighter_a": {
            "name": "Iron Mike",
            "archetype": "brawler",
            "weapon": "none",
            "color": "#22252c",
            "headband_color": "#ff3366",
            "scale": 1.05,
            "line_width": 12,
            "health": 100,
        },
        "fighter_b": {
            "name": "Apollo",
            "archetype": "classic",
            "weapon": "none",
            "color": "#e0e4ec",
            "headband_color": "#ffaa00",
            "scale": 1.0,
            "line_width": 10,
            "health": 100,
        },
        "environment": "city",
        "duration": 6.0,
        "format": "vertical",
        "style": "realistic",
        "aggression": "high",
        "timeline": [
            {"time": 0.0, "actor": "A", "action": "walk_to", "target_x": 480, "duration": 0.9},
            {"time": 0.0, "actor": "B", "action": "walk_to", "target_x": 600, "duration": 0.9},
            {"time": 0.0, "actor": "scene", "action": "caption", "text": "CHAMPIONSHIP BOXING", "duration": 1.4},
            {"time": 1.1, "actor": "A", "action": "jab", "target": "B", "duration": 0.35},
            {"time": 1.5, "actor": "B", "action": "slip", "duration": 0.40},
            {"time": 1.7, "actor": "B", "action": "cross", "target": "A", "duration": 0.40},
            {"time": 2.2, "actor": "A", "action": "bob_weave", "duration": 0.45},
            {"time": 2.6, "actor": "A", "action": "hook", "target": "B", "duration": 0.42},
            {"time": 3.0, "actor": "B", "action": "stagger", "duration": 0.50},
            {"time": 3.6, "actor": "A", "action": "cross", "target": "B", "duration": 0.40},
            {"time": 4.1, "actor": "B", "action": "fall", "duration": 1.3},
            {"time": 4.4, "actor": "scene", "action": "caption", "text": "KNOCKOUT VICTORY!", "duration": 1.8},
        ],
    },
    {
        "id": "realistic_mma",
        "title": "🥋 Championship MMA",
        "description": "Dutch kickboxing, low kicks vs shin checks, clinch knees, double-leg takedown & ground and pound.",
        "fighter_a": {
            "name": "Eagle",
            "archetype": "warrior",
            "weapon": "none",
            "color": "#1e293b",
            "headband_color": "#00d2ff",
            "scale": 1.0,
            "line_width": 10,
            "health": 100,
        },
        "fighter_b": {
            "name": "Predator",
            "archetype": "brawler",
            "weapon": "none",
            "color": "#dc2626",
            "headband_color": "#facc15",
            "scale": 1.08,
            "line_width": 12,
            "health": 120,
        },
        "environment": "dojo",
        "duration": 6.5,
        "format": "vertical",
        "style": "realistic",
        "aggression": "high",
        "timeline": [
            {"time": 0.0, "actor": "A", "action": "walk_to", "target_x": 470, "duration": 0.8},
            {"time": 0.0, "actor": "B", "action": "walk_to", "target_x": 610, "duration": 0.8},
            {"time": 0.0, "actor": "scene", "action": "caption", "text": "WORLD MMA TITLE FIGHT", "duration": 1.4},
            {"time": 1.1, "actor": "B", "action": "low_kick", "target": "A", "duration": 0.42},
            {"time": 1.15, "actor": "A", "action": "check_kick", "duration": 0.45},
            {"time": 1.8, "actor": "A", "action": "jab", "target": "B", "duration": 0.32},
            {"time": 2.15, "actor": "A", "action": "cross", "target": "B", "duration": 0.38},
            {"time": 2.7, "actor": "A", "action": "clinch_knee", "target": "B", "duration": 0.50},
            {"time": 3.4, "actor": "A", "action": "takedown", "target": "B", "duration": 0.70},
            {"time": 4.2, "actor": "A", "action": "ground_pound", "target": "B", "duration": 0.55},
            {"time": 4.8, "actor": "A", "action": "ground_pound", "target": "B", "duration": 0.55},
            {"time": 5.4, "actor": "scene", "action": "caption", "text": "T.K.O. - REFEREE STOPS FIGHT", "duration": 1.8},
        ],
    },
]



def build_custom_timeline_scene(config: Dict[str, Any], width: int, height: int, fps: int, ground_y: float) -> FightScene:
    """Builds a FightScene directly from user-configured actions and timing."""
    style = config.get("style", "arcade")
    scene = FightScene(width=width, height=height, fps=fps, ground_y=ground_y, style=style)
    env = config.get("environment", "dojo")
    scene.background(env)

    fa_cfg = config.get("fighter_a", {})
    fb_cfg = config.get("fighter_b", {})

    spawn_a = width * 0.31
    spawn_b = width * 0.69

    f1 = scene.add_fighter(
        name=fa_cfg.get("name", "Fighter A"),
        x=spawn_a,
        y=ground_y,
        facing=1,
        color=hex_to_rgb(fa_cfg.get("color", "#2d3038")),
        headband_color=hex_to_rgb(fa_cfg.get("headband_color")) if fa_cfg.get("headband_color") else None,
        line_width=int(fa_cfg.get("line_width", 10)),
        scale=float(fa_cfg.get("scale", 1.0)),
        design=fa_cfg.get("archetype", "ninja"),
    )
    f1.render_style = config.get("visual_style", "ink_fight")
    if fa_cfg.get("weapon") and fa_cfg["weapon"] != "none":
        f1.equip(fa_cfg["weapon"])

    f2 = scene.add_fighter(
        name=fb_cfg.get("name", "Fighter B"),
        x=spawn_b,
        y=ground_y,
        facing=-1,
        color=hex_to_rgb(fb_cfg.get("color", "#e6ebf5")),
        headband_color=hex_to_rgb(fb_cfg.get("headband_color")) if fb_cfg.get("headband_color") else None,
        line_width=int(fb_cfg.get("line_width", 10)),
        scale=float(fb_cfg.get("scale", 1.0)),
        design=fb_cfg.get("archetype", "warrior"),
    )
    f2.render_style = config.get("visual_style", "ink_fight")
    if fb_cfg.get("weapon") and fb_cfg["weapon"] != "none":
        f2.equip(fb_cfg["weapon"])

    fighters = {"A": f1, "B": f2}
    events = config.get("timeline", [])

    for ev in events:
        try:
            t = float(ev.get("time", 0.0))
            actor_key = ev.get("actor", "A")
            act = ev.get("action", "")
            dur = float(ev.get("duration", 0.5))

            if actor_key == "scene":
                if act == "caption":
                    text = ev.get("text", "")
                    scene.caption(text, t, t + dur)
                elif act == "shake":
                    intensity = float(ev.get("intensity", 14.0))
                    scene.camera.shake(intensity=intensity, duration=dur)
                continue

            actor = fighters.get(actor_key, f1)
            target = fighters.get(ev.get("target"), f2 if actor == f1 else f1)

            if act == "walk_to":
                target_x = float(ev.get("target_x", width * 0.45))
                scene.at(t, actor.walk_to(target_x, duration=dur))
            elif act == "run_to":
                target_x = float(ev.get("target_x", width * 0.45))
                scene.at(t, actor.run_to(target_x, duration=dur))
            elif act == "punch":
                scene.at(t, actor.punch(target, duration=dur, damage=float(ev.get("damage", 15.0))))
            elif act == "kick":
                scene.at(t, actor.kick(target, duration=dur, damage=float(ev.get("damage", 22.0))))
            elif act == "uppercut":
                scene.at(t, actor.uppercut(target, duration=dur, damage=float(ev.get("damage", 26.0))))
            elif act == "sweep":
                scene.at(t, actor.sweep(target, duration=dur, damage=float(ev.get("damage", 16.0))))
            elif act == "slash":
                scene.at(t, actor.slash(target, duration=dur, damage=float(ev.get("damage", 28.0))))
            elif act == "staff_strike":
                scene.at(t, actor.staff_strike(target, duration=dur, damage=float(ev.get("damage", 21.0))))
            elif act == "throw":
                scene.at(t, actor.throw(target, duration=dur, damage=float(ev.get("damage", 30.0))))
            elif act == "dive_kick":
                scene.at(t, actor.dive_kick(target, duration=dur, damage=float(ev.get("damage", 25.0))))
            elif act == "air_juggle":
                scene.at(t, actor.air_juggle(target, duration=dur, damage=float(ev.get("damage", 22.0))))
            elif act == "wall_bounce":
                wall_val = float(ev.get("wall_x")) if ev.get("wall_x") is not None else None
                scene.at(t, actor.wall_bounce(wall_x=wall_val, duration=dur))
            elif act == "block":
                scene.at(t, actor.block(duration=dur))
            elif act == "dodge":
                scene.at(t, actor.dodge(duration=dur))
            elif act == "hit":
                scene.at(t, actor.hit(duration=dur))
            elif act == "knockback":
                dist = float(ev.get("distance", 140.0))
                scene.at(t, actor.knockback(distance=dist, duration=dur))
            elif act == "fall":
                scene.at(t, actor.fall(duration=dur))
            elif act == "jump":
                height = float(ev.get("height", 160.0))
                scene.at(t, actor.jump(height=height, duration=dur))
            elif act == "counter":
                scene.at(t, actor.counter(target, duration=dur))
            elif act == "combo":
                combo_name = ev.get("combo_name", "ninja_rush")
                scene.at(t, actor.combo(combo_name, target=target))
            # Realistic Martial Arts Actions
            elif act == "jab":
                scene.at(t, actor.jab(target, duration=dur, damage=float(ev.get("damage", 12.0))))
            elif act == "cross":
                scene.at(t, actor.cross(target, duration=dur, damage=float(ev.get("damage", 18.0))))
            elif act == "hook":
                scene.at(t, actor.hook(target, duration=dur, damage=float(ev.get("damage", 24.0))))
            elif act == "low_kick":
                scene.at(t, actor.low_kick(target, duration=dur, damage=float(ev.get("damage", 16.0))))
            elif act == "check_kick":
                scene.at(t, actor.check_kick(duration=dur))
            elif act == "slip":
                scene.at(t, actor.slip(duration=dur))
            elif act == "bob_weave":
                scene.at(t, actor.bob_weave(duration=dur))
            elif act == "clinch_knee":
                scene.at(t, actor.clinch_knee(target, duration=dur, damage=float(ev.get("damage", 25.0))))
            elif act == "takedown":
                scene.at(t, actor.takedown(target, duration=dur, damage=float(ev.get("damage", 22.0))))
            elif act == "ground_pound":
                scene.at(t, actor.ground_pound(target, duration=dur, damage=float(ev.get("damage", 28.0))))
            elif act == "stagger":
                scene.at(t, actor.stagger(duration=dur))
        except Exception as err:
            print(f"Warning: skipped invalid timeline event {ev}: {err}")

    return scene


def create_preview_surface(config: Dict[str, Any]) -> pygame.Surface:
    """Generates an instant in-memory snapshot of the two fighters facing off in the chosen arena."""
    fmt = config.get("format", "vertical")
    if fmt == "horizontal":
        w, h = 960, 540
        gy = 420.0
    elif fmt == "square":
        w, h = 600, 600
        gy = 460.0
    else:  # vertical
        w, h = 540, 960
        gy = 750.0

    pygame.init()
    surface = pygame.Surface((w, h))

    camera = Camera(viewport_width=w, viewport_height=h)
    camera.x = w / 2.0
    camera.y = gy - 120.0
    camera.target_x = camera.x
    camera.target_y = camera.y
    camera.zoom = 0.95

    env = config.get("environment", "dojo")
    renderer = Renderer(width=w, height=h)
    renderer.draw_background(surface, env, camera, ground_y=gy)

    # Configure Fighter A (Left)
    fa_cfg = config.get("fighter_a", {})
    scale_a = float(fa_cfg.get("scale", 1.0)) * 0.95
    fa = Fighter(
        name=fa_cfg.get("name", "Challenger A"),
        x=w * 0.35,
        y=gy,
        facing=1,
        color=hex_to_rgb(fa_cfg.get("color", "#2d3038")),
        headband_color=hex_to_rgb(fa_cfg.get("headband_color")) if fa_cfg.get("headband_color") else None,
        line_width=int(fa_cfg.get("line_width", 10)),
        scale=scale_a,
        design=fa_cfg.get("archetype", "ninja"),
        weapon=fa_cfg.get("weapon") if fa_cfg.get("weapon") != "none" else None,
    )
    fa.render_style = config.get("visual_style", "ink_fight")
    fa.clip_time = 0.15
    fa.update_animation(0.0)

    # Configure Fighter B (Right)
    fb_cfg = config.get("fighter_b", {})
    scale_b = float(fb_cfg.get("scale", 1.0)) * 0.95
    fb = Fighter(
        name=fb_cfg.get("name", "Challenger B"),
        x=w * 0.65,
        y=gy,
        facing=-1,
        color=hex_to_rgb(fb_cfg.get("color", "#e6ebf5")),
        headband_color=hex_to_rgb(fb_cfg.get("headband_color")) if fb_cfg.get("headband_color") else None,
        line_width=int(fb_cfg.get("line_width", 10)),
        scale=scale_b,
        design=fb_cfg.get("archetype", "warrior"),
        weapon=fb_cfg.get("weapon") if fb_cfg.get("weapon") != "none" else None,
    )
    fb.render_style = config.get("visual_style", "ink_fight")
    fb.clip_time = 0.15
    fb.update_animation(0.0)

    renderer.draw_fighter(surface, fa, camera)
    renderer.draw_fighter(surface, fb, camera)

    # Health bars preview
    if config.get("show_ui", True):
        renderer.draw_health_bars(surface, [fa, fb])

    return surface


def _apply_studio_pose_overrides(fighter: Fighter, pose_overrides: Any) -> None:
    """Apply additive per-joint Studio offsets after the production animation/IK pass."""
    if not isinstance(pose_overrides, dict):
        return
    allowed = {
        "head", "neck", "chest",
        "left_shoulder", "left_elbow", "left_hand",
        "right_shoulder", "right_elbow", "right_hand",
        "left_hip", "left_knee", "left_foot",
        "right_hip", "right_knee", "right_foot",
    }
    for joint, value in pose_overrides.items():
        if joint not in allowed or not isinstance(value, dict):
            continue
        try:
            dx = max(-180.0, min(180.0, float(value.get("x", 0.0))))
            dy = max(-180.0, min(180.0, float(value.get("y", 0.0))))
        except (TypeError, ValueError):
            continue
        base_x, base_y = fighter.current_pose.get(joint)
        fighter.current_pose.set(joint, base_x + dx, base_y + dy)


def _resolve_studio_combat_actions(config: Dict[str, Any], frame: int) -> Dict[str, Dict[str, Any]]:
    """Resolve authored Fight workspace events into per-character animation state."""
    resolved: Dict[str, Dict[str, Any]] = {}
    for event in config.get("combat_events", []):
        if not isinstance(event, dict):
            continue
        attacker = str(event.get("attacker_id", ""))
        target = str(event.get("target_id", ""))
        action = normalize_action(event.get("action", "idle"))
        try:
            start = int(event.get("start_frame", 0))
            end = max(start + 1, int(event.get("end_frame", start + 1)))
        except (TypeError, ValueError):
            continue
        if frame < start or frame > end or not attacker:
            continue
        elapsed = frame - start
        duration = max(1, end - start)
        timing = ATTACK_TIMINGS.get(action)
        phase = timing.phase(elapsed, duration) if timing else str(event.get("phase", "action"))
        resolved[attacker] = {"action": action, "phase": phase, "target_id": target}
        if target and timing and timing.is_impact_frame(elapsed, duration, tolerance=0.055):
            resolved[target] = {"action": "hit", "phase": "impact", "source_id": attacker}
    return resolved


def create_studio_frame_surface(config: Dict[str, Any]) -> pygame.Surface:
    """Render a Studio frame through the production Fight renderer.

    Studio only supplies authored intent (transforms + active fight action).
    Skeletons, clips, IK, physics, weapons, hitboxes and rendering remain owned
    by the existing fight engine.
    """
    w, h = 540, 960
    gy = 750.0
    pygame.init()
    surface = pygame.Surface((w, h))
    camera = Camera(viewport_width=w, viewport_height=h)
    camera.x = w / 2.0
    camera.y = gy - 120.0
    camera.target_x = camera.x
    camera.target_y = camera.y
    camera.zoom = 0.95
    env = config.get("environment", "dojo")
    renderer = Renderer(width=w, height=h)
    renderer.draw_background(surface, env, camera, ground_y=gy)

    chars = config.get("characters", [])
    combat_states = _resolve_studio_combat_actions(config, int(config.get("frame", 0)))
    if not chars:
        chars = [
            {"id": "char-a", "name": "Fighter A", "x": w * 0.35, "y": gy,
             "facing": 1, "archetype": "ninja", "color": "#2d3038",
             "style": "ink_fight", "action": "idle"},
            {"id": "char-b", "name": "Fighter B", "x": w * 0.65, "y": gy,
             "facing": -1, "archetype": "warrior", "color": "#e6ebf5",
             "style": "ink_fight", "action": "idle"},
        ]

    fighters = []
    for idx, char in enumerate(chars):
        fighter = Fighter(
            name=char.get("name", f"Fighter {idx + 1}"),
            x=float(char.get("x", w * (0.3 + 0.4 * (idx % 2)))),
            y=float(char.get("y", gy)),
            facing=int(char.get("facing", 1 if idx % 2 == 0 else -1)),
            color=hex_to_rgb(char.get("color", "#2d3038")),
            headband_color=hex_to_rgb(char.get("headband_color")) if char.get("headband_color") else None,
            line_width=int(char.get("line_width", 10)),
            scale=float(char.get("scale", 1.0)),
            design=char.get("archetype", "ninja"),
            weapon=char.get("weapon") if char.get("weapon") not in (None, "", "none") else None,
        )
        fighter.render_style = char.get("style", "ink_fight")
        fighter.facing = 1 if int(char.get("facing", fighter.facing)) >= 0 else -1

        # Fight action is authored by Studio, but executed by the real Fighter
        # animation library. Unknown actions safely resolve to idle.
        authored = combat_states.get(str(char.get("id", "")), {})
        action = normalize_action(authored.get("action", char.get("action", "idle")))
        fighter.set_animation(action, loop=False if action != "idle" else True)
        fighter.update_animation(0.0)
        # Manual Studio pose edits layer on top of the real production clip.
        _apply_studio_pose_overrides(fighter, char.get("pose", {}))
        fighters.append(fighter)

    for fighter in fighters:
        renderer.draw_fighter(surface, fighter, camera)
    return surface


def execute_render_job(job_id: str, config: Dict[str, Any]):
    """Background worker that synthesizes and renders the complete stick fight video."""
    global active_job

    try:
        duration = float(config.get("duration", 5.0))
        fmt = config.get("format", "vertical")
        if fmt == "horizontal":
            width, height = 1920, 1080
            ground_y = 850.0
        elif fmt == "square":
            width, height = 1080, 1080
            ground_y = 850.0
        else:
            width, height = 1080, 1920
            ground_y = 1500.0

        fps = int(config.get("fps", 30))
        env = config.get("environment", "dojo")
        seed = config.get("seed")
        if seed is None or str(seed).strip() == "":
            seed = random.randint(1000, 999999)
        else:
            seed = int(seed)

        timestamp = int(time.time())
        video_filename = f"fight_studio_{timestamp}.mp4"
        output_file = os.path.join(OUTPUT_DIR, "videos", video_filename)

        # Build scene with custom fighter parameters
        fa_cfg = config.get("fighter_a", {})
        fb_cfg = config.get("fighter_b", {})

        arch_a = fa_cfg.get("archetype", "ninja")
        arch_b = fb_cfg.get("archetype", "warrior")

        mode = config.get("mode", "procedural")
        style = config.get("style", "arcade")
        if mode == "timeline" and config.get("timeline"):
            scene = build_custom_timeline_scene(config, width, height, fps, ground_y)
        else:
            scene = generate_fight(
                duration=duration,
                fighter_a_type=arch_a,
                fighter_b_type=arch_b,
                environment=env,
                seed=seed,
                width=width,
                height=height,
                fps=fps,
                ground_y=ground_y,
                style=style,
            )

            # Apply custom names and styling override to fighters
            if len(scene.fighters) >= 2:
                f1, f2 = scene.fighters[0], scene.fighters[1]
                if fa_cfg.get("name"):
                    f1.name = fa_cfg["name"]
                if fa_cfg.get("color"):
                    f1.color = hex_to_rgb(fa_cfg["color"], f1.color)
                if "headband_color" in fa_cfg and fa_cfg["headband_color"]:
                    f1.headband_color = hex_to_rgb(fa_cfg["headband_color"])
                if fa_cfg.get("weapon"):
                    f1.equip(None if fa_cfg["weapon"] == "none" else fa_cfg["weapon"])
                if fa_cfg.get("scale"):
                    f1.scale = float(fa_cfg["scale"])
                f1.render_style = config.get("visual_style", "ink_fight")

                if fb_cfg.get("name"):
                    f2.name = fb_cfg["name"]
                if fb_cfg.get("color"):
                    f2.color = hex_to_rgb(fb_cfg["color"], f2.color)
                if "headband_color" in fb_cfg and fb_cfg["headband_color"]:
                    f2.headband_color = hex_to_rgb(fb_cfg["headband_color"])
                if fb_cfg.get("weapon"):
                    f2.equip(None if fb_cfg["weapon"] == "none" else fb_cfg["weapon"])
                if fb_cfg.get("scale"):
                    f2.scale = float(fb_cfg["scale"])
                f2.render_style = config.get("visual_style", "ink_fight")

        start_t = time.time()

        def on_progress(frame: int, total: int, pct: float):
            with job_lock:
                elapsed = max(0.01, time.time() - start_t)
                active_job["frame"] = frame
                active_job["total_frames"] = total
                active_job["progress"] = pct
                active_job["fps"] = frame / elapsed

        print(f"[GUI] render job {job_id} started: {duration:.2f}s -> {output_file}", flush=True)
        scene.render(output_path=output_file, duration=duration, progress_callback=on_progress)
        print(f"[GUI] render job {job_id} completed", flush=True)

        with job_lock:
            active_job["status"] = "done"
            active_job["progress"] = 1.0
            active_job["video_url"] = f"/output/videos/{video_filename}"
            active_job["output_path"] = output_file

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[GUI] render job {job_id} failed: {e}", flush=True)
        with job_lock:
            active_job["status"] = "error"
            active_job["error"] = str(e)


class StudioRequestHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: Any):
        # Quieter log output for API polling
        if "/api/status" in args[0]:
            return
        super().log_message(format, *args)

    def do_GET(self):
        url_path = self.path.split("?")[0]

        if url_path == "/" or url_path == "/index.html":
            index_path = os.path.join(STATIC_DIR, "index.html")
            if os.path.exists(index_path):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                with open(index_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "index.html not found")
            return

        elif url_path == "/api/presets":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(PRESETS).encode("utf-8"))
            return

        elif url_path == "/api/status":
            with job_lock:
                resp = json.dumps(active_job).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(resp)
            return

        elif url_path.startswith("/output/videos/"):
            filename = os.path.basename(url_path)
            file_path = os.path.join(OUTPUT_DIR, "videos", filename)
            if os.path.exists(file_path):
                self.send_response(200)
                self.send_header("Content-Type", "video/mp4")
                self.send_header("Content-Length", str(os.path.getsize(file_path)))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, f"Video not found: {filename}")
            return

        elif url_path.startswith("/output/"):
            filename = os.path.basename(url_path)
            file_path = os.path.join(OUTPUT_DIR, filename)
            if os.path.exists(file_path):
                mime = "image/png" if filename.endswith(".png") else "application/octet-stream"
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.end_headers()
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, f"File not found: {filename}")
            return

        self.send_error(404, "Not Found")

    def do_POST(self):
        url_path = self.path.split("?")[0]
        print(f"[GUI] POST {url_path}", flush=True)
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
        try:
            payload = json.loads(body)
        except Exception:
            payload = {}

        if url_path == "/api/studio/frame":
            try:
                surface = create_studio_frame_surface(payload)
                buf = io.BytesIO()
                pygame.image.save(surface, buf, "PNG")
                png_bytes = buf.getvalue()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(png_bytes)))
                self.send_header("Cache-Control", "no-cache, no-store")
                self.end_headers()
                self.wfile.write(png_bytes)
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        if url_path == "/api/preview":
            try:
                surface = create_preview_surface(payload)
                buf = io.BytesIO()
                pygame.image.save(surface, buf, "PNG")
                png_bytes = buf.getvalue()

                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(png_bytes)))
                self.send_header("Cache-Control", "no-cache, no-store")
                self.end_headers()
                self.wfile.write(png_bytes)
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        elif url_path == "/api/render":
            global active_job
            with job_lock:
                if active_job["status"] == "rendering":
                    self.send_response(409)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "A render job is already in progress."}).encode("utf-8"))
                    return

                job_id = str(uuid.uuid4())[:8]
                active_job = {
                    "id": job_id,
                    "status": "rendering",
                    "progress": 0.0,
                    "frame": 0,
                    "total_frames": 0,
                    "fps": 0.0,
                    "video_url": None,
                    "error": None,
                }

            thread = threading.Thread(target=execute_render_job, args=(job_id, payload), daemon=True)
            thread.start()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "started", "job_id": job_id}).encode("utf-8"))
            return

        self.send_error(404, "Not Found")


def run_server(host: str = "127.0.0.1", port: int = 5000):
    # Keep preview, render, and status requests independent.
    server = ThreadingHTTPServer((host, port), StudioRequestHandler)
    print(f"🎬 Stick Fight Studio GUI listening at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down Studio GUI server.")
    finally:
        server.server_close()
