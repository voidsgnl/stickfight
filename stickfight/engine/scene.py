"""
FightScene: Core orchestrator integrating fighters, timeline choreography,
physics, combat hitboxes, camera, audio, previewing, and video rendering.
"""

from __future__ import annotations
import bisect
import copy
import math
import os
import random
import tempfile
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import pygame

from stickfight.engine.fighter import Fighter
from stickfight.engine.timeline import Timeline
from stickfight.engine.camera import Camera
from stickfight.engine.effects import EffectsManager
from stickfight.engine.audio import AudioManager
from stickfight.engine.renderer import Renderer, VideoExporter, find_ffmpeg
from stickfight.engine.collision import find_hit, Hitbox
from stickfight.engine.skeleton import BodyProportions
from stickfight.engine.stats import FighterStats
from stickfight.scripting.actions import (
    Action, ParallelAction, CameraAction, SoundAction, CallbackAction,
)

# --- combat tuning -----------------------------------------------------------
PERFECT_BLOCK_WINDOW = 0.10      # a block raised this recently parries
DODGE_INVULNERABLE = (0.06, 0.40)  # seconds after a dodge starts that it fully evades
GLANCE_FACTOR = 0.5              # damage kept when a dodge is mistimed
BLOCK_PUSHBACK = 0.3             # share of knockback a blocked hit still applies
HIT_STOP_HEAVY = 0.08            # seconds of freeze on heavy impacts
HIT_STOP_PARRY = 0.06
HIT_STOP_KO = 0.25
KO_SLOWMO_LENGTH = 0.9           # scene seconds
KO_SLOWMO_FACTOR = 0.35
MIN_TIME_SCALE = 0.05


class ChoreographyError(RuntimeError):
    """Raised in strict mode when a scene contains impossible choreography."""


@dataclass
class SlowMoRegion:
    start: float
    end: float
    factor: float
    ease: float = 0.0


def _new_stats() -> Dict[str, Any]:
    return {"hits": [], "blocks": 0, "dodges": 0, "parries": 0, "whiffs": 0, "kos": []}


class FightScene:
    def __init__(
        self,
        width: int = 1080,
        height: int = 1920,
        fps: int = 30,
        ground_y: float = 1500.0,
        seed: int = 0,
        style: Optional[str] = None,
        strict: bool = False,
    ):
        self.width = width
        self.height = height
        self.fps = fps
        self.ground_y = ground_y
        self.bg_style = "plain"
        self.style = style  # informational (used by the studio GUI)
        self.strict = strict
        self.seed = seed

        # One seeded RNG drives every visual/audio random choice, so the same
        # seed always renders the same video.
        self.rng = random.Random(seed)

        self.fighters: List[Fighter] = []
        self._fighter_map: Dict[str, Fighter] = {}

        self.timeline = Timeline()
        self.camera = Camera(viewport_width=width, viewport_height=height, rng=self.rng)
        self.effects = EffectsManager(rng=self.rng)
        self.audio = AudioManager(seed=seed)
        self.renderer = Renderer(width=width, height=height)

        self.captions: List[Tuple[str, float, float]] = []
        self.show_ui: bool = True

        # Two clocks: current_time is choreography ("scene") time; video_time
        # is what the viewer sees. They differ during slow motion / hit-stop.
        self.current_time: float = 0.0
        self.video_time: float = 0.0
        self._hitstop_left: float = 0.0
        self._slowmo_static: List[SlowMoRegion] = []
        self._slowmo_dynamic: List[SlowMoRegion] = []
        self._map_sim: List[float] = [0.0]
        self._map_video: List[float] = [0.0]

        self.stats: Dict[str, Any] = _new_stats()
        self.warnings: List[str] = []
        self.on_ko: List[Callable[["FightScene", Fighter, Fighter], None]] = []

    # ========================================================================
    # SCENE BUILDING
    # ========================================================================

    def add_fighter(
        self,
        name: str,
        x: float = 400.0,
        y: Optional[float] = None,
        facing: Optional[int] = None,
        color: Optional[Tuple[int, int, int]] = None,
        line_width: int = 8,
        scale: float = 1.0,
        render_style: str = "segmented",
        proportions: Optional[BodyProportions] = None,
        health: Optional[float] = None,
        design: Optional[str] = None,
        stats: Optional[FighterStats] = None,
        headband_color: Optional[Tuple[int, int, int]] = None,
    ) -> Fighter:
        """Adds a fighter to the scene."""
        ground_contact = y if y is not None else self.ground_y
        if color is None:
            # High-contrast default colors: vibrant red vs ice blue
            palette = [(240, 70, 70), (70, 170, 255), (100, 240, 120), (255, 200, 50)]
            color = palette[len(self.fighters) % len(palette)]

        if facing is None:
            # Face center / towards opponent
            facing = 1 if x < self.width / 2 else -1

        fighter = Fighter(
            name=name,
            x=x,
            y=ground_contact,
            facing=facing,
            color=color,
            line_width=line_width,
            scale=scale,
            health=health,
            render_style=render_style,
            proportions=proportions,
            design=design,
            stats=stats,
            headband_color=headband_color,
        )
        self.fighters.append(fighter)
        self._fighter_map[name] = fighter
        return fighter

    def fighter(self, name: str, **kwargs) -> Fighter:
        """Alias for add_fighter / fighter retrieval."""
        if name in self._fighter_map and not kwargs:
            return self._fighter_map[name]
        return self.add_fighter(name, **kwargs)

    def background(self, style: str):
        """Sets environment background style ('plain', 'dojo', 'grid', 'dark')."""
        self.bg_style = style

    def caption(self, text: str, start: float, end: float):
        """Adds text caption on screen during [start, end] seconds."""
        self.captions.append((text, float(start), float(end)))

    def at(self, start_time: float, action: Action):
        """Schedules a choreography action at start_time."""
        self.timeline.at(start_time, action)

    def parallel(self, *actions: Action) -> ParallelAction:
        """Groups actions to execute concurrently."""
        return ParallelAction(list(actions))

    def sound(self, start_time: float, name: str, pitch: Optional[float] = None, gain: Optional[float] = None) -> SoundAction:
        """Schedules a sound effect at start_time."""
        action = SoundAction(name, pitch=pitch, gain=gain)
        self.at(start_time, action)
        return action

    def callback(self, start_time: float, fn: Callable[["FightScene"], None]) -> CallbackAction:
        """Runs fn(scene) at start_time."""
        action = CallbackAction(fn)
        self.at(start_time, action)
        return action

    def camera_shot(
        self,
        start_time: float,
        focus: Optional[Union[Fighter, Tuple[Fighter, ...], List[Fighter]]] = None,
        x: Optional[float] = None,
        y: Optional[float] = None,
        zoom: Optional[float] = None,
        cut: bool = False,
        transition: float = 0.4,
        hold: float = 0.6,
    ) -> CameraAction:
        """Schedules a director-style camera shot (cut/pan/zoom) at start_time.

        `focus` can be a single fighter (close-up) or a list/tuple of
        fighters (frames their midpoint, e.g. a wide two-shot). Explicit
        x/y/zoom override the focus-derived values. Pass cut=True for an
        instant hard cut instead of a smooth pan/zoom transition.

        Example — wide shot on both fighters, then a hard cut to a close-up
        on the attacker right before their strike lands:
            scene.camera_shot(0.0, focus=(a, b), zoom=0.85, hold=1.2)
            scene.camera_shot(1.2, focus=a, zoom=1.35, cut=True, hold=0.8)
        """
        action = CameraAction(
            focus=focus, x=x, y=y, zoom=zoom,
            cut=cut, transition=transition, hold=hold,
        )
        self.at(start_time, action)
        return action

    # ========================================================================
    # TIME CONTROL: slow motion and hit-stop
    # ========================================================================

    def slowmo(self, start: float, end: float, factor: float = 0.3, ease: float = 0.12, _dynamic: bool = False):
        """Plays scene time [start, end] at `factor` speed (0.3 = 30%).

        `ease` seconds are spent ramping into and out of the slow section.
        The video gets longer by exactly the time this adds.
        """
        region = SlowMoRegion(float(start), float(end), max(MIN_TIME_SCALE, float(factor)), max(0.0, float(ease)))
        (self._slowmo_dynamic if _dynamic else self._slowmo_static).append(region)

    def hit_stop(self, duration: float):
        """Freezes the action for `duration` video seconds (impact emphasis)."""
        self._hitstop_left = max(self._hitstop_left, duration)

    def time_scale_at(self, t: float) -> float:
        scale = 1.0
        for r in self._slowmo_static + self._slowmo_dynamic:
            if r.start <= t < r.end:
                weight = 1.0
                if r.ease > 0.0:
                    weight = max(0.0, min(1.0, (t - r.start) / r.ease, (r.end - t) / r.ease))
                scale = min(scale, 1.0 + (r.factor - 1.0) * weight)
        return max(MIN_TIME_SCALE, scale)

    def sim_to_video(self, scene_time: float) -> float:
        """Converts a scene timestamp to the video time it appears at."""
        sims, vids = self._map_sim, self._map_video
        if scene_time <= 0.0:
            return scene_time
        i = bisect.bisect_left(sims, scene_time)
        if i >= len(sims):
            return vids[-1] + (scene_time - sims[-1])
        if i == 0:
            return vids[0]
        s0, s1, v0, v1 = sims[i - 1], sims[i], vids[i - 1], vids[i]
        if s1 - s0 <= 1e-12:
            return v1
        return v0 + (scene_time - s0) / (s1 - s0) * (v1 - v0)

    # ========================================================================
    # WARNINGS / STRICT MODE
    # ========================================================================

    def warn(self, message: str):
        """Records impossible choreography; raises ChoreographyError in strict mode."""
        if message not in self.warnings:
            self.warnings.append(message)
        if self.strict:
            raise ChoreographyError(message)

    def report_whiff(self, action) -> None:
        self.stats["whiffs"] += 1
        d = action.defender
        dist = abs(action.fighter.x - d.x) if d is not None else 0.0
        self.warn(f"t={action.started_at:.2f}s: {action.fighter.name}'s {action.label} never reached "
                  f"{d.name if d else 'its target'} (distance {dist:.0f}px)")

    # ========================================================================
    # COMBAT
    # ========================================================================

    def resolve_attack(self, attacker: Fighter, defender: Fighter, hitbox: Hitbox) -> str:
        """Resolves one strike: collision, dodge/parry/block, damage, reactions, KO.

        Returns "miss", "ignored", "dodged", "parried", "blocked", "hit" or "ko".
        """
        if defender.ko:
            return "ignored"
        res = find_hit(hitbox, defender.get_hurtbox())
        if res is None:
            return "miss"

        now = self.current_time
        impact_x = (hitbox.x + defender.x) / 2.0
        impact_y = hitbox.y
        nominal = hitbox.damage * attacker.stats.power
        is_low = hitbox.attack_type == "sweep"  # sweeps go under a raised guard
        glance = False

        if defender.state == "dodging":
            elapsed = now - defender.dodge_started_at
            if defender.dodge_started_at == float("-inf") or DODGE_INVULNERABLE[0] <= elapsed <= DODGE_INVULNERABLE[1]:
                self.stats["dodges"] += 1
                return "dodged"
            glance = True  # mistimed dodge: only a glancing blow

        if defender.state == "blocking" and not is_low:
            if now - defender.block_started_at <= PERFECT_BLOCK_WINDOW:
                # Perfect block: no damage, attacker is thrown off balance.
                attacker.state = "hit"
                attacker.set_animation("hit", loop=False)
                self.effects.trigger_parry(impact_x, impact_y)
                self.audio.schedule_sound(now, "clang")
                self.camera.shake(intensity=10.0, duration=0.2)
                self.hit_stop(HIT_STOP_PARRY)
                self.stats["parries"] += 1
                return "parried"
            is_slash = hitbox.attack_type == "slash"
            chip = nominal * (0.15 if is_slash else 0.2) / defender.stats.defense
            defender.take_damage(chip, lethal=hitbox.finisher)
            if is_slash:
                # Blade meets guard: steel sparks.
                self.audio.schedule_sound(now, "clang")
                self.effects.trigger_weapon_clash((attacker.x + defender.x) / 2.0, attacker.y - 140.0)
                self.camera.shake(intensity=8.0, duration=0.2)
            else:
                self.effects.trigger_hit_effect(impact_x, impact_y, is_blocked=True)
                self.audio.schedule_sound(now, "block")
                self.camera.shake(intensity=6.0, duration=0.15)
            defender.apply_impulse(hitbox.knockback_x * BLOCK_PUSHBACK, 0.0)  # block-stun pushback
            self.stats["blocks"] += 1
            if defender.health <= 0.0 and not defender.ko:
                self._trigger_ko(defender, attacker)
                return "ko"
            return "blocked"

        # Direct hit!
        is_heavy = nominal >= 20.0
        damage = nominal * res.multiplier / defender.stats.defense
        if glance:
            damage *= GLANCE_FACTOR
        if hitbox.finisher:
            damage = max(damage, defender.health)
        dealt = defender.take_damage(damage, lethal=hitbox.finisher)

        # Trigger sound & visual impact
        sound_name = "kick" if hitbox.attack_type in ("kick", "sweep") else "punch"
        self.audio.schedule_sound(now, sound_name)
        self.effects.trigger_hit_effect(impact_x, impact_y, is_blocked=False, is_heavy=is_heavy)
        self.camera.shake(intensity=14.0 if is_heavy else 9.0, duration=0.25)
        if is_heavy:
            self.hit_stop(HIT_STOP_HEAVY)

        # Turn defender toward attacker on hit
        defender.face_fighter(attacker)

        # Hit reaction animation + physical impulse.
        if is_low and not glance:
            defender.state = "fallen"  # swept off their feet
            defender.set_animation("fall", loop=False)
        elif is_heavy:
            defender.state = "knockback"
            defender.set_animation("knockback", loop=False)
            defender.apply_impulse(hitbox.knockback_x, hitbox.knockback_y)
        else:
            defender.state = "hit"
            defender.set_animation("hit", loop=False)

        self.stats["hits"].append({
            "time": now, "attacker": attacker.name, "defender": defender.name,
            "type": hitbox.attack_type, "region": res.region, "damage": dealt,
            "defender_health": defender.health,
        })
        if defender.health <= 0.0 and not defender.ko:
            self._trigger_ko(defender, attacker)
            return "ko"
        return "hit"

    def _trigger_ko(self, defender: Fighter, attacker: Fighter):
        """Knockout: fighter drops, the moment freezes, then plays in slow motion."""
        now = self.current_time
        defender.ko = True
        defender.state = "fallen"
        defender.set_animation("fall", loop=False)
        self.stats["kos"].append({"time": now, "fighter": defender.name, "by": attacker.name})
        self.hit_stop(HIT_STOP_KO)
        self.slowmo(now, now + KO_SLOWMO_LENGTH, KO_SLOWMO_FACTOR, ease=0.1, _dynamic=True)
        self.audio.schedule_sound(now + 0.35, "fall")
        self.effects.trigger_dust_puff(defender.x, defender.y, count=16)
        self.camera.shake(intensity=16.0, duration=0.35)
        for callback in self.on_ko:
            callback(self, defender, attacker)

    # ========================================================================
    # SIMULATION
    # ========================================================================

    def update(self, dt: float):
        """Advances the scene by one video frame of `dt` seconds."""
        self.video_time += dt
        if self._hitstop_left > 0.0:
            # Frozen on impact; the camera shake keeps ringing.
            self._hitstop_left = max(0.0, self._hitstop_left - dt)
            self.camera.update(dt)
        else:
            self._advance(dt * self.time_scale_at(self.current_time))
        self._map_sim.append(self.current_time)
        self._map_video.append(self.video_time)

    def _advance(self, dt: float):
        """Simulates `dt` seconds of scene time, including fighter physics."""
        self.current_time += dt

        # Scripted actions run first so impulses they apply (a jump, a
        # knockback) take effect in the same frame instead of one frame late.
        self.timeline.update(self.current_time, dt, self)

        # Actions such as walk_to() intentionally control horizontal placement;
        # push that into the physics body, then integrate motion.
        for f in self.fighters:
            f.sync_to_physics()
            f.physics.update(dt)
            f.sync_from_physics()
        self.camera.frame_fighters(self.fighters)
        self.camera.update(dt)
        self.effects.update(dt)

    def draw(self, surface: pygame.Surface):
        """Renders the current frame into the given surface."""
        # 1. Background & floor
        self.renderer.draw_background(surface, self.bg_style, self.camera, ground_y=self.ground_y)

        # 2. Fighters
        for f in self.fighters:
            self.renderer.draw_fighter(surface, f, self.camera)

        # 3. Particle effects & shockwaves
        self.effects.draw(surface, self.camera.world_to_screen)

        # 4. Captions
        self.renderer.draw_captions(surface, self.captions, self.current_time)

        # 5. UI Health Bars
        if self.show_ui:
            self.renderer.draw_health_bars(surface, self.fighters)

    def reset(self):
        """Resets fight state, physics, effects, camera, and audio to the beginning."""
        self.current_time = 0.0
        self.video_time = 0.0
        self._hitstop_left = 0.0
        self._slowmo_dynamic = []
        self._map_sim = [0.0]
        self._map_video = [0.0]
        self.stats = _new_stats()
        self.warnings = []
        self.rng.seed(self.seed)
        self.timeline.reset()
        self.audio.reset()
        self.effects = EffectsManager(rng=self.rng)
        self.camera = Camera(viewport_width=self.width, viewport_height=self.height, rng=self.rng)
        for f in self.fighters:
            f.reset()

    def snapshot(self) -> Dict[str, Any]:
        """Captures the full simulation state so it can be restored later
        (used by the preview to scrub backwards without re-simulating)."""
        cam_rng, eff_rng = self.camera.rng, self.effects.rng
        self.camera.rng = self.effects.rng = None  # re-linked on restore
        try:
            snap = copy.deepcopy({
                "fighters": self.fighters,
                "timeline": self.timeline,
                "camera": self.camera,
                "effects": self.effects,
                "audio_events": list(self.audio.scheduled_events),
                "slowmo_dynamic": self._slowmo_dynamic,
                "stats": self.stats,
                "warnings": self.warnings,
            })
        finally:
            self.camera.rng, self.effects.rng = cam_rng, eff_rng
        snap["scalars"] = {
            "current_time": self.current_time, "video_time": self.video_time,
            "hitstop": self._hitstop_left,
            "map_sim": list(self._map_sim), "map_video": list(self._map_video),
        }
        snap["rng_state"] = self.rng.getstate()
        snap["audio_rng_state"] = copy.deepcopy(self.audio.rng.bit_generator.state)
        return snap

    def restore(self, snap: Dict[str, Any]):
        """Returns to a state captured by snapshot(). The snapshot stays reusable.
        Note: Fighter objects are replaced by copies, so re-fetch them via
        scene.fighters / scene.fighter(name) after restoring."""
        keys = ("fighters", "timeline", "camera", "effects", "audio_events",
                "slowmo_dynamic", "stats", "warnings")
        state = copy.deepcopy({k: snap[k] for k in keys})
        self.fighters = state["fighters"]
        self._fighter_map = {f.name: f for f in self.fighters}
        self.timeline = state["timeline"]
        self.camera, self.effects = state["camera"], state["effects"]
        self.camera.rng = self.effects.rng = self.rng
        self.audio.scheduled_events = state["audio_events"]
        self._slowmo_dynamic = state["slowmo_dynamic"]
        self.stats, self.warnings = state["stats"], state["warnings"]
        sc = snap["scalars"]
        self.current_time, self.video_time, self._hitstop_left = sc["current_time"], sc["video_time"], sc["hitstop"]
        self._map_sim, self._map_video = list(sc["map_sim"]), list(sc["map_video"])
        self.rng.setstate(snap["rng_state"])
        self.audio.rng.bit_generator.state = copy.deepcopy(snap["audio_rng_state"])

    # ========================================================================
    # RENDER & PREVIEW MODES
    # ========================================================================

    def _total_scene_duration(self, duration: Optional[float]) -> float:
        return duration if duration is not None else self.timeline.get_total_duration(tail_padding=1.2)

    def _run_simulation(self, total_scene_duration: float) -> int:
        """Runs the whole scene headlessly from the start; returns video frames used."""
        dt = 1.0 / self.fps
        max_frames = int(total_scene_duration * self.fps / MIN_TIME_SCALE) + self.fps
        self.reset()
        frames = 0
        while self.current_time < total_scene_duration - 1e-6 and frames < max_frames:
            self.update(dt)
            frames += 1
        return frames

    def simulate(self, duration: Optional[float] = None) -> Dict[str, Any]:
        """Dry-runs the fight without drawing anything and returns its stats
        (hits, blocks, dodges, parries, whiffs, kos). Also fills scene.warnings."""
        self._run_simulation(self._total_scene_duration(duration))
        return self.stats

    def render(
        self,
        output_path: str = "output/videos/fight001.mp4",
        duration: Optional[float] = None,
        progress_callback: Optional[Callable[[int, int, float], None]] = None,
        verbose: bool = True,
    ) -> bool:
        """Renders complete video to MP4 using FFmpeg pipe. Returns True on success.

        progress_callback(frame, total_frames, fraction) is called as frames are written.
        """
        find_ffmpeg()  # fail fast, before doing any work
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        pygame.init()

        total_scene = self._total_scene_duration(duration)
        # Pass 1: simulate to learn the video length (slow motion / hit-stop
        # stretch it), schedule sounds, and collect choreography warnings.
        total_frames = self._run_simulation(total_scene)
        video_duration = self.video_time
        warnings = list(self.warnings)
        dt = 1.0 / self.fps

        if verbose:
            print(f"🎬 Rendering Stick Fight: {video_duration:.2f}s ({total_frames} frames) at {self.fps} FPS...")
            print(f"📐 Resolution: {self.width}x{self.height} -> {output_path}")
            if warnings:
                print(f"⚠️  {len(warnings)} choreography warning(s):")
                for w in warnings[:8]:
                    print(f"     - {w}")
                if len(warnings) > 8:
                    print(f"     ... and {len(warnings) - 8} more")

        fd, temp_audio = tempfile.mkstemp(prefix="stickfight_audio_", suffix=".wav")
        os.close(fd)
        try:
            self.audio.export_mix_wav(video_duration, temp_audio, time_map=self.sim_to_video)

            # Pass 2: render the identical (seeded) simulation frame by frame.
            self.reset()
            surface = pygame.Surface((self.width, self.height))
            exporter = VideoExporter(output_path, self.width, self.height, self.fps, audio_path=temp_audio)
            exporter.start()
            start_time = time.time()
            try:
                for frame_idx in range(total_frames):
                    self.update(dt)
                    self.draw(surface)
                    exporter.write_frame(surface)

                    frac = (frame_idx + 1) / max(1, total_frames)
                    if progress_callback:
                        progress_callback(frame_idx + 1, total_frames, frac)
                    if verbose and (frame_idx % (self.fps * 2) == 0 or frame_idx == total_frames - 1):
                        fps_render = (frame_idx + 1) / max(0.01, time.time() - start_time)
                        print(f"   [{int(frac * 100):3d}%] Frame {frame_idx + 1}/{total_frames} ({fps_render:.1f} fps)")
            except BaseException:
                exporter.abort()
                raise
            ret = exporter.finish()
        finally:
            try:
                os.remove(temp_audio)
            except OSError:
                pass

        ok = ret == 0 and os.path.exists(output_path)
        if verbose:
            if ok:
                file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
                print(f"✅ Video render complete: {output_path} ({file_size_mb:.2f} MB)")
            else:
                print(f"❌ Render failed with exit code: {ret}")
        return ok

    def preview(self, window_width: int = 540, window_height: int = 960):
        """Opens interactive animation preview window."""
        pygame.init()
        screen = pygame.display.set_mode((window_width, window_height))
        pygame.display.set_caption("Stick Fight Engine — Preview (Space: Play/Pause, R: Restart, Left/Right: Scrub)")
        clock = pygame.time.Clock()

        # Canvas surface at native resolution
        canvas = pygame.Surface((self.width, self.height))
        total_duration = self.timeline.get_total_duration(tail_padding=1.2)
        dt = 1.0 / self.fps

        # Checkpoints (one per second of playback) make scrubbing backwards
        # instant: restore the nearest one and step forward a few frames.
        checkpoints: Dict[int, Dict[str, Any]] = {}

        def checkpoint():
            key = int(self.current_time)
            if key not in checkpoints:
                checkpoints[key] = self.snapshot()

        def restart():
            self.reset()
            checkpoints.clear()
            checkpoint()

        def seek(target_t: float):
            best = None
            for snap in checkpoints.values():
                t = snap["scalars"]["current_time"]
                if t <= target_t and (best is None or t > best["scalars"]["current_time"]):
                    best = snap
            if best is None:
                restart()
            else:
                self.restore(best)
            while self.current_time < target_t:
                self.update(dt)

        playing = True
        restart()

        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_SPACE:
                        playing = not playing
                    elif event.key == pygame.K_r:
                        restart()
                    elif event.key == pygame.K_RIGHT:
                        # Step forward 0.2s
                        self.update(0.2)
                        checkpoint()
                    elif event.key == pygame.K_LEFT:
                        seek(max(0.0, self.current_time - 0.5))

            if playing:
                if self.current_time < total_duration:
                    self.update(dt)
                    checkpoint()
                else:
                    playing = False

            # Draw to native canvas
            self.draw(canvas)

            # Scale to preview window
            scaled = pygame.transform.smoothscale(canvas, (window_width, window_height))
            screen.blit(scaled, (0, 0))

            # Bottom scrubber bar overlay on preview window
            prog = min(1.0, self.current_time / max(0.01, total_duration))
            bar_y = window_height - 10
            pygame.draw.rect(screen, (50, 50, 50), (0, bar_y, window_width, 10))
            pygame.draw.rect(screen, (70, 200, 100), (0, bar_y, int(window_width * prog), 10))

            pygame.display.flip()
            clock.tick(self.fps)

        pygame.quit()
