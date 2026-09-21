"""Deterministic, code-drawn regional scenery and combat accents."""
import math
import pygame
from models import Element

REGION_COLORS = ((159, 173, 183), (240, 110, 51), (106, 204, 239), (133, 190, 106), (182, 129, 237), (89, 188, 184), (218, 132, 85), (237, 207, 128))
REGION_NAMES = ("THE OSSUARY", "CINDER FORGE", "FROZEN HALLS", "THE POISON GARDEN", "STARLESS PALACE", "DROWNED ARCHIVE", "IRON CATHEDRAL", "DAWN GATE")


def region_layer(size, act):
    layer = pygame.Surface(size, pygame.SRCALPHA)
    w, h = size
    act = min(len(REGION_NAMES), max(1, act))
    color = REGION_COLORS[act - 1]
    def poly(points, fill):
        pygame.draw.polygon(layer, fill, [(round(x*w), round(y*h)) for x,y in points])
    if act == 1:
        for x in (.09, .29, .69, .89):
            r = pygame.Rect(x*w, .17*h, .065*w, .53*h)
            pygame.draw.rect(layer, (19, 26, 33, 230), r)
            pygame.draw.rect(layer, (*color, 90), r, 2)
            pygame.draw.arc(layer, (*color, 120), r.inflate(22, 12), math.pi, math.tau, 3)
            for k in range(4):
                pygame.draw.line(layer, (*color, 55), (r.x, r.y+k*h*.13), (r.right, r.y+k*h*.13), 2)
    elif act == 2:
        for x in (.12, .5, .88):
            r = pygame.Rect(x*w-32, .03*h, 64, .61*h)
            pygame.draw.rect(layer, (21, 13, 17, 220), r)
            pygame.draw.rect(layer, (*color, 100), r, 3)
            for k in range(4):
                pygame.draw.line(layer, (*color, 150), (r.x+12, r.y+70+k*38), (r.right-12, r.y+70+k*38), 4)
        for x in (.03, .36, .73):
            poly([(x,.90),(x+.10,.88),(x+.17,.91),(x+.25,.89),(x+.28,.94),(x+.1,.92)], (*color, 150))
    elif act == 3:
        for k in range(12):
            x = k / 11
            length = .14 + (k*7%5)*.035
            poly([(x-.027,0),(x+.028,0),(x+.005,length)], (126, 205, 240, 140))
        for x in (.04, .18, .79, .92):
            poly([(x-.035,.82),(x-.025,.49),(x,.38),(x+.03,.57),(x+.04,.82)], (95,170,210,140))
            poly([(x,.40),(x+.03,.58),(x,.79)], (187,232,247,120))
    elif act == 4:
        for x in (.04, .17, .80, .94):
            pygame.draw.line(layer, (54,89,67,220), (x*w,0), ((x+.03)*w,.61*h), 5)
            for k in range(5):
                y=.08+k*.11
                poly([(x+.01,y),(x-.035,y-.035),(x-.02,y+.04)], (*color,135))
                poly([(x+.02,y+.05),(x+.065,y+.01),(x+.05,y+.08)], (*color,100))
        for x in (.08, .22, .76, .90):
            pygame.draw.ellipse(layer, (*color, 65), (x*w,.87*h,.10*w,.045*h))
    else:
        for x in (.08,.22,.74,.88):
            poly([(x,0),(x+.05,0),(x+.04,.68),(x+.01,.68)], (21,17,38,220))
            pygame.draw.line(layer, (*color,110), (x*w,0), ((x+.01)*w,.68*h), 2)
        center=(round(w*.5),round(h*.29))
        for radius in (45, 67, 89):
            pygame.draw.circle(layer, (*color,80), center, radius, 2)
        for k in range(12):
            a=k*math.tau/12
            pygame.draw.circle(layer, (232,204,255,170), (round(center[0]+89*math.cos(a)),round(center[1]+89*math.sin(a))), 3)
    return layer


def draw_atmosphere(surface, rect, act, clock):
    act = min(len(REGION_NAMES), max(1, act))
    c = REGION_COLORS[act-1]
    for k in range(18):
        x=rect.x+(k*139+math.sin(clock*.3+k)*17)%rect.width
        travel=clock*(18 if act==3 else -12)
        y=rect.y+(k*67+travel)%max(1,rect.height-94)
        r=1+k%2
        pygame.draw.circle(surface, tuple(round(v*(.35+(k%3)*.15)) for v in c), (round(x),round(y)), r)


def draw_element_impact(layer, x, y, element, progress, block=False):
    alpha=round(230*(1-progress))
    radius=18+progress*64
    if block:
        points=[(x-30,y-38),(x+30,y-38),(x+26,y+14),(x,y+40),(x-26,y+14)]
        pygame.draw.polygon(layer,(154,219,255,alpha), points, 4)
        return
    if element == Element.STORM:
        for k in range(4):
            points=[]
            a=k*math.pi/2+.3
            for j in range(6):
                d=j*radius/4
                side=math.sin(j*5+k)*13*(1-progress)
                points.append((x+math.cos(a)*d-math.sin(a)*side,y+math.sin(a)*d+math.cos(a)*side))
            pygame.draw.lines(layer,(255,236,135,alpha),False,points,3)
    elif element == Element.ICE:
        for k in range(7):
            a=k*math.tau/7
            cx=x+math.cos(a)*radius; cy=y+math.sin(a)*radius
            pygame.draw.polygon(layer,(174,236,255,alpha),[(cx,cy-11),(cx+4,cy),(cx,cy+7),(cx-4,cy)],2)
    elif element == Element.FIRE:
        for k in range(8):
            cx=x+math.cos(k*2.4)*radius*.65; cy=y-progress*85+math.sin(k)*20
            pygame.draw.polygon(layer,(255,133+k*10,49,alpha),[(cx-5,cy+8),(cx+2,cy-15),(cx+6,cy+9)])
    elif element == Element.VENOM:
        for k in range(8):
            cx=x+math.cos(k*2.4)*radius;cy=y+math.sin(k*2.4)*radius*.5+progress*22
            pygame.draw.circle(layer,(155,228,91,alpha),(round(cx),round(cy)),3+k%4,2)
    elif element == Element.ARCANE:
        points=[(x+math.cos(k*math.tau/6+progress)*radius,y+math.sin(k*math.tau/6+progress)*radius) for k in range(6)]
        pygame.draw.polygon(layer,(215,164,255,alpha),points,2)
        pygame.draw.lines(layer,(239,213,255,alpha),True,points[::2],2)
