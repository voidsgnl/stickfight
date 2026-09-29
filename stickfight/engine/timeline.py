"""
Timeline sequencer: manages scheduled combat choreography, parallel actions, and event dispatch.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Set, TYPE_CHECKING
import math

from stickfight.scripting.actions import Action, ParallelAction

if TYPE_CHECKING:
    from stickfight.engine.scene import FightScene
    from stickfight.engine.fighter import Fighter


@dataclass
class TimelineEvent:
    start_time: float
    action: Action
    started: bool = False
    finished: bool = False


class Timeline:
    def __init__(self):
        self.events: List[TimelineEvent] = []
        self.active_events: List[TimelineEvent] = []

    def at(self, start_time: float, action: Action):
        """Schedules an action to start at start_time."""
        self.events.append(TimelineEvent(start_time=float(start_time), action=action))
        self.events.sort(key=lambda e: e.start_time)

    def parallel(self, *actions: Action, start_time: float = 0.0) -> ParallelAction:
        """Groups actions to run simultaneously at start_time."""
        combo = ParallelAction(list(actions))
        self.at(start_time, combo)
        return combo

    def get_total_duration(self, tail_padding: float = 1.0) -> float:
        """Computes total scene duration until the final action completes."""
        if not self.events:
            return 3.0
        max_end = max((e.start_time + e.action.duration for e in self.events), default=0.0)
        return max_end + tail_padding

    def reset(self):
        """Resets all events for fresh playback."""
        for e in self.events:
            e.started = False
            e.finished = False
        self.active_events.clear()

    def _busy_fighters(self) -> Set[Fighter]:
        busy: Set[Fighter] = set()
        for e in self.active_events:
            busy |= e.action.involved_fighters()
        return busy

    def _try_start(self, e: TimelineEvent, scene: FightScene) -> bool:
        """Validates and starts one event. Returns False if it was skipped."""
        involved = e.action.involved_fighters()
        label = e.action.label
        downed = sorted(f.name for f in involved if f.ko)
        if downed and e.action.allowed_when_down:
            return False  # a scripted fall for someone already knocked out is simply redundant
        if downed:
            scene.warn(f"t={e.start_time:.2f}s: {label} skipped because {', '.join(downed)} is already knocked out")
            return False
        clash = sorted(f.name for f in involved & self._busy_fighters())
        if clash:
            scene.warn(f"t={e.start_time:.2f}s: {label} overlaps another action for {', '.join(clash)}")
        if not e.action.allowed_when_down:
            grounded = sorted(f.name for f in involved if f.state == "fallen")
            if grounded:
                scene.warn(f"t={e.start_time:.2f}s: {label} scheduled while {', '.join(grounded)} is on the floor")
        e.action.on_start(scene)
        return True

    def update(self, current_time: float, dt: float, scene: FightScene):
        """Updates all timeline events for the current timestamp."""
        # 1. Start events that reached their start_time
        for e in self.events:
            if not e.started and current_time >= e.start_time:
                e.started = True
                if self._try_start(e, scene):
                    self.active_events.append(e)
                else:
                    e.finished = True

        # 2. Update active events. Everyone an action touches is "busy" (a
        # parallel action keeps *all* its fighters busy, so none of them gets
        # its animation advanced a second time by the idle pass below).
        busy: Set[Fighter] = set()
        still_active: List[TimelineEvent] = []

        for e in self.active_events:
            local_t = current_time - e.start_time
            if local_t <= e.action.duration:
                e.action.update(scene, local_t, dt)
                busy |= e.action.involved_fighters()
                still_active.append(e)
            else:
                # Finished
                e.action.on_finish(scene)
                e.finished = True

        self.active_events = still_active

        # 3. Idle update for fighters without an active action. Downed
        # fighters keep animating so their fall clip actually plays.
        for f in scene.fighters:
            if f not in busy:
                f.update_animation(dt)
