"""Verify real audio decoding, transitions, persistent levels and curated art."""
import os,sys,tempfile,hashlib
from pathlib import Path
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame,numpy as np
from audio import Audio
from game import Game,Screen
from content import STAGES,ITEM_TEMPLATES,create_item
from tools.build_curated_assets import SOURCES

def main():
    out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
    pygame.init()
    with tempfile.TemporaryDirectory() as tmp:
        settings=Path(tmp)/'audio_settings.json';a=Audio();a.bind_settings(settings)
        assert a.enabled and len(a.music_files)==6
        for name,p in a.music_files.items():
            snd=pygame.mixer.Sound(p);pcm=pygame.sndarray.array(snd).astype(float)/32768
            rms=float(np.sqrt(np.mean(pcm*pcm)))
            assert snd.get_length()>60 and rms>.02,(name,rms)
            level=rms*min(1,a.music_volume*a.TRACK_GAIN[name])
            assert .02<level<.1,(name,level)
        a.music('dungeon');assert pygame.mixer.music.get_busy()
        a.music('boss');assert a.current_music=='dungeon'
        for _ in range(30):a.update(.05)
        assert a.current_music=='boss' and a.pending_music is None and a.gain==1
        a.music('boss');assert a.pending_music is None
        a.music('battle');a.update(.1);a.music('boss');a.update(.5)
        assert a.current_music=='boss' and a.pending_music is None
        a.set_volume('music',.6);a.set_volume('effects',.5);a.toggle_music();a.toggle_effects()
        b=Audio();b.bind_settings(settings)
        assert b.music_volume==.6 and b.effects_volume==.5
        assert not b.music_enabled and not b.effects_enabled
        b.music('mystic');assert pygame.mixer.music.get_volume()==0
        b.toggle_music();assert pygame.mixer.music.get_volume()>0
        settings.write_text('{"music_volume": "bad", "effects_volume": 5}')
        c=Audio();c.bind_settings(settings);assert c.music_volume==.4 and c.effects_volume==1
        g=Game(True,Path(tmp)/'game.json');g.new_game();g.transition_target=None;g.screen=Screen.HUB
        assert g.music_for_screen()=='dungeon'
        g.begin_battle(STAGES[5]);g.transition_target=None;g.screen=Screen.BATTLE
        assert g.music_for_screen()=='fire'
        g.battle.enemy.boss=True;assert g.music_for_screen()=='boss'
        g.audio_panel=True;timer=g.battle.timer;g.update(.3);assert g.battle.timer==timer
        g.audio.current_music='boss';g.draw();pygame.image.save(g.screen_surface,out/'audio-panel.png')
        # Modal clicks change audio only and do not pass through to battle.
        before=g.audio.music_volume
        g.mouse=(708,395);g.clicked=True;g.draw()
        assert g.audio.music_volume==round(before+.1,2)
        g.mouse=(800,395);g.clicked=True;g.draw();assert not g.audio.music_enabled
        g.mouse=(600,623);g.clicked=True;g.draw();assert not g.audio_panel
        assert g.battle.timer==timer
        for name in SOURCES:
            img=g.ui.item_images[name]
            assert img.get_size()==(48,48)
            alpha=pygame.surfarray.array_alpha(img)
            assert (alpha==0).any() and (alpha>0).any()
            icon=g.ui.item_sprite(create_item(name),48,True);assert max(icon.get_size())<=48
        assert len(SOURCES)==100
        g.audio_panel=False;g.screen=Screen.INVENTORY;g.hero.inventory=[create_item(k) for k in list(SOURCES)[:12]]
        g.draw();pygame.image.save(g.screen_surface,out/'workshop.png')
    pygame.quit();print('qa_audio_assets_ok: six decoded tracks, balanced levels, fades, mute/persistence, routing, modal pause, 100 icons')
if __name__=='__main__':main()
