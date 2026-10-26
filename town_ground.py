"""Authored village ground; all surfaces remain walkable and save-independent.

Road outlines cover the existing resident travel lines and door approaches.
The same polygons are used by the world, minimap and ledger map. Raised
decoration still uses town's conservative street/building reservations.
"""
from functools import lru_cache
import math
import random

import pygame
from water_geometry import smooth_polygon


def _strip(stations):
    return tuple(smooth_polygon(
        [(x, top) for x, top, bottom in stations]
        + [(x, bottom) for x, top, bottom in reversed(stations)], passes=2))


# Narrow stretches open into modest forecourts. Even the narrowest sections
# cover y=290/625/970/1320 and the residents' twenty-pixel waiting offset.
ROAD_POLYGONS = (
    _strip(((88,600,704),(170,586,722),(390,588,722),(520,603,700),
            (650,586,733),(900,586,745),(1090,586,768),(1320,586,751),
            (1460,601,715),(1640,601,710),(1790,588,731),(2040,588,735),
            (2190,601,710),(2310,588,732),(2520,588,732),(2600,604,704))),
    _strip(((280,265,343),(470,258,355),(700,271,345),(910,258,357),
            (1120,260,356),(1400,265,342),(1560,259,355),(1800,270,344),
            (2140,258,355),(2430,266,344),(2520,273,335))),
    _strip(((100,945,1020),(270,935,1037),(500,947,1025),(760,946,1030),
            (1000,934,1042),(1300,933,1044),(1520,947,1027),(1710,947,1026),
            (1930,947,1025),(2110,934,1042),(2370,945,1028),(2490,953,1016))),
    _strip(((90,1300,1381),(190,1288,1390),(430,1301,1380),(700,1288,1392),
            (990,1288,1392),(1140,1295,1390),(1330,1288,1391),(1520,1300,1380),
            (1660,1295,1385),(1830,1288,1392),(2060,1300,1380),
            (2310,1288,1392),(2480,1302,1378))),
    tuple(smooth_polygon(((1084,120),(1156,120),(1156,390),(1163,520),
        (1162,770),(1155,1000),(1162,1230),(1156,1420),(1084,1420),
        (1080,1230),(1085,1000),(1078,770),(1080,520),(1084,390)),passes=2)),
    tuple(smooth_polygon(((1593,265),(1667,265),(1665,510),(1673,700),
        (1666,960),(1669,1170),(1665,1400),(1595,1400),(1590,1170),
        (1594,960),(1587,700),(1595,510)),passes=2)),
)

# These modest footpaths join existing landmarks, never cross future sites.
GARDEN_PATHS = (((880,731),(880,784),(882,870),(897,923),(900,975)),
                ((575,972),(590,940),(605,922),(699,925),(790,925),(882,900)),
                ((882,900),(950,925),(1050,920),(1120,903)))
WELL_COURT = pygame.Rect(819,829,126,75)


@lru_cache(maxsize=4)
def footpath_surface(size):
    surface = pygame.Surface(size, pygame.SRCALPHA)
    for path in GARDEN_PATHS:
        pygame.draw.lines(surface, (255,255,255), False, path, 27)
        for point in path:
            pygame.draw.circle(surface, (255,255,255), point, 13)
    return surface


@lru_cache(maxsize=4)
def garden_surface(size):
    surface = footpath_surface(size).copy()
    pygame.draw.ellipse(surface, (255,255,255), WELL_COURT)
    return surface


@lru_cache(maxsize=4)
def garden_mask(size):
    return pygame.mask.from_surface(garden_surface(size))


def clears_garden(bounds, size=(2700,1560)):
    area = pygame.Rect(bounds).inflate(4,4)
    return garden_mask(size).overlap(pygame.Mask(area.size,fill=True),area.topleft) is None


@lru_cache(maxsize=4)
def road_surface(size):
    surface = pygame.Surface(size, pygame.SRCALPHA)
    for points in ROAD_POLYGONS:
        pygame.draw.polygon(surface,(255,255,255),points)
    return surface


@lru_cache(maxsize=4)
def road_mask(size):
    return pygame.mask.from_surface(road_surface(size))


def clears_road(bounds,size=(2700,1560)):
    # Full sprite bounds already include shadows; three additional pixels keep
    # the curved paving clear without discarding the well garden's furniture.
    area=pygame.Rect(bounds).inflate(6,6)
    return road_mask(size).overlap(pygame.Mask(area.size,fill=True),area.topleft) is None


def draw_map(surface, position, color):
    for points in ROAD_POLYGONS:
        pygame.draw.polygon(surface,color,[position(x,y) for x,y in points])


def _patch(surface, center, radius, color, rng):
    x,y=center;w,h=radius
    points=[]
    for i in range(18):
        a=i*math.tau/18
        r=rng.uniform(.84,1.06)
        points.append((round(x+math.cos(a)*w*r),round(y+math.sin(a)*h*r)))
    pygame.draw.polygon(surface,color,points)


def soil(surface):
    """Large, quiet material areas relate to actual yards and garden edges."""
    rng=random.Random(603)
    for x,y,w,h in ((260,247,75,43),(2097,565,72,46),(2575,578,58,39),
                    (2304,927,76,43),(427,936,64,35)):
        _patch(surface,(x,y),(w+12,h+10),(117,137,93),rng)
        _patch(surface,(x,y),(w,h),(147,138,101),rng)
        for _ in range(95):
            xx=x+rng.randrange(-w,w);yy=y+rng.randrange(-h,h)
            if ((xx-x)/w)**2+((yy-y)/h)**2<.85:
                pygame.draw.line(surface,rng.choice(((153,141,105),(127,123,91))),
                                 (xx,yy),(xx+rng.randrange(2,7),yy),2)
    # Cultivated garden and connected gathering ground, rather than lone props.
    _patch(surface,(527,859),(112,63),(111,132,86),rng)
    _patch(surface,(527,859),(96,55),(145,128,88),rng)
    _patch(surface,(856,869),(218,61),(126,148,99),rng)
    # Tree groups and residential strips get broader areas of shade and grass.
    for x,y,w,h in ((555,463,120,53),(1430,465,100,44),(1755,855,112,45),
                    (350,1190,165,53),(610,1170,102,44),(1460,1160,106,59),
                    (1980,1160,110,48),(2500,1175,113,58)):
        _patch(surface,(x,y),(w,h),(114,143,97),rng)
        _patch(surface,(x-16,y-8),(w*.68,h*.65),(118,146,99),rng)
    # Worn earth joins real walking ground and the well court.
    # Texture is clipped to the same footprint reserved by raised decoration.
    paths = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    for path in GARDEN_PATHS:
        # Worn grass shoulders, not a dark contour around a painted ribbon.
        pygame.draw.lines(paths,(156,151,108,110),False,path,27)
        for point in path:pygame.draw.circle(paths,(156,151,108,110),point,13)
        pygame.draw.lines(paths,(165,155,112,200),False,path,19)
        for point in path:pygame.draw.circle(paths,(165,155,112,200),point,9)
    mask = garden_mask(surface.get_size())
    for _ in range(1500):
        xx, yy = rng.randrange(555,1135), rng.randrange(720,990)
        if mask.get_at((xx, yy)):
            pygame.draw.rect(paths,rng.choice(((157,150,107,120),(174,161,116,145),(149,145,102,100))), (xx,yy,2,1))
    paths.blit(footpath_surface(surface.get_size()),(0,0),special_flags=pygame.BLEND_RGBA_MULT)
    surface.blit(paths,(0,0))


def roads(surface):
    """One clipped stone surface and exterior edge; no seams at junctions."""
    size=surface.get_size();mask_surface=road_surface(size)
    outline=road_mask(size).outline(2)
    # Draw every contour, including the grass islands inside road loops.
    # The union fill below covers overlapping edges at every intersection.
    edging=pygame.Surface(size,pygame.SRCALPHA)
    for color,width in (((106,128,88),18),((142,142,103),11),((166,155,118),5)):
        for points in ROAD_POLYGONS:
            pygame.draw.lines(edging,color,True,points,width)
    # No curb/grass stripe crosses the mouths of the worn garden paths.
    edging.blit(footpath_surface(size),(0,0),special_flags=pygame.BLEND_RGBA_SUB)
    surface.blit(edging,(0,0))
    paving=pygame.Surface(size,pygame.SRCALPHA)
    paving.fill((160,152,126))
    rng=random.Random(718)
    # Smaller uneven setts, with quiet tonal variation and chipped corners.
    for y in range(0,size[1],15):
        x=-30+(15 if (y//15)%2 else 0)
        while x<size[0]:
            width=rng.randrange(23,36)
            delta=rng.choice((-5,-2,0,0,2,4,6))
            base=(180,169,140) if y<1200 else (172,162,132)
            color=tuple(c+delta for c in base)
            pygame.draw.rect(paving,color,(x+1,y+1,width-2,13),border_radius=3)
            if rng.random()<.30:
                pygame.draw.line(paving,tuple(c+9 for c in color),(x+4,y+2),(x+width-5,y+2),1)
            if rng.random()<.09:
                pygame.draw.line(paving,(153,146,120),(x+width-8,y+8),(x+width-4,y+11),1)
            x+=width
    # Dust settles in the working street; translucent patches retain the setts.
    dust=pygame.Surface(size,pygame.SRCALPHA)
    for x,y,w,h in ((350,666,200,27),(760,681,180,26),(1230,679,190,33),
                    (1910,670,170,30),(2390,671,160,31),(420,320,144,16)):
        _patch(dust,(x,y),(w,h),(183,159,111,45),rng)
    paving.blit(dust,(0,0))
    # A quieter gravel lane serves the homes. It shares the road geometry and
    # door coordinates, with setts retained at thresholds and the bridge.
    lane=pygame.Surface(size,pygame.SRCALPHA)
    pygame.draw.polygon(lane,(174,160,119),ROAD_POLYGONS[3])
    for x in range(95,2490,5):
        for _ in range(4):
            y=rng.randrange(1290,1400)
            tone=rng.choice(((184,169,126),(163,152,114),(179,164,121)))
            pygame.draw.rect(lane,tone,(x,y,rng.randrange(2,5),2))
    # Scattered embedded stones leave a calm center rather than another grid.
    for x in range(100,2480,23):
        y=1334+rng.randrange(-30,31)
        if rng.random()<.58:
            pygame.draw.rect(lane,(158,151,119),(x,y,15,8),border_radius=3)
            pygame.draw.line(lane,(196,180,137),(x+3,y+1),(x+10,y+1),1)
    # Alpha-only clipping avoids multiplying the gravel colors by the mask.
    white=pygame.Surface(size,pygame.SRCALPHA)
    pygame.draw.polygon(white,(255,255,255),ROAD_POLYGONS[3])
    lane.blit(white,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
    paving.blit(lane,(0,0))
    paving.blit(mask_surface,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
    surface.blit(paving,(0,0))
    # A little earth among the setts bridges the material change at each join.
    joins=pygame.Surface(size,pygame.SRCALPHA)
    for path in GARDEN_PATHS:
        pygame.draw.lines(joins,(165,155,112,55),False,path,23)
        for point in path:pygame.draw.circle(joins,(165,155,112,55),point,11)
    joins.blit(mask_surface,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
    surface.blit(joins,(0,0))
    # Occasional grass in the outer shoulder, never over the walking surface.
    mask=pygame.mask.from_surface(mask_surface)
    for i in range(0,len(outline),9):
        x,y=outline[i]
        for dx,dy in ((-8,0),(8,0),(0,-8),(0,8)):
            xx,yy=x+dx,y+dy
            if (2<xx<size[0]-3 and 6<yy<size[1]-3 and not mask.get_at((xx,yy))
                    and not garden_mask(size).get_at((xx,yy))):
                if rng.random()<.24:
                    pygame.draw.line(surface,(102,130,82),(xx,yy),(xx+2,yy-4),2)


def frontage(surface, locations):
    # Short dressed-stone thresholds tie foundations into the worn street.
    for key,(x,y) in locations.items():
        width=86 if key.startswith('home_') else 106
        pygame.draw.rect(surface,(132,132,105),(x-width//2,y-16,width,22),border_radius=4)
        for xx in range(x-width//2+2,x+width//2-2,21):
            pygame.draw.rect(surface,(185,177,145),(xx,y-14,19,13),border_radius=1)


def vacant_plot(surface,x,y,width,height):
    """Reserved land stays open; its grass no longer looks like a UI panel."""
    rng=random.Random(x+y)
    bounds=pygame.Rect(x-width//2,y-height-25,width,height)
    old_clip=surface.get_clip();surface.set_clip(old_clip.clip(bounds))
    for _ in range(11):
        center=(rng.randrange(bounds.left,bounds.right),rng.randrange(bounds.top,bounds.bottom))
        _patch(surface,center,(rng.randrange(22,55),rng.randrange(11,25)),(116,145,98),rng)
    for _ in range(48):
        xx=rng.randrange(bounds.left,bounds.right);yy=rng.randrange(bounds.top,bounds.bottom)
        pygame.draw.line(surface,(136,157,106),(xx,yy),(xx+2,yy-3),1)
    surface.set_clip(old_clip)


def river_margin(surface,width,height):
    """Ground-only bank variation follows the unchanged water boundary."""
    import town_water
    rng=random.Random(581)
    for x in (110,260,480,720,910,1360,1590,1830,2070,2370,2580):
        y=round(town_water.north_bank(x,width,height))
        _patch(surface,(x,y-14),(rng.randrange(60,105),24),(104,133,89),rng)
        for _ in range(18):
            xx=x+rng.randrange(-65,65)
            yy=round(town_water.north_bank(xx,width,height))-rng.randrange(10,34)
            pygame.draw.lines(surface,(86,122,78),False,((xx-3,yy-4),(xx,yy),(xx+2,yy-6)),1)
    # The existing south bridge gets a clear, splayed landing on dry ground.
    pygame.draw.polygon(surface,(145,141,105),((1082,1390),(1156,1390),(1180,1460),(1062,1460)))
    pygame.draw.polygon(surface,(174,162,121),((1089,1392),(1149,1392),(1170,1460),(1072,1460)))
    for yy in range(1400,1460,15):
        for xx in range(1091-(yy-1400)//4,1152+(yy-1400)//4,24):
            pygame.draw.rect(surface,(187,175,133),(xx,yy,21,11),border_radius=2)
