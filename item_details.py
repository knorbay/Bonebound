"""Item mechanics written from the actual combat rules, separate from flavor text."""
TRAITS = {
    "keen": "+5% critical chance (total capped at 38%).",
    "piercing": "Ignore 20% enemy DEF (total pierce capped at 55%).",
    "execution": "+40% damage when the enemy has 25% HP or less.",
    "combo": "Every third attack deals 65% extra damage.",
    "guardian": "Halve the first damaging enemy hit per battle.",
    "shatter": "An enemy block charges your next strike for +35% damage.",
    "leech": "Restore 12% of direct hit damage as HP (minimum 1).",
    "boss_hunter": "+18% damage against bosses.",
    "last_stand": "Survive one lethal hit per battle.",
    "sturdy": "+5% full-block chance (total capped at 32%).",
    "thorns": "Return 10% of received hit damage (minimum 1).",
    "warding": "+8% resistance when shield and enemy elements match.",
    "mending": "Restore up to 2 HP on a full block.",
    "opener": "+4% critical chance on the first two hero attacks.",
    "alchemist": "+25% potion potency.",
}
PERCENT = {
    "bleed_chance": "chance of bleed: +28% hit damage",
    "burn_chance": "chance of burn: +28% hit damage",
    "chill_chance": "chance of frostbite: +28% hit damage",
    "poison_chance": "chance of poison: +28% hit damage",
    "double_strike_chance": "chance to deal +65% strike damage",
    "crit_chance": "additional critical chance (38% total cap)",
    "armor_pierce": "additional enemy DEF ignored (55% total cap)",
    "boss_damage": "additional boss damage",
    "block_chance": "additional full-block chance (32% total cap)",
    "counter_chance": "chance to retaliate for 35% ATK after taking damage",
    "element_resist": "resistance when shield and enemy elements match",
    "element_damage": "element damage bonus (full with advantage, half otherwise; none against same element)",
    "dodge_chance": "dodge chance (35% total cap)",
    "damage_reduction": "hit damage reduction (20% total cap)",
    "poison_resist": "resistance to the venomous enemy's +1 damage",
    "low_health_attack": "extra damage at 30% hero HP or less",
    "last_stand_damage": "extra damage at 30% hero HP or less",
    "execute_bonus": "extra damage at 25% enemy HP or less",
    "healing_bonus": "additional potion potency",
    "chill_attacker": "enemy ATK reduction after taking a hit (20% total cap)",
}


def mechanics(item):
    lines=[TRAITS[t] for t in item.traits if t in TRAITS]
    for key,label in PERCENT.items():
        if item.effects.get(key):
            lines.append(f"{item.effects[key]*100:g}% {label}.")
    for key,label in (("barrier_on_start","Barrier at battle start"),("heal_on_victory","HP restored per defeated enemy")):
        if item.effects.get(key):
            lines.append(f"{label}: {item.effects[key]:g}.")
    if item.effects.get("survive_lethal") and "last_stand" not in item.traits:
        lines.append("Survive one lethal hit per battle.")
    if item.kind.value == "potion":
        lines.append(item.stat_text()+". Consumed on use; stat boosts last the listed turns.")
    if item.kind.value in {"material","essence"}:
        lines.append("Combine with equipment in the Mixer; preview the result before crafting.")
    return lines
