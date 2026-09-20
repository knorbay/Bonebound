"""Repack existing CC0 pixel sources; keep the artists' palette and outlines."""
import os
from pathlib import Path
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
ROOT=Path(__file__).resolve().parents[1]
SOURCES = {'arcane_essence': ('7soul_full', 'I_Amethist.png'),
 'ashglass_charm': ('7soul_full', 'I_Agate.png'),
 'astral_edge': ('7soul_full', 'W_Sword019.png'),
 'astral_orbit': ('7soul_jewelry', 'ring_03_purple.png'),
 'basilisk_needle': ('7soul_full', 'W_Spear010.png'),
 'blended_tonic': ('7soul_full', 'P_Medicine02.png'),
 'bloodsalt_elixir': ('7soul_full', 'P_Red03.png'),
 'bog_sickle': ('idylwild_arsenal', 'scythe2border.png'),
 'bone_cleaver': ('7soul_full', 'W_Sword009.png'),
 'bone_luck': ('7soul_full', 'Ac_Necklace06.png'),
 'bone_shard': ('7soul_full', 'I_Bone.png'),
 'bonewall': ('7soul_full', 'E_Bones02.png'),
 'cinder_locket': ('7soul_full', 'Ac_Necklace01.png'),
 'cinder_plate': ('7soul_full', 'E_Metal09.png'),
 'cinder_scythe': ('idylwild_arsenal', 'scythe1border.png'),
 'copper_loop': ('7soul_jewelry', 'ring_01.png'),
 'crownless_oath': ('7soul_full', 'W_Sword006.png'),
 'dragonbone_pavise': ('7soul_full', 'E_Bones03.png'),
 'eclipse_halberd': ('7soul_full', 'W_Spear013.png'),
 'ember_core': ('7soul_full', 'I_Rock05.png'),
 'ember_essence': ('7soul_full', 'S_Fire03.png'),
 'ember_signet': ('7soul_jewelry', 'ring_03_light_red.png'),
 'emberbrand': ('7soul_full', 'W_Sword016.png'),
 'field_tonic': ('7soul_full', 'P_Red05.png'),
 'fortune_eclipse': ('7soul_jewelry', 'ring_03_pink.png'),
 'fortune_vial': ('7soul_full', 'P_Pink02.png'),
 'frost_mirror': ('7soul_full', 'E_Metal06.png'),
 'frostglass': ('7soul_full', 'I_Sapphire.png'),
 'fury_phial': ('7soul_full', 'P_Orange02.png'),
 'ghost_salt': ('7soul_full', 'I_Crystal03.png'),
 'glacier_glaive': ('7soul_full', 'W_Spear003.png'),
 'grave_hook': ('idylwild_arsenal', 'scythe2border.png'),
 'graveglass_pendant': ('7soul_full', 'Ac_Necklace07.png'),
 'gravewood_targe': ('7soul_full', 'E_Wood02.png'),
 'greater_tonic': ('7soul_full', 'P_Red07.png'),
 'iron_scrap': ('7soul_full', 'I_SilverBar.png'),
 'iron_vow': ('7soul_jewelry', 'ring_02.png'),
 'ironbark_tonic': ('7soul_full', 'P_Green03.png'),
 'kiln_heart': ('7soul_full', 'I_Ruby.png'),
 'kingstone_guard': ('7soul_full', 'E_Gold01.png'),
 'lantern_sabre': ('7soul_full', 'W_Sword018.png'),
 'last_breath_phial': ('7soul_full', 'P_Pink07.png'),
 'last_gate': ('7soul_full', 'E_Metal07.png'),
 'minor_tonic': ('7soul_full', 'P_Red01.png'),
 'moonlit_khopesh': ('idylwild_arsenal', 'scythe1border.png'),
 'moonmilk_cordial': ('7soul_full', 'P_White03.png'),
 'mothwing_ward': ('7soul_full', 'E_Metal04.png'),
 'mourner_seal': ('7soul_full', 'Ac_Necklace02.png'),
 'oathstone_necklace': ('7soul_full', 'Ac_Necklace04.png'),
 'ossuary_lance': ('7soul_full', 'W_Spear012.png'),
 'patched_buckler': ('7soul_full', 'E_Wood01.png'),
 'phoenix_cordial': ('7soul_full', 'P_Yellow05.png'),
 'pilgrim_crook': ('7soul_full', 'W_Staff04.png'),
 'primal_essence': ('7soul_full', 'I_Diamond.png'),
 'red_coil': ('7soul_jewelry', 'ring_03_red.png'),
 'rime_essence': ('7soul_full', 'I_Crystal01.png'),
 'rime_signet': ('7soul_jewelry', 'ring_03_blue.png'),
 'rimefang': ('7soul_full', 'W_Sword017.png'),
 'runic_bastion': ('7soul_full', 'E_Metal03.png'),
 'rusted_falchion': ('7soul_full', 'W_Sword013.png'),
 'slag_hammer': ('7soul_full', 'W_Mace009.png'),
 'sovereign_axe': ('7soul_full', 'W_Axe014.png'),
 'sovereign_reliquary': ('7soul_full', 'I_Chest01.png'),
 'splintered_guard': ('7soul_full', 'E_Wood04.png'),
 'spore_lantern': ('7soul_full', 'I_Torch02.png'),
 'starless_compass': ('7soul_full', 'Ac_Medal02.png'),
 'stoneblood_flask': ('7soul_full', 'P_White05.png'),
 'storm_aegis': ('7soul_full', 'E_Gold02.png'),
 'storm_essence': ('7soul_full', 'S_Thunder01.png'),
 'storm_signet': ('7soul_jewelry', 'ring_03_gray.png'),
 'stormneedle': ('7soul_full', 'W_Spear011.png'),
 'stormstep_serum': ('7soul_full', 'P_Blue07.png'),
 'sunken_king_blade': ('7soul_full', 'W_Sword015.png'),
 'tattered_hide': ('7soul_full', 'I_WolfFur.png'),
 'tempest_talisman': ('7soul_full', 'Ac_Necklace03.png'),
 'thunder_dial': ('7soul_full', 'I_Clock.png'),
 'venom_essence': ('7soul_full', 'I_Jade.png'),
 'venom_filter': ('7soul_full', 'E_Metal08.png'),
 'venom_signet': ('7soul_jewelry', 'ring_03_light_green.png'),
 'venomthorn': ('7soul_full', 'W_Dagger011.png'),
 'vital_draught': ('7soul_full', 'P_Green05.png'),
 'vital_knot': ('7soul_jewelry', 'ring_03_green.png'),
 'void_resin': ('7soul_full', 'I_Ink.png'),
 'voidglass_sabre': ('7soul_full', 'W_Sword022.png'),
 'warden_pike': ('7soul_full', 'W_Spear009.png'),
 'watcher_stone': ('7soul_full', 'I_Eye.png'),
 'wayfarer_blade': ('7soul_full', 'W_Sword001.png'),
 'witchglass_bead': ('7soul_full', 'I_Opal.png')}

from expansion import ICONS
SOURCES.update({key: ('7soul_full', filename) for key, filename in ICONS.items()})

def build():
    pygame.init()
    for name,(pack,file) in SOURCES.items():
        src=pygame.image.load(ROOT/'assets'/'third_party'/pack/file)
        # Blitting honours indexed PNG transparency without repainting its background.
        rgba=pygame.Surface(src.get_size(),pygame.SRCALPHA);rgba.blit(src,(0,0))
        if pack == '7soul_full' and file.startswith('W_'):
            rgba = pygame.transform.flip(rgba, True, False)
        # Keep the original 32px pixel grid, including transparent padding.
        # Runtime scales once to each view; no intermediate 32 -> 44 resampling.
        canvas = pygame.Surface((48, 48), pygame.SRCALPHA)
        canvas.blit(rgba, rgba.get_rect(center=(24, 24)))
        pygame.image.save(canvas,ROOT/'assets'/'items'/(name+'.png'))
    pygame.quit()

if __name__=='__main__':build()
