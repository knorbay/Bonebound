from pathlib import Path
import random

import pygame


class Audio:
    def __init__(self, enabled=True):
        self.enabled = enabled
        self.sounds = {}
        self.current_music = None
        self.music_files = {}
        self.rng = random.Random()
        if not enabled:
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(44100, -16, 2, 512)
            root = Path(__file__).resolve().parent / "assets" / "audio"
            modern = root / "v2"
            files = {
                "click": [modern / "click_soft.ogg", modern / "click_alt.ogg"],
                "confirm": [modern / "confirm_deep.ogg"],
                "collect": [modern / "reward_chime.ogg"],
                "error": [modern / "error_soft.ogg"],
                "potion": [root / "glass_003.ogg"],
                "open": [root / "open_002.ogg", modern / "click_alt.ogg"],
                "hit": [modern / "sword_1.ogg", modern / "sword_2.ogg", modern / "sword_3.ogg"],
                "critical": [modern / "sword_3.ogg", modern / "block_1.ogg"],
                "block": [modern / "block_1.ogg", modern / "block_2.ogg"],
            }
            volumes = {"click": .14, "open": .17, "confirm": .22, "collect": .21, "error": .20, "potion": .24, "hit": .25, "critical": .29, "block": .25}
            for name, paths in files.items():
                variants = []
                for path in paths:
                    sound = pygame.mixer.Sound(path)
                    sound.set_volume(volumes[name])
                    variants.append(sound)
                self.sounds[name] = variants
            music_root = root.parent / "music"
            self.music_files = {
                "ambient": music_root / "dungeon_ambient.ogg",
                "battle": music_root / "heartfelt_battle.ogg",
            }
        except (OSError, pygame.error):
            self.enabled = False
            self.sounds.clear()

    def play(self, name):
        if self.enabled and name in self.sounds:
            self.rng.choice(self.sounds[name]).play()

    def music(self, name):
        if not self.enabled or name == self.current_music or name not in self.music_files:
            return
        try:
            pygame.mixer.music.load(self.music_files[name])
            pygame.mixer.music.set_volume(.18 if name == "ambient" else .24)
            pygame.mixer.music.play(-1, fade_ms=650)
            self.current_music = name
        except (OSError, pygame.error):
            self.current_music = None
