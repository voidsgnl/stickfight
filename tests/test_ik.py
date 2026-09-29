from math import hypot

from stickfight.engine.ik import apply_two_bone_ik
from stickfight.engine.skeleton import Pose
from stickfight.engine.fighter import Fighter


def test_two_bone_ik_reaches_target_within_rig_limits():
    pose = Pose({
        "right_shoulder": (0.0, 0.0),
        "right_elbow": (30.0, 0.0),
        "right_hand": (60.0, 0.0),
    })
    target = (45.0, 25.0)
    solved = apply_two_bone_ik(
        pose, "right_shoulder", "right_elbow", "right_hand", target
    )
    assert hypot(
        solved.get("right_hand")[0] - target[0],
        solved.get("right_hand")[1] - target[1],
    ) < 1e-5


def test_fighter_attack_ik_tracks_defender_head():
    attacker = Fighter("A", x=400, y=1500)
    defender = Fighter("B", x=560, y=1500)

    attacker.set_animation("punch", loop=False)
    attacker.aim_attack_at(defender)
    attacker.update_animation(0.18)

    joints = attacker.get_world_joints()
    target = defender.get_hurtbox().head_pos
    hand = joints["right_hand"]

    assert hypot(hand[0] - target[0], hand[1] - target[1]) < 20.0
