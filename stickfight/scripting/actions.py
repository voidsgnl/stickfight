"""
Action descriptors for scripted fight choreography.
Encapsulates high-level actions (walk, punch, kick, block, dodge, fall, combos).
"""

from __future__ import annotations
from typing import TYPE_CHECKING, List, Optional, Union, Tuple
import math

if TYPE_CHECKING:
    from stickfight.engine.fighter import Fighter
    from stickfight.engine.scene import FightScene


class Action:
    """Base class for all timeline fight actions."""
    def __init__(self, fighter: Fighter, duration: float):
        self.fighter = fighter
        self.duration = duration
        self._started = False

    def on_start(self, scene: FightScene):
        self._started = True

    def update(self, scene: FightScene, local_t: float, dt: float):
        """Called every frame while this action is active (0.0 <= local_t <= duration)."""
        pass

    def on_finish(self, scene: FightScene):
        pass

    def _impact_event(self, scene: FightScene) -> bool:
        """Fire this action's authored impact exactly once."""
        if getattr(self, "_impact_fired", False):
            return False
        if not self.fighter or not self.fighter.is_attack_impact():
            return False
        self._impact_fired = True
        return True


class WalkToAction(Action):
    def __init__(self, fighter: Fighter, target_x: float, speed: float = 240.0, duration: Optional[float] = None):
        self.target_x = float(target_x)
        self.speed = float(speed)
        self.start_x: float = 0.0
        self.has_custom_duration = duration is not None
        computed_dur = duration if duration is not None else 1.0
        super().__init__(fighter, computed_dur)

    def on_start(self, scene: FightScene):
        super().on_start(scene)
        self.start_x = self.fighter.x
        dist = abs(self.target_x - self.start_x)
        if not self.has_custom_duration:
            calc_dur = max(0.2, dist / self.speed)
            self.duration = calc_dur
        self.fighter.face_target(self.target_x)
        self.fighter.set_animation("walk")

    def update(self, scene: FightScene, local_t: float, dt: float):
        progress = max(0.0, min(1.0, local_t / max(1e-5, self.duration)))
        self.fighter.x = self.start_x + (self.target_x - self.start_x) * progress
        # Update walk animation
        self.fighter.update_animation(dt)

    def on_finish(self, scene: FightScene):
        self.fighter.x = self.target_x
        self.fighter.set_animation("idle")


class RunToAction(WalkToAction):
    def __init__(self, fighter: Fighter, target_x: float, speed: float = 450.0, duration: Optional[float] = None):
        super().__init__(fighter, target_x, speed=speed, duration=duration)


class PunchAction(Action):
    def __init__(self, attacker: Fighter, defender: Optional[Fighter] = None, duration: float = 0.45, damage: float = 15.0):
        super().__init__(attacker, duration)
        self.defender = defender
        self.damage = damage
        self.hit_registered = False

    def on_start(self, scene: FightScene):
        super().on_start(scene)
        if self.defender:
            self.fighter.face_fighter(self.defender)
        self.fighter.set_state("attack", clip_name="punch")
        self.hit_registered = False
        scene.audio.schedule_sound(scene.current_time + 0.12, "whoosh")

    def update(self, scene: FightScene, local_t: float, dt: float):
        self.fighter.update_animation(dt)
        strike_time = 0.18
        if not self.hit_registered and self._impact_event(scene):
            self.hit_registered = True
            # Check attack collision against defender
            if self.defender:
                hitbox = self.fighter.get_hitbox()
                if hitbox:
                    hitbox.damage = self.damage
                    scene.resolve_attack(self.fighter, self.defender, hitbox)

    def on_finish(self, scene: FightScene):
        self.fighter.set_state("idle")


class KickAction(Action):
    def __init__(self, attacker: Fighter, defender: Optional[Fighter] = None, duration: float = 0.55, damage: float = 22.0):
        super().__init__(attacker, duration)
        self.defender = defender
        self.damage = damage
        self.hit_registered = False

    def on_start(self, scene: FightScene):
        super().on_start(scene)
        if self.defender:
            self.fighter.face_fighter(self.defender)
        self.fighter.set_state("attack", clip_name="kick")
        self.hit_registered = False
        scene.audio.schedule_sound(scene.current_time + 0.18, "whoosh")

    def update(self, scene: FightScene, local_t: float, dt: float):
        self.fighter.update_animation(dt)
        strike_time = 0.25
        if not self.hit_registered and self._impact_event(scene):
            self.hit_registered = True
            if self.defender:
                hitbox = self.fighter.get_hitbox()
                if hitbox:
                    hitbox.damage = self.damage
                    scene.resolve_attack(self.fighter, self.defender, hitbox)

    def on_finish(self, scene: FightScene):
        self.fighter.set_state("idle")


class BlockAction(Action):
    def __init__(self, fighter: Fighter, duration: float = 0.5):
        super().__init__(fighter, duration)

    def on_start(self, scene: FightScene):
        super().on_start(scene)
        self.fighter.state = "blocking"
        self.fighter.set_animation("block", loop=False)

    def update(self, scene: FightScene, local_t: float, dt: float):
        self.fighter.update_animation(dt)

    def on_finish(self, scene: FightScene):
        self.fighter.state = "idle"
        self.fighter.set_animation("idle")


class DodgeAction(Action):
    def __init__(self, fighter: Fighter, duration: float = 0.5):
        super().__init__(fighter, duration)

    def on_start(self, scene: FightScene):
        super().on_start(scene)
        self.fighter.state = "dodging"
        self.fighter.set_animation("dodge", loop=False)
        scene.audio.schedule_sound(scene.current_time + 0.05, "whoosh")

    def update(self, scene: FightScene, local_t: float, dt: float):
        self.fighter.update_animation(dt)

    def on_finish(self, scene: FightScene):
        self.fighter.state = "idle"
        self.fighter.set_animation("idle")


class HitAction(Action):
    def __init__(self, fighter: Fighter, duration: float = 0.4):
        super().__init__(fighter, duration)

    def on_start(self, scene: FightScene):
        super().on_start(scene)
        self.fighter.state = "hit"
        self.fighter.set_animation("hit", loop=False)

    def update(self, scene: FightScene, local_t: float, dt: float):
        self.fighter.update_animation(dt)

    def on_finish(self, scene: FightScene):
        self.fighter.state = "idle"
        self.fighter.set_animation("idle")


class KnockbackAction(Action):
    def __init__(self, fighter: Fighter, distance: float = 140.0, duration: float = 0.7):
        super().__init__(fighter, duration)
        self.distance = distance
        self.start_x = 0.0

    def on_start(self, scene: FightScene):
        super().on_start(scene)
        self.fighter.state = "knockback"
        self.start_x = self.fighter.x
        self.fighter.set_animation("knockback", loop=False)

    def update(self, scene: FightScene, local_t: float, dt: float):
        self.fighter.update_animation(dt)
        prog = max(0.0, min(1.0, local_t / max(1e-5, self.duration)))
        # Quadratic decay slide backward
        slide_prog = 1.0 - (1.0 - prog) ** 2
        direction = -self.fighter.facing
        self.fighter.x = self.start_x + direction * self.distance * slide_prog

    def on_finish(self, scene: FightScene):
        self.fighter.state = "idle"
        self.fighter.set_animation("idle")


class FallAction(Action):
    def __init__(self, fighter: Fighter, duration: float = 1.2):
        super().__init__(fighter, duration)
        self.start_x = 0.0
        self.thump_played = False

    def on_start(self, scene: FightScene):
        super().on_start(scene)
        self.fighter.state = "fallen"
        self.start_x = self.fighter.x
        # A scripted fall ends on the ground; clear any previous airborne state.
        self.fighter.physics.vx = 0.0
        self.fighter.physics.vy = 0.0
        self.fighter.physics.is_grounded = True
        self.fighter.physics.y = self.fighter.y
        self.fighter.set_animation("fall", loop=False)
        self.thump_played = False

    def update(self, scene: FightScene, local_t: float, dt: float):
        self.fighter.update_animation(dt)
        prog = max(0.0, min(1.0, local_t / max(1e-5, self.duration)))
        # Move back during fall
        if prog <= 0.6:
            self.fighter.x = self.start_x - self.fighter.facing * (70.0 * (prog / 0.6))
        if not self.thump_played and local_t >= 0.5:
            self.thump_played = True
            scene.audio.schedule_sound(scene.current_time, "fall")
            scene.effects.trigger_dust_puff(self.fighter.x, self.fighter.y, count=16)
            scene.camera.shake(intensity=8.0, duration=0.2)

    def on_finish(self, scene: FightScene):
        # Remains down
        self.fighter.state = "fallen"


class JumpAction(Action):
    def __init__(self, fighter: Fighter, height: float = 160.0, duration: float = 0.65):
        super().__init__(fighter, duration)
        self.height = height

    def on_start(self, scene: FightScene):
        super().on_start(scene)
        self.fighter.state = "jumping"
        # Use the physics body for the actual launch; animation supplies pose only.
        self.fighter.apply_impulse(0.0, -math.sqrt(2.0 * self.fighter.physics.gravity * self.height))
        self.fighter.set_animation("jump", loop=False)
        scene.effects.trigger_dust_puff(self.fighter.x, self.fighter.y, count=8)

    def update(self, scene: FightScene, local_t: float, dt: float):
        self.fighter.update_animation(dt)

    def on_finish(self, scene: FightScene):
        # Do not snap an airborne fighter back to the floor when the animation
        # clip ends; physics owns the landing position.
        self.fighter.state = "idle" if self.fighter.physics.is_grounded else "jumping"
        self.fighter.set_animation("idle")
        if self.fighter.physics.is_grounded:
            scene.effects.trigger_dust_puff(self.fighter.x, self.fighter.y, count=8)


class CounterAction(Action):
    """Parry dodge followed immediately by counter punch."""
    def __init__(self, attacker: Fighter, defender: Fighter, duration: float = 0.7):
        super().__init__(attacker, duration)
        self.defender = defender
        self.punch_started = False

    def on_start(self, scene: FightScene):
        super().on_start(scene)
        self.fighter.face_fighter(self.defender)
        self.fighter.state = "dodging"
        self.fighter.set_animation("dodge", loop=False)
        self.punch_started = False

    def update(self, scene: FightScene, local_t: float, dt: float):
        self.fighter.update_animation(dt)
        if not self.punch_started and local_t >= 0.25:
            self.punch_started = True
            self.fighter.set_animation("punch", loop=False)
            scene.audio.schedule_sound(scene.current_time, "whoosh")
        if self.punch_started and local_t >= 0.42 and self.defender:
            hitbox = self.fighter.get_hitbox()
            if hitbox:
                scene.resolve_attack(self.fighter, self.defender, hitbox)
                self.defender = None

    def on_finish(self, scene: FightScene):
        self.fighter.state = "idle"
        self.fighter.set_animation("idle")


class ParallelAction(Action):
    """Executes multiple actions concurrently."""
    def __init__(self, actions: List[Action]):
        self.actions = actions
        max_dur = max((a.duration for a in actions), default=0.0)
        # Pass first fighter as representative
        super().__init__(actions[0].fighter if actions else None, max_dur)

    def on_start(self, scene: FightScene):
        super().on_start(scene)
        for act in self.actions:
            act.on_start(scene)

    def update(self, scene: FightScene, local_t: float, dt: float):
        for act in self.actions:
            if local_t <= act.duration:
                act.update(scene, local_t, dt)

    def on_finish(self, scene: FightScene):
        for act in self.actions:
            act.on_finish(scene)


class UppercutAction(Action):
    """Heavy rising fist driving upward into sky, launching defender airborne."""
    def __init__(self, attacker: Fighter, defender: Optional[Fighter] = None, duration: float = 0.55, damage: float = 26.0):
        super().__init__(attacker, duration)
        self.defender = defender
        self.damage = damage
        self.hit_registered = False

    def on_start(self, scene: FightScene):
        super().on_start(scene)
        if self.defender:
            self.fighter.face_fighter(self.defender)
        self.fighter.set_state("attack", clip_name="uppercut")
        self.hit_registered = False
        scene.audio.schedule_sound(scene.current_time + 0.15, "whoosh")

    def update(self, scene: FightScene, local_t: float, dt: float):
        self.fighter.update_animation(dt)
        if not self.hit_registered and self._impact_event(scene) and self.defender:
            self.hit_registered = True
            hitbox = self.fighter.get_hitbox()
            if hitbox:
                # Add vertical launch impulse
                hitbox.damage = self.damage
                hitbox.knockback_x = 90.0 * self.fighter.facing
                hitbox.knockback_y = -350.0
                scene.resolve_attack(self.fighter, self.defender, hitbox)
                scene.effects.trigger_dust_puff(self.fighter.x, self.fighter.y, count=12)

    def on_finish(self, scene: FightScene):
        self.fighter.set_state("idle")


class SweepAction(Action):
    """Low crouched leg sweep that knocks defender off their feet."""
    def __init__(self, attacker: Fighter, defender: Optional[Fighter] = None, duration: float = 0.50, damage: float = 16.0):
        super().__init__(attacker, duration)
        self.defender = defender
        self.damage = damage
        self.hit_registered = False

    def on_start(self, scene: FightScene):
        super().on_start(scene)
        if self.defender:
            self.fighter.face_fighter(self.defender)
        self.fighter.set_state("attack", clip_name="sweep")
        self.hit_registered = False
        scene.audio.schedule_sound(scene.current_time + 0.12, "whoosh")
        scene.effects.trigger_dust_puff(self.fighter.x + 30 * self.fighter.facing, self.fighter.y, count=10)

    def update(self, scene: FightScene, local_t: float, dt: float):
        self.fighter.update_animation(dt)
        if not self.hit_registered and local_t >= 0.20 and self.defender:
            self.hit_registered = True
            if abs(self.fighter.x - self.defender.x) <= 240.0:
                # Sweep trips defender into fall
                self.defender.health = max(0.0, self.defender.health - self.damage)
                scene.audio.schedule_sound(scene.current_time, "kick")
                scene.effects.trigger_hit_effect(self.defender.x, self.defender.y - 30.0)
                self.defender.state = "fallen"
                self.defender.set_animation("fall", loop=False)
                scene.camera.shake(intensity=9.0, duration=0.2)

    def on_finish(self, scene: FightScene):
        self.fighter.set_state("idle")


class SlashAction(Action):
    """Sword weapon strike with crescent trail and potential blade clash."""
    def __init__(self, attacker: Fighter, defender: Optional[Fighter] = None, duration: float = 0.48, damage: float = 28.0):
        super().__init__(attacker, duration)
        self.defender = defender
        self.damage = damage
        self.hit_registered = False

    def on_start(self, scene: FightScene):
        super().on_start(scene)
        if self.defender:
            self.fighter.face_fighter(self.defender)
        self.fighter.set_state("attack", clip_name="slash")
        self.hit_registered = False
        scene.audio.schedule_sound(scene.current_time + 0.14, "blade_slice")

        # Spawn glowing crescent slash arc
        f_sign = self.fighter.facing
        start_ang = -0.6 if f_sign > 0 else 2.5
        end_ang = 1.4 if f_sign > 0 else 4.2
        scene.effects.trigger_slash_arc(
            x=self.fighter.x + 40 * f_sign,
            y=self.fighter.y - 120.0,
            start_angle=start_ang,
            end_angle=end_ang,
            radius=135.0,
            color=(235, 245, 255)
        )

    def update(self, scene: FightScene, local_t: float, dt: float):
        self.fighter.update_animation(dt)
        if not self.hit_registered and local_t >= 0.22 and self.defender:
            self.hit_registered = True
            hitbox = self.fighter.get_hitbox()
            if hitbox:
                hitbox.damage = self.damage
                hitbox.knockback_x = 160.0 * self.fighter.facing
                if self.defender.state == "blocking":
                    # Blade parried / clashed!
                    scene.audio.schedule_sound(scene.current_time, "clang")
                    scene.effects.trigger_weapon_clash(
                        (self.fighter.x + self.defender.x) / 2.0,
                        self.fighter.y - 140.0
                    )
                    scene.camera.shake(intensity=8.0, duration=0.2)
                    self.defender.health = max(0.0, self.defender.health - self.damage * 0.15)
                else:
                    scene.resolve_attack(self.fighter, self.defender, hitbox)

    def on_finish(self, scene: FightScene):
        self.fighter.set_state("idle")


class StaffStrikeAction(Action):
    """Sweeping staff strike with extended reach."""
    def __init__(self, attacker: Fighter, defender: Optional[Fighter] = None, duration: float = 0.48, damage: float = 21.0):
        super().__init__(attacker, duration)
        self.defender = defender
        self.damage = damage
        self.hit_registered = False

    def on_start(self, scene: FightScene):
        super().on_start(scene)
        if self.defender:
            self.fighter.face_fighter(self.defender)
        self.fighter.set_animation("slash", loop=False)
        self.hit_registered = False
        scene.audio.schedule_sound(scene.current_time + 0.12, "whoosh")

    def update(self, scene: FightScene, local_t: float, dt: float):
        self.fighter.update_animation(dt)
        if not self.hit_registered and local_t >= 0.22 and self.defender:
            self.hit_registered = True
            hitbox = self.fighter.get_hitbox()
            if hitbox:
                hitbox.damage = self.damage
                scene.resolve_attack(self.fighter, self.defender, hitbox)

    def on_finish(self, scene: FightScene):
        self.fighter.set_animation("idle")


class ComboAction(Action):
    """Executes a chain of consecutive combat actions in rapid succession."""
    def __init__(self, fighter: Fighter, actions: List[Action]):
        self.actions = actions
        total_dur = sum(a.duration for a in actions)
        super().__init__(fighter, total_dur)
        self.current_idx = 0
        self.action_start_t = 0.0

    def on_start(self, scene: FightScene):
        super().on_start(scene)
        self.current_idx = 0
        self.action_start_t = 0.0
        if self.actions:
            self.actions[0].on_start(scene)

    def update(self, scene: FightScene, local_t: float, dt: float):
        frame_start_t = max(0.0, local_t - dt)
        cursor_t = max(frame_start_t, self.action_start_t)

        while self.current_idx < len(self.actions):
            action = self.actions[self.current_idx]
            action_end_t = self.action_start_t + action.duration
            segment_end_t = min(local_t, action_end_t)
            segment_dt = max(0.0, segment_end_t - cursor_t)

            if segment_dt > 0.0:
                action.update(scene, segment_end_t - self.action_start_t, segment_dt)

            if local_t < action_end_t:
                break

            action.on_finish(scene)
            self.current_idx += 1
            self.action_start_t = action_end_t
            cursor_t = action_end_t
            if self.current_idx < len(self.actions):
                self.actions[self.current_idx].on_start(scene)

    def on_finish(self, scene: FightScene):
        if self.current_idx < len(self.actions):
            self.actions[self.current_idx].on_finish(scene)
        self.fighter.set_animation("idle")


class CameraAction(Action):
    """Director-style camera shot: cut, pan, or zoom to a target, then hold
    the framing before automatic fighter-tracking resumes.

    The target position can be given explicitly (x/y) or derived from
    `focus`, which may be a single Fighter (frames roughly on their upper
    body) or a tuple/list of Fighters (frames their midpoint — handy for a
    two-shot before cutting to a close-up). Explicit x/y override the
    focus-derived position on whichever axis is given.

    Has no associated fighter (this is a camera-only beat), so it never
    blocks a fighter's idle animation on the timeline.
    """
    def __init__(
        self,
        focus: Optional[Union["Fighter", Tuple["Fighter", ...], List["Fighter"]]] = None,
        x: Optional[float] = None,
        y: Optional[float] = None,
        zoom: Optional[float] = None,
        cut: bool = False,
        transition: float = 0.4,
        hold: float = 0.6,
    ):
        self.focus = focus
        self.x = x
        self.y = y
        self.zoom = zoom
        self.cut = cut
        self.transition = 0.0 if cut else max(0.0, transition)
        total_duration = self.transition + max(0.0, hold)
        super().__init__(None, total_duration)

    def _resolve_target(self, scene: FightScene) -> Tuple[Optional[float], Optional[float]]:
        if self.focus is not None:
            fighters = self.focus if isinstance(self.focus, (tuple, list)) else [self.focus]
            fx = sum(f.x for f in fighters) / len(fighters)
            fy = sum(f.y - 120.0 for f in fighters) / len(fighters)
            tx = fx if self.x is None else self.x
            ty = fy if self.y is None else self.y
        else:
            tx = self.x
            ty = self.y
        return tx, ty

    def on_start(self, scene: FightScene):
        super().on_start(scene)
        cam = scene.camera
        tx, ty = self._resolve_target(scene)
        tx = cam.target_x if tx is None else tx
        ty = cam.target_y if ty is None else ty
        tz = cam.zoom if self.zoom is None else self.zoom

        # Lock out auto fighter-framing for this shot's full duration; each
        # update() call below refreshes the lock so it never expires early.
        cam.director_lock = self.duration + 0.05

        if self.cut:
            clamped_zoom = max(cam.min_zoom, min(cam.max_zoom, tz))
            cam.x, cam.y, cam.zoom = tx, ty, clamped_zoom
            cam.target_x, cam.target_y, cam.target_zoom = tx, ty, clamped_zoom
        else:
            cam.set_target(tx, ty, tz)

    def update(self, scene: FightScene, local_t: float, dt: float):
        # Camera.update() (invoked once per scene tick) already drives the
        # smooth lerp toward target_x/y/zoom; this just keeps the director
        # lock alive so auto-framing doesn't reclaim the camera mid-shot.
        scene.camera.director_lock = max(scene.camera.director_lock, self.duration - local_t + 0.05)

    def on_finish(self, scene: FightScene):
        pass  # Automatic fighter-framing resumes once director_lock elapses.


# ============================================================================
# REALISTIC MARTIAL ARTS ACTIONS (Boxing / Muay Thai / MMA)
# These mechanics power the "realistic" fight style: snap strikes with proper
# timing windows, defensive head movement, the low-kick vs shin-check
# exchange, and the grappling sequence (takedown -> grounded guard ->
# ground-and-pound).
# ============================================================================

class JabAction(Action):
    """Fast lead-hand straight punch. Low damage, quick recovery."""
    def __init__(self, attacker: Fighter, defender: Optional[Fighter] = None, duration: float = 0.35, damage: float = 12.0):
        super().__init__(attacker, duration)
        self.defender = defender
        self.damage = damage
        self.hit_registered = False

    def on_start(self, scene: FightScene):
        super().on_start(scene)
        if self.defender:
            self.fighter.face_fighter(self.defender)
        self.fighter.state = "attacking"
        self.fighter.set_state("attack", clip_name="jab")
        self.hit_registered = False
        scene.audio.schedule_sound(scene.current_time + 0.08, "whoosh")

    def update(self, scene: FightScene, local_t: float, dt: float):
        self.fighter.update_animation(dt)
        if not self.hit_registered and self._impact_event(scene):
            self.hit_registered = True
            if self.defender:
                hitbox = self.fighter.get_hitbox()
                if hitbox:
                    hitbox.damage = self.damage
                    scene.resolve_attack(self.fighter, self.defender, hitbox)

    def on_finish(self, scene: FightScene):
        self.fighter.state = "idle"
        self.fighter.set_state("idle")


class CrossAction(Action):
    """Rear-hand straight power shot thrown off the jab or from stance."""
    def __init__(self, attacker: Fighter, defender: Optional[Fighter] = None, duration: float = 0.40, damage: float = 18.0):
        super().__init__(attacker, duration)
        self.defender = defender
        self.damage = damage
        self.hit_registered = False

    def on_start(self, scene: FightScene):
        super().on_start(scene)
        if self.defender:
            self.fighter.face_fighter(self.defender)
        self.fighter.state = "attacking"
        self.fighter.set_state("attack", clip_name="cross")
        self.hit_registered = False
        scene.audio.schedule_sound(scene.current_time + 0.12, "whoosh")

    def update(self, scene: FightScene, local_t: float, dt: float):
        self.fighter.update_animation(dt)
        if not self.hit_registered and self._impact_event(scene):
            self.hit_registered = True
            if self.defender:
                hitbox = self.fighter.get_hitbox()
                if hitbox:
                    hitbox.damage = self.damage
                    scene.resolve_attack(self.fighter, self.defender, hitbox)

    def on_finish(self, scene: FightScene):
        self.fighter.state = "idle"
        self.fighter.set_state("idle")


class HookAction(Action):
    """Lead hook on a level arc. Heavy damage inside punching range."""
    def __init__(self, attacker: Fighter, defender: Optional[Fighter] = None, duration: float = 0.42, damage: float = 24.0):
        super().__init__(attacker, duration)
        self.defender = defender
        self.damage = damage
        self.hit_registered = False

    def on_start(self, scene: FightScene):
        super().on_start(scene)
        if self.defender:
            self.fighter.face_fighter(self.defender)
        self.fighter.state = "attacking"
        self.fighter.set_state("attack", clip_name="hook")
        self.hit_registered = False
        scene.audio.schedule_sound(scene.current_time + 0.12, "whoosh")

    def update(self, scene: FightScene, local_t: float, dt: float):
        self.fighter.update_animation(dt)
        if not self.hit_registered and self._impact_event(scene):
            self.hit_registered = True
            if self.defender:
                hitbox = self.fighter.get_hitbox()
                if hitbox:
                    hitbox.damage = self.damage
                    scene.resolve_attack(self.fighter, self.defender, hitbox)

    def on_finish(self, scene: FightScene):
        self.fighter.state = "idle"
        self.fighter.set_state("idle")


class LowKickAction(Action):
    """Rear-leg roundhouse to the opponent's lead leg.

    If the defender is checking (state == "checking"), the kick lands on the
    raised shin instead: the defender takes no damage and the kicker absorbs
    recoil damage for striking bone.
    """
    def __init__(self, attacker: Fighter, defender: Optional[Fighter] = None, duration: float = 0.42, damage: float = 16.0):
        super().__init__(attacker, duration)
        self.defender = defender
        self.damage = damage
        self.hit_registered = False

    def on_start(self, scene: FightScene):
        super().on_start(scene)
        if self.defender:
            self.fighter.face_fighter(self.defender)
        self.fighter.state = "attacking"
        self.fighter.set_animation("low_kick", loop=False)
        self.hit_registered = False
        scene.audio.schedule_sound(scene.current_time + 0.14, "whoosh")

    def update(self, scene: FightScene, local_t: float, dt: float):
        self.fighter.update_animation(dt)
        if not self.hit_registered and self._impact_event(scene):
            self.hit_registered = True
            self._resolve_impact(scene)

    def _resolve_impact(self, scene: FightScene):
        if not self.defender:
            return
        if self.defender.state == "checking":
            # Shin check! Kicker eats recoil damage, defender is unharmed.
            recoil = self.damage * 0.4
            self.fighter.health = max(0.0, self.fighter.health - recoil)
            impact_x = (self.fighter.x + self.defender.x) / 2.0
            impact_y = self.defender.y - 90.0
            scene.effects.trigger_hit_effect(impact_x, impact_y, is_blocked=True)
            scene.audio.schedule_sound(scene.current_time, "block")
            scene.camera.shake(intensity=7.0, duration=0.15)
            return
        hitbox = self.fighter.get_hitbox()
        if hitbox:
            hitbox.damage = self.damage
            scene.resolve_attack(self.fighter, self.defender, hitbox)

    def on_finish(self, scene: FightScene):
        self.fighter.state = "idle"
        self.fighter.set_state("idle")


class CheckKickAction(Action):
    """Raise the lead shin to bone-on-bone block an incoming low kick."""
    def __init__(self, fighter: Fighter, duration: float = 0.45):
        super().__init__(fighter, duration)

    def on_start(self, scene: FightScene):
        super().on_start(scene)
        self.fighter.state = "checking"
        self.fighter.set_animation("check_kick", loop=False)

    def update(self, scene: FightScene, local_t: float, dt: float):
        self.fighter.update_animation(dt)

    def on_finish(self, scene: FightScene):
        self.fighter.state = "idle"
        self.fighter.set_animation("idle")


class SlipAction(Action):
    """Lateral head slip that ducks a punch off the centerline.

    While slipping, straight punches (jab/cross/punch) miss entirely; hooks
    and heavier arcs can still catch the shoulder.
    """
    def __init__(self, fighter: Fighter, duration: float = 0.40):
        super().__init__(fighter, duration)

    def on_start(self, scene: FightScene):
        super().on_start(scene)
        self.fighter.state = "slipping"
        self.fighter.set_animation("slip", loop=False)

    def update(self, scene: FightScene, local_t: float, dt: float):
        self.fighter.update_animation(dt)

    def on_finish(self, scene: FightScene):
        self.fighter.state = "idle"
        self.fighter.set_animation("idle")


class BobWeaveAction(Action):
    """U-shaped duck under incoming punches; hands stay glued to the temples."""
    def __init__(self, fighter: Fighter, duration: float = 0.45):
        super().__init__(fighter, duration)

    def on_start(self, scene: FightScene):
        super().on_start(scene)
        self.fighter.state = "weaving"
        self.fighter.set_animation("bob_weave", loop=False)

    def update(self, scene: FightScene, local_t: float, dt: float):
        self.fighter.update_animation(dt)

    def on_finish(self, scene: FightScene):
        self.fighter.state = "idle"
        self.fighter.set_animation("idle")


class ClinchKneeAction(Action):
    """Thai plum clinch driving the rear knee into the opponent's body."""
    def __init__(self, attacker: Fighter, defender: Optional[Fighter] = None, duration: float = 0.50, damage: float = 25.0):
        super().__init__(attacker, duration)
        self.defender = defender
        self.damage = damage
        self.hit_registered = False

    def on_start(self, scene: FightScene):
        super().on_start(scene)
        if self.defender:
            self.fighter.face_fighter(self.defender)
        self.fighter.state = "attacking"
        self.fighter.set_animation("clinch_knee", loop=False)
        self.hit_registered = False
        scene.audio.schedule_sound(scene.current_time + 0.15, "whoosh")

    def update(self, scene: FightScene, local_t: float, dt: float):
        self.fighter.update_animation(dt)
        if not self.hit_registered and self._impact_event(scene):
            self.hit_registered = True
            if self.defender:
                hitbox = self.fighter.get_hitbox()
                if hitbox:
                    hitbox.damage = self.damage
                    scene.resolve_attack(self.fighter, self.defender, hitbox)

    def on_finish(self, scene: FightScene):
        self.fighter.state = "idle"
        self.fighter.set_state("idle")


class TakedownAction(Action):
    """Double-leg wrestling shot: shoot in, drive through, take the rival down.

    On success the defender ends up grounded in the bottom guard position,
    setting up a ground-and-pound follow-up. A defender who is already
    fallen cannot be taken down again.
    """
    def __init__(self, attacker: Fighter, defender: Optional[Fighter] = None, duration: float = 0.70, damage: float = 22.0):
        super().__init__(attacker, duration)
        self.defender = defender
        self.damage = damage
        self.hit_registered = False

    def on_start(self, scene: FightScene):
        super().on_start(scene)
        if self.defender:
            self.fighter.face_fighter(self.defender)
        self.fighter.state = "attacking"
        self.fighter.set_state("attack", clip_name="takedown")
        self.hit_registered = False
        scene.audio.schedule_sound(scene.current_time + 0.20, "whoosh")

    def update(self, scene: FightScene, local_t: float, dt: float):
        self.fighter.update_animation(dt)
        if not self.hit_registered and self._impact_event(scene):
            self.hit_registered = True
            self._complete_takedown(scene)

    def _complete_takedown(self, scene: FightScene):
        d = self.defender
        if not d or d.state == "fallen":
            return
        # Close the distance so the grappling sequence reads physically.
        gap = (d.x - self.fighter.x) * 0.6
        self.fighter.x += gap
        self.fighter.sync_to_physics()

        d.health = max(0.0, d.health - self.damage)
        d.state = "fallen"
        d.set_animation("fall", loop=False)
        d.physics.vx = 0.0
        d.physics.vy = 0.0
        d.physics.is_grounded = True

        impact_x = (self.fighter.x + d.x) / 2.0
        scene.audio.schedule_sound(scene.current_time, "fall")
        scene.effects.trigger_dust_puff(d.x, d.y, count=18)
        scene.camera.shake(intensity=12.0, duration=0.25)

    def on_finish(self, scene: FightScene):
        self.fighter.state = "idle"
        self.fighter.set_state("idle")


class GroundPoundAction(Action):
    """Top-position hammerfists onto a grounded opponent.

    Only effective against a fighter who is already down; standing targets
    simply avoid it, which keeps the choreography honest (you must take the
    rival down first).
    """
    def __init__(self, attacker: Fighter, defender: Optional[Fighter] = None, duration: float = 0.55, damage: float = 28.0):
        super().__init__(attacker, duration)
        self.defender = defender
        self.damage = damage
        self.hit_registered = False

    def on_start(self, scene: FightScene):
        super().on_start(scene)
        if self.defender:
            self.fighter.face_fighter(self.defender)
        self.fighter.state = "attacking"
        self.fighter.set_animation("ground_pound", loop=False)
        self.hit_registered = False
        scene.audio.schedule_sound(scene.current_time + 0.15, "whoosh")

    def update(self, scene: FightScene, local_t: float, dt: float):
        self.fighter.update_animation(dt)
        if not self.hit_registered and self._impact_event(scene):
            self.hit_registered = True
            d = self.defender
            if d and d.state == "fallen":
                d.health = max(0.0, d.health - self.damage)
                impact_x = (self.fighter.x + d.x) / 2.0
                impact_y = d.y - 60.0
                scene.effects.trigger_hit_effect(impact_x, impact_y, is_blocked=False, is_heavy=True)
                scene.audio.schedule_sound(scene.current_time, "punch")
                scene.camera.shake(intensity=10.0, duration=0.2)

    def on_finish(self, scene: FightScene):
        self.fighter.state = "idle"
        self.fighter.set_state("idle")


class StaggerAction(Action):
    """Hurt wobble after eating a clean power shot; barely stays upright."""
    def __init__(self, fighter: Fighter, duration: float = 0.50):
        super().__init__(fighter, duration)

    def on_start(self, scene: FightScene):
        super().on_start(scene)
        self.fighter.state = "staggering"
        self.fighter.set_animation("stagger", loop=False)

    def update(self, scene: FightScene, local_t: float, dt: float):
        self.fighter.update_animation(dt)
        prog = max(0.0, min(1.0, local_t / max(1e-5, self.duration)))
        # Reel backward while wobbling.
        self.fighter.x -= self.fighter.facing * 60.0 * dt * (1.0 - prog)

    def on_finish(self, scene: FightScene):
        self.fighter.state = "idle"
        self.fighter.set_animation("idle")
