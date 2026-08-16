from pathlib import Path

import pygame


class CharacterSprites:
    def __init__(self):
        self.frames = {}
        self.scaled = {}
        root = Path(__file__).resolve().parent / "assets" / "characters"
        arena = root / "hero_arena"
        arena_layout = {
            "idle": ("idle.png", 96),
            "run": ("run.png", 64),
            "attack": ("attack.png", 96),
            "hurt": ("hurt.png", 64),
            "guard": ("guard.png", 64),
            "defeat": ("defeat.png", 96),
        }
        self.hero_pixel = arena.exists()
        if self.hero_pixel:
            for state, (filename, size) in arena_layout.items():
                loaded = []
                try:
                    sheet = pygame.image.load(arena / filename).convert_alpha()
                    for index in range(sheet.get_width() // size):
                        loaded.append(sheet.subsurface((index * size, 0, size, size)).copy())
                except (OSError, pygame.error, ValueError):
                    pass
                self.frames[("hero", state)] = loaded
        else:
            hero_folder = root / ("hero_v2" if (root / "hero_v2").exists() else "hero")
            for state in ("idle", "run", "attack", "hurt", "guard", "defeat"):
                self.frames[("hero", state)] = self.load_folder(hero_folder / state)
        enemy_arena = root / "enemy_arena"
        enemy_layout = {
            "idle": "Skeleton_01_White_Idle.png",
            "attack": "Skeleton_01_White_Attack1.png",
        }
        self.enemy_pixel = enemy_arena.exists()
        if self.enemy_pixel:
            for state, filename in enemy_layout.items():
                loaded = []
                try:
                    sheet = pygame.image.load(enemy_arena / filename).convert_alpha()
                    for index in range(sheet.get_width() // 96):
                        frame = sheet.subsurface((index * 96, 0, 96, 64)).copy()
                        loaded.append(pygame.transform.flip(frame, True, False))
                except (OSError, pygame.error, ValueError):
                    pass
                self.frames[("enemy", state)] = loaded
            self.frames[("enemy", "defeat")] = self.frames[("enemy", "idle")]
        else:
            for state in ("idle", "attack", "defeat"):
                self.frames[("enemy", state)] = self.load_folder(root / "enemy" / state)

    @staticmethod
    def load_folder(folder):
        loaded = []
        paths = sorted(folder.glob("*.png"), key=lambda path: int(path.stem))
        for path in paths:
            try:
                original = pygame.image.load(path).convert_alpha()
                bounds = original.get_bounding_rect(min_alpha=8)
                if bounds.width and bounds.height:
                    bounds.inflate_ip(12, 12)
                    bounds = bounds.clip(original.get_rect())
                    original = original.subsurface(bounds).copy()
                loaded.append(original)
            except (OSError, pygame.error):
                pass
        return loaded

    def frame(self, actor, state, elapsed, height):
        if actor == "hero":
            state = {"walk": "run", "ready": "idle", "victory": "idle"}.get(state, state)
            state = state if state in {"idle", "run", "attack", "hurt", "guard", "defeat"} else "idle"
        else:
            state = state if state in {"attack", "defeat"} else "idle"
        originals = self.frames.get((actor, state), [])
        if not originals:
            return None
        key = (actor, state, int(height))
        if key not in self.scaled:
            resized = []
            for original in originals:
                target_height = round(height * original.get_height() / 96) if actor == "hero" and self.hero_pixel else int(height)
                width = max(1, round(original.get_width() * target_height / original.get_height()))
                pixel_actor = actor == "hero" and self.hero_pixel or actor == "enemy" and self.enemy_pixel
                transform = pygame.transform.scale if pixel_actor else pygame.transform.smoothscale
                resized.append(transform(original, (width, target_height)))
            self.scaled[key] = resized
        frames = self.scaled[key]
        speed = {"idle": 6.0, "run": 12.0, "attack": 10.0, "hurt": 10.0, "guard": 18.0, "defeat": 9.0}.get(state, 6.0)
        if state in {"attack", "hurt", "guard", "defeat"}:
            index = min(len(frames) - 1, int(max(0, elapsed) * speed))
        else:
            index = int(max(0, elapsed) * speed) % len(frames)
        return frames[index]
