"""
FightScene: Core orchestrator integrating fighters, timeline choreography,
physics, combat hitboxes, camera, audio, previewing, and video rendering.
"""

from __future__ import annotations
import os
import sys
import time
from typing import List, Dict, Optional, Tuple, Any, Union
import pygame

from stickfight.engine.fighter import Fighter
from stickfight.engine.timeline import Timeline
from stickfight.engine.camera import Camera
from stickfight.engine.effects import EffectsManager
from stickfight.engine.audio import AudioManager
from stickfight.engine.renderer import Renderer, VideoExporter
from stickfight.engine.collision import check_hit, Hitbox
from stickfight.engine.skeleton import BodyProportions
from stickfight.scripting.actions import Action, HitAction, KnockbackAction, ParallelAction, CameraAction


class FightScene:
    def __init__(self, width: int = 1080, height: int = 1920, fps: int = 30, ground_y: float = 1500.0):
        self.width = width
        self.height = height
        self.fps = fps
        self.ground_y = ground_y
        self.bg_style = "plain"

        self.fighters: List[Fighter] = []
        self._fighter_map: Dict[str, Fighter] = {}

        self.timeline = Timeline()
        self.camera = Camera(viewport_width=width, viewport_height=height)
        self.effects = EffectsManager()
        self.audio = AudioManager()
        self.renderer = Renderer(width=width, height=height)

        self.captions: List[Tuple[str, float, float]] = []
        self.current_time: float = 0.0
        self.show_ui: bool = True

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
            render_style=render_style,
            proportions=proportions,
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

    def resolve_attack(self, attacker: Fighter, defender: Fighter, hitbox: Hitbox):
        """Evaluates collision and resolves damage, blocks, dodges, and reactions."""
        hurtbox = defender.get_hurtbox()

        if not check_hit(hitbox, hurtbox):
            return

        impact_x = (hitbox.x + defender.x) / 2.0
        impact_y = hitbox.y

        if defender.state == "dodging":
            # Defender dodged cleanly!
            return

        if defender.state == "blocking":
            # Deflected!
            reduced_damage = hitbox.damage * 0.2
            defender.health = max(0.0, defender.health - reduced_damage)
            self.effects.trigger_hit_effect(impact_x, impact_y, is_blocked=True)
            self.audio.schedule_sound(self.current_time, "block")
            self.camera.shake(intensity=6.0, duration=0.15)
            return

        # Direct hit!
        is_heavy = hitbox.damage >= 20.0
        defender.health = max(0.0, defender.health - hitbox.damage)

        # Trigger sound & visual impact
        sound_name = "kick" if hitbox.attack_type == "kick" else "punch"
        self.audio.schedule_sound(self.current_time, sound_name)
        self.effects.trigger_hit_effect(impact_x, impact_y, is_blocked=False, is_heavy=is_heavy)
        self.camera.shake(intensity=14.0 if is_heavy else 9.0, duration=0.25)

        # Turn defender toward attacker on hit
        defender.face_fighter(attacker)

        # Hit reaction animation + physical impulse.
        if is_heavy:
            defender.state = "knockback"
            defender.set_animation("knockback", loop=False)
            defender.apply_impulse(hitbox.knockback_x, hitbox.knockback_y)
        else:
            defender.state = "hit"
            defender.set_animation("hit", loop=False)

    def update(self, dt: float):
        """Simulates 1 tick of the scene, including fighter physics."""
        self.current_time += dt

        # Advance existing physical motion first. Scripted actions may then
        # reposition fighters horizontally and the body is synchronized below.
        for f in self.fighters:
            f.physics.update(dt)
            f.sync_from_physics()

        self.timeline.update(self.current_time, dt, self)

        # Actions such as walk_to() intentionally control horizontal placement;
        # preserve that choreography while keeping the physics body synchronized.
        for f in self.fighters:
            f.sync_to_physics()
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
        self.timeline.reset()
        self.audio.scheduled_events.clear()
        self.effects = EffectsManager()
        self.camera = Camera(viewport_width=self.width, viewport_height=self.height)
        for f in self.fighters:
            f.health = f.max_health
            f.state = "idle"
            f.set_animation("idle")
            f.reset_physics()

    # ========================================================================
    # RENDER & PREVIEW MODES
    # ========================================================================

    def render(self, output_path: str = "output/videos/fight001.mp4", duration: Optional[float] = None):
        """Renders complete video to MP4 using FFmpeg pipe."""
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()

        total_duration = duration if duration is not None else self.timeline.get_total_duration(tail_padding=1.2)
        total_frames = int(total_duration * self.fps)
        dt = 1.0 / self.fps

        print(f"🎬 Rendering Stick Fight: {total_duration:.2f}s ({total_frames} frames) at {self.fps} FPS...")
        print(f"📐 Resolution: {self.width}x{self.height} -> {output_path}")

        # 1. Generate master audio mix
        temp_audio = "/tmp/stickfight_audio_mix.wav"
        # Pre-simulate timeline to schedule sound events
        self.reset()
        sim_t = 0.0
        for _ in range(total_frames):
            self.update(dt)
        self.audio.export_mix_wav(total_duration, temp_audio)

        # 2. Reset scene for actual frame rendering
        self.reset()
        surface = pygame.Surface((self.width, self.height))
        exporter = VideoExporter(output_path, self.width, self.height, self.fps, audio_path=temp_audio)
        exporter.start()

        start_time = time.time()
        for frame_idx in range(total_frames):
            self.update(dt)
            self.draw(surface)
            exporter.write_frame(surface)

            if frame_idx % (self.fps * 2) == 0 or frame_idx == total_frames - 1:
                pct = int((frame_idx + 1) / total_frames * 100)
                elapsed = time.time() - start_time
                fps_render = (frame_idx + 1) / max(0.01, elapsed)
                print(f"   [{pct:3d}%] Frame {frame_idx + 1}/{total_frames} ({fps_render:.1f} fps)")

        ret = exporter.finish()
        if os.path.exists(temp_audio):
            try:
                os.remove(temp_audio)
            except Exception:
                pass

        if ret == 0 and os.path.exists(output_path):
            file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
            print(f"✅ Video render complete: {output_path} ({file_size_mb:.2f} MB)")
        else:
            print(f"❌ Render failed with exit code: {ret}")

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

        playing = True
        self.reset()

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
                        self.reset()
                    elif event.key == pygame.K_RIGHT:
                        # Step forward 0.2s
                        self.update(0.2)
                    elif event.key == pygame.K_LEFT:
                        # Jump backward
                        target_t = max(0.0, self.current_time - 0.5)
                        self.reset()
                        while self.current_time < target_t:
                            self.update(dt)

            if playing:
                if self.current_time < total_duration:
                    self.update(dt)
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
