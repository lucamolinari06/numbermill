"""Copperside's natural river shoreline shared by artwork and movement."""
from functools import lru_cache
import math
import random
import pygame
from water_geometry import contains, smooth_polygon


@lru_cache(maxsize=4)
def polygon(width, height):
    # Both banks continue off the map; the river has no rounded rectangular ends.
    top=[];bottom=[]
    for x in range(-180,width+361,150):
        bend=math.sin(x*.006)*11+math.sin(x*.017+.8)*5
        if abs(x-1120)<200:bend*=abs(x-1120)/200
        top.append((x,height-90+bend))
        bottom.append((x,height+10+math.sin(x*.005+2)*13))
    return tuple(smooth_polygon(top+list(reversed(bottom)),passes=2))


def on_bridge(x,y,height):
    return 1060 <= x <= 1187 and height-102 <= y <= height-9


def blocked(x,y,width,height):
    return contains((x,y),polygon(width,height)) and not on_bridge(x,y,height)


def north_bank(x,width,height):
    """Find the rendered shoreline from the polygon, not a separate wave."""
    hits=[];points=polygon(width,height)
    for a,b in zip(points,points[1:]+points[:1]):
        if min(a[0],b[0]) <= x <= max(a[0],b[0]) and abs(b[0]-a[0])>1e-9:
            hits.append(a[1]+(b[1]-a[1])*(x-a[0])/(b[0]-a[0]))
    return min(hits) if hits else height-90


def draw(surface,width,height):
    points=polygon(width,height)
    pygame.draw.polygon(surface,(88,116,88),points)
    pygame.draw.lines(surface,(93,119,88),True,points,16)
    pygame.draw.lines(surface,(151,150,110),True,points,7)
    pygame.draw.polygon(surface,(62,116,128),points)
    # The deeper channel follows the meander while shallow edges remain visible.
    inner=[]
    for x in range(-180,width+361,150):
        inner.append((x,north_bank(x,width,height)+17))
    inner.extend(((width+360,height+80),(-180,height+80)))
    pygame.draw.polygon(surface,(54,107,121),inner)
    pygame.draw.lines(surface,(102,157,153),False,[(x,north_bank(x,width,height)+3) for x in range(-30,width+31,20)],2)


def bank_details(surface,width,height):
    rng=random.Random(89)
    for x in range(34,width-30,26):
        if 1020<x<1220:continue
        y=round(north_bank(x,width,height))-3+rng.randrange(-3,3)
        if rng.random()<.65:
            pygame.draw.ellipse(surface,(80,104,83),(x,y,18,8))
            pygame.draw.polygon(surface,(159,161,126),[(x+2,y+3),(x+5,y-1),(x+13,y),(x+17,y+4),(x+10,y+6)])
            pygame.draw.line(surface,(192,186,143),(x+5,y),(x+12,y+1),1)
        if rng.random()<.45:
            for dx in (0,5,9):
                pygame.draw.line(surface,(70,107,72),(x+dx,y+1),(x+dx-2,y-13-dx//2),2)
                pygame.draw.line(surface,(124,85,51),(x+dx-2,y-18-dx//2),(x+dx-2,y-12-dx//2),3)
    for i in range(100):
        x=rng.randrange(30,width-30);y=round(north_bank(x,width,height))+rng.randrange(9,66)
        if on_bridge(x,y,height):continue
        pygame.draw.line(surface,(80,140,147),(x,y),(x+rng.randrange(5,18),y),1)
        if i%12==0:
            pygame.draw.ellipse(surface,(86,134,93),(x,y,12,5))
    for x in range(1064,1185,15):
        for y in (height-87,height-29):pygame.draw.circle(surface,(76,65,51),(x,y),1)
