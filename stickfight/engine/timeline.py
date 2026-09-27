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

    def update(self, current_time: float, dt: float, scene: FightScene):
        """Updates all timeline events for the current timestamp."""
        # 1. Start events that reached their start_time
        for e in self.events:
            if not e.started and current_time >= e.start_time:
                e.started = True
                e.action.on_start(scene)
                self.active_events.append(e)

        # 2. Update active events
        fighters_with_actions: Set[Fighter] = set()
        still_active: List[TimelineEvent] = []

        for e in self.active_events:
            local_t = current_time - e.start_time
            if local_t <= e.action.duration:
                e.action.update(scene, local_t, dt)
                if e.action.fighter:
                    fighters_with_actions.add(e.action.fighter)
                still_active.append(e)
            else:
                # Finished
                e.action.on_finish(scene)
                e.finished = True

        self.active_events = still_active

        # 3. Idle update for fighters without an active action
        for f in scene.fighters:
            if f not in fighters_with_actions and f.state != "fallen":
                f.update_animation(dt)
