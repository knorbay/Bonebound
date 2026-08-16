import math
from pathlib import Path

import pygame

from models import Element, ItemKind


COLORS = {
    "bg": (7, 11, 18),
    "ink": (6, 9, 14),
    "panel": (17, 23, 31),
    "panel_alt": (22, 30, 40),
    "panel_light": (30, 41, 54),
    "border": (67, 82, 99),
    "border_dark": (32, 42, 54),
    "text": (233, 239, 245),
    "muted": (138, 153, 170),
    "gold": (226, 174, 79),
    "red": (224, 83, 101),
    "green": (70, 200, 139),
    "blue": (71, 159, 226),
    "wood": (54, 48, 48),
    "wood_light": (103, 76, 61),
    "parchment": (192, 189, 176),
    "stone": (49, 61, 75),
}


ELEMENT_COLORS = {
    Element.NEUTRAL: (190, 185, 169),
    Element.FIRE: (242, 91, 45),
    Element.ICE: (83, 193, 229),
    Element.STORM: (242, 207, 63),
    Element.VENOM: (111, 196, 72),
    Element.ARCANE: (181, 91, 220),
}


ITEM_COLORS = {
    ItemKind.WEAPON: (220, 116, 69),
    ItemKind.SHIELD: (82, 148, 202),
    ItemKind.RING: (221, 177, 65),
    ItemKind.POTION: (72, 188, 117),
    ItemKind.ESSENCE: (166, 104, 214),
    ItemKind.MATERIAL: (166, 143, 107),
}


class UI:
    def __init__(self, audio=None):
        self.audio = audio
        self.fonts = {
            "tiny": pygame.font.SysFont("avenir next,arial", 13, bold=True),
            "small": pygame.font.SysFont("avenir next,arial", 16),
            "body": pygame.font.SysFont("avenir next,arial", 19),
            "medium": pygame.font.SysFont("avenir next,arial", 25, bold=True),
            "large": pygame.font.SysFont("georgia", 40, bold=True),
            "title": pygame.font.SysFont("georgia", 67, bold=True),
        }
        self.images = {}
        self.scaled_images = {}
        root = Path(__file__).resolve().parent / "assets" / "ui"
        for name in ("banner_hanging", "button_brown", "button_red", "panel_brown_corners_a"):
            try:
                self.images[name] = pygame.image.load(root / f"{name}.svg").convert_alpha()
            except (FileNotFoundError, OSError, pygame.error):
                pass

    def asset(self, name, size):
        key = (name, tuple(size))
        if key not in self.scaled_images and name in self.images:
            self.scaled_images[key] = pygame.transform.smoothscale(self.images[name], size)
        return self.scaled_images.get(key)

    @staticmethod
    def blend(first, second, amount):
        return tuple(round(a + (b - a) * amount) for a, b in zip(first, second))

    @staticmethod
    def item_color(item):
        if item and item.element != Element.NEUTRAL:
            return ELEMENT_COLORS[item.element]
        return ITEM_COLORS[item.kind] if item else COLORS["muted"]

    def text(self, surface, value, pos, color=None, font="body", anchor="topleft", shadow=False):
        color = color or COLORS["text"]
        image = self.fonts[font].render(str(value), True, color)
        rect = image.get_rect()
        setattr(rect, anchor, pos)
        if shadow:
            shade = self.fonts[font].render(str(value), True, (3, 3, 5))
            shade_rect = shade.get_rect()
            setattr(shade_rect, anchor, (pos[0] + 3, pos[1] + 4))
            surface.blit(shade, shade_rect)
        surface.blit(image, rect)
        return rect

    def fitted_text(self, surface, value, rect, color=None, font="small", anchor="midleft"):
        value = str(value)
        while value and self.fonts[font].size(value)[0] > rect.width:
            value = value[:-2].rstrip(" …") + "…"
        position = rect.midleft if anchor == "midleft" else rect.center
        return self.text(surface, value, position, color, font, anchor)

    def wrapped(self, surface, value, rect, color=None, font="small", line_gap=4, max_lines=None):
        color = color or COLORS["text"]
        words = str(value).split()
        lines = []
        line = ""
        for word in words:
            trial = f"{line} {word}".strip()
            if self.fonts[font].size(trial)[0] <= rect.width:
                line = trial
            else:
                if line:
                    lines.append(line)
                line = word
        if line:
            lines.append(line)
        if max_lines:
            lines = lines[:max_lines]
        y = rect.y
        for line in lines:
            self.text(surface, line, (rect.x, y), color, font)
            y += self.fonts[font].get_linesize() + line_gap
        return y

    def panel(self, surface, rect, fill=None, border=None, radius=12, width=1):
        fill = fill or COLORS["panel"]
        border = border or COLORS["border"]
        pygame.draw.rect(surface, (3, 6, 10), rect.move(0, 4), border_radius=radius)
        pygame.draw.rect(surface, fill, rect, border_radius=radius)
        pygame.draw.rect(surface, border, rect, width, border_radius=radius)
        if rect.height > 12 and rect.width > 12:
            highlight = pygame.Rect(rect.x + 9, rect.y + 5, rect.width - 18, 1)
            pygame.draw.rect(surface, self.blend(fill, (255, 255, 255), .10), highlight)

    def ornamented_panel(self, surface, rect, fill=None, border=None, radius=12, width=2):
        accent = border or COLORS["border"]
        self.panel(surface, rect, fill, accent, radius, width)
        if rect.height >= 70:
            pygame.draw.line(surface, accent, (rect.x + 1, rect.y + radius), (rect.x + 1, rect.bottom - radius), 3)

    def ribbon(self, surface, rect, label, color=None, font="small"):
        color = color or COLORS["gold"]
        fill = self.blend(COLORS["panel_alt"], color, .10)
        pygame.draw.rect(surface, fill, rect, border_radius=rect.height // 2)
        pygame.draw.rect(surface, self.blend(color, COLORS["border"], .35), rect, 1, border_radius=rect.height // 2)
        pygame.draw.circle(surface, color, (rect.x + 16, rect.centery), 3)
        self.text(surface, label, (rect.centerx + 5, rect.centery), COLORS["text"], font, "center")

    def button(self, surface, rect, label, mouse, clicked, enabled=True, accent=None, font="medium"):
        hovered = enabled and rect.collidepoint(mouse)
        accent = accent or COLORS["gold"]
        if not enabled:
            fill = (26, 25, 25)
            border = (58, 53, 47)
            text_color = (91, 86, 78)
        elif hovered:
            fill = self.blend(COLORS["panel_light"], accent, .14)
            border = accent
            text_color = (255, 247, 219)
        else:
            fill = COLORS["panel_alt"]
            border = self.blend(accent, COLORS["ink"], .38)
            text_color = COLORS["text"]
        self.panel(surface, rect, fill, border, 9, 2 if hovered else 1)
        self.text(surface, label, rect.center, text_color, font, "center")
        activated = bool(enabled and hovered and clicked)
        if activated and self.audio:
            self.audio.play("click")
        return activated

    def bar(self, surface, rect, value, maximum, color, label="", show_numbers=True):
        ratio = max(0.0, min(1.0, value / max(1, maximum)))
        pygame.draw.rect(surface, (7, 11, 17), rect.inflate(4, 4), border_radius=6)
        pygame.draw.rect(surface, (26, 32, 41), rect, border_radius=4)
        fill = rect.copy()
        fill.width = round(fill.width * ratio)
        if fill.width:
            pygame.draw.rect(surface, self.blend(color, COLORS["ink"], .18), fill, border_radius=4)
            shine = pygame.Rect(fill.x + 2, fill.y + 2, max(0, fill.width - 4), 2)
            pygame.draw.rect(surface, self.blend(color, (255, 255, 255), .20), shine, border_radius=2)
        pygame.draw.rect(surface, self.blend(color, COLORS["ink"], .28), rect, 2, border_radius=4)
        if label or show_numbers:
            value_text = f"{int(value)}/{int(maximum)}" if show_numbers else ""
            self.text(surface, f"{label} {value_text}".strip(), rect.center, (255, 249, 229), "tiny", "center", True)

    def stat_chip(self, surface, rect, label, value, color):
        self.panel(surface, rect, (18, 25, 34), self.blend(color, COLORS["ink"], .58), 8)
        pygame.draw.rect(surface, color, (rect.x + 10, rect.y + 10, 3, rect.height - 20), border_radius=2)
        self.text(surface, label, (rect.x + 22, rect.centery), COLORS["muted"], "tiny", "midleft")
        self.text(surface, value, (rect.right - 12, rect.centery), color, "medium", "midright")

    def draw_item_icon(self, surface, rect, item, selected=False):
        color = self.item_color(item)
        center = rect.center
        size = min(rect.width, rect.height)
        glow = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*color, 52 if selected else 28), (rect.width // 2, rect.height // 2), max(8, size // 2 - 3))
        surface.blit(glow, rect)
        dark = self.blend(color, COLORS["ink"], .55)
        light = self.blend(color, (255, 255, 255), .35)
        cx, cy = center
        if item.kind == ItemKind.WEAPON:
            length = size * .34
            pygame.draw.line(surface, (235, 230, 213), (cx - length * .55, cy + length * .55), (cx + length * .55, cy - length * .55), max(4, round(size * .08)))
            pygame.draw.line(surface, light, (cx - length * .48, cy + length * .48), (cx + length * .55, cy - length * .55), max(1, round(size * .025)))
            pygame.draw.line(surface, color, (cx - length * .68, cy + length * .22), (cx - length * .20, cy + length * .70), max(3, round(size * .07)))
            pygame.draw.circle(surface, dark, (round(cx - length * .63), round(cy + length * .63)), max(3, round(size * .07)))
        elif item.kind == ItemKind.SHIELD:
            points = [(cx, cy - size * .32), (cx + size * .28, cy - size * .17), (cx + size * .22, cy + size * .20), (cx, cy + size * .36), (cx - size * .22, cy + size * .20), (cx - size * .28, cy - size * .17)]
            pygame.draw.polygon(surface, dark, points)
            pygame.draw.polygon(surface, color, points, max(2, round(size * .045)))
            pygame.draw.line(surface, light, (cx, cy - size * .24), (cx, cy + size * .26), max(2, round(size * .04)))
        elif item.kind == ItemKind.RING:
            pygame.draw.circle(surface, dark, center, round(size * .26), max(5, round(size * .10)))
            pygame.draw.circle(surface, color, center, round(size * .26), max(2, round(size * .045)))
            gem = (cx, round(cy - size * .28))
            pygame.draw.polygon(surface, light, [(gem[0], gem[1] - size * .10), (gem[0] + size * .10, gem[1]), (gem[0], gem[1] + size * .10), (gem[0] - size * .10, gem[1])])
        elif item.kind == ItemKind.POTION:
            bottle = pygame.Rect(0, 0, round(size * .38), round(size * .48))
            bottle.center = (cx, cy + size * .07)
            pygame.draw.rect(surface, (190, 208, 194), bottle, border_radius=max(4, round(size * .09)))
            liquid = pygame.Rect(bottle.x + 4, bottle.centery, bottle.width - 8, bottle.height // 2 - 4)
            pygame.draw.rect(surface, color, liquid, border_radius=4)
            neck = pygame.Rect(round(cx - size * .09), round(bottle.y - size * .14), round(size * .18), round(size * .18))
            pygame.draw.rect(surface, (204, 216, 203), neck, border_radius=2)
            pygame.draw.rect(surface, dark, (neck.x - 2, neck.y - 3, neck.width + 4, 5), border_radius=2)
        elif item.kind == ItemKind.ESSENCE:
            points = [(cx, cy - size * .35), (cx + size * .25, cy - size * .08), (cx + size * .13, cy + size * .34), (cx - size * .20, cy + size * .22), (cx - size * .28, cy - size * .10)]
            pygame.draw.polygon(surface, dark, points)
            pygame.draw.polygon(surface, color, points, max(2, round(size * .04)))
            pygame.draw.line(surface, light, (cx, cy - size * .27), (cx - size * .10, cy + size * .17), max(2, round(size * .035)))
        else:
            for dx, dy, scale in ((-.16, .08, .22), (.12, .12, .18), (.02, -.15, .20)):
                point = (round(cx + size * dx), round(cy + size * dy))
                radius = round(size * scale)
                pygame.draw.circle(surface, dark, point, radius)
                pygame.draw.circle(surface, color, point, radius, max(2, round(size * .035)))

    def item_card(self, surface, rect, item, mouse, clicked, selected=False, compact=False):
        color = self.item_color(item)
        hovered = rect.collidepoint(mouse)
        fill = (52, 46, 40) if hovered else (32, 30, 30)
        border = COLORS["gold"] if selected else self.blend(color, COLORS["border"], .38)
        self.ornamented_panel(surface, rect, fill, border, 8, 2 if selected or hovered else 1)
        icon_size = min(rect.height - 14, 58 if not compact else 48)
        icon = pygame.Rect(rect.x + 8, rect.centery - icon_size // 2, icon_size, icon_size)
        pygame.draw.rect(surface, self.blend(color, COLORS["ink"], .78), icon, border_radius=8)
        self.draw_item_icon(surface, icon, item, selected)
        text_rect = pygame.Rect(icon.right + 9, rect.y + 5, rect.width - icon.width - 26, 28)
        self.fitted_text(surface, item.display_name, text_rect, COLORS["text"], "small")
        if item.stack > 1:
            badge = pygame.Rect(rect.right - 34, rect.bottom - 29, 27, 22)
            pygame.draw.ellipse(surface, COLORS["ink"], badge)
            self.text(surface, item.stack, badge.center, COLORS["text"], "tiny", "center")
        stat_rect = pygame.Rect(icon.right + 9, rect.y + 35, rect.width - icon.width - 20, 21)
        self.fitted_text(surface, item.stat_text(), stat_rect, color, "tiny")
        if not compact:
            tag = item.element.value.upper() if item.element != Element.NEUTRAL else item.kind.value.upper()
            self.text(surface, tag, (rect.right - 9, rect.bottom - 7), color, "tiny", "bottomright")
        return hovered and clicked

    def item_slot(self, surface, rect, item, mouse, clicked, selected=False, label=""):
        hovered = rect.collidepoint(mouse)
        if not item:
            self.empty_card(surface, rect, label or "EMPTY", mouse, clicked, selected)
            activated = hovered and clicked
            if activated and self.audio:
                self.audio.play("click")
            return activated
        color = self.item_color(item)
        fill = self.blend((31, 29, 28), color, .09 if hovered else .035)
        border = COLORS["gold"] if selected else self.blend(color, COLORS["border"], .5)
        self.ornamented_panel(surface, rect, fill, border, 9, 2 if hovered or selected else 1)
        if rect.height < 90:
            icon = pygame.Rect(rect.centerx - 20, rect.centery - 14, 40, 40)
            self.draw_item_icon(surface, icon, item, selected)
            if label:
                self.text(surface, label, (rect.centerx, rect.y + 7), COLORS["muted"], "tiny", "midtop")
            if item.stack > 1:
                self.text(surface, item.stack, (rect.right - 6, rect.bottom - 5), COLORS["text"], "tiny", "bottomright")
            return hovered and clicked
        icon = pygame.Rect(rect.centerx - min(38, rect.width // 3), rect.y + 10, min(76, rect.width * 2 // 3), min(76, rect.height - 42))
        self.draw_item_icon(surface, icon, item, selected)
        name_rect = pygame.Rect(rect.x + 8, rect.bottom - 30, rect.width - 16, 23)
        self.fitted_text(surface, item.display_name, name_rect, COLORS["text"], "tiny", "center")
        if item.stack > 1:
            badge = pygame.Rect(rect.right - 33, rect.y + 7, 26, 22)
            pygame.draw.ellipse(surface, COLORS["ink"], badge)
            pygame.draw.ellipse(surface, color, badge, 1)
            self.text(surface, item.stack, badge.center, COLORS["text"], "tiny", "center")
        if label:
            self.text(surface, label, (rect.x + 7, rect.y + 7), COLORS["muted"], "tiny")
        activated = hovered and clicked
        if activated and self.audio:
            self.audio.play("click")
        return activated

    def empty_card(self, surface, rect, label, mouse, clicked, selected=False):
        hovered = rect.collidepoint(mouse)
        border = COLORS["gold"] if selected else (48, 61, 76)
        fill = (23, 31, 41) if hovered else (15, 21, 29)
        self.panel(surface, rect, fill, border, 8, 2 if selected else 1)
        inner = rect.inflate(-14, -14)
        pygame.draw.rect(surface, (41, 54, 69), inner, 1, border_radius=6)
        self.text(surface, label, rect.center, (104, 121, 139), "tiny", "center")
        return hovered and clicked

    def item_detail(self, surface, rect, item):
        self.ornamented_panel(surface, rect, (36, 32, 29), COLORS["border"], 10, 2)
        if not item:
            self.text(surface, "SELECT AN ITEM", (rect.centerx, rect.y + 88), COLORS["muted"], "small", "center")
            self.text(surface, "Its story and stats will appear here.", (rect.centerx, rect.y + 124), (112, 104, 94), "tiny", "center")
            return
        color = self.item_color(item)
        icon = pygame.Rect(rect.x + 18, rect.y + 18, 78, 78)
        pygame.draw.rect(surface, self.blend(color, COLORS["ink"], .78), icon, border_radius=12)
        self.draw_item_icon(surface, icon, item, True)
        name_rect = pygame.Rect(icon.right + 13, rect.y + 19, rect.right - icon.right - 30, 32)
        self.fitted_text(surface, item.display_name, name_rect, COLORS["text"], "medium")
        element = item.element.value.title() if item.element != Element.NEUTRAL else "Unbound"
        self.text(surface, f"{item.kind.value.title()}  •  {element}", (icon.right + 13, rect.y + 58), color, "small")
        self.text(surface, item.stat_text(), (rect.x + 18, rect.y + 116), COLORS["text"], "body")
        if item.traits:
            traits = "  •  ".join(value.replace("_", " ").title() for value in item.traits)
            self.wrapped(surface, traits, pygame.Rect(rect.x + 18, rect.y + 151, rect.width - 36, 46), COLORS["gold"], "small", 2, 2)
        self.wrapped(surface, item.description, pygame.Rect(rect.x + 18, rect.y + 201, rect.width - 36, 62), COLORS["muted"], "small", 3, 3)

    def toast(self, surface, value, age, duration=3.2, color=None):
        if not value or age >= duration:
            return
        fade = min(1, age * 4, (duration - age) * 3)
        image = self.fonts["body"].render(value, True, color or COLORS["text"])
        box = image.get_rect(center=(surface.get_width() // 2, surface.get_height() - 45)).inflate(38, 22)
        overlay = pygame.Surface(box.size, pygame.SRCALPHA)
        pygame.draw.rect(overlay, (14, 12, 12, int(238 * fade)), overlay.get_rect(), border_radius=9)
        pygame.draw.rect(overlay, (*COLORS["gold"], int(190 * fade)), overlay.get_rect(), 1, border_radius=9)
        image.set_alpha(int(255 * fade))
        surface.blit(overlay, box)
        surface.blit(image, image.get_rect(center=box.center))

    def draw_world_background(self, surface, clock=0.0):
        width, height = surface.get_size()
        surface.fill(COLORS["bg"])
        for y in range(0, height, 8):
            amount = y / max(1, height)
            pygame.draw.rect(surface, self.blend((12, 16, 25), (31, 24, 25), amount), (0, y, width, 9))
        moon = (width - 164, 137)
        pygame.draw.circle(surface, (78, 79, 99), moon, 86)
        pygame.draw.circle(surface, (24, 24, 34), (moon[0] + 31, moon[1] - 20), 82)
        for index in range(38):
            x = int((index * 97 + math.sin(clock * .12 + index) * 18) % (width + 80) - 40)
            y = 80 + (index * 71 % 560)
            pygame.draw.circle(surface, (80, 78, 91), (x, y), 1 if index % 3 else 2)
        for layer in range(3):
            base = height - 160 + layer * 55
            color = self.blend((27, 27, 36), (9, 10, 15), layer * .35)
            points = [(-40, height)]
            for x in range(-40, width + 120, 120):
                peak = base - 95 - ((x // 120 + layer * 2) % 3) * 44
                points.extend([(x, base), (x + 58, peak), (x + 125, base)])
            points.extend([(width + 40, height), (-40, height)])
            pygame.draw.polygon(surface, color, points)

    def draw_cavern(self, surface, rect, element, act, clock=0.0):
        old_clip = surface.get_clip()
        surface.set_clip(rect)
        color = ELEMENT_COLORS[element]
        for y in range(rect.y, rect.bottom, 6):
            amount = (y - rect.y) / max(1, rect.height)
            shade = self.blend(self.blend(color, (13, 17, 25), .82), (10, 9, 12), amount)
            pygame.draw.rect(surface, shade, (rect.x, y, rect.width, 7))
        portal = (rect.centerx, rect.y + 230)
        for radius, amount in ((118, .12), (84, .18), (52, .28)):
            pygame.draw.circle(surface, self.blend((18, 18, 24), color, amount), portal, radius)
        for layer in range(3):
            ground_y = rect.bottom - 92 + layer * 24
            rock = self.blend((63, 56, 58), color, .05 + layer * .02)
            points = [(rect.x - 30, rect.bottom)]
            for index in range(9):
                x = rect.x - 20 + index * (rect.width // 7)
                lift = 18 + ((index * 37 + act * 19 + layer * 13) % 52)
                points.extend([(x, ground_y), (x + 53, ground_y - lift)])
            points.extend([(rect.right + 30, rect.bottom), (rect.x - 30, rect.bottom)])
            pygame.draw.polygon(surface, self.blend(rock, COLORS["ink"], layer * .22), points)
        for index in range(11):
            x = rect.x + index * 127 - 30
            length = 42 + (index * 31 + act * 17) % 78
            pygame.draw.polygon(surface, (25, 23, 28), [(x, rect.y), (x + 66, rect.y), (x + 31, rect.y + length)])
        for index in range(7):
            x = rect.x + 80 + index * 174
            y = rect.bottom - 102 - (index % 2) * 17
            flicker = 3 + math.sin(clock * 6 + index) * 2
            pygame.draw.circle(surface, self.blend(color, (255, 255, 210), .2), (x, round(y - 22)), round(6 + flicker))
            pygame.draw.line(surface, (77, 56, 40), (x, y), (x, y - 18), 4)
        pygame.draw.line(surface, (110, 87, 63), (rect.x, rect.bottom - 86), (rect.right, rect.bottom - 86), 4)
        pygame.draw.line(surface, (52, 43, 39), (rect.x, rect.bottom - 80), (rect.right, rect.bottom - 80), 8)
        surface.set_clip(old_clip)
