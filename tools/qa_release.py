import hashlib
import json
import os
import random
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from combat import CombatEngine
from content import ENEMIES, ITEM_TEMPLATES, STAGES, create_item, recipe_result, starter_loadout
from game import Game, Screen
from models import Hero, ItemKind
from systems import Mixer, SaveManager
from ui import COLORS


NEW_POTIONS = (
    "bloodsalt_elixir",
    "stoneblood_flask",
    "stormstep_serum",
    "moonmilk_cordial",
    "last_breath_phial",
)

NEW_RECIPES = (
    ("minor_tonic", "fury_phial", "bloodsalt_elixir"),
    ("field_tonic", "ironbark_tonic", "stoneblood_flask"),
    ("fortune_vial", "fury_phial", "stormstep_serum"),
    ("vital_draught", "fortune_vial", "moonmilk_cordial"),
    ("phoenix_cordial", "greater_tonic", "last_breath_phial"),
)

SPECIAL_TRINKETS = (
    "graveglass_pendant",
    "cinder_locket",
    "tempest_talisman",
    "watcher_stone",
    "sovereign_reliquary",
)

NEW_GEAR = (
    "pilgrim_crook", "slag_hammer", "moonlit_khopesh", "basilisk_needle", "sovereign_axe",
    "gravewood_targe", "mothwing_ward", "dragonbone_pavise",
    "pilgrim_bell", "ashglass_charm", "witchglass_bead", "oathstone_necklace",
)

HERO_LAYOUTS = {"idle": 8, "run": 10, "attack": 6, "critical": 7, "hurt": 3, "guard": 5, "victory": 8, "defeat": 10}


def pygame_to_pil(surface):
    return Image.frombytes("RGB", surface.get_size(), pygame.image.tobytes(surface, "RGB"))


def test_drag_drop(game):
    game.new_game()
    game.transition_target = None
    weapon = create_item("bone_cleaver", random.Random(2), 5)
    assert game.hero.add_item(weapon)
    game.item_drag_zones = []
    game.drag_candidate = {"uid": weapon.uid, "role": "inventory", "index": len(game.hero.inventory) - 1, "slot": None}
    game.register_item_drag_zone(pygame.Rect(0, 0, 30, 30), "equipment", game.hero.equipment["weapon"], slot="weapon")
    game.finish_item_drag((15, 15))
    assert game.hero.equipment["weapon"].uid == weapon.uid

    potion = create_item("stormstep_serum", random.Random(3), 15)
    assert game.hero.add_item(potion)
    game.item_drag_zones = []
    game.drag_candidate = {"uid": potion.uid, "role": "inventory", "index": len(game.hero.inventory) - 1, "slot": None}
    game.register_item_drag_zone(pygame.Rect(0, 0, 30, 30), "boost")
    game.finish_item_drag((15, 15))
    assert game.hero.boost_uid == potion.uid

    essence = create_item("ember_essence", random.Random(4), 10)
    assert game.hero.add_item(essence)
    game.item_drag_zones = []
    game.drag_candidate = {"uid": essence.uid, "role": "inventory", "index": len(game.hero.inventory) - 1, "slot": None}
    game.register_item_drag_zone(pygame.Rect(0, 0, 30, 30), "mixer_catalyst")
    game.finish_item_drag((15, 15))
    assert game.mixer_right == essence.uid


def test_potions():
    hero = Hero()
    first = create_item("minor_tonic", random.Random(80), 1)
    second = create_item("minor_tonic", random.Random(81), 1)
    assert first.max_stack == second.max_stack == 1
    assert hero.add_item(first) and hero.add_item(second)
    assert len(hero.inventory) == 2
    assert all(item.stack == 1 for item in hero.inventory)

    for index, template_id in enumerate(NEW_POTIONS):
        hero = Hero()
        potion = create_item(template_id, random.Random(100 + index), 20)
        assert hero.add_item(potion)
        assert hero.set_boost(potion.uid)[0]
        battle = CombatEngine(hero, STAGES[0], random.Random(200 + index))
        battle.hero_hp = max(1, battle.hero_max_hp - 12)
        ok, message = battle.use_boost()
        assert ok, message
        assert battle.boost_used

    for index, (first_id, second_id, result_id) in enumerate(NEW_RECIPES):
        hero = Hero()
        first = create_item(first_id, random.Random(300 + index * 2), 15)
        second = create_item(second_id, random.Random(301 + index * 2), 15)
        assert hero.add_item(first) and hero.add_item(second)
        ok, message, result = Mixer.mix(hero, first.uid, second.uid)
        assert ok, message
        assert result.template_id == result_id


def test_universal_fusions():
    template_ids = tuple(ITEM_TEMPLATES)
    for left_index, left_id in enumerate(template_ids):
        for right_index, right_id in enumerate(template_ids):
            left = create_item(left_id, random.Random(1000 + left_index), 12)
            right = create_item(right_id, random.Random(2000 + right_index), 12)
            ok, message = Mixer.preview(left, right)
            assert ok, (left_id, right_id, message)
            result = Mixer.visual_result(left, right)
            assert result is not None, (left_id, right_id)
            if not recipe_result(left_id, right_id):
                assert result.effects.get("fusion_visual"), (left_id, right_id)
                assert result.max_stack == 1

    examples = (
        ("rusted_falchion", "ghost_salt"),
        ("splintered_guard", "minor_tonic"),
        ("copper_loop", "bone_cleaver"),
        ("minor_tonic", "ember_essence"),
        ("rime_essence", "iron_scrap"),
        ("bone_shard", "fortune_vial"),
    )
    for index, (left_id, right_id) in enumerate(examples):
        hero = Hero()
        left = create_item(left_id, random.Random(3000 + index * 2), 12)
        right = create_item(right_id, random.Random(3001 + index * 2), 12)
        assert hero.add_item(left) and hero.add_item(right)
        ok, message, result = Mixer.mix(hero, left.uid, right.uid)
        assert ok, message
        assert result.effects.get("fusion_visual")

    # A catalyst contributes only part of its stat budget. A 10 ATK kept
    # weapon mixed with a 5 ATK weapon must not become a direct 15 ATK sum.
    left = create_item("pilgrim_crook", random.Random(4900), 1)
    right = create_item("wayfarer_blade", random.Random(4901), 1)
    left.stats = {"attack": 10}
    left.caps = {"attack": 18}
    right.stats = {"attack": 5}
    result = Mixer.visual_result(left, right)
    assert result.stats["attack"] == 12, result.stats
    assert result.stats["attack"] != 15

    same_left = create_item("rusted_falchion", random.Random(4910), 1)
    same_right = create_item("rusted_falchion", random.Random(4911), 1)
    reinforced = Mixer.visual_result(same_left, same_right)
    assert reinforced.stats["attack"] == same_left.stats["attack"] + 2


def test_shields_and_trinkets():
    shield_ids = [template_id for template_id, template in ITEM_TEMPLATES.items() if template["kind"] == ItemKind.SHIELD]
    assert shield_ids
    for template_id in shield_ids:
        shield = create_item(template_id, random.Random(5100), 15)
        assert shield.stats.get("defense", 0) >= 5, template_id
        assert "guard_points" not in shield.effects, template_id

    for index, template_id in enumerate(SPECIAL_TRINKETS):
        trinket = create_item(template_id, random.Random(5200 + index), 15)
        assert trinket.kind == ItemKind.RING
        assert trinket.category_label != "Ring"
        hero = Hero()
        assert hero.add_item(trinket)
        assert hero.equip(trinket.uid, "ring1")[0]
        assert hero.equipment["ring1"].uid == trinket.uid

    hero = Hero()
    loadout = starter_loadout()
    hero.equipment = loadout["equipment"]
    hero.inventory = loadout["inventory"]
    assert hero.equipment["shield"] is None
    assert STAGES[0].first_clear_item == "patched_buckler"
    battle = CombatEngine(hero, STAGES[0], random.Random(77))
    assert not hasattr(battle, "hero_guard")
    assert not hasattr(battle, "hero_guard_max")
    shield = create_item("patched_buckler", random.Random(5300), 1)
    assert hero.add_item(shield)
    assert hero.equip(shield.uid)[0]
    battle = CombatEngine(hero, STAGES[0], random.Random(77))
    assert battle.hero_defense == hero.total_stats()["defense"] == 9
    assert not hasattr(battle, "hero_guard")
    assert not hasattr(battle, "hero_guard_max")
    battle.drain_events()
    starting_hp = battle.hero_hp
    battle.hero_stats["luck"] = 0
    battle.enemy.attack = 20
    battle._enemy_strike()
    events = battle.drain_events()
    assert battle.hero_anim == "guard"
    assert battle.hero_hp < starting_hp
    assert all(event.event_type not in {"shield_guard", "guard_ready"} for event in events)
    assert any(event.event_type == "enemy_hit" for event in events)


def test_balance_save_migration():
    hero = Hero()
    loadout = starter_loadout()
    hero.equipment = loadout["equipment"]
    hero.inventory = loadout["inventory"]
    shield = create_item("patched_buckler", random.Random(5400), 1)
    shield.effects["guard_points"] = 3
    hero.equipment["shield"] = shield
    old_save = hero.to_dict()
    old_save.pop("balance_version")
    old_save["base_stats"]["attack"] = 8
    old_save["equipment"]["weapon"]["stats"]["attack"] = 10
    old_save["equipment"]["weapon"]["caps"]["attack"] = 20
    payload = {"version": 3, "saved_at": 0, "selected_stage": 1, "hero": old_save}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload["checksum"] = hashlib.sha256(encoded).hexdigest()[:20]
    with tempfile.TemporaryDirectory(prefix="bonebound-balance-") as temp_dir:
        save_path = Path(temp_dir) / "savegame.json"
        save_path.write_text(json.dumps(payload), encoding="utf-8")
        migrated, selected_stage = SaveManager(save_path).load()
    assert selected_stage == 1
    assert migrated.total_stats()["attack"] == 13
    assert migrated.equipment["weapon"].caps["attack"] == 16
    assert "guard_points" not in migrated.equipment["shield"].effects
    assert migrated.to_dict()["balance_version"] == Hero.BALANCE_VERSION


def test_launch_balance():
    wins = 0
    remaining_hp = []
    for seed in range(200):
        hero = Hero()
        loadout = starter_loadout()
        hero.equipment = loadout["equipment"]
        hero.inventory = loadout["inventory"]
        assert hero.total_stats() == {"health": 55, "attack": 13, "defense": 4, "luck": 3}
        battle = CombatEngine(hero, STAGES[0], random.Random(10000 + seed))
        for _ in range(200):
            if not battle.active:
                break
            battle.update(1.0)
        if battle.outcome.value == "victory":
            wins += 1
            remaining_hp.append(battle.hero_hp)
    win_rate = wins / 200
    assert .72 <= win_rate <= .88, win_rate
    assert remaining_hp and sum(remaining_hp) / len(remaining_hp) < 15
    assert STAGES[0].difficulty == 1.08
    assert STAGES[-1].difficulty > 1.25


def test_campaign_scale_and_boss_phase():
    hero = Hero()
    for _ in range(24):
        hero.gain_xp(hero.xp_needed)
    for template_id, slot in (
        ("sovereign_axe", "weapon"),
        ("dragonbone_pavise", "shield"),
        ("witchglass_bead", "ring1"),
        ("fortune_eclipse", "ring2"),
    ):
        item = create_item(template_id, random.Random(7200 + len(hero.inventory)), 1)
        assert hero.add_item(item)
        assert hero.equip(item.uid, slot)[0]
    assert hero.level == 25
    assert hero.total_stats()["health"] == 495, hero.total_stats()

    boss_health = []
    for stage in STAGES[4::5]:
        battle = CombatEngine(hero, stage, random.Random(7300 + stage.index))
        battle.enemy_index = len(stage.enemies) - 2
        battle._spawn_next_enemy()
        assert battle.enemy.boss
        boss_health.append(battle.enemy.max_hp)
    assert boss_health == sorted(boss_health)
    assert boss_health[-1] >= 1000, boss_health

    final = CombatEngine(hero, STAGES[-1], random.Random(7400))
    final.enemy_index = len(STAGES[-1].enemies) - 2
    final._spawn_next_enemy()
    before_attack = final.enemy.attack
    final.enemy.hp = final.enemy.max_hp // 2
    assert final._trigger_boss_phase()
    assert final.boss_phase_triggered
    assert final.enemy.attack > before_attack
    assert any(event.event_type == "boss_phase" for event in final.drain_events())

    def campaign_win_rate(stage_index, level, gear, attack_points, health_points):
        wins = 0
        samples = 160
        for seed in range(samples):
            runner = Hero()
            for _ in range(level - 1):
                runner.gain_xp(runner.xp_needed)
            for _ in range(attack_points):
                assert runner.spend_point("attack")
            for _ in range(health_points):
                assert runner.spend_point("health")
            for template_id, slot in zip(gear, ("weapon", "shield", "ring1", "ring2")):
                item = create_item(template_id, random.Random(seed * 13 + len(runner.inventory)), stage_index)
                for _ in range(2):
                    Mixer._reinforce(item)
                assert runner.add_item(item)
                assert runner.equip(item.uid, slot)[0]
            fight = CombatEngine(runner, STAGES[stage_index - 1], random.Random(100000 + seed))
            for _ in range(4000):
                if not fight.active:
                    break
                fight.update(1.0)
            wins += fight.outcome.value == "victory"
        return wins / samples

    act_four_rate = campaign_win_rate(
        20, 18, ("basilisk_needle", "runic_bastion", "witchglass_bead", "watcher_stone"), 9, 8,
    )
    final_rate = campaign_win_rate(
        25, 22, ("voidglass_sabre", "dragonbone_pavise", "fortune_eclipse", "oathstone_necklace"), 11, 10,
    )
    assert .40 <= act_four_rate <= .72, act_four_rate
    assert .30 <= final_rate <= .62, final_rate


def test_wave_counter_bounds():
    hero = Hero()
    loadout = starter_loadout()
    hero.equipment = loadout["equipment"]
    hero.inventory = loadout["inventory"]
    battle = CombatEngine(hero, STAGES[0], random.Random(7500))
    battle.enemy_index = battle.wave_total - 1
    battle._spawn_next_enemy()
    assert battle.outcome.value == "victory"
    assert battle.wave_number == battle.wave_total


def test_content_expansion():
    assert len(ITEM_TEMPLATES) >= 81
    for template_id in NEW_GEAR:
        template = ITEM_TEMPLATES[template_id]
        assert template["description"]
        assert (ROOT / "assets" / "items" / f"{template_id}.png").is_file()


def test_rat_animation(game):
    for state in ("idle", "run", "attack", "defeat"):
        frames = game.sprites.enemy_frames.get(("dust_rat", state), [])
        assert len(frames) == 6, (state, len(frames))
        assert len({frame.get_size() for frame in frames}) == 1
        for frame in frames:
            bounds = frame.get_bounding_rect(min_alpha=8)
            assert bounds.width and bounds.height
            assert bounds.left >= 4 and bounds.right <= frame.get_width() - 4
            assert bounds.top >= 4 and bounds.bottom <= frame.get_height() - 3


def test_enemy_canvases(game):
    from content import ENEMIES

    for enemy_id in ENEMIES:
        sizes = set()
        for state in ("idle", "run", "attack", "defeat"):
            frames = game.sprites.enemy_frames.get((enemy_id, state), [])
            assert frames, (enemy_id, state)
            sizes.update(frame.get_size() for frame in frames)
            for frame in frames:
                bounds = frame.get_bounding_rect(min_alpha=8)
                assert bounds.width and bounds.height, (enemy_id, state)
                assert bounds.left >= 4 and bounds.right <= frame.get_width() - 4, (enemy_id, state, bounds, frame.get_size())
                assert bounds.top >= 4 and bounds.bottom <= frame.get_height() - 3, (enemy_id, state, bounds, frame.get_size())
        assert len(sizes) == 1, (enemy_id, sizes)


def test_hero_cohesion(game):
    for state, expected_count in HERO_LAYOUTS.items():
        frames = game.sprites.frames.get(("hero", state), [])
        assert len(frames) == expected_count, (state, len(frames))
        for frame in frames:
            assert frame.get_size() == (96, 96)
            bounds = frame.get_bounding_rect(min_alpha=8)
            assert bounds.width <= 94 and bounds.height <= 94, (state, bounds)
            # The old human face/hand palette must not leak back into any pose.
            assert all(frame.get_at((x, y))[:3] != (222, 174, 125) for y in range(96) for x in range(96))

        poses = game.sprites.hero_equipment_points.get(state, [])
        assert len(poses) == expected_count, (state, "equipment points", len(poses))
        if state in {"hurt", "defeat"}:
            continue
        for pose in poses:
            for key in ("weapon_grip", "weapon_elbow", "shield_center"):
                x, y = pose[key]
                assert 1 <= x <= 95 and 1 <= y <= 95, (state, key, pose[key])
            assert -180 <= pose["weapon_angle"] <= 180

    idle = game.sprites.frames[("hero", "idle")][0]
    mask_points = []
    cloth_points = []
    grave_light_points = []
    for y in range(96):
        for x in range(96):
            r, g, b, alpha = idle.get_at((x, y))
            if alpha < 16:
                continue
            if r > 160 and g > 155 and b > 140 and abs(r - g) < 25 and r > b and g > b:
                mask_points.append((x, y))
            if g > r * 1.45 and g > b * 1.02 and 75 < g < 205:
                cloth_points.append((x, y))
            if g > 205 and 60 < r < 105 and 135 < b < 190:
                grave_light_points.append((x, y))
    assert mask_points and cloth_points
    mask_width = max(x for x, _ in mask_points) - min(x for x, _ in mask_points) + 1
    torso_width = max(x for x, _ in cloth_points) - min(x for x, _ in cloth_points) + 1
    assert mask_width <= torso_width * .65, (mask_width, torso_width)
    assert grave_light_points
    mask_center_x = (min(x for x, _ in mask_points) + max(x for x, _ in mask_points)) / 2
    assert max(x for x, _ in grave_light_points) > mask_center_x, (grave_light_points, mask_center_x)


def test_item_alpha():
    from content import ITEM_TEMPLATES

    item_root = ROOT / "assets" / "items"
    for template_id, template in ITEM_TEMPLATES.items():
        if template["kind"].value not in {"weapon", "shield", "ring", "potion"}:
            continue
        image = pygame.image.load(item_root / f"{template_id}.png")
        width, height = image.get_size()
        corners = ((0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1))
        assert all(image.get_at(point).a < 16 for point in corners), (template_id, "opaque item backdrop")
        transparent = sum(image.get_at((x, y)).a < 16 for y in range(height) for x in range(width))
        assert transparent >= width * height * .12, (template_id, transparent, width * height)


def render_animation(game, output_dir, state, frame_count, duration_ms):
    frames = []
    for index in range(frame_count):
        elapsed = index / max(1, frame_count - 1) * (.56 if state == "critical" else .60)
        game.screen_surface.fill((9, 13, 18))
        pygame.draw.rect(game.screen_surface, (16, 22, 29), (0, 0, 540, 480))
        pygame.draw.circle(game.screen_surface, (34, 42, 52), (265, 175), 132, 2)
        pygame.draw.line(game.screen_surface, (92, 72, 51), (36, 425), (505, 425), 4)
        game.time = elapsed
        game.draw_hero(pygame.Vector2(245, 412), state, elapsed, .92)
        frame = game.screen_surface.subsurface((0, 0, 540, 480)).copy()
        frames.append(pygame_to_pil(frame))
    frames[0].save(
        output_dir / f"hero_{state}_animation_v4.gif",
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=0,
        optimize=False,
    )
    rows = (len(frames) + 3) // 4
    contact = Image.new("RGB", (540 * 4, 480 * rows), (9, 13, 18))
    for index, frame in enumerate(frames):
        thumb = frame.resize((540, 480), Image.Resampling.NEAREST)
        contact.paste(thumb, ((index % 4) * 540, (index // 4) * 480))
    contact.save(output_dir / f"hero_{state}_contact_v10.png")


def render_hero_state_catalog(game, output_dir):
    surface = pygame.Surface((1200, 670))
    surface.fill((8, 12, 17))
    game.ui.text(surface, "BONEBOUND  •  MYSTIC WAYFARER", (40, 26), COLORS["gold"], "medium")
    chosen_frames = {"idle": 0, "run": 3, "attack": 4, "critical": 5, "hurt": 1, "guard": 3, "victory": 4, "defeat": 7}
    for index, state in enumerate(HERO_LAYOUTS):
        row, col = divmod(index, 4)
        card = pygame.Rect(25 + col * 292, 72 + row * 292, 274, 268)
        game.ui.ornamented_panel(surface, card, (15, 21, 28), (67, 119, 116), 10, 2)
        pygame.draw.circle(surface, (32, 41, 49), (card.centerx, card.y + 118), 86, 2)
        pygame.draw.line(surface, (91, 69, 49), (card.x + 23, card.y + 225), (card.right - 23, card.y + 225), 3)
        frame = game.sprites.frames[("hero", state)][chosen_frames[state]]
        enlarged = pygame.transform.scale(frame, (230, 230))
        surface.blit(enlarged, enlarged.get_rect(midbottom=(card.centerx, card.y + 230)))
        game.ui.text(surface, state.upper(), (card.centerx, card.bottom - 25), COLORS["text"], "small", "center")
    pygame.image.save(surface, output_dir / "hero_mystic_design_v10.png")


def render_equipment_hold_catalog(game, output_dir):
    game.new_game()
    game.transition_target = None
    shield = create_item("patched_buckler", random.Random(6700), 1)
    assert game.hero.add_item(shield)
    assert game.hero.equip(shield.uid)[0]
    poses = (("idle", .20), ("run", .25), ("attack", .31), ("critical", .39), ("guard", .25))
    atlas = pygame.Surface((1260, 360))
    atlas.fill((8, 12, 17))
    game.ui.text(atlas, "EQUIPPED SWORD + SHIELD • HAND-LOCK CHECK", (28, 20), COLORS["gold"], "medium")
    for index, (pose, elapsed) in enumerate(poses):
        game.screen_surface.fill((11, 16, 22))
        pygame.draw.circle(game.screen_surface, (33, 43, 52), (300, 230), 130, 2)
        pygame.draw.line(game.screen_surface, (91, 69, 49), (100, 420), (500, 420), 4)
        game.time = elapsed
        game.draw_hero(pygame.Vector2(300, 410), pose, elapsed, .86)
        crop = game.screen_surface.subsurface((70, 80, 460, 360)).copy()
        card = pygame.Rect(15 + index * 248, 62, 235, 280)
        atlas.blit(pygame.transform.smoothscale(crop, (235, 184)), (card.x, card.y + 30))
        pygame.draw.rect(atlas, (65, 105, 109), card, 2)
        game.ui.text(atlas, pose.upper(), (card.centerx, card.bottom - 17), COLORS["text"], "small", "center")
    pygame.image.save(atlas, output_dir / "hero_equipment_holds_v10.png")


def render_shield_brace_animation(game, output_dir):
    frames = []
    for index in range(5):
        elapsed = index / 12
        game.screen_surface.fill((10, 15, 21))
        pygame.draw.circle(game.screen_surface, (34, 43, 52), (270, 195), 135, 2)
        pygame.draw.line(game.screen_surface, (91, 69, 49), (40, 425), (500, 425), 4)
        game.time = elapsed
        game.draw_hero(pygame.Vector2(260, 412), "guard", elapsed, .92)
        frames.append(pygame_to_pil(game.screen_surface.subsurface((0, 0, 540, 480)).copy()))
    frames[0].save(output_dir / "hero_shield_brace_v10.gif", save_all=True,
                   append_images=frames[1:], duration=90, loop=0, optimize=False)
    contact = Image.new("RGB", (540 * len(frames), 480), (9, 13, 18))
    for index, frame in enumerate(frames):
        contact.paste(frame, (index * 540, 0))
    contact.save(output_dir / "hero_shield_brace_contact_v10.png")


def render_potion_catalog(game, output_dir):
    potions = [template_id for template_id, template in ITEM_TEMPLATES.items() if template["kind"] == ItemKind.POTION]
    surface = pygame.Surface((1140, 620))
    surface.fill((9, 13, 18))
    game.ui.text(surface, "BONEBOUND  •  POTION SILHOUETTES", (40, 28), COLORS["gold"], "medium")
    for index, template_id in enumerate(potions):
        row, col = divmod(index, 4)
        card = pygame.Rect(35 + col * 276, 78 + row * 132, 258, 114)
        item = create_item(template_id, random.Random(500 + index), max(1, ITEM_TEMPLATES[template_id]["tier"] * 5))
        game.ui.ornamented_panel(surface, card, (16, 22, 30), game.ui.item_color(item), 9, 1)
        game.ui.draw_item_icon(surface, pygame.Rect(card.x + 10, card.y + 16, 78, 78), item, True)
        game.ui.fitted_text(surface, item.display_name, pygame.Rect(card.x + 96, card.y + 19, 150, 25), COLORS["text"], "small")
        game.ui.wrapped(surface, item.stat_text(), pygame.Rect(card.x + 96, card.y + 51, 150, 42), game.ui.item_color(item), "tiny", 3, 2)
    pygame.image.save(surface, output_dir / "item_potion_catalog_v4.png")


def render_new_gear_catalog(game, output_dir):
    surface = pygame.Surface((1200, 760))
    surface.fill((8, 12, 17))
    game.ui.text(surface, "BONEBOUND • TWELVE NEW RELICS", (34, 24), COLORS["gold"], "medium")
    for index, template_id in enumerate(NEW_GEAR):
        row, col = divmod(index, 4)
        card = pygame.Rect(20 + col * 295, 70 + row * 225, 275, 205)
        item = create_item(template_id, random.Random(8100 + index), max(1, ITEM_TEMPLATES[template_id]["tier"] * 5))
        color = game.ui.item_color(item)
        game.ui.ornamented_panel(surface, card, (15, 21, 28), color, 9, 2)
        icon = pygame.Rect(card.x + 12, card.y + 20, 92, 92)
        game.ui.draw_item_icon(surface, icon, item, True)
        game.ui.fitted_text(surface, item.display_name, pygame.Rect(card.x + 112, card.y + 21, 148, 27), COLORS["text"], "small")
        game.ui.fitted_text(surface, item.category_label.upper(), pygame.Rect(card.x + 112, card.y + 53, 148, 20), COLORS["muted"], "tiny")
        game.ui.wrapped(surface, item.stat_text(), pygame.Rect(card.x + 112, card.y + 79, 148, 42), color, "tiny", 3, 2)
        game.ui.wrapped(surface, item.description, pygame.Rect(card.x + 16, card.y + 132, card.width - 32, 57), COLORS["muted"], "tiny", 3, 3)
    pygame.image.save(surface, output_dir / "new_relic_catalog_v11.png")


def render_fusion_catalog(game, output_dir):
    examples = (
        ("rusted_falchion", "ghost_salt"),
        ("splintered_guard", "minor_tonic"),
        ("copper_loop", "bone_cleaver"),
        ("minor_tonic", "ember_essence"),
        ("rime_essence", "iron_scrap"),
        ("bone_shard", "fortune_vial"),
    )
    surface = pygame.Surface((1140, 600))
    surface.fill((9, 13, 18))
    game.ui.text(surface, "BONEBOUND  •  UNIVERSAL FUSION RESULTS", (40, 28), COLORS["gold"], "medium")
    for index, (left_id, right_id) in enumerate(examples):
        row, col = divmod(index, 3)
        card = pygame.Rect(35 + col * 370, 82 + row * 244, 350, 218)
        left = create_item(left_id, random.Random(4000 + index * 2), 12)
        right = create_item(right_id, random.Random(4001 + index * 2), 12)
        result = Mixer.visual_result(left, right)
        game.ui.ornamented_panel(surface, card, (16, 22, 30), game.ui.item_color(result), 10, 2)
        game.ui.draw_item_icon(surface, pygame.Rect(card.x + 20, card.y + 22, 72, 72), left)
        game.ui.text(surface, "+", (card.x + 111, card.y + 58), COLORS["muted"], "medium", "center")
        game.ui.draw_item_icon(surface, pygame.Rect(card.x + 130, card.y + 22, 72, 72), right)
        game.ui.text(surface, "=>", (card.x + 220, card.y + 58), COLORS["gold"], "medium", "center")
        game.ui.draw_item_icon(surface, pygame.Rect(card.x + 246, card.y + 11, 88, 88), result, True)
        game.ui.fitted_text(surface, result.display_name, pygame.Rect(card.x + 18, card.y + 119, card.width - 36, 28), COLORS["text"], "medium")
        game.ui.wrapped(surface, result.description, pygame.Rect(card.x + 18, card.y + 156, card.width - 36, 49), game.ui.item_color(result), "tiny", 3, 2)
    pygame.image.save(surface, output_dir / "universal_fusion_catalog_v4.png")


def render_entrance_animation(game, output_dir):
    game.begin_battle(STAGES[0])
    game.transition_target = None
    game.screen = Screen.BATTLE
    frames = []
    duration = game.battle.APPROACH_DURATION
    for index in range(12):
        progress = index / 11
        game.battle.phase = "approach"
        game.battle.timer = duration * (1 - progress)
        game.battle.hero_anim = "walk"
        game.battle.enemy_anim = "run"
        game.battle.anim_clock = progress * duration
        game.time = progress * duration
        game.draw_battle()
        frame = game.screen_surface.subsurface((0, 0, 1200, 666)).copy()
        preview = pygame.transform.smoothscale(frame, (900, 500))
        frames.append(pygame_to_pil(preview))
    frames[0].save(output_dir / "stage_entrance_animation_v4.gif", save_all=True, append_images=frames[1:], duration=105, loop=0, optimize=False)


def render_drag_preview(game, output_dir):
    weapon = create_item("voidglass_sabre", random.Random(700), 22)
    game.hero.add_item(weapon)
    game.screen = Screen.INVENTORY
    game.transition_target = None
    game.mouse = (0, 0)
    game.draw()
    source = next(zone for zone in game.item_drag_zones if zone["role"] == "inventory" and zone.get("item") and zone["item"].uid == weapon.uid)
    target = next(zone for zone in game.item_drag_zones if zone["role"] == "equipment" and zone.get("slot") == "weapon")
    game.drag_candidate = {"uid": weapon.uid, "role": "inventory", "index": source["index"], "slot": None}
    game.drag_active = True
    game.mouse = target["rect"].center
    game.draw()
    pygame.image.save(game.screen_surface, output_dir / "drag_drop_preview_v4.png")


def render_trinket_catalog(game, output_dir):
    surface = pygame.Surface((1140, 330))
    surface.fill((9, 13, 18))
    game.ui.text(surface, "BONEBOUND  •  SPECIAL TRINKETS", (40, 27), COLORS["gold"], "medium")
    for index, template_id in enumerate(SPECIAL_TRINKETS):
        card = pygame.Rect(25 + index * 222, 78, 202, 225)
        item = create_item(template_id, random.Random(6000 + index), max(1, ITEM_TEMPLATES[template_id]["tier"] * 5))
        game.ui.ornamented_panel(surface, card, (16, 22, 30), game.ui.item_color(item), 10, 2)
        game.ui.draw_item_icon(surface, pygame.Rect(card.centerx - 47, card.y + 14, 94, 94), item, True)
        game.ui.fitted_text(surface, item.display_name, pygame.Rect(card.x + 12, card.y + 119, card.width - 24, 26), COLORS["text"], "small", "center")
        game.ui.text(surface, item.category_label.upper(), (card.centerx, card.y + 151), game.ui.item_color(item), "tiny", "center")
        game.ui.wrapped(surface, game.ui.item_power_text(item), pygame.Rect(card.x + 12, card.y + 174, card.width - 24, 40), COLORS["muted"], "tiny", 2, 2)
    pygame.image.save(surface, output_dir / "trinket_catalog_v5.png")


def render_shield_catalog(game, output_dir):
    shield_ids = [template_id for template_id, template in ITEM_TEMPLATES.items() if template["kind"] == ItemKind.SHIELD]
    surface = pygame.Surface((1140, 520))
    surface.fill((9, 13, 18))
    game.ui.text(surface, "BONEBOUND  •  SHIELD DEFENSE", (40, 27), COLORS["gold"], "medium")
    for index, template_id in enumerate(shield_ids):
        row, col = divmod(index, 5)
        card = pygame.Rect(25 + col * 222, 75 + row * 214, 202, 196)
        item = create_item(template_id, random.Random(6200 + index), max(1, ITEM_TEMPLATES[template_id]["tier"] * 5))
        game.ui.ornamented_panel(surface, card, (16, 22, 30), game.ui.item_color(item), 10, 2)
        game.ui.draw_item_icon(surface, pygame.Rect(card.centerx - 41, card.y + 9, 82, 82), item, True)
        game.ui.fitted_text(surface, item.display_name, pygame.Rect(card.x + 10, card.y + 101, card.width - 20, 25), COLORS["text"], "small", "center")
        game.ui.text(surface, f"+{item.stats['defense']} DEF", (card.centerx, card.y + 136), (86, 184, 236), "tiny", "center")
        game.ui.fitted_text(surface, game.ui.item_power_text(item), pygame.Rect(card.x + 10, card.y + 158, card.width - 20, 22), COLORS["muted"], "tiny", "center")
    pygame.image.save(surface, output_dir / "shield_defense_catalog_v8.png")


def render_rat_and_shield(game, output_dir):
    game.new_game()
    game.transition_target = None
    game.begin_battle(STAGES[0])
    game.transition_target = None
    game.screen = Screen.BATTLE
    frames = []
    for index in range(8):
        elapsed = index / 12
        game.time = elapsed
        game.screen_surface.fill((9, 13, 18))
        pygame.draw.line(game.screen_surface, (92, 72, 51), (35, 405), (505, 405), 4)
        game.draw_enemy(pygame.Vector2(315, 404), game.battle.enemy, "run", elapsed)
        frame = game.screen_surface.subsurface((0, 0, 540, 450)).copy()
        frames.append(pygame_to_pil(frame))
    frames[0].save(output_dir / "dust_rat_animation_v5.gif", save_all=True, append_images=frames[1:], duration=95, loop=0, optimize=False)
    contact = Image.new("RGB", (1080, 900), (9, 13, 18))
    for index, frame in enumerate(frames):
        contact.paste(frame.crop((0, 105, 540, 330)), ((index % 2) * 540, (index // 2) * 225))
    contact.save(output_dir / "dust_rat_animation_v5_contact.png")

    game.battle.phase = "player_windup"
    game.battle.timer = .38
    game.battle.hero_anim = "idle"
    game.battle.enemy_anim = "idle"
    game.battle.anim_clock = .35
    game.time = .35
    game.draw_battle()
    pygame.image.save(game.screen_surface, output_dir / "shieldless_start_v8.png")

    shield = create_item("patched_buckler", random.Random(6400), 1)
    assert game.hero.add_item(shield)
    assert game.hero.equip(shield.uid)[0]
    game.begin_battle(STAGES[0])
    game.transition_target = None
    game.screen = Screen.BATTLE
    game.battle.phase = "player_windup"
    game.battle.timer = .38
    game.battle.hero_anim = "idle"
    game.battle.enemy_anim = "idle"
    game.battle.anim_clock = .35
    game.draw_battle()
    pygame.image.save(game.screen_surface, output_dir / "shield_equipped_v8.png")
    game.battle.drain_events()
    game.battle.rng = random.Random(77)
    game.battle._enemy_strike()
    game.process_battle_events()
    # Force the short shield ward window for a deterministic visual review;
    # combat probability itself is covered separately by simulation checks.
    game.hero_block_flash = .34
    game.draw_battle()
    pygame.image.save(game.screen_surface, output_dir / "shield_defense_impact_v8.png")


def render_final_ui(game, output_dir):
    game.new_game()
    game.transition_target = None
    game.mouse = (0, 0)
    game.clicked = False
    game.screen = Screen.INVENTORY
    game.draw()
    pygame.image.save(game.screen_surface, output_dir / "final_inventory_shieldless_v8.png")
    game.screen = Screen.HUB
    game.selected_stage = 1
    game.draw()
    pygame.image.save(game.screen_surface, output_dir / "final_hub_stage1_v6.png")


def render_enemy_fit_catalog(game, output_dir):
    game.new_game()
    game.transition_target = None
    game.begin_battle(STAGES[0])
    game.transition_target = None
    game.screen = Screen.BATTLE
    game.battle.phase = "player_windup"
    timings = {"idle": .25, "run": .18, "attack": .24, "defeat": .32}
    for state, clock in timings.items():
        atlas = pygame.Surface((1200, 950))
        atlas.fill((7, 11, 18))
        for index, (enemy_id, enemy) in enumerate(ENEMIES.items()):
            row, col = divmod(index, 5)
            cell = pygame.Rect(col * 240, row * 190, 240, 190)
            game.screen_surface.fill((7, 11, 18))
            game.time = clock
            game.actor_anim_key["enemy"] = (id(game.battle), state)
            game.actor_anim_started["enemy"] = 0.0
            pygame.draw.line(game.screen_surface, (85, 70, 58), (495, 590), (1165, 590), 3)
            game.draw_enemy(pygame.Vector2(830, 580), enemy, state, clock)
            crop = game.screen_surface.subsurface((490, 190, 680, 430)).copy()
            atlas.blit(pygame.transform.smoothscale(crop, (220, 150)), (cell.x + 10, cell.y + 27))
            game.ui.fitted_text(atlas, enemy.name, pygame.Rect(cell.x + 8, cell.y + 2, cell.width - 16, 22), COLORS["text"], "tiny", "center")
            pygame.draw.rect(atlas, (48, 62, 78), cell, 1)
        pygame.image.save(atlas, output_dir / f"enemy_fit_{state}_v7.png")


def render_boss_scale_catalog(game, output_dir):
    atlas = pygame.Surface((1200, 380))
    atlas.fill((7, 11, 18))
    game.ui.text(atlas, "CAMPAIGN BOSSES • SECOND PHASE SCALE", (28, 18), COLORS["gold"], "medium")
    for index, stage in enumerate(STAGES[4::5]):
        game.new_game()
        game.begin_battle(stage)
        game.transition_target = None
        game.battle.enemy_index = len(stage.enemies) - 2
        game.battle._spawn_next_enemy()
        game.battle.phase = "player_windup"
        game.battle.enemy.hp = game.battle.enemy.max_hp // 2
        game.battle._trigger_boss_phase()
        game.screen_surface.fill((7, 11, 18))
        pygame.draw.line(game.screen_surface, (85, 70, 58), (500, 590), (1160, 590), 3)
        game.time = .32
        game.draw_enemy(pygame.Vector2(830, 580), game.battle.enemy, "ready", .32)
        crop = game.screen_surface.subsurface((500, 190, 660, 420)).copy()
        card = pygame.Rect(10 + index * 238, 62, 228, 300)
        atlas.blit(pygame.transform.smoothscale(crop, (228, 225)), card.topleft)
        pygame.draw.rect(atlas, game.ui.item_color(create_item(stage.first_clear_item, random.Random(9000 + index), stage.index)), card, 2)
        game.ui.fitted_text(atlas, game.battle.enemy.name, pygame.Rect(card.x + 8, card.y + 232, card.width - 16, 23), COLORS["text"], "tiny", "center")
        game.ui.text(atlas, f"{game.battle.enemy.max_hp} HP  •  PHASE II", (card.centerx, card.y + 272), COLORS["gold"], "tiny", "center")
    pygame.image.save(atlas, output_dir / "boss_scale_v11.png")


def main():
    output_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "work" / "qa_release"
    output_dir.mkdir(parents=True, exist_ok=True)
    pygame.init()
    game = Game(True)
    test_drag_drop(game)
    test_potions()
    test_universal_fusions()
    test_shields_and_trinkets()
    test_balance_save_migration()
    test_launch_balance()
    test_campaign_scale_and_boss_phase()
    test_wave_counter_bounds()
    test_content_expansion()
    test_rat_animation(game)
    test_enemy_canvases(game)
    test_hero_cohesion(game)
    test_item_alpha()
    render_animation(game, output_dir, "attack", 8, 82)
    render_animation(game, output_dir, "critical", 10, 70)
    render_hero_state_catalog(game, output_dir)
    render_equipment_hold_catalog(game, output_dir)
    render_shield_brace_animation(game, output_dir)
    render_potion_catalog(game, output_dir)
    render_new_gear_catalog(game, output_dir)
    render_fusion_catalog(game, output_dir)
    render_entrance_animation(game, output_dir)
    render_drag_preview(game, output_dir)
    render_trinket_catalog(game, output_dir)
    render_shield_catalog(game, output_dir)
    render_rat_and_shield(game, output_dir)
    render_final_ui(game, output_dir)
    render_enemy_fit_catalog(game, output_dir)
    render_boss_scale_catalog(game, output_dir)
    pygame.quit()
    print(f"qa_release_ok potions={len(NEW_POTIONS)} recipes={len(NEW_RECIPES)} trinkets={len(SPECIAL_TRINKETS)} universal_pairs={len(ITEM_TEMPLATES) ** 2} output={output_dir}")


if __name__ == "__main__":
    main()
