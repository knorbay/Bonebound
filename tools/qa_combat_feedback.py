"""Regression checks for simultaneous damage/status feedback and weapon alpha."""
import os, sys, tempfile
from pathlib import Path
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame
from game import Game, Screen
from combat import CombatEvent
from content import STAGES
from models import Element

def main():
    with tempfile.TemporaryDirectory() as tmp:
        g=Game(True,Path(tmp)/'save.json');g.new_game();g.begin_battle(STAGES[0])
        g.transition_target=None;g.screen=Screen.BATTLE;g.battle.drain_events()
        g.combat_bounds={'hero':pygame.Rect(270,425,120,160),'enemy':pygame.Rect(780,300,160,240)}
        for kind,actor,n in [('hero_hit','hero',20),('proc','hero',4),('proc','hero',7),('chill','hero',12),('boss_phase','enemy',0)]:
            g.battle.events.append(CombatEvent(kind,'QA',actor,n,element=Element.ICE))
        g.process_battle_events()
        notices=g.float_notices
        assert all(n.target=='enemy' for n in notices)
        assert all(abs(a.y-b.y)>=34 for i,a in enumerate(notices) for b in notices[i+1:])
        phase=notices[-1];assert phase.age==0 and phase.update(1.2)
        assert all(b.x==860 and b.y==420 for b in g.fx_bursts)
        g.shake=g.impact_pause=g.hero_hit_flash=0
        for kind,n in [('heal',8),('barrier',5),('boost',0)]:
            g.battle.events.append(CombatEvent(kind,'QA','hero',n))
        g.process_battle_events()
        assert g.shake==g.impact_pause==g.hero_hit_flash==0
        assert g.float_notices[-1].text=='BOOST'
        # Exercise the actual equipped-weapon render, including rotated trails.
        # Every trail surface must retain zero RGBA outside its silhouette.
        original_rotate=pygame.transform.rotate;trails=[]
        def capture(image, angle):
            if image.get_alpha()==255 and image.get_flags() & pygame.SRCALPHA:
                alphas=pygame.surfarray.array_alpha(image)
                if alphas.max() in (34,52):
                    trails.append(image.copy())
                    rgb=pygame.surfarray.array3d(image)
                    assert not rgb[alphas==0].any()
            return original_rotate(image,angle)
        pygame.transform.rotate=capture
        try:g.draw_equipped_gear(pygame.Rect(200,330,250,250),'attack',.18)
        finally:pygame.transform.rotate=original_rotate
        assert trails, 'Weapon trail path was not exercised'
        class CaptureSurface(pygame.Surface):
            def blit(self, source, *args, **kwargs):
                # Death overlays must never color transparent texels white.
                rgba = pygame.surfarray.array_alpha(source)
                rgb = pygame.surfarray.array3d(source)
                if source.get_alpha() is not None and source.get_alpha() < 255:
                    assert not (rgb[rgba == 0] == 255).all(axis=1).any()
                return super().blit(source, *args, **kwargs)
        g.screen_surface = CaptureSurface((1200,960))
        g.battle.phase='wave_clear'
        g.draw_enemy(pygame.Vector2(875,574),g.battle.enemy,'defeat',0)
        for elapsed in (.08,.16,.4,.7):
            g.time=g.actor_anim_started['enemy']+elapsed
            g.draw_enemy(pygame.Vector2(875,574),g.battle.enemy,'defeat',elapsed)
        g.battle.hero.equipment['weapon'].traits += ('leech',)
        g.battle.hero_hp -= 10; before=g.battle.hero_hp
        g.battle.enemy.hp=1000;g.battle.drain_events();g.battle._hero_strike()
        healed=sum(e.amount for e in g.battle.drain_events() if e.event_type=='heal')
        assert healed > 0 and g.battle.hero_hp-before == healed
        g.battle.events.append(CombatEvent('wave','New enemy','enemy'))
        g.process_battle_events();assert not g.float_notices and not g.fx_bursts
    pygame.quit();print('qa_combat_feedback_ok: stacked targets, phase duration, non-damage feedback, transparent trails, wave cleanup')
if __name__=='__main__':main()
