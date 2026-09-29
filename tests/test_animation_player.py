"""Tests for the dedicated animation playback runtime."""

from stickfight.engine.animation import create_idle_clip, create_punch_clip
from stickfight.engine.animation_player import AnimationPlayer


def test_animation_player_starts_on_idle():
    player = AnimationPlayer({
        "idle": create_idle_clip(),
        "punch": create_punch_clip(),
    })
    assert player.current_name == "idle"
    assert player.clip_time == 0.0


def test_animation_player_advances_and_finishes_non_looping_clip():
    player = AnimationPlayer({
        "idle": create_idle_clip(),
        "punch": create_punch_clip(duration=0.4),
    })
    assert player.play("punch")
    pose, _, _ = player.update(0.5)
    assert pose.joints
    assert player.current_name == "punch"
    assert player.finished


def test_animation_player_crossfades_between_clips():
    player = AnimationPlayer({
        "idle": create_idle_clip(),
        "punch": create_punch_clip(),
    })
    player.update(0.1)
    assert player.play("punch", blend=0.2)
    assert player.transition is not None
    player.update(0.1)
    assert player.transition is not None
    player.update(0.2)
    assert player.transition is None
