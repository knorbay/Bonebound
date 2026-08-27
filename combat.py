import math
import random
from collections import deque
from dataclasses import dataclass
from enum import Enum

from content import ENEMIES
from models import Element, ItemKind


class BattleOutcome(Enum):
    ACTIVE = "active"
    VICTORY = "victory"
    DEFEAT = "defeat"
    RETREATED = "retreated"


@dataclass
class CombatEvent:
    event_type: str
    text: str
    actor: str = ""
    amount: int = 0
    critical: bool = False
    blocked: bool = False
    element: Element = Element.NEUTRAL


@dataclass
class EnemyState:
    enemy_id: str
    name: str
    max_hp: int
    hp: int
    attack: int
    defense: int
    luck: int
    element: Element
    xp: int
    elite: bool
    boss: bool


ELEMENT_ADVANTAGE = {
    Element.FIRE: Element.ICE,
    Element.ICE: Element.FIRE,
    Element.STORM: Element.VENOM,
    Element.VENOM: Element.ARCANE,
    Element.ARCANE: Element.STORM,
}


class CombatEngine:
    APPROACH_DURATION = 1.65

    def __init__(self, hero, stage, rng=None):
        self.hero = hero
        self.stage = stage
        self.rng = rng or random.Random()
        self.hero_stats = hero.total_stats()
        self.hero_max_hp = self.hero_stats["health"]
        self.hero_hp = self.hero_max_hp
        self.hero_barrier = max(0, round(hero.effect_total("barrier_on_start")))
        self.bonus_stats = {"attack": 0, "defense": 0, "luck": 0}
        self.enemy_index = -1
        self.enemy = None
        self.outcome = BattleOutcome.ACTIVE
        self.phase = "approach"
        self.timer = self.APPROACH_DURATION
        self.turns = 0
        self.defeated = 0
        self.xp_earned = 0
        self.levels_gained = 0
        self.total_damage = 0
        self.damage_taken = 0
        self.critical_hits = 0
        self.blocks = 0
        self.hero_attacks = 0
        self.enemy_attacks = 0
        self.enemy_chill = 0.0
        self.shatter_charge = False
        self.guardian_used = False
        self.last_stand_used = False
        self.revive_ratio = 0.0
        self.boost_turns = 0
        self.boost_used = False
        self.events = deque()
        self.history = deque(maxlen=9)
        self.hero_anim = "walk"
        self.enemy_anim = "idle"
        self.anim_clock = 0.0
        self._spawn_next_enemy()

    @property
    def active(self):
        return self.outcome == BattleOutcome.ACTIVE

    @property
    def wave_number(self):
        return self.enemy_index + 1

    @property
    def wave_total(self):
        return len(self.stage.enemies)

    @property
    def hero_attack(self):
        return self.hero_stats["attack"] + self.bonus_stats["attack"]

    @property
    def hero_defense(self):
        return self.hero_stats["defense"] + self.bonus_stats["defense"]

    @property
    def hero_luck(self):
        return self.hero_stats["luck"] + self.bonus_stats["luck"]

    @property
    def selected_boost(self):
        return self.hero.item_by_uid(self.hero.boost_uid) if self.hero.boost_uid else None

    def has_trait(self, name):
        return any(name in item.traits for item in self.hero.equipment_items())

    def enemy_has(self, name):
        template = ENEMIES[self.enemy.enemy_id] if self.enemy else None
        return bool(template and name in template.traits)

    def emit(self, event):
        self.events.append(event)
        self.history.append(event)

    def drain_events(self):
        result = list(self.events)
        self.events.clear()
        return result

    def _spawn_next_enemy(self):
        self.enemy_index += 1
        if self.enemy_index >= len(self.stage.enemies):
            self.outcome = BattleOutcome.VICTORY
            self.phase = "victory"
            self.hero_anim = "victory"
            self.emit(CombatEvent("victory", f"Dungeon {self.stage.index} cleared in {self.turns} rounds.", "hero"))
            return
        template = ENEMIES[self.stage.enemies[self.enemy_index]]
        difficulty = max(1.0, float(getattr(self.stage, "difficulty", 1.0)))
        health_scale = difficulty
        attack_scale = 1.0 + (difficulty - 1.0) * .82
        defense_scale = 1.0 + (difficulty - 1.0) * .54
        max_hp = max(1, round(template.max_hp * health_scale))
        self.enemy_chill = 0.0
        self.enemy = EnemyState(
            template.enemy_id,
            template.name,
            max_hp,
            max_hp,
            max(1, round(template.attack * attack_scale)),
            max(0, round(template.defense * defense_scale)),
            max(0, round(template.luck + (difficulty - 1.0) * 3)),
            template.element,
            max(1, round(template.xp * (1.0 + (difficulty - 1.0) * .58))),
            template.elite,
            template.boss,
        )
        self.phase = "approach"
        self.timer = self.APPROACH_DURATION
        self.hero_anim = "walk"
        self.enemy_anim = "run"
        self.emit(CombatEvent("wave", f"Wave {self.wave_number}/{self.wave_total}: {self.enemy.name} approaches.", "enemy", element=self.enemy.element))

    def _crit_chance(self, luck):
        bonus = (.05 if self.has_trait("keen") else 0) + self.hero.effect_total("crit_chance")
        if self.has_trait("opener") and self.hero_attacks < 3:
            bonus += .04
        return min(.38, .03 + luck * .012 + bonus)

    def _block_chance(self, luck):
        bonus = (.05 if self.has_trait("sturdy") else 0) + self.hero.effect_total("block_chance")
        return min(.32, max(0, luck) * .01 + bonus)

    def _element_attack_multiplier(self):
        weapon_element = self.hero.weapon_element()
        if weapon_element == Element.NEUTRAL:
            return 1.0
        power_bonus = min(.22, .05 + self.hero.weapon_element_power() * .01)
        if ELEMENT_ADVANTAGE.get(weapon_element) == self.enemy.element:
            return 1.25 + power_bonus + self.hero.effect_total("element_damage")
        if weapon_element == self.enemy.element:
            return .90 + power_bonus * .45
        return 1.0 + power_bonus + self.hero.effect_total("element_damage") * .5

    def _element_defense_multiplier(self):
        shield_element = self.hero.shield_element()
        if shield_element == self.enemy.element and shield_element != Element.NEUTRAL:
            ward = .08 if self.has_trait("warding") else 0
            resist = self.hero.effect_total("element_resist")
            return max(.35, .75 - ward - resist - min(.20, self.hero.shield_element_power() / 500))
        if ELEMENT_ADVANTAGE.get(self.enemy.element) == shield_element:
            return 1.12
        return 1.0

    def _hero_strike(self):
        self.turns += 1
        self.hero_attacks += 1
        self.hero_anim = "attack"
        self.enemy_anim = "idle"
        variance = self.rng.uniform(.90, 1.10)
        pierce = (.20 if self.has_trait("piercing") else 0) + self.hero.effect_total("armor_pierce")
        effective_defense = self.enemy.defense * max(.45, 1 - pierce)
        raw = self.hero_attack * variance - math.floor(effective_defense * .55)
        damage = max(1, round(raw * self._element_attack_multiplier()))
        weapon = self.hero.equipment.get("weapon")
        if weapon and weapon.upgrade:
            damage = max(1, round(damage * (1 + min(.24, weapon.upgrade * .035))))
        if self.hero_hp / self.hero_max_hp <= .30:
            low_bonus = self.hero.effect_total("low_health_attack") + self.hero.effect_total("last_stand_damage")
            damage = round(damage * (1 + low_bonus))
        if self.has_trait("execution") and self.enemy.hp / self.enemy.max_hp <= .25:
            damage = round(damage * (1.40 + self.hero.effect_total("execute_bonus")))
        if self.has_trait("combo") and self.hero_attacks % 3 == 0:
            damage = round(damage * 1.65)
        if self.has_trait("boss_hunter") and self.enemy.boss:
            damage = round(damage * (1.18 + self.hero.effect_total("boss_damage")))
        if self.rng.random() < self.hero.effect_total("double_strike_chance"):
            damage = round(damage * 1.65)
        if self.shatter_charge:
            damage = round(damage * 1.35)
            self.shatter_charge = False
        if self.enemy_has("guarded") and self.hero_attacks % 3 == 0:
            damage = max(1, round(damage * .55))
        critical = self.rng.random() < self._crit_chance(self.hero_luck)
        if critical:
            damage = max(2, round(damage * 1.75))
            self.critical_hits += 1
        blocked = self.rng.random() < min(.22, max(0, self.enemy.luck) * .01)
        if blocked:
            damage = 0
            if self.has_trait("shatter"):
                self.shatter_charge = True
        self.enemy.hp = max(0, self.enemy.hp - damage)
        self.total_damage += damage
        proc_events = []
        if damage and self.enemy.hp > 0:
            proc_data = (
                ("bleed_chance", "Bleed", Element.NEUTRAL),
                ("burn_chance", "Burn", Element.FIRE),
                ("chill_chance", "Frostbite", Element.ICE),
                ("poison_chance", "Poison", Element.VENOM),
            )
            for effect, label, element in proc_data:
                if self.rng.random() < self.hero.effect_total(effect):
                    extra = max(1, round(damage * .28))
                    self.enemy.hp = max(0, self.enemy.hp - extra)
                    self.total_damage += extra
                    proc_events.append(CombatEvent("proc", f"{label} adds {extra} damage.", "hero", extra, element=element))
        if damage and self.has_trait("leech"):
            self.hero_hp = min(self.hero_max_hp, self.hero_hp + max(1, round(damage * .12)))
        if damage and self.enemy_has("thorned"):
            reflected = max(1, round(damage * .10))
            self.hero_hp = max(0, self.hero_hp - reflected)
            self.damage_taken += reflected
            self.emit(CombatEvent("thorns", f"Thorns return {reflected} damage.", "enemy", reflected, element=self.enemy.element))
        if blocked:
            text = f"{self.enemy.name} completely blocks the attack."
        elif critical:
            text = f"Critical strike deals {damage} damage to {self.enemy.name}."
        else:
            text = f"You deal {damage} damage to {self.enemy.name}."
        self.emit(CombatEvent("hero_hit", text, "hero", damage, critical, blocked, self.hero.weapon_element()))
        for event in proc_events:
            self.emit(event)
        if self.hero_hp <= 0 and not self._survive_lethal():
            self._defeat("Thorns claim the final breath.")
            return
        if self.enemy.hp <= 0:
            self._award_enemy_defeat()
        else:
            self.phase = "enemy_windup"
            self.timer = .62

    def _award_enemy_defeat(self):
        self.enemy.hp = 0
        self.enemy_anim = "defeat"
        self.defeated += 1
        self.hero.total_enemies += 1
        self.xp_earned += self.enemy.xp
        gained = self.hero.gain_xp(self.enemy.xp)
        self.levels_gained += gained
        text = f"{self.enemy.name} falls. +{self.enemy.xp} XP."
        if gained:
            text += f" Level {self.hero.level} reached."
        self.emit(CombatEvent("enemy_down", text, "hero", self.enemy.xp, element=self.enemy.element))
        victory_heal = round(self.hero.effect_total("heal_on_victory"))
        if victory_heal:
            restored = min(victory_heal, self.hero_max_hp - self.hero_hp)
            self.hero_hp += restored
            if restored:
                self.emit(CombatEvent("heal", f"Your weapon restores {restored} HP.", "hero", restored))
        self.phase = "wave_clear"
        self.timer = .95

    def _survive_lethal(self):
        if self.revive_ratio > 0:
            restored = max(1, round(self.hero_max_hp * self.revive_ratio))
            self.hero_hp = restored
            self.revive_ratio = 0
            self.emit(CombatEvent("revive", f"The cordial restores {restored} HP after a lethal hit.", "hero", restored))
            return True
        if (self.has_trait("last_stand") or self.hero.effect_total("survive_lethal")) and not self.last_stand_used:
            self.last_stand_used = True
            self.hero_hp = 1
            self.emit(CombatEvent("last_stand", "A charm holds you at 1 HP.", "hero", 1))
            return True
        return False

    def _defeat(self, text=None):
        self.outcome = BattleOutcome.DEFEAT
        self.phase = "defeat"
        self.hero_anim = "defeat"
        self.hero.total_losses += 1
        self.emit(CombatEvent("defeat", text or f"The dungeon wins, but {self.xp_earned} earned XP is kept.", "enemy"))

    def _enemy_strike(self):
        self.enemy_attacks += 1
        self.enemy_anim = "attack"
        self.hero_anim = "idle"
        blocked = self.rng.random() < self._block_chance(self.hero_luck)
        critical = self.rng.random() < min(.30, .03 + self.enemy.luck * .012)
        variance = self.rng.uniform(.90, 1.10)
        enemy_attack = self.enemy.attack
        if self.enemy_has("heavy") and self.enemy_attacks % 3 == 0:
            enemy_attack *= 1.45
        if self.enemy_has("enraged") and self.enemy.hp / self.enemy.max_hp <= .30:
            enemy_attack *= 1.30
        enemy_attack *= 1 - min(.20, self.enemy_chill)
        mitigated = enemy_attack * variance * 14 / (14 + max(0, self.hero_defense))
        damage = max(1, round(mitigated * self._element_defense_multiplier()))
        if critical:
            damage = max(2, round(damage * 1.65))
        damage_reduction = min(.20, max(0.0, self.hero.effect_total("damage_reduction")))
        if damage_reduction:
            damage = max(1, round(damage * (1 - damage_reduction)))
        if blocked:
            damage = 0
            self.blocks += 1
            if self.has_trait("mending"):
                restored = min(2, self.hero_max_hp - self.hero_hp)
                self.hero_hp += restored
                if restored:
                    self.emit(CombatEvent("heal", f"The shield mend restores {restored} HP.", "hero", restored))
        if damage and self.has_trait("guardian") and not self.guardian_used:
            damage = max(1, round(damage * .50))
            self.guardian_used = True
        if damage and self.enemy_has("venomous") and self.rng.random() >= min(.85, self.hero.effect_total("poison_resist")):
            damage += 1
        if self.rng.random() < min(.35, self.hero.effect_total("dodge_chance")):
            damage = 0
            blocked = True
            self.blocks += 1
        if self.hero_barrier and damage:
            absorbed = min(self.hero_barrier, damage)
            self.hero_barrier -= absorbed
            damage -= absorbed
            self.emit(CombatEvent("barrier", f"The starting barrier absorbs {absorbed} damage.", "hero", absorbed))
        self.hero_hp = max(0, self.hero_hp - damage)
        self.damage_taken += damage
        if damage and self.enemy_has("leeching"):
            self.enemy.hp = min(self.enemy.max_hp, self.enemy.hp + max(1, round(damage * .15)))
        if blocked:
            text = "Luck turns the blow into a complete block."
        elif critical:
            text = f"{self.enemy.name} lands a critical hit for {damage}."
        else:
            text = f"{self.enemy.name} deals {damage} damage."
        self.emit(CombatEvent("enemy_hit", text, "enemy", damage, critical, blocked, self.enemy.element))
        chill_power = max(0.0, self.hero.effect_total("chill_attacker"))
        if damage and chill_power and self.enemy_chill < .20:
            self.enemy_chill = min(.20, self.enemy_chill + chill_power)
            reduction = round(self.enemy_chill * 100)
            self.emit(CombatEvent("chill", f"Frost Mirror chills {self.enemy.name}; its attack falls by {reduction}%.", "hero", reduction, element=Element.ICE))
        retaliation = 0
        if damage and self.has_trait("thorns"):
            retaliation += max(1, round(damage * .10))
        counter_chance = self.hero.effect_total("counter_chance")
        if damage and counter_chance and self.rng.random() < counter_chance:
            retaliation += max(1, round(self.hero_attack * .35))
        if retaliation:
            self.enemy.hp = max(0, self.enemy.hp - retaliation)
            self.total_damage += retaliation
            self.emit(CombatEvent("counter", f"Retaliation deals {retaliation} damage.", "hero", retaliation, element=self.hero.weapon_element()))
        if self.boost_turns > 0:
            self.boost_turns -= 1
            if self.boost_turns == 0 and any(self.bonus_stats.values()):
                self.bonus_stats = {"attack": 0, "defense": 0, "luck": 0}
                self.emit(CombatEvent("boost_fade", "The temporary potion bonuses fade.", "hero"))
        if self.hero_hp <= 0:
            if self._survive_lethal():
                if self.enemy.hp <= 0:
                    self._award_enemy_defeat()
                else:
                    self.phase = "player_windup"
                    self.timer = .62
                return
            self._defeat()
        elif self.enemy.hp <= 0:
            self._award_enemy_defeat()
        else:
            self.phase = "player_windup"
            self.timer = .62

    def use_boost(self):
        if not self.active or self.boost_used:
            return False, "The boost slot has already been used."
        item = self.selected_boost
        if not item or item.kind != ItemKind.POTION:
            return False, "No potion is prepared in the boost slot."
        has_heal = bool(item.effects.get("heal_flat") or item.effects.get("heal_percent") or item.effects.get("heal"))
        has_other = bool(item.effects.get("revive_percent") or any(item.effects.get(f"battle_{stat}") for stat in ("attack", "defense", "luck")))
        if has_heal and not has_other and self.hero_hp >= self.hero_max_hp:
            return False, "Health is already full; the healing potion was not consumed."
        consumed = self.hero.remove_item(item.uid, 1)
        if not consumed:
            return False, "The prepared potion is missing."
        self.boost_used = True
        heal = int(consumed.effects.get("heal_flat", consumed.effects.get("heal", 0)))
        heal += round(self.hero_max_hp * float(consumed.effects.get("heal_percent", 0)))
        potency = (1.25 if self.has_trait("alchemist") else 1.0) + self.hero.effect_total("healing_bonus")
        heal = round(heal * potency)
        healed = min(heal, self.hero_max_hp - self.hero_hp)
        self.hero_hp += healed
        for stat in ("attack", "defense", "luck"):
            effect = consumed.effects.get(f"battle_{stat}", consumed.effects.get(stat, 0))
            self.bonus_stats[stat] += round(int(effect) * potency)
        self.boost_turns = max(self.boost_turns, int(consumed.effects.get("duration_turns", 0)))
        self.revive_ratio = max(self.revive_ratio, float(consumed.effects.get("revive_percent", 0)))
        details = []
        if healed:
            details.append(f"{healed} HP")
        for stat in ("attack", "defense", "luck"):
            value = round(int(consumed.effects.get(f"battle_{stat}", consumed.effects.get(stat, 0))) * potency)
            if value:
                details.append(f"+{value} {stat.upper()}")
        if self.revive_ratio:
            details.append(f"revive {round(self.revive_ratio * 100)}%")
        if not details:
            details.append("no immediate effect")
        message = f"Used {consumed.display_name}: " + ", ".join(details) + "."
        self.emit(CombatEvent("boost", message, "hero", healed, element=consumed.element))
        return True, message

    def retreat(self):
        if not self.active:
            return False
        self.outcome = BattleOutcome.RETREATED
        self.phase = "retreated"
        self.hero_anim = "idle"
        self.emit(CombatEvent("retreat", f"You retreat with {self.xp_earned} earned XP.", "hero"))
        return True

    def _advance(self):
        if not self.active:
            return
        if self.phase == "approach":
            if self.enemy_has("ambusher"):
                self.phase = "enemy_windup"
                self.timer = .50
                self.enemy_anim = "ready"
                self.emit(CombatEvent("turn", f"{self.enemy.name} ambushes first.", "enemy"))
            else:
                self.phase = "player_windup"
                self.timer = .58
                self.hero_anim = "ready"
                self.emit(CombatEvent("turn", "You strike first.", "hero"))
        elif self.phase == "player_windup":
            self.phase = "hero_attack"
            self.timer = .28
            self.hero_anim = "attack"
            self.enemy_anim = "idle"
        elif self.phase == "hero_attack":
            self._hero_strike()
        elif self.phase == "enemy_windup":
            self.phase = "enemy_attack"
            self.timer = .26
            self.enemy_anim = "attack"
            self.hero_anim = "idle"
        elif self.phase == "enemy_attack":
            self._enemy_strike()
        elif self.phase == "wave_clear":
            self._spawn_next_enemy()

    def update(self, dt):
        self.anim_clock += dt
        if not self.active:
            return
        remaining = max(0.0, dt)
        safety = 0
        while remaining > 0 and self.active and safety < 8:
            safety += 1
            if remaining < self.timer:
                self.timer -= remaining
                remaining = 0
            else:
                remaining -= self.timer
                self.timer = 0
                self._advance()

    def summary(self):
        return {
            "outcome": self.outcome.value,
            "turns": self.turns,
            "defeated": self.defeated,
            "xp": self.xp_earned,
            "levels": self.levels_gained,
            "damage": self.total_damage,
            "taken": self.damage_taken,
            "criticals": self.critical_hits,
            "blocks": self.blocks,
        }
