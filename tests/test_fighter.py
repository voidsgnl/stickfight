import pytest
from stickfight.engine.fighter import Fighter
from stickfight.engine.collision import Hitbox, check_hit
from stickfight.engine.scene import FightScene


def test_fighter_initialization():
    f = Fighter("A", x=300, y=1500, facing=1)
    assert f.name == "A"
    assert f.x == 300
    assert f.y == 1500
    assert f.facing == 1
    assert f.health == 100.0


def test_fighter_hurtbox():
    f = Fighter("B", x=600, y=1500)
    hb = f.get_hurtbox()
    assert hb.head_radius > 0
    assert hb.torso_radius > 0
    assert hb.head_pos[1] < hb.pelvis_pos[1]  # head is above pelvis


def test_fighter_punch_hitbox():
    f = Fighter("A", x=400, y=1500, facing=1)
    f.set_animation("punch")
    f.update_animation(0.18)  # Advance to punch strike frame
    hitbox = f.get_hitbox()
    assert hitbox is not None
    assert hitbox.damage > 0
    assert hitbox.attack_type == "punch"


def test_staff_strike_damages_target():
    from stickfight.engine.scene import FightScene

    scene = FightScene(width=640, height=960)
    attacker = scene.add_fighter("Monk", x=300)
    attacker.equip("staff")
    defender = scene.add_fighter("Opponent", x=450)

    action = attacker.staff_strike(defender)
    action.on_start(scene)
    action.update(scene, 0.25, 0.25)

    assert defender.health == pytest.approx(79.0)


def test_staff_combo_sequences_three_hits():
    scene = FightScene(width=640, height=960)
    attacker = scene.add_fighter("Monk", x=300)
    attacker.equip("staff")
    defender = scene.add_fighter("Opponent", x=450)

    scene.at(0.0, attacker.combo("staff_combo", target=defender))
    for _ in range(46):
        scene.update(0.025)

    assert defender.health == pytest.approx(46.0)


@pytest.mark.parametrize(
    ("action_name", "strike_time", "damage"),
    [("punch", 0.18, 7.0), ("kick", 0.25, 9.0)],
)
def test_strike_action_uses_configured_damage(action_name, strike_time, damage, monkeypatch):
    scene = FightScene(width=640, height=960)
    attacker = scene.add_fighter("Attacker", x=250)
    defender = scene.add_fighter("Defender", x=400)
    resolve_attack = scene.resolve_attack

    def resolve_at_hitbox(attacker, defender, hitbox):
        defender.x = hitbox.x
        defender.y = hitbox.y + 265.0
        resolve_attack(attacker, defender, hitbox)

    monkeypatch.setattr(scene, "resolve_attack", resolve_at_hitbox)
    action = getattr(attacker, action_name)(defender, damage=damage)
    action.on_start(scene)
    action.update(scene, strike_time, strike_time)

    assert defender.health == pytest.approx(100.0 - damage)


@pytest.mark.parametrize(("action_name", "weapon", "damage"), [("uppercut", None, 26.0), ("slash", "sword", 28.0)])
def test_heavy_strike_hitboxes_reach_at_engagement_distance(action_name, weapon, damage):
    scene = FightScene(width=640, height=960)
    attacker = scene.add_fighter("Attacker", x=300)
    defender = scene.add_fighter("Defender", x=450)
    if weapon:
        attacker.equip(weapon)

    action = getattr(attacker, action_name)(defender)
    action.on_start(scene)
    action.update(scene, local_t=0.22, dt=0.22)

    assert defender.health == pytest.approx(100.0 - damage)


def test_attack_misses_when_hitbox_does_not_intersect():
    scene = FightScene(width=640, height=960)
    attacker = scene.add_fighter("Attacker", x=250)
    defender = scene.add_fighter("Defender", x=300)
    hitbox = Hitbox(x=attacker.x, y=0.0, radius=10.0, damage=30.0)

    scene.resolve_attack(attacker, defender, hitbox)

    assert defender.health == 100.0


@pytest.mark.parametrize(("state", "expected_health"), [("blocking", 95.0), ("dodging", 100.0)])
def test_defense_only_resolves_intersecting_attacks(state, expected_health):
    scene = FightScene(width=640, height=960)
    attacker = scene.add_fighter("Attacker", x=250)
    defender = scene.add_fighter("Defender", x=300)
    defender.state = state
    head_x, head_y = defender.get_hurtbox().head_pos
    hitbox = Hitbox(x=head_x, y=head_y, radius=5.0, damage=25.0)

    scene.resolve_attack(attacker, defender, hitbox)

    assert defender.health == pytest.approx(expected_health)


def test_combo_carries_elapsed_time_across_children():
    from stickfight.scripting.actions import Action, ComboAction

    class TimedAction(Action):
        def __init__(self, fighter):
            super().__init__(fighter, 0.1)
            self.updated_time = 0.0
            self.finished = False

        def update(self, scene, local_t, dt):
            self.updated_time += dt

        def on_finish(self, scene):
            self.finished = True

    scene = FightScene(width=640, height=960)
    fighter = scene.add_fighter("A", x=250)
    actions = [TimedAction(fighter) for _ in range(3)]
    combo = ComboAction(fighter, actions)
    combo.on_start(scene)
    combo.update(scene, local_t=0.35, dt=0.35)

    assert [action.updated_time for action in actions] == pytest.approx([0.1, 0.1, 0.1])
    assert all(action.finished for action in actions)


def test_generator_seed_is_deterministic_without_changing_global_random():
    import random
    from stickfight.scripting.generator import generate_fight

    global_state = random.getstate()
    first = generate_fight(duration=8.0, seed=42)
    second = generate_fight(duration=8.0, seed=42)
    first_events = [(event.start_time, type(event.action).__name__) for event in first.timeline.events]
    second_events = [(event.start_time, type(event.action).__name__) for event in second.timeline.events]

    assert first_events == second_events
    assert random.getstate() == global_state


@pytest.mark.parametrize("style", ["segmented", "silhouette", "classic", "tech", "ink_fight"])
def test_fighter_render_styles_are_configurable(style):
    fighter = Fighter("Styled", render_style=style)
    assert fighter.render_style == style


def test_scene_exposes_render_style():
    scene = FightScene(width=640, height=960)
    fighter = scene.add_fighter("Styled", render_style="silhouette")
    assert fighter.render_style == "silhouette"
