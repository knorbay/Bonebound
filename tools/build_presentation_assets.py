"""Generate original pixel icons and synthesized SFX without external assets."""
import os, sys, math, random, wave, struct
from pathlib import Path
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from content import REGIONAL_ITEMS
from presentation import REGION_COLORS
pygame.init()
for i,row in enumerate(REGIONAL_ITEMS):
    key=row[0]; s=pygame.Surface((48,48),pygame.SRCALPHA)
    c=REGION_COLORS[i//2]; dark=(35,39,53); white=(240,231,207); gold=(180,143,87)
    def poly(points,color): pygame.draw.polygon(s,color,points)
    if i%2==0:
        pygame.draw.line(s,dark,(10,41),(33,12),7)
        pygame.draw.line(s,gold,(10,40),(31,13),3)
        if i==0:
            poly([(25,17),(34,4),(39,3),(37,14),(29,24)],dark)
            poly([(28,17),(35,6),(36,13),(30,21)],white)
            for j in range(3): pygame.draw.line(s,c,(23+j*3,17-j*3),(27+j*3,21-j*3),2)
        elif i in (2,6):
            poly([(23,13),(29,5),(39,6),(45,13),(44,23),(40,16),(33,13),(28,22)],dark)
            poly([(26,13),(30,7),(38,8),(42,13),(42,18),(37,12),(32,11),(28,18)],c)
            if i==6: pygame.draw.circle(s,c,(41,27),2)
        elif i==4:
            poly([(24,18),(26,8),(38,3),(43,8),(37,17),(29,23)],dark)
            poly([(27,17),(29,9),(38,6),(40,9),(34,16),(29,20)],c)
            pygame.draw.line(s,white,(29,17),(38,7),2)
        else:
            poly([(25,16),(27,4),(35,9),(44,7),(43,19),(34,25)],dark)
            poly([(28,15),(29,7),(34,12),(41,10),(40,18),(34,22)],c)
        pygame.draw.line(s,white,(16,27),(23,32),2)
        pygame.draw.circle(s,c,(11,39),3)
    elif i==1:
        pygame.draw.arc(s,gold,(11,3,26,27),0,math.pi,2)
        poly([(24,14),(35,27),(31,39),(17,39),(13,27)],dark)
        poly([(24,18),(31,28),(28,35),(20,35),(17,28)],white)
        poly([(24,22),(27,29),(24,33),(21,29)],c)
    elif i==3:
        pygame.draw.circle(s,gold,(24,24),17,3)
        poly([(15,31),(16,20),(23,12),(25,23),(31,17),(34,29),(28,36),(20,35)],dark)
        poly([(19,29),(20,23),(24,18),(25,28),(29,23),(30,30),(26,33),(22,33)],c)
    elif i==5:
        pygame.draw.circle(s,dark,(24,24),18)
        pygame.draw.circle(s,gold,(24,24),16,3)
        pygame.draw.circle(s,c,(24,24),11,1)
        for j in range(4):
            a=j*math.pi/2;pygame.draw.circle(s,white,(round(24+13*math.cos(a)),round(24+13*math.sin(a))),2)
        poly([(25,13),(18,26),(24,25),(22,35),(31,21),(25,22)],c)
    elif i==7:
        pygame.draw.arc(s,gold,(17,3,14,15),0,math.pi,2)
        poly([(14,16),(34,16),(38,35),(31,41),(17,41),(10,35)],dark)
        pygame.draw.rect(s,c,(16,20,16,15),2)
        pygame.draw.line(s,gold,(13,16),(35,16),3)
        pygame.draw.line(s,gold,(13,37),(35,37),3)
        for x,y in ((21,24),(27,27),(22,31)):pygame.draw.circle(s,c,(x,y),2)
    else:
        poly([(24,3),(43,24),(24,44),(5,24)],dark)
        poly([(24,7),(39,24),(24,40),(9,24)],gold)
        poly([(24,11),(35,24),(24,36),(13,24)],dark)
        poly([(24,13),(27,23),(34,24),(26,27),(24,35),(21,26),(14,24),(22,22)],c)
        pygame.draw.circle(s,white,(24,24),2)
    pygame.image.save(s,ROOT/'assets'/'items'/f'{key}.png')

root=ROOT/'assets'/'audio'/'v3';root.mkdir(parents=True,exist_ok=True)
for k,name in enumerate(('element_fire','element_ice','element_storm','element_venom','element_arcane','boss_phase','victory')):
    rate=44100; duration=(.30,.38,.26,.40,.45,.85,.85)[k]; rng=random.Random(160+k);samples=[]
    for n in range(round(rate*duration)):
        t=n/rate;p=t/duration; envelope=min(1,t/.008)*(1-p)**2
        noise=rng.uniform(-1,1)
        if k==0: v=.55*noise+.25*math.sin(math.tau*(130*t-60*t*t))
        elif k==1: v=sum(math.sin(math.tau*f*t)*math.exp(-t*(8+j*5)) for j,f in enumerate((1900,2870,4110)))*.23
        elif k==2: v=.36*noise+.35*math.sin(math.tau*(440*t+700*t*t))*math.sin(math.tau*48*t)
        elif k==3: v=.55*math.sin(math.tau*(260*t-130*t*t)+3*math.sin(35*t))
        elif k==4: v=sum(math.sin(math.tau*f*t) for f in (440,660,881))*.19
        elif k==5: v=.38*math.sin(math.tau*(85*t-23*t*t))+.18*noise*math.exp(-9*t)
        else:
            v=0
            for j,f in enumerate((523.25,659.25,783.99,1046.5)):
                tt=t-j*.10
                if tt>=0:v+=.22*math.sin(math.tau*f*tt)*min(1,tt/.008)*math.exp(-tt*5)
        samples.append(round(max(-1,min(1,v*envelope))*.7*32767))
    with wave.open(str(root/f'{name}.wav'),'wb') as out:
        out.setnchannels(1);out.setsampwidth(2);out.setframerate(rate)
        out.writeframes(struct.pack('<'+'h'*len(samples),*samples))
pygame.quit()
from build_curated_assets import build
build()
print('Generated 7 synthesized SFX and repacked 10 curated CC0 item icons.')
