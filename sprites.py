from pathlib import Path

import pygame


class CharacterSprites:
    def __init__(self):
        self.frames = {}
        self.scaled = {}
        self.enemy_frames = {}
        root = Path(__file__).resolve().parent / "assets" / "characters"
        arena = root / ("hero_unarmored" if (root / "hero_unarmored").exists() else "hero_arena")
        self.hero_ground = 92 if arena.name == "hero_unarmored" else None
        arena_layout = {
            "idle": ("idle.png", 64),
            "run": ("run.png", 64),
            "attack": ("attack.png", 64),
            "hurt": ("hurt.png", 64),
            "guard": ("guard.png", 64),
            "defeat": ("defeat.png", 96),
            "critical": ("critical.png", 96),
            "victory": ("victory.png", 96),
        }
        if arena.name == "hero_unarmored":
            arena_layout = {state: (filename, 96) for state, (filename, size) in arena_layout.items()}
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
        self._load_cc0_enemies(root / "enemies_cc0")
        self._load_arena_enemy_overrides()
        self._load_original_enemies(root / "enemies_original")
        self._normalize_enemy_canvases()

    def _load_cc0_enemies(self, root):
        """Load the public-domain bestiary as per-enemy animation sheets."""
        sources = {
            "dust_rat": ("01_rat/01_rat_brown_walk.png", 16),
            "bone_scout": ("04_skeleton/04_skeleton_white_walk.png", 16),
            "crypt_slinger": ("17_cultist/17_cultist_blue_walk.png", 16),
            "marrow_guard": ("05_skeleton_warrior/skeleton_warrior_white_walk.png", 16),
            "ossuary_captain": ("13_mummy/13_mummy_brown_walk.png", 16),
            "cinder_imp": ("09_goblin/09_goblin_red_walk.png", 16),
            "ash_hound": ("20_hyena/20_hyena_gray_walk.png", 32),
            "furnace_knight": ("12_demon/12_demon_red_walk.png", 16),
            "coal_oracle": ("11_spirit/11_spirit_red_fly.png", 16),
            "pyre_warden": ("19_triceratops/19_triceratops_brown_walk.png", 32),
            "rime_widow": ("10_killer_fly/10_killer_fly_purple_walk.png", 16),
            "icebound_thrall": ("08_zombie/08_zombie_blue_walk.png", 16),
            "thunder_crow": ("02_bat/02_bat_blue_fly.png", 16),
            "hail_sentinel": ("14_toad/14_toad_blue_walk.png", 16),
            "tempest_matriarch": ("12_demon/12_demon_blue_walk.png", 16),
            "mire_leech": ("03_snake/03_snake_green_walk.png", 16),
            "plague_duelist": ("07_ghoul/07_ghoul_green_walk.png", 16),
            "hex_moth": ("06_ghost/06_ghost_blue_dark_fly.png", 16),
            "rune_golem": ("15_mud_man/15_mud_man_green_walk.png", 16),
            "alchemist_revenant": ("08_zombie/08_zombie_red_walk.png", 16),
            "void_acolyte": ("17_cultist/17_cultist_purple_walk.png", 16),
            "crownless_guard": ("05_skeleton_warrior/skeleton_warrior_pink_dark_walk.png", 16),
            "starved_dragon": ("18_raptor/18_raptor_red_walk.png", 32),
            "oathbreaker": ("13_mummy/13_mummy_blue_walk.png", 16),
            "hollow_sovereign": ("11_spirit/11_spirit_purple_fly.png", 16),
        }
        for enemy_id, (relative, frame_width) in sources.items():
            primary = root / relative
            idle = primary
            attack = primary
            native_attack = False
            if "_walk.png" in relative:
                candidate = root / relative.replace("_walk.png", "_idle.png")
                if candidate.exists():
                    idle = candidate
                candidate = root / relative.replace("_walk.png", "_attack.png")
                if candidate.exists():
                    attack = candidate
                    native_attack = True
            elif "_fly.png" in relative:
                candidate = root / relative.replace("_fly.png", "_wake_up.png")
                if candidate.exists():
                    attack = candidate
                    native_attack = True
                else:
                    attack = idle
            defeat = idle
            if enemy_id == "bone_scout":
                candidate = root / "04_skeleton/04_skeleton_white_bones.png"
                if candidate.exists():
                    defeat = candidate
            for state, path in {"idle": idle, "run": primary, "attack": attack, "defeat": defeat}.items():
                try:
                    sheet = pygame.image.load(path).convert_alpha()
                except (FileNotFoundError, OSError, pygame.error):
                    continue
                frames = []
                for index in range(sheet.get_width() // frame_width):
                    frame = sheet.subsurface((index * frame_width, 0, frame_width, sheet.get_height())).copy()
                    # Keep the source canvas intact across the sequence. Per-frame
                    # trimming made tails, wings and crouches change scale wildly.
                    frames.append(frame)
                # Small beasts still need a readable attack cycle. Keeping the
                # rat's two walk poses gives its lunge motion instead of a
                # frozen single-frame sprite.
                if state == "attack" and not native_attack and enemy_id != "dust_rat":
                    frames = frames[:1]
                if frames:
                    self.enemy_frames[(enemy_id, state)] = frames

    def _load_arena_enemy_overrides(self):
        """Give the Crypt Slinger a complete higher-resolution silhouette."""
        idle = self.frames.get(("enemy", "idle"), [])
        attack = self.frames.get(("enemy", "attack"), [])
        if not idle or not attack:
            return

        shared_bounds = pygame.Rect(0, 0, 0, 0)
        for frame in idle + attack:
            bounds = frame.get_bounding_rect(min_alpha=8)
            if bounds.width and bounds.height:
                shared_bounds = bounds if not shared_bounds.width else shared_bounds.union(bounds)
        shared_bounds.inflate_ip(6, 6)
        shared_bounds = shared_bounds.clip(idle[0].get_rect())

        def crypt_palette(frame):
            recolored = frame.subsurface(shared_bounds).copy()
            for y in range(recolored.get_height()):
                for x in range(recolored.get_width()):
                    red, green, blue, alpha = recolored.get_at((x, y))
                    if alpha < 8 or max(red, green, blue) - min(red, green, blue) > 24:
                        continue
                    light = max(red, green, blue)
                    if light < 72:
                        continue
                    ratio = (light - 72) / 183
                    recolored.set_at((x, y), (
                        round(64 + 148 * ratio),
                        round(82 + 144 * ratio),
                        round(132 + 123 * ratio),
                        alpha,
                    ))
            return recolored

        idle_frames = [crypt_palette(frame) for frame in idle]
        attack_frames = [crypt_palette(frame) for frame in attack]
        self.enemy_frames[("crypt_slinger", "idle")] = idle_frames
        self.enemy_frames[("crypt_slinger", "run")] = idle_frames
        self.enemy_frames[("crypt_slinger", "attack")] = attack_frames
        self.enemy_frames[("crypt_slinger", "defeat")] = idle_frames

    def _load_original_enemies(self, root):
        """Override selected CC0 actors with higher-resolution Bonebound sheets."""
        for state in ("idle", "run", "attack", "defeat"):
            try:
                sheet = pygame.image.load(root / f"dust_rat_{state}.png").convert_alpha()
            except (FileNotFoundError, OSError, pygame.error):
                continue
            frames = []
            for index in range(sheet.get_width() // 48):
                frames.append(sheet.subsurface((index * 48, 0, 48, 32)).copy())
            if frames:
                self.enemy_frames[("dust_rat", state)] = frames

    def _normalize_enemy_canvases(self):
        """Keep every state of one enemy on an identical, padded ground plane."""
        enemy_ids = {enemy_id for enemy_id, state in self.enemy_frames}
        states = ("idle", "run", "attack", "defeat")
        for enemy_id in enemy_ids:
            sequences = [self.enemy_frames.get((enemy_id, state), []) for state in states]
            all_frames = [frame for sequence in sequences for frame in sequence]
            if not all_frames:
                continue
            canvas_width = max(frame.get_width() for frame in all_frames) + 4
            canvas_height = max(frame.get_height() for frame in all_frames) + 4
            for state, sequence in zip(states, sequences):
                if not sequence:
                    continue
                normalized = []
                for frame in sequence:
                    canvas = pygame.Surface((canvas_width, canvas_height), pygame.SRCALPHA)
                    x = (canvas_width - frame.get_width()) // 2
                    y = canvas_height - frame.get_height() - 2
                    canvas.blit(frame, (x, y))
                    normalized.append(canvas)
                self.enemy_frames[(enemy_id, state)] = normalized

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

    def frame(self, actor, state, elapsed, height, variant=None, max_width=None):
        if actor == "hero":
            state = {"walk": "run", "ready": "idle"}.get(state, state)
            state = state if state in {"idle", "run", "attack", "critical", "hurt", "guard", "victory", "defeat"} else "idle"
        else:
            state = {"ready": "idle", "walk": "run"}.get(state, state)
            state = state if state in {"idle", "run", "attack", "defeat"} else "idle"
        if actor == "enemy" and variant:
            originals = self.enemy_frames.get((variant, state)) or self.enemy_frames.get((variant, "idle"), [])
        else:
            originals = self.frames.get((actor, state), [])
        if not originals:
            return None
        key = (actor, variant, state, int(height), int(max_width or 0))
        if key not in self.scaled:
            resized = []
            for original in originals:
                target_height = round(height * original.get_height() / 96) if actor == "hero" and self.hero_pixel else int(height)
                width = max(1, round(original.get_width() * target_height / original.get_height()))
                if max_width and width > max_width:
                    target_height = max(1, round(target_height * max_width / width))
                    width = int(max_width)
                pixel_actor = actor == "hero" and self.hero_pixel or actor == "enemy" and self.enemy_pixel
                transform = pygame.transform.scale if pixel_actor else pygame.transform.smoothscale
                resized.append(transform(original, (width, target_height)))
            self.scaled[key] = resized
        frames = self.scaled[key]
        speed = {"idle": 5.0, "run": 12.0, "attack": 16.0, "critical": 18.0, "hurt": 13.0, "guard": 12.0, "victory": 7.0, "defeat": 10.0}.get(state, 6.0)
        if state in {"attack", "critical", "hurt", "guard", "defeat"}:
            index = min(len(frames) - 1, int(max(0, elapsed) * speed))
        else:
            index = int(max(0, elapsed) * speed) % len(frames)
        return frames[index]
