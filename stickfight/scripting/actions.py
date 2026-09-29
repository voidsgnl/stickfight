"""
Action descriptors for scripted fight choreography.
Encapsulates high-level actions (walk, punch, kick, block, dodge, fall, combos)
plus fighter-less scene actions (camera, sound, slow motion, callbacks).
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Callable, List, Optional, Set, Union, Tuple
import math

from stickfight.engine.collision import find_hit

if TYPE_CHECKING:
    from stickfight.engine.fighter import Fighter
    from stickfight.engine.scene import FightScene

# Attack contact is sampled this finely (seconds of animation time) so a
# fast strike is tested along its whole path instead of once per frame.
HIT_SUBSTEP = 1.0 / 120.0


class Action:
    """Base class for all timeline fight actions."""
    allowed_when_down = False  # may start while its fighter is on the floor

    def __init__(self, fighter: Optional[Fighter], duration: float):
        self.fighter = fighter
        self.duration = duration
        self._started = False

    def involved_fighters(self) -> Set[Fighter]:
        """Every fighter this action animates. The timeline uses it to know
        who is busy (so nobody's animation is advanced twice per frame)."""
        return {self.fighter} if self.fighter is not None else set()

    @property
    def label(self) -> str:
        name = type(self).__name__
        return (name[:-6] if name.endswith("Action") else name).lower()

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


class ApproachAction(Action):
    """Chases another fighter until `gap` px away. The target position is
    re-measured every frame (from where the body is actually drawn), so it
    keeps up with a fighter who is still skidding back. Never retreats, and
    does nothing if already in range."""
    def __init__(self, fighter: Fighter, target_fighter: Fighter, gap: float = 135.0,
                 duration: float = 0.4, speed: float = 600.0):
        super().__init__(fighter, duration)
        self.target_fighter = target_fighter
        self.gap = gap
        self.speed = speed
        self._moving = False

    def _set_moving(self, moving: bool):
        if moving != self._moving:
            self._moving = moving
            self.fighter.set_animation("walk" if moving else "idle")

    def on_start(self, scene: FightScene):
        super().on_start(scene)
        self._moving = False
        self.fighter.set_animation("idle")

    def update(self, scene: FightScene, local_t: float, dt: float):
        me, other = self.fighter, self.target_fighter
        direction = 1.0 if other.body_x >= me.x else -1.0
        desired = other.body_x - direction * self.gap
        remaining = (desired - me.x) * direction  # > 0 means still too far away
        if remaining > 1.0:
            me.x += direction * min(remaining, self.speed * me.stats.speed * dt)
            me.face_fighter(other)
            self._set_moving(True)
        else:
            self._set_moving(False)
        me.update_animation(dt)

    def on_finish(self, scene: FightScene):
        self.fighter.face_fighter(self.target_fighter)
        self.fighter.set_animation("idle")


class AttackAction(Action):
    """Shared logic for every strike.

    The strike can connect at any moment inside `window` (seconds of clip
    time). The fist/foot is sampled between frames along its real animated
    path, so a fast punch cannot pass through a target. The first contact
    with the head or torso registers immediately; contact with limbs alone
    registers when the window closes.
    """
    clip_name = "punch"
    strike_clip_time = 0.16        # nominal contact moment; used to time defenders' reactions
    window: Tuple[float, float] = (0.11, 0.34)
    whoosh_delay = 0.12
    whoosh_sound = "whoosh"

    def __init__(self, attacker: Fighter, defender: Optional[Fighter] = None,
                 duration: float = 0.45, damage: float = 15.0, finisher: bool = False):
        super().__init__(attacker, duration)
        self.defender = defender
        self.damage = damage
        self.finisher = finisher
        self.hit_registered = False
        self.contact = False
        self.started_at = 0.0
        self._prev_pos: Optional[Tuple[float, float]] = None
        self._last_sample_t: Optional[float] = None
        self._limb_candidate = None
        self._evaded = False  # defender was dodging while the strike was live

    @property
    def strike_offset(self) -> float:
        """Action-time moment the strike is expected to land."""
        return self.strike_clip_time / max(0.1, self.fighter.stats.speed)

    # -- hooks -------------------------------------------------------------
    def _on_attack_start(self, scene: FightScene):
        pass

    def _after_hit(self, scene: FightScene):
        pass

    # -- lifecycle ---------------------------------------------------------
    def _reset_strike_state(self, scene: FightScene):
        self.hit_registered = False
        self.contact = False
        self.started_at = scene.current_time
        self._prev_pos = None
        self._last_sample_t = None
        self._limb_candidate = None
        self._evaded = False

    def on_start(self, scene: FightScene):
        super().on_start(scene)
        self._reset_strike_state(scene)
        if self.defender:
            self.fighter.face_fighter(self.defender)
        self.fighter.set_animation(self.clip_name, loop=False)
        self._on_attack_start(scene)
        scene.audio.schedule_sound(scene.current_time + self.whoosh_delay, self.whoosh_sound)

    def update(self, scene: FightScene, local_t: float, dt: float):
        t0 = self.fighter.clip_time
        self.fighter.update_animation(dt)
        self._process_strike(scene, t0, self.fighter.clip_time)

    def on_finish(self, scene: FightScene):
        if not self.hit_registered and self._limb_candidate is not None:
            self._register(scene, self._limb_candidate)
        self._finish_contact_check(scene)
        self.fighter.set_animation("idle")

    def _finish_contact_check(self, scene: FightScene):
        if self.defender is None or self.contact:
            return
        if self._evaded:
            scene.stats["dodges"] += 1  # slipped out of range: a successful dodge, not a choreography error
        else:
            scene.report_whiff(self)

    # -- hit detection -----------------------------------------------------
    def _process_strike(self, scene: FightScene, t0: float, t1: float):
        if self.hit_registered or self.defender is None:
            return
        lo, hi = max(t0, self.window[0]), min(t1, self.window[1])
        if lo <= hi:
            if self.defender.state == "dodging":
                self._evaded = True
            steps = max(1, int(math.ceil((hi - lo) / HIT_SUBSTEP)))
            for i in range(steps + 1):
                tau = lo + (hi - lo) * i / steps
                if self._last_sample_t is not None and abs(tau - self._last_sample_t) < 1e-9:
                    continue
                self._last_sample_t = tau
                hb = self.fighter.hitbox_at(tau)
                if hb is None:
                    continue
                if self._prev_pos is not None:
                    hb.prev_x, hb.prev_y = self._prev_pos
                self._prev_pos = (hb.x, hb.y)
                res = find_hit(hb, self.defender.get_hurtbox())
                if res is None:
                    continue
                self.contact = True
                if res.region in ("head", "torso"):
                    self._register(scene, hb)
                    return
                if self._limb_candidate is None:
                    self._limb_candidate = hb
        if t1 >= self.window[1] and self._limb_candidate is not None:
            self._register(scene, self._limb_candidate)

    def _register(self, scene: FightScene, hitbox):
        self.hit_registered = True
        self.contact = True
        hitbox.damage = self.damage
        hitbox.finisher = self.finisher
        scene.resolve_attack(self.fighter, self.defender, hitbox)
        self._after_hit(scene)


class PunchAction(AttackAction):
    clip_name = "punch"
    strike_clip_time = 0.16
    window = (0.11, 0.34)
    whoosh_delay = 0.12


class KickAction(AttackAction):
    clip_name = "kick"
    strike_clip_time = 0.22
    window = (0.17, 0.42)
    whoosh_delay = 0.18

    def __init__(self, attacker, defender=None, duration: float = 0.55, damage: float = 22.0, finisher: bool = False):
        super().__init__(attacker, defender, duration, damage, finisher)


class UppercutAction(AttackAction):
    """Heavy rising fist driving upward into sky, launching defender airborne."""
    clip_name = "uppercut"
    strike_clip_time = 0.20
    window = (0.15, 0.45)
    whoosh_delay = 0.15

    def __init__(self, attacker, defender=None, duration: float = 0.55, damage: float = 26.0, finisher: bool = False):
        super().__init__(attacker, defender, duration, damage, finisher)

    def _after_hit(self, scene: FightScene):
        scene.effects.trigger_dust_puff(self.fighter.x, self.fighter.y, count=12)


class SweepAction(AttackAction):
    """Low crouched leg sweep that knocks defender off their feet."""
    clip_name = "sweep"
    strike_clip_time = 0.14
    window = (0.09, 0.40)
    whoosh_delay = 0.12

    def __init__(self, attacker, defender=None, duration: float = 0.50, damage: float = 16.0, finisher: bool = False):
        super().__init__(attacker, defender, duration, damage, finisher)

    def _on_attack_start(self, scene: FightScene):
        scene.effects.trigger_dust_puff(self.fighter.x + 30 * self.fighter.facing, self.fighter.y, count=10)


class SlashAction(AttackAction):
    """Sword weapon strike with crescent trail and potential blade clash."""
    clip_name = "slash"
    strike_clip_time = 0.20
    window = (0.15, 0.40)
    whoosh_delay = 0.14
    whoosh_sound = "blade_slice"

    def __init__(self, attacker, defender=None, duration: float = 0.48, damage: float = 28.0, finisher: bool = False):
        super().__init__(attacker, defender, duration, damage, finisher)

    def _on_attack_start(self, scene: FightScene):
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


class StaffStrikeAction(AttackAction):
    """Sweeping staff strike with extended reach."""
    clip_name = "slash"
    strike_clip_time = 0.20
    window = (0.15, 0.40)
    whoosh_delay = 0.12

    def __init__(self, attacker, defender=None, duration: float = 0.48, damage: float = 21.0, finisher: bool = False):
        super().__init__(attacker, defender, duration, damage, finisher)


class BlockAction(Action):
    def __init__(self, fighter: Fighter, duration: float = 0.5):
        super().__init__(fighter, duration)

    def on_start(self, scene: FightScene):
        super().on_start(scene)
        self.fighter.state = "blocking"
        self.fighter.block_started_at = scene.current_time
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
        self.fighter.dodge_started_at = scene.current_time
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
    allowed_when_down = True

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


class CounterAction(AttackAction):
    """Parry dodge followed immediately by counter punch."""
    clip_name = "punch"
    strike_clip_time = 0.16
    window = (0.11, 0.34)

    def __init__(self, attacker: Fighter, defender: Fighter, duration: float = 0.7):
        super().__init__(attacker, defender, duration=duration, damage=15.0)
        self.punch_started = False

    def on_start(self, scene: FightScene):
        Action.on_start(self, scene)
        self._reset_strike_state(scene)
        self.fighter.face_fighter(self.defender)
        self.fighter.state = "dodging"
        self.fighter.dodge_started_at = scene.current_time
        self.fighter.set_animation("dodge", loop=False)
        self.punch_started = False

    def update(self, scene: FightScene, local_t: float, dt: float):
        t0 = self.fighter.clip_time
        self.fighter.update_animation(dt)
        if not self.punch_started:
            if local_t >= 0.25:
                self.punch_started = True
                self.fighter.set_animation("punch", loop=False)
                scene.audio.schedule_sound(scene.current_time, "whoosh")
            return
        self._process_strike(scene, t0, self.fighter.clip_time)

    def on_finish(self, scene: FightScene):
        if not self.hit_registered and self._limb_candidate is not None:
            self._register(scene, self._limb_candidate)
        self._finish_contact_check(scene)
        self.fighter.state = "idle"
        self.fighter.set_animation("idle")


class ParallelAction(Action):
    """Executes multiple actions concurrently."""
    def __init__(self, actions: List[Action]):
        self.actions = actions
        max_dur = max((a.duration for a in actions), default=0.0)
        # Pass first fighter as representative
        super().__init__(actions[0].fighter if actions else None, max_dur)

    def involved_fighters(self) -> Set[Fighter]:
        result: Set[Fighter] = set()
        for act in self.actions:
            result |= act.involved_fighters()
        return result

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


class ComboAction(Action):
    """Executes a chain of consecutive combat actions in rapid succession."""
    def __init__(self, fighter: Fighter, actions: List[Action]):
        self.actions = actions
        total_dur = sum(a.duration for a in actions)
        super().__init__(fighter, total_dur)
        self.current_idx = 0
        self.action_start_t = 0.0

    def involved_fighters(self) -> Set[Fighter]:
        result = super().involved_fighters()
        for act in self.actions:
            result |= act.involved_fighters()
        return result

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


class SceneAction(Action):
    """An action that belongs to the scene rather than a fighter. It never
    keeps anybody busy, so it can overlap anything on the timeline."""
    def __init__(self, duration: float = 0.0):
        super().__init__(None, duration)


class SoundAction(SceneAction):
    """Plays a named sound effect at its start time."""
    def __init__(self, sound_name: str, pitch: Optional[float] = None, gain: Optional[float] = None):
        super().__init__(0.0)
        self.sound_name = sound_name
        self.pitch = pitch
        self.gain = gain

    def on_start(self, scene: FightScene):
        super().on_start(scene)
        scene.audio.schedule_sound(scene.current_time, self.sound_name, pitch=self.pitch, gain=self.gain)


class CallbackAction(SceneAction):
    """Calls `fn(scene)` at its start time (spawn effects, shake, anything)."""
    def __init__(self, fn: Callable[["FightScene"], None]):
        super().__init__(0.0)
        self.fn = fn

    def on_start(self, scene: FightScene):
        super().on_start(scene)
        self.fn(scene)


class SlowMotionAction(SceneAction):
    """Plays the next `duration` seconds of the fight at `factor` speed."""
    def __init__(self, duration: float = 1.0, factor: float = 0.3, ease: float = 0.12):
        super().__init__(duration)
        self.factor = factor
        self.ease = ease

    def on_start(self, scene: FightScene):
        super().on_start(scene)
        scene.slowmo(scene.current_time, scene.current_time + self.duration, self.factor, self.ease, _dynamic=True)
