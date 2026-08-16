import uuid
import random
from dataclasses import dataclass, field
from enum import Enum


class Element(Enum):
    NEUTRAL = "neutral"
    FIRE = "fire"
    ICE = "ice"
    STORM = "storm"
    VENOM = "venom"
    ARCANE = "arcane"


class ItemKind(Enum):
    WEAPON = "weapon"
    SHIELD = "shield"
    RING = "ring"
    POTION = "potion"
    ESSENCE = "essence"
    MATERIAL = "material"


STAT_NAMES = {
    "health": "HP",
    "attack": "ATK",
    "defense": "DEF",
    "luck": "LUCK",
}


@dataclass
class Item:
    template_id: str
    name: str
    kind: ItemKind
    stats: dict = field(default_factory=dict)
    caps: dict = field(default_factory=dict)
    element: Element = Element.NEUTRAL
    element_power: int = 0
    tier: int = 1
    upgrade: int = 0
    stack: int = 1
    max_stack: int = 1
    effects: dict = field(default_factory=dict)
    traits: tuple = ()
    description: str = ""
    value: int = 0
    uid: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    @property
    def display_name(self):
        suffix = f" +{self.upgrade}" if self.upgrade else ""
        return f"{self.name}{suffix}"

    @property
    def slot(self):
        if self.kind == ItemKind.WEAPON:
            return "weapon"
        if self.kind == ItemKind.SHIELD:
            return "shield"
        if self.kind == ItemKind.RING:
            return "ring"
        return None

    @property
    def attribute_count(self):
        return sum(1 for value in self.stats.values() if value)

    @property
    def stackable(self):
        return self.max_stack > 1

    def compatible_stack(self, other):
        return (
            self.stackable
            and self.template_id == other.template_id
            and self.name == other.name
            and self.stats == other.stats
            and self.caps == other.caps
            and self.effects == other.effects
            and self.element == other.element
            and self.element_power == other.element_power
            and self.tier == other.tier
            and self.upgrade == other.upgrade
            and self.traits == other.traits
            and self.value == other.value
        )

    def stat_text(self):
        parts = []
        for key in ("health", "attack", "defense", "luck"):
            value = self.stats.get(key, 0)
            if value:
                sign = "+" if value > 0 else ""
                parts.append(f"{sign}{value} {STAT_NAMES[key]}")
        if self.element != Element.NEUTRAL:
            parts.append(f"{self.element.value.title()} {self.element_power}")
        if self.kind == ItemKind.POTION:
            if self.effects.get("heal_flat"):
                parts.append(f"Heal {int(self.effects['heal_flat'])}")
            if self.effects.get("heal_percent"):
                parts.append(f"Heal {round(self.effects['heal_percent'] * 100)}%")
            if self.effects.get("revive_percent"):
                parts.append(f"Revive {round(self.effects['revive_percent'] * 100)}%")
            for effect, label in (("battle_attack", "ATK"), ("battle_defense", "DEF"), ("battle_luck", "LUCK")):
                if self.effects.get(effect):
                    parts.append(f"+{int(self.effects[effect])} {label}")
        return "  •  ".join(parts) if parts else "No stat bonus"

    def to_dict(self):
        return {
            "template_id": self.template_id,
            "name": self.name,
            "kind": self.kind.value,
            "stats": dict(self.stats),
            "caps": dict(self.caps),
            "element": self.element.value,
            "element_power": self.element_power,
            "tier": self.tier,
            "upgrade": self.upgrade,
            "stack": self.stack,
            "max_stack": self.max_stack,
            "effects": dict(self.effects),
            "traits": list(self.traits),
            "description": self.description,
            "value": self.value,
            "uid": self.uid,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            template_id=data["template_id"],
            name=data["name"],
            kind=ItemKind(data["kind"]),
            stats=dict(data.get("stats", {})),
            caps=dict(data.get("caps", {})),
            element=Element(data.get("element", "neutral")),
            element_power=int(data.get("element_power", 0)),
            tier=int(data.get("tier", 1)),
            upgrade=int(data.get("upgrade", 0)),
            stack=int(data.get("stack", 1)),
            max_stack=int(data.get("max_stack", 1)),
            effects=dict(data.get("effects", {})),
            traits=tuple(data.get("traits", [])),
            description=data.get("description", ""),
            value=int(data.get("value", 0)),
            uid=data.get("uid", uuid.uuid4().hex[:12]),
        )


@dataclass
class EnemyTemplate:
    enemy_id: str
    name: str
    max_hp: int
    attack: int
    defense: int
    luck: int
    element: Element
    xp: int
    loot: tuple
    description: str
    elite: bool = False
    boss: bool = False
    traits: tuple = ()


@dataclass
class Stage:
    index: int
    name: str
    recommended_level: int
    enemies: tuple
    first_clear_item: str
    loot_rolls: int
    description: str
    act: int


class Hero:
    def __init__(self):
        self.name = "The Wayfarer"
        self.level = 1
        self.experience = 0
        self.base_stats = {"health": 40, "attack": 8, "defense": 4, "luck": 3}
        self.stat_points = 0
        self.inventory_capacity = 12
        self.inventory = []
        self.equipment = {"weapon": None, "shield": None, "ring1": None, "ring2": None}
        self.boost_uid = None
        self.gold = 0
        self.bone_dust = 0
        self.unlocked_stage = 1
        self.cleared_stages = set()
        self.best_turns = {}
        self.total_wins = 0
        self.total_losses = 0
        self.total_enemies = 0
        self.discovery = set()
        self.discovered_recipes = set()
        self.campaign_seed = random.SystemRandom().randrange(100000, 999999999)
        self.loot_counter = 0
        self.battle_counter = 0
        self.stage_clear_counts = {}
        self.pending_loot = []
        self.pending_routes = []
        self.pending_stage = 0
        self.training_count = 0

    @property
    def xp_needed(self):
        return 24 + self.level * 12

    def equipment_items(self):
        return [item for item in self.equipment.values() if item]

    def effect_total(self, effect):
        total = 0.0
        for item in self.equipment_items():
            value = item.effects.get(effect, 0)
            if isinstance(value, (int, float)):
                total += value
        return total

    def total_stats(self):
        result = dict(self.base_stats)
        for item in self.equipment_items():
            for key in result:
                result[key] += item.stats.get(key, 0)
        for key in result:
            result[key] = max(0, int(result[key]))
        result["health"] = max(1, result["health"])
        result["attack"] = max(1, result["attack"])
        return result

    def weapon_element(self):
        weapon = self.equipment.get("weapon")
        return weapon.element if weapon else Element.NEUTRAL

    def weapon_element_power(self):
        weapon = self.equipment.get("weapon")
        return weapon.element_power if weapon else 0

    def shield_element(self):
        shield = self.equipment.get("shield")
        return shield.element if shield else Element.NEUTRAL

    def shield_element_power(self):
        shield = self.equipment.get("shield")
        return shield.element_power if shield else 0

    def item_by_uid(self, uid):
        return next((item for item in self.inventory if item.uid == uid), None)

    def add_item(self, item):
        if item.stackable:
            remaining = item.stack
            stack_space = sum(current.max_stack - current.stack for current in self.inventory if current.compatible_stack(item))
            free_slots = self.inventory_capacity - len(self.inventory)
            if stack_space + free_slots * item.max_stack < remaining:
                return False
            for current in self.inventory:
                if current.compatible_stack(item) and current.stack < current.max_stack:
                    moved = min(remaining, current.max_stack - current.stack)
                    current.stack += moved
                    remaining -= moved
                    if remaining <= 0:
                        self.discovery.add(item.template_id)
                        return True
            first = True
            while remaining > 0:
                amount = min(remaining, item.max_stack)
                if first:
                    new_item = item
                    first = False
                else:
                    data = item.to_dict()
                    data["uid"] = uuid.uuid4().hex[:12]
                    new_item = Item.from_dict(data)
                new_item.stack = amount
                self.inventory.append(new_item)
                remaining -= amount
        else:
            if len(self.inventory) >= self.inventory_capacity:
                return False
            self.inventory.append(item)
        self.discovery.add(item.template_id)
        return True

    def can_add_item(self, item):
        if not item.stackable:
            return len(self.inventory) < self.inventory_capacity
        stack_space = sum(current.max_stack - current.stack for current in self.inventory if current.compatible_stack(item))
        free_slots = self.inventory_capacity - len(self.inventory)
        return stack_space + free_slots * item.max_stack >= item.stack

    def remove_item(self, uid, amount=1):
        item = self.item_by_uid(uid)
        if not item:
            return None
        if item.stack > amount:
            item.stack -= amount
            removed = Item.from_dict(item.to_dict())
            removed.uid = uuid.uuid4().hex[:12]
            removed.stack = amount
            return removed
        self.inventory.remove(item)
        if self.boost_uid == uid:
            self.boost_uid = None
        return item

    def equip(self, uid, target_slot=None):
        item = self.item_by_uid(uid)
        if not item or not item.slot:
            return False, "That item cannot be equipped."
        if item.kind == ItemKind.RING:
            if target_slot not in {"ring1", "ring2"}:
                target_slot = "ring1" if self.equipment["ring1"] is None else "ring2"
        else:
            target_slot = item.slot
        self.inventory.remove(item)
        old = self.equipment[target_slot]
        self.equipment[target_slot] = item
        if old:
            self.inventory.append(old)
        if self.boost_uid == uid:
            self.boost_uid = None
        return True, f"Equipped {item.display_name}."

    def unequip(self, slot):
        item = self.equipment.get(slot)
        if not item:
            return False, "That slot is already empty."
        if len(self.inventory) >= self.inventory_capacity:
            return False, "The backpack is full."
        self.equipment[slot] = None
        self.inventory.append(item)
        return True, f"Stored {item.display_name}."

    def set_boost(self, uid):
        item = self.item_by_uid(uid)
        if not item or item.kind != ItemKind.POTION:
            return False, "Only potions fit in the boost slot."
        self.boost_uid = uid
        return True, f"{item.display_name} is ready for the next dungeon."

    def gain_xp(self, amount):
        self.experience += max(0, int(amount))
        levels = 0
        while self.experience >= self.xp_needed:
            need = self.xp_needed
            self.experience -= need
            self.level += 1
            self.base_stats["health"] += 3
            self.stat_points += 1
            levels += 1
        return levels

    def spend_point(self, stat):
        if self.stat_points <= 0 or stat not in self.base_stats:
            return False
        self.base_stats[stat] += 4 if stat == "health" else 1
        self.stat_points -= 1
        return True

    @property
    def training_cost(self):
        return 20 + self.training_count * 15

    def train_with_dust(self):
        cost = self.training_cost
        if self.bone_dust < cost:
            return False, cost
        self.bone_dust -= cost
        self.training_count += 1
        self.stat_points += 1
        return True, cost

    def to_dict(self):
        return {
            "name": self.name,
            "level": self.level,
            "experience": self.experience,
            "base_stats": dict(self.base_stats),
            "stat_points": self.stat_points,
            "inventory_capacity": self.inventory_capacity,
            "inventory": [item.to_dict() for item in self.inventory],
            "equipment": {key: item.to_dict() if item else None for key, item in self.equipment.items()},
            "boost_uid": self.boost_uid,
            "gold": self.gold,
            "bone_dust": self.bone_dust,
            "unlocked_stage": self.unlocked_stage,
            "cleared_stages": sorted(self.cleared_stages),
            "best_turns": {str(key): value for key, value in self.best_turns.items()},
            "total_wins": self.total_wins,
            "total_losses": self.total_losses,
            "total_enemies": self.total_enemies,
            "discovery": sorted(self.discovery),
            "discovered_recipes": sorted(self.discovered_recipes),
            "campaign_seed": self.campaign_seed,
            "loot_counter": self.loot_counter,
            "battle_counter": self.battle_counter,
            "stage_clear_counts": {str(key): value for key, value in self.stage_clear_counts.items()},
            "pending_loot": [item.to_dict() for item in self.pending_loot],
            "pending_routes": list(self.pending_routes),
            "pending_stage": self.pending_stage,
            "training_count": self.training_count,
        }

    @classmethod
    def from_dict(cls, data):
        hero = cls()
        hero.name = data.get("name", hero.name)
        hero.level = int(data.get("level", 1))
        hero.experience = int(data.get("experience", 0))
        hero.base_stats.update({key: int(value) for key, value in data.get("base_stats", {}).items() if key in hero.base_stats})
        hero.stat_points = int(data.get("stat_points", 0))
        hero.inventory_capacity = 12
        hero.inventory = [Item.from_dict(item) for item in data.get("inventory", [])]
        equipment = data.get("equipment", {})
        for slot in hero.equipment:
            value = equipment.get(slot)
            hero.equipment[slot] = Item.from_dict(value) if value else None
        hero.boost_uid = data.get("boost_uid")
        if hero.boost_uid and not hero.item_by_uid(hero.boost_uid):
            hero.boost_uid = None
        hero.gold = int(data.get("gold", 0))
        hero.bone_dust = int(data.get("bone_dust", 0))
        hero.unlocked_stage = max(1, min(25, int(data.get("unlocked_stage", 1))))
        hero.cleared_stages = {int(value) for value in data.get("cleared_stages", []) if 1 <= int(value) <= 25}
        hero.best_turns = {int(key): int(value) for key, value in data.get("best_turns", {}).items() if 1 <= int(key) <= 25}
        hero.total_wins = int(data.get("total_wins", 0))
        hero.total_losses = int(data.get("total_losses", 0))
        hero.total_enemies = int(data.get("total_enemies", 0))
        hero.discovery = set(data.get("discovery", []))
        hero.discovered_recipes = set(data.get("discovered_recipes", []))
        hero.campaign_seed = int(data.get("campaign_seed", hero.campaign_seed))
        hero.loot_counter = int(data.get("loot_counter", 0))
        hero.battle_counter = int(data.get("battle_counter", 0))
        hero.stage_clear_counts = {int(key): int(value) for key, value in data.get("stage_clear_counts", {}).items()}
        hero.pending_loot = [Item.from_dict(item) for item in data.get("pending_loot", [])]
        hero.pending_routes = [str(value) for value in data.get("pending_routes", [])][:3]
        hero.pending_stage = int(data.get("pending_stage", 0))
        hero.training_count = int(data.get("training_count", 0))
        return hero
