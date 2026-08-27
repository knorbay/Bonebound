import math
import os
import random
import sys
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import pygame

from audio import Audio
from combat import BattleOutcome, CombatEngine
from content import ENEMIES, ITEM_TEMPLATES, RECIPES, STAGES, create_endless_stage, starter_loadout
from models import Element, Hero, ItemKind
from sprites import CharacterSprites
from systems import LootSystem, Mixer, SaveError, SaveManager
from ui import COLORS, ELEMENT_COLORS, ITEM_COLORS, UI


WIDTH, HEIGHT = 1200, 960
FPS = 60
VERSION = "0.1.0"


class Screen(Enum):
    MAIN_MENU = "main_menu"
    HUB = "hub"
    INVENTORY = "inventory"
    MIXER = "mixer"
    CHARACTER = "character"
    RECIPES = "recipes"
    BATTLE = "battle"
    LOOT = "loot"
    EPILOGUE = "epilogue"


@dataclass
class FloatNotice:
    text: str
    x: float
    y: float
    color: tuple
    age: float = 0.0
    duration: float = 1.25

    def update(self, dt):
        self.age += dt
        self.y -= 35 * dt
        return self.age < self.duration


@dataclass
class FxBurst:
    x: float
    y: float
    color: tuple
    kind: str = "hit"
    age: float = 0.0
    duration: float = .52

    def update(self, dt):
        self.age += dt
        return self.age < self.duration

    def draw(self, surface):
        progress = min(1.0, self.age / self.duration)
        alpha = max(0, round(255 * (1 - progress)))
        layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        radius = 18 + progress * 58
        pygame.draw.circle(layer, (*self.color, alpha // 2), (round(self.x), round(self.y)), round(radius), max(1, round(5 * (1 - progress))))
        if self.kind in {"hero_hit", "critical"}:
            slash_width = max(1, round((10 if self.kind == "critical" else 6) * (1 - progress)))
            slash_rect = pygame.Rect(round(self.x - 88 - progress * 18), round(self.y - 74), round(176 + progress * 36), 148)
            pygame.draw.arc(layer, (*self.color, alpha), slash_rect, -.88, .74, slash_width)
            pygame.draw.arc(layer, (255, 250, 226, alpha), slash_rect.inflate(-13, -13), -.88, .74, max(1, slash_width // 3))
        count = 14 if self.kind == "critical" else 9
        for index in range(count):
            angle = index * math.tau / count + progress * .35
            distance = 12 + progress * (82 if self.kind == "critical" else 55)
            px = self.x + math.cos(angle) * distance
            py = self.y + math.sin(angle) * distance * .65
            size = max(1, round((5 if self.kind == "critical" else 4) * (1 - progress)))
            pygame.draw.circle(layer, (*self.color, alpha), (round(px), round(py)), size)
        surface.blit(layer, (0, 0))


class Game:
    def __init__(self, simulate=False, save_path=None):
        if simulate:
            os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
            os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        pygame.init()
        self.simulate = simulate
        flags = pygame.HIDDEN if simulate else 0
        self.screen_surface = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        pygame.display.set_caption(f"BONEBOUND • Descent v{VERSION}")
        self.clock = pygame.time.Clock()
        self.audio = Audio(not simulate)
        self.ui = UI(self.audio)
        self.sprites = CharacterSprites()
        if simulate and save_path is None:
            save_path = Path(tempfile.gettempdir()) / f"bonebound_sim_{os.getpid()}.json"
        self.save_manager = SaveManager(save_path)
        self.screen = Screen.MAIN_MENU
        self.return_screen = Screen.HUB
        self.hero = None
        self.selected_stage = 1
        self.selected_uid = None
        self.selected_equipment_slot = None
        self.mixer_left = None
        self.mixer_right = None
        self.trash_confirm_uid = None
        self.battle = None
        self.battle_processed = False
        self.battle_finish_timer = 0.0
        self.float_notices = []
        self.fx_bursts = []
        self.mouse = (0, 0)
        self.clicked = False
        self.running = True
        self.confirm_new = False
        self.toast_text = ""
        self.toast_age = 99.0
        self.craft_result = None
        self.craft_reveal_age = 99.0
        self.transition_target = None
        self.transition_age = 0.0
        self.transition_duration = .64
        self.transition_swapped = False
        self.transition_label = "DESCENDING"
        self.item_drag_zones = []
        self.drag_candidate = None
        self.drag_active = False
        self.drag_start = (0, 0)
        self.time = 0.0
        self.shake = 0.0
        self.impact_pause = 0.0
        self.hero_hit_flash = 0.0
        self.hero_block_flash = 0.0
        self.hero_critical_flash = 0.0
        self.enemy_hit_flash = 0.0
        self.actor_anim_key = {"hero": None, "enemy": None}
        self.actor_anim_started = {"hero": 0.0, "enemy": 0.0}

    def toast(self, text):
        self.toast_text = text
        self.toast_age = 0.0

    def begin_transition(self, target, label="DESCENDING"):
        self.drag_candidate = None
        self.drag_active = False
        self.transition_target = target
        self.transition_age = 0.0
        self.transition_swapped = False
        self.transition_label = label

    def register_item_drag_zone(self, rect, role, item=None, **payload):
        self.item_drag_zones.append({"rect": pygame.Rect(rect), "role": role, "item": item, **payload})

    def dragged_item(self):
        if not self.hero or not self.drag_candidate:
            return None
        uid = self.drag_candidate.get("uid")
        item = self.hero.item_by_uid(uid)
        if item:
            return item
        return next((value for value in self.hero.equipment.values() if value and value.uid == uid), None)

    def valid_item_drop(self, zone, item):
        if not zone or not item:
            return False
        role = zone["role"]
        source_role = self.drag_candidate.get("role") if self.drag_candidate else None
        if role == "equipment":
            slot = zone["slot"]
            if item.kind == ItemKind.RING:
                return slot in {"ring1", "ring2"}
            return item.slot == slot
        if role == "inventory":
            return source_role == "inventory" or len(self.hero.inventory) < self.hero.inventory_capacity
        if role in {"mixer_base", "mixer_catalyst"}:
            return source_role == "inventory" or len(self.hero.inventory) < self.hero.inventory_capacity
        if role == "boost":
            return source_role == "inventory" and item.kind == ItemKind.POTION
        return False

    def finish_item_drag(self, position):
        item = self.dragged_item()
        if not item:
            return
        target = next((zone for zone in reversed(self.item_drag_zones) if zone["rect"].collidepoint(position) and self.valid_item_drop(zone, item)), None)
        if not target:
            self.toast("No valid slot under the item.")
            return
        source_role = self.drag_candidate.get("role")
        source_slot = self.drag_candidate.get("slot")
        role = target["role"]
        ok, message = True, ""
        if role == "equipment":
            target_slot = target["slot"]
            if source_role == "equipment":
                if source_slot == target_slot:
                    return
                other = self.hero.equipment.get(target_slot)
                self.hero.equipment[target_slot], self.hero.equipment[source_slot] = item, other
                message = f"Moved {item.display_name} to {target_slot.upper()}."
            else:
                ok, message = self.hero.equip(item.uid, target_slot)
            if ok:
                self.audio.play("equip")
        elif role == "inventory":
            if source_role == "equipment":
                ok, message = self.hero.unequip(source_slot)
                item = self.hero.item_by_uid(item.uid)
            if ok and item in self.hero.inventory:
                self.hero.inventory.remove(item)
                index = min(int(target.get("index", len(self.hero.inventory))), len(self.hero.inventory))
                self.hero.inventory.insert(index, item)
                message = f"Moved {item.display_name}."
        elif role in {"mixer_base", "mixer_catalyst"}:
            if source_role == "equipment":
                ok, message = self.hero.unequip(source_slot)
                item = self.hero.item_by_uid(item.uid)
            if ok:
                if role == "mixer_base":
                    self.mixer_left = item.uid
                    if self.mixer_right == item.uid and item.stack < 2:
                        self.mixer_right = None
                    message = f"{item.display_name} set as mixer base."
                elif item.uid != self.mixer_left or item.stack >= 2:
                    self.mixer_right = item.uid
                    message = f"{item.display_name} set as catalyst."
                else:
                    ok, message = False, "That stack needs two items to fill both mixer sides."
        elif role == "boost":
            ok, message = self.hero.set_boost(item.uid)
            if ok:
                self.mixer_left = None if self.mixer_left == item.uid else self.mixer_left
                self.mixer_right = None if self.mixer_right == item.uid else self.mixer_right
                self.audio.play("potion")
        if ok:
            self.selected_uid = item.uid if item else None
            self.save()
        self.toast(message)

    def draw_item_drag_overlay(self):
        if not self.drag_active:
            return
        item = self.dragged_item()
        if not item:
            return
        for zone in self.item_drag_zones:
            if not self.valid_item_drop(zone, item):
                continue
            hovered = zone["rect"].collidepoint(self.mouse)
            if hovered or zone["role"] in {"equipment", "mixer_base", "mixer_catalyst", "boost"}:
                color = (92, 222, 151) if hovered else self.ui.blend(self.ui.item_color(item), COLORS["border"], .48)
                pygame.draw.rect(self.screen_surface, color, zone["rect"].inflate(6, 6), 3 if hovered else 1, border_radius=10)
        ghost = pygame.Rect(0, 0, 76, 76)
        ghost.center = (self.mouse[0] + 18, self.mouse[1] + 15)
        shade = pygame.Surface(ghost.size, pygame.SRCALPHA)
        pygame.draw.rect(shade, (8, 11, 16, 220), shade.get_rect(), border_radius=12)
        pygame.draw.rect(shade, (*self.ui.item_color(item), 230), shade.get_rect(), 2, border_radius=12)
        self.screen_surface.blit(shade, ghost)
        self.ui.draw_item_icon(self.screen_surface, ghost.inflate(-8, -8), item, True)

    def draw_transition(self):
        if self.transition_target is None:
            return
        progress = min(1.0, self.transition_age / self.transition_duration)
        cover = math.sin(progress * math.pi) ** .72
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((4, 6, 10, round(252 * cover)))
        self.screen_surface.blit(veil, (0, 0))
        if cover < .22:
            return
        panel = pygame.Rect(0, 0, 430, 128)
        panel.center = (WIDTH // 2, HEIGHT // 2)
        alpha = round(235 * min(1.0, cover * 1.35))
        layer = pygame.Surface(panel.size, pygame.SRCALPHA)
        pygame.draw.rect(layer, (12, 15, 20, alpha), layer.get_rect(), border_radius=13)
        pygame.draw.rect(layer, (*COLORS["gold"], alpha), layer.get_rect(), 2, border_radius=13)
        self.screen_surface.blit(layer, panel)
        title, _, detail = self.transition_label.partition("•")
        self.ui.fitted_text(self.screen_surface, title.strip(), pygame.Rect(panel.x + 20, panel.y + 17, panel.width - 40, 35), COLORS["text"], "medium", "center")
        if detail:
            self.ui.fitted_text(self.screen_surface, detail.strip(), pygame.Rect(panel.x + 24, panel.y + 51, panel.width - 48, 25), COLORS["muted"], "small", "center")
        active = int(progress * 12) % 3
        for index in range(3):
            x = panel.centerx - 34 + index * 34
            color = COLORS["gold"] if index == active else COLORS["border"]
            pygame.draw.polygon(self.screen_surface, color, [(x, panel.y + 99), (x + 7, panel.y + 92), (x + 14, panel.y + 99), (x + 7, panel.y + 106)])
            pygame.draw.circle(self.screen_surface, color, (x + 2, panel.y + 99), 4)
            pygame.draw.circle(self.screen_surface, color, (x + 12, panel.y + 99), 4)

    def reveal_craft(self, item):
        self.craft_result = item
        self.craft_reveal_age = 0.0

    def draw_craft_reveal(self):
        if not self.craft_result or self.craft_reveal_age >= 2.35:
            return
        age = self.craft_reveal_age
        fade = min(1.0, age / .16, (2.35 - age) / .42)
        pop = .82 + .18 * min(1.0, age / .22)
        width, height = round(440 * pop), round(164 * pop)
        card = pygame.Rect(0, 0, width, height)
        card.center = (WIDTH // 2, 194)
        layer = pygame.Surface(card.size, pygame.SRCALPHA)
        alpha = max(0, min(255, round(245 * fade)))
        pygame.draw.rect(layer, (10, 12, 18, alpha), layer.get_rect(), border_radius=14)
        color = self.ui.item_color(self.craft_result)
        pygame.draw.rect(layer, (*color, alpha), layer.get_rect(), 3, border_radius=14)
        self.screen_surface.blit(layer, card)
        icon_side = max(56, round(108 * pop))
        icon_rect = pygame.Rect(card.x + 19, card.centery - icon_side // 2, icon_side, icon_side)
        self.ui.draw_item_icon(self.screen_surface, icon_rect, self.craft_result, True)
        text_x = icon_rect.right + 18
        self.ui.text(self.screen_surface, "CRAFT RESULT", (text_x, card.y + 27), COLORS["gold"], "tiny")
        self.ui.fitted_text(self.screen_surface, self.craft_result.display_name, pygame.Rect(text_x, card.y + 50, card.right - text_x - 18, 33), COLORS["text"], "medium")
        self.ui.fitted_text(self.screen_surface, self.craft_result.stat_text(), pygame.Rect(text_x, card.y + 91, card.right - text_x - 18, 25), color, "small")
        self.ui.text(self.screen_surface, "READY FOR THE DESCENT", (text_x, card.y + 124), COLORS["muted"], "tiny")

    def animation_elapsed(self, actor, state, fallback_clock):
        if self.screen != Screen.BATTLE or not self.battle:
            return fallback_clock
        key = (id(self.battle), state)
        if self.actor_anim_key[actor] != key:
            self.actor_anim_key[actor] = key
            self.actor_anim_started[actor] = self.time
        return max(0.0, self.time - self.actor_anim_started[actor])

    def save(self):
        if not self.hero:
            return
        try:
            self.save_manager.save(self.hero, self.selected_stage)
        except OSError:
            self.toast("Save failed. Check folder permissions.")

    def new_game(self):
        self.hero = Hero()
        loadout = starter_loadout()
        for slot in self.hero.equipment:
            self.hero.equipment[slot] = loadout.get("equipment", {}).get(slot)
        for item in loadout.get("inventory", []):
            self.hero.add_item(item)
        self.selected_stage = 1
        self.selected_uid = None
        self.selected_equipment_slot = None
        self.mixer_left = None
        self.mixer_right = None
        self.trash_confirm_uid = None
        self.battle = None
        self.confirm_new = False
        self.begin_transition(Screen.HUB, "OPENING THE DESCENT")
        self.save()
        self.toast("A new descent begins. Progress is saved automatically.")

    def load_game(self):
        try:
            self.hero, self.selected_stage = self.save_manager.load()
        except SaveError as exc:
            self.toast(str(exc))
            return
        if self.hero.pending_loot and len(self.hero.pending_routes) != len(self.hero.pending_loot):
            self.hero.pending_routes = []
            loot_system = LootSystem()
            for item in self.hero.pending_loot:
                delivered = type(item).from_dict(item.to_dict())
                if self.hero.add_item(delivered):
                    self.hero.pending_routes.append("BACKPACK")
                else:
                    value = loot_system.salvage_value(delivered)
                    self.hero.bone_dust += value
                    self.hero.pending_routes.append(f"AUTO-SALVAGED  +{value} DUST")
            self.save()
        self.selected_uid = None
        self.selected_equipment_slot = None
        self.mixer_left = None
        self.mixer_right = None
        self.trash_confirm_uid = None
        self.battle = None
        if self.hero.pending_loot:
            target = Screen.LOOT
        elif self.hero.campaign_complete and not self.hero.ending_seen:
            target = Screen.EPILOGUE
        else:
            target = Screen.HUB
        self.begin_transition(target, "RETURNING BELOW")
        self.toast("Save loaded.")

    def start_battle(self):
        if not self.hero:
            return
        stage = STAGES[self.selected_stage - 1]
        if stage.index > self.hero.unlocked_stage:
            self.toast("That dungeon is still locked.")
            return
        self.begin_battle(stage)

    def start_endless(self, depth=None):
        if not self.hero or not self.hero.campaign_complete:
            self.toast("The Endless Descent opens after the Hollow Crown falls.")
            return
        depth = max(1, int(depth or self.hero.endless_depth + 1))
        seed = self.hero.campaign_seed * 3000017 + depth * 7919
        self.begin_battle(create_endless_stage(depth, seed))

    def begin_battle(self, stage):
        seed = self.hero.campaign_seed * 1000003 + stage.index * 9176 + self.hero.battle_counter * 7919
        self.hero.battle_counter += 1
        self.battle = CombatEngine(self.hero, stage, random.Random(seed))
        self.battle_processed = False
        self.battle_finish_timer = 0
        self.float_notices.clear()
        self.fx_bursts.clear()
        self.impact_pause = 0.0
        self.hero_hit_flash = 0.0
        self.hero_block_flash = 0.0
        self.hero_critical_flash = 0.0
        self.enemy_hit_flash = 0.0
        self.actor_anim_key = {"hero": None, "enemy": None}
        self.actor_anim_started = {"hero": self.time, "enemy": self.time}
        self.mixer_left = None
        self.mixer_right = None
        self.begin_transition(Screen.BATTLE, f"DESCENDING • {stage.name.upper()}")
        self.audio.play("open")
        self.save()

    def finish_victory(self):
        stage = self.battle.stage
        endless = bool(stage.endless_depth)
        first_clear = not endless and stage.index not in self.hero.cleared_stages
        self.hero.total_wins += 1
        if endless:
            self.hero.endless_depth = max(self.hero.endless_depth, stage.endless_depth)
            self.hero.best_endless = max(self.hero.best_endless, stage.endless_depth)
        else:
            self.hero.stage_clear_counts[stage.index] = self.hero.stage_clear_counts.get(stage.index, 0) + 1
            self.hero.cleared_stages.add(stage.index)
            if stage.index == self.hero.unlocked_stage and stage.index < len(STAGES):
                self.hero.unlocked_stage += 1
            best = self.hero.best_turns.get(stage.index)
            if best is None or self.battle.turns < best:
                self.hero.best_turns[stage.index] = self.battle.turns
            if stage.index == len(STAGES):
                self.hero.campaign_complete = True
        loot_seed = self.hero.campaign_seed * 2000003 + stage.index * 1237 + self.hero.loot_counter * 104729
        loot_rng = random.Random(loot_seed)
        rewards = LootSystem(loot_rng).rewards(stage, first_clear)
        self.hero.pending_loot = [type(item).from_dict(item.to_dict()) for item in rewards]
        self.hero.pending_routes = []
        loot_system = LootSystem()
        for item in rewards:
            if self.hero.add_item(item):
                self.hero.pending_routes.append("BACKPACK")
            else:
                value = loot_system.salvage_value(item)
                self.hero.bone_dust += value
                self.hero.pending_routes.append(f"AUTO-SALVAGED  +{value} DUST")
        self.hero.pending_stage = -stage.endless_depth if endless else stage.index
        self.hero.loot_counter += 1
        self.battle_processed = True
        self.battle_finish_timer = 1.25
        self.save()

    def process_battle_events(self):
        for event in self.battle.drain_events():
            if event.event_type in {"hero_hit", "enemy_hit", "proc", "counter", "thorns"} and (event.amount or event.blocked):
                self.audio.play("block" if event.blocked else "critical" if event.critical else "hit")
            elif event.event_type == "boost":
                self.audio.play("potion")
            elif event.event_type in {"victory", "enemy_down"}:
                self.audio.play("confirm")
            elif event.event_type == "defeat":
                self.audio.play("error")
            if event.event_type == "enemy_hit" and event.blocked:
                self.hero_block_flash = .34
                self.impact_pause = max(self.impact_pause, .045)
            if event.event_type == "hero_hit" and event.critical:
                self.hero_critical_flash = .58
            if event.event_type in {"hero_hit", "enemy_hit", "boost", "thorns", "proc", "counter", "heal", "revive", "barrier", "chill"}:
                x = 870 if event.actor == "enemy" else 330
                if event.event_type == "enemy_hit":
                    x = 330
                elif event.event_type == "hero_hit":
                    x = 870
                if event.event_type in {"heal", "revive"}:
                    text = f"+{event.amount}"
                    color = (81, 222, 130)
                elif event.event_type == "chill":
                    text = f"CHILL {event.amount}%"
                    color = ELEMENT_COLORS[Element.ICE]
                elif event.event_type == "barrier":
                    text = f"ABSORB {event.amount}"
                    color = (130, 205, 245)
                elif event.blocked:
                    text = "BLOCK"
                    color = (130, 205, 245)
                elif event.event_type == "boost":
                    text = f"+{event.amount}"
                    color = (81, 222, 130)
                else:
                    text = f"-{event.amount}" + (" CRIT" if event.critical else "")
                    color = (248, 193, 72) if event.critical else ELEMENT_COLORS[event.element]
                self.float_notices.append(FloatNotice(text, x, 450, color))
                if event.amount:
                    self.shake = .12 if event.critical else .06
                    self.impact_pause = max(self.impact_pause, .075 if event.critical else .045)
                    if event.event_type == "enemy_hit" and not event.blocked:
                        self.hero_hit_flash = .18
                    elif event.event_type == "hero_hit" and not event.blocked:
                        self.enemy_hit_flash = .16
            if event.event_type in {"hero_hit", "enemy_hit", "proc", "counter", "thorns"} and event.amount:
                    burst_y = 438
                    self.fx_bursts.append(FxBurst(x, burst_y, color, "critical" if event.critical else event.event_type))
            if event.event_type == "enemy_down":
                self.save()

    def update(self, dt):
        self.time += dt
        self.toast_age += dt
        self.craft_reveal_age += dt
        if self.transition_target is not None:
            self.transition_age += dt
            if not self.transition_swapped and self.transition_age >= self.transition_duration * .48:
                self.screen = self.transition_target
                self.transition_swapped = True
            if self.transition_age >= self.transition_duration:
                self.transition_target = None
                self.transition_swapped = False
        self.shake = max(0, self.shake - dt)
        self.hero_hit_flash = max(0, self.hero_hit_flash - dt)
        self.hero_block_flash = max(0, self.hero_block_flash - dt)
        self.hero_critical_flash = max(0, self.hero_critical_flash - dt)
        self.enemy_hit_flash = max(0, self.enemy_hit_flash - dt)
        self.float_notices = [notice for notice in self.float_notices if notice.update(dt)]
        self.fx_bursts = [burst for burst in self.fx_bursts if burst.update(dt)]
        if self.screen == Screen.BATTLE and self.battle:
            if self.impact_pause > 0:
                self.impact_pause = max(0, self.impact_pause - dt)
            else:
                self.battle.update(dt)
            self.process_battle_events()
            if self.battle.outcome == BattleOutcome.VICTORY and not self.battle_processed:
                self.finish_victory()
            elif self.battle.outcome in {BattleOutcome.DEFEAT, BattleOutcome.RETREATED} and not self.battle_processed:
                self.battle_processed = True
                self.save()
            if self.battle.outcome == BattleOutcome.VICTORY and self.battle_processed:
                self.battle_finish_timer -= dt
                if self.battle_finish_timer <= 0:
                    self.begin_transition(Screen.LOOT, "RECOVERING THE SPOILS")
                    self.battle_finish_timer = 999.0

    def handle_events(self):
        self.clicked = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif self.transition_target is not None:
                if event.type == pygame.MOUSEMOTION:
                    self.mouse = event.pos
                continue
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.mouse = event.pos
                source = next((zone for zone in reversed(self.item_drag_zones) if zone.get("item") and zone["rect"].collidepoint(event.pos) and zone["role"] in {"inventory", "equipment"}), None)
                if source:
                    self.drag_candidate = {
                        "uid": source["item"].uid,
                        "role": source["role"],
                        "slot": source.get("slot"),
                        "index": source.get("index"),
                    }
                    self.drag_start = event.pos
                    self.drag_active = False
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.mouse = event.pos
                if self.drag_active:
                    self.finish_item_drag(event.pos)
                    self.clicked = False
                else:
                    self.clicked = True
                self.drag_candidate = None
                self.drag_active = False
            elif event.type == pygame.MOUSEMOTION:
                self.mouse = event.pos
                if self.drag_candidate and pygame.Vector2(event.pos).distance_to(self.drag_start) >= 7:
                    self.drag_active = True
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if self.confirm_new:
                    self.confirm_new = False
                elif self.screen == Screen.MAIN_MENU:
                    self.running = False
                elif self.screen == Screen.BATTLE and self.battle and self.battle.active:
                    self.battle.retreat()
                    self.battle_processed = True
                    self.begin_transition(Screen.HUB, "LEAVING THE ARENA")
                    self.save()
                elif self.screen == Screen.RECIPES:
                    self.screen = Screen.MIXER
                elif self.screen in {Screen.INVENTORY, Screen.MIXER, Screen.CHARACTER}:
                    self.screen = self.return_screen
                elif self.screen == Screen.LOOT:
                    self.hero.pending_loot = []
                    self.hero.pending_routes = []
                    self.hero.pending_stage = 0
                    self.screen = Screen.EPILOGUE if self.hero.campaign_complete and not self.hero.ending_seen else Screen.HUB
                    self.save()
                elif self.screen == Screen.EPILOGUE:
                    self.hero.ending_seen = True
                    self.screen = Screen.HUB
                    self.save()
                else:
                    self.screen = Screen.MAIN_MENU

    def header(self, title, subtitle=""):
        pygame.draw.line(self.screen_surface, COLORS["border_dark"], (30, 103), (1170, 103), 2)
        pygame.draw.line(self.screen_surface, COLORS["border"], (30, 101), (1170, 101), 1)
        self.ui.text(self.screen_surface, title, (36, 24), COLORS["gold"], "large", shadow=True)
        if subtitle:
            self.ui.text(self.screen_surface, subtitle, (38, 74), COLORS["muted"], "small")
        if self.hero:
            stats = self.hero.total_stats()
            plaque = pygame.Rect(790, 21, 378, 70)
            self.ui.panel(self.screen_surface, plaque, (29, 27, 27), COLORS["border_dark"], 8)
            self.ui.text(self.screen_surface, f"LV {self.hero.level}", (plaque.x + 17, plaque.y + 14), COLORS["gold"], "medium")
            self.ui.text(self.screen_surface, f"HP {stats['health']}   ATK {stats['attack']}   DEF {stats['defense']}   LUCK {stats['luck']}", (plaque.right - 15, plaque.y + 16), COLORS["text"], "small", "topright")
            self.ui.text(self.screen_surface, f"BONE DUST {self.hero.bone_dust}   •   BAG {len(self.hero.inventory)}/{self.hero.inventory_capacity}", (plaque.right - 15, plaque.y + 44), COLORS["muted"], "tiny", "topright")

    def draw_brand_mark(self):
        """Keep the Bonebound identity visible outside the title screen."""
        if self.screen in {Screen.MAIN_MENU, Screen.BATTLE}:
            return
        size = (156, 60)
        position = ((WIDTH - size[0]) // 2, 9)
        logo = self.ui.asset("bonebound_logo_v3", size)
        if not logo:
            return
        plate = pygame.Surface((size[0] + 18, size[1] + 10), pygame.SRCALPHA)
        pygame.draw.rect(plate, (5, 8, 12, 184), plate.get_rect(), border_radius=9)
        pygame.draw.rect(plate, (112, 82, 43, 155), plate.get_rect(), 1, border_radius=9)
        plate.blit(logo, (9, 5))
        self.screen_surface.blit(plate, (position[0] - 9, position[1] - 5))

    def draw_main_menu(self):
        self.ui.draw_world_background(self.screen_surface, self.time)
        wash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(wash, (5, 8, 13, 185), (0, 0, 590, HEIGHT))
        pygame.draw.polygon(wash, (5, 8, 13, 185), [(590, 0), (735, 0), (555, HEIGHT), (410, HEIGHT)])
        self.screen_surface.blit(wash, (0, 0))
        doorway = pygame.Rect(642, 92, 462, 714)
        pygame.draw.rect(self.screen_surface, (8, 9, 13), doorway, border_radius=150)
        pygame.draw.rect(self.screen_surface, (96, 72, 55), doorway, 12, border_radius=150)
        pygame.draw.rect(self.screen_surface, (38, 34, 39), doorway.inflate(-28, -28), 4, border_radius=138)
        inner = doorway.inflate(-46, -46)
        pygame.draw.rect(self.screen_surface, (7, 8, 13), inner, border_radius=126)
        for index in range(24):
            angle = index * math.tau / 24 + self.time * .035
            radius = 92 + index % 4 * 30
            x = inner.centerx + math.cos(angle) * radius
            y = inner.centery + 35 + math.sin(angle) * radius * .78
            color = (73, 57, 83) if index % 3 == 0 else (48, 43, 51)
            pygame.draw.circle(self.screen_surface, color, (round(x), round(y)), 2 + index % 3)
        pygame.draw.ellipse(self.screen_surface, (2, 3, 5), (701, 683, 343, 58))
        self.ui.ribbon(self.screen_surface, pygame.Rect(88, 112, 230, 34), "AUTOMATIC RPG", (131, 88, 158), "tiny")
        logo = self.ui.asset("bonebound_logo_v3", (520, 199))
        if logo:
            self.screen_surface.blit(logo, (38, 151))
        else:
            self.ui.text(self.screen_surface, "BONEBOUND", (86, 225), COLORS["gold"], "title", "midleft", True)
        pygame.draw.line(self.screen_surface, COLORS["gold"], (91, 349), (500, 349), 2)
        self.ui.text(self.screen_surface, "DESCENT", (89, 381), COLORS["text"], "large", "midleft")
        self.ui.wrapped(self.screen_surface, "Build a traveler. Break the dead road. Carry every scar and every item deeper.", pygame.Rect(91, 427, 410, 68), COLORS["muted"], "small", 5, 3)
        features = (("25", "DUNGEONS"), ("12", "BAG SLOTS"), ("∞", "ENDGAME"))
        for index, (value, label) in enumerate(features):
            card = pygame.Rect(90 + index * 143, 505, 128, 76)
            self.ui.panel(self.screen_surface, card, (14, 20, 28), (47, 61, 76), 9)
            self.ui.text(self.screen_surface, value, (card.centerx, card.y + 24), COLORS["gold"] if index < 2 else (188, 112, 218), "medium", "center")
            self.ui.text(self.screen_surface, label, (card.centerx, card.y + 54), COLORS["muted"], "tiny", "center")
        menu_hero = self.sprites.frame("hero", "idle", self.time, 440)
        if menu_hero:
            scale = .93 + math.sin(self.time * 2.1) * .008
            hero_size = (round(menu_hero.get_width() * scale), round(menu_hero.get_height() * scale))
            menu_hero = pygame.transform.scale(menu_hero, hero_size)
            self.screen_surface.blit(menu_hero, menu_hero.get_rect(midbottom=(873, 704)))
        play = pygame.Rect(90, 628, 410, 64)
        load = pygame.Rect(90, 710, 410, 64)
        modal_was_open = self.confirm_new
        menu_click = self.clicked if not modal_was_open else False
        if self.ui.button(self.screen_surface, play, "PLAY", self.mouse, menu_click, True, COLORS["gold"], "large"):
            if self.save_manager.exists():
                self.confirm_new = True
            else:
                self.new_game()
        if self.ui.button(self.screen_surface, load, "LOAD", self.mouse, menu_click, self.save_manager.exists(), (91, 159, 224), "large"):
            self.load_game()
        self.ui.text(self.screen_surface, f"EARLY PROTOTYPE  •  v{VERSION}", (92, 815), (104, 96, 88), "tiny")
        self.ui.text(self.screen_surface, "FIXED-PACE AUTO COMBAT  •  CONTINUOUS SAVE", (92, 849), (86, 92, 104), "tiny")
        if self.confirm_new:
            self.draw_new_confirmation(self.clicked if modal_was_open else False)

    def draw_new_confirmation(self, modal_click):
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((3, 5, 9, 205))
        self.screen_surface.blit(veil, (0, 0))
        rect = pygame.Rect(335, 335, 530, 280)
        self.ui.ornamented_panel(self.screen_surface, rect, (30, 27, 26), COLORS["gold"], 14, 2)
        self.ui.text(self.screen_surface, "Begin a new descent?", (rect.centerx, rect.y + 43), COLORS["gold"], "large", "midtop")
        self.ui.wrapped(self.screen_surface, "PLAY will replace the current save. LOAD keeps the existing journey.", pygame.Rect(rect.x + 55, rect.y + 107, rect.width - 110, 65), COLORS["muted"], "body", 5, 2)
        yes = pygame.Rect(rect.x + 54, rect.bottom - 78, 192, 48)
        no = pygame.Rect(rect.right - 246, rect.bottom - 78, 192, 48)
        if self.ui.button(self.screen_surface, yes, "NEW GAME", self.mouse, modal_click, True, (210, 83, 91), "body"):
            self.new_game()
        if self.ui.button(self.screen_surface, no, "CANCEL", self.mouse, modal_click, True, COLORS["border"], "body"):
            self.confirm_new = False

    def draw_hub(self):
        self.ui.draw_world_background(self.screen_surface, self.time)
        self.header("THE DESCENT", "Follow the road downward. Cleared dungeons remain open for another run.")
        map_rect = pygame.Rect(30, 120, 755, 682)
        self.ui.ornamented_panel(self.screen_surface, map_rect, (25, 25, 29), COLORS["border"], 13, 2)
        act_names = ["BONE ORCHARD", "ASH GALLERIES", "FROST RELIQUARY", "STORM OSSUARY", "ECLIPSE VAULT"]
        act_colors = [(164, 155, 133), (225, 91, 43), (79, 177, 216), (225, 196, 62), (166, 82, 203)]
        positions = []
        for row in range(5):
            band = pygame.Rect(map_rect.x + 12, map_rect.y + 12 + row * 130, map_rect.width - 24, 122)
            tint = self.ui.blend((25, 25, 29), act_colors[row], .07)
            pygame.draw.rect(self.screen_surface, tint, band, border_radius=9)
            pygame.draw.line(self.screen_surface, self.ui.blend(act_colors[row], COLORS["ink"], .60), (band.x + 12, band.bottom), (band.right - 12, band.bottom), 1)
            self.ui.text(self.screen_surface, f"ACT {row + 1}", (band.x + 15, band.y + 10), act_colors[row], "tiny")
            self.ui.text(self.screen_surface, act_names[row], (band.x + 72, band.y + 10), COLORS["muted"], "tiny")
            y = band.y + 77
            xs = [map_rect.x + 72 + col * 145 for col in range(5)]
            if row % 2:
                xs.reverse()
            for col in range(5):
                index = row * 5 + col + 1
                positions.append((xs[col], y))
        for index in range(24):
            start = positions[index]
            end = positions[index + 1]
            unlocked = index + 2 <= self.hero.unlocked_stage
            color = (91, 123, 98) if unlocked else (54, 52, 55)
            pygame.draw.line(self.screen_surface, (9, 9, 11), start, end, 9)
            pygame.draw.line(self.screen_surface, color, start, end, 4)
            distance = math.dist(start, end)
            marks = max(1, round(distance / 30))
            for mark in range(1, marks):
                amount = mark / marks
                x = round(start[0] + (end[0] - start[0]) * amount)
                y = round(start[1] + (end[1] - start[1]) * amount)
                pygame.draw.circle(self.screen_surface, self.ui.blend(color, COLORS["ink"], .28), (x, y), 2)
        for row in range(5):
            band_y = map_rect.y + 12 + row * 130
            accent = act_colors[row]
            for decoration in range(6):
                x = map_rect.x + 42 + decoration * 124 + (row % 2) * 31
                y = band_y + 105
                if row == 0:
                    pygame.draw.line(self.screen_surface, (64, 60, 54), (x, y), (x, y - 30), 4)
                    pygame.draw.line(self.screen_surface, (64, 60, 54), (x, y - 20), (x - 10, y - 31), 3)
                elif row == 1:
                    pygame.draw.circle(self.screen_surface, self.ui.blend(accent, COLORS["ink"], .42), (x, y - 8), 4 + decoration % 3)
                elif row == 2:
                    pygame.draw.polygon(self.screen_surface, self.ui.blend(accent, COLORS["ink"], .55), [(x, y), (x + 7, y - 20), (x + 13, y)])
                elif row == 3:
                    pygame.draw.lines(self.screen_surface, self.ui.blend(accent, COLORS["ink"], .50), False, [(x - 8, y - 28), (x + 2, y - 17), (x - 3, y - 7), (x + 9, y)], 2)
                else:
                    pygame.draw.rect(self.screen_surface, self.ui.blend(accent, COLORS["ink"], .65), (x - 5, y - 25, 10, 25))
        for index, (x, y) in enumerate(positions, 1):
                unlocked = index <= self.hero.unlocked_stage
                cleared = index in self.hero.cleared_stages
                selected = index == self.selected_stage
                act_color = act_colors[(index - 1) // 5]
                color = (79, 190, 116) if cleared else act_color if unlocked else (63, 59, 61)
                radius = 28 if index % 5 == 0 else 22
                pygame.draw.circle(self.screen_surface, (7, 7, 9), (x, y + 5), radius + 7)
                pygame.draw.circle(self.screen_surface, COLORS["gold"] if selected else (41, 38, 39), (x, y), radius + 5)
                pygame.draw.circle(self.screen_surface, self.ui.blend(color, COLORS["ink"], .60), (x, y), radius)
                pygame.draw.circle(self.screen_surface, color, (x, y), radius, 3)
                if index % 5 == 0:
                    pygame.draw.polygon(self.screen_surface, color, [(x, y - radius + 4), (x + 8, y - 7), (x + radius - 4, y), (x + 8, y + 7), (x, y + radius - 4), (x - 8, y + 7), (x - radius + 4, y), (x - 8, y - 7)], 2)
                self.ui.text(self.screen_surface, index if unlocked else "×", (x, y), COLORS["text"] if unlocked else (91, 84, 84), "small", "center", selected)
                node = pygame.Rect(x - radius - 8, y - radius - 8, (radius + 8) * 2, (radius + 8) * 2)
                if unlocked and node.collidepoint(self.mouse) and self.clicked:
                    self.selected_stage = index
                    self.save()
        stage = STAGES[self.selected_stage - 1]
        detail = pygame.Rect(807, 120, 363, 682)
        stage_element = ENEMIES[stage.enemies[-1]].element
        detail_color = ELEMENT_COLORS[stage_element]
        self.ui.ornamented_panel(self.screen_surface, detail, (35, 31, 29), self.ui.blend(detail_color, COLORS["border"], .42), 13, 2)
        pygame.draw.circle(self.screen_surface, self.ui.blend(detail_color, COLORS["ink"], .72), (detail.centerx, detail.y + 68), 43)
        pygame.draw.circle(self.screen_surface, detail_color, (detail.centerx, detail.y + 68), 43, 2)
        self.ui.text(self.screen_surface, stage.index, (detail.centerx, detail.y + 68), COLORS["text"], "large", "center", True)
        self.ui.ribbon(self.screen_surface, pygame.Rect(detail.x + 54, detail.y + 119, detail.width - 108, 32), f"ACT {stage.act}  •  DUNGEON", detail_color, "tiny")
        self.ui.fitted_text(self.screen_surface, stage.name, pygame.Rect(detail.x + 25, detail.y + 161, detail.width - 50, 34), COLORS["text"], "medium", "center")
        reward_name = ITEM_TEMPLATES[stage.first_clear_item]["name"]
        reward_text = "REWARD CLAIMED" if stage.index in self.hero.cleared_stages else f"FIRST CLEAR  •  {reward_name.upper()}"
        self.ui.fitted_text(self.screen_surface, f"LEVEL {stage.recommended_level}  •  {reward_text}", pygame.Rect(detail.x + 24, detail.y + 193, detail.width - 48, 25), COLORS["muted"], "tiny", "center")
        self.ui.wrapped(self.screen_surface, stage.description, pygame.Rect(detail.x + 25, detail.y + 234, detail.width - 50, 58), COLORS["text"], "small", 3, 2)
        self.ui.text(self.screen_surface, "THE LINE AHEAD", (detail.x + 24, detail.y + 307), COLORS["muted"], "tiny")
        y = detail.y + 336
        for enemy_id in stage.enemies:
            enemy = ENEMIES[enemy_id]
            ecolor = ELEMENT_COLORS[enemy.element]
            pygame.draw.circle(self.screen_surface, self.ui.blend(ecolor, COLORS["ink"], .65), (detail.x + 39, y + 10), 14)
            pygame.draw.circle(self.screen_surface, ecolor, (detail.x + 39, y + 10), 14, 2)
            pygame.draw.circle(self.screen_surface, COLORS["text"], (detail.x + 39, y + 7), 3)
            marker = "BOSS" if enemy.boss else "ELITE" if enemy.elite else enemy.element.value.upper()
            if "ambusher" in enemy.traits:
                marker += " / AMBUSH"
            self.ui.text(self.screen_surface, enemy.name, (detail.x + 63, y), COLORS["text"], "small")
            self.ui.text(self.screen_surface, marker, (detail.right - 22, y + 2), ecolor, "tiny", "topright")
            y += 38
        equipment_y = detail.y + 494
        self.ui.text(self.screen_surface, "LOADOUT", (detail.x + 24, equipment_y), COLORS["muted"], "tiny")
        for slot_index, slot in enumerate(("weapon", "shield", "ring1", "ring2")):
            item = self.hero.equipment[slot]
            slot_rect = pygame.Rect(detail.x + 24 + slot_index * 78, equipment_y + 26, 68, 73)
            slot_label = {"weapon": "W", "shield": "S", "ring1": "T1", "ring2": "T2"}[slot]
            self.ui.item_slot(self.screen_surface, slot_rect, item, self.mouse, False, False, slot_label)
        boost = self.hero.item_by_uid(self.hero.boost_uid) if self.hero.boost_uid else None
        boost_rect = pygame.Rect(detail.x + 24, detail.y + 609, 68, 48)
        if boost:
            self.ui.draw_item_icon(self.screen_surface, boost_rect, boost)
        self.ui.text(self.screen_surface, "BOOST", (detail.x + 101, detail.y + 612), COLORS["muted"], "tiny")
        self.ui.fitted_text(self.screen_surface, boost.display_name if boost else "No potion prepared", pygame.Rect(detail.x + 101, detail.y + 632, 220, 23), self.ui.item_color(boost) if boost else (104, 99, 96), "small")
        fight = pygame.Rect(detail.x + 22, detail.bottom - 67, detail.width - 44, 49)
        if self.ui.button(self.screen_surface, fight, "ENTER DUNGEON", self.mouse, self.clicked, True, (213, 89, 75), "medium"):
            self.start_battle()
        workshop_width = 520 if self.hero.campaign_complete else 805
        workshop_label = "WORKSHOP  •  GEAR & MIXER" if self.hero.campaign_complete else "OPEN WORKSHOP  •  GEAR  •  MIXER  •  CHARACTER"
        if self.ui.button(self.screen_surface, pygame.Rect(30, 831, workshop_width, 61), workshop_label, self.mouse, self.clicked, True, COLORS["blue"], "medium"):
            self.return_screen = Screen.HUB
            self.begin_transition(Screen.INVENTORY, "OPENING THE WORKSHOP")
            self.selected_uid = None
        if self.hero.campaign_complete:
            endless_label = f"ENDLESS  •  DEPTH {self.hero.endless_depth + 1}"
            if self.ui.button(self.screen_surface, pygame.Rect(570, 831, 265, 61), endless_label, self.mouse, self.clicked, True, (158, 87, 202), "small"):
                self.start_endless()
        if self.ui.button(self.screen_surface, pygame.Rect(855, 831, 315, 61), "SAVE & TITLE", self.mouse, self.clicked, True, COLORS["gold"], "medium"):
            self.save()
            self.begin_transition(Screen.MAIN_MENU, "SEALING THE CHRONICLE")

    def find_selected_item(self):
        if not self.hero or not self.selected_uid:
            return None
        item = self.hero.item_by_uid(self.selected_uid)
        if item:
            return item
        for equipped in self.hero.equipment.values():
            if equipped and equipped.uid == self.selected_uid:
                return equipped
        return None

    def selected_slot(self):
        if not self.selected_uid:
            return None
        for slot, item in self.hero.equipment.items():
            if item and item.uid == self.selected_uid:
                return slot
        return None

    def draw_workshop(self):
        self.ui.draw_world_background(self.screen_surface, self.time)
        self.header("WORKSHOP", "Hold and drag items between the backpack, gear slots and mixer sockets.")
        character = pygame.Rect(20, 120, 300, 712)
        backpack = pygame.Rect(335, 120, 500, 712)
        forge = pygame.Rect(850, 120, 330, 712)
        self.ui.ornamented_panel(self.screen_surface, character, (16, 24, 33), (61, 122, 170), 12, 1)
        self.ui.ornamented_panel(self.screen_surface, backpack, (17, 23, 31), (58, 72, 88), 12, 1)
        self.ui.ornamented_panel(self.screen_surface, forge, (19, 22, 31), (112, 72, 137), 12, 1)
        self.ui.ribbon(self.screen_surface, pygame.Rect(character.x + 49, character.y + 17, 202, 32), "CHARACTER + GEAR", COLORS["blue"], "tiny")
        equipment_rects = {}
        for index, slot in enumerate(("weapon", "shield", "ring1", "ring2")):
            rect = pygame.Rect(character.x + 15 + index * 68, character.y + 61, 62, 82)
            equipment_rects[slot] = rect
            item = self.hero.equipment[slot]
            slot_label = {"weapon": "W", "shield": "S", "ring1": "T1", "ring2": "T2"}[slot]
            if self.ui.item_slot(self.screen_surface, rect, item, self.mouse, self.clicked, bool(item and item.uid == self.selected_uid), slot_label) and item:
                self.selected_uid = item.uid
                self.trash_confirm_uid = None
            self.register_item_drag_zone(rect, "equipment", item, slot=slot)
        portrait = pygame.Rect(character.x + 18, character.y + 157, character.width - 36, 235)
        self.ui.draw_cavern(self.screen_surface, portrait, Element.ARCANE, 1, self.time)
        pygame.draw.rect(self.screen_surface, (61, 105, 141), portrait, 2, border_radius=10)
        self.draw_hero(pygame.Vector2(portrait.centerx, portrait.bottom - 24), "idle", self.time, .75)
        self.ui.text(self.screen_surface, f"LV {self.hero.level}", (portrait.x + 14, portrait.y + 13), COLORS["gold"], "medium", shadow=True)
        totals = self.hero.total_stats()
        stat_data = (("health", "HP", (216, 78, 91)), ("attack", "ATK", (230, 145, 74)), ("defense", "DEF", (77, 151, 222)), ("luck", "LUCK", (174, 105, 213)))
        for index, (stat, label, color) in enumerate(stat_data):
            col, row = index % 2, index // 2
            chip = pygame.Rect(character.x + 16 + col * 137, character.y + 408 + row * 57, 104, 47)
            self.ui.stat_chip(self.screen_surface, chip, label, totals[stat], color)
            plus = pygame.Rect(chip.right + 5, chip.y + 8, 22, 30)
            if self.ui.button(self.screen_surface, plus, "+", self.mouse, self.clicked, self.hero.stat_points > 0, color, "small"):
                if self.hero.spend_point(stat):
                    self.save()
                    self.toast(f"Raised {stat.upper()}.")
        xp = pygame.Rect(character.x + 22, character.y + 536, character.width - 44, 21)
        self.ui.bar(self.screen_surface, xp, self.hero.experience, self.hero.xp_needed, (109, 101, 222), "XP")
        self.ui.text(self.screen_surface, f"{self.hero.stat_points} UNSPENT POINTS", (character.centerx, character.y + 574), COLORS["gold"] if self.hero.stat_points else COLORS["muted"], "tiny", "center")
        training = pygame.Rect(character.x + 25, character.y + 598, character.width - 50, 43)
        if self.ui.button(self.screen_surface, training, f"TRAIN +1  •  {self.hero.training_cost} DUST", self.mouse, self.clicked, self.hero.bone_dust >= self.hero.training_cost, (146, 90, 185), "small"):
            ok, cost = self.hero.train_with_dust()
            if ok:
                self.save()
                self.toast(f"Training used {cost} bone dust.")
        self.ui.text(self.screen_surface, f"WINS {self.hero.total_wins}   LOSSES {self.hero.total_losses}", (character.centerx, character.y + 665), COLORS["muted"], "tiny", "center")
        self.ui.ribbon(self.screen_surface, pygame.Rect(backpack.x + 107, backpack.y + 17, 286, 32), f"BACKPACK  {len(self.hero.inventory)}/12", (112, 85, 62), "tiny")
        for index in range(self.hero.inventory_capacity):
            row, col = divmod(index, 4)
            card = pygame.Rect(backpack.x + 16 + col * 118, backpack.y + 59 + row * 143, 109, 133)
            if index < len(self.hero.inventory):
                item = self.hero.inventory[index]
                if self.ui.item_slot(self.screen_surface, card, item, self.mouse, self.clicked, self.selected_uid == item.uid, str(index + 1)):
                    self.selected_uid = item.uid
                    self.trash_confirm_uid = None
            else:
                item = None
                self.ui.empty_card(self.screen_surface, card, str(index + 1), self.mouse, self.clicked)
            self.register_item_drag_zone(card, "inventory", item, index=index)
        selected = self.find_selected_item()
        selected_panel = pygame.Rect(backpack.x + 16, backpack.y + 503, backpack.width - 32, 190)
        self.ui.ornamented_panel(self.screen_surface, selected_panel, (13, 19, 27), (49, 65, 82), 9, 1)
        if selected:
            color = self.ui.item_color(selected)
            icon = pygame.Rect(selected_panel.x + 16, selected_panel.y + 17, 92, 92)
            self.ui.draw_item_icon(self.screen_surface, icon, selected, True)
            self.ui.fitted_text(self.screen_surface, selected.display_name, pygame.Rect(icon.right + 14, selected_panel.y + 18, selected_panel.width - 140, 28), COLORS["text"], "medium")
            tag = selected.element.value.upper() if selected.element != Element.NEUTRAL else selected.category_label.upper()
            if selected.kind in {ItemKind.WEAPON, ItemKind.SHIELD, ItemKind.RING}:
                tag += f"  •  FORGE +{selected.upgrade}/{Mixer._reinforcement_limit(selected)}"
            self.ui.text(self.screen_surface, tag, (icon.right + 14, selected_panel.y + 53), color, "tiny")
            self.ui.fitted_text(self.screen_surface, selected.stat_text(), pygame.Rect(icon.right + 14, selected_panel.y + 76, selected_panel.width - 140, 22), COLORS["text"], "small")
            comparison = ""
            if selected.slot and not self.selected_slot():
                if selected.kind == ItemKind.RING:
                    candidates = [self.hero.equipment["ring1"], self.hero.equipment["ring2"]]
                    equipped = min(candidates, key=lambda item: sum(item.stats.values()) if item else -1)
                else:
                    equipped = self.hero.equipment[selected.slot]
                old_stats = equipped.stats if equipped else {}
                changes = []
                for key in ("health", "attack", "defense", "luck"):
                    delta = selected.stats.get(key, 0) - old_stats.get(key, 0)
                    if delta:
                        changes.append(f"{key[:3].upper()} {delta:+d}")
                comparison = "EQUIP DELTA  " + ("  ".join(changes) if changes else "NO BASE STAT CHANGE")
            if comparison:
                comparison_y = selected_panel.y + 128 if self.ui.item_power_text(selected) else selected_panel.y + 109
                self.ui.fitted_text(self.screen_surface, comparison, pygame.Rect(selected_panel.x + 18, comparison_y, selected_panel.width - 36, 19), (91, 188, 220), "tiny")
            power_text = self.ui.item_power_text(selected)
            if power_text:
                self.ui.fitted_text(self.screen_surface, power_text.upper(), pygame.Rect(selected_panel.x + 18, selected_panel.y + 105, selected_panel.width - 36, 19), COLORS["gold"], "tiny")
            description_y = selected_panel.y + 151 if comparison and power_text else selected_panel.y + 132 if comparison or power_text else selected_panel.y + 116
            self.ui.wrapped(self.screen_surface, selected.description, pygame.Rect(selected_panel.x + 18, description_y, selected_panel.width - 36, 38), COLORS["muted"], "tiny", 2, 2)
        else:
            self.ui.text(self.screen_surface, "SELECT AN ITEM", (selected_panel.centerx, selected_panel.y + 69), COLORS["muted"], "medium", "center")
            self.ui.text(self.screen_surface, "Inspect, equip, brew or salvage without leaving this screen.", (selected_panel.centerx, selected_panel.y + 109), (106, 111, 121), "tiny", "center")
        self.ui.ribbon(self.screen_surface, pygame.Rect(forge.x + 68, forge.y + 17, 194, 32), "FIELD MIXER", (144, 82, 168), "tiny")
        left = self.hero.item_by_uid(self.mixer_left)
        right = self.hero.item_by_uid(self.mixer_right)
        left_rect = pygame.Rect(forge.x + 17, forge.y + 62, 138, 132)
        right_rect = pygame.Rect(forge.right - 155, forge.y + 62, 138, 132)
        if self.ui.item_slot(self.screen_surface, left_rect, left, self.mouse, self.clicked, bool(left), "BASE • KEPT"):
            self.mixer_left = None
        if self.ui.item_slot(self.screen_surface, right_rect, right, self.mouse, self.clicked, bool(right), "CATALYST • SPENT"):
            self.mixer_right = None
        self.register_item_drag_zone(left_rect, "mixer_base", left)
        self.register_item_drag_zone(right_rect, "mixer_catalyst", right)
        valid, preview = Mixer.preview(left, right)
        result_preview = Mixer.visual_result(left, right)
        preview_rect = pygame.Rect(forge.x + 17, forge.y + 208, forge.width - 34, 86)
        self.ui.ornamented_panel(self.screen_surface, preview_rect, (18, 18, 25), (99, 72, 119), 8)
        self.ui.text(self.screen_surface, "PREVIEW", (preview_rect.x + 13, preview_rect.y + 10), COLORS["muted"], "tiny")
        preview_text_width = preview_rect.width - (96 if result_preview else 26)
        self.ui.wrapped(self.screen_surface, preview, pygame.Rect(preview_rect.x + 13, preview_rect.y + 33, preview_text_width, 44), (91, 211, 137) if valid else (214, 111, 120), "tiny", 2, 3)
        if result_preview:
            result_rect = pygame.Rect(preview_rect.right - 75, preview_rect.y + 9, 66, 66)
            self.ui.draw_item_icon(self.screen_surface, result_rect, result_preview, True)
            self.ui.text(self.screen_surface, "OUTPUT", (result_rect.centerx, preview_rect.bottom - 8), self.ui.item_color(result_preview), "tiny", "midbottom")
        mix_button = pygame.Rect(forge.x + 17, forge.y + 307, 194, 43)
        if self.ui.button(self.screen_surface, mix_button, "MIX ITEMS", self.mouse, self.clicked, valid, (169, 96, 203), "small"):
            source_template = left.template_id if left else ""
            ok, message, result = Mixer.mix(self.hero, self.mixer_left, self.mixer_right)
            if ok:
                self.mixer_left = result.uid
                self.mixer_right = None
                self.selected_uid = result.uid
                self.audio.play("forge" if result.template_id != source_template else "mix")
                self.reveal_craft(result)
                self.save()
            else:
                self.audio.play("error")
            self.toast(message)
        if self.ui.button(self.screen_surface, pygame.Rect(forge.right - 102, forge.y + 307, 85, 43), "SWAP", self.mouse, self.clicked, bool(left or right), COLORS["border"], "tiny"):
            self.mixer_left, self.mixer_right = self.mixer_right, self.mixer_left
        pygame.draw.line(self.screen_surface, (61, 53, 70), (forge.x + 18, forge.y + 369), (forge.right - 18, forge.y + 369), 1)
        self.ui.text(self.screen_surface, "SELECTED ITEM ACTIONS", (forge.x + 18, forge.y + 386), COLORS["muted"], "tiny")
        source_slot = self.selected_slot()
        action_y = forge.y + 416
        if selected and not source_slot:
            if self.ui.button(self.screen_surface, pygame.Rect(forge.x + 17, action_y, 138, 39), "SET BASE", self.mouse, self.clicked, True, (72, 158, 127), "small"):
                self.mixer_left = selected.uid
                if self.mixer_right == selected.uid and selected.stack < 2:
                    self.mixer_right = None
            catalyst_ok = selected.uid != self.mixer_left or selected.stack >= 2
            if self.ui.button(self.screen_surface, pygame.Rect(forge.right - 155, action_y, 138, 39), "SET CATALYST", self.mouse, self.clicked, catalyst_ok, (190, 91, 108), "tiny"):
                self.mixer_right = selected.uid
            action_y += 49
        if selected and source_slot:
            if self.ui.button(self.screen_surface, pygame.Rect(forge.x + 17, action_y, forge.width - 34, 42), "UNEQUIP", self.mouse, self.clicked, True, COLORS["blue"], "small"):
                ok, message = self.hero.unequip(source_slot)
                if ok:
                    self.selected_uid = None
                    self.save()
                self.toast(message)
            action_y += 51
        elif selected and selected.slot:
            targets = (("TRINKET I", "ring1"), ("TRINKET II", "ring2")) if selected.kind == ItemKind.RING else (("EQUIP", None),)
            for label, target in targets:
                width = 138 if len(targets) == 2 else forge.width - 34
                x = forge.x + 17 if target != "ring2" else forge.right - 155
                if self.ui.button(self.screen_surface, pygame.Rect(x, action_y, width, 42), label, self.mouse, self.clicked, True, COLORS["blue"], "small"):
                    ok, message = self.hero.equip(selected.uid, target)
                    if ok:
                        self.selected_uid = None
                        self.audio.play("equip")
                        self.save()
                    self.toast(message)
            action_y += 51
        if selected and selected.kind in {ItemKind.WEAPON, ItemKind.SHIELD, ItemKind.RING}:
            temper_cost = Mixer.reinforcement_cost(selected)
            temper_ready = selected.upgrade < Mixer._reinforcement_limit(selected) and self.hero.bone_dust >= temper_cost
            temper_label = f"TEMPER +1  •  {temper_cost} DUST" if selected.upgrade < Mixer._reinforcement_limit(selected) else "MAX TEMPER REACHED"
            if self.ui.button(self.screen_surface, pygame.Rect(forge.x + 17, action_y, forge.width - 34, 42), temper_label, self.mouse, self.clicked, temper_ready, (225, 145, 65), "small"):
                ok, message, result = Mixer.temper(self.hero, selected.uid)
                if ok:
                    self.audio.play("temper")
                    self.reveal_craft(result)
                    self.save()
                self.toast(message)
            action_y += 51
        if selected and not source_slot and selected.kind == ItemKind.POTION:
            if self.ui.button(self.screen_surface, pygame.Rect(forge.x + 17, action_y, forge.width - 34, 42), "PREPARE BOOST", self.mouse, self.clicked, True, (69, 180, 126), "small"):
                ok, message = self.hero.set_boost(selected.uid)
                if ok:
                    self.save()
                self.toast(message)
            action_y += 51
        if selected and not source_slot:
            confirm = self.trash_confirm_uid == selected.uid
            if self.ui.button(self.screen_surface, pygame.Rect(forge.x + 17, action_y, forge.width - 34, 40), "CONFIRM SALVAGE" if confirm else "SALVAGE", self.mouse, self.clicked, True, (182, 72, 85), "small"):
                if confirm:
                    value = LootSystem().salvage_value(selected)
                    self.hero.remove_item(selected.uid, selected.stack)
                    self.hero.bone_dust += value
                    self.selected_uid = None
                    self.trash_confirm_uid = None
                    self.mixer_left = None if self.mixer_left == selected.uid else self.mixer_left
                    self.mixer_right = None if self.mixer_right == selected.uid else self.mixer_right
                    self.audio.play("salvage")
                    self.save()
                    self.toast(f"Salvaged for {value} bone dust.")
                else:
                    self.trash_confirm_uid = selected.uid
                    self.toast("Press confirm to salvage this item.")
        self.ui.text(self.screen_surface, f"{len(self.hero.discovered_recipes)}/{len(RECIPES)} RECIPES DISCOVERED", (forge.centerx, forge.bottom - 20), COLORS["muted"], "tiny", "center")
        if self.ui.button(self.screen_surface, pygame.Rect(30, 861, 230, 59), "BACK TO MAP", self.mouse, self.clicked, True, COLORS["border"], "medium"):
            self.screen = self.return_screen
            self.selected_uid = None

    def draw_inventory(self):
        self.ui.draw_world_background(self.screen_surface, self.time)
        self.header("INVENTORY", "Build the traveler on the left. The twelve carved slots are everything carried below.")
        equip_rect = pygame.Rect(25, 120, 360, 712)
        bag_rect = pygame.Rect(400, 120, 475, 712)
        detail_rect = pygame.Rect(890, 120, 285, 712)
        self.ui.ornamented_panel(self.screen_surface, equip_rect, (31, 29, 28), COLORS["border"], 12, 2)
        self.ui.ornamented_panel(self.screen_surface, bag_rect, (29, 27, 27), COLORS["wood_light"], 12, 2)
        self.ui.ribbon(self.screen_surface, pygame.Rect(equip_rect.x + 82, equip_rect.y + 18, 196, 33), "LOADOUT", COLORS["blue"], "small")
        self.ui.ribbon(self.screen_surface, pygame.Rect(bag_rect.x + 110, bag_rect.y + 18, 255, 33), f"BACKPACK  {len(self.hero.inventory)}/12", COLORS["wood_light"], "small")
        labels = {
            "weapon": "WEAPON",
            "shield": "SHIELD" if self.hero.equipment.get("shield") else "SHIELD • EMPTY",
            "ring1": "TRINKET I",
            "ring2": "TRINKET II",
        }
        equipment_rects = {
            "weapon": pygame.Rect(equip_rect.x + 18, equip_rect.y + 74, 145, 126),
            "shield": pygame.Rect(equip_rect.right - 163, equip_rect.y + 74, 145, 126),
            "ring1": pygame.Rect(equip_rect.x + 18, equip_rect.y + 414, 145, 118),
            "ring2": pygame.Rect(equip_rect.right - 163, equip_rect.y + 414, 145, 118),
        }
        pygame.draw.ellipse(self.screen_surface, (10, 9, 11), (equip_rect.centerx - 90, equip_rect.y + 388, 180, 34))
        self.draw_hero(pygame.Vector2(equip_rect.centerx, equip_rect.y + 405), "idle", self.time, .92)
        for slot, card in equipment_rects.items():
            item = self.hero.equipment[slot]
            if self.ui.item_slot(self.screen_surface, card, item, self.mouse, self.clicked, bool(item and self.selected_uid == item.uid), labels[slot]):
                if item:
                    self.selected_uid = item.uid
                    self.trash_confirm_uid = None
        stats = self.hero.total_stats()
        stat_data = (("health", (210, 72, 83)), ("attack", (230, 143, 70)), ("defense", (83, 151, 226)), ("luck", (186, 105, 220)))
        for index, (key, color) in enumerate(stat_data):
            col, row = index % 2, index // 2
            chip = pygame.Rect(equip_rect.x + 18 + col * 166, equip_rect.y + 560 + row * 57, 157, 47)
            self.ui.stat_chip(self.screen_surface, chip, key.upper(), stats[key], color)
        boost = self.hero.item_by_uid(self.hero.boost_uid) if self.hero.boost_uid else None
        pygame.draw.line(self.screen_surface, COLORS["border_dark"], (equip_rect.x + 20, equip_rect.y + 683), (equip_rect.right - 20, equip_rect.y + 683), 1)
        self.ui.text(self.screen_surface, "PREPARED BOOST", (equip_rect.x + 22, equip_rect.y + 694), COLORS["muted"], "tiny")
        self.ui.fitted_text(self.screen_surface, boost.display_name if boost else "None", pygame.Rect(equip_rect.x + 151, equip_rect.y + 687, 182, 30), self.ui.item_color(boost) if boost else (99, 94, 90), "small")
        for index in range(self.hero.inventory_capacity):
            row, col = divmod(index, 4)
            card = pygame.Rect(bag_rect.x + 18 + col * 110, bag_rect.y + 70 + row * 205, 101, 187)
            if index < len(self.hero.inventory):
                item = self.hero.inventory[index]
                if self.ui.item_slot(self.screen_surface, card, item, self.mouse, self.clicked, self.selected_uid == item.uid, str(index + 1)):
                    self.selected_uid = item.uid
                    self.trash_confirm_uid = None
            else:
                self.ui.empty_card(self.screen_surface, card, f"SLOT {index + 1}", self.mouse, self.clicked)
        selected = self.find_selected_item()
        self.ui.item_detail(self.screen_surface, pygame.Rect(detail_rect.x, detail_rect.y, detail_rect.width, 300), selected)
        source_slot = self.selected_slot()
        y = detail_rect.y + 325
        if selected and source_slot:
            if self.ui.button(self.screen_surface, pygame.Rect(detail_rect.x + 16, y, detail_rect.width - 32, 48), "UNEQUIP", self.mouse, self.clicked, True, COLORS["blue"], "body"):
                ok, message = self.hero.unequip(source_slot)
                if ok:
                    self.selected_uid = None
                    self.save()
                self.toast(message)
        elif selected and selected.slot:
            if selected.kind == ItemKind.RING:
                for label, slot in (("EQUIP TRINKET I", "ring1"), ("EQUIP TRINKET II", "ring2")):
                    if self.ui.button(self.screen_surface, pygame.Rect(detail_rect.x + 16, y, detail_rect.width - 32, 44), label, self.mouse, self.clicked, True, COLORS["blue"], "small"):
                        ok, message = self.hero.equip(selected.uid, slot)
                        if ok:
                            self.selected_uid = None
                            self.audio.play("equip")
                            self.save()
                        self.toast(message)
                    y += 53
            else:
                if self.ui.button(self.screen_surface, pygame.Rect(detail_rect.x + 16, y, detail_rect.width - 32, 48), "EQUIP", self.mouse, self.clicked, True, COLORS["blue"], "body"):
                    ok, message = self.hero.equip(selected.uid)
                    if ok:
                        self.selected_uid = None
                        self.audio.play("equip")
                        self.save()
                    self.toast(message)
                y += 57
        if selected and not source_slot and selected.kind == ItemKind.POTION:
            if self.ui.button(self.screen_surface, pygame.Rect(detail_rect.x + 16, y, detail_rect.width - 32, 48), "SET AS BOOST", self.mouse, self.clicked, True, (75, 183, 119), "body"):
                ok, message = self.hero.set_boost(selected.uid)
                if ok:
                    self.save()
                self.toast(message)
            y += 57
        if selected and not source_slot:
            confirm = self.trash_confirm_uid == selected.uid
            label = "CONFIRM SALVAGE" if confirm else "SALVAGE"
            if self.ui.button(self.screen_surface, pygame.Rect(detail_rect.x + 16, max(y, detail_rect.y + 510), detail_rect.width - 32, 48), label, self.mouse, self.clicked, True, (190, 73, 81), "body"):
                if confirm:
                    value = LootSystem().salvage_value(selected)
                    self.hero.remove_item(selected.uid, selected.stack)
                    self.hero.bone_dust += value
                    self.selected_uid = None
                    self.trash_confirm_uid = None
                    self.audio.play("salvage")
                    self.save()
                    self.toast(f"Salvaged for {value} bone dust.")
                else:
                    self.trash_confirm_uid = selected.uid
                    self.toast("Click confirm to permanently salvage this item.")
        self.ui.wrapped(self.screen_surface, "Select a slot to inspect it. Equipment swaps never destroy the item already worn.", pygame.Rect(detail_rect.x + 18, detail_rect.bottom - 89, detail_rect.width - 36, 58), COLORS["muted"], "tiny", 3, 3)
        back = pygame.Rect(30, 861, 210, 59)
        if self.ui.button(self.screen_surface, back, "BACK", self.mouse, self.clicked, True, COLORS["border"], "medium"):
            self.screen = self.return_screen
            self.selected_uid = None

    def draw_mixer(self):
        self.ui.draw_world_background(self.screen_surface, self.time)
        self.header("THE MIXER", "Drag a base and catalyst into the rig; the result is shown before committing.")
        bag = pygame.Rect(25, 120, 505, 712)
        work = pygame.Rect(545, 120, 630, 712)
        self.ui.ornamented_panel(self.screen_surface, bag, (30, 28, 27), COLORS["wood_light"], 12, 2)
        self.ui.ornamented_panel(self.screen_surface, work, (28, 26, 27), (126, 77, 145), 12, 2)
        self.ui.ribbon(self.screen_surface, pygame.Rect(bag.x + 123, bag.y + 18, 260, 33), f"BACKPACK  {len(self.hero.inventory)}/12", COLORS["wood_light"], "small")
        for index in range(self.hero.inventory_capacity):
            row, col = divmod(index, 4)
            card = pygame.Rect(bag.x + 17 + col * 118, bag.y + 70 + row * 205, 108, 187)
            if index < len(self.hero.inventory):
                item = self.hero.inventory[index]
                selected = item.uid in {self.mixer_left, self.mixer_right}
                if self.ui.item_slot(self.screen_surface, card, item, self.mouse, self.clicked, selected, str(index + 1)):
                    if item.uid == self.mixer_left and item.uid == self.mixer_right:
                        self.mixer_left = None
                        self.mixer_right = None
                    elif item.uid == self.mixer_left and self.mixer_right is None and item.stack >= 2:
                        self.mixer_right = item.uid
                    elif item.uid == self.mixer_left:
                        self.mixer_left = None
                    elif item.uid == self.mixer_right:
                        self.mixer_right = None
                    elif self.mixer_left is None:
                        self.mixer_left = item.uid
                    else:
                        self.mixer_right = item.uid
            else:
                item = None
                self.ui.empty_card(self.screen_surface, card, f"SLOT {index + 1}", self.mouse, self.clicked)
            self.register_item_drag_zone(card, "inventory", item, index=index)
        left = self.hero.item_by_uid(self.mixer_left)
        right = self.hero.item_by_uid(self.mixer_right)
        valid, preview = Mixer.preview(left, right)
        result_preview = Mixer.visual_result(left, right)
        self.ui.ribbon(self.screen_surface, pygame.Rect(work.centerx - 135, work.y + 18, 270, 33), "BUBBLEGUM'S FIELD RIG", (145, 80, 153), "small")
        left_rect = pygame.Rect(work.x + 42, work.y + 82, 168, 176)
        right_rect = pygame.Rect(work.right - 210, work.y + 82, 168, 176)
        self.ui.item_slot(self.screen_surface, left_rect, left, self.mouse, False, bool(left), "BASE • RETURNS")
        self.ui.item_slot(self.screen_surface, right_rect, right, self.mouse, False, bool(right), "CATALYST • SPENT")
        self.register_item_drag_zone(left_rect, "mixer_base", left)
        self.register_item_drag_zone(right_rect, "mixer_catalyst", right)
        vessel = (work.centerx, work.y + 205)
        pulse = 3 + math.sin(self.time * 3.2) * 3
        pygame.draw.line(self.screen_surface, (89, 69, 89), (left_rect.right, left_rect.centery), (vessel[0] - 42, vessel[1]), 10)
        pygame.draw.line(self.screen_surface, (53, 44, 56), (left_rect.right, left_rect.centery), (vessel[0] - 42, vessel[1]), 5)
        pygame.draw.line(self.screen_surface, (89, 69, 89), (right_rect.x, right_rect.centery), (vessel[0] + 42, vessel[1]), 10)
        pygame.draw.line(self.screen_surface, (53, 44, 56), (right_rect.x, right_rect.centery), (vessel[0] + 42, vessel[1]), 5)
        pygame.draw.circle(self.screen_surface, (12, 11, 14), vessel, 61)
        pygame.draw.circle(self.screen_surface, (111, 66, 130), vessel, 55, 5)
        pygame.draw.circle(self.screen_surface, (54, 35, 64), vessel, round(38 + pulse))
        pygame.draw.arc(self.screen_surface, (200, 111, 215), pygame.Rect(vessel[0] - 34, vessel[1] - 34, 68, 68), self.time, self.time + 4.2, 4)
        if result_preview:
            output_rect = pygame.Rect(0, 0, 82, 82)
            output_rect.center = vessel
            self.ui.draw_item_icon(self.screen_surface, output_rect, result_preview, True)
        else:
            self.ui.text(self.screen_surface, "+", vessel, COLORS["gold"], "large", "center", True)
        self.ui.text(self.screen_surface, "BASE ITEM", (left_rect.centerx, left_rect.y - 27), (87, 207, 129), "tiny", "center")
        self.ui.text(self.screen_surface, "CATALYST", (right_rect.centerx, right_rect.y - 27), (226, 91, 96), "tiny", "center")
        preview_rect = pygame.Rect(work.x + 40, work.y + 292, work.width - 80, 108)
        self.ui.ornamented_panel(self.screen_surface, preview_rect, (18, 16, 20), (103, 71, 112), 8)
        self.ui.text(self.screen_surface, "THE RIG PREDICTS", (preview_rect.x + 17, preview_rect.y + 13), COLORS["muted"], "tiny")
        text_width = preview_rect.width - (132 if result_preview else 34)
        self.ui.wrapped(self.screen_surface, preview, pygame.Rect(preview_rect.x + 17, preview_rect.y + 42, text_width, 58), (91, 211, 137) if valid else (218, 115, 119), "small", 4, 2)
        if result_preview:
            result_rect = pygame.Rect(preview_rect.right - 99, preview_rect.y + 10, 82, 82)
            self.ui.draw_item_icon(self.screen_surface, result_rect, result_preview, True)
            self.ui.text(self.screen_surface, "OUTPUT", (result_rect.centerx, preview_rect.bottom - 5), self.ui.item_color(result_preview), "tiny", "midbottom")
        mix_rect = pygame.Rect(work.x + 91, work.y + 422, work.width - 182, 58)
        if self.ui.button(self.screen_surface, mix_rect, "MIX ITEMS", self.mouse, self.clicked, valid, (183, 104, 224), "medium"):
            source_template = left.template_id if left else ""
            ok, message, result = Mixer.mix(self.hero, self.mixer_left, self.mixer_right)
            if ok:
                self.mixer_left = result.uid
                self.mixer_right = None
                self.audio.play("forge" if result.template_id != source_template else "mix")
                self.reveal_craft(result)
                self.save()
            else:
                self.audio.play("error")
            self.toast(message)
        swap = pygame.Rect(work.centerx - 85, work.y + 492, 170, 38)
        if self.ui.button(self.screen_surface, swap, "SWAP SIDES", self.mouse, self.clicked, bool(left or right), COLORS["border"], "small"):
            self.mixer_left, self.mixer_right = self.mixer_right, self.mixer_left
        self.ui.text(self.screen_surface, f"FIELD NOTES  •  {len(self.hero.discovered_recipes)} RECIPES FOUND", (work.x + 42, work.y + 555), COLORS["muted"], "tiny")
        rules = [
            "Hold an item, then drag it into either socket.",
            "Every complete pair creates a unique visible fusion.",
            "Compatible power transfers; cosmetic fusions still survive.",
        ]
        for i, rule in enumerate(rules):
            pygame.draw.circle(self.screen_surface, (153, 93, 169), (work.x + 48, work.y + 589 + i * 27), 4)
            self.ui.text(self.screen_surface, rule, (work.x + 61, work.y + 578 + i * 27), COLORS["text"], "small")
        recipes = pygame.Rect(work.right - 226, work.bottom - 56, 186, 40)
        if self.ui.button(self.screen_surface, recipes, "RECIPE BOOK", self.mouse, self.clicked, True, COLORS["gold"], "small"):
            self.screen = Screen.RECIPES
        if self.ui.button(self.screen_surface, pygame.Rect(30, 861, 210, 59), "BACK", self.mouse, self.clicked, True, COLORS["border"], "medium"):
            self.screen = self.return_screen
            self.mixer_left = None
            self.mixer_right = None

    def draw_character(self):
        self.ui.draw_world_background(self.screen_surface, self.time)
        self.header("CHARACTER", "Levels provide a little health and one choice. Equipment still carries most of the build.")
        portrait = pygame.Rect(35, 125, 370, 705)
        sheet = pygame.Rect(425, 125, 740, 705)
        self.ui.ornamented_panel(self.screen_surface, portrait, (29, 27, 28), COLORS["blue"], 13, 2)
        self.ui.ornamented_panel(self.screen_surface, sheet, (31, 28, 27), COLORS["border"], 13, 2)
        scene = pygame.Rect(portrait.x + 14, portrait.y + 72, portrait.width - 28, 377)
        self.ui.draw_cavern(self.screen_surface, scene, Element.ARCANE, 1, self.time)
        pygame.draw.rect(self.screen_surface, COLORS["border_dark"], scene, 2, border_radius=8)
        self.ui.ribbon(self.screen_surface, pygame.Rect(portrait.x + 67, portrait.y + 18, portrait.width - 134, 36), self.hero.name.upper(), COLORS["blue"], "small")
        self.draw_hero(pygame.Vector2(portrait.centerx, portrait.y + 420), "idle", self.time, 1.18)
        level_seal = (portrait.centerx, portrait.y + 482)
        pygame.draw.circle(self.screen_surface, COLORS["ink"], level_seal, 43)
        pygame.draw.circle(self.screen_surface, COLORS["gold"], level_seal, 40, 3)
        self.ui.text(self.screen_surface, f"LV {self.hero.level}", level_seal, COLORS["gold"], "medium", "center")
        xp_rect = pygame.Rect(portrait.x + 38, portrait.y + 541, portrait.width - 76, 22)
        self.ui.bar(self.screen_surface, xp_rect, self.hero.experience, self.hero.xp_needed, (105, 92, 214), "XP")
        self.ui.text(self.screen_surface, f"{self.hero.stat_points} UNSPENT POINTS", (portrait.centerx, portrait.y + 585), COLORS["gold"] if self.hero.stat_points else COLORS["muted"], "small", "center")
        training = pygame.Rect(portrait.x + 38, portrait.y + 620, portrait.width - 76, 52)
        training_label = f"TRAIN +1 POINT  •  {self.hero.training_cost} DUST"
        if self.ui.button(self.screen_surface, training, training_label, self.mouse, self.clicked, self.hero.bone_dust >= self.hero.training_cost, (161, 96, 204), "small"):
            ok, cost = self.hero.train_with_dust()
            if ok:
                self.save()
                self.toast(f"Training converted {cost} bone dust into one stat point.")
        totals = self.hero.total_stats()
        colors = {"health": (210, 72, 83), "attack": (230, 143, 70), "defense": (83, 151, 226), "luck": (186, 105, 220)}
        descriptions = {"health": "Maximum health carried through every wave.", "attack": "Base force behind each automatic strike.", "defense": "Reduces damage before elemental resistance.", "luck": "Raises critical strike and complete block chance."}
        self.ui.ribbon(self.screen_surface, pygame.Rect(sheet.centerx - 145, sheet.y + 18, 290, 36), "THE FOUR MEASURES", COLORS["wood_light"], "small")
        for index, stat in enumerate(("health", "attack", "defense", "luck")):
            col, row_index = index % 2, index // 2
            row = pygame.Rect(sheet.x + 27 + col * 351, sheet.y + 77 + row_index * 258, 330, 232)
            self.ui.ornamented_panel(self.screen_surface, row, self.ui.blend((30, 27, 27), colors[stat], .055), self.ui.blend(colors[stat], COLORS["border"], .38), 11, 2)
            pygame.draw.circle(self.screen_surface, self.ui.blend(colors[stat], COLORS["ink"], .68), (row.x + 73, row.y + 83), 47)
            pygame.draw.circle(self.screen_surface, colors[stat], (row.x + 73, row.y + 83), 47, 3)
            self.ui.text(self.screen_surface, totals[stat], (row.x + 73, row.y + 83), colors[stat], "large", "center")
            self.ui.text(self.screen_surface, stat.upper(), (row.x + 143, row.y + 43), colors[stat], "medium")
            gear_bonus = totals[stat] - self.hero.base_stats[stat]
            self.ui.text(self.screen_surface, f"BASE {self.hero.base_stats[stat]}  •  GEAR {gear_bonus:+d}", (row.x + 144, row.y + 83), COLORS["text"], "tiny")
            self.ui.wrapped(self.screen_surface, descriptions[stat], pygame.Rect(row.x + 25, row.y + 146, row.width - 93, 46), COLORS["muted"], "small", 3, 2)
            plus = pygame.Rect(row.right - 58, row.bottom - 66, 43, 49)
            if self.ui.button(self.screen_surface, plus, "+", self.mouse, self.clicked, self.hero.stat_points > 0, colors[stat], "large"):
                if self.hero.spend_point(stat):
                    self.save()
                    self.toast(f"Raised {stat.upper()}.")
        self.ui.text(self.screen_surface, f"VICTORIES {self.hero.total_wins}   •   DEFEATS {self.hero.total_losses}   •   ENEMIES {self.hero.total_enemies}   •   ITEMS {len(self.hero.discovery)}", (sheet.centerx, sheet.bottom - 48), COLORS["muted"], "tiny", "center")
        if self.ui.button(self.screen_surface, pygame.Rect(30, 861, 210, 59), "BACK", self.mouse, self.clicked, True, COLORS["border"], "medium"):
            self.screen = self.return_screen

    def draw_recipes(self):
        self.ui.draw_world_background(self.screen_surface, self.time)
        self.header("RECIPE BOOK", f"The field rig remembers {len(self.hero.discovered_recipes)} of {len(RECIPES)} stable combinations.")
        panel = pygame.Rect(42, 120, 1116, 712)
        self.ui.ornamented_panel(self.screen_surface, panel, (70, 55, 42), COLORS["wood_light"], 13, 3)
        left_page = pygame.Rect(panel.x + 21, panel.y + 20, 523, panel.height - 40)
        right_page = pygame.Rect(panel.centerx + 14, panel.y + 20, 523, panel.height - 40)
        pygame.draw.rect(self.screen_surface, (55, 47, 39), left_page, border_radius=9)
        pygame.draw.rect(self.screen_surface, (55, 47, 39), right_page, border_radius=9)
        pygame.draw.line(self.screen_surface, (22, 18, 17), (panel.centerx, panel.y + 18), (panel.centerx, panel.bottom - 18), 12)
        pygame.draw.line(self.screen_surface, (129, 91, 54), (panel.centerx - 7, panel.y + 24), (panel.centerx - 7, panel.bottom - 24), 2)
        pygame.draw.line(self.screen_surface, (129, 91, 54), (panel.centerx + 7, panel.y + 24), (panel.centerx + 7, panel.bottom - 24), 2)
        self.ui.ribbon(self.screen_surface, pygame.Rect(left_page.centerx - 105, left_page.y + 10, 210, 31), "FIELD FORMULAE I", COLORS["wood_light"], "tiny")
        self.ui.ribbon(self.screen_surface, pygame.Rect(right_page.centerx - 105, right_page.y + 10, 210, 31), "FIELD FORMULAE II", COLORS["wood_light"], "tiny")
        entries = sorted(RECIPES.items(), key=lambda value: ITEM_TEMPLATES[value[1]]["tier"])
        rows_per_page = max(1, math.ceil(len(entries) / 2))
        row_step = min(60, max(42, (left_page.height - 60) // rows_per_page))
        for index, (ingredients, output) in enumerate(entries):
            col, row = divmod(index, rows_per_page)
            page = left_page if col == 0 else right_page
            rect = pygame.Rect(page.x + 14, page.y + 53 + row * row_step, page.width - 28, row_step - 6)
            key = f"{'+'.join(ingredients)}={output}"
            known = key in self.hero.discovered_recipes
            template = ITEM_TEMPLATES[output]
            color = ELEMENT_COLORS[template["element"]] if template["element"] != Element.NEUTRAL else ITEM_COLORS[template["kind"]]
            if not known:
                color = (86, 78, 69)
            pygame.draw.rect(self.screen_surface, (38, 34, 31), rect, border_radius=6)
            pygame.draw.rect(self.screen_surface, self.ui.blend(color, (83, 66, 49), .45), rect, 1, border_radius=6)
            seal = (rect.x + 27, rect.centery)
            seal_radius = min(17, max(13, rect.height // 2 - 3))
            pygame.draw.circle(self.screen_surface, (22, 20, 19), seal, seal_radius + 1)
            pygame.draw.circle(self.screen_surface, color, seal, seal_radius, 2)
            if known:
                left_name = ITEM_TEMPLATES[ingredients[0]]["name"]
                right_name = ITEM_TEMPLATES[ingredients[1]]["name"]
                output_name = ITEM_TEMPLATES[output]["name"]
                self.ui.text(self.screen_surface, "✓", seal, color, "small", "center")
                self.ui.fitted_text(self.screen_surface, f"{left_name} + {right_name}", pygame.Rect(rect.x + 55, rect.y + 2, rect.width - 66, rect.height // 2), COLORS["muted"], "tiny")
                self.ui.fitted_text(self.screen_surface, f"=>  {output_name}", pygame.Rect(rect.x + 55, rect.centery, rect.width - 66, rect.height // 2 - 1), color, "small")
            else:
                self.ui.text(self.screen_surface, "?", seal, color, "small", "center")
                self.ui.text(self.screen_surface, "Unknown pairing  =>  Unwritten result", (rect.x + 55, rect.centery), (112, 102, 92), "small", "midleft")
        if self.ui.button(self.screen_surface, pygame.Rect(40, 861, 220, 59), "BACK TO MIXER", self.mouse, self.clicked, True, COLORS["border"], "medium"):
            self.screen = Screen.MIXER

    def draw_hero(self, pos, anim, clock, scale=1.22):
        if anim == "defeat":
            display_anim = anim
        elif self.hero_critical_flash > 0:
            display_anim = "critical"
        elif self.hero_block_flash > 0:
            display_anim = "guard"
        elif self.hero_hit_flash > 0:
            display_anim = "hurt"
        else:
            display_anim = anim
        elapsed = self.animation_elapsed("hero", display_anim, clock)
        bob = round(math.sin(clock * 2.4) * scale) if anim in {"idle", "ready", "victory"} else 0
        x, y = pos.x, pos.y + bob
        sprite = self.sprites.frame("hero", display_anim, elapsed, round(330 * scale))
        if sprite:
            pygame.draw.ellipse(self.screen_surface, (3, 6, 10), (x - sprite.get_width() * .34, y + 7, sprite.get_width() * .68, 17 * scale))
            if anim == "victory":
                halo = pygame.Surface((round(210 * scale), round(210 * scale)), pygame.SRCALPHA)
                pygame.draw.circle(halo, (226, 174, 79, 34), halo.get_rect().center, round(82 * scale))
                pygame.draw.circle(halo, (226, 174, 79, 120), halo.get_rect().center, round(82 * scale), 2)
                self.screen_surface.blit(halo, halo.get_rect(center=(round(x), round(y - sprite.get_height() * .52))))
            if self.sprites.hero_pixel:
                source_ground = self.sprites.hero_ground or (64 if display_anim in {"walk", "run", "hurt", "guard"} else 80)
                pixel_scale = round(330 * scale) / 96
                rect = sprite.get_rect()
                rect.centerx = round(x)
                rect.y = round(y + 8 * scale - source_ground * pixel_scale)
            else:
                rect = sprite.get_rect(midbottom=(round(x), round(y + 15 * scale)))
            weapon = self.hero.equipment.get("weapon") if self.hero else None
            if weapon and weapon.element != Element.NEUTRAL:
                weapon_color = ELEMENT_COLORS[weapon.element]
                power = min(1.0, .35 + weapon.element_power / 35)
                focus = (round(rect.x + rect.width * .70), round(rect.y + rect.height * .49))
                aura = pygame.Surface((180, 170), pygame.SRCALPHA)
                local_focus = (88, 84)
                pygame.draw.circle(aura, (*weapon_color, round(24 + 30 * power)), local_focus, round(28 + 18 * power), 3)
                for index in range(4):
                    angle = self.time * (1.7 + index * .13) + index * math.tau / 4
                    radius = 25 + index * 6
                    point = (round(local_focus[0] + math.cos(angle) * radius), round(local_focus[1] + math.sin(angle) * radius * .72))
                    pygame.draw.circle(aura, (*weapon_color, round(135 * power)), point, 2 + index % 2)
                if display_anim in {"attack", "critical"}:
                    pygame.draw.arc(aura, (*weapon_color, round(210 * power)), pygame.Rect(local_focus[0] - 65, local_focus[1] - 68, 140, 130), -.95, .68, 5 if display_anim == "critical" else 3)
                self.screen_surface.blit(aura, (focus[0] - local_focus[0], focus[1] - local_focus[1]))
            if self.hero_hit_flash > 0 and anim != "defeat":
                flash = sprite.copy()
                flash.fill((95, 65, 70, 0), special_flags=pygame.BLEND_RGB_ADD)
                self.screen_surface.blit(flash, rect)
            else:
                self.screen_surface.blit(sprite, rect)
            self.draw_equipped_gear(rect, display_anim, elapsed)
            return
        if anim == "defeat":
            y += 45 * scale
        skin = (222, 184, 143)
        blue = (50, 123, 191)
        dark_blue = (29, 74, 122)
        boot = (44, 37, 34)
        pygame.draw.ellipse(self.screen_surface, (5, 6, 9), (x - 66 * scale, y + 13 * scale, 132 * scale, 30 * scale))
        if anim == "victory":
            pygame.draw.circle(self.screen_surface, (238, 190, 64), (round(x), round(y - 118 * scale)), round(58 * scale), 3)
        cape = [(x - 31 * scale, y - 101 * scale), (x - 54 * scale, y - 15 * scale), (x - 8 * scale, y - 27 * scale), (x + 24 * scale, y - 92 * scale)]
        pygame.draw.polygon(self.screen_surface, dark_blue, cape)
        pygame.draw.line(self.screen_surface, boot, (x - 18 * scale, y - 29 * scale), (x - 35 * scale, y + 18 * scale), round(15 * scale))
        pygame.draw.line(self.screen_surface, boot, (x + 17 * scale, y - 29 * scale), (x + 39 * scale, y + 18 * scale), round(15 * scale))
        pygame.draw.line(self.screen_surface, (81, 57, 41), (x - 47 * scale, y + 18 * scale), (x - 24 * scale, y + 18 * scale), round(11 * scale))
        pygame.draw.line(self.screen_surface, (81, 57, 41), (x + 29 * scale, y + 18 * scale), (x + 51 * scale, y + 18 * scale), round(11 * scale))
        torso = [(x - 34 * scale, y - 103 * scale), (x + 30 * scale, y - 103 * scale), (x + 43 * scale, y - 31 * scale), (x - 41 * scale, y - 31 * scale)]
        pygame.draw.polygon(self.screen_surface, blue, torso)
        pygame.draw.polygon(self.screen_surface, (80, 159, 218), torso, max(2, round(3 * scale)))
        pygame.draw.rect(self.screen_surface, (111, 72, 45), (x - 40 * scale, y - 52 * scale, 82 * scale, 11 * scale), border_radius=round(4 * scale))
        head = (round(x), round(y - 133 * scale))
        pygame.draw.circle(self.screen_surface, (242, 239, 218), head, round(34 * scale))
        pygame.draw.rect(self.screen_surface, (242, 239, 218), (x - 35 * scale, y - 143 * scale, 70 * scale, 21 * scale), border_radius=round(8 * scale))
        pygame.draw.circle(self.screen_surface, skin, (round(x), round(y - 128 * scale)), round(23 * scale))
        pygame.draw.circle(self.screen_surface, (27, 29, 33), (round(x + 7 * scale), round(y - 132 * scale)), max(2, round(2 * scale)))
        pygame.draw.line(self.screen_surface, (98, 66, 48), (x + 4 * scale, y - 118 * scale), (x + 13 * scale, y - 116 * scale), max(1, round(2 * scale)))
        shield = self.hero.equipment.get("shield") if self.hero else None
        shield_color = self.ui.item_color(shield) if shield else (91, 116, 135)
        left_hand = (x - 52 * scale, y - 67 * scale)
        pygame.draw.line(self.screen_surface, skin, (x - 27 * scale, y - 89 * scale), left_hand, round(12 * scale))
        shield_points = [(left_hand[0] - 26 * scale, left_hand[1] - 31 * scale), (left_hand[0] + 20 * scale, left_hand[1] - 20 * scale), (left_hand[0] + 18 * scale, left_hand[1] + 25 * scale), (left_hand[0] - 8 * scale, left_hand[1] + 43 * scale), (left_hand[0] - 33 * scale, left_hand[1] + 20 * scale)]
        pygame.draw.polygon(self.screen_surface, self.ui.blend(shield_color, COLORS["ink"], .48), shield_points)
        pygame.draw.polygon(self.screen_surface, shield_color, shield_points, max(2, round(4 * scale)))
        right_hand = (x + 52 * scale, y - 69 * scale)
        pygame.draw.line(self.screen_surface, skin, (x + 26 * scale, y - 88 * scale), right_hand, round(12 * scale))
        weapon = self.hero.equipment.get("weapon") if self.hero else None
        blade_color = self.ui.item_color(weapon) if weapon else (207, 215, 226)
        blade_end = (x + 103 * scale, y - (116 if anim == "attack" else 107) * scale)
        pygame.draw.line(self.screen_surface, (89, 59, 39), (right_hand[0] - 5 * scale, right_hand[1] + 7 * scale), (right_hand[0] + 12 * scale, right_hand[1] - 10 * scale), round(8 * scale))
        pygame.draw.line(self.screen_surface, (229, 225, 210), right_hand, blade_end, round(10 * scale))
        pygame.draw.line(self.screen_surface, blade_color, (right_hand[0] + 5 * scale, right_hand[1] - 4 * scale), blade_end, round(4 * scale))
        pygame.draw.line(self.screen_surface, (111, 76, 43), (right_hand[0] - 13 * scale, right_hand[1] - 12 * scale), (right_hand[0] + 13 * scale, right_hand[1] + 12 * scale), round(6 * scale))
        if anim == "attack":
            arc = pygame.Rect(x + 24 * scale, y - 158 * scale, 122 * scale, 122 * scale)
            pygame.draw.arc(self.screen_surface, (*blade_color,), arc, -.8, 1.4, max(2, round(5 * scale)))

    def draw_equipped_gear(self, hero_rect, anim, elapsed):
        """Lock the exact inventory artwork to the animated hands at its grip."""
        if not self.hero or anim in {"hurt", "defeat"}:
            return
        weapon = self.hero.equipment.get("weapon")
        shield = self.hero.equipment.get("shield")
        unit = hero_rect.height / 96
        pose = {"walk": "run", "ready": "idle"}.get(anim, anim)
        counts = {"idle": 6, "run": 8, "attack": 8, "critical": 10, "guard": 5, "victory": 6}
        speeds = {"idle": 5.0, "run": 12.0, "attack": 16.0, "critical": 18.0, "guard": 12.0, "victory": 7.0}
        count = counts.get(pose, 1)
        cursor = max(0, int(elapsed * speeds.get(pose, 1.0)))
        frame = min(count - 1, cursor) if pose in {"attack", "critical", "guard"} else cursor % count

        idle_bob = (0, 0, -1, -1, -1, 0)
        run_phase = (0, .72, 1, .58, 0, -.72, -1, -.58)
        run_bob = (0, -1, -2, -1, 0, -1, -2, -1)
        attack_right = ((64, 44), (54, 32), (48, 24), (62, 26), (80, 40), (94, 54), (88, 60), (72, 48))
        attack_left = ((26, 56), (22, 56), (20, 54), (24, 52), (32, 54), (40, 56), (38, 58), (30, 56))
        critical_right = ((62, 48), (52, 36), (42, 24), (38, 16), (50, 14), (74, 24), (98, 44), (104, 60), (88, 60), (70, 48))
        critical_left = ((24, 60), (20, 60), (16, 58), (14, 54), (18, 50), (28, 48), (40, 54), (44, 58), (38, 60), (28, 58))
        guard_right = ((64, 56), (66, 58), (68, 60), (68, 60), (66, 58))
        guard_left = ((48, 52), (56, 50), (64, 48), (66, 48), (56, 50))
        victory_bob = (0, -2, -3, -3, -2, 0)

        if pose == "attack":
            right_hand, left_hand = attack_right[frame], attack_left[frame]
            angle = (0, 34, 67, 82, 54, 12, -42, -10)[frame]
            shield_angle = (-4, -2, 1, 4, 7, 5, 1, -3)[frame]
        elif pose == "critical":
            right_hand, left_hand = critical_right[frame], critical_left[frame]
            angle = (-4, 30, 62, 92, 118, 92, 46, -12, -72, -10)[frame]
            shield_angle = (-5, -3, 0, 3, 6, 9, 8, 4, 0, -4)[frame]
        elif pose == "guard":
            right_hand, left_hand = guard_right[frame], guard_left[frame]
            angle = -48
            shield_angle = (-4, -9, -13, -15, -8)[frame]
        elif pose == "run":
            phase = run_phase[frame]
            bob = run_bob[frame]
            right_hand = ((32 + round(4 * phase)) * 2, (25 + bob - round(3 * phase)) * 2)
            left_hand = ((16 + round(4 * phase)) * 2, (25 + bob + round(3 * phase)) * 2)
            angle = -12 + phase * 8
            shield_angle = phase * -5
        elif pose == "victory":
            bob = victory_bob[frame]
            right_hand, left_hand = (58, (10 + bob) * 2), (26, (21 + bob) * 2)
            angle = 44 + math.sin(elapsed * 2.8) * 3
            shield_angle = -5 + math.sin(elapsed * 2.8) * 3
        else:
            bob = idle_bob[frame % len(idle_bob)]
            drift = ((0, 0), (0, -1), (1, -1), (1, 0), (0, 1), (0, 0))[frame % 6]
            right_hand = ((34 + drift[0]) * 2, (24 + bob + drift[1]) * 2)
            left_hand = ((14 - drift[0]) * 2, (27 + bob - drift[1]) * 2)
            angle = (-18, -17, -16, -17, -18, -19)[frame % 6]
            shield_angle = (-4, -2, 0, 2, 0, -2)[frame % 6]

        right_grip = (hero_rect.x + right_hand[0] * unit, hero_rect.y + right_hand[1] * unit)
        left_grip = (hero_rect.x + left_hand[0] * unit, hero_rect.y + left_hand[1] * unit)

        def blit_at_grip(image, grip, rotation):
            pivot = pygame.Vector2(image.get_width() * .10, image.get_height() * .89)
            center = pygame.Vector2(image.get_rect().center)
            rotated = pygame.transform.rotate(image, rotation)
            rotated_center = pygame.Vector2(grip) + (center - pivot).rotate(-rotation)
            self.screen_surface.blit(rotated, rotated.get_rect(center=(round(rotated_center.x), round(rotated_center.y))))

        if shield:
            side = max(24, round((27 if pose == "guard" else 24) * unit))
            image = self.ui.item_sprite(shield, side, crop=True)
            if image:
                shield_center = (left_grip[0] - 2 * unit, left_grip[1] + 2 * unit)
                rotated = pygame.transform.rotate(image, shield_angle)
                self.screen_surface.blit(rotated, rotated.get_rect(center=(round(shield_center[0]), round(shield_center[1]))))
                # The fist and leather brace sit over the shield, making it
                # visually held instead of floating beside the character.
                hand_radius = max(2, round(1.7 * unit))
                pygame.draw.line(self.screen_surface, (38, 28, 27),
                                 (left_grip[0] - 3 * unit, left_grip[1] + unit),
                                 (left_grip[0] + 3 * unit, left_grip[1] - unit),
                                 max(2, round(1.1 * unit)))
                pygame.draw.circle(self.screen_surface, (34, 27, 27), (round(left_grip[0]), round(left_grip[1])), hand_radius + 1)
                pygame.draw.circle(self.screen_surface, (74, 51, 42), (round(left_grip[0]), round(left_grip[1])), hand_radius)
                pygame.draw.line(self.screen_surface, (142, 99, 61),
                                 (left_grip[0] - unit, left_grip[1] - unit),
                                 (left_grip[0] + unit, left_grip[1]),
                                 max(1, round(unit * .55)))
        if weapon:
            side = max(31, round(30 * unit))
            image = self.ui.item_sprite(weapon, side, crop=True)
            if not image:
                return
            blit_at_grip(image, right_grip, angle)
            hand_radius = max(2, round(1.65 * unit))
            pygame.draw.circle(self.screen_surface, (34, 27, 27), (round(right_grip[0]), round(right_grip[1])), hand_radius + 1)
            pygame.draw.circle(self.screen_surface, (74, 51, 42), (round(right_grip[0]), round(right_grip[1])), hand_radius)
            pygame.draw.circle(self.screen_surface, (126, 83, 53), (round(right_grip[0] - unit * .4), round(right_grip[1] - unit * .4)), max(1, round(unit * .45)))

    def draw_enemy(self, pos, enemy, anim, clock):
        color = ELEMENT_COLORS[enemy.element]
        elapsed = self.animation_elapsed("enemy", anim, clock)
        dying = anim == "defeat"
        bob = math.sin(clock * 2.4 + 1) * 3 if anim in {"idle", "ready"} and not dying else 0
        attack_progress = min(1.0, elapsed / .52)
        lunge = 0.0
        if anim == "attack":
            if attack_progress < .22:
                lunge = 11 * (attack_progress / .22)
            elif attack_progress < .58:
                strike = (attack_progress - .22) / .36
                lunge = 11 - 62 * (1 - (1 - strike) ** 3)
            else:
                recover = (attack_progress - .58) / .42
                lunge = -51 * (1 - recover) ** 2
        hit_kick = 12 * min(1.0, self.enemy_hit_flash / .16) if self.enemy_hit_flash > 0 and not dying else 0
        x, y = pos.x + lunge + hit_kick, pos.y + bob
        height = 370 if enemy.boss else 345 if enemy.elite else 320
        size_scale = {
            "dust_rat": .72, "bone_scout": .76, "crypt_slinger": .78,
            "marrow_guard": .84, "ossuary_captain": .88, "cinder_imp": .72,
            "ash_hound": .74, "furnace_knight": .88, "coal_oracle": .78,
            "pyre_warden": .88, "rime_widow": .74, "icebound_thrall": .82,
            "thunder_crow": .72, "hail_sentinel": .86, "tempest_matriarch": .88,
            "mire_leech": .70, "plague_duelist": .82, "hex_moth": .72,
            "rune_golem": .90, "alchemist_revenant": .88, "void_acolyte": .80,
            "crownless_guard": .86, "starved_dragon": .86, "oathbreaker": .86,
            "hollow_sovereign": .88,
        }.get(enemy.enemy_id, 1.0)
        height = round(height * size_scale)
        max_width = 460 if enemy.boss else 420
        sprite = self.sprites.frame("enemy", anim, elapsed, height, enemy.enemy_id, max_width)
        if sprite:
            # Several source actors use near-black cloaks and armor. Against the
            # dungeon backdrop those pixels looked transparent, even though the
            # sprite was fully inside the battle frame. Lift the palette very
            # slightly and add a crisp elemental rim at render time.
            sprite = sprite.copy()
            palette_lift = tuple(12 + round(channel * .055) for channel in color)
            sprite.fill((*palette_lift, 0), special_flags=pygame.BLEND_RGB_ADD)
            death_progress = min(1.0, elapsed / .88) if dying else 0.0
            death_flash = max(0.0, 1.0 - abs(death_progress - .16) / .16) if dying else 0.0
            fade = max(0.0, 1.0 - max(0.0, death_progress - .22) / .78) if dying else 1.0
            if dying:
                fall = death_progress * death_progress * (3 - 2 * death_progress)
                sprite = pygame.transform.rotate(sprite, -67 * fall)
                if death_progress > .46:
                    collapse = (death_progress - .46) / .54
                    collapsed_height = max(8, round(sprite.get_height() * (1 - collapse * .48)))
                    sprite = pygame.transform.scale(sprite, (sprite.get_width(), collapsed_height))
            elif anim == "attack":
                impact = math.sin(min(1.0, attack_progress) * math.pi)
                attack_width = max(1, round(sprite.get_width() * (1 + impact * .10)))
                attack_height = max(1, round(sprite.get_height() * (1 - impact * .055)))
                sprite = pygame.transform.scale(sprite, (attack_width, attack_height))
                sprite = pygame.transform.rotate(sprite, 7 * impact)
            elif anim == "ready":
                charge = (math.sin(elapsed * 14) + 1) * .5
                sprite = pygame.transform.scale(sprite, (max(1, round(sprite.get_width() * (1 + charge * .025))), max(1, round(sprite.get_height() * (1 + charge * .025)))))
            flyers = {"thunder_crow", "hex_moth", "rime_widow", "tempest_matriarch", "coal_oracle", "hollow_sovereign"}
            render_y = y - (74 if enemy.enemy_id in flyers else 0)
            rect = sprite.get_rect(midbottom=(round(x), round(render_y + 18)))
            if self.battle and self.battle.phase != "approach":
                safe_frame = pygame.Rect(504, 202, 657, 406)
                fit = min(1.0, safe_frame.width / max(1, rect.width), safe_frame.height / max(1, rect.height))
                if fit < 1.0:
                    sprite = pygame.transform.scale(sprite, (max(1, round(sprite.get_width() * fit)), max(1, round(sprite.get_height() * fit))))
                    rect = sprite.get_rect(midbottom=(round(x), round(render_y + 18)))
                rect.clamp_ip(safe_frame)
            shadow_width = max(46, round(sprite.get_width() * .72))
            shadow = pygame.Surface((shadow_width, 36), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow, (4, 5, 7, round(255 * fade)), shadow.get_rect())
            body_center_x = rect.centerx
            self.screen_surface.blit(shadow, (body_center_x - shadow_width / 2, y - 4))
            if not dying:
                aura_size = (sprite.get_width() + 40, sprite.get_height() + 40)
                aura_position = (rect.centerx - aura_size[0] / 2, rect.top - 20)
                aura = pygame.Surface(aura_size, pygame.SRCALPHA)
                pygame.draw.ellipse(aura, (*color, 42 if enemy.boss else 27), aura.get_rect().inflate(-12, -12), 7 if enemy.boss else 4)
                self.screen_surface.blit(aura, aura_position)
                if anim == "ready":
                    charge = (math.sin(elapsed * 15) + 1) * .5
                    ring = pygame.Surface((sprite.get_width() + 70, 42), pygame.SRCALPHA)
                    pygame.draw.ellipse(ring, (*color, round(80 + 90 * charge)), ring.get_rect().inflate(-8, -12), max(2, round(2 + charge * 3)))
                    self.screen_surface.blit(ring, (rect.centerx - ring.get_width() / 2, y - 8))
            enemy_mask = pygame.mask.from_surface(sprite, 8)
            rim_color = self.ui.blend(color, COLORS["text"], .34)
            rim = pygame.Surface(sprite.get_size(), pygame.SRCALPHA)
            enemy_mask.to_surface(
                rim,
                setcolor=(*rim_color, round((132 if enemy.boss else 112) * fade)),
                unsetcolor=(0, 0, 0, 0),
            )
            rim_width = max(2, min(4, round(sprite.get_height() / 105)))
            for offset_x, offset_y in (
                (-rim_width, 0), (rim_width, 0), (0, -rim_width), (0, rim_width),
                (-rim_width, -rim_width), (rim_width, -rim_width),
                (-rim_width, rim_width), (rim_width, rim_width),
            ):
                self.screen_surface.blit(rim, rect.move(offset_x, offset_y))
            if dying:
                body = sprite.copy()
                body.set_alpha(round(255 * fade))
                white = sprite.copy()
                white.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_MAX)
                white.set_alpha(round(105 * fade * death_flash))
                self.screen_surface.blit(body, rect)
                self.screen_surface.blit(white, rect)
            elif self.enemy_hit_flash > 0:
                flash = sprite.copy()
                flash.fill((110, 70, 70, 0), special_flags=pygame.BLEND_RGB_ADD)
                self.screen_surface.blit(flash, rect)
            else:
                self.screen_surface.blit(sprite, rect)
            if anim == "attack" and .28 < attack_progress < .82 and not dying:
                slash = pygame.Surface((190, 170), pygame.SRCALPHA)
                slash_alpha = round(210 * math.sin((attack_progress - .28) / .54 * math.pi))
                pygame.draw.arc(slash, (*color, slash_alpha), pygame.Rect(20, 14, 150, 142), 2.30, 4.05, 6 if enemy.boss else 4)
                pygame.draw.arc(slash, (255, 242, 218, slash_alpha), pygame.Rect(29, 23, 132, 124), 2.30, 4.05, 2)
                self.screen_surface.blit(slash, (rect.left - 104, rect.centery - 85))
            if (enemy.elite or enemy.boss) and not dying:
                pygame.draw.circle(self.screen_surface, color, (rect.centerx, rect.y + 36), 9 if enemy.boss else 6, 2)
            return
        scale = 1.52 if enemy.boss else 1.30 if enemy.elite else 1.18
        if self.draw_enemy_variant(x, y, enemy, anim, clock, scale):
            return
        bone = self.ui.blend((216, 210, 184), color, .10)
        dark = self.ui.blend(color, COLORS["ink"], .62)
        pygame.draw.ellipse(self.screen_surface, (4, 5, 7), (x - 70 * scale, y + 13 * scale, 140 * scale, 30 * scale))
        if enemy.elite or enemy.boss:
            aura = pygame.Surface((220, 240), pygame.SRCALPHA)
            pygame.draw.circle(aura, (*color, 28), (110, 125), round(78 + math.sin(clock * 2) * 5), 5)
            self.screen_surface.blit(aura, (x - 110, y - 210))
        pygame.draw.line(self.screen_surface, bone, (x - 15 * scale, y - 80 * scale), (x - 26 * scale, y + 16 * scale), round(11 * scale))
        pygame.draw.line(self.screen_surface, bone, (x + 15 * scale, y - 80 * scale), (x + 31 * scale, y + 16 * scale), round(11 * scale))
        pygame.draw.line(self.screen_surface, bone, (x - 40 * scale, y - 24 * scale), (x - 26 * scale, y + 16 * scale), round(8 * scale))
        pygame.draw.line(self.screen_surface, bone, (x + 40 * scale, y - 24 * scale), (x + 31 * scale, y + 16 * scale), round(8 * scale))
        pygame.draw.line(self.screen_surface, bone, (x, y - 122 * scale), (x, y - 53 * scale), round(12 * scale))
        for rib in range(4):
            rib_y = y - (105 - rib * 14) * scale
            pygame.draw.arc(self.screen_surface, bone, pygame.Rect(x - 38 * scale, rib_y, 76 * scale, 26 * scale), 0, math.pi, max(2, round(5 * scale)))
        skull = (round(x), round(y - 151 * scale))
        pygame.draw.circle(self.screen_surface, bone, skull, round(31 * scale))
        pygame.draw.rect(self.screen_surface, bone, (x - 23 * scale, y - 151 * scale, 46 * scale, 35 * scale), border_radius=round(8 * scale))
        pygame.draw.circle(self.screen_surface, dark, (round(x - 11 * scale), round(y - 157 * scale)), round(7 * scale))
        pygame.draw.circle(self.screen_surface, dark, (round(x + 11 * scale), round(y - 157 * scale)), round(7 * scale))
        pygame.draw.circle(self.screen_surface, color, (round(x - 11 * scale), round(y - 157 * scale)), max(2, round(3 * scale)))
        pygame.draw.circle(self.screen_surface, color, (round(x + 11 * scale), round(y - 157 * scale)), max(2, round(3 * scale)))
        for tooth in range(4):
            tx = x - 15 * scale + tooth * 10 * scale
            pygame.draw.line(self.screen_surface, dark, (tx, y - 127 * scale), (tx, y - 117 * scale), max(1, round(2 * scale)))
        if enemy.boss:
            pygame.draw.polygon(self.screen_surface, color, [(x - 23 * scale, y - 174 * scale), (x - 39 * scale, y - 213 * scale), (x - 4 * scale, y - 181 * scale)])
            pygame.draw.polygon(self.screen_surface, color, [(x + 23 * scale, y - 174 * scale), (x + 39 * scale, y - 213 * scale), (x + 4 * scale, y - 181 * scale)])
        left_hand = (x - 58 * scale, y - 74 * scale)
        right_hand = (x + 58 * scale, y - 76 * scale)
        pygame.draw.line(self.screen_surface, bone, (x - 16 * scale, y - 111 * scale), left_hand, round(9 * scale))
        pygame.draw.line(self.screen_surface, bone, (x + 16 * scale, y - 109 * scale), right_hand, round(9 * scale))
        if self.battle.enemy_has("guarded"):
            points = [(left_hand[0] - 29 * scale, left_hand[1] - 34 * scale), (left_hand[0] + 18 * scale, left_hand[1] - 23 * scale), (left_hand[0] + 15 * scale, left_hand[1] + 31 * scale), (left_hand[0] - 12 * scale, left_hand[1] + 47 * scale), (left_hand[0] - 35 * scale, left_hand[1] + 21 * scale)]
            pygame.draw.polygon(self.screen_surface, dark, points)
            pygame.draw.polygon(self.screen_surface, color, points, 4)
        pygame.draw.line(self.screen_surface, (78, 58, 43), right_hand, (right_hand[0] + 14 * scale, right_hand[1] - 12 * scale), round(9 * scale))
        pygame.draw.line(self.screen_surface, color, (right_hand[0] + 8 * scale, right_hand[1] - 7 * scale), (right_hand[0] + 77 * scale, right_hand[1] - 72 * scale), round(8 * scale))

    def draw_enemy_variant(self, x, y, enemy, anim, clock, scale):
        """Distinct silhouettes for beasts, flyers, constructs and humanoids."""
        eid = enemy.enemy_id
        color = ELEMENT_COLORS[enemy.element]
        dark = self.ui.blend(color, COLORS["ink"], .62)
        light = self.ui.blend(color, COLORS["text"], .24)
        bob = math.sin(clock * 3.1) * 3
        if eid in {"dust_rat", "ash_hound", "mire_leech", "starved_dragon"}:
            body_w = (122 if eid == "starved_dragon" else 88) * scale
            body_h = (52 if eid != "mire_leech" else 38) * scale
            pygame.draw.ellipse(self.screen_surface, (3, 5, 8), (x - body_w * .56, y + 11, body_w * 1.12, 25 * scale))
            pygame.draw.ellipse(self.screen_surface, dark, (x - body_w / 2, y - body_h, body_w, body_h))
            head_x = x - body_w * .47
            pygame.draw.circle(self.screen_surface, light, (round(head_x), round(y - body_h * .72)), round(body_h * .36))
            for leg_x in (-.32, -.08, .22, .39):
                pygame.draw.line(self.screen_surface, light, (x + body_w * leg_x, y - 12 * scale), (x + body_w * leg_x - 8 * scale, y + 14 * scale), max(4, round(7 * scale)))
            pygame.draw.circle(self.screen_surface, color, (round(head_x - 8 * scale), round(y - body_h * .78)), max(2, round(3 * scale)))
            if eid == "starved_dragon":
                pygame.draw.polygon(self.screen_surface, dark, [(x, y - body_h), (x + 15 * scale, y - 120 * scale), (x + 50 * scale, y - body_h)], 0)
                pygame.draw.polygon(self.screen_surface, dark, [(x + 28 * scale, y - body_h), (x + 62 * scale, y - 110 * scale), (x + 75 * scale, y - body_h)], 0)
            return True
        if eid in {"thunder_crow", "hex_moth", "rime_widow", "tempest_matriarch"}:
            center = (round(x), round(y - 92 * scale + bob))
            wing = 66 * scale
            pygame.draw.polygon(self.screen_surface, dark, [(center[0], center[1]), (center[0] - wing, center[1] - 36 * scale), (center[0] - 42 * scale, center[1] + 30 * scale)])
            pygame.draw.polygon(self.screen_surface, dark, [(center[0], center[1]), (center[0] + wing, center[1] - 36 * scale), (center[0] + 42 * scale, center[1] + 30 * scale)])
            pygame.draw.ellipse(self.screen_surface, light, (center[0] - 19 * scale, center[1] - 31 * scale, 38 * scale, 67 * scale))
            pygame.draw.circle(self.screen_surface, color, center, max(3, round(6 * scale)))
            return True
        if eid in {"hail_sentinel", "rune_golem", "furnace_knight", "pyre_warden"}:
            pygame.draw.ellipse(self.screen_surface, (3, 5, 8), (x - 72 * scale, y + 8, 144 * scale, 28 * scale))
            torso = pygame.Rect(x - 45 * scale, y - 142 * scale, 90 * scale, 119 * scale)
            pygame.draw.rect(self.screen_surface, dark, torso, border_radius=round(18 * scale))
            pygame.draw.rect(self.screen_surface, color, torso, max(3, round(5 * scale)), border_radius=round(18 * scale))
            pygame.draw.circle(self.screen_surface, light, (round(x), round(y - 169 * scale)), round(29 * scale))
            pygame.draw.circle(self.screen_surface, color, (round(x), round(y - 169 * scale)), round(10 * scale))
            for side in (-1, 1):
                pygame.draw.line(self.screen_surface, dark, (x + side * 39 * scale, y - 117 * scale), (x + side * 66 * scale, y - 45 * scale), round(16 * scale))
                pygame.draw.line(self.screen_surface, dark, (x + side * 24 * scale, y - 28 * scale), (x + side * 36 * scale, y + 14 * scale), round(19 * scale))
            return True
        if eid in {"cinder_imp", "coal_oracle", "icebound_thrall", "plague_duelist", "alchemist_revenant", "void_acolyte", "oathbreaker", "hollow_sovereign"}:
            pygame.draw.ellipse(self.screen_surface, (3, 5, 8), (x - 65 * scale, y + 10, 130 * scale, 26 * scale))
            cloak = [(x, y - 155 * scale), (x - 48 * scale, y + 10 * scale), (x + 48 * scale, y + 10 * scale)]
            pygame.draw.polygon(self.screen_surface, dark, cloak)
            pygame.draw.lines(self.screen_surface, color, True, cloak, max(2, round(4 * scale)))
            pygame.draw.circle(self.screen_surface, light, (round(x), round(y - 171 * scale)), round(28 * scale))
            pygame.draw.rect(self.screen_surface, dark, (x - 25 * scale, y - 178 * scale, 50 * scale, 25 * scale), border_radius=round(8 * scale))
            pygame.draw.circle(self.screen_surface, color, (round(x - 9 * scale), round(y - 170 * scale)), max(2, round(4 * scale)))
            pygame.draw.circle(self.screen_surface, color, (round(x + 9 * scale), round(y - 170 * scale)), max(2, round(4 * scale)))
            if enemy.boss:
                pygame.draw.polygon(self.screen_surface, color, [(x - 27 * scale, y - 196 * scale), (x - 15 * scale, y - 225 * scale), (x, y - 201 * scale), (x + 15 * scale, y - 225 * scale), (x + 27 * scale, y - 196 * scale)], 3)
            return True
        return False

    def draw_battle(self):
        element_color = ELEMENT_COLORS[self.battle.enemy.element]
        stage_act = self.battle.stage.act
        scene = pygame.Rect(0, 0, WIDTH, 666)
        self.ui.draw_cavern(self.screen_surface, scene, self.battle.enemy.element, stage_act, self.battle.anim_clock)
        shake_x = math.sin(self.time * 211) * min(5, self.shake * 70) if self.shake > 0 else 0
        hero_plaque = pygame.Rect(26, 25, 430, 116)
        enemy_plaque = pygame.Rect(744, 25, 430, 116)
        self.ui.ornamented_panel(self.screen_surface, hero_plaque, (14, 22, 31), (55, 122, 177), 10, 1)
        self.ui.ornamented_panel(self.screen_surface, enemy_plaque, (25, 18, 23), self.ui.blend(element_color, COLORS["border"], .44), 10, 1)
        self.ui.text(self.screen_surface, self.hero.name, (hero_plaque.x + 20, hero_plaque.y + 15), (93, 172, 230), "medium")
        self.ui.text(self.screen_surface, f"LV {self.hero.level}", (hero_plaque.right - 18, hero_plaque.y + 20), COLORS["muted"], "tiny", "topright")
        self.ui.text(self.screen_surface, self.battle.enemy.name, (enemy_plaque.right - 20, enemy_plaque.y + 15), element_color, "medium", "topright")
        enemy_rank = "BOSS" if self.battle.enemy.boss else "ELITE" if self.battle.enemy.elite else self.battle.enemy.element.value.upper()
        self.ui.text(self.screen_surface, enemy_rank, (enemy_plaque.x + 18, enemy_plaque.y + 20), COLORS["muted"], "tiny")
        hero_health = pygame.Rect(hero_plaque.x + 20, hero_plaque.y + 54, hero_plaque.width - 40, 27)
        self.ui.bar(self.screen_surface, hero_health, self.battle.hero_hp, self.battle.hero_max_hp, (204, 57, 69), "HP")
        self.ui.bar(self.screen_surface, pygame.Rect(enemy_plaque.x + 20, enemy_plaque.y + 54, enemy_plaque.width - 40, 27), self.battle.enemy.hp, self.battle.enemy.max_hp, (204, 57, 69), "HP")
        barrier_text = f"   BARRIER {self.battle.hero_barrier}" if self.battle.hero_barrier else ""
        self.ui.text(self.screen_surface, f"ATK {self.battle.hero_attack}   DEF {self.battle.hero_defense}   LUCK {self.battle.hero_luck}{barrier_text}", (hero_plaque.x + 20, hero_plaque.y + 91), COLORS["muted"], "tiny")
        self.ui.text(self.screen_surface, f"ATK {self.battle.enemy.attack}   DEF {self.battle.enemy.defense}   LUCK {self.battle.enemy.luck}", (enemy_plaque.right - 20, enemy_plaque.y + 91), COLORS["muted"], "tiny", "topright")
        wave_plate = pygame.Rect(493, 25, 214, 91)
        self.ui.ornamented_panel(self.screen_surface, wave_plate, (16, 22, 30), self.ui.blend(COLORS["gold"], COLORS["border"], .42), 10, 1)
        self.ui.text(self.screen_surface, f"WAVE {self.battle.wave_number}/{self.battle.wave_total}", (wave_plate.centerx, wave_plate.y + 21), COLORS["gold"], "medium", "center", True)
        for index in range(self.battle.wave_total):
            pip_color = (84, 190, 116) if index < self.battle.defeated else element_color if index == self.battle.enemy_index else (67, 61, 59)
            x = wave_plate.centerx - (self.battle.wave_total - 1) * 13 + index * 26
            pygame.draw.circle(self.screen_surface, COLORS["ink"], (x, wave_plate.y + 66), 8)
            pygame.draw.circle(self.screen_surface, pip_color, (x, wave_plate.y + 66), 6)
        self.ui.text(self.screen_surface, f"ROUND {self.battle.turns}", (600, 131), COLORS["muted"], "tiny", "center")
        self.ui.ribbon(self.screen_surface, pygame.Rect(470, 158, 260, 31), self.battle.stage.name.upper(), self.ui.blend(element_color, COLORS["border"], .5), "tiny")
        hero_x = 330.0
        enemy_x = 875.0
        hero_scale = .76
        if self.battle.phase == "approach":
            duration = getattr(self.battle, "APPROACH_DURATION", 1.65)
            approach = max(0.0, min(1.0, 1.0 - self.battle.timer / duration))
            eased = 1.0 - (1.0 - approach) ** 1.75
            hero_start = -120 if self.battle.wave_number == 1 else 215
            hero_x = hero_start + (330 - hero_start) * eased
            enemy_x = 1280 + (875 - 1280) * eased
            hero_scale = .64 + .12 * eased
            entry_layer = pygame.Surface((WIDTH, 666), pygame.SRCALPHA)
            streak_alpha = round(75 * math.sin(approach * math.pi))
            for index in range(7):
                streak_y = 258 + index * 45 + math.sin(self.time * 5 + index) * 7
                pygame.draw.line(entry_layer, (124, 137, 151, streak_alpha), (0, streak_y), (150 + index * 31, streak_y), 2)
                pygame.draw.line(entry_layer, (*element_color, streak_alpha), (WIDTH - 160 - index * 23, streak_y + 18), (WIDTH, streak_y + 18), 2)
            self.screen_surface.blit(entry_layer, (0, 0))
            for index in range(9):
                dust_x = hero_x - 38 - index * 17 + (self.time * 120 % 22)
                dust_y = 589 + math.sin(self.time * 9 + index) * 3
                radius = max(1, 5 - index)
                pygame.draw.circle(self.screen_surface, (91, 78, 68), (round(dust_x), round(dust_y)), radius, 1)
            for index in range(7):
                dust_x = enemy_x + 34 + index * 18 - (self.time * 108 % 24)
                dust_y = 589 + math.sin(self.time * 8 + index * .7) * 3
                pygame.draw.circle(self.screen_surface, self.ui.blend(element_color, (89, 77, 67), .58), (round(dust_x), round(dust_y)), max(1, 4 - index // 2), 1)
        self.draw_hero(pygame.Vector2(hero_x + shake_x, 574), self.battle.hero_anim, self.battle.anim_clock, hero_scale)
        self.draw_enemy(pygame.Vector2(enemy_x - shake_x, 574), self.battle.enemy, self.battle.enemy_anim, self.battle.anim_clock)
        if self.hero_critical_flash > 0:
            strength = min(1.0, self.hero_critical_flash * 4)
            slash = pygame.Surface((WIDTH, 666), pygame.SRCALPHA)
            alpha = round(220 * strength)
            pygame.draw.arc(slash, (255, 231, 135, alpha), pygame.Rect(535, 265, 350, 260), -.75, .62, 12)
            pygame.draw.arc(slash, (255, 255, 235, alpha), pygame.Rect(550, 278, 320, 230), -.75, .62, 4)
            self.screen_surface.blit(slash, (0, 0))
            self.ui.text(self.screen_surface, "CRITICAL", (600, 218), (255, 211, 84), "large", "center", True)
        for burst in self.fx_bursts:
            burst.draw(self.screen_surface)
        for notice in self.float_notices:
            alpha = max(0, round(255 * (1 - notice.age / notice.duration)))
            image = self.ui.fonts["medium"].render(notice.text, True, notice.color)
            image.set_alpha(alpha)
            self.screen_surface.blit(image, image.get_rect(center=(notice.x, notice.y)))
        deck = pygame.Rect(0, 650, WIDTH, 310)
        pygame.draw.rect(self.screen_surface, (9, 14, 21), deck)
        pygame.draw.line(self.screen_surface, COLORS["border"], (0, deck.y), (WIDTH, deck.y), 2)
        loadout_rect = pygame.Rect(18, 674, 238, 258)
        bag_rect = pygame.Rect(270, 674, 590, 258)
        action_rect = pygame.Rect(874, 674, 308, 258)
        self.ui.ornamented_panel(self.screen_surface, loadout_rect, (16, 22, 30), COLORS["border_dark"], 10, 1)
        self.ui.ornamented_panel(self.screen_surface, bag_rect, (15, 21, 29), (48, 65, 81), 10, 1)
        self.ui.ornamented_panel(self.screen_surface, action_rect, (16, 23, 30), (57, 104, 80), 10, 1)
        self.ui.text(self.screen_surface, "EQUIPPED", (loadout_rect.x + 16, loadout_rect.y + 14), COLORS["muted"], "tiny")
        for index, slot in enumerate(("weapon", "shield", "ring1", "ring2")):
            item = self.hero.equipment[slot]
            icon_rect = pygame.Rect(loadout_rect.x + 14 + index * 53, loadout_rect.y + 43, 47, 63)
            slot_label = {"weapon": "W", "shield": "S", "ring1": "T1", "ring2": "T2"}[slot]
            self.ui.item_slot(self.screen_surface, icon_rect, item, self.mouse, False, False, slot_label)
        equipped_shield = self.hero.equipment.get("shield")
        shield_status = f"{equipped_shield.display_name}  •  +{equipped_shield.stats.get('defense', 0)} DEF" if equipped_shield else "NO SHIELD  •  FIRST SHIELD: DUNGEON 1"
        self.ui.fitted_text(self.screen_surface, shield_status, pygame.Rect(loadout_rect.x + 14, loadout_rect.y + 111, loadout_rect.width - 28, 18), self.ui.item_color(equipped_shield) if equipped_shield else (218, 132, 86), "tiny", "center")
        stats = (("ATK", self.battle.hero_attack, (230, 143, 70)), ("DEF", self.battle.hero_defense, (83, 151, 226)), ("LUCK", self.battle.hero_luck, (186, 105, 220)))
        for index, (label, value, color) in enumerate(stats):
            chip = pygame.Rect(loadout_rect.x + 14, loadout_rect.y + 126 + index * 40, loadout_rect.width - 28, 35)
            self.ui.stat_chip(self.screen_surface, chip, label, value, color)
        self.ui.text(self.screen_surface, "BATTLE PACK", (bag_rect.x + 18, bag_rect.y + 14), COLORS["muted"], "tiny")
        self.ui.text(self.screen_surface, "Drag: potion to boost  •  gear to mix", (bag_rect.right - 18, bag_rect.y + 14), COLORS["muted"], "tiny", "topright")
        for index in range(self.hero.inventory_capacity):
            row, col = divmod(index, 6)
            slot_rect = pygame.Rect(bag_rect.x + 17 + col * 94, bag_rect.y + 42 + row * 99, 84, 90)
            if index < len(self.hero.inventory):
                item = self.hero.inventory[index]
                active_item = (not self.battle.boost_used and self.hero.boost_uid == item.uid) or item.uid in {self.mixer_left, self.mixer_right}
                if self.ui.item_slot(self.screen_surface, slot_rect, item, self.mouse, self.clicked, active_item, str(index + 1)):
                    self.selected_uid = item.uid
                    if item.kind == ItemKind.POTION and not self.battle.boost_used:
                        self.mixer_left = None
                        self.mixer_right = None
                        ok, message = self.hero.set_boost(item.uid)
                        if ok:
                            self.save()
                        self.toast(message)
                    elif item.kind == ItemKind.POTION:
                        self.toast("The battle boost has already been used.")
                    else:
                        if item.uid == self.mixer_left and self.mixer_right is None and item.stack >= 2:
                            self.mixer_right = item.uid
                        elif item.uid == self.mixer_left:
                            self.mixer_left = None
                        elif item.uid == self.mixer_right:
                            self.mixer_right = None
                        elif self.mixer_left is None:
                            self.mixer_left = item.uid
                        elif self.mixer_right is None and (item.uid != self.mixer_left or item.stack >= 2):
                            self.mixer_right = item.uid
                        else:
                            self.mixer_left = item.uid
                            self.mixer_right = None
                        self.toast(f"Field mixer: {item.display_name} selected.")
            else:
                item = None
                self.ui.empty_card(self.screen_surface, slot_rect, str(index + 1), self.mouse, self.clicked)
            self.register_item_drag_zone(slot_rect, "inventory", item, index=index)
        boost = self.battle.selected_boost
        self.ui.text(self.screen_surface, "DUNGEON CHRONICLE", (action_rect.x + 16, action_rect.y + 14), COLORS["muted"], "tiny")
        y = action_rect.y + 38
        for event in list(self.battle.history)[-3:]:
            color = ELEMENT_COLORS[event.element] if event.element != Element.NEUTRAL else COLORS["text"]
            self.ui.fitted_text(self.screen_surface, "> " + event.text, pygame.Rect(action_rect.x + 16, y, action_rect.width - 32, 20), color, "tiny")
            y += 22
        pygame.draw.line(self.screen_surface, COLORS["border_dark"], (action_rect.x + 15, action_rect.y + 108), (action_rect.right - 15, action_rect.y + 108), 1)
        use = pygame.Rect(action_rect.x + 24, action_rect.y + 194, action_rect.width - 48, 43)
        left = self.hero.item_by_uid(self.mixer_left)
        right = self.hero.item_by_uid(self.mixer_right)
        if left or right:
            self.ui.text(self.screen_surface, "FIELD MIXER", (action_rect.x + 17, action_rect.y + 119), (192, 117, 218), "tiny")
            left_socket = pygame.Rect(action_rect.x + 18, action_rect.y + 139, 58, 48)
            right_socket = pygame.Rect(action_rect.x + 89, action_rect.y + 139, 58, 48)
            if self.ui.item_slot(self.screen_surface, left_socket, left, self.mouse, self.clicked, bool(left), "B"):
                self.mixer_left = None
            self.ui.text(self.screen_surface, "+", (action_rect.x + 82, action_rect.y + 162), COLORS["gold"], "small", "center")
            if self.ui.item_slot(self.screen_surface, right_socket, right, self.mouse, self.clicked, bool(right), "C"):
                self.mixer_right = None
            self.register_item_drag_zone(left_socket, "mixer_base", left)
            self.register_item_drag_zone(right_socket, "mixer_catalyst", right)
            valid, preview = Mixer.preview(left, right)
            result_preview = Mixer.visual_result(left, right)
            preview_width = action_rect.width - (231 if result_preview else 177)
            self.ui.fitted_text(self.screen_surface, preview, pygame.Rect(action_rect.x + 159, action_rect.y + 132, preview_width, 49), (92, 205, 139) if valid else COLORS["muted"], "tiny")
            if result_preview:
                result_rect = pygame.Rect(action_rect.right - 65, action_rect.y + 132, 50, 50)
                self.ui.draw_item_icon(self.screen_surface, result_rect, result_preview, True)
            if self.ui.button(self.screen_surface, use, "MIX DURING BATTLE", self.mouse, self.clicked, valid and self.battle.active, (169, 96, 203), "small"):
                source_template = left.template_id if left else ""
                ok, message, result = Mixer.mix(self.hero, self.mixer_left, self.mixer_right)
                if ok:
                    self.mixer_left = result.uid
                    self.mixer_right = None
                    self.audio.play("forge" if result.template_id != source_template else "mix")
                    self.reveal_craft(result)
                    self.save()
                self.toast(message)
        else:
            boost_icon = pygame.Rect(action_rect.x + 18, action_rect.y + 122, 64, 60)
            if boost and not self.battle.boost_used:
                self.ui.draw_item_icon(self.screen_surface, boost_icon, boost, True)
                self.ui.text(self.screen_surface, "PREPARED", (action_rect.x + 91, action_rect.y + 123), COLORS["muted"], "tiny")
                self.ui.fitted_text(self.screen_surface, boost.display_name, pygame.Rect(action_rect.x + 91, action_rect.y + 143, action_rect.width - 110, 24), self.ui.item_color(boost), "small")
                self.ui.fitted_text(self.screen_surface, boost.stat_text(), pygame.Rect(action_rect.x + 91, action_rect.y + 166, action_rect.width - 110, 19), COLORS["muted"], "tiny")
            else:
                label = "Boost already used" if self.battle.boost_used else "Select a potion or mix gear"
                pygame.draw.circle(self.screen_surface, (46, 42, 40), (action_rect.x + 50, action_rect.y + 151), 28, 2)
                self.ui.fitted_text(self.screen_surface, label, pygame.Rect(action_rect.x + 91, action_rect.y + 137, action_rect.width - 110, 30), COLORS["muted"], "small")
            if not self.battle.boost_used:
                self.register_item_drag_zone(boost_icon, "boost", boost)
            if self.ui.button(self.screen_surface, use, "USE BOOST", self.mouse, self.clicked, bool(boost and not self.battle.boost_used and self.battle.active), (75, 190, 119), "medium"):
                ok, message = self.battle.use_boost()
                if ok:
                    self.save()
                self.toast(message)
        self.ui.text(self.screen_surface, "AUTOMATIC  •  FIXED PACE", (action_rect.centerx, action_rect.bottom - 12), COLORS["muted"], "tiny", "midbottom")
        if self.battle.outcome in {BattleOutcome.DEFEAT, BattleOutcome.RETREATED}:
            self.draw_battle_result()

    def draw_battle_result(self):
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((3, 5, 9, 200))
        self.screen_surface.blit(veil, (0, 0))
        rect = pygame.Rect(345, 260, 510, 420)
        self.ui.panel(self.screen_surface, rect, (18, 22, 32), (194, 72, 84), 14, 2)
        title = "RETREATED" if self.battle.outcome == BattleOutcome.RETREATED else "DEFEAT"
        self.ui.text(self.screen_surface, title, (rect.centerx, rect.y + 42), (225, 96, 108), "title", "midtop", True)
        self.ui.text(self.screen_surface, f"Enemies defeated  {self.battle.defeated}/{self.battle.wave_total}", (rect.centerx, rect.y + 145), COLORS["text"], "body", "center")
        self.ui.text(self.screen_surface, f"XP kept  {self.battle.xp_earned}", (rect.centerx, rect.y + 182), COLORS["gold"], "medium", "center")
        self.ui.text(self.screen_surface, "Prepare different gear, mix stronger items, or grind an earlier dungeon.", (rect.centerx, rect.y + 229), COLORS["muted"], "small", "center")
        if self.ui.button(self.screen_surface, pygame.Rect(rect.x + 45, rect.bottom - 104, 195, 54), "RETRY", self.mouse, self.clicked, True, (202, 83, 76), "medium"):
            if self.battle.stage.endless_depth:
                self.start_endless(self.battle.stage.endless_depth)
            else:
                self.start_battle()
        if self.ui.button(self.screen_surface, pygame.Rect(rect.right - 240, rect.bottom - 104, 195, 54), "MAP", self.mouse, self.clicked, True, COLORS["border"], "medium"):
            self.begin_transition(Screen.HUB, "RETURNING TO THE MAP")

    def collect_loot(self, item):
        if self.hero.add_item(item):
            self.hero.pending_loot.remove(item)
            self.audio.play("collect")
            self.save()
            self.toast(f"Collected {item.display_name}.")
            return True
        self.toast("Backpack full. Manage items or salvage a reward.")
        return False

    def salvage_loot(self, item):
        value = LootSystem().salvage_value(item)
        self.hero.pending_loot.remove(item)
        self.hero.bone_dust += value
        self.audio.play("critical")
        self.save()
        self.toast(f"Reward salvaged for {value} bone dust.")

    def draw_loot(self):
        self.ui.draw_world_background(self.screen_surface, self.time)
        endless = self.hero.pending_stage < 0
        run_name = f"Endless Depth {-self.hero.pending_stage}" if endless else f"Dungeon {self.hero.pending_stage}"
        self.header("RUN COMPLETE", f"{run_name} is clear. Every reward has already been delivered.")
        summary = pygame.Rect(35, 120, 1130, 132)
        self.ui.ornamented_panel(self.screen_surface, summary, (35, 30, 25), COLORS["gold"], 12, 2)
        pygame.draw.polygon(self.screen_surface, (93, 56, 32), [(summary.x + 27, summary.y + 92), (summary.x + 27, summary.y + 48), (summary.x + 112, summary.y + 48), (summary.x + 126, summary.y + 92)])
        pygame.draw.arc(self.screen_surface, COLORS["gold"], pygame.Rect(summary.x + 32, summary.y + 14, 88, 76), math.pi, math.tau, 7)
        self.ui.text(self.screen_surface, "VICTORY", (summary.x + 154, summary.y + 26), COLORS["gold"], "large")
        best = self.battle.turns if endless and self.battle else self.hero.best_turns.get(self.hero.pending_stage, 0)
        best_label = "ENDLESS CLEAR" if endless else "BEST CLEAR"
        self.ui.text(self.screen_surface, f"{best_label}  {best} ROUNDS", (summary.x + 157, summary.y + 82), COLORS["muted"], "tiny")
        if self.battle:
            data = self.battle.summary()
            values = [("XP", data["xp"]), ("DAMAGE", data["damage"]), ("CRITS", data["criticals"]), ("BLOCKS", data["blocks"])]
            for index, (label, value) in enumerate(values):
                x = summary.x + 578 + index * 130
                pygame.draw.circle(self.screen_surface, (22, 20, 19), (x, summary.centery), 39)
                pygame.draw.circle(self.screen_surface, COLORS["border"], (x, summary.centery), 39, 1)
                self.ui.text(self.screen_surface, label, (x, summary.y + 31), COLORS["muted"], "tiny", "center")
                self.ui.text(self.screen_surface, value, (x, summary.y + 63), COLORS["text"], "medium", "center")
        stored = sum(route == "BACKPACK" for route in self.hero.pending_routes)
        salvaged = len(self.hero.pending_routes) - stored
        self.ui.text(self.screen_surface, f"RUN DROPS  •  {stored} STORED  •  {salvaged} AUTO-SALVAGED", (45, 278), COLORS["muted"], "tiny")
        for index, item in enumerate(list(self.hero.pending_loot)):
            rect = pygame.Rect(45 + index * 380, 310, 350, 392)
            item_color = self.ui.item_color(item)
            self.ui.ornamented_panel(self.screen_surface, rect, (34, 30, 27), self.ui.blend(item_color, COLORS["border"], .35), 13, 2)
            self.ui.ribbon(self.screen_surface, pygame.Rect(rect.x + 56, rect.y + 18, rect.width - 112, 31), item.category_label.upper(), item_color, "tiny")
            icon = pygame.Rect(rect.centerx - 77, rect.y + 67, 154, 154)
            pygame.draw.circle(self.screen_surface, self.ui.blend(item_color, COLORS["ink"], .79), icon.center, 74)
            pygame.draw.circle(self.screen_surface, item_color, icon.center, 74, 2)
            self.ui.draw_item_icon(self.screen_surface, icon, item, True)
            self.ui.fitted_text(self.screen_surface, item.display_name, pygame.Rect(rect.x + 24, rect.y + 235, rect.width - 48, 34), COLORS["text"], "medium", "center")
            self.ui.fitted_text(self.screen_surface, item.stat_text(), pygame.Rect(rect.x + 22, rect.y + 278, rect.width - 44, 25), item_color, "small", "center")
            self.ui.wrapped(self.screen_surface, item.description, pygame.Rect(rect.x + 27, rect.y + 314, rect.width - 54, 44), COLORS["muted"], "tiny", 3, 2)
            route = self.hero.pending_routes[index] if index < len(self.hero.pending_routes) else "BACKPACK"
            route_color = (81, 208, 132) if route == "BACKPACK" else (218, 154, 74)
            self.ui.text(self.screen_surface, route, (rect.centerx, rect.bottom - 21), route_color, "tiny", "center")
        workshop = pygame.Rect(45, 832, 300, 59)
        replay = pygame.Rect(365, 832, 300, 59)
        back = pygame.Rect(865, 832, 300, 59)
        if self.ui.button(self.screen_surface, workshop, "OPEN WORKSHOP", self.mouse, self.clicked, True, COLORS["blue"], "medium"):
            self.return_screen = Screen.EPILOGUE if self.hero.campaign_complete and not self.hero.ending_seen else Screen.HUB
            self.begin_transition(Screen.INVENTORY, "OPENING THE WORKSHOP")
            self.selected_uid = None
            self.hero.pending_loot = []
            self.hero.pending_routes = []
            self.hero.pending_stage = 0
            self.save()
        replay_label = "REPLAY DEPTH" if endless else "REPLAY DUNGEON"
        if self.ui.button(self.screen_surface, replay, replay_label, self.mouse, self.clicked, True, (188, 102, 71), "medium"):
            pending_stage = self.hero.pending_stage
            self.hero.pending_loot = []
            self.hero.pending_routes = []
            self.hero.pending_stage = 0
            if pending_stage < 0:
                self.start_endless(-pending_stage)
            else:
                self.selected_stage = pending_stage
                self.start_battle()
        back_label = "VIEW EPILOGUE" if self.hero.campaign_complete and not self.hero.ending_seen else "RETURN TO MAP"
        if self.ui.button(self.screen_surface, back, back_label, self.mouse, self.clicked, True, COLORS["gold"], "medium"):
            self.hero.pending_loot = []
            self.hero.pending_routes = []
            self.hero.pending_stage = 0
            self.save()
            target = Screen.EPILOGUE if self.hero.campaign_complete and not self.hero.ending_seen else Screen.HUB
            self.begin_transition(target, "LEAVING THE VAULT")

    def draw_epilogue(self):
        self.ui.draw_world_background(self.screen_surface, self.time)
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((18, 10, 27, 72))
        self.screen_surface.blit(veil, (0, 0))
        self.header("THE CROWN IS HOLLOW", "Campaign complete  •  The descent remembers you")
        frame = pygame.Rect(90, 130, 1020, 680)
        self.ui.ornamented_panel(self.screen_surface, frame, (25, 22, 31), (175, 104, 209), 16, 2)
        portrait = pygame.Rect(frame.x + 38, frame.y + 38, 360, 430)
        self.ui.draw_cavern(self.screen_surface, portrait, Element.ARCANE, 7, self.time)
        pygame.draw.rect(self.screen_surface, (176, 101, 207), portrait, 2, border_radius=12)
        self.draw_hero(pygame.Vector2(portrait.centerx, portrait.bottom - 35), "victory", self.time, 1.05)
        pygame.draw.polygon(self.screen_surface, COLORS["gold"], [(portrait.centerx - 34, portrait.y + 58), (portrait.centerx - 15, portrait.y + 82), (portrait.centerx, portrait.y + 53), (portrait.centerx + 16, portrait.y + 82), (portrait.centerx + 35, portrait.y + 58), (portrait.centerx + 28, portrait.y + 99), (portrait.centerx - 27, portrait.y + 99)], 3)
        text_x = frame.x + 445
        self.ui.text(self.screen_surface, "THE WAYFARER RETURNS", (text_x, frame.y + 51), COLORS["gold"], "large")
        story = "The Hollow Sovereign falls, but the road beneath the throne does not end. Every enemy, every item and every choice now echoes below in a dungeon that rebuilds itself after each victory."
        self.ui.wrapped(self.screen_surface, story, pygame.Rect(text_x, frame.y + 119, 510, 118), COLORS["text"], "body", 8, 5)
        stats = (("LEVEL", self.hero.level), ("WINS", self.hero.total_wins), ("ENEMIES", self.hero.total_enemies), ("RECIPES", f"{len(self.hero.discovered_recipes)}/{len(RECIPES)}"))
        for index, (label, value) in enumerate(stats):
            col, row = index % 2, index // 2
            chip = pygame.Rect(text_x + col * 250, frame.y + 270 + row * 72, 230, 56)
            self.ui.stat_chip(self.screen_surface, chip, label, value, (183, 103, 216) if col else COLORS["gold"])
        unlock = pygame.Rect(frame.x + 38, frame.bottom - 164, frame.width - 76, 94)
        self.ui.ornamented_panel(self.screen_surface, unlock, (35, 25, 43), (175, 104, 209), 11, 2)
        self.ui.text(self.screen_surface, "ENDLESS DESCENT UNLOCKED", (unlock.x + 24, unlock.y + 18), (208, 139, 235), "medium")
        self.ui.text(self.screen_surface, "Scaling enemies  •  rotating bosses  •  three automatic drops  •  no final depth", (unlock.x + 26, unlock.y + 57), COLORS["muted"], "small")
        if self.ui.button(self.screen_surface, pygame.Rect(390, 843, 420, 62), "CONTINUE INTO THE ENDLESS", self.mouse, self.clicked, True, (162, 89, 204), "medium"):
            self.hero.ending_seen = True
            self.begin_transition(Screen.HUB, "THE DESCENT CONTINUES")
            self.save()

    def draw(self):
        self.item_drag_zones = []
        self.audio.music("battle" if self.screen == Screen.BATTLE else "ambient")
        if self.screen == Screen.MAIN_MENU:
            self.draw_main_menu()
        elif self.screen == Screen.HUB:
            self.draw_hub()
        elif self.screen == Screen.INVENTORY:
            self.draw_workshop()
        elif self.screen == Screen.MIXER:
            self.draw_mixer()
        elif self.screen == Screen.CHARACTER:
            self.draw_character()
        elif self.screen == Screen.RECIPES:
            self.draw_recipes()
        elif self.screen == Screen.BATTLE:
            self.draw_battle()
        elif self.screen == Screen.LOOT:
            self.draw_loot()
        elif self.screen == Screen.EPILOGUE:
            self.draw_epilogue()
        self.draw_brand_mark()
        self.draw_craft_reveal()
        self.draw_item_drag_overlay()
        self.ui.toast(self.screen_surface, self.toast_text, self.toast_age)
        self.draw_transition()
        pygame.display.flip()
        self.clicked = False

    def run_simulation(self):
        self.new_game()
        stats = self.hero.total_stats()
        if stats != {"health": 55, "attack": 13, "defense": 4, "luck": 3}:
            raise RuntimeError(f"Invalid starting stats: {stats}")
        self.start_battle()
        steps = 0
        while self.battle.active and steps < 10000:
            self.battle.update(.1)
            steps += 1
        if self.battle.active:
            raise RuntimeError("Battle simulation did not finish")
        print(f"simulation_ok outcome={self.battle.outcome.value} turns={self.battle.turns} stats={stats} stages={len(STAGES)}")
        if self.save_manager.path.exists():
            self.save_manager.path.unlink()
        pygame.quit()

    def run(self):
        if self.simulate:
            self.run_simulation()
            return
        while self.running:
            dt = min(.05, self.clock.tick(FPS) / 1000)
            self.handle_events()
            self.update(dt)
            self.draw()
        self.save()
        pygame.quit()


def launch():
    Game("--simulate" in sys.argv).run()
