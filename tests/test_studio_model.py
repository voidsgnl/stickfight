from stickfight.studio import (
    AnimationProject,
    AnimationScene,
    CharacterAsset,
    CharacterInstance,
    TimelineTrack,
)
from stickfight.studio.styles import get_style


def test_project_supports_many_character_instances_and_styles():
    project = AnimationProject("demo")
    project.add_asset(
        CharacterAsset("kai", "Kai", visual_style=get_style("anime"))
    )
    project.add_asset(
        CharacterAsset("rex", "Rex", visual_style=get_style("cartoon"))
    )

    scene = AnimationScene("scene-1", "Opening")
    scene.add_character(CharacterInstance("kai-1", "kai", x=100))
    scene.add_character(CharacterInstance("rex-1", "rex", x=500))
    scene.add_character(CharacterInstance("kai-2", "kai", x=800))
    scene.add_track(TimelineTrack("kai-track", "Kai", "character", "kai-1"))
    project.add_scene(scene)

    assert len(scene.characters) == 3
    assert project.assets["kai"].visual_style.id == "anime"
    assert project.assets["rex"].visual_style.id == "cartoon"
    assert project.validate() == []


def test_validation_catches_missing_asset_and_target():
    project = AnimationProject("broken")
    scene = AnimationScene("scene", "Broken")
    scene.add_character(CharacterInstance("hero", "missing"))
    scene.add_track(TimelineTrack("track", "Hero", "character", "missing-instance"))
    project.add_scene(scene)

    errors = project.validate()
    assert any("missing character asset" in e for e in errors)
    assert any("missing instance" in e for e in errors)
