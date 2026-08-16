import hashlib
import json
import os
import random
import sys
import time
import uuid
from pathlib import Path

from models import Element, Hero, Item, ItemKind


class SaveError(Exception):
    def __init__(self, message):
        super().__init__(message)


class SaveManager:
    VERSION = 2

    def __init__(self, path=None):
        if path:
            self.path = Path(path)
        elif getattr(sys, "frozen", False) or "__compiled__" in globals():
            if sys.platform == "win32":
                root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
            elif sys.platform == "darwin":
                root = Path.home() / "Library" / "Application Support"
            else:
                root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
            self.path = root / "Bonebound" / "savegame.json"
        else:
            self.path = Path(__file__).resolve().with_name("savegame.json")

    def exists(self):
        return self.path.is_file()

    def _payload(self, hero, selected_stage):
        body = {
            "version": self.VERSION,
            "saved_at": int(time.time()),
            "selected_stage": int(selected_stage),
            "hero": hero.to_dict(),
        }
        encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
        body["checksum"] = hashlib.sha256(encoded).hexdigest()[:20]
        return body

    def save(self, hero, selected_stage):
        payload = self._payload(hero, selected_stage)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp, self.path)

    def load(self):
        if not self.exists():
            raise SaveError("No save file exists.")
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise SaveError("The save file could not be read.") from exc
        if not isinstance(payload, dict):
            raise SaveError("The save file has an invalid root structure.")
        checksum = payload.pop("checksum", None)
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        expected = hashlib.sha256(encoded).hexdigest()[:20]
        if checksum != expected:
            raise SaveError("The save file is damaged or incomplete.")
        try:
            if int(payload.get("version", 0)) > self.VERSION:
                raise SaveError("This save was created by a newer game version.")
            hero_data = payload["hero"]
            if not isinstance(hero_data, dict) or not isinstance(hero_data.get("inventory", []), list):
                raise ValueError
            if not isinstance(hero_data.get("pending_routes", []), list):
                raise ValueError
            if len(hero_data.get("inventory", [])) > 12 or len(hero_data.get("pending_loot", [])) > 3 or len(hero_data.get("pending_routes", [])) > 3:
                raise ValueError
            hero = Hero.from_dict(hero_data)
            selected_stage = int(payload.get("selected_stage", hero.unlocked_stage))
        except SaveError:
            raise
        except (AttributeError, KeyError, OverflowError, TypeError, ValueError) as exc:
            raise SaveError("The save data is invalid.") from exc
        selected_stage = max(1, min(hero.unlocked_stage, selected_stage))
        return hero, selected_stage


class Mixer:
    PRIMARY_STAT = {ItemKind.WEAPON: "attack", ItemKind.SHIELD: "defense"}
    PRIMAL_CAP_BONUS_LIMIT = 2

    @staticmethod
    def _reinforcement_limit(item):
        return 3 + max(0, int(item.effects.get("upgrade_cap_bonus", 0)))

    @staticmethod
    def _active_stats(item):
        return {key: value for key, value in item.stats.items() if value}

    @classmethod
    def _transferable_stats(cls, item):
        result = cls._active_stats(item)
        if item.kind == ItemKind.POTION:
            if item.effects.get("heal_flat"):
                result["health"] = max(result.get("health", 0), max(1, round(item.effects["heal_flat"] / 6)))
            if item.effects.get("heal_percent"):
                result["health"] = max(result.get("health", 0), round(item.effects["heal_percent"] * 10))
            for effect, stat in (("battle_attack", "attack"), ("battle_defense", "defense"), ("battle_luck", "luck")):
                if item.effects.get(effect):
                    result[stat] = max(result.get(stat, 0), int(item.effects[effect]))
        if item.kind == ItemKind.MATERIAL and not result:
            if item.template_id in {"bone_shard", "tattered_hide"}:
                result["health"] = max(1, item.tier)
            elif item.template_id == "iron_scrap":
                result["defense"] = max(1, item.tier)
            elif item.template_id == "ghost_salt":
                result["luck"] = max(1, item.tier - 1)
            elif item.template_id in {"ember_core", "storm_wire", "void_resin", "crown_fragment"}:
                result["attack"] = max(1, item.tier)
            elif item.template_id == "frostglass":
                result["defense"] = max(1, item.tier)
        return result

    @staticmethod
    def _potion_channels(item):
        channels = set()
        if item.effects.get("heal_flat") or item.effects.get("heal_percent") or item.effects.get("revive_percent"):
            channels.add("heal")
        for effect, channel in (("battle_attack", "attack"), ("battle_defense", "defense"), ("battle_luck", "luck")):
            if item.effects.get(effect):
                channels.add(channel)
        return channels

    @classmethod
    def preview(cls, left, right):
        if not left or not right:
            return False, "Choose a kept item on the left and an ingredient on the right."
        if left.uid == right.uid and left.stack < 2:
            return False, "This stack needs at least two items for both mixer sides."
        from content import ITEM_TEMPLATES, recipe_result

        special = recipe_result(left.template_id, right.template_id)
        if special:
            return True, f"Special recipe: forge {ITEM_TEMPLATES[special]['name']}. Compatible upgrades and bonus stats carry over from the left, replacing optional quality rolls when needed."
        if left.kind in {ItemKind.WEAPON, ItemKind.SHIELD, ItemKind.RING}:
            if right.kind == ItemKind.ESSENCE and (right.effects.get("raise_element_power") or right.effects.get("upgrade_cap")):
                power_gain = max(0, int(right.effects.get("raise_element_power", 0)))
                current_cap_bonus = max(0, int(left.effects.get("upgrade_cap_bonus", 0)))
                cap_gain = min(
                    max(0, int(right.effects.get("upgrade_cap", 0))),
                    max(0, cls.PRIMAL_CAP_BONUS_LIMIT - current_cap_bonus),
                )
                benefits = []
                if left.element != Element.NEUTRAL and power_gain and left.element_power < 100:
                    benefits.append(f"element power +{min(power_gain, 100 - left.element_power)}")
                if cap_gain:
                    benefits.append(f"stat and reinforcement caps +{cap_gain}")
                if not benefits:
                    return False, f"{left.display_name} cannot absorb more primal power."
                return True, f"Primal refinement: {', '.join(benefits)}. {left.display_name} survives."
            if right.kind == ItemKind.ESSENCE and right.element != Element.NEUTRAL:
                if left.element == right.element:
                    if left.element_power >= 100:
                        return False, f"{left.display_name} has reached maximum elemental power."
                    return True, f"Reinforce {left.element.value} power. {left.display_name} survives."
                return True, f"Bind {right.element.value} to {left.display_name}. The old element is replaced."
            incoming = cls._transferable_stats(right)
            if not incoming and right.template_id != left.template_id:
                return False, "That ingredient carries nothing this gear can absorb."
            active = set(cls._active_stats(left))
            primary = cls.PRIMARY_STAT.get(left.kind)
            if primary:
                active.add(primary)
            new_stats = [key for key in incoming if key not in active]
            if len(active | set(new_stats)) > 2:
                return False, "Gear can hold at most two attributes. Use a matching ingredient."
            if left.template_id == right.template_id and left.kind == right.kind:
                reinforcement_limit = cls._reinforcement_limit(left)
                if left.upgrade >= reinforcement_limit:
                    return False, f"{left.display_name} has reached the +{reinforcement_limit} reinforcement limit."
                return True, f"Reinforce the matching gear and raise its limits. {left.display_name} survives."
            transferable = False
            for key, value in incoming.items():
                cap = left.caps.get(key, max(left.stats.get(key, 0) + abs(value) * 3, abs(value)))
                if left.stats.get(key, 0) < cap:
                    transferable = True
                    break
            if incoming and not transferable:
                return False, "Every matching attribute is already at this item's capacity."
            names = ", ".join(key.upper() for key in incoming)
            return True, f"Transfer {names} into {left.display_name}. The right item is consumed."
        if left.kind == ItemKind.POTION and right.kind == ItemKind.POTION:
            keys = cls._potion_channels(left) | cls._potion_channels(right)
            if len(keys) > 2:
                return False, "A tonic can contain at most two effects."
            return True, "Blend both potion effects into one stronger tonic. The left bottle survives."
        if left.kind == ItemKind.ESSENCE and right.kind == ItemKind.ESSENCE:
            if left.element != right.element:
                return False, "Opposing raw essences refuse to bind without equipment."
            return True, f"Refine the {left.element.value} essence to a higher tier."
        if left.kind == ItemKind.MATERIAL and right.kind == ItemKind.MATERIAL and left.template_id == right.template_id:
            return True, "Compress matching materials into a more valuable bundle."
        return False, "These item types do not produce a stable mixture."

    @classmethod
    def mix(cls, hero, left_uid, right_uid):
        left = hero.item_by_uid(left_uid)
        right = hero.item_by_uid(right_uid)
        valid, message = cls.preview(left, right)
        if not valid:
            return False, message, None
        from content import create_item, recipe_result

        special = recipe_result(left.template_id, right.template_id)
        original_left_template = left.template_id
        original_right_template = right.template_id
        same_stack = left.uid == right.uid
        needs_split_slot = left.stack > 1 and (not same_stack or left.stack > 2)
        if needs_split_slot and len(hero.inventory) >= hero.inventory_capacity and right.stack > 1:
            return False, "Free one backpack slot to separate the kept item from its stack.", None
        consumed = hero.remove_item(right.uid, 1)
        if not consumed:
            return False, "The ingredient is no longer in the backpack.", None
        if left.stack > 1:
            left.stack -= 1
            split_data = left.to_dict()
            split_data["uid"] = uuid.uuid4().hex[:12]
            split_data["stack"] = 1
            left = Item.from_dict(split_data)
            hero.inventory.append(left)
        if special:
            seed_text = f"{left.uid}:{consumed.uid}:{special}".encode("utf-8")
            seed = int(hashlib.sha256(seed_text).hexdigest()[:16], 16)
            crafted = create_item(special, random.Random(seed), max(1, min(25, max(left.tier, consumed.tier) * 5)))
            crafted.uid = left.uid
            from content import ITEM_TEMPLATES

            crafted_template = ITEM_TEMPLATES[special]
            old_base = ITEM_TEMPLATES.get(original_left_template, {}).get("stats", {})
            crafted_base = crafted_template.get("stats", {})
            protected_channels = set()
            upgrade_cap_bonus = max(0, int(left.effects.get("upgrade_cap_bonus", 0)))
            if upgrade_cap_bonus:
                crafted.effects["upgrade_cap_bonus"] = upgrade_cap_bonus
            crafted.upgrade = min(3 + upgrade_cap_bonus, left.upgrade)
            for key, old_value in left.stats.items():
                inherited = max(0, old_value - old_base.get(key, 0))
                if not inherited:
                    continue
                active = {name for name, value in crafted.stats.items() if value}
                if key not in active and len(active) >= 2:
                    optional = [
                        name for name in active
                        if not crafted_base.get(name, 0) and name not in protected_channels
                    ]
                    if not optional:
                        continue
                    removed = min(optional, key=lambda name: (crafted.stats.get(name, 0), name))
                    removed_bonus = max(0, crafted.stats.pop(removed, 0) - crafted_base.get(removed, 0))
                    quality_value = 4 + crafted.tier * 2
                    crafted.value = max(crafted_template["value"], crafted.value - removed_bonus * quality_value)
                desired = crafted.stats.get(key, 0) + inherited
                inherited_cap = max(crafted.caps.get(key, 0), left.caps.get(key, 0), desired)
                crafted.caps[key] = inherited_cap
                crafted.stats[key] = desired
                protected_channels.add(key)
            hero.inventory[hero.inventory.index(left)] = crafted
            recipe_key = f"{'+'.join(sorted((original_left_template, original_right_template)))}={special}"
            discovered = recipe_key not in hero.discovered_recipes
            hero.discovered_recipes.add(recipe_key)
            hero.discovery.add(crafted.template_id)
            levels = hero.gain_xp(10) if discovered else 0
            suffix = " New recipe discovered: +10 XP." if discovered else ""
            if levels:
                suffix += f" Level {hero.level} reached."
            return True, f"Forged {crafted.display_name}.{suffix}", crafted
        if left.kind in {ItemKind.WEAPON, ItemKind.SHIELD, ItemKind.RING}:
            if consumed.kind == ItemKind.ESSENCE and (consumed.effects.get("raise_element_power") or consumed.effects.get("upgrade_cap")):
                power_gain = max(0, int(consumed.effects.get("raise_element_power", 0)))
                current_cap_bonus = max(0, int(left.effects.get("upgrade_cap_bonus", 0)))
                cap_gain = min(
                    max(0, int(consumed.effects.get("upgrade_cap", 0))),
                    max(0, cls.PRIMAL_CAP_BONUS_LIMIT - current_cap_bonus),
                )
                gained_power = 0
                if left.element != Element.NEUTRAL and power_gain:
                    before = left.element_power
                    left.element_power = min(100, left.element_power + power_gain)
                    gained_power = left.element_power - before
                if cap_gain:
                    active = set(cls._active_stats(left))
                    primary = cls.PRIMARY_STAT.get(left.kind)
                    if primary:
                        active.add(primary)
                    for key in active:
                        left.caps[key] = max(left.caps.get(key, 0), left.stats.get(key, 0)) + cap_gain
                    left.effects["upgrade_cap_bonus"] = max(0, int(left.effects.get("upgrade_cap_bonus", 0))) + cap_gain
                details = []
                if gained_power:
                    details.append(f"element power +{gained_power}")
                if cap_gain:
                    details.append(f"stat and reinforcement caps +{cap_gain}")
                return True, f"Refined {left.display_name}: {', '.join(details)}.", left
            if consumed.kind == ItemKind.ESSENCE and consumed.element != Element.NEUTRAL:
                if left.element == consumed.element:
                    left.element_power = min(100, left.element_power + 12 + consumed.tier * 5)
                else:
                    left.element = consumed.element
                    left.element_power = min(100, 18 + consumed.tier * 6)
            for key, value in cls._transferable_stats(consumed).items():
                cap = left.caps.get(key, max(left.stats.get(key, 0) + abs(value) * 3, abs(value)))
                left.caps[key] = cap
                left.stats[key] = min(cap, left.stats.get(key, 0) + value)
            if left.template_id == consumed.template_id and left.kind == consumed.kind:
                left.upgrade += 1
                for key in set(left.caps) | set(consumed.caps):
                    left.caps[key] = max(left.caps.get(key, 0), consumed.caps.get(key, 0)) + 1
                primary = cls.PRIMARY_STAT.get(left.kind)
                if primary:
                    left.stats[primary] = min(left.caps.get(primary, 999), left.stats.get(primary, 0) + 1)
                left.element_power = min(100, left.element_power + consumed.element_power // 2)
            return True, f"Created {left.display_name}. The ingredient was consumed.", left
        if left.kind == ItemKind.POTION:
            for key, value in consumed.effects.items():
                if not isinstance(value, (int, float)):
                    continue
                if key == "duration_turns":
                    left.effects[key] = max(left.effects.get(key, 0), value)
                elif key == "heal_flat":
                    left.effects[key] = min(120, left.effects.get(key, 0) + value)
                elif key in {"heal_percent", "revive_percent"}:
                    left.effects[key] = min(1.0, left.effects.get(key, 0) + value)
                else:
                    left.effects[key] = min(15, left.effects.get(key, 0) + value)
            for key, value in consumed.stats.items():
                left.stats[key] = left.stats.get(key, 0) + value
            left.tier = min(5, max(left.tier, consumed.tier) + (1 if left.template_id == consumed.template_id else 0))
            left.name = "Blended Tonic" if left.template_id != consumed.template_id else left.name
            left.template_id = "blended_tonic"
            left.description = "A field tonic shaped by the two ingredients mixed into it."
            return True, f"Brewed {left.display_name}. The right bottle was consumed.", left
        if left.kind == ItemKind.ESSENCE:
            left.tier = min(5, max(left.tier, consumed.tier) + 1)
            left.element_power = min(100, left.element_power + consumed.element_power)
            left.name = f"Refined {left.element.value.title()} Essence"
            return True, f"Refined the essence to tier {left.tier}.", left
        if left.kind == ItemKind.MATERIAL:
            left.value += consumed.value
            left.tier = min(5, max(left.tier, consumed.tier) + 1)
            left.name = f"Compressed {left.name}"
            return True, f"Compressed the material bundle to tier {left.tier}.", left
        return False, "The mixture collapsed.", None


class LootSystem:
    def __init__(self, rng=None):
        self.rng = rng or random.Random()

    def rewards(self, stage, first_clear):
        from content import ENEMIES, create_item

        ids = []
        if first_clear:
            ids.append(stage.first_clear_item)
        pool = []
        for enemy_id in stage.enemies:
            pool.extend(ENEMIES[enemy_id].loot)
        while len(ids) < stage.loot_rolls:
            ids.append(self.rng.choice(pool))
        ids = ids[:stage.loot_rolls]
        self.rng.shuffle(ids)
        return [create_item(template_id, self.rng, stage.index) for template_id in ids]

    def salvage_value(self, item):
        single = max(1, item.value // 3 + item.tier * 2)
        return single * max(1, item.stack)
