from pathlib import Path
import random
import json
import math

import pygame


class Audio:
    def __init__(self, enabled=True):
        self.enabled = enabled
        self.music_enabled = True
        self.effects_enabled = True
        self.last_played = {}
        self.sounds = {}
        self.current_music = None
        self.pending_music = None
        self.music_volume = .40
        self.effects_volume = .80
        self.settings_path = None
        self.gain = 1.0
        self.failed_music = set()
        self.music_files = {}
        self.rng = random.Random()
        if not enabled:
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(44100, -16, 2, 512)
            pygame.mixer.set_num_channels(24)
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
                "equip": [root / "impactMetal_medium_002.ogg"],
                "mix": [root / "glass_003.ogg", root / "confirmation_002.ogg"],
                "forge": [root / "impactMining_002.ogg", modern / "confirm_deep.ogg"],
                "temper": [root / "impactMetal_medium_002.ogg", modern / "confirm_deep.ogg"],
                "salvage": [root / "impactWood_heavy_002.ogg", root / "drop_003.ogg"],
            }
            rpg = root / "kenney_rpg"
            files.update({
                "hit": [rpg / "knifeSlice.ogg", rpg / "knifeSlice2.ogg", modern / "sword_1.ogg"],
                "hurt": [rpg / "chop.ogg"],
                "critical": [modern / "sword_3.ogg"],
                "equip": [rpg / "drawKnife1.ogg", rpg / "drawKnife2.ogg"],
                "door": [rpg / "doorOpen_1.ogg"],
                "book": [rpg / "bookOpen.ogg"],
                "collect": [rpg / "handleCoins.ogg"],
                "enemy_down": [rpg / "dropLeather.ogg"] if (rpg / "dropLeather.ogg").exists() else [rpg / "chop.ogg"],
            })
            for name in ("element_fire", "element_ice", "element_storm", "element_venom", "element_arcane", "boss_phase", "victory"):
                files[name] = [root / "v3" / (name + ".wav")]
            volumes = {
                "click": .28, "open": .32, "confirm": .42, "collect": .42,
                "error": .35, "potion": .48, "hit": .65, "critical": .75,
                "block": .62, "equip": .42, "mix": .40, "forge": .48,
                "temper": .44, "salvage": .38,
            }
            for name, paths in files.items():
                variants = []
                for path in paths:
                    try:
                        sound = pygame.mixer.Sound(path)
                        sound.set_volume(volumes.get(name, .42))
                        variants.append(sound)
                    except (OSError, pygame.error):
                        continue
                if variants:
                    self.sounds[name] = variants
            music_root = root.parent / "music"
            self.music_files = {
                "ambient": music_root / "dungeon_ambient.ogg",
                "battle": music_root / "heartfelt_battle.ogg",
                "dungeon": music_root / "dungeon.ogg",
                "fire": music_root / "dungeon_fire.ogg",
                "mystic": music_root / "dungeon_mystic.ogg",
                "boss": music_root / "boss.ogg",
            }
        except (OSError, pygame.error):
            self.enabled = False
            self.sounds.clear()

    def play(self, name):
        if not self.enabled or not self.effects_enabled or name not in self.sounds:
            return
        now = pygame.time.get_ticks()
        if now - self.last_played.get(name, -1000) < 45:
            return
        # A single accent per impact prevents simultaneous elemental procs
        # from masking the weapon transient. UI sounds retain their own cadence.
        if name.startswith("element_"):
            if now - self.last_played.get("element_bus", -1000) < 110:
                return
            self.last_played["element_bus"] = now
        self.last_played[name] = now
        sound = self.rng.choice(self.sounds[name])
        channel = pygame.mixer.find_channel()
        if channel is None:
            channel = pygame.mixer.find_channel(True)
        if channel:
            channel.set_volume(self.effects_volume)
            channel.play(sound)

    # Source RMS varies by almost 20 dB. Match perceived levels without
    # amplifying the already loud dungeon masters or drowning combat effects.
    TRACK_GAIN = {"ambient": 2.4, "battle": 1.65, "dungeon": .37,
                  "fire": .38, "mystic": .38, "boss": .63}
    TRACK_LABEL = {"ambient": "Dungeon Ambience / JaggedStone",
                   "battle": "Heartfelt Battle / request",
                   "dungeon": "Dungeon / FazeDevWater",
                   "fire": "Dungeon Fire / FazeDevWater",
                   "mystic": "Dungeon Mystic / FazeDevWater",
                   "boss": "Boss Battle Theme / Cleyton Kauffman"}

    def bind_settings(self, path):
        self.settings_path = Path(path)
        try:
            data = json.loads(self.settings_path.read_text())
            if not isinstance(data, dict):
                return
            for key in ("music_volume", "effects_volume"):
                value = data.get(key)
                if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
                    setattr(self, key, max(0.0, min(1.0, value)))
            for key in ("music_enabled", "effects_enabled"):
                if isinstance(data.get(key), bool):
                    setattr(self, key, data[key])
        except (OSError, ValueError):
            pass
        self.apply_volume()

    def save_settings(self):
        if self.settings_path is None:
            return
        data = {key: getattr(self, key) for key in
                ("music_volume", "effects_volume", "music_enabled", "effects_enabled")}
        try:
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.settings_path.with_suffix(".tmp")
            temporary.write_text(json.dumps(data, indent=2))
            temporary.replace(self.settings_path)
        except OSError:
            pass

    def apply_volume(self):
        if self.enabled:
            volume = self.music_volume * self.TRACK_GAIN.get(self.current_music, 1.0) * self.gain
            pygame.mixer.music.set_volume(min(1.0, volume) if self.music_enabled else 0)

    def set_volume(self, bus, value):
        if bus not in {"music", "effects"}:
            return
        setattr(self, bus + "_volume", round(max(0.0, min(1.0, value)), 2))
        self.apply_volume()
        self.save_settings()

    def toggle_music(self):
        self.music_enabled = not self.music_enabled
        self.apply_volume()
        self.save_settings()

    def toggle_effects(self):
        self.effects_enabled = not self.effects_enabled
        if self.enabled and not self.effects_enabled:
            pygame.mixer.stop()
        self.save_settings()

    def _start_music(self, name):
        try:
            pygame.mixer.music.load(self.music_files[name])
            self.current_music = name
            self.apply_volume()
            pygame.mixer.music.play(-1)
        except (OSError, pygame.error):
            self.failed_music.add(name)
            self.current_music = None

    def music(self, name):
        if not self.enabled or name not in self.music_files or name in self.failed_music:
            return
        if name == self.current_music:
            self.pending_music = None
        elif self.current_music is None:
            self._start_music(name)
        else:
            self.pending_music = name

    def update(self, dt):
        if not self.enabled:
            return
        if self.pending_music:
            self.gain = max(0.0, self.gain - dt / .35)
            if self.gain <= 0:
                name, self.pending_music = self.pending_music, None
                self._start_music(name)
        else:
            self.gain = min(1.0, self.gain + dt / .65)
        self.apply_volume()
