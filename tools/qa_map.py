import os, sys, tempfile, random
from pathlib import Path
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pygame
from game import Game,Screen
from content import STAGES,create_item
from world_map import VIEW,node_positions,focus,scroll_limit
from audio import Audio

def main():
    out=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'work'/'qa_map';out.mkdir(parents=True,exist_ok=True)
    g=Game(True);g.new_game();g.transition_target=None;g.screen=Screen.HUB
    g.draw();pygame.image.save(g.screen_surface,out/'map-start.png')
    # Act tabs expose locked chapters for inspection without entering them.
    for act in range(8):
        g.mouse=(85+act*91,178);g.clicked=True;g.draw()
        assert g.selected_stage==act*5+1
        assert g.map_scroll==focus(act)
        x,y=node_positions()[act*5];g.mouse=(VIEW.x+x,VIEW.y+y-g.map_scroll)
        g.clicked=True;g.draw();assert g.selected_stage==act*5+1
        g.clicked=False
    g.selected_stage=40;g.map_scroll=scroll_limit();g.mouse=(980,760);g.clicked=True;g.draw()
    assert g.battle is None, 'Locked stage must not launch'
    g.hero.unlocked_stage=40;g.hero.cleared_stages=set(range(1,40));g.hero.boost_uid=g.hero.inventory[0].uid
    g.clicked=False;g.mouse=(0,0);g.draw();pygame.image.save(g.screen_surface,out/'map-final.png')
    g.mouse=VIEW.center;pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL,y=1000,x=0));g.handle_events();assert g.map_scroll==0
    pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL,y=-1000,x=0));g.handle_events();assert g.map_scroll==scroll_limit()
    g.begin_battle(STAGES[5]);g.transition_target=None;g.screen=Screen.BATTLE;g.battle.phase='hero_windup';g.battle.anim_clock=2;g.draw()
    pygame.image.save(g.screen_surface,out/'battle-curated.png')
    a=Audio();assert a.enabled
    for name in ('hit','hurt','equip','door','book','collect','enemy_down','block'):
        assert a.sounds[name],name
        a.play(name)
    a.toggle_effects();assert not a.effects_enabled;a.toggle_effects();assert a.effects_enabled
    a.music('ambient');a.toggle_music();assert pygame.mixer.music.get_volume()==0
    a.toggle_music();assert pygame.mixer.music.get_volume()>0
    # Inventory icons all fit their target rectangles regardless of source padding.
    for name in g.ui.item_images:
        from content import ITEM_TEMPLATES
        if name not in ITEM_TEMPLATES:continue
        icon=g.ui.item_sprite(create_item(name,random.Random(2)),48,crop=True)
        assert max(icon.get_size())<=48
    pygame.quit();print('qa_map_ok: 40 stages, tabs, locked entry, scroll bounds, 8 sound events, audio toggles, icon bounds')
if __name__=='__main__': main()
