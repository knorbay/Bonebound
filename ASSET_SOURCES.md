# Asset Sources

Bonebound v0.1.0 uses curated assets with licenses suitable for continued development.

## Bonebound Original Pixel Assets

Source: Created inside the Bonebound project

License: Project-owned original work

Used files: named relic, essence and material icon overlays; Bonebound palette/rune transformations; and the higher-resolution Dust Rat idle, run, attack and defeat sheets.

The deterministic transformations and original supplements are reproducible from `tools/build_pixel_assets.py`.

## Hero Knight

Source: https://sventhole.itch.io/hero-knight

Author: Sven Thole

License: The author's Hero Knight asset terms permit use in commercial and non-commercial games and prohibit reselling the pack itself as an asset.

Used file: `assets/third_party/sven_hero_knight/HeroKnight.pyxel`

Bonebound composes the source's separate body/scarf layers, removes its baked equipment, mirrors and recolors the result as the bone-masked Wayfarer, and exports native idle, run, attack, critical, hurt, guard, victory and defeat sheets. The source weapon and shield layers are used only to derive per-frame grip coordinates for the player's actual equipped item artwork.

## Idylwild's Arsenal

Source: https://opengameart.org/content/idylwilds-arsenal

Author: Idylwild

License: Creative Commons CC0

Used files: selected 32x32 weapon PNGs under `assets/third_party/idylwild_arsenal/`, recolored and marked for Bonebound's weapon icons.

## CC0 Shield, Jewelry and Potion Icons

Sources:

- https://opengameart.org/content/cc0-shield-icons
- https://opengameart.org/content/cc0-jewelry-icons
- https://opengameart.org/content/cc0-potion-icons

Collection author: AntumDeluge; selected pixel originals by 7Soul1 / Henrique Lazarini

License: Creative Commons CC0

Used files: selected 32x32 PNGs under `assets/third_party/7soul_shields/`, `assets/third_party/7soul_jewelry/` and `assets/third_party/7soul_potions/`, recolored and augmented with Bonebound-specific marks.

## UI Pack - Adventure

Source: https://kenney.nl/assets/ui-pack-adventure

License: Creative Commons CC0

Used files: selected SVG interface pieces retained as optional fallbacks.

## Kenney Interface Sounds

Source: https://kenney.nl/assets/interface-sounds

License: Creative Commons CC0

Used files: glass and opening effects.

## UI Sound Effects

Source: https://opengameart.org/content/ui-sound-effects-button-clicks-user-feedback-notifications

Author: Robin Lamb

License: Creative Commons CC0

Used files: selected click, confirmation, reward and negative-feedback sounds.

## 20 Sword Sound Effects

Source: https://opengameart.org/content/20-sword-sound-effects-attacks-and-clashes

Author: StarNinjas

License: Creative Commons CC0

Used files: three sword attacks and two sword clashes.

## Simple Knight - Character Pack

Source: https://phi9009.itch.io/big-knight-character-pack

Author: Phi9009

License: Free for commercial projects and modification under the terms stated by the author.

Used files: idle, run, ground attack, guard hit, hurt and death sprite sheets.

The author page explicitly marks the pack as not made with generative AI.

## Pixel Art Skeletons Pack

Source: https://monopixelart.itch.io/skeletons-pack

Author: MonoPixelArt

License: Free for commercial and non-commercial projects under the terms stated by the author.

Used files: white skeleton idle and sword attack sprite sheets with VFX.

The author page explicitly marks the pack as not made with generative AI.

## Heartfelt Battle

Source: https://opengameart.org/content/heartfelt-battle-loopable-fantasy-stringspianohorn

Author: request

License: Creative Commons CC0

Used file: `heartfelt-battle_loop.ogg`

## Loopable Dungeon Ambience

Source: https://opengameart.org/content/loopable-dungeon-ambience

Author: JaggedStone

License: Creative Commons CC0

Used file: `dungeon_ambient_1.ogg`

The original license files are stored in `assets/licenses`.
# Enemy bestiary (CC0)

- Pixel Monsters & Enemies Asset Pack by elesrech
- Source: https://elesrech.itch.io/pixel-monsters-enemies-asset-pack
- License: Creative Commons Zero v1.0 Universal / Public Domain
- Used for the per-enemy animated battle sprites under `assets/characters/enemies_cc0/`.

## Original presentation expansion (2026-09-14)

The seven WAV files in `assets/audio/v3` and elemental impact geometry in
`presentation.py` were generated specifically for Bonebound with deterministic Python code.
The original regional item prototypes were replaced in 0.2.1 with the CC0 sources below.
Rebuild sounds with `tools/build_presentation_assets.py` and curated icons with `tools/build_curated_assets.py`.
Existing asset attributions above continue to apply.


## 0.2.1 — Curated pixel art refresh (2026-09-20)

### Dungeon Tileset II v1.7
Author: 0x72 (Robert)
Source: https://0x72.itch.io/dungeontileset-ii
License: CC0 1.0 Universal; author explicitly allows any use.
Downloaded from the author's official itch.io free download on 2026-09-19.
Used: selected wall, floor, column, banner, skull, crate, door and chest frames in
`assets/third_party/0x72_dungeon/`. Layouts are assembled in `dungeon_art.py` for the
scrollable campaign map and battle arenas. The asset page marks the pack as not
made with generative AI. Terms are recorded in `assets/licenses/0x72_dungeon.txt`.

### RPG Audio
Author: Kenney (Kenney.nl)
Source: https://kenney.nl/assets/rpg-audio
License: CC0 1.0 Universal; included License.txt copied to `assets/licenses/kenney_rpg_audio.txt`.
Used: selected knife, impact, equipment, door, book and coin recordings in
`assets/audio/kenney_rpg/`. Music/SFX mix and routing are implemented in `audio.py`.

### Regional item artwork
The ten regional items now use Idylwild's Arsenal and 7Soul/AntumDeluge CC0 sources,
credited above. Exact file mapping is in `tools/build_curated_assets.py`.
Artists' colors are preserved; transparent padding and nearest-neighbour resizing
adapt the originals to the existing equipment system. No generated map image is used.


## 0.2.3 — item art and soundtrack (2026-09-20)

### 496 pixel art icons for medieval/fantasy RPG
Author: Henrique Lazarini (7Soul1), CC0 collection repacked by gnola14.
Source: https://opengameart.org/content/496-pixel-art-icons-for-medievalfantasy-rpg
License: CC0 1.0 Universal. The collection excludes incompatible derivative icons.
Selected native 32px files are in `assets/third_party/7soul_full/`.
`tools/build_curated_assets.py` maps 88 items explicitly to these and the previously
credited Idylwild/7Soul sources. Colors remain intact; weapon icons from this set
are flipped horizontally to match the equipped hand. Original icon pixels are
centered on transparent 48px canvases, without recoloring or extra rune overlays.
The three retained original icons are pilgrim_bell, storm_wire and crown_fragment.

### Dungeon Themes
Author: FazeDevWater
Source: https://opengameart.org/content/dungeon-themes
License: CC0 1.0 Universal.
Files: dungeon.ogg, dungeon_fire.ogg, dungeon_mystic.ogg under assets/music/.
Original downloads: dungeon_11.ogg, dungeonfire_1.ogg, dungeonmystic_1.ogg.
Used for menu, workshop and regional exploration/fire battles.

### Boss Battle Theme
Author: Cleyton Kauffman — https://soundcloud.com/cleytonkauffman
Source: https://opengameart.org/content/boss-battle-theme
License: CC0 1.0 Universal.
Original file: CleytonRX - Battle RPG Theme Var_0.ogg, stored as assets/music/boss.ogg.
Music source audio is unmodified; per-track playback gain balances the mix.


### 0.3 expansion
`assets/characters/enemies_expansion/`: original four-frame slug, swampy,
masked_orc, orc_shaman, big_zombie, orc_warrior, chort, wogol, necromancer,
big_demon, pumpkin_dude, doc, muddy, lizard_m and angel animations from the
already credited 0x72 Dungeon Tileset II v1.7 (CC0). No AI-generated sprites.
The 12 added item icons use the already credited 7Soul CC0 collection;
exact source filenames are listed in `expansion.ICONS`.
