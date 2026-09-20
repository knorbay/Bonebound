from campaign_config import ACT_COUNT, TOTAL_STAGES
"""Scrollable atlas: presentation is independent of campaign progression."""
import math
import pygame
from presentation import REGION_COLORS, REGION_NAMES
from ui import COLORS

VIEW = pygame.Rect(44, 202, 727, 546)
WORLD_H = 224 * ACT_COUNT
REGION_H = WORLD_H / ACT_COUNT

def node_positions():
    result=[]
    for act in range(ACT_COUNT):
        for step,(x,y) in enumerate(((80,112),(208,144),(352,112),(496,144),(640,112))):
            result.append((x if act%2==0 else VIEW.width-x, round(act*REGION_H+y)))
    return result

def scroll_limit():
    return WORLD_H - VIEW.height

def focus(act):
    return max(0,min(scroll_limit(),round(act*REGION_H-80)))

def draw_map(g):
    ui=g.ui;s=g.screen_surface
    if g.map_scroll is None:g.map_scroll=focus((g.selected_stage-1)//5)
    ui.ornamented_panel(s,pygame.Rect(30,120,755,682),(13,20,27),(59,73,83),13,1)
    ui.text(s,"ATLAS OF THE FALLEN KINGDOM",(51,139),COLORS['gold'],'tiny')
    ui.text(s,f"{len(g.hero.cleared_stages)} / {TOTAL_STAGES} CLEARED",(762,139),COLORS['muted'],'tiny','topright')
    for act in range(ACT_COUNT):
        tab=pygame.Rect(46+act*91,164,86,28)
        selected=(g.selected_stage-1)//5==act
        if ui.button(s,tab,f"ACT {act+1}",g.mouse,g.clicked,True,REGION_COLORS[act] if selected else (63,76,87),'tiny'):
            g.map_scroll=focus(act)
            g.selected_stage=act*5+1
    old=s.get_clip();s.set_clip(VIEW)
    art=ui.dungeon.atlas((VIEW.width,WORLD_H),node_positions())
    s.blit(art,(VIEW.x,VIEW.y-g.map_scroll))
    # Restrained dark wash gives path markers contrast without hiding the atlas.
    key=('atlas_wash',VIEW.size)
    if key not in ui.scaled_images:
        wash=pygame.Surface(VIEW.size,pygame.SRCALPHA);wash.fill((4,9,16,12));ui.scaled_images[key]=wash
    s.blit(ui.scaled_images[key],VIEW)
    positions=[(VIEW.x+x,VIEW.y+y-g.map_scroll) for x,y in node_positions()]
    for i,(a,b) in enumerate(zip(positions,positions[1:])):
        complete=i+1 in g.hero.cleared_stages
        color=(163,147,102) if complete else (75,75,77)
        dist=math.dist(a,b)
        for n in range(1,int(dist)//14):
            t=n/(int(dist)//14);p=(round(a[0]+(b[0]-a[0])*t),round(a[1]+(b[1]-a[1])*t))
            pygame.draw.circle(s,(10,17,22),p,4)
            pygame.draw.circle(s,color,p,2 if complete else 1)
    for act in range(ACT_COUNT):
        y=VIEW.y+round(act*REGION_H)+23-g.map_scroll
        label=pygame.Rect(VIEW.x+18,y,315,34)
        pygame.draw.rect(s,(14,22,28),label,border_radius=5)
        pygame.draw.rect(s,REGION_COLORS[act],(label.x,label.y,3,label.height),border_radius=1)
        ui.text(s,f"0{act+1}  /  {REGION_NAMES[act]}",(label.x+14,label.y+10),REGION_COLORS[act],'tiny')
    for index,(x,y) in enumerate(positions,1):
        unlocked=index<=g.hero.unlocked_stage;cleared=index in g.hero.cleared_stages
        selected=index==g.selected_stage;boss=index%5==0;radius=20 if boss else 17
        hit=pygame.Rect(x-32,y-32,64,64)
        hovered=VIEW.collidepoint(g.mouse) and hit.collidepoint(g.mouse)
        c=(113,211,165) if cleared else REGION_COLORS[(index-1)//5] if unlocked else (96,112,127)
        if selected:
            pygame.draw.circle(s,(234,205,133),(x,y),radius+8,2)
            pygame.draw.circle(s,(96,81,54),(x,y),radius+11,1)
        pygame.draw.circle(s,(4,8,13),(x,y+3),radius+4)
        pygame.draw.circle(s,(31,42,52) if hovered else (13,22,31),(x,y),radius)
        pygame.draw.circle(s,c,(x,y),radius,2)
        if unlocked:
            ui.text(s,str(index),(x,y-1),COLORS['text'],'small','center')
        else:
            pygame.draw.arc(s,c,(x-5,y-9,10,12),0,math.pi,2)
            pygame.draw.rect(s,c,(x-7,y-2,14,10),border_radius=2)
            pygame.draw.circle(s,(13,22,31),(x,y+2),1)
        if boss:
            pygame.draw.lines(s,c,False,[(x-10,y-radius-7),(x-7,y-radius-1),(x,y-radius-9),(x+7,y-radius-1),(x+10,y-radius-7)],2)
        if cleared:
            pygame.draw.circle(s,(15,33,31),(x+17,y+17),8)
            pygame.draw.lines(s,c,False,[(x+13,y+17),(x+16,y+20),(x+22,y+13)],2)
        if hovered and g.clicked:
            g.selected_stage=index;g.audio.play('click')
        if hovered and not unlocked:
            ui.text(s,f"CLEAR {index-1} FIRST",(x,y+36),COLORS['text'],'tiny','center',True)
    s.set_clip(old)
    pygame.draw.rect(s,(64,79,88),VIEW,1,border_radius=2)
    # A narrow scrollbar communicates that the atlas continues below the viewport.
    track=pygame.Rect(VIEW.right-7,VIEW.y+8,3,VIEW.height-16)
    pygame.draw.rect(s,(34,43,49),track)
    thumb_h=round(track.height*VIEW.height/WORLD_H)
    thumb_y=track.y+round(g.map_scroll/scroll_limit()*(track.height-thumb_h))
    pygame.draw.rect(s,COLORS['gold'],(track.x,thumb_y,3,thumb_h),border_radius=1)
    ui.text(s,"SCROLL TO EXPLORE  /  SELECT A LANDMARK",(51,766),COLORS['muted'],'tiny')
    for x,label,delta in ((614,'UP',-220),(689,'DOWN',220)):
        if ui.button(s,pygame.Rect(x,758,67,30),label,g.mouse,g.clicked,True,COLORS['border'],'tiny'):
            g.map_scroll=max(0,min(scroll_limit(),g.map_scroll+delta))
