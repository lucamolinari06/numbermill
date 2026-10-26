"""Authored Copperside architecture and small, simulation-aware visual effects.

Building art stays inside the established collision/cache envelope. Animation is
driven by the town's paused visual clock; it never mutates economic state.
"""
import math
import random
import pygame
import town_roofs
import town_ground

INK = (43, 55, 51)
TIMBER = (95, 69, 48)
WOOD = (153, 108, 65)
EDGE = (211, 168, 102)
GLASS = (66, 114, 120)
CREAM = (241, 223, 181)


def rect(s, color, bounds, radius=0, border=0):
    pygame.draw.rect(s, color, bounds, border, border_radius=radius)


def window(s, x, y, width=34, height=38, *, arched=False, shutters=False):
    rect(s, TIMBER, (x-4, y-4, width+8, height+9), 11 if arched else 2)
    rect(s, (184, 155, 106), (x-2, y-2, width+4, height+4), 9 if arched else 1)
    rect(s, GLASS, (x, y, width, height), 8 if arched else 0)
    rect(s, (87, 139, 139), (x+2, y+height//2, width-4, height//2-2))
    pygame.draw.line(s, (175, 205, 186), (x+4, y+5), (x+width-7, y+5), 2)
    pygame.draw.line(s, (132, 175, 164), (x+4, y+8), (x+4, y+height//2-3), 2)
    pygame.draw.line(s, CREAM, (x+width//2, y+1), (x+width//2, y+height-1), 3)
    pygame.draw.line(s, CREAM, (x+1, y+height//2), (x+width-1, y+height//2), 3)
    rect(s, (195, 168, 118), (x-6, y+height+3, width+12, 5), 1)
    if shutters:
        for xx in (x-16, x+width+6):
            rect(s, (75, 105, 94), (xx, y+1, 10, height-1), 1)
            for yy in range(y+5, y+height-2, 7):
                pygame.draw.line(s, (111, 137, 112), (xx+2, yy), (xx+7, yy), 1)


def facade_windows(point, key):
    """Shared glazing positions for the architecture and cached evening light."""
    x, y = point
    home = key.startswith('home_')
    width = 180 if home else 255
    left = x-width//2
    windows = []
    if home:
        windows.extend(((left+15, y-104, 30, 34, False, True),
                        (left+width-45, y-104, 30, 34, False, True)))
    elif key not in ('mill', 'fuel_yard', 'foundry'):
        windows.append((left+22, y-104, 34, 34, key in ('bakery', 'market'), False))
    if not home and key not in ('bakery', 'foundry', 'sawmill', 'fuel_yard'):
        windows.append((left+width-58, y-104, 34, 34, key == 'market', False))
    return windows


def window_light(image, bounds, point, key):
    """Cache only visible glass pixels, retaining mullions, shutters and awnings."""
    light = pygame.Surface(image.get_size(), pygame.SRCALPHA)
    colors = {GLASS: (239, 185, 99, 240), (87, 139, 139): (220, 151, 73, 225),
              (175, 205, 186): (255, 219, 146, 240), (132, 175, 164): (249, 199, 117, 240)}
    glazing = facade_windows(point, key)
    if key.startswith('home_') or key == 'parts_shop':
        glazing.append((point[0]-40, point[1]-188, 20, 21, False, False))
    if key in ('workshop', 'grace_shop'):
        gx = point[0]+12 if key == 'grace_shop' else point[0]-38
        glazing.append((gx-12, point[1]-204, 59, 22, False, False))
        colors[(102, 155, 155)] = (239, 185, 99, 225)
    for x, y, width, height, _, _ in glazing:
        area = pygame.Rect(x-bounds.x, y-bounds.y, width, height).clip(image.get_rect())
        for xx in range(area.left, area.right):
            for yy in range(area.top, area.bottom):
                pixel = tuple(image.get_at((xx, yy)))
                if pixel[:3] in colors and pixel[3]:
                    light.set_at((xx, yy), colors[pixel[:3]])
    # A quiet, stepped lantern halo stays on the facade, above the door approach.
    x, y = point[0]-bounds.x, point[1]-bounds.y
    lx, ly = (x, y-114) if key.startswith('home_') else (x+43, y-73)
    pygame.draw.rect(light, (248, 179, 82, 12), (lx-16, ly-14, 33, 29), border_radius=6)
    pygame.draw.rect(light, (255, 193, 101, 19), (lx-10, ly-10, 21, 21), border_radius=3)
    pygame.draw.rect(light, (255, 220, 145, 170), (lx-2, ly-4, 4, 7))
    return light


def gear(s, center, radius, angle=0., color=EDGE):
    x, y = center
    pygame.draw.circle(s, (64, 67, 56), center, radius+3)
    for i in range(12):
        a = angle+i*math.tau/12
        pygame.draw.line(s, color, (x+math.cos(a)*(radius-4), y+math.sin(a)*(radius-4)),
                         (x+math.cos(a)*(radius+1), y+math.sin(a)*(radius+1)), 5)
    pygame.draw.circle(s, color, center, radius-3, 4)
    for i in range(4):
        a = angle+i*math.pi/2
        pygame.draw.line(s, color, center, (x+math.cos(a)*(radius-6), y+math.sin(a)*(radius-6)), 3)
    pygame.draw.circle(s, TIMBER, center, 5)
    pygame.draw.circle(s, (221, 190, 131), center, 2)


def wheel(s, x, y, angle=0.):
    pygame.draw.circle(s, (67, 67, 52), (x, y), 44)
    pygame.draw.circle(s, (105, 78, 52), (x, y), 41, 6)
    pygame.draw.circle(s, (180, 137, 83), (x, y), 34, 3)
    for i in range(12):
        a = angle+i*math.tau/12
        end = (x+math.cos(a)*36, y+math.sin(a)*36)
        pygame.draw.line(s, (163, 119, 68), (x, y), end, 5)
        dx, dy = math.sin(a)*7, -math.cos(a)*7
        pygame.draw.line(s, (192, 150, 92), (end[0]-dx, end[1]-dy), (end[0]+dx, end[1]+dy), 4)
    pygame.draw.circle(s, (63, 72, 65), (x, y), 10)
    pygame.draw.circle(s, EDGE, (x, y), 6)
    pygame.draw.circle(s, (81, 77, 60), (x, y), 2)


def brickwork(s, bounds, colors, seed, rows=17, columns=31):
    rng = random.Random(seed)
    left, top, width, height = bounds
    old = s.get_clip()
    s.set_clip(old.clip(pygame.Rect(bounds)))
    for yy in range(top, top+height, rows):
        for xx in range(left-columns, left+width, columns):
            xx += columns//2 if (yy-top)//rows % 2 else 0
            col = rng.choice(colors)
            rect(s, col, (xx+1, yy+1, columns-2, rows-2), 2)
            pygame.draw.line(s, tuple(min(255,c+12) for c in col), (xx+3, yy+2), (xx+columns-5, yy+2), 1)
    s.set_clip(old)


def roof(s, x, y, width, key, color):
    left = x-width//2
    low = y-145
    high = y-207
    if key in ('mill', 'workshop', 'grace_shop', 'farm'):
        # Broad gables make the workshops and mill readable at map scale.
        ridge = x + (35 if key == 'grace_shop' else -22 if key == 'farm' else 0)
        points = [(left-9,low), (ridge,high-20), (left+width+8,low)]
    elif key == 'foundry':
        points = [(left-9,low),(left+31,high-5),(left+width-39,high-5),(left+width+9,low)]
    elif key in ('fuel_yard','sawmill'):
        points = [(left-8,high+8),(left+width+8,high+29),(left+width+8,low),(left-8,low)]
    else:
        points = [(left-9,low),(left+13,high),(left+width-19,high),(left+width+9,low)]
    town_roofs.draw(s, points, key, color)
    if key == 'foundry':
        # Attached louvered roof vent, with a cap and a shaded vertical face.
        rect(s,(46,65,61),(x-24,y-220,48,23),1)
        rect(s,(108,130,119),(x-28,y-223,56,5),1)
        for yy in range(y-215,y-199,5):
            pygame.draw.line(s,(139,153,128),(x-20,yy),(x+20,yy),2)
    if key in ('workshop','grace_shop'):
        # Roof glass is part of each workshop's silhouette rather than a label.
        gx = x+12 if key=='grace_shop' else x-38
        pygame.draw.polygon(s,TIMBER,[(gx-18,y-180),(gx+15,y-209),(gx+54,y-180)])
        pygame.draw.polygon(s,(102,155,155),[(gx-12,y-183),(gx+15,y-204),(gx+46,y-183)])
        for dx in (0,15,30):
            pygame.draw.line(s,(188,185,137),(gx+dx,y-199+abs(15-dx)//2),(gx+dx,y-182),2)
    elif key.startswith('home_') or key == 'parts_shop':
        gx = x-30
        rect(s,(205,187,143),(gx-18,y-195,36,36),1)
        pygame.draw.polygon(s,TIMBER,[(gx-23,y-194),(gx,y-217),(gx+23,y-194)])
        pygame.draw.polygon(s,tuple(min(255,c+13) for c in color),[(gx-18,y-195),(gx,y-212),(gx+18,y-195)])
        window(s,gx-10,y-188,20,21)


def chimney(s,x,y,key):
    width = 31 if key in ('bakery','foundry') else 20
    # Extend behind the full roof; short stacks float above the sloping gables.
    height = 83
    top = y-229
    rect(s,(79,67,55),(x-3,top+4,width+6,height),2)
    rect(s,(135,92,67),(x,top,width,height),1)
    for yy in range(top+7,top+height,10):
        pygame.draw.line(s,(96,69,54),(x+1,yy),(x+width-1,yy),2)
        pygame.draw.line(s,(180,129,85),(x+3,yy-2),(x+width-4,yy-2),1)
        xx=x+(10 if (yy-top)//10%2 else width-10)
        pygame.draw.line(s,(95,69,53),(xx,yy-7),(xx,yy-1),1)
    rect(s,(175,139,94),(x-5,top-3,width+10,7),1)
    rect(s,(66,63,51),(x+3,top-3,width-6,3))


def building(s, point, key, heading, small, color, label):
    x,y = point
    home = key.startswith('home_')
    width = 180 if home else 255
    left=x-width//2
    wall=(218,199,157)
    if key in ('mill','foundry'):wall=(139,142,123)
    elif key in ('fuel_yard','sawmill','farm'):wall=(167,131,83)
    elif key in ('workshop','parts_shop'):wall=(205,193,156)
    elif key=='grace_shop':wall=(192,187,163)
    # The wall starts at the eaves. A rectangular wall behind a triangular roof
    # exposes square corners above the roof and makes it look pasted together.
    rect(s,(86,82,64),(left-3,y-145,width+6,132),3)
    rect(s,wall,(left,y-144,width,117),2)
    if key in ('mill','foundry'):
        colors=((153,151,126),(143,144,119),(162,157,129)) if key=='mill' else ((134,119,98),(145,123,99),(123,113,96))
        brickwork(s,(left+3,y-143,width-6,113),colors,sum(map(ord,key)))
    elif key in ('fuel_yard','sawmill','farm'):
        for xx in range(left+7,left+width,16):
            pygame.draw.line(s,(117,87,59),(xx,y-143),(xx,y-31),2)
            pygame.draw.line(s,(193,154,100),(xx+3,y-140),(xx+3,y-35),1)
    else:
        rng=random.Random(sum(map(ord,key)))
        for _ in range(58):
            xx,yy=rng.randrange(left+6,left+width-6),rng.randrange(y-143,y-32)
            pygame.draw.line(s,tuple(max(0,c-13) for c in wall),(xx,yy),(xx+4,yy),1)
    # Recessed foundations and front timber frame remain clear of the doorstep.
    brickwork(s,(left,y-41,width,16),((157,151,121),(168,160,129),(180,169,136)),24,16,27)
    for xx in (left+4,left+width-11):
        rect(s,TIMBER,(xx,y-145,7,118))
        pygame.draw.line(s,EDGE,(xx+1,y-142),(xx+1,y-31),1)
    rect(s,(113,85,59),(left,y-113,width,5))
    chimney(s,left+width-45,y,key)
    roof(s,x,y,width,key,color)
    # Facade windows remain secondary to each trade's large identifying object.
    for wx, wy, ww, wh, arched, shutters in facade_windows(point, key):
        window(s, wx, wy, ww, wh, arched=arched, shutters=shutters)
    # A consistently centered, inset door preserves the established entry point.
    rect(s,(76,65,47),(x-27,y-92,54,68),5)
    rect(s,(148,103,61),(x-22,y-87,44,63),3)
    rect(s,(170,124,73),(x-20,y-85,8,59),2)
    for xx in range(x-11,x+20,9):
        pygame.draw.line(s,(106,76,49),(xx,y-82),(xx,y-29),1)
    for yy in (y-69,y-37):
        pygame.draw.line(s,(65,70,60),(x-20,yy),(x-9,yy),3)
    pygame.draw.circle(s,EDGE,(x+13,y-55),3)
    pygame.draw.circle(s,(244,209,135),(x+12,y-56),1)
    rect(s,(114,113,93),(x-33,y-24,66,11),2)
    rect(s,(207,190,150),(x-32,y-24,64,5),1)
    # Lantern, with a bracket that stays inside the front wall.
    lx,ly=(x-5,y-121) if home else (x+38,y-80)
    pygame.draw.lines(s,INK,False,[(lx-4,ly-7),(lx+5,ly-7),(lx+5,ly-1)],2)
    rect(s,INK,(lx,ly,11,15),2)
    rect(s,(241,191,102),(lx+3,ly+3,5,8),1)
    if not home:
        rendered = heading.render(label.upper(),True,CREAM)
        font = heading if rendered.get_width() < width-23 else small
        value=label.upper()
        while font.render(value,True,CREAM).get_width()>width-23 and value:
            value=value[:-1]
        rendered=font.render(value,True,CREAM)
        rect(s,(41,65,58),(left+4,y-143,width-8,29),2)
        pygame.draw.line(s,(202,164,105),(left+6,y-141),(left+width-7,y-141),1)
        pygame.draw.line(s,(118,111,77),(left+6,y-116),(left+width-7,y-116),1)
        for xx in (left+9,left+width-10):pygame.draw.circle(s,EDGE,(xx,y-129),2)
        s.blit(rendered,rendered.get_rect(center=(x,y-128)))
    if key=='mill':
        rect(s,(75,82,67),(left+8,y-107,6,84),1)
        rect(s,(75,82,67),(left+80,y-107,6,84),1)
        pygame.draw.line(s,(148,142,104),(left+9,y-66),(left+84,y-66),5)
        rect(s,(69,85,76),(left+4,y-29,88,8),1)
        rect(s,(83,134,136),(left+7,y-27,82,3))
        wheel(s,left+46,y-66)
        for xx in (left+width-63,left+width-43):
            rect(s,(195,169,111),(xx,y-57,18,29),7)
            pygame.draw.line(s,(133,108,69),(xx+3,y-50),(xx+14,y-50),2)
    elif key in ('bakery','east_bakery'):
        # Large vaulted bread oven gives the bakery its own street silhouette.
        ox=left+width-58
        rect(s,(94,72,52),(ox-12,y-106,65,78),22)
        rect(s,(172,117,75),(ox-7,y-102,55,70),20)
        rect(s,(64,59,45),(ox+1,y-83,38,46),17)
        rect(s,(191,91,49),(ox+7,y-61,26,20),6)
        for i in range(4):
            pygame.draw.ellipse(s,(225,177,91),(left+15+i*14,y-55,13,19))
            pygame.draw.line(s,(252,222,155),(left+19+i*14,y-51),(left+23+i*14,y-53),1)
        rect(s,WOOD,(left+10,y-36,69,8),1)
        for xx in (left+17,left+68):rect(s,TIMBER,(xx,y-30,5,9))
    elif key=='market':
        for xx in (x-59,x+55):rect(s,TIMBER,(xx,y-100,5,76))
        for i in range(8):
            col=(227,212,170) if i%2 else (56,109,100)
            pygame.draw.polygon(s,col,[(x-52+i*13,y-110),(x-39+i*13,y-110),(x-48+i*16,y-94),(x-64+i*16,y-94)])
            rect(s,col,(x-64+i*16,y-94,16,8),3)
        for xx in (left+10,left+width-57):
            rect(s,WOOD,(xx,y-49,47,22),2)
            for i in range(4):
                pygame.draw.circle(s,((191,104,65),(204,170,75),(107,142,87))[i%3],(xx+7+i*10,y-48),5)
    elif key=='fuel_yard':
        rect(s,(71,64,47),(left+12,y-107,80,73),2)
        for row in range(3):
            for col in range(4-row//2):
                xx,yy=left+24+col*18+row%2*5,y-43-row*16
                pygame.draw.circle(s,(99,71,46),(xx,yy),10)
                pygame.draw.circle(s,(197,152,91),(xx,yy),7)
                pygame.draw.circle(s,(140,101,58),(xx,yy),3,1)
        rect(s,(104,76,47),(left+8,y-110,88,6))
        for xx in (left+8,left+90):rect(s,TIMBER,(xx,y-106,5,78))
        for yy in range(y-91,y-30,14):rect(s,(93,77,55),(left+width-71,yy,60,9),2)
        for xx in (left+width-65,left+width-19):rect(s,(68,73,58),(xx,y-97,4,68))
    elif key=='foundry':
        rect(s,(70,69,58),(left+12,y-107,80,79),19)
        rect(s,(176,118,70),(left+18,y-101,68,70),17)
        rect(s,(47,51,45),(left+24,y-92,56,58),14)
        for dx,dy in ((0,0),(14,4),(30,-1)):
            pygame.draw.polygon(s,(209,113+dx,55),[(left+28+dx,y-38),(left+36+dx,y-76+dy),(left+45+dx,y-38)])
        for row in range(2):
            for col in range(3-row):
                xx=left+width-75+col*22+row*10; yy=y-40-row*15
                pygame.draw.polygon(s,(106,133,128),[(xx,yy),(xx+4,yy-9),(xx+17,yy-9),(xx+21,yy),(xx+17,yy+8),(xx+3,yy+8)])
                pygame.draw.line(s,(170,185,160),(xx+5,yy-8),(xx+16,yy-8),2)
    elif key=='sawmill':
        for i in range(5):
            rect(s,(177+i*4,131+i*3,76),(left+width-79,y-70+i*9,67,8),1)
            pygame.draw.line(s,(107,81,51),(left+width-76,y-65+i*9),(left+width-19,y-65+i*9),1)
        gear(s,(left+45,y-48),21,color=(159,174,158))
    elif key in ('workshop','parts_shop','toolmaker','grace_shop'):
        bx=left+12
        # A real sheltered workbench, tools and workpiece replace generic barrels.
        rect(s,TIMBER,(bx,y-61,73,7),2)
        rect(s,EDGE,(bx+2,y-61,69,3))
        for xx in (bx+5,bx+62):rect(s,TIMBER,(xx,y-54,6,27),1)
        rect(s,(120,134,115),(bx+10,y-76,28,14),2)
        rect(s,(69,87,78),(bx+19,y-81,8,8))
        pygame.draw.line(s,(194,176,129),(bx+50,y-78),(bx+44,y-64),3)
        pygame.draw.line(s,(89,109,100),(bx+45,y-79),(bx+55,y-76),4)
        gear(s,(left+width-31,y-46),19)
        if key=='grace_shop':
            # A compact copper experimental manifold on the roof.
            pygame.draw.lines(s,(192,137,72),False,[(x-77,y-159),(x-77,y-195),(x-53,y-195)],5)
            pygame.draw.circle(s,(207,176,114),(x-49,y-195),10)
            pygame.draw.circle(s,CREAM,(x-49,y-195),7)
            pygame.draw.line(s,INK,(x-49,y-195),(x-45,y-199),1)
    elif key=='farm':
        for i in range(3):
            rect(s,(205,175,100),(left+14+i*19,y-66,18,39),6)
            pygame.draw.line(s,(134,113,64),(left+17+i*19,y-57),(left+28+i*19,y-57),2)
        pygame.draw.line(s,(100,80,53),(left+width-30,y-92),(left+width-49,y-28),4)
        for dx in (-7,0,7):pygame.draw.line(s,(134,146,117),(left+width-30+dx,y-99),(left+width-29+dx,y-83),2)
    if home:
        rect(s,(118,88,59),(left+7,y-140,width-14,7))
        pygame.draw.line(s,(193,153,99),(left+8,y-139),(left+width-9,y-139),1)
        for xx,sgn in ((left+12,1),(left+width-13,-1)):
            pygame.draw.line(s,(126,94,62),(xx,y-132),(xx+sgn*22,y-116),5)
        for xx in (left+18,left+width-63):
            rect(s,(140,89,57),(xx,y-63,46,14),2)
            for i in range(5):
                pygame.draw.circle(s,(68,111,74),(xx+5+i*9,y-65),5)
                pygame.draw.circle(s,((226,153,125),(235,203,123),(182,158,184))[i%3],(xx+5+i*9,y-69),3)
        # Personal cottage doors and climbing plants retain unlabeled homes.
        for i in range(8):
            yy=y-43-i*12
            pygame.draw.line(s,(74,110,68),(left+6,yy),(left+9,yy-13),2)
            pygame.draw.ellipse(s,(104,142,81),(left+4-(i%2)*6,yy-5,9,4))


def river_motion(surface,camera,width,height,seconds):
    import town_water
    ox,oy=camera
    if height-92-oy>surface.get_height():return
    for i in range(width//54):
        x=(i*57+int(seconds*9))%(width-80)+40
        if 1030<x<1220:continue
        y=height-72+(i%4)*7
        length=9+int((math.sin(seconds+i)*.5+.5)*14)
        if not town_water.blocked(x,y,width,height) or not town_water.blocked(x+length,y,width,height):continue
        pygame.draw.line(surface,(136,185,179),(x-ox,y-oy),(x+length-ox,y-oy),1)


WELL_COURT = town_ground.WELL_COURT


def ground_details(surface):
    """Flat district materials add character without changing walkable ground."""
    # A small worn stone court anchors the existing well and garden.
    under_court=surface.subsurface(WELL_COURT).copy()
    pygame.draw.ellipse(surface,(110,132,91),WELL_COURT)
    pygame.draw.ellipse(surface,(167,162,121),(824,834,116,65))
    for i in range(18):
        a=i*math.tau/18
        x,y=882+math.cos(a)*51,866+math.sin(a)*27
        pygame.draw.line(surface,(194,184,142),(x-4,y),(x+4,y),5)
    pygame.draw.ellipse(surface,(181,174,132),(843,847,78,39))
    # Break the rim at the actual approaches. A green outline or paving ring
    # across a path mouth reads as a texture seam even though depth is correct.
    trail=town_ground.footpath_surface(surface.get_size())
    inner=pygame.Surface(WELL_COURT.size,pygame.SRCALPHA)
    pygame.draw.ellipse(inner,(255,255,255),(13,12,100,53))
    for xx in range(WELL_COURT.width):
        for yy in range(WELL_COURT.height):
            wx,wy=WELL_COURT.x+xx,WELL_COURT.y+yy
            if trail.get_at((wx,wy)).a and not inner.get_at((xx,yy)).a:
                surface.set_at((wx,wy),under_court.get_at((xx,yy)))
    # Drain grates sit at the working street's southern shoulders.
    for x in (1810,2020,2280,2490):
        rect(surface,(103,113,91),(x,720,45,9),2)
        for xx in range(x+5,x+40,7):pygame.draw.line(surface,(61,82,74),(xx,722),(xx,726),2)
        pygame.draw.line(surface,(175,164,117),(x+2,720),(x+43,720),1)


def planting_clusters(surface,layout,exclusions):
    """Low flowers and ferns cluster around existing scenery, off all routes."""
    rng=random.Random(881)
    for kind,x,y,_ in layout:
        if kind not in ('tree','birch','pine','bench','well'):continue
        for _ in range(22):
            angle=rng.random()*math.tau
            xx=round(x+math.cos(angle)*rng.randrange(27,63))
            yy=round(y+math.sin(angle)*rng.randrange(12,32))
            bounds=pygame.Rect(xx-5,yy-8,12,12)
            if any(bounds.colliderect(area) for area in exclusions):continue
            if not town_ground.clears_road(bounds):continue
            if not town_ground.clears_garden(bounds):continue
            pygame.draw.line(surface,(72,113,69),(xx,yy+2),(xx,yy-6),1)
            pygame.draw.line(surface,(104,143,77),(xx-4,yy-3),(xx,yy),2)
            pygame.draw.line(surface,(127,155,88),(xx+1,yy-4),(xx+4,yy-6),2)
            if rng.random()<.25:
                pygame.draw.rect(surface,(223,192,127),(xx-1,yy-8,3,3))


def building_effects(surface,camera,key,point,seconds,working=False,evening=0.):
    x,y=point;ox,oy=camera
    x-=ox;y-=oy
    width=180 if key.startswith('home_') else 255
    left=x-width//2
    if key=='mill':
        wheel(surface,left+46,y-66,seconds*.38 if working else 0.)
    if key=='sawmill':
        gear(surface,(left+45,y-48),21,seconds*.35 if working else 0.,color=(159,174,158))
    elif key in ('workshop','parts_shop','toolmaker','grace_shop'):
        gear(surface,(left+width-31,y-46),19,seconds*.45 if working else 0.)
    bakery = key in ('bakery', 'east_bakery')
    if bakery:
        rect(surface,(64,59,45),(left+width-51,y-61,26,20),6)
    elif key=='foundry':
        # Clear the baked-in flame silhouettes when production stops.
        rect(surface,(47,51,45),(left+27,y-83,49,46))
    if working and (bakery or key=='foundry'):
        cx=left+width-30 if bakery else left+52
        cy=y-52
        for i in range(3):
            flicker=math.sin(seconds*7+i*3)
            pygame.draw.polygon(surface,(244,176+i*13,76),[(cx-12+i*8,cy+12),(cx-9+i*8,cy-6-flicker*6),(cx-5+i*8,cy+12)])
    if working and key in ('mill','bakery','east_bakery','foundry','workshop','parts_shop'):
        chimney_x=left+width-34
        for i in range(4):
            age=(seconds*.31+i*.24)%1.
            puff=pygame.Surface((32,28),pygame.SRCALPHA)
            pygame.draw.ellipse(puff,(220,220,190,round((1-age)*80)),(1,1,12+round(age*16),8+round(age*13)))
            surface.blit(puff,(chimney_x-7+round(age*15),y-241-round(age*35)))


def clothing(surface,x,y,name,facing,moving=False,phase=0.):
    """Extra character silhouettes retain original eyes, feet and hit targets."""
    front=facing!='north'
    side=facing in ('east','west')
    sign=-1 if facing=='west' else 1
    if name in ('Agnes','Dara','Bram'):
        apron=(215,198,153) if name=='Agnes' else (167,176,151) if name=='Dara' else (147,119,76)
        if front:
            if side:
                pygame.draw.polygon(surface,apron,[(x+sign*3,y-11),(x+sign*9,y-11),(x+sign*11,y+8),(x+sign*2,y+8)])
                rect(surface,(110,101,75),(x+(4 if sign>0 else -9),y-2,5,6),1)
            else:
                pygame.draw.polygon(surface,apron,[(x-6,y-11),(x+6,y-11),(x+9,y+8),(x-8,y+8)])
                rect(surface,(110,101,75),(x-4,y-2,9,6),1)
        else:
            pygame.draw.line(surface,apron,(x-8,y),(x+8,y),2)
            pygame.draw.lines(surface,apron,False,[(x-3,y+5),(x,y),(x+4,y+5)],2)
        if name=='Bram':
            rect(surface,(97,112,81),(x-12,y-40,25,5),2)
            rect(surface,(122,134,93),(x-7,y-44,17,7),3)
        elif name=='Agnes':
            bun_x=x-sign*10 if side else x-10
            pygame.draw.circle(surface,(186,151,102),(bun_x,y-35),5)
            pygame.draw.line(surface,(229,204,153),(x-10,y-40),(x+9,y-37),3)
        else:  # Dara's tied headcloth remains visible from behind.
            cloth=(120,166,167)
            rect(surface,cloth,(x-11,y-39,22,5),1)
            tail=x-sign*10 if side else x+8
            pygame.draw.polygon(surface,cloth,[(tail-3,y-35),(tail+3,y-35),(tail+4,y-25),(tail,y-28)])
    elif name=='Mely':
        if facing!='south':
            bun_x=x-sign*10 if side else x+5
            rect(surface,(71,55,46),(bun_x-4,y-32,8,9),2)
            pygame.draw.line(surface,(239,188,119),(bun_x-3,y-29),(bun_x+3,y-29),2)
        shawl=(200,151,98)
        pygame.draw.polygon(surface,shawl,[(x-12,y-15),(x-3,y-12),(x+11,y-15),(x+10,y-7),(x-11,y-9)])
        pygame.draw.line(surface,(239,188,119),(x-10,y-14),(x+8,y-11),1)
        if front:pygame.draw.circle(surface,(235,194,112),(x+3,y-10),2)
    elif name=='Luca':
        if facing!='north':
            pygame.draw.line(surface,(151,143,119),(x-sign*7 if side else x-9,y-30),
                             (x-sign*7 if side else x-9,y-23),2)
        if front:
            rect(surface,(108,82,58),(x-7,y-9,13,16),2)
            pygame.draw.line(surface,(202,161,94),(x-5,y-5),(x+4,y-5),2)
            pygame.draw.line(surface,(168,180,162),(x+2,y-7),(x+2,y+2),2)
        else:pygame.draw.line(surface,(191,151,92),(x-8,y+1),(x+8,y+1),2)
    elif name=='Grace':
        # A tied-back braid, clear of the established wooden leg.
        braid_x=x-sign*11 if side else x+9
        if facing!='south':
            swing=round(math.sin(phase)*2) if moving else 0
            pygame.draw.lines(surface,(157,108,66),False,[(braid_x,y-32),(braid_x+2,y-22),(braid_x+swing,y-14)],4)
            rect(surface,(206,164,103),(braid_x-2+swing,y-17,5,3),1)
        if front:
            pygame.draw.polygon(surface,(74,82,78),[(x-7,y-11),(x+7,y-11),(x+8,y+6),(x-6,y+6)])
            pygame.draw.line(surface,(186,148,94),(x-6,y-6),(x+6,y-6),2)
        pygame.draw.line(surface,(206,164,103),(x-10,y-36),(x+9,y-36),2)
    elif name=='Ada':
        rect(surface,(184,151,91),(x-14,y-38,28,4),2)
        rect(surface,(207,176,112),(x-8,y-45,17,8),3)
        pygame.draw.line(surface,(117,92,55),(x-8,y-40),(x+9,y-40),2)
    elif name in ('Rowan','Saffron','Felix','Wren','Hugo','Alma','Perry','Cleo','Jun'):
        if name in ('Rowan','Felix','Hugo'):
            cap={'Rowan':(157,128,83),'Felix':(99,128,149),'Hugo':(172,130,91)}[name]
            rect(surface,cap,(x-10,y-42,20,8),2)
            pygame.draw.line(surface,(66,66,55),(x-12,y-35),(x+12,y-35),2)
        elif name in ('Wren','Jun'):
            rect(surface,(208,180,118),(x-14,y-37,28,4),1)
            rect(surface,(182,149,91),(x-8,y-43,16,8),2)
        elif name in ('Saffron','Alma'):
            pygame.draw.polygon(surface,(229,191,130),[(x-12,y-16),(x,y-11),(x+12,y-16),(x+9,y-6),(x-9,y-6)])
            pygame.draw.circle(surface,(216,163,102),(x-sign*10,y-34),4)
        else:
            rect(surface,(180,160,119),(x-10,y-16,20,4),1)
            tail=x-sign*8 if side else x+7
            rect(surface,(180,160,119),(tail-2,y-13,4,15),1)
        if facing=='north':
            pygame.draw.line(surface,(193,169,118),(x-8,y-10),(x+8,y+4),2)
        else:
            rect(surface,(193,169,118),(x+(4 if side and sign>0 else -8),y-5,6,8),1)


def activity_prop(surface,x,y,person,seconds,moving):
    """Show a resident's existing activity without inventing simulation work."""
    action=person.get('activity','')
    if action=='seeking food':
        pygame.draw.arc(surface,(103,77,48),(x+9,y-7,12,13),0,math.pi,2)
        rect(surface,(174,127,70),(x+8,y+1,16,11),2)
        pygame.draw.line(surface,(219,173,101),(x+9,y+4),(x+22,y+4),2)
    elif action=='working' and not moving:
        name=person['name']
        if name in ('Luca','Bram','Mely'):
            angle=math.sin(seconds*2+len(name))*.35
            xx=x+15+round(math.sin(angle)*5)
            pygame.draw.line(surface,(163,128,81),(x+12,y+3),(xx,y-10),3)
            pygame.draw.line(surface,(148,166,147),(xx-5,y-11),(xx+5,y-9),4)
        elif name in ('Agnes','Dara'):
            rect(surface,(111,80,48),(x-13,y+3,26,5),1)
            for i in range(3):pygame.draw.ellipse(surface,(224,180,104),(x-10+i*7,y-2,7,7))
