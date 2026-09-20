"""Room layouts assembled from 0x72's CC0 Dungeon Tileset II."""
from pathlib import Path
import pygame

ROOT = Path(__file__).resolve().parent / 'assets' / 'third_party' / '0x72_dungeon'

class DungeonArt:
    def __init__(self):
        self.tiles={}
        self.cache={}
        for path in ROOT.glob('*.png'):
            self.tiles[path.stem]=pygame.image.load(path).convert_alpha()

    def tile(self,name,scale=2):
        key=(name,scale)
        if key not in self.cache:
            src=self.tiles[name]
            self.cache[key]=pygame.transform.scale(src,(src.get_width()*scale,src.get_height()*scale))
        return self.cache[key]

    def blit(self,s,name,pos,scale=2):
        s.blit(self.tile(name,scale),pos)

    def atlas(self,size,positions):
        key=('atlas',size)
        if key in self.cache:return self.cache[key]
        s=pygame.Surface(size);s.fill((15,17,22))
        # Corridors are built first so the room floor covers their joins.
        for a,b in zip(positions,positions[1:]):
            ax,ay=a;bx,by=b
            points=((ax,ay),(bx,ay),(bx,by))
            for p,q in zip(points,points[1:]):
                if p[0]==q[0]:
                    for y in range(min(p[1],q[1])-16,max(p[1],q[1])+16,16):self.blit(s,'floor_1',(p[0]-16,y))
                else:
                    for x in range(min(p[0],q[0])-16,max(p[0],q[0])+16,16):self.blit(s,'floor_1',(x,p[1]-16))
        banners=('wall_banner_yellow','wall_banner_red','wall_banner_blue','wall_banner_green','wall_banner_blue','wall_banner_blue','wall_banner_red','wall_banner_yellow')
        for i,(cx,cy) in enumerate(positions):
            act=i//5;boss=i%5==4
            left=cx-48;top=cy-48
            for row in range(3):
                for col in range(3):
                    self.blit(s,'floor_'+str(1+(i+row*3+col)%8),(left+col*32,top+row*32))
            for col in range(3):
                self.blit(s,'wall_top_mid',(left+col*32,top-40))
                self.blit(s,'wall_mid',(left+col*32,top-24))
                self.blit(s,'edge_down',(left+col*32,top+96))
            self.blit(s,'wall_left',(left-16,top-24))
            self.blit(s,'wall_right',(left+80,top-24))
            self.blit(s,banners[act],(cx-16,top-24))
            # Each room has its own landmark instead of a field of identical circles.
            prop=('skull','crate','column','wall_goo_base','chest_full_open_anim_f0','wall_goo_base','column','chest_full_open_anim_f0')[act]
            self.blit(s,prop,(left+4,top+50))
            if boss:
                self.blit(s,'chest_full_open_anim_f0',(cx+18,cy+12))
                self.blit(s,'column',(left-12,top-32))
                self.blit(s,'column',(left+82,top-32))
            elif i%2:
                self.blit(s,'floor_stairs',(cx+16,cy+16))
            else:
                self.blit(s,'crate',(cx+24,cy+18))
        self.cache[key]=s
        return s

    def arena(self,size,act):
        key=('arena',size,act)
        if key in self.cache:return self.cache[key]
        # Compose at a fixed pixel density, then scale with nearest-neighbour.
        # Match the battle viewport aspect ratio: square source pixels stay square.
        w,h=400,222
        low=pygame.Surface((w,h));low.fill((19,20,26))
        horizon=148
        for y in range(0,horizon,16):
            for x in range(0,w,16):
                name='wall_hole_1' if (x//16+y//16*3)%67==7 else 'wall_mid'
                self.blit(low,name,(x,y),1)
        for y in range(horizon,h,16):
            for x in range(0,w,16):
                self.blit(low,'floor_'+str(1+(x//16+y//16*3)%8),(x,y),1)
        for x in range(0,w,16):self.blit(low,'wall_top_mid',(x,horizon-10),1)
        banners=('wall_banner_yellow','wall_banner_red','wall_banner_blue','wall_banner_green','wall_banner_blue','wall_banner_blue','wall_banner_red','wall_banner_yellow')
        columns=(24,144,240,360) if act==7 else (52,332) if act==8 else (32,352)
        for x in columns:
            self.blit(low,'column_wall',(x,104),2)
            self.blit(low,banners[min(7,act-1)],(x+1,72),1)
        fountain='red' if act in (2,7) else 'blue'
        self.blit(low,'wall_fountain_top_2',(192,100),1)
        self.blit(low,'wall_fountain_mid_'+fountain+'_anim_f0',(192,116),1)
        self.blit(low,'wall_fountain_basin_'+fountain+'_anim_f0',(192,132),1)
        # Keep the fighting floor clear. The tall crate sprite read as tiny,
        # disconnected doors when placed at the two edges of this side view.
        if act in (4,6):
            for x in (66,150,272):self.blit(low,'wall_goo',(x,horizon-32),1)
        tint = {6:(132,178,185),7:(190,145,128),8:(192,185,155)}.get(act,(155,159,171))
        low.fill(tint,special_flags=pygame.BLEND_RGB_MULT)
        self.cache[key]=pygame.transform.scale(low,size)
        return self.cache[key]
