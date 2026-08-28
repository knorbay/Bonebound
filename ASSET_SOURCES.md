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
