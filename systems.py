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
    VERSION = 4

    WEAPON_ATTACK_V4 = {
        "wayfarer_blade": 7,
        "rusted_falchion": 8,
        "bone_cleaver": 12,
        "grave_hook": 14,
        "emberbrand": 16,
        "warden_pike": 18,
        "rimefang": 19,
        "stormneedle": 20,
        "venomthorn": 22,
        "lantern_sabre": 23,
        "astral_edge": 26,
        "sunken_king_blade": 29,
        "voidglass_sabre": 34,
        "crownless_oath": 38,
    }

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
            save_version = int(payload.get("version", 0))
            hero = Hero.from_dict(hero_data)
            if save_version < 4:
                for item in hero.inventory + hero.equipment_items():
                    base_attack = self.WEAPON_ATTACK_V4.get(item.template_id)
                    if base_attack is None:
                        continue
                    target = base_attack + item.upgrade * 2
                    item.stats["attack"] = max(target, int(item.stats.get("attack", 0)))
                    if item.template_id == "wayfarer_blade":
                        cap_target = 16 + item.upgrade * 2
                    else:
                        cap_target = target + max(0, 5 - item.upgrade) * 2
                    item.caps["attack"] = max(cap_target, int(item.caps.get("attack", 0)))
            selected_stage = int(payload.get("selected_stage", hero.unlocked_stage))
        except SaveError:
            raise
        except (AttributeError, KeyError, OverflowError, TypeError, ValueError) as exc:
            raise SaveError("The save data is invalid.") from exc
        selected_stage = max(1, min(hero.unlocked_stage, selected_stage))
        return hero, selected_stage


class Mixer:
    PRIMARY_STAT = {ItemKind.WEAPON: "attack", ItemKind.SHIELD: "defense"}
    PRIMAL_CAP_BONUS_LIMIT = 4
    FUSION_PRIMARY_RATE = .34
    FUSION_SECONDARY_RATE = .42

    @staticmethod
    def _reinforcement_limit(item):
        return 5 + max(0, int(item.effects.get("upgrade_cap_bonus", 0)))

    @classmethod
    def reinforcement_cost(cls, item):
        return 14 + item.tier * 8 + item.upgrade * 12

    @classmethod
    def _reinforce(cls, item):
        if item.upgrade >= cls._reinforcement_limit(item):
            return False
        item.upgrade += 1
        active = set(cls._active_stats(item))
        primary = cls.PRIMARY_STAT.get(item.kind)
        if primary:
            active.add(primary)
        for key in active:
            item.caps[key] = max(item.caps.get(key, 0), item.stats.get(key, 0)) + 2
        if primary:
            gain = 2 if item.kind == ItemKind.WEAPON else 1
            item.stats[primary] = min(item.caps[primary], item.stats.get(primary, 0) + gain)
        secondary = [key for key in active if key != primary]
        if secondary and item.upgrade % 2 == 0:
            key = min(secondary, key=lambda value: (item.stats.get(value, 0), value))
            item.stats[key] = min(item.caps[key], item.stats.get(key, 0) + 1)
        if item.element != Element.NEUTRAL:
            item.element_power = min(100, item.element_power + 5 + item.tier * 2)
        item.value += 8 + item.tier * 6 + item.upgrade * 3
        return True

    @classmethod
    def temper(cls, hero, uid):
        item = hero.item_by_uid(uid)
        if not item:
            item = next((value for value in hero.equipment.values() if value and value.uid == uid), None)
        if not item or item.kind not in {ItemKind.WEAPON, ItemKind.SHIELD, ItemKind.RING}:
            return False, "Only equipped gear can be tempered.", None
        if item.upgrade >= cls._reinforcement_limit(item):
            return False, f"{item.display_name} is at its reinforcement limit.", item
        cost = cls.reinforcement_cost(item)
        if hero.bone_dust < cost:
            return False, f"Tempering needs {cost} bone dust.", item
        hero.bone_dust -= cost
        cls._reinforce(item)
        return True, f"Tempered {item.display_name} for {cost} bone dust.", item

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

    @classmethod
    def _absorbed_stat_gain(cls, item, catalyst, stat, value):
        """Return a diminishing fusion gain instead of adding whole items.

        The kept object remains the identity of the result. A catalyst lends a
        fraction of its power, with secondary channels absorbing slightly more
        readily so high-tier gear does not collapse into one enormous number.
        """
        value = max(0, int(value))
        if not value:
            return 0
        primary = cls.PRIMARY_STAT.get(item.kind)
        rate = cls.FUSION_PRIMARY_RATE if stat == primary else cls.FUSION_SECONDARY_RATE
        if catalyst.kind != item.kind:
            rate *= .78
        before = max(0, int(item.stats.get(stat, 0)))
        soft_cap = {
            "health": 8 + item.tier * 7,
            "attack": 7 + item.tier * 6,
            "defense": 4 + item.tier * 4,
            "luck": 2 + item.tier,
        }[stat]
        if before >= soft_cap:
            rate *= .62
        return max(1, round(value * rate))

    @staticmethod
    def _potion_channels(item):
        channels = set()
        if item.effects.get("heal_flat") or item.effects.get("heal_percent") or item.effects.get("revive_percent"):
            channels.add("heal")
        for effect, channel in (("battle_attack", "attack"), ("battle_defense", "defense"), ("battle_luck", "luck")):
            if item.effects.get(effect):
                channels.add(channel)
        return channels

    @staticmethod
    def _fusion_name(item, catalyst):
        from content import ITEM_TEMPLATES

        element_words = {
            Element.FIRE: "Cinder",
            Element.ICE: "Rime",
            Element.STORM: "Storm",
            Element.VENOM: "Mire",
            Element.ARCANE: "Astral",
        }
        kind_words = {
            ItemKind.WEAPON: "Edge",
            ItemKind.SHIELD: "Ward",
            ItemKind.RING: "Gilded",
            ItemKind.POTION: "Distilled",
            ItemKind.ESSENCE: "Prism",
            ItemKind.MATERIAL: "Grafted",
        }
        accent = element_words.get(catalyst.element, kind_words[catalyst.kind])
        base_template = item.effects.get("fusion_base", item.template_id)
        base_name = ITEM_TEMPLATES.get(base_template, {}).get("name", item.name)
        if item.kind == ItemKind.POTION:
            return f"{accent} Concoction"
        if item.kind == ItemKind.ESSENCE:
            return f"{accent} Prism"
        if item.kind == ItemKind.MATERIAL:
            return f"{accent} Relic"
        return f"{accent} {base_name}"

    @classmethod
    def _stamp_fusion(cls, item, catalyst, effectful):
        previous = str(item.effects.get("fusion_visual", item.template_id))
        catalyst_mark = str(catalyst.effects.get("fusion_visual", catalyst.template_id))
        signature = hashlib.sha256(f"{previous}>{catalyst_mark}>{item.uid}".encode("utf-8")).hexdigest()[:16]
        item.effects["fusion_visual"] = signature
        item.effects["fusion_base"] = item.effects.get("fusion_base", item.template_id)
        item.effects["fusion_catalyst"] = catalyst.effects.get("fusion_base", catalyst.template_id)
        item.effects["fusion_accent"] = catalyst.element.value if catalyst.element != Element.NEUTRAL else catalyst.kind.value
        item.name = cls._fusion_name(item, catalyst)
        item.stack = 1
        item.max_stack = 1
        item.tier = min(5, max(item.tier, catalyst.tier))
        item.value += max(3, catalyst.value // 3) + item.tier * 2
        if effectful:
            item.description = "A one-off fusion whose visible inlay carries every compatible trace of its catalyst."
        else:
            item.description = "A one-off cosmetic fusion. Its strange inlay changes the object, even when no useful power transfers."
        return item

    @classmethod
    def _merge_generic(cls, item, catalyst):
        """Apply every compatible channel, then always stamp a unique visual fusion."""
        effectful = False
        if item.kind in {ItemKind.WEAPON, ItemKind.SHIELD, ItemKind.RING}:
            if catalyst.kind == ItemKind.ESSENCE and (catalyst.effects.get("raise_element_power") or catalyst.effects.get("upgrade_cap")):
                power_gain = max(0, int(catalyst.effects.get("raise_element_power", 0)))
                before_power = item.element_power
                if item.element != Element.NEUTRAL:
                    item.element_power = min(100, item.element_power + power_gain)
                current_cap_bonus = max(0, int(item.effects.get("upgrade_cap_bonus", 0)))
                cap_gain = min(max(0, int(catalyst.effects.get("upgrade_cap", 0))), max(0, cls.PRIMAL_CAP_BONUS_LIMIT - current_cap_bonus))
                if cap_gain:
                    active_stats = set(cls._active_stats(item))
                    primary_stat = cls.PRIMARY_STAT.get(item.kind)
                    if primary_stat:
                        active_stats.add(primary_stat)
                    for key in active_stats:
                        item.caps[key] = max(item.caps.get(key, 0), item.stats.get(key, 0)) + cap_gain
                    item.effects["upgrade_cap_bonus"] = current_cap_bonus + cap_gain
                effectful = item.element_power != before_power or bool(cap_gain)
            if catalyst.kind == ItemKind.ESSENCE and catalyst.element != Element.NEUTRAL:
                before = (item.element, item.element_power)
                if item.element == catalyst.element:
                    item.element_power = min(100, item.element_power + 12 + catalyst.tier * 5)
                else:
                    item.element = catalyst.element
                    item.element_power = min(100, 18 + catalyst.tier * 6)
                effectful = effectful or before != (item.element, item.element_power)
            active = {key for key, value in item.stats.items() if value}
            primary = cls.PRIMARY_STAT.get(item.kind)
            if primary:
                active.add(primary)
            same_template = item.template_id == catalyst.template_id and item.kind == catalyst.kind
            for key, value in cls._transferable_stats(catalyst).items():
                # Identical gear reinforces once; it does not transfer its full
                # stat block and then reinforce a second time.
                if same_template:
                    continue
                if key not in active and len(active) >= 2:
                    continue
                before = item.stats.get(key, 0)
                gain = cls._absorbed_stat_gain(item, catalyst, key, value)
                if not gain:
                    continue
                if key in item.caps:
                    cap = max(before, int(item.caps[key]))
                else:
                    cap = before + max(gain, round(value * .58))
                    item.caps[key] = cap
                item.stats[key] = min(cap, before + gain)
                if item.stats[key] != before:
                    active.add(key)
                    effectful = True
            if same_template:
                effectful = cls._reinforce(item) or effectful
                for key in set(item.caps) | set(catalyst.caps):
                    item.caps[key] = max(item.caps.get(key, 0), catalyst.caps.get(key, 0), item.stats.get(key, 0))
                before_power = item.element_power
                item.element_power = min(100, item.element_power + catalyst.element_power // 2)
                effectful = effectful or item.element_power != before_power
        elif item.kind == ItemKind.POTION:
            allowed = {"heal_flat", "heal_percent", "revive_percent", "battle_attack", "battle_defense", "battle_luck", "duration_turns"}
            if catalyst.kind == ItemKind.POTION:
                for key, value in catalyst.effects.items():
                    if key not in allowed or not isinstance(value, (int, float)):
                        continue
                    before = item.effects.get(key, 0)
                    if key == "duration_turns":
                        item.effects[key] = max(before, value)
                    elif key == "heal_flat":
                        item.effects[key] = min(120, before + max(1, round(value * .45)))
                    elif key in {"heal_percent", "revive_percent"}:
                        item.effects[key] = min(1.0, before + value * .5)
                    else:
                        item.effects[key] = min(15, before + max(1, round(value * .45)))
                    effectful = effectful or item.effects[key] != before
            elif catalyst.kind == ItemKind.ESSENCE and catalyst.element != Element.NEUTRAL:
                before = (item.element, item.element_power)
                item.element = catalyst.element
                item.element_power = max(item.element_power, 12 + catalyst.tier * 5)
                effectful = before != (item.element, item.element_power)
            item.template_id = "blended_tonic"
        elif item.kind == ItemKind.ESSENCE:
            if catalyst.kind == ItemKind.ESSENCE:
                before = (item.tier, item.element_power)
                item.tier = min(5, max(item.tier, catalyst.tier) + 1)
                item.element_power = min(100, item.element_power + catalyst.element_power)
                effectful = before != (item.tier, item.element_power)
        elif item.kind == ItemKind.MATERIAL:
            before = (item.value, item.tier)
            item.value += max(1, catalyst.value // 2)
            item.tier = min(5, max(item.tier, catalyst.tier) + (1 if item.template_id == catalyst.template_id else 0))
            effectful = before != (item.value, item.tier)
        cls._stamp_fusion(item, catalyst, effectful)
        return effectful

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
        return True, "Experimental fusion: the catalyst is consumed and a unique inlaid item is created. Compatible power transfers when possible; otherwise the result is cosmetic."

    @classmethod
    def visual_result(cls, left, right):
        """Build a non-mutating item preview for the mixer's output socket."""
        valid, _ = cls.preview(left, right)
        if not valid:
            return None
        from content import create_item, recipe_result

        special = recipe_result(left.template_id, right.template_id)
        if special:
            stage = max(1, min(25, max(left.tier, right.tier) * 5))
            result = create_item(special, random.Random(0), stage)
            result.uid = "mix-preview"
            return result
        result = Item.from_dict(left.to_dict())
        result.uid = "mix-preview"
        cls._merge_generic(result, right)
        return result

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
            crafted.upgrade = min(5 + upgrade_cap_bonus, left.upgrade)
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
        effectful = cls._merge_generic(left, consumed)
        detail = "Compatible power transferred." if effectful else "No combat power transferred; the fusion is visual and collectible."
        return True, f"Created {left.display_name}. {detail}", left


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
