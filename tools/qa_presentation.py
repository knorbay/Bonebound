"""Check new gear acquisition, damage targets, sound loading, saves and render bounds."""
import os, sys, random, tempfile
from pathlib import Path
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pygame
from game import Game, Screen, FxBurst
from combat import CombatEvent, CombatEngine
from content import REGIONAL_ITEMS, ITEM_TEMPLATES, RECIPES, ENEMIES, STAGES, create_item
from models import Element, Hero
from systems import Mixer, SaveManager, LootSystem
from audio import Audio
from presentation import REGION_NAMES

def main():
    out=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'work'/'qa_presentation';out.mkdir(parents=True,exist_ok=True)
    g=Game(True);g.new_game();g.transition_target=None
    assert len(ITEM_TEMPLATES)==103
    for row in REGIONAL_ITEMS:
        key=row[0];item=create_item(key,random.Random(2),1)
        assert key in g.ui.item_images and g.ui.item_images[key].get_bounding_rect().width>0
        pairs=[pair for pair,result in RECIPES.items() if result==key]; assert len(pairs)==1
        a,b=(create_item(x,random.Random(3+j),1) for j,x in enumerate(pairs[0]))
        assert Mixer.visual_result(a,b).template_id==key
        hero=Hero();hero.inventory=[a,b]
        ok,message,result=Mixer.mix(hero,a.uid,b.uid)
        assert ok and result.template_id==key, message
        assert any(key in e.loot for e in ENEMIES.values())
    # Repeated samples prove all regional additions can actually be awarded by LootSystem.
    drops={i.template_id for stage in STAGES for seed in range(80) for i in LootSystem(random.Random(seed)).rewards(stage,False)}
    assert all(row[0] in drops for row in REGIONAL_ITEMS)
    g.hero.inventory=[create_item(row[0],random.Random(i),i+1) for i,row in enumerate(REGIONAL_ITEMS)]
    with tempfile.TemporaryDirectory() as tmp:
        sm=SaveManager(Path(tmp)/'save.json');sm.save(g.hero,1);hero,_=sm.load()
        assert [i.to_dict() for i in hero.inventory]==[i.to_dict() for i in g.hero.inventory]
    g.begin_battle(STAGES[0]);g.transition_target=None;g.battle.drain_events()
    for kind,actor,target in (('proc','hero',870),('counter','hero',870),('thorns','enemy',330)):
        g.battle.events.append(CombatEvent(kind,'QA',actor,5,element=Element.VENOM));g.process_battle_events()
        assert g.fx_bursts[-1].x==target and g.fx_bursts[-1].element==Element.VENOM
    # Numeric boss/execute bonuses also work without their corresponding traits.
    for effect,stage,low_hp in (("boss_damage",STAGES[24],False),("execute_bonus",STAGES[0],True)):
        damages=[]
        for bonus in (0,.5):
            h=Hero(); blade=create_item("wayfarer_blade",random.Random(8),1)
            blade.stats["attack"]=100;blade.effects[effect]=bonus;h.equipment["weapon"]=blade
            b=CombatEngine(h,stage,random.Random(76));b.enemy.hp=1000;b.enemy.max_hp=5000 if low_hp else 1000
            if effect=="boss_damage": b.enemy.boss=True
            b._hero_strike();damages.append(b.total_damage)
        assert damages[1]>damages[0],(effect,damages)
    sound=Audio(); assert sound.enabled
    for name in ('element_fire','element_ice','element_storm','element_venom','element_arcane','boss_phase','victory'):
        assert len(sound.sounds[name])==1;sound.play(name)
    atlas=pygame.Surface((1200,840));atlas.fill((8,12,20))
    for i,row in enumerate(REGIONAL_ITEMS):
        item=create_item(row[0],random.Random(i),1);r=pygame.Rect(20+(i%5)*238,20+(i//5)*400,224,380)
        g.ui.panel(atlas,r);g.ui.draw_item_icon(atlas,pygame.Rect(r.x+32,r.y+20,160,160),item)
        g.ui.fitted_text(atlas,item.name,pygame.Rect(r.x+12,r.y+195,200,28),g.ui.item_color(item),'small','center')
        g.ui.wrapped(atlas,item.description,pygame.Rect(r.x+15,r.y+253,194,120),font='small',max_lines=5)
        g.ui.text(atlas,'ACT '+str(i//2+1),(r.centerx,r.y+231),font='tiny',anchor='center')
    pygame.image.save(atlas,out/'new-items.png')
    regions=pygame.Surface((1200,1000));regions.fill((8,12,20))
    for act in range(1,6):
        scene=pygame.Surface((1160,480));g.ui.draw_cavern(scene,scene.get_rect(),(Element.NEUTRAL,Element.FIRE,Element.ICE,Element.VENOM,Element.ARCANE)[act-1],act,2.3)
        g.ui.text(regions,REGION_NAMES[act-1],(20,(act-1)*200+8),font='small')
        regions.blit(pygame.transform.smoothscale(scene,(464,164)),(20,(act-1)*200+32))
        for j,el in enumerate((Element.FIRE,Element.ICE,Element.STORM,Element.VENOM,Element.ARCANE)):
            if j==act-1:
                fx=FxBurst(760,(act-1)*200+100,(190,190,200),'hero_hit',age=.15,element=el);fx.draw(regions)
                g.ui.text(regions,el.value.upper()+' IMPACT',(940,(act-1)*200+95),font='small')
    pygame.image.save(regions,out/'regions-and-effects.png')
    g.screen=Screen.INVENTORY;g.mouse=(380,237);g.draw()
    g.ui.hover_item=g.hero.inventory[8];g.ui.hover_uid=g.hero.inventory[8].uid;g.ui.hover_since=0
    g.ui.draw_item_tooltip(g.screen_surface,(770,250),2)
    pygame.image.save(g.screen_surface,out/'item-details.png')
    g.screen=Screen.BATTLE;g.battle.anim_clock=2.0;g.draw()
    pygame.image.save(g.screen_surface,out/'battle.png')
    g.hero.discovered_recipes={f"{'+'.join(pair)}={result}" for pair,result in RECIPES.items()}
    g.screen=Screen.RECIPES;g.recipe_page=0;g.mouse=(930,890);g.clicked=True;g.draw()
    assert g.recipe_page==1
    g.clicked=False;g.mouse=(0,0);g.draw()
    pygame.image.save(g.screen_surface,out/'recipes-page-2.png')
    pygame.quit();print('qa_presentation_ok: 10 recipes, loot, icons, save roundtrip, damage targets, 7 sounds, 4 previews')

if __name__=='__main__':main()
