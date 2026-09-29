"""Fight-specific actions exposed to the Animation Studio authoring layer.

The registry is deliberately small and declarative: it names actions that the
existing Fighter animation library already understands. It does not duplicate
combat physics, hitboxes, timing, or choreography.
"""

from __future__ import annotations

from typing import Dict, FrozenSet


STUDIO_FIGHT_ACTIONS: FrozenSet[str] = frozenset({
    "idle", "walk", "punch", "kick", "block", "dodge", "hit", "knockback",
    "fall", "jump", "uppercut", "sweep", "slash", "sword_guard",
    "jab", "cross", "hook", "low_kick", "check_kick", "slip", "bob_weave",
    "clinch_knee", "takedown", "ground_pound", "stagger", "grounded_guard",
    "ground_frame", "ground_shrimp", "ground_sweep", "ground_stand",
})


ACTION_LABELS: Dict[str, str] = {
    "idle": "Idle / Guard",
    "walk": "Walk",
    "punch": "Punch",
    "kick": "Kick",
    "jab": "Jab",
    "cross": "Cross",
    "hook": "Hook",
    "uppercut": "Uppercut",
    "low_kick": "Low Kick",
    "check_kick": "Check Kick",
    "sweep": "Sweep",
    "block": "Block",
    "dodge": "Dodge",
    "slip": "Slip",
    "bob_weave": "Bob & Weave",
    "hit": "Hit Reaction",
    "knockback": "Knockback",
    "stagger": "Stagger",
    "jump": "Jump",
    "fall": "Fall",
    "clinch_knee": "Clinch Knee",
    "takedown": "Takedown",
    "ground_pound": "Ground Pound",
    "grounded_guard": "Ground Guard",
    "ground_frame": "Ground Frame",
    "ground_shrimp": "Ground Shrimp",
    "ground_sweep": "Ground Sweep",
    "ground_stand": "Ground Stand",
    "slash": "Sword Slash",
    "sword_guard": "Sword Guard",
}


def normalize_action(action: str | None) -> str:
    """Return a production Fighter clip name, or idle for unknown input."""
    value = str(action or "idle").strip().lower().replace("-", "_").replace(" ", "_")
    return value if value in STUDIO_FIGHT_ACTIONS else "idle"


def action_label(action: str | None) -> str:
    value = normalize_action(action)
    return ACTION_LABELS.get(value, value.replace("_", " ").title())
