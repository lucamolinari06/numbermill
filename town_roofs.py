"""Pixel roof construction inside the established building silhouettes.

Courses follow roof planes in perspective. Triangular roofs retain a complete
roof surface; their material overlaps and eaves supply depth within the outline.
"""
import math
import random
import pygame


def shade(color, amount):
    return tuple(max(0,min(255,c+amount)) for c in color)


def _point(quad,u,v):
    a,b,c,d=quad
    return (round((a[0]*(1-u)+b[0]*u)*(1-v)+(d[0]*(1-u)+c[0]*u)*v),
            round((a[1]*(1-u)+b[1]*u)*(1-v)+(d[1]*(1-u)+c[1]*u)*v))


def _panel(surface,quad,u0,v0,u1,v1,color):
    pygame.draw.polygon(surface,color,[_point(quad,u0,v0),_point(quad,u1,v0),
                                     _point(quad,u1,v1),_point(quad,u0,v1)])


def _line(surface,quad,u0,v0,u1,v1,color,width=1):
    pygame.draw.line(surface,color,_point(quad,u0,v0),_point(quad,u1,v1),width)


def _cover(surface,quad,color,material,seed):
    rng=random.Random(seed)
    pygame.draw.polygon(surface,shade(color,-24),quad)
    width=max(20,math.dist(quad[2],quad[3]))
    if material in ('boards','copper'):
        count=max(3,round(width/(19 if material=='boards' else 35)))
        for i in range(count):
            u0=i/count;u1=(i+1)/count
            tone=shade(color,rng.randrange(-9,9))
            _panel(surface,quad,u0,.015,u1,1,tone)
            # Flat lower band establishes light fall-off without gradients.
            _panel(surface,quad,u0,.70,u1,1,shade(tone,-8))
            _line(surface,quad,u0,0,u0,1,shade(color,-27),2)
            _line(surface,quad,u0+.009,0,u0+.009,1,shade(color,25),1)
            if material=='boards':
                for _ in range(3):
                    u=u0+rng.uniform(.2,.85)/count;v=rng.uniform(.1,.65)
                    _line(surface,quad,u,v,u+.004,min(.96,v+.22),shade(tone,-13),1)
                for v in (.12,.87):
                    pygame.draw.circle(surface,(77,69,54),_point(quad,(u0+u1)/2,v),1)
                if i%5==2:
                    k=_point(quad,u0+.62/count,.51)
                    pygame.draw.ellipse(surface,shade(color,-21),(k[0]-2,k[1]-3,4,7),1)
            else:
                if i%3==1:
                    _panel(surface,quad,u0+.04/count,.35,u0+.20/count,.91,shade(color,12))
                for v in (.33,.72):
                    _line(surface,quad,u0,v,u1,v,shade(color,-12),1)
        return
    # Rows widen towards the eave; each tile overlaps the row below it.
    rows=6;columns=max(4,round(width/(18 if material=='clay' else 23)))
    for row in range(rows):
        v0=(row/rows)**1.25;v1=((row+1)/rows)**1.25
        for col in range(-1,columns+1):
            offset=.5 if row%2 else 0
            u0=max(0,(col+offset)/columns);u1=min(1,(col+offset+1)/columns)
            if u1<=u0:continue
            tone=shade(color,rng.choice((-8,-4,0,3,6))-(5 if row>3 else 0))
            _panel(surface,quad,u0,v0,u1,v1,tone)
            _line(surface,quad,u0,v0,u0,v1,shade(color,-23),1)
            _line(surface,quad,u0,v1,u1,v1,shade(color,-31),2)
            _line(surface,quad,u0+.007,max(v0,v1-.035),u1-.007,max(v0,v1-.035),shade(tone,24),1)
            if material=='clay':
                # Barrel-tile ridges run down the slope, with shaded channels.
                mid=(u0+u1)/2
                _line(surface,quad,mid,v0+.01,mid,v1-.04,shade(tone,25),2)
                _line(surface,quad,u1-.014,v0,u1-.014,v1,shade(tone,-17),1)
            elif material=='shingles':
                for fraction in (.3,.7):
                    u=u0+(u1-u0)*fraction
                    _line(surface,quad,u,v0+.02,u,v1-.04,shade(tone,-12),1)
            elif rng.random()<.22:
                # Occasional split edge; slate is not dressed wall masonry.
                _line(surface,quad,u1-.025,v1-.08,u1-.012,v1,shade(tone,-23),1)


def _triangular_cover(layer,points,color,material,seed):
    """A single broad roof plane with lapped courses, no diagonal wall inset."""
    left,ridge,right=points
    rng=random.Random(seed)
    texture=pygame.Surface(layer.get_size(),pygame.SRCALPHA)
    texture.fill(shade(color,-23))
    top=ridge[1];bottom=left[1];height=bottom-top
    yy=top;row=0
    while yy<bottom:
        depth=(yy-top)/height
        course=round(7+depth*7)
        tile_width=round(16+depth*13)
        offset=tile_width//2 if row%2 else 0
        for xx in range(left[0]-tile_width+offset,right[0]+tile_width,tile_width):
            tone=shade(color,rng.choice((-5,-2,0,2,4))-round(depth*7))
            # The slate's exposed toe has a little unevenness. Only its lower
            # edge casts a shadow; a complete mortar grid would read as brick.
            toe=yy+course-2
            chip=rng.choice((0,0,1,2))
            polygon=((xx,yy),(xx+tile_width-1,yy),(xx+tile_width-1,toe-chip),
                     (xx+tile_width-4,toe+1),(xx+2,toe+1),(xx,toe-1))
            pygame.draw.polygon(texture,tone,polygon)
            pygame.draw.line(texture,shade(tone,17),(xx+3,toe),(xx+tile_width-5,toe),1)
            if material=='clay':
                for dx in (tile_width//3,tile_width*2//3):
                    pygame.draw.line(texture,shade(tone,17),(xx+dx,yy+1),(xx+dx,toe-1),2)
                    pygame.draw.line(texture,shade(tone,-13),(xx+dx+3,yy+1),(xx+dx+3,toe-1),1)
            elif material=='shingles':
                pygame.draw.line(texture,shade(tone,-11),(xx+6,yy+2),(xx+7,toe-1),1)
            elif rng.random()<.23:
                pygame.draw.line(texture,shade(tone,-12),(xx+tile_width-6,toe-3),(xx+tile_width-4,toe),1)
        yy+=course;row+=1
    mask=pygame.Surface(layer.get_size(),pygame.SRCALPHA)
    pygame.draw.polygon(mask,(255,255,255),points)
    texture.blit(mask,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
    layer.blit(texture,(0,0))
    # Sloping caps follow the silhouette, with equal construction on both sides.
    pygame.draw.lines(layer,shade(color,-25),False,(left,ridge,right),4)
    pygame.draw.lines(layer,shade(color,18),False,
                      ((left[0]+2,left[1]-1),ridge,(right[0]-2,right[1]-1)),2)


def draw(surface,points,key,color):
    bounds=pygame.Rect(min(x for x,y in points)-2,min(y for x,y in points)-2,
                       max(x for x,y in points)-min(x for x,y in points)+5,
                       max(y for x,y in points)-min(y for x,y in points)+8)
    layer=pygame.Surface(bounds.size,pygame.SRCALPHA)
    local=[(x-bounds.x,y-bounds.y) for x,y in points]
    seed=sum(map(ord,key))
    if len(local)==3:
        material='shingles' if key=='farm' else 'clay' if key=='mill' else 'slate'
        _triangular_cover(layer,local,color,material,seed)
    else:
        # Shed polygons begin at their back-left; hipped roofs at front-left.
        shed=key in ('fuel_yard','sawmill')
        quad=local if shed else [local[1],local[2],local[3],local[0]]
        material=('boards' if shed else 'copper' if key in ('toolmaker','home_4')
                  else 'clay' if key in ('bakery','east_bakery','home_1','home_3')
                  else 'shingles' if key in ('market','home_2','home_5') else 'slate')
        _cover(layer,quad,color,material,seed)
        # Keep the material across the whole roof, including the sloping sides.
        # Only the narrow ridge cap is drawn over the textured surface.
        if not shed:
            a,b,c,d=quad
            pygame.draw.line(layer,shade(color,-29),a,b,6)
            pygame.draw.line(layer,shade(color,28),(a[0],a[1]-1),(b[0],b[1]-1),3)
            for xx in range(a[0]+5,b[0],12):
                pygame.draw.line(layer,shade(color,-6),(xx,a[1]-2),(xx+2,a[1]+2),1)
        else:
            pygame.draw.line(layer,shade(color,-27),quad[0],quad[1],5)
            pygame.draw.line(layer,shade(color,28),quad[0],quad[1],2)
    # A continuous fascia, under-eave shadow and small rafter ends give weight.
    bottom=max(y for x,y in local)
    left=min(x for x,y in local);right=max(x for x,y in local)
    pygame.draw.line(layer,(68,59,46),(left,bottom+3),(right,bottom+3),5)
    pygame.draw.line(layer,(162,129,82),(left,bottom),(right,bottom),3)
    for xx in range(left+12,right-4,27):
        pygame.draw.rect(layer,(111,82,55),(xx,bottom+2,4,4))
    surface.blit(layer,bounds)
