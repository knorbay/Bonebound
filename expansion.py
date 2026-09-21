"""Beyond the Hollow Crown: three regions using licensed, hand-drawn pixel art."""
from models import Element, EnemyTemplate, ItemKind, Stage

SPRITES = dict(zip(
    ('salt_slug','drowned_growth','reef_guard','tide_shaman','drowned_colossus','iron_marauder','furnace_chort','ember_wing','ash_necromancer','furnace_devourer','lantern_husk','pale_physician','dusk_amalgam','dawn_sentinel','first_light'),
    ('slug','swampy','masked_orc','orc_shaman','big_zombie','orc_warrior','chort','wogol','necromancer','big_demon','pumpkin_dude','doc','muddy','lizard_m','angel')))
ICONS = dict(zip(
    ('tidebreaker','brineward','tidal_glass','abyssal_tonic','furnace_maul','cathedral_guard','ember_oath','forge_elixir','dawnspear','daybreak_aegis','dawn_relic','dawn_phial'),
    ('W_Axe003.png','E_Wood03.png','Ac_Necklace08.png','P_Blue08.png','W_Mace007.png','E_Metal05.png','Ac_Medal01.png','P_Orange05.png','W_Gold_Spear.png','E_Metal02.png','Ac_Medal04.png','P_Yellow08.png')))
REGIONS = (
    ('Drowned Archive', Element.ICE, ('The Flood Steps','Silt Library','Reef Barricade','The Bell Below','Keeper of the Undertow'),
     ('Salt Slug','Drowned Growth','Reef Guard','Tide Shaman','Drowned Colossus'),
     ('Salt crystals armour a body that never leaves the flooded stair.','Roots drink the ink of a thousand drowned books.','A mask of coral hides the last reader of the archive.','Its staff calls the current through rooms without a sea.','The keeper carries the drowned library on its back.')),
    ('Iron Cathedral', Element.FIRE, ('Chain Processional','The Furnace Choir','Cinder Belfry','Ash Sacristy','Maw of the Foundry'),
     ('Iron Marauder','Furnace Chort','Ember Wing','Ash Necromancer','Furnace Devourer'),
     ('Every link in its mail was taken from a broken pilgrim.','It tends the cathedral fire with living hands.','A furnace spark learned to hunt.','The choir sings through the mouths of the dead.','The foundry built an altar; the altar learned hunger.')),
    ('Dawn Gate', Element.ARCANE, ('Lantern Vigil','The Pale Infirmary','Dusk Reservoir','Last Watch','The First Light'),
     ('Lantern Husk','Pale Physician','Dusk Amalgam','Dawn Sentinel','First Light'),
     ('A borrowed flame keeps a forgotten watchman awake.','It searches for a cure to the waking world.','The last shadows gather beneath the gate.','A sentinel waits for a dawn it has never seen.','Beyond the crown, one final guardian holds the morning shut.')),
)

def install(items, enemies, item):
    stages=[]
    enemy_ids=list(SPRITES)
    item_ids=list(ICONS)
    for region,(name,element,rooms,names,descriptions) in enumerate(REGIONS):
        act=6+region; ids=enemy_ids[region*5:region*5+5]; gear=item_ids[region*4:region*4+4]
        entries=(
            (ItemKind.WEAPON, {'attack':46+region*8,'luck':4+region}, {}, 'A balanced edge recovered beyond the crown. Its elemental strike cuts through the region\'s guardians.'),
            (ItemKind.SHIELD, {'defense':22+region*4,'health':30+region*15}, {}, 'A broad guard built for the long descent. Raises defense and maximum health.'),
            (ItemKind.RING, {'health':35+region*10,'luck':6+region*2}, {}, 'A keepsake carried through the sealed gate. Raises maximum health and critical chance.'),
            (ItemKind.POTION, {}, {'heal_percent':.60+region*.05,'battle_attack':5+region*2,'duration_turns':5}, 'Restores health and strengthens attacks for five turns.'),
        )
        for key,(kind,stats,effects,desc) in zip(gear,entries):
            items[key]=item(key.replace('_',' ').title(),kind,stats,{k:v+(12 if k!='health' else 30) for k,v in stats.items()},element,5+region,act,9 if kind==ItemKind.POTION else 1,effects,description=desc,value=300+region*100)
        for j,key in enumerate(ids):
            boss=j==4
            traits=(('second_phase','heavy') if boss else ('guarded',) if j==2 else ('leeching',) if j==3 else ('ambusher',) if j==1 else ())
            enemies[key]=EnemyTemplate(key,names[j],900+region*200 if boss else 380+region*95+j*22,52+region*5+j*2,25+region*3+j,14+region*2,element,260+region*60 if boss else 125+region*30+j*8,tuple(gear)+('primal_essence',),descriptions[j],elite=j==2,boss=boss,traits=traits)
        waves=((0,1,0),(1,0,2),(0,2,3),(1,3,2),(2,3,4))
        for j,wave in enumerate(waves):
            index=26+region*5+j
            stages.append(Stage(index,rooms[j],index,tuple(ids[n] for n in wave),gear[(0,1,2,3,0)[j]],3,f'{name}: {descriptions[j]}',act))
    return tuple(stages)
