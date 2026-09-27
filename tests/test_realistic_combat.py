"""
Unit tests for Realistic Combat mechanics (Boxing, Muay Thai, MMA, Ground Fighting).
"""

import pytest
import os

os.environ["SDL_VIDEODRIVER"] = "dummy"

from stickfight import FightScene, Fighter
from stickfight.engine.skeleton import (
    make_jab_strike,
    make_cross_strike,
    make_hook_strike,
    make_low_kick_pose,
    make_check_kick_pose,
    make_slip_pose,
    make_bob_weave_pose,
    make_clinch_knee_pose,
    make_takedown_shoot_pose,
    make_ground_and_pound_top_pose,
    make_stagger_pose,
)
from stickfight.engine.animation import (
    create_jab_clip,
    create_cross_clip,
    create_hook_clip,
    create_low_kick_clip,
    create_check_kick_clip,
    create_slip_clip,
    create_bob_weave_clip,
    create_clinch_knee_clip,
    create_takedown_clip,
    create_ground_pound_clip,
    create_stagger_clip,
)
from stickfight.scripting.actions import (
    JabAction,
    CrossAction,
    HookAction,
    LowKickAction,
    CheckKickAction,
    SlipAction,
    BobWeaveAction,
    ClinchKneeAction,
    TakedownAction,
    GroundPoundAction,
    StaggerAction,
)
from stickfight.scripting.generator import generate_fight


def test_realistic_poses():
    poses = [
        make_jab_strike(),
        make_cross_strike(),
        make_hook_strike(),
        make_low_kick_pose(),
        make_check_kick_pose(),
        make_slip_pose(),
        make_bob_weave_pose(),
        make_clinch_knee_pose(),
        make_takedown_shoot_pose(),
        make_ground_and_pound_top_pose(),
        make_stagger_pose(),
    ]
    for p in poses:
        assert p is not None
        assert hasattr(p, "joints")
        assert "pelvis" in p.joints
        assert "head" in p.joints
        assert "left_hand" in p.joints
        assert "right_hand" in p.joints
        assert "left_foot" in p.joints
        assert "right_foot" in p.joints
        # World joint computation should work without error
        joints = p.to_world(500, 500, facing=1, scale=1.0)
        assert "head" in joints
        assert "left_hand" in joints
        assert "right_hand" in joints
        assert "left_foot" in joints
        assert "right_foot" in joints


def test_realistic_animation_clips():
    clips = [
        create_jab_clip(),
        create_cross_clip(),
        create_hook_clip(),
        create_low_kick_clip(),
        create_check_kick_clip(),
        create_slip_clip(),
        create_bob_weave_clip(),
        create_clinch_knee_clip(),
        create_takedown_clip(),
        create_ground_pound_clip(),
        create_stagger_clip(),
    ]
    for clip in clips:
        assert clip is not None
        assert clip.duration > 0.0
        assert len(clip.keyframes) >= 2
        pose, rdx, rdy = clip.evaluate(clip.duration / 2.0)
        assert pose is not None
        assert hasattr(pose, "joints")
        assert "head" in pose.joints


def test_fighter_realistic_actions_execution():
    scene = FightScene(width=1080, height=720, fps=30, style="realistic")
    f1 = scene.add_fighter("Boxer A", x=400, y=500, facing=1)
    f2 = scene.add_fighter("Boxer B", x=500, y=500, facing=-1)

    assert scene.style == "realistic"

    # Test individual action methods
    act_jab = f1.jab(f2, duration=0.35)
    assert isinstance(act_jab, JabAction)

    act_cross = f1.cross(f2, duration=0.40)
    assert isinstance(act_cross, CrossAction)

    act_hook = f1.hook(f2, duration=0.42)
    assert isinstance(act_hook, HookAction)

    act_low_kick = f1.low_kick(f2, duration=0.42)
    assert isinstance(act_low_kick, LowKickAction)

    act_check = f2.check_kick(duration=0.45)
    assert isinstance(act_check, CheckKickAction)

    act_slip = f2.slip(duration=0.40)
    assert isinstance(act_slip, SlipAction)

    act_bob = f1.bob_weave(duration=0.45)
    assert isinstance(act_bob, BobWeaveAction)

    act_knee = f1.clinch_knee(f2, duration=0.50)
    assert isinstance(act_knee, ClinchKneeAction)

    act_takedown = f1.takedown(f2, duration=0.70)
    assert isinstance(act_takedown, TakedownAction)

    act_gnp = f1.ground_pound(f2, duration=0.55)
    assert isinstance(act_gnp, GroundPoundAction)

    act_stagger = f2.stagger(duration=0.50)
    assert isinstance(act_stagger, StaggerAction)


def test_low_kick_vs_shin_check_mechanic():
    scene = FightScene(width=1080, height=720, fps=30, style="realistic")
    f1 = scene.add_fighter("Attacker", x=400, y=500, facing=1)
    f2 = scene.add_fighter("Defender", x=480, y=500, facing=-1)

    # Defender checks
    f2.state = "checking"
    initial_f1_health = f1.health
    initial_f2_health = f2.health

    low_kick = LowKickAction(f1, f2, damage=16.0, duration=0.42)
    low_kick.on_start(scene)
    low_kick.update(scene, 0.20, 0.033)  # Impact point

    # Attacker absorbs recoil damage when checked
    assert f1.health < initial_f1_health
    # Defender took no damage
    assert f2.health == initial_f2_health


def test_takedown_and_ground_pound_flow():
    scene = FightScene(width=1080, height=720, fps=30, style="realistic")
    f1 = scene.add_fighter("Wrestler", x=400, y=500, facing=1)
    f2 = scene.add_fighter("Opponent", x=480, y=500, facing=-1)

    takedown = TakedownAction(f1, f2, damage=22.0, duration=0.70)
    takedown.on_start(scene)
    takedown.update(scene, 0.45, 0.033)

    # Defender should be grounded/fallen
    assert f2.state == "fallen"
    assert f2.active_clip.name in ["fallen", "fall"]

    # Follow up with ground and pound
    gnp = GroundPoundAction(f1, f2, damage=28.0, duration=0.55)
    gnp.on_start(scene)
    gnp.update(scene, 0.28, 0.033)
    assert f2.health < 100.0


def test_realistic_combos():
    scene = FightScene(width=1080, height=720, fps=30, style="realistic")
    f1 = scene.add_fighter("Martial Artist", x=400, y=500, facing=1)
    f2 = scene.add_fighter("Opponent", x=500, y=500, facing=-1)

    c1 = f1.combo("one_two", target=f2)
    assert c1 is not None
    assert len(c1.actions) == 2

    c2 = f1.combo("dutch_kickboxing", target=f2)
    assert c2 is not None
    assert len(c2.actions) == 4

    c3 = f1.combo("mma_clinch_takedown", target=f2)
    assert c3 is not None
    assert len(c3.actions) == 3


def test_procedural_generator_realistic_style():
    scene = generate_fight(
        duration=4.0,
        fighter_a_type="brawler",
        fighter_b_type="classic",
        environment="city",
        seed=42,
        style="realistic",
    )
    assert scene.style == "realistic"
    assert len(scene.fighters) == 2
    assert len(scene.timeline.events) > 0
