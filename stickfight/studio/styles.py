"""Built-in style registry for Story Animation Studio.

Styles are data-level identities. The actual drawing implementation remains
inside the renderer. New visual families can therefore be added without
changing skeleton, animation, collision, physics, or story data structures.
"""

from __future__ import annotations

from typing import Dict

from .model import VisualStyle


BUILTIN_STYLES: Dict[str, VisualStyle] = {
    "classic": VisualStyle("classic", "segmented"),
    "ink_fight": VisualStyle("ink_fight", "ink_fight"),
    "bold": VisualStyle("bold", "bold"),
    "silhouette": VisualStyle("silhouette", "silhouette"),
    "anime": VisualStyle(
        "anime",
        "anime",
        {"line_weight": 0.8, "face_detail": "expressive", "motion_lines": True},
    ),
    "cartoon": VisualStyle(
        "cartoon",
        "cartoon",
        {"line_weight": 1.2, "face_detail": "expressive", "squash_stretch": True},
    ),
    "custom": VisualStyle("custom", "custom"),
}


def get_style(style_id: str) -> VisualStyle:
    """Return a copy-like style object so callers can safely customize it."""

    if style_id not in BUILTIN_STYLES:
        raise KeyError(f"unknown visual style: {style_id}")
    style = BUILTIN_STYLES[style_id]
    return VisualStyle(style.id, style.renderer, dict(style.parameters))
