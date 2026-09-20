"""0.3 campaign, migration, animation and progression regression checks."""
import os,sys,tempfile,random,json,hashlib
from pathlib import Path
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame
from game import Game,Screen
from content import STAGES,ENEMIES,ITEM_TEMPLATES,create_item,create_endless_stage,_validate_content
from expansion import SPRITES,ICONS
from models import Hero
from systems import SaveManager,Mixer
from combat import CombatEngine

def runner(level,gear,seed):
    h=Hero()
    for _ in range(level-1):h.gain_xp(h.xp_needed)
    for i in range((level-1)*2):
        if not h.spend_point('attack' if i%2 else 'health'):break
    for name,slot in zip(gear,('weapon','shield','ring1','ring2')):
        item=create_item(name,random.Random(seed),level)
        for _ in range(2):Mixer._reinforce(item)
        h.equipment[slot]=item
    return h

def main():
    out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
    _validate_content();assert len(STAGES)==40 and len(ENEMIES)==40 and len(ITEM_TEMPLATES)==103
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/'save.json';h=Hero();h.equipment['weapon']=create_item('crownless_oath',random.Random(1),25);h.cleared_stages=set(range(1,26));h.unlocked_stage=25;h.campaign_complete=True;h.ending_seen=True
        payload=SaveManager(path)._payload(h,25);payload.pop('checksum');payload['version']=4
        payload['checksum']=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()[:20];path.write_text(json.dumps(payload))
        migrated,_=SaveManager(path).load();assert migrated.unlocked_stage==26 and migrated.endless_unlocked and not migrated.campaign_complete
        assert migrated.cleared_stages==h.cleared_stages and migrated.equipment['weapon'].uid==h.equipment['weapon'].uid
        migrated.unlocked_stage=40;migrated.cleared_stages=set(range(1,41));migrated.campaign_complete=True
        SaveManager(path).save(migrated,40);loaded,selected=SaveManager(path).load();assert selected==40 and loaded.campaign_complete and loaded.cleared_stages==migrated.cleared_stages
        g=Game(True,Path(tmp)/'game.json');g.new_game();g.transition_target=None
        for eid in SPRITES:
            for state in ('idle','run','attack','defeat'):
                frames=g.sprites.enemy_frames[(eid,state)]
                assert len(frames)==4 and all(f.get_bounding_rect().width for f in frames),(eid,state)
        for eid in SPRITES:
            src=pygame.image.load(Path(__file__).resolve().parents[1]/'assets'/'characters'/'enemies_expansion'/eid/'idle'/'0.png').convert_alpha()
            expected=pygame.transform.flip(src,True,False)
            actual=g.sprites.enemy_frames[(eid,'idle')][0]
            expected=expected.subsurface(expected.get_bounding_rect(min_alpha=8))
            actual=actual.subsurface(actual.get_bounding_rect(min_alpha=8))
            assert pygame.image.tobytes(expected,'RGBA')==pygame.image.tobytes(actual,'RGBA'),eid
        from dungeon_art import DungeonArt
        art=DungeonArt();seen=[];original_blit=art.blit
        def record(surface,name,pos,scale=2):
            seen.append(name);original_blit(surface,name,pos,scale)
        art.blit=record
        for act in range(1,9):art.arena((1200,666),act)
        assert 'crate' not in seen and not any(name.startswith('doors_') for name in seen)
        sheet=pygame.Surface((1200,960));sheet.fill((12,18,25))
        for n,stage in enumerate(STAGES[25:]):
            g.begin_battle(stage);g.transition_target=None;g.screen=Screen.BATTLE
            g.battle.enemy_index=len(stage.enemies)-2;g.battle._spawn_next_enemy();g.battle.phase='hero_windup';g.battle.anim_clock=1
            g.draw();crop=g.screen_surface.subsurface((660,190,520,430));thumb=pygame.transform.scale(crop,(240,198));x=n%5*240;y=n//5*260
            sheet.blit(thumb,(x,y+38));g.ui.fitted_text(sheet,f'{stage.index}: {g.battle.enemy.name}',pygame.Rect(x+8,y+10,224,25),(230,220,200),'small')
            if n in (4,9,14):pygame.image.save(g.screen_surface,out/f'battle-act{stage.act}.png')
        for n,key in enumerate(ICONS):
            item=create_item(key,random.Random(42),40);g.ui.draw_item_icon(sheet,pygame.Rect(n*100+18,814,64,64),item)
            g.ui.fitted_text(sheet,item.name,pygame.Rect(n*100+3,890,94,50),(230,220,200),'tiny')
            if item.kind.value=='potion':assert item.effects['heal_percent']>0 and item.effects['battle_attack']>0
        pygame.image.save(sheet,out/'expansion.png')
        g.health_fills={};g.health_fill('hero',100);v=g.health_fill('hero',20,.016);assert 20<v<100
        for _ in range(60):v=g.health_fill('hero',20,1/60)
        assert v==20
        for depth in (1,5,10,15,30,100):assert 1<=create_endless_stage(depth,11).act<=8
    results={}
    gears=(('crownless_oath','dragonbone_pavise','witchglass_bead','fortune_eclipse'),('tidebreaker','brineward','tidal_glass','fortune_eclipse'),('furnace_maul','cathedral_guard','ember_oath','tidal_glass'),('dawnspear','daybreak_aegis','dawn_relic','ember_oath'))
    for index,gear_index in ((26,0),(30,1),(31,1),(35,2),(36,2),(40,3)):
        wins=0
        for seed in range(80):
            h=runner(STAGES[index-1].recommended_level,gears[gear_index],seed)
            b=CombatEngine(h,STAGES[index-1],random.Random(seed+987))
            for _ in range(4000):
                if not b.active:break
                b.update(1)
            assert not b.active
            wins+=b.outcome.value=='victory'
        results[index]=wins/80
        assert .55 <= results[index] <= 1.0, (index, results[index])
        if index % 5 == 0: assert results[index] < .98, (index, results[index])
    (out/'balance.json').write_text(json.dumps(results,indent=2))
    pygame.quit();print('qa_expansion_ok: assets, migration, 40-stage roundtrip, bars, endless; win rates',results)
if __name__=='__main__':main()
