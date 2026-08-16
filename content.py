import random

from models import Element, EnemyTemplate, Item, ItemKind, Stage


def _item(name, kind, stats=None, caps=None, element=Element.NEUTRAL, element_power=0, tier=1, max_stack=1, effects=None, traits=(), description="", value=0):
    return {
        "name": name,
        "kind": kind,
        "stats": dict(stats or {}),
        "caps": dict(caps or {}),
        "element": element,
        "element_power": element_power,
        "tier": tier,
        "max_stack": max_stack,
        "effects": dict(effects or {}),
        "traits": tuple(traits),
        "description": description,
        "value": value,
    }


ITEM_TEMPLATES = {
    "wayfarer_blade": _item(
        "Wayfarer's Blade", ItemKind.WEAPON,
        stats={}, caps={}, description="A plain, dependable sword carried from the first mile.", value=0,
    ),
    "rusted_falchion": _item(
        "Rusted Falchion", ItemKind.WEAPON,
        stats={"attack": 1}, caps={"attack": 2}, description="The edge is tired, but its weight still teaches a useful lesson.", value=12,
    ),
    "bone_cleaver": _item(
        "Bone Cleaver", ItemKind.WEAPON,
        stats={"attack": 2}, caps={"attack": 3, "luck": 1}, tier=1,
        effects={"execute_bonus": 0.05}, description="A broad blade carved from something too large to name.", value=24,
    ),
    "grave_hook": _item(
        "Grave Hook", ItemKind.WEAPON,
        stats={"attack": 3, "luck": 1}, caps={"attack": 4, "luck": 2}, tier=1,
        effects={"bleed_chance": 0.08}, description="Its hooked tip finds every loose plate and careless guard.", value=46,
    ),
    "emberbrand": _item(
        "Emberbrand", ItemKind.WEAPON,
        stats={"attack": 4}, caps={"attack": 5, "luck": 1}, element=Element.FIRE, element_power=2, tier=2,
        effects={"burn_chance": 0.12}, description="A furnace mark glows whenever the weapon tastes air.", value=78,
    ),
    "warden_pike": _item(
        "Warden Pike", ItemKind.WEAPON,
        stats={"attack": 4, "defense": 1}, caps={"attack": 6, "defense": 2}, tier=2,
        effects={"armor_pierce": 0.08}, description="Built to keep charging beasts exactly one bad decision away.", value=84,
    ),
    "rimefang": _item(
        "Rimefang", ItemKind.WEAPON,
        stats={"attack": 5, "defense": 1}, caps={"attack": 7, "defense": 2}, element=Element.ICE, element_power=3, tier=3,
        effects={"chill_chance": 0.16}, description="Frost grows along the fuller, even beside a warm fire.", value=138,
    ),
    "stormneedle": _item(
        "Stormneedle", ItemKind.WEAPON,
        stats={"attack": 5, "luck": 2}, caps={"attack": 7, "luck": 3}, element=Element.STORM, element_power=3, tier=3,
        effects={"double_strike_chance": 0.08}, description="A narrow blade that hums a heartbeat before lightning.", value=146,
    ),
    "venomthorn": _item(
        "Venomthorn", ItemKind.WEAPON,
        stats={"attack": 6, "luck": 1}, caps={"attack": 8, "luck": 3}, element=Element.VENOM, element_power=3, tier=4,
        effects={"poison_chance": 0.18}, description="Green sap beads along a thorn that never goes dry.", value=188,
    ),
    "lantern_sabre": _item(
        "Lantern Sabre", ItemKind.WEAPON,
        stats={"attack": 6, "health": 3}, caps={"attack": 8, "health": 6}, element=Element.ARCANE, element_power=2, tier=4,
        effects={"heal_on_victory": 4}, description="A captive blue flame remembers every foe it outlives.", value=196,
    ),
    "astral_edge": _item(
        "Astral Edge", ItemKind.WEAPON,
        stats={"attack": 8, "luck": 2}, caps={"attack": 10, "luck": 4}, element=Element.ARCANE, element_power=4, tier=4,
        effects={"crit_chance": 0.09}, description="Its edge seems a finger-width away from the world around it.", value=286,
    ),
    "sunken_king_blade": _item(
        "Sunken King's Blade", ItemKind.WEAPON,
        stats={"attack": 9, "health": 5}, caps={"attack": 11, "health": 9}, element=Element.STORM, element_power=4, tier=5,
        effects={"boss_damage": 0.12}, description="Saltwater runs from the hilt, though no sea remains nearby.", value=342,
    ),
    "voidglass_sabre": _item(
        "Voidglass Sabre", ItemKind.WEAPON,
        stats={"attack": 11, "luck": 4}, caps={"attack": 14, "luck": 6}, element=Element.ARCANE, element_power=6, tier=5,
        effects={"crit_chance": 0.12, "armor_pierce": 0.12}, description="The blade reflects stars that vanished before the first road was built.", value=520,
    ),
    "crownless_oath": _item(
        "Crownless Oath", ItemKind.WEAPON,
        stats={"attack": 12, "luck": 3}, caps={"attack": 15, "luck": 5}, tier=5,
        effects={"last_stand_damage": 0.22, "execute_bonus": 0.10}, description="A king broke this sword. A wanderer taught it purpose.", value=600,
    ),
    "patched_buckler": _item(
        "Patched Buckler", ItemKind.SHIELD,
        stats={}, caps={}, description="Leather, wood and stubbornness held together by old cord.", value=0,
    ),
    "splintered_guard": _item(
        "Splintered Guard", ItemKind.SHIELD,
        stats={"defense": 1}, caps={"defense": 2}, description="Its cracks are honest records of battles survived.", value=12,
    ),
    "bonewall": _item(
        "Bonewall", ItemKind.SHIELD,
        stats={"health": 2, "defense": 2}, caps={"health": 4, "defense": 3}, tier=1,
        effects={"block_chance": 0.05}, description="Layered ribs turn glancing blows with an unsettling rattle.", value=32,
    ),
    "cinder_plate": _item(
        "Cinder Plate", ItemKind.SHIELD,
        stats={"health": 4, "defense": 3}, caps={"health": 7, "defense": 4}, element=Element.FIRE, element_power=2, tier=2,
        effects={"element_resist": 0.12}, description="Heat rolls across the plate instead of through it.", value=82,
    ),
    "frost_mirror": _item(
        "Frost Mirror", ItemKind.SHIELD,
        stats={"health": 5, "defense": 4}, caps={"health": 8, "defense": 6}, element=Element.ICE, element_power=3, tier=3,
        effects={"element_resist": 0.16, "chill_attacker": 0.08}, description="An attacker briefly sees the cold end of every possible road.", value=142,
    ),
    "storm_aegis": _item(
        "Storm Aegis", ItemKind.SHIELD,
        stats={"defense": 5, "luck": 2}, caps={"defense": 7, "luck": 3}, element=Element.STORM, element_power=3, tier=3,
        effects={"element_resist": 0.16, "counter_chance": 0.07}, description="Copper veins answer violence with a sharp blue spark.", value=154,
    ),
    "venom_filter": _item(
        "Venom Filter", ItemKind.SHIELD,
        stats={"health": 7, "defense": 5}, caps={"health": 11, "defense": 7}, element=Element.VENOM, element_power=3, tier=4,
        effects={"element_resist": 0.18, "poison_resist": 0.35}, description="Moss and silver mesh drink poison before it reaches the bearer.", value=202,
    ),
    "runic_bastion": _item(
        "Runic Bastion", ItemKind.SHIELD,
        stats={"health": 9, "defense": 7}, caps={"health": 14, "defense": 9}, element=Element.ARCANE, element_power=4, tier=4,
        effects={"element_resist": 0.20, "barrier_on_start": 5}, description="Each rune is a locked door facing outward.", value=304,
    ),
    "kingstone_guard": _item(
        "Kingstone Guard", ItemKind.SHIELD,
        stats={"health": 13, "defense": 8}, caps={"health": 18, "defense": 11}, tier=5,
        effects={"block_chance": 0.12, "damage_reduction": 0.06}, description="A slab from a fallen throne that softens even the blows it cannot fully stop.", value=366,
    ),
    "last_gate": _item(
        "The Last Gate", ItemKind.SHIELD,
        stats={"health": 18, "defense": 11}, caps={"health": 24, "defense": 14}, element=Element.ARCANE, element_power=5, tier=5,
        effects={"block_chance": 0.15, "survive_lethal": 1}, description="It has never opened for an enemy and never closed on a friend.", value=580,
    ),
    "copper_loop": _item(
        "Copper Loop", ItemKind.RING,
        stats={"luck": 1}, caps={"luck": 2}, effects={"block_chance": 0.015}, description="The loop turns cold a heartbeat before danger arrives.", value=18,
    ),
    "bone_luck": _item(
        "Knucklebone Charm", ItemKind.RING,
        stats={"health": 1, "luck": 1}, caps={"health": 3, "luck": 2}, effects={"crit_chance": 0.015},
        description="The markings never land the same way twice.", value=28,
    ),
    "red_coil": _item(
        "Red Coil", ItemKind.RING,
        stats={"attack": 2}, caps={"attack": 3, "health": 2}, tier=2, effects={"low_health_attack": 0.10},
        description="It tightens around the finger when danger draws close.", value=62,
    ),
    "iron_vow": _item(
        "Iron Vow", ItemKind.RING,
        stats={"defense": 2}, caps={"defense": 3, "health": 3}, tier=2, effects={"block_chance": 0.04},
        description="A promise hammered into a shape too small to escape.", value=64,
    ),
    "vital_knot": _item(
        "Vital Knot", ItemKind.RING,
        stats={"health": 6}, caps={"health": 9, "defense": 1}, tier=2, effects={"healing_bonus": 0.10},
        description="A green cord knotted around a seed that still dreams of spring.", value=70,
    ),
    "ember_signet": _item(
        "Ember Signet", ItemKind.RING,
        stats={"attack": 2, "luck": 1}, caps={"attack": 4, "luck": 2}, element=Element.FIRE, element_power=2, tier=2,
        effects={"element_damage": 0.12}, description="Its seal leaves a perfect flame on cold wax.", value=118,
    ),
    "rime_signet": _item(
        "Rime Signet", ItemKind.RING,
        stats={"defense": 2, "luck": 2}, caps={"defense": 4, "luck": 3}, element=Element.ICE, element_power=2, tier=3,
        effects={"element_damage": 0.12}, description="Frost traces delicate maps across its silver face.", value=128,
    ),
    "storm_signet": _item(
        "Storm Signet", ItemKind.RING,
        stats={"attack": 2, "luck": 3}, caps={"attack": 4, "luck": 4}, element=Element.STORM, element_power=2, tier=3,
        effects={"element_damage": 0.12, "crit_chance": 0.04}, description="Thunder rolls softly when the ring changes hands.", value=142,
    ),
    "venom_signet": _item(
        "Venom Signet", ItemKind.RING,
        stats={"health": 4, "luck": 2}, caps={"health": 7, "luck": 4}, element=Element.VENOM, element_power=2, tier=4,
        effects={"element_damage": 0.14, "poison_resist": 0.18}, description="A sealed droplet circles beneath its cloudy stone.", value=176,
    ),
    "astral_orbit": _item(
        "Astral Orbit", ItemKind.RING,
        stats={"attack": 3, "luck": 3}, caps={"attack": 5, "luck": 5}, element=Element.ARCANE, element_power=3, tier=4,
        effects={"crit_chance": 0.07, "dodge_chance": 0.05}, description="A tiny moon circles the band without touching it.", value=276,
    ),
    "fortune_eclipse": _item(
        "Fortune Eclipse", ItemKind.RING,
        stats={"health": 8, "luck": 6}, caps={"health": 12, "luck": 8}, element=Element.ARCANE, element_power=4, tier=5,
        effects={"block_chance": 0.06, "crit_chance": 0.10}, description="Good fortune enters its shadow and returns sharpened.", value=540,
    ),
    "minor_tonic": _item(
        "Minor Tonic", ItemKind.POTION, max_stack=8,
        effects={"heal_flat": 12}, description="A bitter red tonic that closes small wounds between breaths.", value=10,
    ),
    "field_tonic": _item(
        "Field Tonic", ItemKind.POTION, tier=2, max_stack=8,
        effects={"heal_flat": 22}, description="Soldiers trust its ugly bottle more than a clean bandage.", value=24,
    ),
    "greater_tonic": _item(
        "Greater Tonic", ItemKind.POTION, tier=4, max_stack=6,
        effects={"heal_flat": 38}, description="Warmth returns from the center outward after one bright mouthful.", value=52,
    ),
    "vital_draught": _item(
        "Vital Draught", ItemKind.POTION, tier=5, max_stack=4,
        effects={"heal_percent": 0.65}, description="A living green light coils inside the stoppered glass.", value=96,
    ),
    "ironbark_tonic": _item(
        "Ironbark Tonic", ItemKind.POTION, tier=2, max_stack=5,
        effects={"battle_defense": 3, "duration_turns": 5}, description="For a few minutes, the skin remembers how to be a tree.", value=30,
    ),
    "fury_phial": _item(
        "Fury Phial", ItemKind.POTION, tier=3, max_stack=5,
        effects={"battle_attack": 4, "duration_turns": 5}, description="The stopper trembles whenever a weapon is drawn nearby.", value=42,
    ),
    "fortune_vial": _item(
        "Fortune Vial", ItemKind.POTION, tier=3, max_stack=5,
        effects={"battle_luck": 5, "duration_turns": 6}, description="Drink before the coin lands, never after.", value=44,
    ),
    "phoenix_cordial": _item(
        "Phoenix Cordial", ItemKind.POTION, tier=5, max_stack=3,
        effects={"revive_percent": 0.35}, description="A single golden feather dissolves when the bottle is opened.", value=120,
    ),
    "ember_essence": _item(
        "Ember Essence", ItemKind.ESSENCE, element=Element.FIRE, element_power=1, tier=2, max_stack=12,
        effects={"imbue_element": "fire", "imbue_power": 1}, description="Concentrated heat waiting for a worthy edge.", value=32,
    ),
    "rime_essence": _item(
        "Rime Essence", ItemKind.ESSENCE, element=Element.ICE, element_power=1, tier=3, max_stack=12,
        effects={"imbue_element": "ice", "imbue_power": 1}, description="A snowflake held forever at the instant before melting.", value=36,
    ),
    "storm_essence": _item(
        "Storm Essence", ItemKind.ESSENCE, element=Element.STORM, element_power=1, tier=3, max_stack=12,
        effects={"imbue_element": "storm", "imbue_power": 1}, description="A thunderclap folded into a shard of blue crystal.", value=44,
    ),
    "venom_essence": _item(
        "Venom Essence", ItemKind.ESSENCE, element=Element.VENOM, element_power=1, tier=4, max_stack=12,
        effects={"imbue_element": "venom", "imbue_power": 1}, description="A patient toxin refined until even glass avoids it.", value=50,
    ),
    "arcane_essence": _item(
        "Arcane Essence", ItemKind.ESSENCE, element=Element.ARCANE, element_power=1, tier=4, max_stack=10,
        effects={"imbue_element": "arcane", "imbue_power": 1}, description="A thought from somewhere beyond the visible sky.", value=72,
    ),
    "primal_essence": _item(
        "Primal Essence", ItemKind.ESSENCE, element=Element.NEUTRAL, element_power=2, tier=5, max_stack=6,
        effects={"raise_element_power": 2, "upgrade_cap": 1}, description="All five currents meet inside this colorless flame.", value=150,
    ),
    "bone_shard": _item(
        "Bone Shard", ItemKind.MATERIAL, max_stack=30,
        effects={"craft_value": 1}, description="Clean enough to carve, sharp enough to regret mishandling.", value=3,
    ),
    "tattered_hide": _item(
        "Tattered Hide", ItemKind.MATERIAL, max_stack=30,
        effects={"craft_value": 1}, description="Tough scraps suitable for straps, patches and ugly repairs.", value=4,
    ),
    "iron_scrap": _item(
        "Iron Scrap", ItemKind.MATERIAL, max_stack=30,
        effects={"craft_value": 2}, description="Bent nails and broken plates with one useful life remaining.", value=5,
    ),
    "ghost_salt": _item(
        "Ghost Salt", ItemKind.MATERIAL, tier=2, max_stack=24,
        effects={"craft_value": 3, "purify": 1}, description="Pale crystals that hiss near curses and old lies.", value=9,
    ),
    "ember_core": _item(
        "Ember Core", ItemKind.MATERIAL, tier=2, max_stack=20,
        effects={"craft_value": 4, "element_material": "fire"}, description="A furnace creature's last stubborn spark.", value=14,
    ),
    "frostglass": _item(
        "Frostglass", ItemKind.MATERIAL, tier=3, max_stack=20,
        effects={"craft_value": 4, "element_material": "ice"}, description="Clear ice that rings like glass and never softens.", value=16,
    ),
    "storm_wire": _item(
        "Storm Wire", ItemKind.MATERIAL, tier=3, max_stack=18,
        effects={"craft_value": 5, "element_material": "storm"}, description="Metal filament that twists toward distant thunder.", value=20,
    ),
    "void_resin": _item(
        "Void Resin", ItemKind.MATERIAL, tier=4, max_stack=16,
        effects={"craft_value": 6, "element_material": "arcane"}, description="Black resin used to bind objects that disagree with reality.", value=28,
    ),
    "crown_fragment": _item(
        "Crown Fragment", ItemKind.MATERIAL, tier=5, max_stack=10,
        effects={"craft_value": 10, "legendary_component": 1}, description="A warm piece of a crown whose ruler has been forgotten.", value=60,
    ),
}


_ITEM_TRAITS = {
    "rusted_falchion": ("keen",),
    "bone_cleaver": ("execution",),
    "grave_hook": ("piercing",),
    "emberbrand": ("combo",),
    "warden_pike": ("piercing", "guardian"),
    "rimefang": ("shatter",),
    "stormneedle": ("keen", "combo"),
    "venomthorn": ("leech", "execution"),
    "lantern_sabre": ("leech",),
    "astral_edge": ("keen", "piercing"),
    "sunken_king_blade": ("boss_hunter",),
    "voidglass_sabre": ("keen", "piercing", "shatter"),
    "crownless_oath": ("execution", "last_stand", "boss_hunter"),
    "splintered_guard": ("sturdy",),
    "bonewall": ("sturdy", "thorns"),
    "cinder_plate": ("warding",),
    "frost_mirror": ("warding", "thorns"),
    "storm_aegis": ("guardian",),
    "venom_filter": ("warding", "mending"),
    "runic_bastion": ("guardian", "warding"),
    "kingstone_guard": ("sturdy", "guardian"),
    "last_gate": ("guardian", "last_stand", "mending"),
    "copper_loop": ("alchemist",),
    "bone_luck": ("opener",),
    "red_coil": ("last_stand",),
    "iron_vow": ("sturdy",),
    "vital_knot": ("mending",),
    "ember_signet": ("opener",),
    "rime_signet": ("warding",),
    "storm_signet": ("keen", "combo"),
    "venom_signet": ("leech",),
    "astral_orbit": ("opener", "keen"),
    "fortune_eclipse": ("alchemist", "boss_hunter"),
}


for _template_id, _traits in _ITEM_TRAITS.items():
    ITEM_TEMPLATES[_template_id]["traits"] = _traits


def create_item(template_id, rng=None, stage=1):
    if template_id not in ITEM_TEMPLATES:
        raise KeyError(f"Unknown item template: {template_id}")
    roller = rng if rng is not None else random.Random()
    template = ITEM_TEMPLATES[template_id]
    stage = max(1, min(25, int(stage)))
    stats = dict(template["stats"])
    quality_limit = max(0, min(4, (stage - 1) // 6))
    for stat, cap in template["caps"].items():
        base = stats.get(stat, 0)
        headroom = max(0, int(cap) - int(base))
        if headroom and quality_limit:
            stats[stat] = base + roller.randint(0, min(headroom, quality_limit))
    rolled_bonus = sum(max(0, stats.get(key, 0) - template["stats"].get(key, 0)) for key in template["caps"])
    item_tier = template["tier"] if template["max_stack"] > 1 else max(template["tier"], min(5, (stage + 4) // 5))
    uid = f"{roller.randint(0, 16 ** 12 - 1):012x}"
    return Item(
        template_id=template_id,
        name=template["name"],
        kind=template["kind"],
        stats=stats,
        caps=dict(template["caps"]),
        element=template["element"],
        element_power=template["element_power"],
        tier=item_tier,
        max_stack=template["max_stack"],
        effects=dict(template["effects"]),
        traits=tuple(template["traits"]),
        description=template["description"],
        value=template["value"] + rolled_bonus * (4 + template["tier"] * 2),
        uid=uid,
    )


ENEMIES = {
    "dust_rat": EnemyTemplate("dust_rat", "Dust Rat", 18, 5, 1, 1, Element.NEUTRAL, 7, ("bone_shard", "tattered_hide", "minor_tonic"), "A cellar scavenger made fearless by grave dust."),
    "bone_scout": EnemyTemplate("bone_scout", "Bone Scout", 24, 6, 2, 2, Element.NEUTRAL, 9, ("bone_shard", "iron_scrap", "rusted_falchion", "minor_tonic"), "A restless skeleton sent ahead to count the living."),
    "crypt_slinger": EnemyTemplate("crypt_slinger", "Crypt Slinger", 22, 7, 1, 4, Element.NEUTRAL, 10, ("bone_shard", "ghost_salt", "copper_loop", "minor_tonic"), "It hurls grave pebbles with unnerving patience."),
    "marrow_guard": EnemyTemplate("marrow_guard", "Marrow Guard", 34, 7, 4, 2, Element.NEUTRAL, 13, ("bone_shard", "iron_scrap", "bonewall", "iron_vow"), "Old discipline remains after every softer thing has gone.", elite=True),
    "ossuary_captain": EnemyTemplate("ossuary_captain", "Ossuary Captain", 50, 9, 5, 4, Element.NEUTRAL, 24, ("grave_hook", "bonewall", "bone_luck", "ghost_salt"), "A commander assembled from the finest bones in the vault.", boss=True),
    "cinder_imp": EnemyTemplate("cinder_imp", "Cinder Imp", 38, 10, 3, 5, Element.FIRE, 16, ("ember_core", "ember_essence", "field_tonic", "red_coil"), "A laughing coal with claws and terrible manners."),
    "ash_hound": EnemyTemplate("ash_hound", "Ash Hound", 45, 11, 3, 4, Element.FIRE, 18, ("ember_core", "tattered_hide", "ember_essence", "fury_phial"), "It tracks warm blood through smoke-thick corridors."),
    "furnace_knight": EnemyTemplate("furnace_knight", "Furnace Knight", 58, 12, 6, 3, Element.FIRE, 22, ("iron_scrap", "ember_core", "cinder_plate", "warden_pike"), "Its armor is a walking kiln with no door.", elite=True),
    "coal_oracle": EnemyTemplate("coal_oracle", "Coal Oracle", 48, 14, 4, 8, Element.FIRE, 24, ("ghost_salt", "ember_essence", "ember_signet", "fortune_vial"), "Every crack in its black shell shows a different doomed future."),
    "pyre_warden": EnemyTemplate("pyre_warden", "Pyre Warden", 78, 15, 8, 6, Element.FIRE, 40, ("emberbrand", "cinder_plate", "ember_signet", "ember_core"), "The final keeper of a furnace built to burn names.", boss=True),
    "rime_widow": EnemyTemplate("rime_widow", "Rime Widow", 66, 16, 6, 9, Element.ICE, 28, ("frostglass", "rime_essence", "rime_signet", "field_tonic"), "Each glassy leg carries winter into the stone."),
    "icebound_thrall": EnemyTemplate("icebound_thrall", "Icebound Thrall", 78, 16, 9, 4, Element.ICE, 30, ("frostglass", "iron_scrap", "frost_mirror", "greater_tonic"), "A prisoner preserved long after the sentence lost meaning."),
    "thunder_crow": EnemyTemplate("thunder_crow", "Thunder Crow", 61, 19, 5, 12, Element.STORM, 31, ("storm_wire", "storm_essence", "storm_signet", "fortune_vial"), "Black wings cut bright seams into the frozen air."),
    "hail_sentinel": EnemyTemplate("hail_sentinel", "Hail Sentinel", 92, 18, 11, 6, Element.ICE, 36, ("frostglass", "storm_wire", "frost_mirror", "storm_aegis"), "A stone watchman polished smooth by a private blizzard.", elite=True),
    "tempest_matriarch": EnemyTemplate("tempest_matriarch", "Tempest Matriarch", 116, 21, 12, 11, Element.STORM, 56, ("rimefang", "stormneedle", "storm_aegis", "storm_signet"), "She nests where mountain weather is born.", boss=True),
    "mire_leech": EnemyTemplate("mire_leech", "Mire Leech", 94, 21, 9, 8, Element.VENOM, 39, ("tattered_hide", "venom_essence", "greater_tonic", "venom_signet"), "A swollen thing that leaves poisoned footprints before it arrives."),
    "plague_duelist": EnemyTemplate("plague_duelist", "Plague Duelist", 102, 23, 10, 13, Element.VENOM, 43, ("venom_essence", "venomthorn", "venom_signet", "fury_phial"), "Courtly manners survive beneath a mask full of spores."),
    "hex_moth": EnemyTemplate("hex_moth", "Hex Moth", 88, 24, 8, 16, Element.ARCANE, 44, ("ghost_salt", "arcane_essence", "fortune_vial", "astral_orbit"), "Its wings shed symbols that become curses when read."),
    "rune_golem": EnemyTemplate("rune_golem", "Rune Golem", 132, 22, 15, 5, Element.ARCANE, 50, ("iron_scrap", "void_resin", "runic_bastion", "arcane_essence"), "A walking argument written in a dead geometric language.", elite=True),
    "alchemist_revenant": EnemyTemplate("alchemist_revenant", "Alchemist Revenant", 156, 26, 15, 15, Element.VENOM, 72, ("venomthorn", "lantern_sabre", "venom_filter", "arcane_essence"), "Death only gave the old experimenter a quieter laboratory.", boss=True),
    "void_acolyte": EnemyTemplate("void_acolyte", "Void Acolyte", 128, 27, 13, 16, Element.ARCANE, 54, ("void_resin", "arcane_essence", "greater_tonic", "astral_edge"), "A pilgrim devoted to the silence between stars."),
    "crownless_guard": EnemyTemplate("crownless_guard", "Crownless Guard", 152, 28, 17, 10, Element.NEUTRAL, 59, ("crown_fragment", "kingstone_guard", "sunken_king_blade", "iron_scrap"), "It protects an empty throne from a kingdom that no longer exists.", elite=True),
    "starved_dragon": EnemyTemplate("starved_dragon", "Starved Dragon", 174, 31, 15, 15, Element.FIRE, 66, ("ember_core", "primal_essence", "sunken_king_blade", "phoenix_cordial"), "Hunger has sharpened every scale into a grievance."),
    "oathbreaker": EnemyTemplate("oathbreaker", "The Oathbreaker", 188, 32, 18, 18, Element.STORM, 74, ("storm_wire", "voidglass_sabre", "kingstone_guard", "fortune_eclipse"), "Once a hero, now the reason every promise needs a witness.", elite=True),
    "hollow_sovereign": EnemyTemplate("hollow_sovereign", "Hollow Sovereign", 248, 35, 21, 20, Element.ARCANE, 120, ("crown_fragment", "primal_essence", "last_gate", "fortune_eclipse", "voidglass_sabre"), "The throne is full. The ruler is not.", boss=True),
}


_ENEMY_TRAITS = {
    "dust_rat": (),
    "bone_scout": ("ambusher",),
    "crypt_slinger": ("ambusher",),
    "marrow_guard": ("guarded",),
    "ossuary_captain": ("heavy", "guarded"),
    "cinder_imp": ("enraged",),
    "ash_hound": ("ambusher", "enraged"),
    "furnace_knight": ("heavy", "guarded", "thorned"),
    "coal_oracle": ("enraged",),
    "pyre_warden": ("heavy", "enraged", "thorned"),
    "rime_widow": ("ambusher", "thorned"),
    "icebound_thrall": ("guarded",),
    "thunder_crow": ("ambusher",),
    "hail_sentinel": ("guarded", "thorned"),
    "tempest_matriarch": ("ambusher", "enraged"),
    "mire_leech": ("venomous", "leeching"),
    "plague_duelist": ("venomous", "ambusher"),
    "hex_moth": ("ambusher", "leeching"),
    "rune_golem": ("heavy", "guarded", "thorned"),
    "alchemist_revenant": ("venomous", "leeching", "enraged"),
    "void_acolyte": ("leeching",),
    "crownless_guard": ("heavy", "guarded"),
    "starved_dragon": ("heavy", "enraged"),
    "oathbreaker": ("ambusher", "enraged"),
    "hollow_sovereign": ("heavy", "guarded", "leeching", "enraged"),
}


for _enemy_id, _traits in _ENEMY_TRAITS.items():
    ENEMIES[_enemy_id].traits = _traits


STAGES = (
    Stage(1, "The First Rattle", 1, ("dust_rat", "bone_scout"), "minor_tonic", 1, "The road descends into a vault that has started breathing again.", 1),
    Stage(2, "Chalk Teeth", 1, ("dust_rat", "dust_rat", "crypt_slinger"), "splintered_guard", 1, "Small hunters test every shadow between the burial shelves.", 1),
    Stage(3, "The Empty Procession", 2, ("bone_scout", "crypt_slinger", "bone_scout"), "rusted_falchion", 2, "A funeral march repeats without mourners or destination.", 1),
    Stage(4, "Marrow Barracks", 3, ("bone_scout", "marrow_guard", "crypt_slinger"), "bone_luck", 2, "Dead soldiers drill beneath banners reduced to thread.", 1),
    Stage(5, "Captain of the Ossuary", 4, ("marrow_guard", "crypt_slinger", "ossuary_captain"), "bone_cleaver", 3, "The vault's assembled commander waits behind a gate of ribs.", 1),
    Stage(6, "Cinder Stair", 5, ("cinder_imp", "cinder_imp", "ash_hound"), "ember_essence", 2, "Each downward step is hotter than the last.", 2),
    Stage(7, "Kennels of Smoke", 6, ("ash_hound", "cinder_imp", "ash_hound"), "ember_signet", 2, "Something hungry circles beyond the furnace haze.", 2),
    Stage(8, "The Walking Kiln", 7, ("cinder_imp", "furnace_knight", "ash_hound"), "cinder_plate", 2, "Armored footsteps ring through chambers bright with slag.", 2),
    Stage(9, "Prophecies in Coal", 8, ("ash_hound", "coal_oracle", "furnace_knight"), "field_tonic", 3, "Every ember shows a future in which the road ends here.", 2),
    Stage(10, "Warden of the Namefire", 9, ("furnace_knight", "coal_oracle", "pyre_warden"), "emberbrand", 3, "A great furnace burns the names of those it defeats.", 2),
    Stage(11, "White Thread Pass", 10, ("rime_widow", "icebound_thrall", "rime_widow"), "rime_essence", 2, "Frozen silk marks the safe path and the trap alike.", 3),
    Stage(12, "Prisoners of Winter", 11, ("icebound_thrall", "rime_widow", "icebound_thrall"), "frost_mirror", 3, "Ancient captives wake when warm footsteps cross the ice.", 3),
    Stage(13, "Black Wings, Blue Sky", 12, ("thunder_crow", "rime_widow", "thunder_crow", "icebound_thrall"), "storm_essence", 3, "The storm sends scouts with feathers like knives.", 3),
    Stage(14, "Sentinel in the Hail", 13, ("icebound_thrall", "hail_sentinel", "thunder_crow"), "storm_signet", 3, "A patient guardian blocks the only break in the weather.", 3),
    Stage(15, "Nest of the Tempest", 14, ("hail_sentinel", "thunder_crow", "tempest_matriarch"), "rimefang", 4, "At the summit, a vast nest cradles an unfinished thunderstorm.", 3),
    Stage(16, "The Green Water", 15, ("mire_leech", "mire_leech", "plague_duelist"), "venom_essence", 3, "The flooded road glows wherever poison touches stone.", 4),
    Stage(17, "Courtyard of Masks", 16, ("plague_duelist", "mire_leech", "plague_duelist"), "venom_filter", 3, "Masked nobles continue a duel whose audience turned to moss.", 4),
    Stage(18, "Wingwritten Hex", 17, ("hex_moth", "plague_duelist", "hex_moth"), "arcane_essence", 3, "Curses flutter through the dark looking for someone to read them.", 4),
    Stage(19, "The Geometric Door", 18, ("mire_leech", "rune_golem", "hex_moth"), "astral_orbit", 4, "A door made of equations has appointed its own guard.", 4),
    Stage(20, "Revenant Laboratory", 19, ("rune_golem", "plague_duelist", "alchemist_revenant"), "runic_bastion", 4, "The final experiment has been waiting for a living ingredient.", 4),
    Stage(21, "Pilgrims of Nothing", 20, ("void_acolyte", "void_acolyte", "crownless_guard"), "greater_tonic", 3, "Silent pilgrims climb toward a palace cut from night.", 5),
    Stage(22, "The Unoccupied Throne", 21, ("crownless_guard", "void_acolyte", "crownless_guard"), "void_resin", 4, "An army guards a throne that refuses every claimant.", 5),
    Stage(23, "Hunger Beneath Gold", 22, ("void_acolyte", "starved_dragon", "crownless_guard"), "astral_edge", 4, "A dragon gnaws the gilded foundations from below.", 5),
    Stage(24, "Promise at World's End", 23, ("crownless_guard", "oathbreaker", "starved_dragon"), "crown_fragment", 4, "A broken hero offers one last chance to turn back.", 5),
    Stage(25, "The Hollow Crown", 25, ("void_acolyte", "oathbreaker", "crownless_guard", "hollow_sovereign"), "crownless_oath", 5, "Beyond every dungeon waits a ruler shaped exactly like absence.", 5),
)


for _stage in STAGES:
    _stage.loot_rolls = 3
    _stage.recommended_level = max(1, round(_stage.index * .75))


STAGE_BY_INDEX = {stage.index: stage for stage in STAGES}


RECIPES = {
    tuple(sorted(("rusted_falchion", "ember_essence"))): "emberbrand",
    tuple(sorted(("rusted_falchion", "rime_essence"))): "rimefang",
    tuple(sorted(("bone_cleaver", "storm_essence"))): "stormneedle",
    tuple(sorted(("grave_hook", "venom_essence"))): "venomthorn",
    tuple(sorted(("grave_hook", "arcane_essence"))): "lantern_sabre",
    tuple(sorted(("splintered_guard", "ember_essence"))): "cinder_plate",
    tuple(sorted(("splintered_guard", "rime_essence"))): "frost_mirror",
    tuple(sorted(("bonewall", "storm_essence"))): "storm_aegis",
    tuple(sorted(("bonewall", "venom_essence"))): "venom_filter",
    tuple(sorted(("bonewall", "arcane_essence"))): "runic_bastion",
    tuple(sorted(("copper_loop", "ember_essence"))): "ember_signet",
    tuple(sorted(("copper_loop", "rime_essence"))): "rime_signet",
    tuple(sorted(("copper_loop", "storm_essence"))): "storm_signet",
    tuple(sorted(("copper_loop", "venom_essence"))): "venom_signet",
    tuple(sorted(("copper_loop", "arcane_essence"))): "astral_orbit",
    tuple(sorted(("minor_tonic", "field_tonic"))): "greater_tonic",
    tuple(sorted(("emberbrand", "rimefang"))): "astral_edge",
    tuple(sorted(("runic_bastion", "crown_fragment"))): "last_gate",
    tuple(sorted(("astral_edge", "primal_essence"))): "voidglass_sabre",
    tuple(sorted(("fortune_eclipse", "primal_essence"))): "crownless_oath",
}


def recipe_result(first_template, second_template):
    return RECIPES.get(tuple(sorted((first_template, second_template))))


def starter_loadout():
    roller = random.Random(7319)
    blade = create_item("wayfarer_blade", roller, 1)
    shield = create_item("patched_buckler", roller, 1)
    tonic = create_item("minor_tonic", roller, 1)
    tonic.stack = 2
    bark = create_item("ironbark_tonic", roller, 1)
    bones = create_item("bone_shard", roller, 1)
    bones.stack = 3
    iron = create_item("iron_scrap", roller, 1)
    iron.stack = 2
    return {
        "equipment": {"weapon": blade, "shield": shield, "ring1": None, "ring2": None},
        "inventory": [tonic, bark, bones, iron],
    }


def _validate_content():
    if len(ITEM_TEMPLATES) < 35:
        raise ValueError("At least 35 item templates are required")
    kinds = {template["kind"] for template in ITEM_TEMPLATES.values()}
    if kinds != set(ItemKind):
        raise ValueError("Every item kind must be represented")
    for template_id, template in ITEM_TEMPLATES.items():
        required = {"stats", "caps", "effects", "traits", "description", "value"}
        if not required.issubset(template):
            raise ValueError(f"Incomplete item template: {template_id}")
        for stat, value in template["stats"].items():
            if stat not in {"health", "attack", "defense", "luck"} or not isinstance(value, int):
                raise ValueError(f"Invalid stat in item template: {template_id}")
        if sum(1 for value in template["stats"].values() if value) > 2:
            raise ValueError(f"Too many item attributes: {template_id}")
        for stat, cap in template["caps"].items():
            if cap < template["stats"].get(stat, 0):
                raise ValueError(f"Cap below base stat in item template: {template_id}")
    if len(ENEMIES) < 12:
        raise ValueError("At least 12 enemy templates are required")
    for enemy_id, enemy in ENEMIES.items():
        if enemy.enemy_id != enemy_id:
            raise ValueError(f"Enemy key mismatch: {enemy_id}")
        for template_id in enemy.loot:
            if template_id not in ITEM_TEMPLATES:
                raise ValueError(f"Unknown loot item {template_id} on {enemy_id}")
    if len(STAGES) != 25 or [stage.index for stage in STAGES] != list(range(1, 26)):
        raise ValueError("Stages must be exactly 1 through 25")
    if {stage.act for stage in STAGES} != {1, 2, 3, 4, 5}:
        raise ValueError("Stages must span five acts")
    if any(sum(1 for stage in STAGES if stage.act == act) != 5 for act in range(1, 6)):
        raise ValueError("Each act must contain five stages")
    for stage in STAGES:
        if len(stage.enemies) < 2:
            raise ValueError(f"Stage {stage.index} needs a multi-enemy wave")
        if stage.first_clear_item not in ITEM_TEMPLATES:
            raise ValueError(f"Unknown first-clear item on stage {stage.index}")
        for enemy_id in stage.enemies:
            if enemy_id not in ENEMIES:
                raise ValueError(f"Unknown enemy {enemy_id} on stage {stage.index}")
    for ingredients, result in RECIPES.items():
        if len(ingredients) != 2 or any(value not in ITEM_TEMPLATES for value in ingredients) or result not in ITEM_TEMPLATES:
            raise ValueError(f"Invalid recipe: {ingredients}")


_validate_content()
