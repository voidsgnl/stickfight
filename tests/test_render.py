import os
import pytest
from stickfight import FightScene


def test_headless_render(tmp_path):
    output_mp4 = str(tmp_path / "test_fight.mp4")
    scene = FightScene(width=360, height=640, fps=15)
    A = scene.add_fighter("A", x=120, y=500)
    B = scene.add_fighter("B", x=240, y=500)

    scene.at(0.0, A.punch(B))
    scene.render(output_path=output_mp4, duration=0.8)

    assert os.path.exists(output_mp4)
    assert os.path.getsize(output_mp4) > 1000
