"""Hand-drawn Copperside field scenery, cached independently of gameplay."""
import random
import math
import pygame
import scenery
import scene_depth
import mosswater
import expedition_scenery
from ui_theme import INK, COPPER, GOLD, TEAL

WIDTH, HEIGHT = mosswater.WIDTH, mosswater.HEIGHT
ENTRY_PATH = ((60,690),(240,680),(395,585),(610,505),(850,555),
              (1080,500),(1230,500),(1450,420),(1730,420),(1875,600))
ROAD_LAYERS = ((106,(145,151,111)),(82,(181,165,122)),(54,(191,176,132)))
PIPE_ROUTES = (
    ((799,720),(1000,720),(1000,620),(1037,620),(1037,500)),
    ((1123,478),(1154,478),(1154,583),(1310,583),(1310,600),
     (1585,600),(1585,440),(1687,440)),
    ((1218,583),(1218,562)),
)


def rounded_route(points):
    """Quadratic bends retain endpoints and stay within each corner's triangle."""
    result=[points[0]]
    for a,b,c in zip(points,points[1:],points[2:]):
        incoming=math.dist(a,b);outgoing=math.dist(b,c)
        radius=min(70,incoming*.3,outgoing*.3)
        start=(b[0]+(a[0]-b[0])*radius/incoming,b[1]+(a[1]-b[1])*radius/incoming)
        end=(b[0]+(c[0]-b[0])*radius/outgoing,b[1]+(c[1]-b[1])*radius/outgoing)
        result.append(start)
        for i in range(1,13):
            t=i/12;u=1-t
            result.append((u*u*start[0]+2*u*t*b[0]+t*t*end[0],
                           u*u*start[1]+2*u*t*b[1]+t*t*end[1]))
    result.append(points[-1])
    return tuple((round(x),round(y)) for x,y in result)


ROAD_ROUTES=tuple(rounded_route(route) for route in (ENTRY_PATH,*mosswater.PATHS))


def round_stroke(s,color,route,width):
    # A polygon per segment gives diagonal sections the same physical width.
    # Pygame's thick lines otherwise vary their apparent width with angle.
    radius=width/2
    for a,b in zip(route,route[1:]):
        length=math.dist(a,b)
        if not length:continue
        nx,ny=-(b[1]-a[1])*radius/length,(b[0]-a[0])*radius/length
        pygame.draw.polygon(s,color,[(a[0]+nx,a[1]+ny),(b[0]+nx,b[1]+ny),
                                     (b[0]-nx,b[1]-ny),(a[0]-nx,a[1]-ny)])
    for point in route:pygame.draw.circle(s,color,point,round(radius))


def draw_roads(s):
    # Paint the whole network one layer at a time: no branch borders across forks.
    for width,color in ROAD_LAYERS:
        for route in ROAD_ROUTES:round_stroke(s,color,route,width)


def foliage_exclusion():
    """Full sprite clearance keeps crowns, trunks and shadows off roads/water."""
    surface=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
    for route in ROAD_ROUTES:round_stroke(surface,(255,255,255),route,114)
    for polygon in mosswater.WATER_POLYGONS:
        pygame.draw.polygon(surface,'white',polygon)
        pygame.draw.lines(surface,'white',True,polygon,32)
    for bounds in ((338,545,67,76),(687,633,128,136),(1028,443,105,100),
                   (1618,277,251,210),(2998,1213,105,100),
                   (mosswater.POINTS['artifact'][0]-112,1277,251,210)):
        pygame.draw.rect(surface,'white',pygame.Rect(bounds).inflate(24,24))
    for route in PIPE_ROUTES:round_stroke(surface,'white',route,22)
    return pygame.mask.from_surface(surface)


def plant_groves(rng,tree,groves,outside=False):
    """Loose woodland on either side of the walkable-area boundary."""
    for cx,cy,rx,ry,count in groves:
        for _ in range(count):
            angle=rng.random()*math.tau
            distance=math.sqrt(rng.random())
            x=round(cx+math.cos(angle)*rx*distance)
            y=round(cy+math.sin(angle)*ry*distance)
            if mosswater.blocked(x,y)!=outside:continue
            tree(x,y,rng.choice(('pine','birch','tree')) if y<1000 else
                 rng.choice(('birch','tree','tree')))


WESTERN_GROVES = (
    (310,365,185,115,110),(530,730,190,105,105),(770,345,195,115,110),
    (975,700,180,100,90),(1400,325,170,90,75),
    (1490,690,190,125,110),(1760,690,150,115,85),
)
SURVEY_GROVES = (
    (2080,525,195,135,95),(2040,1160,220,245,135),
    (2370,970,180,140,95),(2710,750,220,170,105),
    (2820,535,220,150,95),(2630,1500,175,130,95),
    (3010,815,160,220,105),(3470,450,245,200,105),
    (3820,660,200,220,100),(3490,1170,210,185,85),
    (3940,1220,160,160,65),(3610,1620,220,125,65),
)
WILDERNESS_GROVES = (
    # The western trail has a large visible slope beyond its southern edge.
    (260,970,280,165,230),(770,995,335,185,260),
    (1280,1010,325,190,260),(1740,1050,220,220,210),
    (320,1440,350,290,180),(940,1450,390,300,190),
    (1540,1450,330,300,180),
    (320,1810,310,80,105),(920,1810,400,80,130),
    (1530,1810,330,80,105),
    # Woodland continues north of the western path and the survey basin.
    (290,100,250,100,145),(790,100,310,100,150),
    (1340,100,230,105,125),(1730,100,190,110,105),
    (2200,95,260,105,115),(2750,90,300,105,130),
    (3490,90,300,105,115),(3970,95,200,105,110),
    # A shorter backdrop skirts the far side of the expanded map.
    (2200,1800,250,70,85),(2800,1800,300,70,95),
    (3500,1800,290,70,90),(3980,1800,180,70,75),
)


def steam_jet(surface,x,y,seconds,seed,span=30):
    """Animated pressurized steam; time comes from the paused field clock."""
    pygame.draw.line(surface,COPPER,(x-4,y+2),(x+span+4,y+2),5)
    pygame.draw.line(surface,GOLD,(x,y),(x+span,y),3)
    cloud=pygame.Surface((100,112),pygame.SRCALPHA)
    for i in range(6):
        age=(seconds*.85+i/6+seed*.137)%1
        rise=age*78
        px=30+(i%3)*8+math.sin(age*3+seed)*age*13
        py=100-rise
        radius=3+int(age*9)
        alpha=round(165*(1-age))
        pygame.draw.ellipse(cloud,(224,230,210,alpha),(int(px-radius),int(py-radius),radius*2+5,radius*2))
        if age<.65:
            pygame.draw.arc(cloud,(249,239,203,alpha),(int(px-radius),int(py-radius),radius*2,radius*2),.4,2.7,1)
    surface.blit(cloud,(int(x-26),int(y-100)))


def pipe_joint(s,x,y,vertical=False):
    rect=pygame.Rect(x-8,y-5,16,10) if vertical else pygame.Rect(x-5,y-8,10,16)
    pygame.draw.rect(s,(69,73,59),rect,border_radius=2)
    pygame.draw.rect(s,(180,143,86),rect.inflate(-2,-2),border_radius=2)
    if vertical:
        for dx in (-5,5):pygame.draw.circle(s,INK,(x+dx,y),1)
    else:
        for dy in (-5,5):pygame.draw.circle(s,INK,(x,y+dy),1)


def machine(surface, x, y, scale=1):
    """The anonymous maker's repeated three-ring brass signature."""
    pygame.draw.ellipse(surface, (82, 105, 77), (x-48, y+22, 96, 28))
    pygame.draw.rect(surface, (99, 103, 86), (x-43, y-38, 86, 70), border_radius=7)
    pygame.draw.rect(surface, (153, 155, 123), (x-39, y-40, 78, 63), border_radius=6)
    pygame.draw.rect(surface, COPPER, (x-31, y-30, 62, 42), border_radius=5)
    for dx in (-19, 0, 19):
        pygame.draw.circle(surface, GOLD, (x+dx,y-9), 9, 3)
        pygame.draw.circle(surface, INK, (x+dx,y-9), 3)
    for dx in (-33,33):
        for dy in (-34,17):
            pygame.draw.circle(surface, INK, (x+dx,y+dy), 2)
    pygame.draw.line(surface, (79, 124, 89), (x-42,y+10), (x-19,y-37), 4)
    for i in range(5):
        pygame.draw.ellipse(surface, (104,146,94), (x-47+i*5,y+3-i*10,12,6))


def gear(surface, x, y, radius, teeth=12):
    points=[]
    for i in range(teeth*4):
        angle=i*math.tau/(teeth*4)
        r=radius if i%4 in (1,2) else radius-4
        points.append((x+math.cos(angle)*r,y+math.sin(angle)*r))
    pygame.draw.polygon(surface,(84,71,51),points)
    pygame.draw.circle(surface,GOLD,(x,y),radius-4)
    pygame.draw.circle(surface,(113,93,64),(x,y),radius-8,2)
    pygame.draw.circle(surface,INK,(x,y),3)


def artifact_cradle(s,x,y):
    """A precision mechanism sheltered in an old, moss-covered service alcove."""
    pygame.draw.ellipse(s,(97,116,83),(x-101,y-9,202,72))
    for row in range(3):
        for col in range(6):
            xx=x-91+col*31;yy=y+row*17-12
            pygame.draw.rect(s,(148,149,118),(xx,yy,29,15),border_radius=2)
            pygame.draw.line(s,(177,173,136),(xx+2,yy+2),(xx+26,yy+2),1)
    # Broken pillars frame the mechanism without hiding the approach.
    for side in (-1,1):
        for i in range(4 if side<0 else 3):
            yy=y-27-i*24;xx=x+side*78-17
            pygame.draw.rect(s,(103,115,96),(xx,yy,34,23),border_radius=3)
            pygame.draw.rect(s,(156,158,126),(xx+2,yy+2,28,17),border_radius=2)
            pygame.draw.line(s,(189,181,145),(xx+4,yy+3),(xx+25,yy+3),2)
            if i%2==0:pygame.draw.line(s,(83,113,75),(xx,yy+20),(xx+23,yy+20),4)
    pygame.draw.polygon(s,(139,145,115),[(x-94,y-102),(x-61,y-130),(x-30,y-137),(x-27,y-113),(x-66,y-93)])
    pygame.draw.line(s,(190,183,146),(x-83,y-107),(x-36,y-128),3)
    machine(s,x,y)
    pygame.draw.rect(s,(56,75,69),(x-29,y-30,59,43),border_radius=3)
    gear(s,x-12,y-10,17)
    gear(s,x+15,y-20,13,10)
    pygame.draw.line(s,(206,196,146),(x+21,y-3),(x+21,y+11),3)
    for dx in (-18,0,18):pygame.draw.circle(s,GOLD,(x+dx,y-47),4,1)
    for dx,dy in ((-102,30),(90,28),(109,19)):
        pygame.draw.polygon(s,(130,141,111),[(x+dx,y+dy),(x+dx+8,y+dy-9),(x+dx+20,y+dy-7),(x+dx+24,y+dy+5)])


def old_boiler(s,x,y):
    pygame.draw.ellipse(s,(80,101,76),(x-57,y+18,114,27))
    for dx in (-32,28):pygame.draw.rect(s,(78,78,65),(x+dx,y+5,9,25),border_radius=2)
    pygame.draw.rect(s,(106,93,66),(x-49,y-47,98,63),border_radius=18)
    pygame.draw.rect(s,(157,122,76),(x-45,y-44,90,49),border_radius=17)
    for xx in (x-30,x+28):
        pygame.draw.line(s,(78,79,65),(xx,y-43),(xx,y+12),6)
        for yy in (y-32,y-13,y+5):pygame.draw.circle(s,GOLD,(xx,yy),2)
    pygame.draw.rect(s,(76,85,72),(x+11,y-74,16,30),border_radius=3)
    pygame.draw.polygon(s,(120,108,78),[(x+10,y-75),(x+14,y-82),(x+20,y-77),(x+27,y-83),(x+29,y-75)])
    pygame.draw.circle(s,(220,207,156),(x-5,y-22),12)
    pygame.draw.circle(s,(82,78,58),(x-5,y-22),12,3)
    pygame.draw.line(s,INK,(x-5,y-22),(x-12,y-28),2)
    pygame.draw.line(s,(78,116,76),(x-48,y-3),(x-22,y+4),5)


def beacon(s,x,y):
    pygame.draw.ellipse(s,(87,111,78),(x-19,y+1,38,16))
    pygame.draw.rect(s,(143,145,111),(x-15,y-9,30,19),border_radius=4)
    pygame.draw.line(s,COPPER,(x,y-6),(x,y-40),4)
    pygame.draw.circle(s,GOLD,(x,y-40),10,2)
    pygame.draw.line(s,TEAL,(x-13,y-25),(x+13,y-25),3)
    for dx in (-9,0,9):pygame.draw.circle(s,GOLD,(x+dx,y-4),2)


def expanded_ground(s,rng):
    """Lay down meadow and water before any roads or raised props."""
    expedition_scenery.field_ground(s)
    for index,polygon in enumerate(mosswater.POND_POLYGONS):
        expedition_scenery.water(s,polygon,904+index)
    for index,polygon in enumerate(mosswater.RIVER_POLYGONS):
        expedition_scenery.water(s,polygon,908+index,river=True,bridge_y=(500,1270)[index])
    expedition_scenery.forest_floor(s,foliage_exclusion())


def expanded_woods(s,cache,rng,tree,exclusion):
    """The survey forks have distinct woodland, wetland and archive silhouettes."""
    points=list(mosswater.POINTS.values())+[b['position'] for b in mosswater.BEACONS]
    flower_area=pygame.mask.Mask((24,28),fill=True)
    def clear_path(x,y):
        return (exclusion.overlap(flower_area,(x-12,y-22)) is None and
                all(math.hypot(x-a,y-b)>110 for a,b in points))
    for _ in range(900):
        x,y=rng.randrange(1940,4130),rng.randrange(230,1750)
        if mosswater.blocked(x,y) or 3100<x<3300:continue
        if not clear_path(x,y):continue
        if rng.random()<.22:
            tree(x,y,rng.choice(('pine','birch','tree')) if y<1050 else rng.choice(('birch','tree')))
        else:
            for dx in (-5,0,7):
                pygame.draw.line(s,(75,118,79),(x+dx,y),(x+dx-2,y-7-abs(dx)),2)
                if rng.random()<.45:pygame.draw.circle(s,rng.choice(((216,184,102),(198,163,169),(186,202,159))),(x+dx-2,y-9-abs(dx)),2)
    plant_groves(rng,tree,SURVEY_GROVES)
    for x in range(1940,4180,52):
        for y in (190+rng.randrange(-18,18),1790+rng.randrange(-10,18)):
            if not 3090<x<3310:tree(x,y,rng.choice(('pine','birch')))
    for y in range(900,1790,55):tree(1880+rng.randrange(-15,15),y,'pine')
    for y in range(250,1780,55):tree(4170,y,'pine')
    # Abandoned apparatus marks the maker's presence without naming them.
    for index,(x,y) in enumerate(((2160,470),(2670,530),(2290,1330),(2740,1680),(3500,1490),(3950,1220))):
        def ruin(target,x=x,y=y,index=index):
            expedition_scenery.ruin(target,x,y,index)
            gear(target,x+24,y+5,19)
        cache.capture((x-42,y-45,94,77),y+18,ruin)
    # The console feeds a supported manifold beneath the eastern bridge.
    route=((3093,1260),(3115,1260),(3115,1360),(3280,1360),(3280,1320))
    for width,color in ((9,(73,90,75)),(6,(127,108,73)),(2,(190,145,80))):
        pygame.draw.lines(s,color,False,route,width)
    for xx in (3152,3260):
        pygame.draw.line(s,(81,85,65),(xx,1344),(xx,1366),5)
        pipe_joint(s,xx,1360)
    pipe_joint(s,3280,1340,True)
    # Return leg enters the bridge's rail; no dangling pipe endpoint.
    pygame.draw.line(s,(165,132,80),(3280,1320),(3260,1320),6)
    def console(target):
        machine(target,3050,1260);pipe_joint(target,3093,1260)
    cache.capture((2998,1213,105,100),1292,console)
    ax,ay=mosswater.POINTS['artifact']
    cache.capture((ax-112,ay-143,251,210),ay+32,lambda target:artifact_cradle(target,ax,ay))


def build_scene():
    cache = scene_depth.Cache((WIDTH, HEIGHT))
    exclusion=foliage_exclusion()
    tree_area=pygame.mask.Mask((104,134),fill=True)
    tree_cells={}
    landmark_positions=tuple(mosswater.POINTS.values())+tuple(b['position'] for b in mosswater.BEACONS)
    def tree(x,y,kind):
        bounds=pygame.Rect(x-50,y-108,104,134)
        if exclusion.overlap(tree_area,bounds.topleft) is not None:return False
        if any((x-px)**2+(y-py)**2<110**2 for px,py in landmark_positions):return False
        cell=(x//48,y//48)
        if any((x-px)**2+(y-py)**2<48**2
               for nx in range(cell[0]-1,cell[0]+2)
               for ny in range(cell[1]-1,cell[1]+2)
               for px,py in tree_cells.get((nx,ny),())):return False
        cache.capture(bounds,y+16,lambda target:scenery.tree(target,x,y,kind))
        tree_cells.setdefault(cell,[]).append((x,y))
        return True
    s = pygame.Surface((WIDTH, HEIGHT)); s.fill((121,151,103))
    scenery.grass(s,WIDTH,HEIGHT)
    rng=random.Random(477)
    expanded_ground(s,random.Random(904))
    # The existing bridge spans the shared meandering water contour.
    pygame.draw.rect(s,(159,143,106),(1175,423,115,157))
    for y in range(427,579,13):
        pygame.draw.line(s,(95,89,69),(1179,y),(1285,y),2)
        pygame.draw.line(s,(190,168,117),(1182,y+3),(1282,y+3),1)
    draw_roads(s)
    for xx in range(3143,3273,13):
        pygame.draw.rect(s,(133,111,77),(xx,1194,12,151))
        pygame.draw.line(s,(185,163,113),(xx+2,1197),(xx+2,1342),2)
    for _ in range(1600):
        x,y=rng.randrange(70,1990),rng.randrange(210,850)
        if s.get_at((x,y))[:3] in ((181,165,122),(191,176,132)):
            pygame.draw.line(s,rng.choice(((166,152,112),(204,186,139))), (x,y),(x+3,y),1)
    # Stone sleepers carry the bridge over the water; the brass defense sits
    # on top in the live scene, so a powered crossing is immediately visible.
    for xx in range(1180,1285,13):
        pygame.draw.rect(s,(133,111,77),(xx,437,12,126))
        pygame.draw.line(s,(185,163,113),(xx+2,440),(xx+2,560),2)
    for yy in (436,563):pygame.draw.line(s,(90,80,58),(1177,yy),(1288,yy),5)
    # Woodland borders, wildflowers and fern banks; no props obscure the terminals.
    for x in range(10,2050,58):
        for y in (175+rng.randrange(-45,40),885+rng.randrange(-30,65)):
            tree(x,y,rng.choice(('pine','birch','tree')))
    for _ in range(130):
        x,y=rng.randrange(70,1990),rng.randrange(255,805)
        if 1150<x<1320 or any((x-a)**2+(y-b)**2<125**2 for a,b in ((370,600),(1080,490),(1730,420))): continue
        # Keep tree canopies off the exposed pipe runs and their valves.
        if any(pygame.Rect(min(a[0],b[0])-65,min(a[1],b[1])-30,
                           abs(a[0]-b[0])+130,abs(a[1]-b[1])+145).collidepoint(x,y)
               for route in PIPE_ROUTES for a,b in zip(route,route[1:])):continue
        if s.get_at((x,y))[:3] in ((181,165,122),(191,176,132)): continue
        if rng.random()<.24:
            tree(x,y,rng.choice(('pine','birch','tree')))
        else:
            for dx,dy in ((0,0),(8,-4),(-6,-2)):
                pygame.draw.line(s,(74,116,74),(x+dx,y),(x+dx,y+dy-8),2)
                pygame.draw.circle(s,rng.choice(((223,191,99),(209,157,150),(189,199,166))),(x+dx,y+dy-9),3)
    plant_groves(rng,tree,WESTERN_GROVES)
    # One readable steam circuit: boiler -> interlock -> bridge manifold ->
    # artifact cradle. The crossing pipe is supported below the walking deck.
    for x in (1186,1282):
        pygame.draw.line(s,(71,78,65),(x,564),(x,592),5)
        pygame.draw.line(s,(135,131,94),(x-7,591),(x+7,591),4)
    for offset,color in ((9,(73,90,75)),(6,(127,108,73)),(2,(190,145,80))):
        for route in PIPE_ROUTES:
            pygame.draw.lines(s,color,False,route,offset)
            for point in route[1:-1]:pygame.draw.circle(s,color,point,max(1,offset//2))
    for x,y,vertical in ((900,720,False),(1000,650,True),(1154,545,True),
                         (1186,583,False),(1282,583,False),(1435,600,False),
                         (1585,520,True),(1640,440,False),(1218,575,True)):
        pipe_joint(s,x,y,vertical)
    for x,y in ((1000,675),(1500,600)):
        pygame.draw.circle(s,COPPER,(x,y),14,4)
        pygame.draw.line(s,GOLD,(x-11,y),(x+11,y),3)
        pygame.draw.line(s,GOLD,(x,y-11),(x,y+11),3)
    def wall(target,x,y):
        for dx in range(-35,45,22):
            pygame.draw.rect(target,(116,125,104),(x+dx,y,21,35),border_radius=3)
            pygame.draw.line(target,(168,169,134),(x+dx+2,y+3),(x+dx+18,y+3),2)
    for x,y in ((670,720),(950,280),(1510,690),(1820,320)):
        cache.capture((x-38,y-2,95,40),y+35,lambda target,x=x,y=y:wall(target,x,y))
    def boiler(target):
        old_boiler(target,750,720)
        pipe_joint(target,799,720)
    def interlock(target):
        machine(target,1080,490)
        pipe_joint(target,1037,500);pipe_joint(target,1123,478)
    def artifact(target):
        artifact_cradle(target,1730,420)
        # Compass dial and aerial distinguish the survey station from the archive.
        pygame.draw.rect(target,(56,75,69),(1701,390,59,43),border_radius=3)
        pygame.draw.circle(target,GOLD,(1730,410),16,2)
        pygame.draw.line(target,(213,205,162),(1718,410),(1742,410),2)
        pygame.draw.line(target,(213,205,162),(1730,398),(1730,422),2)
        pygame.draw.line(target,COPPER,(1755,391),(1767,365),3)
        pygame.draw.circle(target,GOLD,(1767,365),7,2)
        pipe_joint(target,1687,440)
    cache.capture((687,633,128,136),750,boiler)
    cache.capture((1028,443,105,100),522,interlock)
    cache.capture((1618,277,251,210),452,artifact)
    def receiver(target):
        # Receiver discarded on a weathered stone plinth.
        pygame.draw.rect(target,(123,134,108),(342,590,58,27),border_radius=6)
        pygame.draw.rect(target,COPPER,(355,567,30,25),border_radius=4)
        pygame.draw.circle(target,GOLD,(370,577),8,2)
        pygame.draw.line(target,INK,(370,568),(382,550),2)
        for dx in (-9,0,9): pygame.draw.line(target,TEAL,(366+dx,559),(376+dx,551),2)
    cache.capture((338,545,67,76),617,receiver)
    expanded_woods(s,cache,rng,tree,exclusion)
    plant_groves(random.Random(917),tree,WILDERNESS_GROVES,outside=True)
    return s,cache.finish()


def build():
    """Flattened preview; live scenes keep scenery separate for occlusion."""
    surface,props=build_scene()
    scene_depth.draw(surface,(0,0),props)
    return surface

