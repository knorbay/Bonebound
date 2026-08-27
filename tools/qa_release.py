import os
import random
import sys
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
from systems import Mixer
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


def test_shields_and_trinkets():
    shield_ids = [template_id for template_id, template in ITEM_TEMPLATES.items() if template["kind"] == ItemKind.SHIELD]
    assert shield_ids
    for template_id in shield_ids:
        shield = create_item(template_id, random.Random(5100), 15)
        assert shield.stats.get("defense", 0) >= 5, template_id
        assert shield.effects.get("guard_points", 0) > 0, template_id

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
    assert battle.hero_guard_max == 0
    shield = create_item("patched_buckler", random.Random(5300), 1)
    assert hero.add_item(shield)
    assert hero.equip(shield.uid)[0]
    battle = CombatEngine(hero, STAGES[0], random.Random(77))
    assert battle.hero_guard_max == 3
    battle.drain_events()
    battle.enemy.attack = 20
    battle._enemy_strike()
    events = battle.drain_events()
    assert battle.hero_guard < battle.hero_guard_max
    assert any(event.event_type == "shield_guard" for event in events)


def test_rat_animation(game):
    for state in ("idle", "run", "attack", "defeat"):
        frames = game.sprites.enemy_frames.get(("dust_rat", state), [])
        assert len(frames) == 6, (state, len(frames))
        assert all(frame.get_size() == (52, 36) for frame in frames)


def test_enemy_canvases(game):
    from content import ENEMIES

    for enemy_id in ENEMIES:
        sizes = set()
        for state in ("idle", "run", "attack", "defeat"):
            frames = game.sprites.enemy_frames.get((enemy_id, state), [])
            assert frames, (enemy_id, state)
            sizes.update(frame.get_size() for frame in frames)
        assert len(sizes) == 1, (enemy_id, sizes)


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
    game.ui.text(surface, "BONEBOUND  •  SHIELD GUARD", (40, 27), COLORS["gold"], "medium")
    for index, template_id in enumerate(shield_ids):
        row, col = divmod(index, 5)
        card = pygame.Rect(25 + col * 222, 75 + row * 214, 202, 196)
        item = create_item(template_id, random.Random(6200 + index), max(1, ITEM_TEMPLATES[template_id]["tier"] * 5))
        game.ui.ornamented_panel(surface, card, (16, 22, 30), game.ui.item_color(item), 10, 2)
        game.ui.draw_item_icon(surface, pygame.Rect(card.centerx - 41, card.y + 9, 82, 82), item, True)
        game.ui.fitted_text(surface, item.display_name, pygame.Rect(card.x + 10, card.y + 101, card.width - 20, 25), COLORS["text"], "small", "center")
        game.ui.text(surface, f"+{item.stats['defense']} DEF  •  GUARD {item.effects['guard_points']}", (card.centerx, card.y + 136), (86, 184, 236), "tiny", "center")
        game.ui.fitted_text(surface, game.ui.item_power_text(item), pygame.Rect(card.x + 10, card.y + 158, card.width - 20, 22), COLORS["muted"], "tiny", "center")
    pygame.image.save(surface, output_dir / "shield_guard_catalog_v5.png")


def render_rat_and_guard(game, output_dir):
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
    pygame.image.save(game.screen_surface, output_dir / "unguarded_start_v6.png")

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
    pygame.image.save(game.screen_surface, output_dir / "shield_equipped_v6.png")
    game.battle.drain_events()
    game.battle.rng = random.Random(77)
    game.battle._enemy_strike()
    game.process_battle_events()
    game.draw_battle()
    pygame.image.save(game.screen_surface, output_dir / "shield_guard_impact_v6.png")


def render_final_ui(game, output_dir):
    game.new_game()
    game.transition_target = None
    game.mouse = (0, 0)
    game.clicked = False
    game.screen = Screen.INVENTORY
    game.draw()
    pygame.image.save(game.screen_surface, output_dir / "final_inventory_unguarded_v6.png")
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


def main():
    output_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "work" / "qa_release"
    output_dir.mkdir(parents=True, exist_ok=True)
    pygame.init()
    game = Game(True)
    test_drag_drop(game)
    test_potions()
    test_universal_fusions()
    test_shields_and_trinkets()
    test_rat_animation(game)
    test_enemy_canvases(game)
    render_animation(game, output_dir, "attack", 8, 82)
    render_animation(game, output_dir, "critical", 10, 70)
    render_potion_catalog(game, output_dir)
    render_fusion_catalog(game, output_dir)
    render_entrance_animation(game, output_dir)
    render_drag_preview(game, output_dir)
    render_trinket_catalog(game, output_dir)
    render_shield_catalog(game, output_dir)
    render_rat_and_guard(game, output_dir)
    render_final_ui(game, output_dir)
    render_enemy_fit_catalog(game, output_dir)
    pygame.quit()
    print(f"qa_release_ok potions={len(NEW_POTIONS)} recipes={len(NEW_RECIPES)} trinkets={len(SPECIAL_TRINKETS)} universal_pairs={len(ITEM_TEMPLATES) ** 2} output={output_dir}")


if __name__ == "__main__":
    main()
