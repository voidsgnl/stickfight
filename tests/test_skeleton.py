import pytest
from stickfight.engine.skeleton import Pose, make_idle_pose, make_punch_strike


def test_pose_lerp():
    p1 = Pose({"head": (0.0, -100.0), "pelvis": (0.0, 0.0)})
    p2 = Pose({"head": (50.0, -100.0), "pelvis": (10.0, 0.0)})

    mid = p1.lerp(p2, 0.5)
    assert mid.get("head") == (25.0, -100.0)
    assert mid.get("pelvis") == (5.0, 0.0)


def test_pose_flip():
    p = Pose({
        "left_shoulder": (-20.0, -80.0),
        "right_shoulder": (20.0, -80.0),
        "head": (10.0, -120.0),
    })
    flipped = p.flip_horizontal()
    # Left and right shoulders swapped and x-mirrored
    assert flipped.get("left_shoulder") == (-20.0, -80.0)
    assert flipped.get("right_shoulder") == (20.0, -80.0)
    assert flipped.get("head") == (-10.0, -120.0)


def test_world_coordinates():
    p = make_idle_pose()
    world = p.to_world(root_x=400.0, root_y=1360.0, facing=1, scale=1.0)
    assert "head" in world
    assert "pelvis" in world
    assert world["pelvis"] == (400.0, 1360.0)
