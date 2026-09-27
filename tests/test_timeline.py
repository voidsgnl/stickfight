import pytest
from stickfight.engine.scene import FightScene


def test_timeline_duration():
    scene = FightScene(width=1080, height=1920, fps=30)
    A = scene.add_fighter("A", x=300)
    B = scene.add_fighter("B", x=700)

    scene.at(0.0, A.walk_to(500, duration=1.5))
    scene.at(1.5, B.punch(A, duration=0.5))

    total = scene.timeline.get_total_duration(tail_padding=0.0)
    assert total == pytest.approx(2.0, abs=1e-3)


def test_scene_update():
    scene = FightScene(width=1080, height=1920, fps=30)
    A = scene.add_fighter("A", x=300)
    scene.at(0.0, A.walk_to(500, duration=1.0))

    assert A.x == 300
    scene.update(0.5)
    assert 380 < A.x < 420
    scene.update(0.5)
    assert A.x == pytest.approx(500.0, abs=1.0)
