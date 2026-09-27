"""
Action descriptors for scripted fight choreography.
Encapsulates high-level actions (walk, punch, kick, block, dodge, fall, combos).
"""

from __future__ import annotations
from typing import TYPE_CHECKING, List, Optional
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
        self.fighter.set_animation("punch", loop=False)
        self.hit_registered = False
        scene.audio.schedule_sound(scene.current_time + 0.12, "whoosh")

    def update(self, scene: FightScene, local_t: float, dt: float):
        self.fighter.update_animation(dt)
        strike_time = 0.18
        if not self.hit_registered and local_t >= strike_time:
            self.hit_registered = True
            # Check attack collision against defender
            if self.defender:
                hitbox = self.fighter.get_hitbox()
                if hitbox:
                    scene.resolve_attack(self.fighter, self.defender, hitbox)

    def on_finish(self, scene: FightScene):
        self.fighter.set_animation("idle")


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
        self.fighter.set_animation("kick", loop=False)
        self.hit_registered = False
        scene.audio.schedule_sound(scene.current_time + 0.18, "whoosh")

    def update(self, scene: FightScene, local_t: float, dt: float):
        self.fighter.update_animation(dt)
        strike_time = 0.25
        if not self.hit_registered and local_t >= strike_time:
            self.hit_registered = True
            if self.defender:
                hitbox = self.fighter.get_hitbox()
                if hitbox:
                    scene.resolve_attack(self.fighter, self.defender, hitbox)

    def on_finish(self, scene: FightScene):
        self.fighter.set_animation("idle")


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
        self.fighter.set_animation("jump", loop=False)
        scene.effects.trigger_dust_puff(self.fighter.x, self.fighter.y, count=8)

    def update(self, scene: FightScene, local_t: float, dt: float):
        self.fighter.update_animation(dt)

    def on_finish(self, scene: FightScene):
        self.fighter.state = "idle"
        self.fighter.set_animation("idle")
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
