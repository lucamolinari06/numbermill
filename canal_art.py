"""Reedhaven: pale lockstone, patinated copper and a wide reed-fringed lake."""
import math
import random
import pygame
import canal_layout as layout
import scene_depth
import town_art
import town_roofs
from ui_theme import INK, COPPER, GOLD, PAPER, TEAL

GRASS=(137,153,111)
STONE=(200,193,158)
WATER=(69,122,133)
WOOD=(122,91,61)


def boat(surface,x,y,repaired=True,seconds=0.):
    """A small broadside steam launch; (x,y) is its waterline centre."""
    x,y=round(x),round(y)
    pygame.draw.ellipse(surface,(54,103,115),(x-92,y+18,187,21))
    pygame.draw.polygon(surface,(67,58,45),[(x-90,y-8),(x+80,y-8),(x+67,y+31),(x-62,y+35),(x-88,y+9)])
    pygame.draw.polygon(surface,(139,84,51),[(x-85,y-7),(x+76,y-7),(x+63,y+23),(x-60,y+27)])
    for yy in range(y-1,y+23,7):
        pygame.draw.line(surface,(174,111,65),(x-76+(yy-y)//2,yy),(x+65-(yy-y)//3,yy),2)
    pygame.draw.polygon(surface,(207,167,105),[(x-82,y-11),(x+77,y-11),(x+67,y+2),(x-73,y+2)])
    for xx in range(x-65,x+65,12):
        pygame.draw.line(surface,(157,122,76),(xx,y-10),(xx-4,y+1))
    pygame.draw.rect(surface,(74,100,91),(x-13,y-42,58,31))
    pygame.draw.rect(surface,(167,181,144),(x-16,y-45,64,5))
    pygame.draw.rect(surface,(55,85,86),(x-5,y-36,22,18))
    pygame.draw.rect(surface,(143,190,178),(x-2,y-33,16,11))
    pygame.draw.line(surface,PAPER,(x+5,y-33),(x+5,y-22),2)
    pygame.draw.rect(surface,(92,69,49),(x+25,y-38,14,27))
    pygame.draw.circle(surface,GOLD,(x+28,y-24),2)
    pygame.draw.rect(surface,(49,61,57),(x-45,y-38,17,27))
    pygame.draw.rect(surface,COPPER if repaired else (107,94,65),(x-47,y-43,21,7))
    pygame.draw.line(surface,GOLD if repaired else WOOD,(x-56,y-9),(x-56,y-26),3)
    pygame.draw.circle(surface,(188,145,76),(x-56,y-29),6,2)
    for xx in (x-67,x+59):
        pygame.draw.circle(surface,(62,65,57),(xx,y+11),7,3)
    if not repaired:
        pygame.draw.line(surface,WOOD,(x-12,y-39),(x+37,y-13),6)
        pygame.draw.line(surface,(189,143,85),(x-11,y-40),(x+37,y-14),2)
    elif seconds:
        for i in range(3):
            phase=(seconds*.32+i/3)%1
            pygame.draw.rect(surface,(198,208,185),(x-42+round(phase*12),y-49-round(phase*29),5+round(phase*3),3))


def _tree(surface,x,y,seed):
    rng=random.Random(seed)
    pygame.draw.ellipse(surface,(111,132,95),(x-35,y-9,72,20))
    pygame.draw.rect(surface,(99,85,59),(x-5,y-73,11,73))
    pygame.draw.line(surface,(173,157,105),(x-3,y-70),(x-3,y-3),2)
    for dx,dy,r in ((-21,-75,27),(17,-83,34),(-3,-111,31),(-27,-103,22),(27,-112,21)):
        color=rng.choice(((85,120,81),(97,132,89),(118,147,99),(130,155,103)))
        pygame.draw.circle(surface,color,(x+dx,y+dy),r)
        for _ in range(9):
            xx=x+dx+rng.randrange(-r+4,r-3); yy=y+dy+rng.randrange(-r+4,r-3)
            if (xx-x-dx)**2+(yy-y-dy)**2<r*r:
                pygame.draw.rect(surface,tuple(min(255,c+14) for c in color),(xx,yy,5,3))


def _roof(surface,points,key):
    # Reuse the material-aware roof painter, with Reedhaven's patinated metal.
    material,color=('home_1',(151,112,81)) if key=='west_home' else ('parts_shop',(95,113,119)) if key=='east_home' else ('toolmaker',(91,130,116))
    town_roofs.draw(surface,points,material,color)
    pygame.draw.lines(surface,(166,177,135),False,points[:2],2)
    # Riveted copper edges remain thin; no untextured side-face wedges.
    for a,b in zip(points,(*points[1:],points[0])):
        length=math.dist(a,b)
        for i in range(0,max(1,int(length)),22):
            blend=i/max(1,length)
            pygame.draw.rect(surface,(198,159,99),(round(a[0]+(b[0]-a[0])*blend),round(a[1]+(b[1]-a[1])*blend),2,2))


def _building(surface,key):
    (x,y),width,height,kind=layout.BUILDINGS[key]
    left=x-width//2; top=y-height
    pygame.draw.ellipse(surface,(107,123,92),(left-16,y-18,width+35,35))
    pygame.draw.rect(surface,(116,115,91),(left-6,top-5,width+12,height+7))
    pygame.draw.rect(surface,STONE,(left,top,width,height))
    town_art.brickwork(surface,(left+2,top+3,width-4,height-6),
        ((203,196,164),(214,204,170),(194,190,159),(218,210,178)),sum(map(ord,key)),rows=18,columns=36)
    pygame.draw.rect(surface,(173,169,136),(left,y-20,width,20))
    for xx in (left+2,left+width-16):
        for yy in range(top+3,y-18,21):
            pygame.draw.rect(surface,(227,216,179),(xx,yy,14,17))
    pygame.draw.rect(surface,(100,87,61),(x-21,y-65,42,65))
    pygame.draw.rect(surface,(64,101,94),(x-16,y-61,32,61))
    for xx in range(x-13,x+15,8):pygame.draw.line(surface,(94,130,114),(xx,y-58),(xx,y-3),1)
    pygame.draw.circle(surface,GOLD,(x+10,y-29),3)
    pygame.draw.rect(surface,(225,212,169),(x-29,y-2,58,9))
    for xx in (left+25,left+width-60):town_art.window(surface,xx,y-105,34,38,arched=True,shutters=kind=='home')
    if kind=='boathouse':
        pygame.draw.rect(surface,(75,77,59),(x-51,y-96,102,96))
        for xx in range(x-47,x+49,12):pygame.draw.rect(surface,(132,105,69),(xx,y-92,9,89))
        pygame.draw.lines(surface,(196,160,99),False,[(x-48,y-89),(x+46,y-7),(x+46,y-89),(x-48,y-7)],3)
    ridge=top-(51 if kind=='chandlery' else 75)
    roof=[(left-13,top+5),(left+25,ridge),(left+width-22,ridge),(left+width+13,top+5)]
    if kind=='lockhouse':roof=[(left-12,top+5),(x-24,ridge-20),(left+width+12,top+5)]
    elif kind=='boathouse':roof=[(left-16,top+6),(x,ridge-23),(left+width+16,top+6)]
    elif key=='west_home':roof=[(left-12,top+5),(x-18,ridge-14),(left+width+12,top+5)]
    _roof(surface,roof,key)
    pygame.draw.line(surface,(76,89,72),(left-12,top+6),(left+width+12,top+6),4)
    if kind=='chandlery':
        # A rope walk and small clerestory give this building a low working profile.
        pygame.draw.rect(surface,(181,176,141),(x-38,ridge-20,76,22))
        for xx in range(x-31,x+30,15):pygame.draw.rect(surface,(81,127,127),(xx,ridge-16,10,12))
        pygame.draw.rect(surface,(88,122,107),(x-43,ridge-25,86,6))
        for xx in (left+20,left+65):
            pygame.draw.circle(surface,(126,96,58),(xx,y-8),16,5)
            pygame.draw.circle(surface,(204,171,106),(xx,y-9),14,3)
            pygame.draw.line(surface,(204,171,106),(xx+12,y-6),(xx+36,y+6),3)
    elif kind=='lockhouse':
        pygame.draw.rect(surface,(178,174,137),(x-29,ridge-62,58,63))
        town_art.brickwork(surface,(x-27,ridge-60,54,59),((205,198,162),(194,190,151)),2,rows=15,columns=25)
        pygame.draw.rect(surface,(57,83,77),(x-14,ridge-49,28,31))
        town_art.gear(surface,(x,ridge-34),12,color=(200,164,95))
        pygame.draw.polygon(surface,(76,116,103),[(x-38,ridge-61),(x,ridge-88),(x+38,ridge-61)])
        pygame.draw.line(surface,GOLD,(x,ridge-88),(x,ridge-105),3)
        pygame.draw.polygon(surface,(176,115,66),[(x,ridge-104),(x+28,ridge-98),(x,ridge-92)])
    elif kind=='market':
        for index in range(9):
            xx=left+10+index*28
            col=(92,132,116) if index%2 else (230,211,157)
            pygame.draw.polygon(surface,col,[(xx,y-69),(xx+28,y-69),(xx+31,y-40),(xx-3,y-40)])
            pygame.draw.rect(surface,tuple(max(0,c-19) for c in col),(xx-3,y-40,34,9))
        for xx in (left+10,left+width-10):pygame.draw.line(surface,WOOD,(xx,y-40),(xx,y+20),5)
        pygame.draw.rect(surface,(130,94,59),(left+18,y+1,width-36,25))
        for xx in range(left+24,left+width-25,35):
            pygame.draw.rect(surface,(187,139,78),(xx,y-11,29,17))
            for dx in (4,12,20):pygame.draw.ellipse(surface,(229,185,104),(xx+dx,y-8,8,8))
    # Iron-bracket lantern beside each door, with a visibly solid fixture.
    pygame.draw.lines(surface,(70,77,63),False,[(x+20,y-82),(x+31,y-82),(x+31,y-71)],3)
    pygame.draw.rect(surface,(80,77,55),(x+24,y-71,14,22))
    pygame.draw.rect(surface,(215,169,87),(x+27,y-68,8,15))
    pygame.draw.line(surface,(110,91,58),(x+31,y-69),(x+31,y-52),2)


GLASS_LIGHTS={town_art.GLASS:(239,185,99,240),(87,139,139):(220,151,73,225),
              (175,205,186):(255,219,146,240),(132,175,164):(249,199,117,240),
              (81,127,127):(239,185,99,225)}


def building_light(image,bounds,key):
    """Only visible glazing receives warm pixels; all framing stays intact."""
    (x,y),width,height,kind=layout.BUILDINGS[key];left=x-width//2
    light=pygame.Surface(image.get_size(),pygame.SRCALPHA)
    regions=[pygame.Rect(xx,y-105,34,38) for xx in (left+25,left+width-60)]
    if kind=='chandlery':
        ridge=y-height-51
        regions.extend(pygame.Rect(xx,ridge-16,10,12) for xx in range(x-31,x+30,15))
    for region in regions:
        area=region.move(-bounds.x,-bounds.y).clip(image.get_rect())
        for xx in range(area.left,area.right):
            for yy in range(area.top,area.bottom):
                color=image.get_at((xx,yy))
                replacement=GLASS_LIGHTS.get(tuple(color)[:3])
                if color.a and replacement:light.set_at((xx,yy),replacement)
    lx,ly=x-bounds.x,y-bounds.y
    pygame.draw.rect(light,(254,205,110,25),(lx+18,ly-78,26,36))
    pygame.draw.rect(light,(255,225,146,210),(lx+27,ly-68,8,15))
    return light


def _crate(surface,x,y,seed=0):
    pygame.draw.rect(surface,(91,73,48),(x-19,y-28,38,29))
    pygame.draw.rect(surface,(159,119,67),(x-17,y-26,34,25))
    for yy in range(y-23,y-2,7):pygame.draw.line(surface,(190,149,88),(x-15,yy),(x+15,yy),1)
    pygame.draw.lines(surface,(105,79,47),False,[(x-15,y-25),(x+15,y-3),(x+15,y-25),(x-15,y-3)],3)
    for xx in (x-15,x+14):pygame.draw.line(surface,(218,177,110),(xx,y-25),(xx,y-3),2)


def _bridge(surface):
    r=layout.BRIDGE
    pygame.draw.rect(surface,(79,74,52),r)
    pygame.draw.rect(surface,(157,130,82),r.inflate(-8,0))
    for yy in range(r.top+3,r.bottom,12):
        pygame.draw.rect(surface,(176+(yy//12%3)*5,145,93),(r.left+7,yy,r.width-14,9))
        pygame.draw.line(surface,(115,94,62),(r.left+8,yy+10),(r.right-9,yy+10),2)
    for xx in (r.left+10,r.right-12):
        for yy in range(r.top+10,r.bottom-5,36):pygame.draw.rect(surface,(218,187,121),(xx,yy,3,3))


def _bridge_rail(surface,x,y):
    pygame.draw.rect(surface,(78,80,61),(x-5,y-49,10,51))
    pygame.draw.rect(surface,(167,137,83),(x-3,y-47,6,45))
    pygame.draw.rect(surface,(211,177,105),(x-7,y-51,14,5))


def _lock(surface):
    # Upstream closed lock: deliberately scenery, with a survey plaque on shore.
    for xx in (135,240):
        pygame.draw.rect(surface,(127,139,116),(xx,304,32,294))
        town_art.brickwork(surface,(xx+2,306,28,288),((184,185,151),(165,173,139)),xx,rows=20,columns=24)
    for yy in (349,513):
        pygame.draw.line(surface,(69,80,67),(155,yy),(255,yy+15),14)
        pygame.draw.line(surface,(147,111,63),(155,yy-3),(254,yy+12),5)
    pygame.draw.rect(surface,(91,107,87),(130,579,160,34))
    pygame.draw.line(surface,GOLD,(146,589),(271,589),3)
    town_art.gear(surface,(192,580),22,color=(190,152,85))


def road_layers():
    """Texture is clipped to the complete union of streets, mouths and courts.

    Drawing a brick whose origin is on a road lets its far edge leak onto grass.
    Full-layer alpha masking also prevents seams between separately painted
    branches and their round endcaps.
    """
    size=(layout.WIDTH,layout.HEIGHT)
    def rounded(path):
        if len(path)<3:return path
        result=[path[0]]
        for a,b,c in zip(path,path[1:],path[2:]):
            before=math.dist(a,b);after=math.dist(b,c)
            cut=min(52.,before*.32,after*.32)
            start=(b[0]+(a[0]-b[0])*cut/before,b[1]+(a[1]-b[1])*cut/before)
            end=(b[0]+(c[0]-b[0])*cut/after,b[1]+(c[1]-b[1])*cut/after)
            result.append(tuple(map(round,start)))
            for i in range(1,9):
                t=i/8
                result.append((round((1-t)**2*start[0]+2*t*(1-t)*b[0]+t*t*end[0]),
                               round((1-t)**2*start[1]+2*t*(1-t)*b[1]+t*t*end[1])))
        result.append(path[-1])
        return result
    paths=[rounded(path) for path in layout.PATHS]
    def coverage(extra):
        mask=pygame.Surface(size,pygame.SRCALPHA)
        for index,path in enumerate(paths):
            width=(56 if index==0 else 52 if index==2 else 42 if index in (6,7,9) else 68)+extra
            pygame.draw.lines(mask,(255,255,255,255),False,path,width)
            for point in path:pygame.draw.circle(mask,(255,255,255,255),point,width//2)
        square=layout.SQUARE.inflate(extra,extra)
        pygame.draw.rect(mask,(255,255,255,255),square,border_radius=42+extra//2)
        # Soft widened courts terminate secondary paths with a purpose.
        for point,radius in (((230,685),43),((1680,1100),49),((2390,410),50)):
            pygame.draw.circle(mask,(255,255,255,255),point,radius+extra//2)
        for (x,y),_,_,_ in layout.BUILDINGS.values():
            pygame.draw.rect(mask,(255,255,255,255),(x-43-extra//2,y-5-extra//2,86+extra,46+extra),border_radius=9+extra//2)
        return mask
    mask=coverage(0);shoulder_mask=coverage(10)
    shoulder=pygame.Surface(size,pygame.SRCALPHA);shoulder.fill((155,159,121,255))
    shoulder.blit(shoulder_mask,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
    paving=pygame.Surface(size,pygame.SRCALPHA);paving.fill((181,179,142,255))
    rng=random.Random(18179)
    for yy in range(0,layout.HEIGHT,14):
        for xx in range(-27+(yy//14%2)*13,layout.WIDTH,27):
            color=rng.choice(((190,185,148),(173,173,139),(184,181,145)))
            pygame.draw.rect(paving,color,(xx,yy,23+rng.randrange(3),10),border_radius=2)
            pygame.draw.line(paving,(198,193,155),(xx+2,yy+1),(xx+18,yy+1))
    paving.blit(mask,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
    return mask,shoulder,paving


def build_scene():
    rng=random.Random(91271)
    ground=pygame.Surface((layout.WIDTH,layout.HEIGHT));ground.fill(GRASS)
    # Clusters of low meadow texture keep paved routes and silhouettes readable.
    for _ in range(19000):
        x=rng.randrange(layout.WIDTH);y=rng.randrange(layout.HEIGHT)
        col=rng.choice(((143,158,116),(132,149,106),(149,161,117),(124,146,104)))
        pygame.draw.rect(ground,col,(x,y,rng.choice((3,5,9)),rng.choice((2,3))))
    path_mask,shoulder,paving=road_layers()
    ground.blit(shoulder,(0,0));ground.blit(paving,(0,0))
    # One contour paints banks and water, and is also the movement boundary.
    pygame.draw.polygon(ground,(102,128,101),layout.WATER)
    pygame.draw.lines(ground,(169,172,130),True,layout.WATER,15)
    pygame.draw.polygon(ground,WATER,layout.WATER)
    pygame.draw.lines(ground,(109,155,153),True,layout.WATER,3)
    # Low lockstone retaining courses follow the southern bank, with open
    # planting intervals instead of a continuous hard border around the lake.
    for index,(x,y) in enumerate(layout.WATER):
        if 320<x<1740 and 500<y<690 and not layout.BRIDGE.inflate(65,30).collidepoint(x,y):
            pygame.draw.rect(ground,(111,126,105),(x-11,y,23,13))
            pygame.draw.rect(ground,(181,185,152),(x-10,y-1,21,7))
            pygame.draw.line(ground,(217,207,169),(x-8,y),(x+8,y),1)
    for _ in range(1650):
        x=rng.randrange(layout.WIDTH);y=rng.randrange(280,1450)
        if layout.wet(x,y) and layout.wet(x+28,y):
            pygame.draw.rect(ground,rng.choice(((76,133,141),(81,136,141),(61,114,128))),(x,y,rng.randrange(7,28),2))
    _bridge(ground)
    dock=layout.DOCK
    pygame.draw.rect(ground,(83,77,53),dock)
    for yy in range(dock.top+3,dock.bottom,12):
        pygame.draw.rect(ground,(172,137+(yy//12%3)*5,86),(dock.x+4,yy,dock.width-8,9))
        for xx in (dock.x+8,dock.right-12):pygame.draw.rect(ground,(222,181,110),(xx,yy+4,2,2))
    # Workyards belong to particular buildings; they cannot erase road paving.
    yard=pygame.Surface(ground.get_size(),pygame.SRCALPHA)
    for x,y,w,h in ((1360,872,300,65),(310,850,260,58),(2460,350,270,70)):
        pygame.draw.ellipse(yard,(159,159,122),(x,y,w,h))
        for _ in range(90):
            xx=x+rng.randrange(w);yy=y+rng.randrange(h)
            if ((xx-x-w/2)/(w/2))**2+((yy-y-h/2)/(h/2))**2<1:
                pygame.draw.rect(yard,(180,174,132),(xx,yy,3,2))
    unpaved=pygame.Surface(ground.get_size(),pygame.SRCALPHA);unpaved.fill((255,255,255,255))
    unpaved.blit(path_mask,(0,0),special_flags=pygame.BLEND_RGBA_SUB)
    yard.blit(unpaved,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
    ground.blit(yard,(0,0))
    for x,y,w,h in ((465,1150,60,135),(1370,1160,85,145),(700,1080,105,62)):
        pygame.draw.rect(ground,(122,125,87),(x,y,w,h),border_radius=8)
        for yy in range(y+7,y+h-4,13):
            for xx in range(x+7,x+w-4,13):
                pygame.draw.rect(ground,(85,118,77),(xx,yy,8,5))
                pygame.draw.rect(ground,(155,170,110),(xx+2,yy-2,4,3))
                if (xx+yy)%5==0:pygame.draw.rect(ground,(207,181,102),(xx+3,yy-3,3,3))
    cache=scene_depth.Cache(ground.get_size());lights=[]
    for key,((x,y),width,height,kind) in layout.BUILDINGS.items():
        bounds=(x-width//2-25,y-height-180,width+50,height+220)
        cache.capture(bounds,y,lambda s,key=key:_building(s,key))
        building=cache.props[-1]
        lights.append(scene_depth.Prop(y,building.rect.copy(),building_light(building.image,building.rect,key)))
    cache.capture((110,280,200,345),600,_lock)
    # Lift-bridge rails share character ground depth. Its centre stays walkable.
    for xx in (layout.BRIDGE.left+3,layout.BRIDGE.right-3):
        for yy in range(layout.BRIDGE.top+10,layout.BRIDGE.bottom,48):
            cache.capture((xx-9,yy-55,18,60),yy,lambda s,x=xx,y=yy:_bridge_rail(s,x,y))
    for xx in (dock.x-1,dock.right+1):
        for yy in (dock.y+30,dock.y+140,dock.bottom):
            cache.capture((xx-9,yy-22,18,27),yy,lambda s,x=xx,y=yy:(pygame.draw.rect(s,(92,77,51),(x-6,y-20,12,22)),pygame.draw.ellipse(s,(206,172,106),(x-7,y-23,14,7))))
    for x,y in ((2500,410),(2540,410),(2610,385),(1555,906),(1610,897),(1168,887)):
        cache.capture((x-22,y-30,44,36),y,lambda s,x=x,y=y:_crate(s,x,y))
    # Low riverside reeds follow the actual bank; no invisible rectangular lake.
    for i,(x,y) in enumerate(layout.WATER):
        if not (10<x<layout.WIDTH-10 and 30<y<layout.HEIGHT-30):continue
        if any(r.inflate(48,30).collidepoint(x,y) for r in layout.WALKWAYS):continue
        if i%2:continue
        def reeds(s,x=x,y=y,i=i):
            rr=random.Random(i*53)
            for j in range(10):
                xx=x+rr.randrange(-17,18);h=rr.randrange(12,32)
                pygame.draw.line(s,(95,126,85),(xx,y+4),(xx-3,y-h),2)
                if j%3==0:pygame.draw.rect(s,(133,111,69),(xx-5,y-h-5,4,10))
        cache.capture((x-24,y-39,48,50),y,reeds)
    # Reserve paths, buildings, interaction space and shore before planting.
    for x,y in ((140,180),(390,180),(1160,110),(1530,110),(1910,170),
                (160,960),(250,1080),(400,1250),(340,1460),(820,1490),
                (1460,1470),(1700,1360),(1760,1090),(1640,590),(1880,270),
                (2640,1550),(2250,1530),(1150,1510),(80,1400)):
        if layout.distance_to_path((x,y))>85 and not layout.wet(x,y):
            cache.capture((x-70,y-155,140,180),y,lambda s,x=x,y=y:_tree(s,x,y,x+y))
    # Benches, planting and rope bollards provide inhabited forecourts.
    for x,y in ((746,1025),(1330,1080),(540,1345),(1450,1340),(1692,1140)):
        def bench(s,x=x,y=y):
            for dx in (-26,25):pygame.draw.rect(s,(73,83,65),(x+dx,y-20,5,23))
            for yy in (y-34,y-27,y-13):pygame.draw.rect(s,(172,132,77),(x-34,yy,70,6))
        cache.capture((x-38,y-38,80,44),y,bench)
    # A small orchard and grouped waterside planting give the open banks shape.
    for x,y in ((175,1240),(230,1330),(130,1450),(355,1510),
                (1565,1260),(1635,1380),(1750,1510),(2690,1430)):
        cache.capture((x-65,y-150,130,170),y,lambda s,x=x,y=y:_tree(s,x,y,x*3+y))
    def shrubs(s,x,y,seed):
        rr=random.Random(seed)
        for dx,dy in ((-23,0),(0,-5),(22,2)):
            pygame.draw.ellipse(s,(82,115,78),(x+dx-18,y+dy-24,36,27))
            pygame.draw.ellipse(s,(113,140,88),(x+dx-14,y+dy-24,27,18))
            for _ in range(5):
                xx=x+dx+rr.randrange(-11,12);yy=y+dy-rr.randrange(6,22)
                pygame.draw.rect(s,(210,188,111) if seed%2 else (189,164,152),(xx,yy,3,3))
    reserved=pygame.mask.from_surface(path_mask)
    shrub_footprint=pygame.mask.Mask((82,14),fill=True)
    for x,y in ((300,870),(585,812),(907,856),(1235,840),(1340,836),(1680,863),
                (550,1278),(773,1260),(1132,1275),(1415,1295),(2000,240),
                (2140,300),(2740,320),(1540,1170),(410,1140)):
        if reserved.overlap(shrub_footprint,(x-41,y-7)) is not None:continue
        if any(layout.wet(xx,y+7) for xx in (x-41,x,x+41)):continue
        cache.capture((x-45,y-32,90,40),y,lambda s,x=x,y=y:shrubs(s,x,y,x+y))
    # A fixed loading crane and timber stock explain the arrival boatyard.
    def crane(s):
        x,y=2720,388
        pygame.draw.rect(s,(118,109,76),(x-25,y-10,55,17))
        pygame.draw.line(s,(90,83,57),(x,y),(x,y-115),13)
        pygame.draw.line(s,(173,134,77),(x-2,y-4),(x-2,y-110),6)
        pygame.draw.line(s,(83,88,65),(x-5,y-110),(x-105,y-75),10)
        pygame.draw.line(s,(189,155,94),(x-6,y-113),(x-105,y-78),3)
        pygame.draw.line(s,(129,116,75),(x-3,y-70),(x-90,y-80),6)
        pygame.draw.line(s,(201,174,107),(x-100,y-79),(x-100,y-19),2)
        pygame.draw.arc(s,(75,84,66),(x-106,y-23,13,17),math.pi,math.tau,3)
        town_art.gear(s,(x+4,y-37),15,color=GOLD)
    cache.capture((2605,258,155,155),388,crane)
    for x,y in ((2670,380),(1600,918)):
        def timber(s,x=x,y=y):
            for index in range(4):
                yy=y-index*8
                pygame.draw.rect(s,(152,111,63),(x-33,yy-8,78,8))
                pygame.draw.line(s,(198,156,93),(x-31,yy-7),(x+43,yy-7),2)
                pygame.draw.circle(s,(209,175,111),(x-33,yy-4),4)
                pygame.draw.circle(s,(119,89,52),(x-33,yy-4),2,1)
        cache.capture((x-40,y-38,90,45),y,lambda s,x=x,y=y:timber(s,x,y))
    # Mooring rings on the retaining stone, with restrained coiled ropes.
    for x,y in ((1210,591),(1440,624),(1720,706)):
        def mooring(s,x=x,y=y):
            pygame.draw.ellipse(s,(104,114,88),(x-13,y-5,27,10))
            pygame.draw.rect(s,(72,88,76),(x-6,y-20,12,19))
            pygame.draw.ellipse(s,(146,149,110),(x-9,y-25,18,8))
            pygame.draw.ellipse(s,(195,164,98),(x+9,y-7,24,9),2)
            pygame.draw.ellipse(s,(162,135,83),(x+12,y-5,18,5),1)
        cache.capture((x-18,y-30,57,44),y,lambda s,x=x,y=y:mooring(s,x,y))
    return ground,cache.finish(),tuple(lights)


def water_motion(surface,camera,seconds,reduced_motion=False):
    ox,oy=camera
    phase=0 if reduced_motion else seconds
    for index in range(110):
        x=(index*173+73)%layout.WIDTH;y=330+(index*97)%1010
        xx=x+round(math.sin(phase*.5+index)*7)
        if layout.wet(xx,y) and layout.wet(xx+19,y) and not any(r.collidepoint(xx,y) for r in layout.WALKWAYS):
            pygame.draw.line(surface,(101,157,157),(xx-ox,y-oy),(xx+13+(index%7)-ox,y-oy),1)


def cistern(surface,x,y,repaired=False,seconds=0.):
    pygame.draw.ellipse(surface,(113,132,102),(x-55,y-4,110,24))
    pygame.draw.rect(surface,(138,143,118),(x-43,y-48,86,51))
    town_art.brickwork(surface,(x-41,y-46,82,46),((205,202,166),(189,190,155)),39,rows=14,columns=26)
    pygame.draw.ellipse(surface,(231,220,179),(x-47,y-56,94,24))
    pygame.draw.ellipse(surface,(72,126,132),(x-39,y-51,78,15))
    pygame.draw.lines(surface,COPPER,False,[(x+24,y-21),(x+24,y-89),(x+2,y-89),(x+2,y-63)],7)
    pygame.draw.lines(surface,(223,176,101),False,[(x+22,y-23),(x+22,y-87),(x+2,y-87)],2)
    town_art.gear(surface,(x+25,y-65),10,color=GOLD if repaired else (135,116,77))
    if repaired:
        pygame.draw.line(surface,(146,199,183),(x+2,y-62),(x+2,y-48),3)
        pygame.draw.ellipse(surface,(171,209,187),(x-8,y-50,20,5),1)
    else:
        pygame.draw.line(surface,(116,81,54),(x+12,y-80),(x+38,y-50),5)


def survey_plate(surface,x,y):
    pygame.draw.rect(surface,(106,108,83),(x-21,y-30,42,33))
    pygame.draw.polygon(surface,(176,133,76),[(x-32,y-54),(x+28,y-54),(x+35,y-29),(x-26,y-29)])
    pygame.draw.lines(surface,(236,208,140),False,[(x-20,y-47),(x-7,y-36),(x+4,y-45),(x+20,y-35)],2)
    for xx in (x-14,x+9):pygame.draw.circle(surface,(236,208,140),(xx,y-41),3,1)
