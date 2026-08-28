import hashlib
import io
import json
import math
import os
import sys
import zipfile
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
ITEM_ROOT = ROOT / "assets" / "items"
HERO_ROOT = ROOT / "assets" / "characters" / "hero_unarmored"
ENEMY_ROOT = ROOT / "assets" / "characters" / "enemies_original"
THIRD_PARTY_ROOT = ROOT / "assets" / "third_party"
SVEN_HERO_SOURCE = THIRD_PARTY_ROOT / "sven_hero_knight" / "HeroKnight.pyxel"
ARSENAL_ROOT = THIRD_PARTY_ROOT / "idylwild_arsenal"
SHIELD_SOURCE_ROOT = THIRD_PARTY_ROOT / "7soul_shields"
JEWELRY_SOURCE_ROOT = THIRD_PARTY_ROOT / "7soul_jewelry"
POTION_SOURCE_ROOT = THIRD_PARTY_ROOT / "7soul_potions"


EXTERNAL_ITEM_SOURCES = {
    "weapon": (
        "sword1.png", "sword2.png", "sword3.png", "sword4.png", "sword5.png",
        "dagger1.png", "dagger2.png", "dagger3.png", "dagger4.png", "dagger5.png",
        "axe1.png", "axe2.png", "axe3.png", "axe4.png", "hammer1.png", "hammer2.png",
        "spear1.png", "spear2.png", "polearm1.png", "polearm2.png", "polearm3.png",
        "staff1.png", "staff2.png", "staff3.png", "scythe1.png", "scythe2.png",
    ),
    "shield": (
        "E_Wood01.png", "E_Wood02.png", "E_Wood03.png", "E_Wood04.png",
        "E_Metal01.png", "E_Metal02.png", "E_Metal03.png", "E_Metal04.png",
        "E_Metal05.png", "E_Metal06.png", "E_Metal07.png", "E_Metal08.png",
        "E_Metal09.png", "E_Gold01.png", "E_Gold02.png",
    ),
    "ring": (
        "ring_01.png", "ring_02.png", "ring_03_blue.png", "ring_03_gray.png",
        "ring_03_green.png", "ring_03_light_green.png", "ring_03_light_red.png",
        "ring_03_pink.png", "ring_03_purple.png", "ring_03_red.png",
        "necklace_01.png", "necklace_02.png", "necklace_03.png", "necklace_04.png",
        "necklace_05.png", "necklace_06.png", "necklace_07.png", "necklace_08.png",
    ),
    "potion": (
        "potion_01_red.png", "potion_02_blue.png", "potion_03_yellow.png",
        "potion_04_green.png", "potion_05_pink.png", "potion_06_blue.png",
        "potion_07_orange.png", "potion_08_red.png", "potion_09_green.png",
        "vial_01.png", "vial_02.png", "medicine_01.png", "medicine_04.png",
        "medicine_07.png", "antidote.png", "bottle_01.png", "bottle_02.png",
    ),
}


ELEMENT_PALETTES = {
    "neutral": ((202, 196, 177), (126, 112, 93), (238, 230, 207)),
    "fire": ((229, 83, 42), (126, 42, 31), (255, 184, 68)),
    "ice": ((79, 186, 221), (43, 91, 142), (190, 239, 247)),
    "storm": ((232, 199, 55), (104, 83, 42), (255, 245, 154)),
    "venom": ((105, 187, 68), (48, 91, 48), (189, 235, 96)),
    "arcane": ((173, 83, 211), (75, 43, 116), (229, 167, 244)),
}

POTION_PALETTES = {
    "minor_tonic": ((202, 63, 70), (104, 33, 44), (255, 151, 118)),
    "field_tonic": ((220, 111, 48), (119, 57, 35), (255, 198, 106)),
    "greater_tonic": ((230, 57, 68), (117, 26, 46), (255, 207, 102)),
    "vital_draught": ((65, 196, 111), (29, 92, 68), (175, 245, 145)),
    "ironbark_tonic": ((91, 153, 76), (57, 76, 43), (186, 212, 115)),
    "fury_phial": ((231, 76, 35), (127, 32, 29), (255, 174, 66)),
    "fortune_vial": ((161, 87, 209), (70, 40, 111), (229, 161, 245)),
    "blended_tonic": ((73, 191, 185), (84, 47, 119), (241, 145, 225)),
    "phoenix_cordial": ((240, 154, 35), (133, 46, 30), (255, 235, 129)),
    "bloodsalt_elixir": ((194, 45, 69), (78, 22, 42), (255, 131, 119)),
    "stoneblood_flask": ((122, 126, 132), (54, 58, 66), (214, 198, 158)),
    "stormstep_serum": ((70, 158, 230), (42, 55, 130), (247, 234, 94)),
    "moonmilk_cordial": ((184, 184, 231), (71, 64, 125), (250, 242, 205)),
    "last_breath_phial": ((77, 67, 99), (28, 25, 40), (205, 179, 232)),
}


def seed_for(value):
    return int(hashlib.sha256(value.encode("utf-8")).hexdigest()[:8], 16)


def outline_line(surface, color, start, end, width=2):
    pygame.draw.line(surface, (26, 24, 27), start, end, width + 2)
    pygame.draw.line(surface, color, start, end, width)


def weapon_icon(surface, template_id, seed, palette):
    main, dark, light = palette
    profile = {
        "rusted_falchion": "curve", "bone_cleaver": "cleaver", "grave_hook": "hook",
        "emberbrand": "flame", "warden_pike": "pike", "rimefang": "fang",
        "stormneedle": "needle", "venomthorn": "thorn", "lantern_sabre": "curve",
        "astral_edge": "split", "sunken_king_blade": "royal", "voidglass_sabre": "curve",
        "crownless_oath": "great", "pilgrim_crook": "crook", "slag_hammer": "hammer",
        "moonlit_khopesh": "khopesh", "basilisk_needle": "rapier", "sovereign_axe": "axe",
    }.get(template_id, "straight")
    handle_start, hilt = (4, 28), (8, 24)
    outline_line(surface, (121, 73, 42), handle_start, hilt, 3)
    if profile == "crook":
        outline_line(surface, (112, 77, 47), (5, 28), (23, 8), 3)
        pygame.draw.lines(surface, (25, 23, 27), False, [(22, 9), (27, 5), (29, 8), (26, 12)], 5)
        pygame.draw.lines(surface, light, False, [(22, 9), (27, 6), (28, 8), (25, 11)], 2)
        pygame.draw.circle(surface, main, (15, 18), 3)
        pygame.draw.circle(surface, light, (15, 18), 1)
        return
    if profile == "hammer":
        outline_line(surface, (112, 70, 43), (6, 27), (21, 10), 4)
        pygame.draw.polygon(surface, (24, 23, 27), [(16, 5), (27, 5), (30, 10), (24, 15), (14, 12)])
        pygame.draw.polygon(surface, dark, [(17, 7), (26, 7), (27, 10), (23, 13), (16, 11)])
        pygame.draw.line(surface, light, (18, 7), (26, 8), 2)
        pygame.draw.circle(surface, main, (24, 10), 2)
        return
    if profile == "khopesh":
        pygame.draw.line(surface, (25, 23, 27), (6, 20), (14, 27), 5)
        pygame.draw.line(surface, main, (7, 20), (14, 26), 2)
        pygame.draw.lines(surface, (25, 23, 27), False, [(9, 23), (17, 16), (20, 8), (28, 4), (27, 11), (23, 15)], 7)
        pygame.draw.lines(surface, light, False, [(10, 22), (18, 15), (21, 8), (27, 5), (26, 10), (22, 14)], 3)
        return
    if profile == "rapier":
        pygame.draw.circle(surface, main, (10, 22), 5, 2)
        outline_line(surface, light, (9, 22), (28, 4), 2)
        pygame.draw.polygon(surface, dark, [(27, 3), (30, 2), (29, 6)])
        pygame.draw.circle(surface, light, (11, 21), 1)
        return
    if profile == "axe":
        outline_line(surface, (112, 70, 43), (6, 28), (22, 8), 4)
        pygame.draw.polygon(surface, (24, 23, 28), [(17, 5), (25, 3), (30, 7), (26, 16), (20, 12), (15, 13)])
        pygame.draw.polygon(surface, dark, [(19, 6), (25, 5), (28, 7), (25, 13), (21, 11), (17, 11)])
        pygame.draw.line(surface, light, (20, 6), (27, 7), 2)
        pygame.draw.rect(surface, main, (21, 8, 3, 3))
        return
    if profile == "pike":
        outline_line(surface, (117, 79, 48), (6, 27), (24, 8), 3)
        pygame.draw.polygon(surface, (24, 23, 27), [(22, 9), (28, 3), (26, 12)])
        pygame.draw.polygon(surface, light, [(23, 9), (27, 5), (25, 11)])
        pygame.draw.line(surface, main, (8, 23), (12, 27), 2)
        return
    pygame.draw.line(surface, (25, 23, 27), (6, 20), (14, 27), 5)
    pygame.draw.line(surface, main, (7, 20), (14, 26), 2)
    if profile in {"cleaver", "great", "royal"}:
        widths = {"cleaver": 7, "great": 6, "royal": 6}
        end = (25, 6 if profile != "cleaver" else 8)
        outline_line(surface, (220, 219, 207), hilt, end, widths[profile])
        pygame.draw.line(surface, light, (11, 21), end, 2)
        if profile == "cleaver":
            pygame.draw.polygon(surface, dark, [(18, 8), (27, 4), (26, 12)])
        elif profile == "royal":
            pygame.draw.polygon(surface, main, [(22, 8), (27, 3), (26, 11)])
    elif profile == "hook":
        pygame.draw.lines(surface, (25, 23, 27), False, [(8, 23), (22, 9), (27, 10), (25, 15)], 6)
        pygame.draw.lines(surface, (215, 213, 200), False, [(9, 22), (22, 9), (26, 10), (24, 14)], 3)
        pygame.draw.line(surface, light, (11, 20), (23, 9), 1)
    elif profile == "thorn":
        pygame.draw.lines(surface, (25, 23, 27), False, [(8, 23), (14, 20), (15, 15), (21, 13), (22, 7), (27, 4)], 6)
        pygame.draw.lines(surface, light, False, [(9, 22), (15, 19), (16, 15), (22, 12), (23, 7), (27, 4)], 3)
    elif profile == "flame":
        outline_line(surface, (224, 210, 185), hilt, (25, 7), 5)
        pygame.draw.polygon(surface, main, [(18, 13), (25, 4), (24, 11), (29, 8), (25, 16)])
        pygame.draw.line(surface, light, (11, 21), (24, 8), 1)
    elif profile == "fang":
        pygame.draw.polygon(surface, (25, 23, 27), [(7, 23), (22, 7), (27, 4), (23, 14), (11, 25)])
        pygame.draw.polygon(surface, light, [(10, 22), (23, 7), (25, 6), (22, 13), (12, 23)])
    elif profile == "needle":
        outline_line(surface, light, hilt, (28, 4), 2)
        pygame.draw.line(surface, main, (8, 20), (13, 25), 2)
    elif profile == "split":
        outline_line(surface, (222, 220, 209), hilt, (25, 6), 4)
        pygame.draw.line(surface, dark, (14, 18), (25, 7), 1)
        pygame.draw.line(surface, light, (11, 21), (22, 10), 1)
    else:
        end = (25, 6) if profile == "straight" else (27, 7)
        outline_line(surface, (222, 220, 209), hilt, end, 4)
        pygame.draw.line(surface, light, (11, 21), end, 1)
        if profile == "curve":
            pygame.draw.polygon(surface, dark, [(22, 8), (28, 4), (25, 12)])


def shield_icon(surface, template_id, seed, palette):
    main, dark, light = palette
    if template_id == "patched_buckler":
        pygame.draw.circle(surface, (25, 24, 27), (16, 16), 14)
        pygame.draw.circle(surface, (103, 65, 39), (16, 16), 12)
        pygame.draw.circle(surface, main, (16, 16), 12, 2)
        pygame.draw.line(surface, light, (16, 5), (16, 27), 2)
        pygame.draw.line(surface, dark, (7, 16), (25, 16), 2)
        return
    if template_id == "gravewood_targe":
        pygame.draw.circle(surface, (24, 23, 27), (16, 16), 14)
        pygame.draw.circle(surface, (81, 55, 39), (16, 16), 12)
        pygame.draw.circle(surface, main, (16, 16), 11, 2)
        for angle in range(0, 360, 60):
            end = (round(16 + math.cos(math.radians(angle)) * 10), round(16 + math.sin(math.radians(angle)) * 10))
            pygame.draw.line(surface, light, (16, 16), end, 2)
        pygame.draw.circle(surface, dark, (16, 16), 4)
        pygame.draw.circle(surface, light, (15, 15), 1)
        return
    if template_id == "frost_mirror":
        points = [(16, 2), (28, 13), (23, 26), (16, 30), (9, 26), (4, 13)]
    elif template_id == "mothwing_ward":
        points = [(16, 3), (27, 7), (24, 15), (29, 22), (18, 29), (16, 24), (14, 29), (3, 22), (8, 15), (5, 7)]
    elif template_id == "dragonbone_pavise":
        points = [(9, 2), (23, 2), (28, 9), (25, 27), (16, 31), (7, 27), (4, 9)]
    elif template_id in {"runic_bastion", "kingstone_guard", "last_gate"}:
        points = [(7, 4), (25, 4), (27, 23), (16, 30), (5, 23)]
    else:
        points = [(16, 3), (27, 8), (25, 21), (16, 29), (7, 21), (5, 8)]
    pygame.draw.polygon(surface, (25, 24, 27), points)
    inner = [(16 + round((x - 16) * .78), 16 + round((y - 16) * .78)) for x, y in points]
    pygame.draw.polygon(surface, dark, inner)
    pygame.draw.lines(surface, main, True, inner, 2)
    if template_id == "bonewall":
        for x in (11, 16, 21):
            pygame.draw.line(surface, light, (x, 8), (x, 24), 2)
    elif template_id in {"storm_aegis", "last_gate"}:
        pygame.draw.lines(surface, light, False, [(18, 6), (12, 15), (18, 14), (13, 25)], 2)
    elif template_id == "venom_filter":
        pygame.draw.polygon(surface, light, [(16, 7), (21, 15), (16, 24), (11, 15)])
        pygame.draw.line(surface, dark, (16, 9), (16, 22), 1)
    elif template_id == "runic_bastion":
        pygame.draw.circle(surface, light, (16, 15), 6, 2)
        pygame.draw.line(surface, light, (10, 15), (22, 15), 1)
        pygame.draw.line(surface, light, (16, 9), (16, 21), 1)
    elif template_id == "mothwing_ward":
        pygame.draw.polygon(surface, main, [(16, 7), (23, 11), (18, 17), (24, 22), (16, 26), (8, 22), (14, 17), (9, 11)])
        pygame.draw.circle(surface, light, (16, 16), 3)
        pygame.draw.circle(surface, (30, 25, 35), (16, 16), 1)
    elif template_id == "dragonbone_pavise":
        pygame.draw.line(surface, light, (10, 6), (22, 25), 3)
        pygame.draw.line(surface, light, (22, 6), (10, 25), 3)
        pygame.draw.circle(surface, main, (16, 15), 4)
        pygame.draw.circle(surface, dark, (16, 15), 2)
    elif seed % 4 == 0:
        pygame.draw.line(surface, light, (16, 7), (16, 24), 2)
        pygame.draw.line(surface, main, (9, 14), (23, 14), 2)
    elif seed % 4 == 1:
        pygame.draw.polygon(surface, main, [(16, 7), (21, 15), (16, 23), (11, 15)])
        pygame.draw.polygon(surface, light, [(16, 9), (18, 15), (16, 19), (14, 15)])
    elif seed % 4 == 2:
        pygame.draw.circle(surface, main, (16, 15), 6)
        pygame.draw.circle(surface, light, (14, 13), 2)
    else:
        pygame.draw.line(surface, main, (9, 21), (23, 9), 3)
        pygame.draw.line(surface, light, (11, 20), (23, 10), 1)


def ring_icon(surface, seed, palette):
    main, dark, light = palette
    pygame.draw.circle(surface, (27, 25, 25), (16, 18), 9, 5)
    pygame.draw.circle(surface, main, (16, 18), 8, 3)
    gem = seed % 3
    if gem == 0:
        pygame.draw.polygon(surface, dark, [(16, 3), (22, 8), (19, 14), (13, 14), (10, 8)])
        pygame.draw.polygon(surface, main, [(16, 5), (20, 8), (18, 12), (14, 12), (12, 8)])
    elif gem == 1:
        pygame.draw.rect(surface, dark, (11, 4, 10, 9), border_radius=2)
        pygame.draw.rect(surface, main, (13, 5, 6, 6))
    else:
        pygame.draw.circle(surface, dark, (16, 8), 6)
        pygame.draw.circle(surface, main, (16, 8), 4)
    pygame.draw.rect(surface, light, (14, 6, 2, 2))


def accessory_icon(surface, template_id, seed, palette):
    """Give wearable stones and neck pieces silhouettes distinct from rings."""
    main, dark, light = palette
    if template_id == "pilgrim_bell":
        pygame.draw.arc(surface, dark, (6, 0, 20, 19), .1, math.pi - .1, 3)
        pygame.draw.polygon(surface, (25, 23, 27), [(11, 10), (21, 10), (25, 25), (7, 25)])
        pygame.draw.polygon(surface, main, [(12, 12), (20, 12), (22, 23), (10, 23)])
        pygame.draw.line(surface, light, (13, 13), (11, 21), 2)
        pygame.draw.circle(surface, dark, (16, 26), 3)
        pygame.draw.circle(surface, light, (16, 25), 1)
        return
    if template_id == "ashglass_charm":
        pygame.draw.lines(surface, dark, False, [(7, 4), (13, 11), (16, 28), (19, 11), (25, 4)], 3)
        pygame.draw.circle(surface, (25, 23, 28), (16, 17), 9)
        pygame.draw.circle(surface, dark, (16, 17), 7)
        pygame.draw.polygon(surface, main, [(16, 9), (21, 17), (16, 24), (11, 17)])
        pygame.draw.polygon(surface, light, [(16, 12), (18, 17), (16, 20), (14, 17)])
        return
    if template_id == "witchglass_bead":
        pygame.draw.arc(surface, dark, (4, 0, 24, 23), .1, math.pi - .1, 3)
        for x, y, radius in ((9, 13, 3), (16, 11, 4), (23, 13, 3), (16, 21, 7)):
            pygame.draw.circle(surface, (25, 23, 29), (x, y), radius + 2)
            pygame.draw.circle(surface, main, (x, y), radius)
        pygame.draw.ellipse(surface, light, (12, 18, 8, 5))
        pygame.draw.circle(surface, dark, (16, 20), 2)
        return
    if template_id == "oathstone_necklace":
        pygame.draw.arc(surface, dark, (3, 0, 26, 25), .05, math.pi - .05, 4)
        pygame.draw.arc(surface, main, (4, 1, 24, 23), .05, math.pi - .05, 1)
        for x, y in ((8, 14), (12, 18), (16, 20), (20, 18), (24, 14)):
            pygame.draw.circle(surface, (24, 23, 27), (x, y), 4)
            pygame.draw.circle(surface, dark, (x, y), 2)
            pygame.draw.rect(surface, light, (x - 1, y - 1, 1, 1))
        return
    if template_id == "graveglass_pendant":
        pygame.draw.arc(surface, (30, 28, 30), (5, 1, 22, 23), 0.08, math.pi - .08, 4)
        pygame.draw.arc(surface, main, (6, 2, 20, 21), .08, math.pi - .08, 1)
        pygame.draw.polygon(surface, (25, 24, 28), [(16, 11), (23, 18), (19, 29), (13, 29), (9, 18)])
        pygame.draw.polygon(surface, main, [(16, 13), (21, 18), (18, 27), (14, 27), (11, 18)])
        pygame.draw.line(surface, light, (15, 15), (13, 22), 2)
        return
    if template_id == "cinder_locket":
        pygame.draw.arc(surface, dark, (5, 0, 22, 24), 0.10, math.pi - .10, 3)
        pygame.draw.circle(surface, (25, 23, 26), (16, 20), 10)
        pygame.draw.circle(surface, main, (16, 20), 8)
        pygame.draw.line(surface, light, (16, 13), (16, 26), 1)
        pygame.draw.polygon(surface, light, [(16, 15), (20, 21), (16, 25), (12, 21)])
        return
    if template_id == "tempest_talisman":
        pygame.draw.lines(surface, dark, False, [(7, 4), (13, 10), (11, 18), (16, 28), (21, 18), (19, 10), (25, 4)], 3)
        pygame.draw.lines(surface, main, False, [(8, 4), (14, 10), (13, 17), (16, 25), (19, 17), (18, 10), (24, 4)], 1)
        pygame.draw.polygon(surface, light, [(17, 8), (13, 17), (17, 17), (14, 25), (21, 14), (17, 14)])
        return
    if template_id == "watcher_stone":
        points = [(16, 3), (27, 11), (24, 25), (16, 30), (7, 25), (4, 12)]
        pygame.draw.polygon(surface, (24, 23, 28), points)
        pygame.draw.polygon(surface, dark, [(16, 5), (25, 12), (22, 24), (16, 28), (9, 23), (6, 12)])
        pygame.draw.ellipse(surface, main, (8, 11, 16, 10))
        pygame.draw.circle(surface, light, (16, 16), 4)
        pygame.draw.circle(surface, (28, 25, 34), (16, 16), 2)
        return
    if template_id == "sovereign_reliquary":
        pygame.draw.line(surface, dark, (8, 5), (13, 11), 3)
        pygame.draw.line(surface, dark, (24, 5), (19, 11), 3)
        pygame.draw.rect(surface, (24, 23, 27), (6, 10, 20, 19), border_radius=3)
        pygame.draw.rect(surface, dark, (8, 12, 16, 15), border_radius=2)
        pygame.draw.polygon(surface, main, [(9, 12), (11, 6), (16, 11), (21, 6), (23, 12)])
        pygame.draw.rect(surface, light, (12, 16, 8, 7), 2)
        pygame.draw.circle(surface, main, (16, 20), 2)
        return
    ring_icon(surface, seed, palette)


def _bottle_body(surface, outer, inner, liquid_y, palette):
    main, dark, light = palette
    pygame.draw.polygon(surface, (26, 25, 30), outer)
    pygame.draw.lines(surface, (26, 25, 30), True, outer, 2)
    pygame.draw.polygon(surface, (180, 202, 201), inner)
    mask = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    pygame.draw.polygon(mask, (255, 255, 255, 255), inner)
    liquid = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    pygame.draw.rect(liquid, (*main, 255), (0, liquid_y, surface.get_width(), surface.get_height() - liquid_y))
    liquid.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    surface.blit(liquid, (0, 0))
    pygame.draw.line(surface, light, (inner[0][0] + 2, inner[0][1] + 2), (inner[0][0] + 1, min(25, liquid_y + 4)), 1)
    pygame.draw.line(surface, dark, inner[-2], inner[-1], 1)


def potion_icon(surface, template_id, seed, palette):
    main, dark, light = palette
    profile = {
        "minor_tonic": "vial", "blended_tonic": "twin", "field_tonic": "canteen",
        "greater_tonic": "faceted", "vital_draught": "round", "ironbark_tonic": "square",
        "fury_phial": "triangle", "fortune_vial": "teardrop", "phoenix_cordial": "winged",
        "bloodsalt_elixir": "ampoule", "stoneblood_flask": "stone", "stormstep_serum": "bolt",
        "moonmilk_cordial": "orb", "last_breath_phial": "hourglass",
    }.get(template_id, "vial")

    pygame.draw.rect(surface, (191, 203, 197), (13, 5, 6, 8))
    pygame.draw.rect(surface, (82, 52, 38), (11, 3, 10, 4))
    if profile == "twin":
        _bottle_body(surface, [(5, 13), (13, 11), (17, 17), (15, 28), (5, 28), (3, 18)], [(7, 14), (12, 13), (15, 18), (13, 26), (6, 26), (5, 18)], 20, palette)
        alt = (light, dark, main)
        _bottle_body(surface, [(17, 12), (25, 13), (29, 18), (27, 28), (17, 28), (15, 17)], [(19, 14), (24, 15), (27, 19), (25, 26), (18, 26), (17, 18)], 18, alt)
        pygame.draw.line(surface, light, (10, 17), (22, 24), 1)
        return
    if profile == "canteen":
        outer, inner, liquid_y = [(6, 12), (25, 12), (28, 16), (26, 28), (6, 28), (4, 16)], [(8, 14), (23, 14), (25, 17), (24, 26), (8, 26), (6, 17)], 19
    elif profile == "faceted":
        outer, inner, liquid_y = [(10, 11), (22, 11), (27, 17), (22, 29), (10, 29), (5, 17)], [(11, 13), (21, 13), (24, 17), (20, 27), (11, 27), (8, 17)], 18
    elif profile in {"round", "orb"}:
        outer, inner, liquid_y = [(10, 11), (22, 11), (28, 17), (27, 24), (22, 29), (10, 29), (5, 24), (4, 17)], [(11, 13), (21, 13), (25, 17), (25, 23), (21, 27), (11, 27), (7, 23), (7, 17)], 18
    elif profile == "square":
        outer, inner, liquid_y = [(7, 11), (25, 11), (27, 14), (27, 28), (5, 28), (5, 14)], [(8, 13), (24, 13), (25, 15), (25, 26), (7, 26), (7, 15)], 18
    elif profile == "triangle":
        outer, inner, liquid_y = [(12, 10), (20, 10), (28, 27), (25, 29), (7, 29), (4, 27)], [(13, 12), (19, 12), (25, 26), (23, 27), (9, 27), (7, 26)], 19
    elif profile == "teardrop":
        outer, inner, liquid_y = [(13, 10), (20, 10), (25, 17), (23, 27), (16, 30), (8, 26), (6, 18)], [(14, 12), (19, 12), (23, 17), (21, 25), (16, 27), (10, 25), (8, 18)], 18
    elif profile == "winged":
        pygame.draw.polygon(surface, dark, [(8, 15), (2, 12), (5, 20), (1, 24), (10, 24)])
        pygame.draw.polygon(surface, dark, [(24, 15), (30, 12), (27, 20), (31, 24), (22, 24)])
        pygame.draw.line(surface, light, (4, 15), (9, 22), 1)
        pygame.draw.line(surface, light, (28, 15), (23, 22), 1)
        outer, inner, liquid_y = [(11, 10), (21, 10), (25, 16), (23, 28), (9, 28), (7, 16)], [(12, 12), (20, 12), (22, 17), (21, 26), (11, 26), (9, 17)], 17
    elif profile == "ampoule":
        outer, inner, liquid_y = [(12, 9), (20, 9), (22, 16), (20, 29), (12, 29), (10, 16)], [(14, 11), (18, 11), (20, 16), (18, 27), (14, 27), (12, 16)], 16
    elif profile == "stone":
        outer, inner, liquid_y = [(8, 12), (23, 10), (28, 16), (25, 28), (8, 29), (4, 21)], [(10, 14), (22, 12), (25, 17), (23, 26), (9, 27), (7, 21)], 18
    elif profile == "bolt":
        outer, inner, liquid_y = [(12, 10), (22, 10), (19, 17), (25, 17), (15, 30), (16, 21), (8, 21)], [(14, 12), (19, 12), (16, 19), (21, 19), (17, 25), (18, 19), (11, 19)], 16
    elif profile == "hourglass":
        outer, inner, liquid_y = [(7, 10), (25, 10), (23, 15), (18, 20), (24, 27), (24, 29), (8, 29), (8, 27), (14, 20), (9, 15)], [(10, 12), (22, 12), (20, 15), (16, 18), (12, 15)], 14
        _bottle_body(surface, outer, inner, liquid_y, palette)
        pygame.draw.polygon(surface, main, [(16, 20), (21, 27), (11, 27)])
        pygame.draw.line(surface, light, (16, 17), (16, 24), 1)
        return
    else:
        outer, inner, liquid_y = [(9, 10), (23, 10), (26, 16), (24, 28), (8, 28), (6, 16)], [(11, 12), (21, 12), (23, 17), (22, 26), (10, 26), (8, 17)], 18
    _bottle_body(surface, outer, inner, liquid_y, palette)

    if profile == "square":
        pygame.draw.lines(surface, light, False, [(10, 17), (15, 14), (15, 25), (21, 18), (22, 25)], 1)
    elif profile == "round":
        pygame.draw.line(surface, light, (16, 16), (16, 24), 2)
        pygame.draw.line(surface, light, (12, 20), (20, 20), 2)
    elif profile == "orb":
        pygame.draw.arc(surface, light, pygame.Rect(11, 16, 11, 9), 1.0, 5.1, 2)
    elif profile == "bolt":
        pygame.draw.lines(surface, light, False, [(17, 12), (14, 18), (18, 18), (14, 25)], 2)
    elif profile == "ampoule":
        pygame.draw.circle(surface, light, (16, 22), 2)
    elif profile == "stone":
        pygame.draw.lines(surface, light, False, [(11, 16), (16, 20), (14, 25)], 1)
    elif profile == "winged":
        pygame.draw.polygon(surface, light, [(16, 14), (19, 20), (16, 25), (13, 20)])
    elif profile == "faceted":
        pygame.draw.lines(surface, light, False, [(9, 17), (16, 14), (23, 17), (16, 26), (9, 17)], 1)


def essence_icon(surface, seed, palette):
    main, dark, light = palette
    points = [(16, 2), (25, 10), (22, 25), (16, 30), (7, 23), (5, 11)]
    pygame.draw.polygon(surface, (25, 23, 28), points)
    inner = [(16, 4), (23, 11), (20, 23), (16, 27), (9, 21), (7, 12)]
    pygame.draw.polygon(surface, dark, inner)
    pygame.draw.lines(surface, main, True, inner, 2)
    pygame.draw.line(surface, light, (15, 7), (11, 19), 2)
    if seed % 2:
        pygame.draw.circle(surface, light, (19, 18), 2)


def material_icon(surface, template_id, seed, palette):
    main, dark, light = palette
    if "bone" in template_id or "crown" in template_id:
        outline_line(surface, main, (7, 24), (25, 7), 5)
        pygame.draw.circle(surface, light, (7, 24), 4)
        pygame.draw.circle(surface, light, (25, 7), 4)
    elif "wire" in template_id:
        pygame.draw.lines(surface, dark, False, [(5, 23), (11, 8), (17, 24), (26, 7)], 5)
        pygame.draw.lines(surface, main, False, [(5, 23), (11, 8), (17, 24), (26, 7)], 2)
    elif "hide" in template_id:
        points = [(5, 9), (12, 5), (16, 8), (21, 5), (27, 11), (24, 19), (27, 25), (18, 28), (13, 25), (6, 27), (8, 18)]
        pygame.draw.polygon(surface, dark, points)
        pygame.draw.lines(surface, main, True, points, 2)
        pygame.draw.line(surface, light, (11, 10), (20, 23), 2)
    else:
        count = 3 + seed % 3
        for index in range(count):
            x = 8 + (index * 7 + seed % 5) % 17
            y = 11 + (index * 9 + seed % 4) % 14
            points = [(x, y - 6), (x + 5, y - 1), (x + 2, y + 5), (x - 5, y + 3), (x - 4, y - 3)]
            pygame.draw.polygon(surface, dark, points)
            pygame.draw.lines(surface, main, True, points, 1)
            pygame.draw.line(surface, light, (x - 2, y - 3), (x, y - 1), 1)


def refine_item_icon(low, palette, kind, seed):
    """Upscale the readable silhouette, then add a restrained high-res edge pass."""
    refined = pygame.transform.scale(low, (48, 48))
    source = refined.copy()
    light = palette[2]
    dark = palette[1]
    for y in range(1, 47):
        for x in range(1, 47):
            current = source.get_at((x, y))
            if current.a < 12:
                continue
            top_open = source.get_at((x, y - 1)).a < 12
            left_open = source.get_at((x - 1, y)).a < 12
            bottom_open = source.get_at((x, y + 1)).a < 12
            right_open = source.get_at((x + 1, y)).a < 12
            if top_open or left_open:
                refined.set_at((x, y), (*light, current.a))
            elif bottom_open or right_open:
                refined.set_at((x, y), (*dark, current.a))
    if kind in {"weapon", "shield", "ring", "potion"} and seed % 3 == 0:
        pygame.draw.rect(refined, light, (41, 6, 2, 2))
        pygame.draw.line(refined, light, (42, 4), (42, 9), 1)
        pygame.draw.line(refined, light, (39, 7), (45, 7), 1)
    return refined


WEAPON_SOURCE_MAP = {
    "wayfarer_blade": "sword1.png",
    "rusted_falchion": "sword2.png",
    "bone_cleaver": "sword5.png",
    "grave_hook": "scythe2.png",
    "emberbrand": "sword4.png",
    "warden_pike": "polearm1.png",
    "rimefang": "dagger5.png",
    "stormneedle": "spear1.png",
    "venomthorn": "dagger3.png",
    "lantern_sabre": "sword3.png",
    "astral_edge": "sword5.png",
    "sunken_king_blade": "sword4.png",
    "voidglass_sabre": "sword2.png",
    "crownless_oath": "sword1.png",
    "pilgrim_crook": "staff2.png",
    "slag_hammer": "hammer2.png",
    "moonlit_khopesh": "scythe1.png",
    "basilisk_needle": "spear2.png",
    "sovereign_axe": "axe4.png",
}


def tint_external_icon(source, palette, kind):
    """Bring public-domain item silhouettes into Bonebound's material palette."""
    icon = pygame.image.load(source)
    if icon.get_size() != (32, 32):
        icon = pygame.transform.scale(icon, (32, 32))
    icon = icon.copy()
    main, dark, light = palette

    def blend(left, right, amount):
        return tuple(round(left[index] + (right[index] - left[index]) * amount) for index in range(3))

    for y in range(32):
        for x in range(32):
            color = icon.get_at((x, y))
            if color.a < 16:
                continue
            rgb = color[:3]
            brightest, dimmest = max(rgb), min(rgb)
            if brightest < 44:
                # Keep the author's crisp outline intact.
                continue
            target = dark if brightest < 104 else light if brightest > 205 else main
            saturation = brightest - dimmest
            amount = .72 if saturation > 28 else (.48 if kind in {"weapon", "shield"} else .58)
            icon.set_at((x, y), (*blend(rgb, target, amount), color.a))
    return icon


def external_item_icon(template_id, kind, seed, palette):
    if kind not in EXTERNAL_ITEM_SOURCES:
        return None
    if kind == "weapon":
        filename = WEAPON_SOURCE_MAP.get(template_id, EXTERNAL_ITEM_SOURCES[kind][seed % len(EXTERNAL_ITEM_SOURCES[kind])])
        root = ARSENAL_ROOT
    elif kind == "shield":
        filename = EXTERNAL_ITEM_SOURCES[kind][seed % len(EXTERNAL_ITEM_SOURCES[kind])]
        root = SHIELD_SOURCE_ROOT
    elif kind == "ring":
        choices = EXTERNAL_ITEM_SOURCES[kind]
        accessory_names = {"graveglass_pendant", "cinder_locket", "tempest_talisman", "watcher_stone",
                           "sovereign_reliquary", "pilgrim_bell", "ashglass_charm", "witchglass_bead",
                           "oathstone_necklace"}
        # Named relic silhouettes communicate their mechanic at a glance; keep
        # their bespoke Bonebound drawing while ordinary bands use CC0 bases.
        if template_id in accessory_names:
            return None
        pool = choices[:10]
        filename = pool[seed % len(pool)]
        root = JEWELRY_SOURCE_ROOT
    else:
        filename = EXTERNAL_ITEM_SOURCES[kind][seed % len(EXTERNAL_ITEM_SOURCES[kind])]
        root = POTION_SOURCE_ROOT
    source = root / filename
    if not source.exists():
        return None
    return tint_external_icon(source, palette, kind)


def add_bonebound_item_marks(surface, template_id, kind, seed, palette):
    """Make licensed base art read as one authored set without hiding its silhouette."""
    main, dark, light = palette
    if kind == "weapon":
        x = 14 + seed % 5
        y = 14 - seed % 4
        pygame.draw.rect(surface, dark, (x - 1, y - 1, 3, 3))
        pygame.draw.rect(surface, light, (x, y, 1, 1))
    elif kind == "shield":
        pygame.draw.circle(surface, dark, (16, 16), 5, 1)
        pygame.draw.line(surface, light, (16, 12), (16, 20), 1)
        pygame.draw.line(surface, main, (12, 16), (20, 16), 1)
    elif kind == "ring":
        pygame.draw.rect(surface, light, (16 + seed % 3 - 1, 8 + seed % 4, 2, 2))
    elif kind == "potion":
        symbol = seed % 3
        if symbol == 0:
            pygame.draw.line(surface, light, (14, 18), (18, 18), 1)
            pygame.draw.line(surface, light, (16, 16), (16, 20), 1)
        elif symbol == 1:
            pygame.draw.polygon(surface, light, [(16, 15), (19, 19), (16, 21), (13, 19)])
        else:
            pygame.draw.circle(surface, light, (16, 18), 2, 1)


def build_items():
    from content import ITEM_TEMPLATES

    ITEM_ROOT.mkdir(parents=True, exist_ok=True)
    for template_id, template in ITEM_TEMPLATES.items():
        seed = seed_for(template_id)
        palette = POTION_PALETTES.get(template_id, ELEMENT_PALETTES[template["element"].value])
        kind = template["kind"].value
        surface = external_item_icon(template_id, kind, seed, palette)
        if surface is None:
            surface = pygame.Surface((32, 32), pygame.SRCALPHA)
            if kind == "weapon":
                weapon_icon(surface, template_id, seed, palette)
            elif kind == "shield":
                shield_icon(surface, template_id, seed, palette)
            elif kind == "ring":
                accessory_icon(surface, template_id, seed, palette)
            elif kind == "potion":
                potion_icon(surface, template_id, seed, palette)
            elif kind == "essence":
                essence_icon(surface, seed, palette)
            else:
                material_icon(surface, template_id, seed, palette)
        else:
            add_bonebound_item_marks(surface, template_id, kind, seed, palette)
        if seed % 4 == 0:
            pygame.draw.rect(surface, palette[2], (27, 4, 2, 2))
            pygame.draw.rect(surface, palette[2], (28, 3, 1, 4))
        pygame.image.save(refine_item_icon(surface, palette, kind, seed), ITEM_ROOT / f"{template_id}.png")


def limb(surface, color, start, end, width):
    pygame.draw.line(surface, (34, 27, 27), start, end, width + 2)
    pygame.draw.line(surface, color, start, end, width)


def ritual_arm(surface, sleeve, wrap, glove, start, hand):
    """Build a cloth sleeve, wrapped forearm and gloved equipment hand."""
    elbow = (
        round(start[0] * .54 + hand[0] * .46),
        round(start[1] * .54 + hand[1] * .46),
    )
    wrist = (
        round(elbow[0] * .35 + hand[0] * .65),
        round(elbow[1] * .35 + hand[1] * .65),
    )
    limb(surface, sleeve, start, elbow, 4)
    limb(surface, wrap, elbow, wrist, 3)
    limb(surface, glove, wrist, hand, 3)
    pygame.draw.circle(surface, (34, 27, 27), elbow, 2)
    pygame.draw.circle(surface, wrap, elbow, 1)
    pygame.draw.circle(surface, (34, 27, 27), hand, 3)
    pygame.draw.circle(surface, glove, hand, 2)


def hero_frame(state, frame, total):
    surface = pygame.Surface((48, 48), pygame.SRCALPHA)
    x = 24
    ground = 44
    bob = 0
    leg_phase = 0.0
    body_angle = 0.0
    if state == "idle":
        bob = (0, 0, -1, -1, -1, 0)[frame % 6]
    elif state == "run":
        leg_phase = (0, .72, 1, .58, 0, -.72, -1, -.58)[frame % 8]
        bob = (0, -1, -2, -1, 0, -1, -2, -1)[frame % 8]
        body_angle = 7
    elif state == "attack":
        index = min(frame, 7)
        x += (0, -2, -3, -1, 3, 7, 6, 2)[index]
        bob = (0, 0, -1, -2, -1, 0, 1, 0)[index]
        body_angle = (-2, -6, -9, -4, 6, 12, 8, 2)[index]
    elif state == "critical":
        index = min(frame, 9)
        x += (0, -2, -4, -5, -3, 2, 8, 10, 7, 2)[index]
        bob = (1, 1, 0, -2, -4, -5, -2, 0, 1, 0)[index]
        body_angle = (-3, -7, -11, -14, -10, 3, 13, 16, 9, 2)[index]
    elif state == "hurt":
        index = min(frame, 3)
        x -= (0, 4, 6, 2)[index]
        bob = (0, -2, 1, 0)[index]
        body_angle = (-4, -18, -12, -3)[index]
    elif state == "guard":
        index = min(frame, 4)
        x += (0, 1, 2, 2, 1)[index]
        bob = (0, 1, 2, 2, 1)[index]
        body_angle = (0, 4, 7, 7, 3)[index]
    elif state == "victory":
        bob = (0, -2, -3, -3, -2, 0)[frame % 6]
        body_angle = (0, -2, -3, -3, -2, 0)[frame % 6]
    if state == "defeat":
        base = hero_frame("hurt", min(frame, 3), 4)
        if frame < 2:
            return base
        angle = min(82, (frame - 1) * 16)
        rotated = pygame.transform.rotate(base, angle)
        result = pygame.Surface((48, 48), pygame.SRCALPHA)
        bounds = rotated.get_bounding_rect(min_alpha=8)
        fallen = rotated.subsurface(bounds).copy()
        result.blit(fallen, fallen.get_rect(midbottom=(24 + min(6, frame), 46)))
        return result
    hood_dark = (43, 29, 39)
    hood = (77, 43, 57)
    hood_light = (132, 69, 72)
    robe = (42, 119, 105)
    robe_light = (75, 166, 132)
    sleeve = (38, 101, 92)
    wrap = (137, 99, 65)
    trousers = (58, 48, 51)
    leather = (111, 69, 41)
    glove = (58, 40, 37)
    boot = (49, 35, 34)
    charm = (214, 159, 63)
    body_y = 25 + bob
    # The torso and head stay on a fixed skeleton. Motion comes from whole-body
    # translation and articulated limbs, avoiding the rubbery morphing seen in
    # the earlier attack frames.
    shoulder_center = x + max(-1, min(1, round(body_angle * .07)))
    hip = (x, body_y + 8)
    if state == "run":
        left_foot = (x - round(7 * leg_phase), ground)
        right_foot = (x + round(7 * leg_phase), ground - (1 if leg_phase > 0 else 0))
    elif state in {"attack", "critical"}:
        stride = 2 if frame < total // 2 else 6
        left_foot = (x - 5, ground)
        right_foot = (x + stride, ground)
    elif state == "guard":
        left_foot = (x - 6, ground)
        right_foot = (x + 7, ground)
    else:
        left_foot = (x - 4, ground)
        right_foot = (x + 5, ground)
    limb(surface, trousers, (hip[0] - 3, hip[1]), left_foot, 4)
    limb(surface, trousers, (hip[0] + 3, hip[1]), right_foot, 4)
    pygame.draw.line(surface, boot, (left_foot[0] - 3, left_foot[1]), (left_foot[0] + 2, left_foot[1]), 3)
    pygame.draw.line(surface, boot, (right_foot[0] - 2, right_foot[1]), (right_foot[0] + 4, right_foot[1]), 3)
    torso = [(shoulder_center - 8, body_y - 9), (shoulder_center + 7, body_y - 9), (hip[0] + 8, body_y + 8), (hip[0] - 8, body_y + 8)]
    pygame.draw.polygon(surface, (30, 35, 38), [(a, b + 1) for a, b in torso])
    pygame.draw.polygon(surface, robe, torso)
    pygame.draw.line(surface, robe_light, (shoulder_center - 5, body_y - 7), (hip[0] - 6, body_y + 5), 2)
    # Split traveling robe, stitched hem and a small hanging ward make the body
    # read as ritual clothing rather than fitted futuristic armor.
    pygame.draw.polygon(surface, (32, 86, 80), [
        (hip[0] - 7, body_y + 5), (hip[0] + 7, body_y + 5),
        (hip[0] + 6, body_y + 11), (hip[0] + 1, body_y + 8),
        (hip[0] - 2, body_y + 11), (hip[0] - 7, body_y + 9),
    ])
    pygame.draw.line(surface, robe_light, (hip[0] - 6, body_y + 8), (hip[0] - 2, body_y + 9), 1)
    pygame.draw.line(surface, leather, (hip[0] - 8, body_y + 5), (hip[0] + 8, body_y + 5), 3)
    pygame.draw.rect(surface, charm, (hip[0] - 1, body_y + 4, 3, 3))
    pygame.draw.line(surface, charm, (hip[0], body_y + 7), (hip[0] - 1, body_y + 10), 1)
    shoulder_y = body_y - 6
    left_hand = (x - 10, body_y + 2)
    right_hand = (x + 10, body_y - 1)
    if state == "run":
        left_hand = (x - 8 + round(4 * leg_phase), body_y + round(3 * leg_phase))
        right_hand = (x + 8 + round(4 * leg_phase), body_y - round(3 * leg_phase))
    elif state == "attack":
        index = min(frame, 7)
        right_hand = (
            x + (8, 5, 3, 8, 13, 16, 14, 10)[index],
            body_y + (-3, -9, -12, -10, -4, 2, 4, -1)[index],
        )
        left_hand = (x - 11, body_y + 3)
    elif state == "critical":
        index = min(frame, 9)
        right_hand = (
            x + (7, 4, 1, 0, 4, 11, 17, 18, 13, 9)[index],
            body_y + (-2, -8, -13, -15, -14, -8, -1, 5, 4, -1)[index],
        )
        left_hand = (x - 12, body_y + 4)
    elif state == "hurt":
        right_hand = (x + 7, body_y + 4)
        left_hand = (x - 8, body_y - 1)
    elif state == "guard":
        index = min(frame, 4)
        left_hand = (x + (0, 3, 6, 7, 3)[index], body_y + (1, -1, -3, -3, -1)[index])
        right_hand = (x + 8, body_y + 3)
    elif state == "victory":
        right_hand = (x + 5, body_y - 15)
        left_hand = (x - 11, body_y - 4)
    elif state == "idle":
        drift = ((0, 0), (0, -1), (1, -1), (1, 0), (0, 1), (0, 0))[frame % 6]
        right_hand = (x + 10 + drift[0], body_y - 1 + drift[1])
        left_hand = (x - 10 - drift[0], body_y + 2 - drift[1])
    ritual_arm(surface, sleeve, wrap, glove, (shoulder_center - 6, shoulder_y), left_hand)
    ritual_arm(surface, sleeve, wrap, glove, (shoulder_center + 6, shoulder_y), right_hand)
    # Equipment is intentionally not baked into the body sheet. The game draws
    # the exact equipped item over these hands, so a new sword or shield is
    # visible immediately instead of leaving the starter gear on the hero.
    neck = (shoulder_center, body_y - 10)
    cowl_outline = [
        (neck[0] - 8, neck[1] + 2), (neck[0] - 5, neck[1] - 3),
        (neck[0] + 5, neck[1] - 3), (neck[0] + 8, neck[1] + 2),
        (neck[0] + 5, neck[1] + 6), (neck[0] - 5, neck[1] + 6),
    ]
    pygame.draw.polygon(surface, hood_dark, cowl_outline)
    pygame.draw.polygon(surface, hood, [
        (neck[0] - 6, neck[1] + 2), (neck[0] - 4, neck[1] - 2),
        (neck[0] + 4, neck[1] - 2), (neck[0] + 6, neck[1] + 2),
        (neck[0] + 4, neck[1] + 4), (neck[0] - 4, neck[1] + 4),
    ])
    pygame.draw.line(surface, hood_light, (neck[0] - 5, neck[1] + 2), (neck[0] + 5, neck[1] + 2), 1)
    pygame.draw.circle(surface, charm, (neck[0], neck[1] + 3), 1)
    head = (shoulder_center, body_y - 15)
    outline = (27, 27, 31)
    mask_bone = (204, 187, 151)
    mask_light = (238, 218, 174)
    mask_shadow = (126, 96, 76)
    mask_eye = (87, 226, 177)
    hood_shape = [
        (head[0] - 3, head[1] - 9), (head[0] + 3, head[1] - 7),
        (head[0] + 7, head[1] - 3), (head[0] + 8, head[1] + 3),
        (head[0] + 4, head[1] + 7), (head[0] - 4, head[1] + 7),
        (head[0] - 8, head[1] + 3), (head[0] - 7, head[1] - 5),
    ]
    pygame.draw.polygon(surface, outline, hood_shape)
    pygame.draw.polygon(surface, hood, [
        (head[0] - 3, head[1] - 8), (head[0] + 2, head[1] - 6),
        (head[0] + 6, head[1] - 2), (head[0] + 6, head[1] + 3),
        (head[0] + 3, head[1] + 6), (head[0] - 4, head[1] + 6),
        (head[0] - 6, head[1] + 2), (head[0] - 6, head[1] - 4),
    ])
    pygame.draw.polygon(surface, hood_dark, [
        (head[0] - 5, head[1] - 4), (head[0] + 3, head[1] - 5),
        (head[0] + 5, head[1] - 1), (head[0] + 4, head[1] + 4),
        (head[0] - 4, head[1] + 4),
    ])
    mask = [
        (head[0] - 4, head[1] - 4), (head[0] + 2, head[1] - 4),
        (head[0] + 5, head[1] - 1), (head[0] + 4, head[1] + 3),
        (head[0] + 1, head[1] + 5), (head[0] - 3, head[1] + 3),
        (head[0] - 5, head[1]),
    ]
    pygame.draw.polygon(surface, mask_bone, mask)
    pygame.draw.polygon(surface, mask_shadow, [
        (head[0] + 2, head[1] - 3), (head[0] + 5, head[1] - 1),
        (head[0] + 4, head[1] + 3), (head[0] + 1, head[1] + 5),
        (head[0], head[1] + 1),
    ])
    pygame.draw.line(surface, mask_light, (head[0] - 3, head[1] - 3), (head[0] + 1, head[1] - 3), 1)
    pygame.draw.rect(surface, outline, (head[0] - 3, head[1] - 1, 2, 2))
    pygame.draw.rect(surface, outline, (head[0] + 1, head[1] - 1, 2, 2))
    pygame.draw.rect(surface, mask_eye, (head[0] - 2, head[1] - 1, 1, 1))
    pygame.draw.rect(surface, mask_eye, (head[0] + 2, head[1] - 1, 1, 1))
    pygame.draw.line(surface, mask_eye, (head[0], head[1] - 4), (head[0], head[1] - 2), 1)
    pygame.draw.line(surface, (86, 61, 52), (head[0] - 1, head[1] + 1), (head[0] + 1, head[1] + 4), 1)
    pygame.draw.line(surface, outline, (head[0] - 2, head[1] + 3), (head[0] + 2, head[1] + 4), 1)
    pygame.draw.line(surface, hood_light, (head[0] - 5, head[1] - 5), (head[0] - 3, head[1] - 7), 1)
    if state == "victory":
        pygame.draw.rect(surface, (240, 193, 61), (head[0] - 1, head[1] - 1, 3, 2))
    return surface


def refine_hero_frame(low, state):
    """Raise the hero's logical detail grid from 48px to 96px.

    The original silhouette remains stable across every animation, while the
    extra grid space adds finer edge lighting and material texture before the
    frame is shown. Scale2x adds stepped contours without introducing blurry
    colors or uneven limb widths between poses.
    """
    refined = pygame.transform.scale2x(low)
    source = refined.copy()
    width, height = refined.get_size()

    def blend(color, target, amount):
        return tuple(round(color[index] + (target[index] - color[index]) * amount) for index in range(3))

    for y in range(1, height - 1):
        for x in range(1, width - 1):
            color = source.get_at((x, y))
            if color.a < 16:
                continue
            rgb = color[:3]
            left_open = source.get_at((x - 1, y)).a < 16
            top_open = source.get_at((x, y - 1)).a < 16
            right_open = source.get_at((x + 1, y)).a < 16
            bottom_open = source.get_at((x, y + 1)).a < 16
            result = rgb
            if (left_open or top_open) and sum(rgb) > 150:
                result = blend(result, (255, 242, 214), .12)
            if (right_open or bottom_open) and sum(rgb) > 105:
                result = blend(result, (18, 18, 22), .16)
            # Sparse one-pixel weave and leather grain: visible at game scale,
            # but deliberately subtle enough to keep the sprite readable.
            if rgb[1] > rgb[0] * 1.22 and rgb[1] > rgb[2] * 1.04 and (x * 3 + y * 5) % 17 == 0:
                result = blend(result, (116, 205, 174), .24)
            elif rgb[0] > rgb[1] * 1.28 and rgb[1] > rgb[2] * 1.12 and (x * 5 + y * 3) % 19 == 0:
                result = blend(result, (205, 137, 75), .18)
            refined.set_at((x, y), (*result, color.a))

    if state != "defeat":
        tunic_points = []
        mask_points = []
        trouser_points = []
        for y in range(height):
            for x in range(width):
                color = source.get_at((x, y))
                if color.a < 16:
                    continue
                r, g, b = color[:3]
                if g > r * 1.55 and g > b * 1.03 and 80 < g < 190:
                    tunic_points.append((x, y))
                elif r > 160 and g > 155 and b > 140 and abs(r - g) < 25 and r > b and g > b:
                    mask_points.append((x, y))
                elif 42 < r < 90 and 38 < g < 80 and 38 < b < 80:
                    trouser_points.append((x, y))

        if tunic_points:
            left = min(point[0] for point in tunic_points)
            right = max(point[0] for point in tunic_points)
            top = min(point[1] for point in tunic_points)
            bottom = max(point[1] for point in tunic_points)
            center = (left + right) // 2
            outline = (27, 29, 31)
            leather_dark = (77, 48, 34)
            leather_light = (154, 96, 49)
            cloth_light = (92, 187, 157)
            # Split collar, shoulder leather and a fine diagonal chest seam.
            pygame.draw.polygon(refined, outline, [(center - 5, top), (center, top + 5), (center + 5, top)])
            pygame.draw.line(refined, cloth_light, (left + 3, top + 3), (center - 2, bottom - 3), 1)
            pygame.draw.line(refined, (35, 101, 95), (center + 2, top + 5), (right - 2, bottom - 3), 1)
            for shoulder_x in (left + 1, right - 4):
                pygame.draw.rect(refined, outline, (shoulder_x - 1, top + 1, 6, 4), border_radius=1)
                pygame.draw.rect(refined, leather_dark, (shoulder_x, top + 1, 4, 3), border_radius=1)
                pygame.draw.line(refined, leather_light, (shoulder_x + 1, top + 1), (shoulder_x + 3, top + 1), 1)
            # Belt buckle and short tunic hem make the body read at a glance.
            belt_y = max(top + 7, bottom - 5)
            pygame.draw.rect(refined, leather_dark, (left, belt_y, right - left + 1, 3))
            pygame.draw.rect(refined, (207, 160, 70), (center - 1, belt_y, 3, 3))
            pygame.draw.line(refined, cloth_light, (left + 2, bottom - 1), (right - 2, bottom - 1), 1)

        if mask_points and tunic_points:
            head_points = [point for point in mask_points if point[1] < top + 4]
            if head_points:
                head_left = min(point[0] for point in head_points)
                head_right = max(point[0] for point in head_points)
                head_top = min(point[1] for point in head_points)
                head_bottom = max(point[1] for point in head_points)
                face_height = head_bottom - head_top + 1
                face_width = head_right - head_left + 1
                eye_y = head_top + max(7, round(face_height * .47))
                left_eye = head_left + max(5, round(face_width * .32))
                right_eye = head_left + max(10, round(face_width * .67))
                rune_x = (left_eye + right_eye) // 2
                # Warm carved planes, two independent sockets and a hand-cut
                # ward replace the previous horizontal sci-fi visor language.
                pygame.draw.line(refined, (248, 226, 181), (head_left + 4, head_top + 3), (rune_x - 2, head_top + 2), 1)
                pygame.draw.line(refined, (122, 88, 69), (head_right - 4, head_top + 5), (head_right - 3, head_bottom - 5), 2)
                socket = (31, 28, 31)
                pygame.draw.polygon(refined, socket, [
                    (left_eye - 3, eye_y), (left_eye, eye_y - 2),
                    (left_eye + 3, eye_y), (left_eye, eye_y + 2),
                ])
                pygame.draw.polygon(refined, socket, [
                    (right_eye - 3, eye_y), (right_eye, eye_y - 2),
                    (right_eye + 3, eye_y), (right_eye, eye_y + 2),
                ])
                pygame.draw.rect(refined, (76, 220, 157), (left_eye, eye_y, 2, 1))
                pygame.draw.rect(refined, (76, 220, 157), (right_eye - 1, eye_y, 2, 1))
                pygame.draw.rect(refined, (210, 255, 207), (left_eye, eye_y, 1, 1))
                pygame.draw.rect(refined, (210, 255, 207), (right_eye, eye_y, 1, 1))
                pygame.draw.line(refined, (51, 167, 127), (rune_x, head_top + 4), (rune_x, eye_y - 4), 1)
                pygame.draw.line(refined, (51, 167, 127), (rune_x - 2, head_top + 7), (rune_x + 2, head_top + 7), 1)
                crack_y = min(head_bottom - 5, eye_y + 5)
                pygame.draw.lines(refined, (93, 65, 54), False, [
                    (head_left + 5, eye_y + 3),
                    (head_left + 8, crack_y),
                    (head_left + 6, min(head_bottom - 2, crack_y + 4)),
                ], 1)
                pygame.draw.lines(refined, (73, 51, 46), False, [
                    (right_eye + 1, eye_y + 3),
                    (head_right - 6, crack_y + 2),
                    (head_right - 3, head_bottom - 4),
                ], 1)
                pygame.draw.line(refined, (45, 34, 35), (rune_x - 3, head_bottom - 3), (rune_x + 3, head_bottom - 4), 1)

        if trouser_points:
            leg_top = min(point[1] for point in trouser_points)
            leg_bottom = max(point[1] for point in trouser_points)
            leg_left = min(point[0] for point in trouser_points)
            leg_right = max(point[0] for point in trouser_points)
            center = (leg_left + leg_right) // 2
            pygame.draw.line(refined, (103, 89, 84), (center - 5, leg_top + 3), (center - 6, leg_bottom - 2), 1)
            pygame.draw.line(refined, (37, 32, 33), (center + 5, leg_top + 3), (center + 7, leg_bottom - 2), 1)
    return refined


HERO_SOURCE_LAYOUTS = {
    "idle": tuple(range(0, 8)),
    "run": tuple(range(8, 18)),
    "attack": tuple(range(18, 24)),
    "critical": tuple(range(30, 37)),
    "hurt": tuple(range(45, 48)),
    "guard": tuple(range(66, 71)),
    "victory": tuple(range(58, 66)),
    "defeat": tuple(range(48, 58)),
}


def _load_pyxel_layers(source):
    with zipfile.ZipFile(source) as archive:
        document = json.loads(archive.read("docData.json"))
        layers = {
            index: pygame.image.load(io.BytesIO(archive.read(f"layer{index}.png")), f"layer{index}.png")
            for index in range(document["canvas"]["numLayers"])
        }
    return document, layers


def _source_cell(layer, index, width=100, height=55):
    return layer.subsurface(((index % 10) * width, (index // 10) * height, width, height)).copy()


def _recolor_mystic_wayfarer(frame):
    """Turn Sven's human knight into Bonebound's bone-masked teal wanderer."""
    source = frame.copy()
    bone_colors = []
    for y in range(frame.get_height()):
        for x in range(frame.get_width()):
            color = source.get_at((x, y))
            if color.a < 16:
                continue
            r, g, b = color[:3]
            replacement = None
            if b > r * 1.20 and b > g * 1.06:
                brightness = max(r, g, b)
                replacement = (30, 69, 68) if brightness < 110 else (47, 127, 112) if brightness < 205 else (119, 201, 174)
            elif r > 105 and r > g * 1.42 and r > b * 1.22:
                brightness = max(r, g, b)
                replacement = (67, 36, 31) if brightness < 125 else (128, 64, 38) if brightness < 205 else (198, 113, 55)
            elif y < 29 and r > 170 and g > 110 and b > 70 and r > b * 1.10:
                brightness = r + g + b
                replacement = (143, 132, 111) if brightness < 430 else (222, 215, 185)
                bone_colors.append((x, y))
            if replacement:
                frame.set_at((x, y), (*replacement, color.a))

    # A carved brow, independent eye socket and green grave-light make the
    # face unmistakably non-human even at the native source resolution.
    if bone_colors:
        left = min(x for x, _ in bone_colors)
        right = max(x for x, _ in bone_colors)
        top = min(y for _, y in bone_colors)
        bottom = max(y for _, y in bone_colors)
        eye_x = right - max(1, (right - left) // 4)
        eye_y = top + max(2, (bottom - top) // 2)
        pygame.draw.rect(frame, (28, 27, 29), (eye_x - 1, eye_y, 3, 2))
        pygame.draw.rect(frame, (82, 224, 164), (eye_x, eye_y, 1, 1))
        rune_x = (left + right) // 2
        pygame.draw.line(frame, (63, 167, 126), (rune_x, top + 1), (rune_x, max(top + 1, eye_y - 1)), 1)
        if bottom - top > 5:
            pygame.draw.line(frame, (91, 64, 51), (left + 1, eye_y + 2), (rune_x, bottom), 1)
    return frame


def _weapon_source_pose(frontarm, index):
    cell = _source_cell(frontarm, index)
    guard = []
    metal = []
    for y in range(cell.get_height()):
        for x in range(cell.get_width()):
            r, g, b, alpha = cell.get_at((x, y))
            if alpha < 16:
                continue
            if r > 180 and g > 125 and b < 125:
                guard.append(pygame.Vector2(x, y))
            if b > 125 and abs(r - g) < 85 and b >= g:
                metal.append(pygame.Vector2(x, y))
    if not guard:
        return pygame.Vector2(50, 28), pygame.Vector2(62, 18)
    grip = sum(guard, pygame.Vector2()) / len(guard)
    candidates = [point for point in metal if point.distance_squared_to(grip) > 18]
    tip = max(candidates or metal or [grip + pygame.Vector2(-12, 8)], key=lambda point: point.distance_squared_to(grip))
    return grip, tip


def _shield_source_center(shield, index):
    cell = _source_cell(shield, index)
    bounds = cell.get_bounding_rect(min_alpha=8)
    if not bounds.width:
        return pygame.Vector2(62, 27)
    return pygame.Vector2(bounds.center)


def _remove_source_weapon(frame, frontarm, index):
    """Erase the source blade while preserving the animated body underneath."""
    grip, tip = _weapon_source_pose(frontarm, index)
    blade = tip - grip
    if blade.length_squared() < 1:
        return frame
    length = blade.length()
    direction = blade / length
    normal = pygame.Vector2(-direction.y, direction.x)
    for y in range(frame.get_height()):
        for x in range(frame.get_width()):
            color = frame.get_at((x, y))
            if color.a < 16:
                continue
            relative = pygame.Vector2(x, y) - grip
            projection = relative.dot(direction)
            distance = abs(relative.dot(normal))
            r, g, b = color[:3]
            pale_weapon_pixel = (b > 115 and abs(r - g) < 90) or (r > 175 and g > 120 and b < 130)
            source_forward_half = x <= grip.x + 4
            if (-2.5 <= projection <= length + 2.5 and distance <= 3.25) or (source_forward_half and pale_weapon_pixel):
                frame.set_at((x, y), (0, 0, 0, 0))
    return frame


def build_hero():
    """Build an equipment-free hero from the licensed layered animation source."""
    HERO_ROOT.mkdir(parents=True, exist_ok=True)
    document, layers = _load_pyxel_layers(SVEN_HERO_SOURCE)
    assert document["canvas"]["tileWidth"] == 100 and document["canvas"]["tileHeight"] == 55

    raw_frames = {}
    for state, source_indices in HERO_SOURCE_LAYOUTS.items():
        state_frames = []
        for source_index in source_indices:
            frame = pygame.Surface((100, 55), pygame.SRCALPHA)
            # Backside, body and scarf contain no baked equipment. The source
            # alternates weapon ordering between poses, so strip its blade and
            # consult the original weapon/shield layers only for grip metadata.
            for layer_index in (5, 4, 1):
                frame.blit(_source_cell(layers[layer_index], source_index), (0, 0))
            frame = _remove_source_weapon(frame, layers[2], source_index)
            frame = _recolor_mystic_wayfarer(frame)
            state_frames.append(pygame.transform.flip(frame, True, False))
        raw_frames[state] = state_frames

    bounds = [frame.get_bounding_rect(min_alpha=8) for frames in raw_frames.values() for frame in frames]
    min_x = min(rect.left for rect in bounds if rect.width)
    max_x = max(rect.right for rect in bounds if rect.width)
    min_y = min(rect.top for rect in bounds if rect.height)
    max_y = max(rect.bottom for rect in bounds if rect.height)
    scale = min(2.0, 90 / max(1, max_x - min_x), 89 / max(1, max_y - min_y))
    offset_x = 3 + (90 - (max_x - min_x) * scale) / 2 - min_x * scale
    offset_y = 92 - max_y * scale

    equipment_points = {"source": "Sven Hero Knight", "states": {}}
    for state, source_indices in HERO_SOURCE_LAYOUTS.items():
        frames = raw_frames[state]
        sheet = pygame.Surface((96 * len(frames), 96), pygame.SRCALPHA)
        poses = []
        for frame_number, (frame, source_index) in enumerate(zip(frames, source_indices)):
            scaled = pygame.transform.scale(frame, (round(100 * scale), round(55 * scale)))
            sheet.blit(scaled, (frame_number * 96 + round(offset_x), round(offset_y)))

            source_grip, source_tip = _weapon_source_pose(layers[2], source_index)
            # The game faces right, so mirror source points exactly like art.
            grip = pygame.Vector2(99 - source_grip.x, source_grip.y)
            tip = pygame.Vector2(99 - source_tip.x, source_tip.y)
            blade = tip - grip
            if blade.length_squared() < 1:
                blade = pygame.Vector2(10, -10)
            blade = blade.normalize()
            elbow = grip - blade * 8
            shield_center = _shield_source_center(layers[3], source_index)
            shield_center.x = 99 - shield_center.x

            def project(point):
                return [round(point.x * scale + offset_x, 2), round(point.y * scale + offset_y, 2)]

            desired_angle = math.degrees(math.atan2(-(tip.y - grip.y), tip.x - grip.x))
            weapon_angle = (desired_angle - 45 + 180) % 360 - 180
            poses.append({
                "weapon_grip": project(grip),
                "weapon_elbow": project(elbow),
                "weapon_angle": round(weapon_angle, 2),
                "shield_center": project(shield_center),
            })
        pygame.image.save(sheet, HERO_ROOT / f"{state}.png")
        equipment_points["states"][state] = poses

    (HERO_ROOT / "equipment_points.json").write_text(
        json.dumps(equipment_points, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def dust_rat_frame(state, frame, count):
    """Draw a stable 48x32 rat with distinct run, bite and defeat poses."""
    surface = pygame.Surface((48, 32), pygame.SRCALPHA)
    outline = (29, 22, 20)
    fur_dark = (105, 55, 25)
    fur = (181, 91, 25)
    fur_light = (224, 139, 54)
    skin = (239, 169, 137)
    eye = (248, 218, 91)
    phase = frame / max(1, count - 1)
    bob = 0
    reach = 0
    flatten = 0
    if state == "run":
        bob = (0, -1, 0, 1, 0, -1)[frame % 6]
    elif state == "idle":
        bob = -1 if frame in {2, 3} else 0
    elif state == "attack":
        reach = (0, 2, 5, 8, 5, 1)[frame % 6]
        bob = (0, -1, -2, 0, 1, 0)[frame % 6]
    elif state == "defeat":
        flatten = round(phase * 6)
        bob = round(phase * 5)

    ground = 27 + bob
    body = pygame.Rect(16 + reach // 4, 12 + bob + flatten // 2, 24, max(7, 13 - flatten))
    pygame.draw.ellipse(surface, outline, body.inflate(4, 4))
    pygame.draw.ellipse(surface, fur_dark, body)
    pygame.draw.ellipse(surface, fur, (body.x + 3, body.y + 1, body.width - 5, max(5, body.height - 3)))
    pygame.draw.line(surface, fur_light, (body.x + 7, body.y + 3), (body.right - 5, body.y + 4), 2)

    head_x = 13 - reach
    head_y = 17 + bob + flatten
    pygame.draw.circle(surface, outline, (head_x, head_y), max(5, 8 - flatten // 2))
    pygame.draw.circle(surface, fur, (head_x, head_y), max(4, 6 - flatten // 2))
    pygame.draw.polygon(surface, outline, [(head_x - 5, head_y - 4), (head_x - 10, head_y), (head_x - 4, head_y + 3)])
    pygame.draw.polygon(surface, skin, [(head_x - 5, head_y - 2), (head_x - 9, head_y), (head_x - 4, head_y + 2)])
    pygame.draw.circle(surface, outline, (head_x + 2, head_y - 6), 4)
    pygame.draw.circle(surface, skin, (head_x + 2, head_y - 6), 2)
    pygame.draw.rect(surface, eye, (head_x - 2, head_y - 3, 2, 2))
    pygame.draw.rect(surface, (28, 21, 20), (head_x - 10, head_y, 2, 2))

    tail_start = (body.right - 2, body.y + body.height // 2)
    tail_wave = (-2, 0, 2, 1, -1, -2)[frame % 6]
    pygame.draw.lines(surface, outline, False, [tail_start, (43, 10 + tail_wave + bob), (47, 13 - tail_wave)], 3)
    pygame.draw.lines(surface, skin, False, [tail_start, (43, 10 + tail_wave + bob), (47, 13 - tail_wave)], 1)

    if state != "defeat":
        stride = (-3, 2, 4, -2, 0, 3)[frame % 6] if state == "run" else (-1, 0, 1, 2, 1, 0)[frame % 6]
        for leg_x, direction in ((21, stride), (34, -stride)):
            pygame.draw.line(surface, outline, (leg_x, ground - 5), (leg_x + direction, ground), 3)
            pygame.draw.line(surface, skin, (leg_x, ground - 5), (leg_x + direction, ground), 1)
        whisker_x = head_x - 8
        pygame.draw.line(surface, skin, (whisker_x, head_y), (max(0, whisker_x - 6), head_y - 2), 1)
        pygame.draw.line(surface, skin, (whisker_x, head_y + 1), (max(0, whisker_x - 6), head_y + 3), 1)
    if state == "attack" and reach >= 5:
        pygame.draw.rect(surface, (19, 15, 16), (max(0, head_x - 10), head_y + 2, 6, 3))
        pygame.draw.polygon(surface, (242, 235, 213), [(max(0, head_x - 8), head_y + 2), (max(0, head_x - 6), head_y + 5), (max(0, head_x - 5), head_y + 2)])
    return surface


def build_dust_rat():
    ENEMY_ROOT.mkdir(parents=True, exist_ok=True)
    layouts = {"idle": 6, "run": 6, "attack": 6, "defeat": 6}
    for state, count in layouts.items():
        sheet = pygame.Surface((48 * count, 32), pygame.SRCALPHA)
        for frame in range(count):
            sheet.blit(dust_rat_frame(state, frame, count), (frame * 48, 0))
        pygame.image.save(sheet, ENEMY_ROOT / f"dust_rat_{state}.png")


def main():
    pygame.init()
    build_items()
    build_hero()
    build_dust_rat()
    pygame.quit()


if __name__ == "__main__":
    main()
