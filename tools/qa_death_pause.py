import os,sys,tempfile
from pathlib import Path
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame
from game import Game,Screen
from content import STAGES,ENEMIES
from combat import BattleOutcome,CombatEvent

def main():
    out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        g=Game(True,Path(tmp)/'save.json');g.new_game();g.transition_target=None
        seen=set();sheet=pygame.Surface((1200,870));sheet.fill((12,18,25));row=0
        for stage in STAGES:
            g.begin_battle(stage);g.transition_target=None;g.screen=Screen.BATTLE
            for i in range(len(stage.enemies)):
                if i:g.battle._spawn_next_enemy()
                enemy=g.battle.enemy
                if enemy.enemy_id in seen:continue
                seen.add(enemy.enemy_id);g.battle.phase='player_windup'
                g.actor_anim_key['enemy']=None;g.time=0
                g.draw_enemy(pygame.Vector2(875,574),enemy,'idle',0)
                original=g.combat_bounds['enemy'].copy();pose=g.enemy_still_pose
                # Death remains identical even if the camera shake/input position changes.
                for j,t in enumerate((0,.14,.44,.76)):
                    g.time=t
                    g.screen_surface.fill((18,24,33))
                    g.draw_enemy(pygame.Vector2(885+j*3,574),enemy,'defeat',t)
                    assert g.combat_bounds['enemy']==original,(enemy.enemy_id,t)
                    assert g.enemy_still_pose is pose
                    if enemy.enemy_id in {'dust_rat','bone_scout','thunder_crow'}:
                        crop=g.screen_surface.subsurface((635,190,480,430))
                        sheet.blit(pygame.transform.scale(crop,(300,269)),(j*300,row*290+21))
                        g.ui.text(sheet,f'{enemy.name}  /  {t:.2f}s',(j*300+12,row*290+2),font='tiny')
                if enemy.enemy_id in {'dust_rat','bone_scout','thunder_crow'}:row+=1
        assert seen==set(ENEMIES)
        pygame.image.save(sheet,out/'death-still.png')
        g.begin_battle(STAGES[0]);g.transition_target=None;g.screen=Screen.BATTLE
        # Escape pauses, no accidental retreat; P resumes.
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE));g.handle_events()
        assert g.battle_paused and g.battle.active
        timer=g.battle.timer;clock=g.time;g.update(2)
        assert g.battle.timer==timer and g.time==clock
        g.draw();pygame.image.save(g.screen_surface,out/'pause.png')
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_p));g.handle_events()
        assert not g.battle_paused
        g.update(.1);assert g.battle.timer<timer
        g.battle.hero_barrier=4;g.battle.bonus_stats['defense']=3;g.battle.boost_turns=2;g.battle.enemy_chill=.12
        hero,enemy=g.battle_status();assert 'BARRIER 4' in hero and '+3 DEF' in hero and '2 TURNS' in hero and '12%' in enemy
        g.battle.events.append(CombatEvent('boost_fade','Expired','hero'));g.process_battle_events()
        assert g.float_notices[-1].text=='BOOST ENDED'
        g.battle_paused=True;g.mouse=(750,665);g.clicked=True;g.draw()
        assert g.battle.outcome==BattleOutcome.RETREATED and not g.battle_paused and g.transition_target==Screen.HUB
    pygame.quit();print(f'qa_death_pause_ok: {len(seen)} frozen enemy silhouettes, no source death animation, pause/resume/retreat, status durations')
if __name__=='__main__':main()
