"""Cached, deterministic town artwork; decoration never changes the simulation."""
import math
import random
import pygame
from ui_theme import COPPER, GOLD, PAPER, TEAL


def grass(surface, width, height):
    rng = random.Random(416)
    # Irregular meadow patches have softer value changes than isolated ovals.
    for _ in range(280):
        x, y = rng.randrange(width), rng.randrange(height)
        color = rng.choice(((114, 144, 98), (122, 151, 103), (125, 152, 104)))
        w,h=rng.randrange(60,165),rng.randrange(24,52)
        pygame.draw.polygon(surface,color,[(x-w//2,y-5),(x-w//3,y-h//2),
                            (x+w//5,y-h//2+4),(x+w//2,y-4),(x+w//3,y+h//3),
                            (x-w//6,y+h//2),(x-w//2,y+h//4)])
    for _ in range(1700):
        x, y = rng.randrange(width), rng.randrange(height)
        shade = rng.choice(((97, 132, 88), (142, 163, 113), (133, 158, 108)))
        pygame.draw.lines(surface, shade, False, [(x - 3, y - 4), (x, y), (x + 1, y - 7), (x + 2, y), (x + 5, y - 3)], 1)
        if rng.random() < .16:
            pygame.draw.rect(surface, (207, 194, 136), (x + 4, y - 4, 2, 2))


def riverbank(surface, width, height):
    from town_water import bank_details
    bank_details(surface, width, height)


def tree(surface, x, y, kind="tree"):
    rng = random.Random(x * 37 + y * 71)
    if kind == "pine":
        pygame.draw.ellipse(surface, (84, 114, 81), (x - 30, y + 1, 65, 19))
        pygame.draw.rect(surface, (97, 72, 49), (x - 5, y - 30, 10, 45), border_radius=2)
        pygame.draw.line(surface,(163,119,69),(x-2,y-27),(x-2,y+12),2)
        for yy, half, color in ((y - 30, 34, (39, 83, 65)), (y - 52, 28, (48, 101, 71)), (y - 73, 20, (66, 121, 81))):
            points=[(x,yy-27),(x-half//3,yy-6),(x-half//4,yy-7),
                    (x-half*2//3,yy+8),(x-half//2,yy+6),(x-half,yy+20),
                    (x+half,yy+20),(x+half//2,yy+6),(x+half*2//3,yy+8),(x+half//3,yy-6)]
            pygame.draw.polygon(surface,color,points)
            pygame.draw.polygon(surface,tuple(min(255,c+16) for c in color),[(x,yy-23),(x-half+8,yy+17),(x-3,yy+10)])
            for j in range(8):
                dx=rng.randrange(-half+6,half-5);dy=rng.randrange(8,18)
                pygame.draw.line(surface,(86,137,86),(x+dx,yy+dy),(x+dx+4,yy+dy-1),1)
        return
    birch = kind == "birch"
    pygame.draw.ellipse(surface, (84, 114, 81), (x - 30 if birch else x - 38, y - 3, 68 if birch else 88, 24))
    bark = (208, 198, 156) if birch else (104, 77, 53)
    pygame.draw.rect(surface, bark, (x - 5, y - 50, 10, 66), border_radius=2)
    pygame.draw.line(surface, bark, (x, y - 22), (x - 17, y - 52), 5)
    pygame.draw.line(surface, bark, (x, y - 30), (x + 17, y - 62), 4)
    if not birch:
        pygame.draw.line(surface,(160,113,66),(x-3,y-36),(x-3,y+11),2)
        pygame.draw.line(surface,bark,(x-1,y+7),(x-10,y+15),3)
        pygame.draw.line(surface,bark,(x+2,y+8),(x+11,y+15),3)
    if birch:
        for yy in range(y - 45, y + 12, 9):
            pygame.draw.line(surface, (108, 110, 86), (x - 4, yy), (x + (1 if yy % 2 else 4), yy), 2)
    colors = ((47, 94, 67), (75, 123, 77), (112, 151, 88)) if birch else ((38, 86, 63), (57, 110, 69), (85, 137, 79))
    clusters = ((0, -54, 31), (-15, -68, 23), (12, -77, 22), (-5, -87, 17)) if birch else ((0, -44, 39), (-16, -58, 30), (8, -67, 23), (-9, -78, 12))
    for i, (dx, dy, radius) in enumerate(clusters):
        # Scalloped canopy edges, layered shadows and small leaf clusters.
        points=[]
        for j in range(20):
            angle=j*math.tau/20
            extent=radius-(j%2)*3
            points.append((round(x+dx+math.cos(angle)*extent),round(y+dy+math.sin(angle)*extent)))
        pygame.draw.polygon(surface,colors[min(i,2)],points)
        pygame.draw.arc(surface,tuple(min(255,c+18) for c in colors[min(i,2)]),
                        (x+dx-radius+4,y+dy-radius+3,radius*2-8,radius*2-8),.5,2.9,3)
    for _ in range(65):
        dx, dy = rng.randrange(-27, 28), rng.randrange(-81 if not birch else -94, -32)
        if any((dx - cx) ** 2 + (dy - cy) ** 2 < (radius - 5) ** 2 for cx, cy, radius in clusters):
            color = rng.choice((colors[1], colors[2], (139, 171, 103)))
            pygame.draw.rect(surface,color,(x+dx,y+dy,4,2))
            if rng.random()<.35:pygame.draw.rect(surface,color,(x+dx+2,y+dy-2,3,2))
    if not birch and (x + y) % 3 == 0:
        for dx, dy in ((-17, -47), (13, -61), (-2, -73), (24, -39)):
            pygame.draw.circle(surface, (197, 119, 80), (x + dx, y + dy), 3)
            pygame.draw.rect(surface, (233, 169, 108), (x + dx - 1, y + dy - 2, 2, 2))


def flowers(surface, rng, x, y, width=94, height=32):
    pygame.draw.rect(surface, (94, 123, 82), (x, y, width, height), border_radius=10)
    pygame.draw.rect(surface, (130, 116, 78), (x + 4, y + 5, width - 8, height - 9), border_radius=8)
    for i in range(16):
        fx, fy = x + rng.randrange(8, width - 8), y + rng.randrange(6, height - 5)
        pygame.draw.line(surface, (65, 113, 76), (fx, fy + 3), (fx, fy - 3), 2)
        color = ((226, 161, 128), (192, 163, 186), PAPER, GOLD)[i % 4]
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            pygame.draw.rect(surface, color, (fx + dx - 1, fy + dy - 2, 3, 3))
        pygame.draw.rect(surface, (174, 127, 60), (fx, fy - 1, 2, 2))


def small_prop(surface, rng, kind, x, y):
    if kind == 'logpile':
        pygame.draw.ellipse(surface,(94,116,79),(x-36,y-2,74,13))
        for row in range(3):
            for col in range(4-row):
                xx,yy=x-25+col*17+row*8,y-2-row*13
                pygame.draw.circle(surface,(98,72,46),(xx,yy),10)
                pygame.draw.circle(surface,(181,139,78),(xx,yy),8)
                pygame.draw.circle(surface,(117,84,47),(xx,yy),4,1)
                pygame.draw.line(surface,(216,176,103),(xx-4,yy-5),(xx+3,yy-5),1)
        pygame.draw.line(surface,(99,78,48),(x-35,y+7),(x+35,y+7),3)
    elif kind == 'cart':
        pygame.draw.ellipse(surface,(92,116,81),(x-40,y+5,84,16))
        for xx in (x-31,x+30):
            pygame.draw.circle(surface,(66,68,53),(xx,y+7),11)
            pygame.draw.circle(surface,(177,137,77),(xx,y+7),8,2)
            for dx,dy in ((-5,0),(5,0),(0,-5),(0,5)):
                pygame.draw.line(surface,(177,137,77),(xx,y+7),(xx+dx,y+7+dy),2)
        pygame.draw.polygon(surface,(103,76,46),[(x-34,y-28),(x+29,y-28),(x+37,y+2),(x-33,y+2)])
        pygame.draw.rect(surface,(174,127,71),(x-31,y-22,67,21),border_radius=2)
        for yy in (y-18,y-9):pygame.draw.line(surface,(116,83,49),(x-29,yy),(x+34,yy),2)
        for xx in (x-25,x+25):pygame.draw.line(surface,(79,78,53),(xx,y-24),(xx,y+1),3)
        pygame.draw.line(surface,(110,83,49),(x-35,y-24),(x-38,y-45),4)
        for xx in (x-21,x+2):
            pygame.draw.rect(surface,(202,175,107),(xx,y-36,19,15),border_radius=5)
            pygame.draw.line(surface,(139,114,69),(xx+3,y-31),(xx+15,y-31),2)
    elif kind == 'baskets':
        pygame.draw.ellipse(surface,(92,117,81),(x-22,y+1,49,10))
        for xx,yy in ((x-20,y-15),(x+3,y-7)):
            pygame.draw.arc(surface,(109,81,48),(xx+3,yy-12,18,17),0,math.pi,2)
            pygame.draw.rect(surface,(177,128,69),(xx,yy,23,15),border_radius=4)
            for dy in (4,8,12):pygame.draw.line(surface,(222,178,105),(xx+2,yy+dy),(xx+20,yy+dy),1)
            for dx in (5,11,17):pygame.draw.line(surface,(131,94,50),(xx+dx,yy+1),(xx+dx,yy+13),1)
    elif kind == 'garden':
        pygame.draw.rect(surface,(115,101,64),(x,y-23,85,31),border_radius=5)
        for row in range(2):
            for col in range(7):
                xx,yy=x+8+col*11,y-16+row*14
                pygame.draw.line(surface,(65,111,67),(xx,yy+5),(xx,yy-7),2)
                pygame.draw.ellipse(surface,(93,143,76),(xx-5,yy-4,6,3))
                pygame.draw.ellipse(surface,(119,155,85),(xx+1,yy-7,6,3))
                pygame.draw.circle(surface,((225,163,128),(197,171,187),(239,214,134))[col%3],(xx,yy-9),3)
        for yy in (y-26,y+5):pygame.draw.line(surface,(170,141,87),(x+1,yy),(x+82,yy),3)
    elif kind == "shrub":
        pygame.draw.ellipse(surface, (99, 126, 87), (x - 20, y + 2, 45, 15))
        for dx, dy, radius in ((-9, -1, 11), (8, -5, 13), (0, -10, 10)):
            pygame.draw.circle(surface, (79 + dx, 127 + dx, 85), (x + dx, y + dy), radius)
        for dx, dy in ((-10, -5), (6, -14), (14, -3)):
            pygame.draw.rect(surface, (202, 156, 131), (x + dx, y + dy, 3, 3))
    elif kind == "rocks":
        for dx, dy, size in ((-18, 0, 19), (0, -9, 23), (17, 4, 8)):
            pygame.draw.ellipse(surface, (106, 122, 100), (x + dx, y + dy + 5, size, 8))
            pygame.draw.polygon(surface, (158, 159, 131), [(x + dx, y + dy + 5), (x + dx + 4, y + dy), (x + dx + size - 4, y + dy), (x + dx + size, y + dy + 8), (x + dx + 2, y + dy + 8)])
            pygame.draw.line(surface, (188, 186, 149), (x + dx + 5, y + dy + 1), (x + dx + size - 5, y + dy + 1), 2)
    elif kind == "planter":
        flowers(surface, rng, x + 2, y - 19, 72, 27)
        pygame.draw.rect(surface, (142, 99, 64), (x, y + 2, 76, 20), border_radius=3)
        for xx in range(x + 5, x + 75, 12):
            pygame.draw.line(surface, (106, 82, 56), (xx, y + 4), (xx, y + 19), 1)
        pygame.draw.line(surface, (196, 153, 96), (x + 2, y + 4), (x + 73, y + 4), 3)
    elif kind == "barrel":
        pygame.draw.ellipse(surface, (98, 121, 84), (x - 16, y + 6, 34, 11))
        pygame.draw.rect(surface, (148, 105, 66), (x - 14, y - 25, 28, 36), border_radius=7)
        pygame.draw.ellipse(surface, (188, 148, 92), (x - 14, y - 31, 28, 12))
        for dx in (-8, 0, 8):
            pygame.draw.line(surface, (112, 84, 58), (x + dx, y - 17), (x + dx, y + 7), 1)
        for yy in (y - 14, y + 3):
            pygame.draw.line(surface, (83, 94, 81), (x - 13, yy), (x + 13, yy), 3)
    elif kind == "well":
        pygame.draw.ellipse(surface, (99, 125, 85), (x - 35, y + 5, 74, 17))
        pygame.draw.rect(surface, (156, 151, 119), (x - 26, y - 12, 52, 29), border_radius=7)
        pygame.draw.ellipse(surface, (191, 181, 141), (x - 28, y - 18, 56, 20))
        pygame.draw.ellipse(surface, (55, 79, 72), (x - 19, y - 13, 38, 11))
        for dx in (-23, 20):
            pygame.draw.rect(surface, (109, 83, 57), (x + dx, y - 48, 4, 55))
        pygame.draw.polygon(surface, (90, 115, 104), [(x - 35, y - 43), (x, y - 68), (x + 35, y - 43)])
        pygame.draw.line(surface, (150, 156, 118), (x - 33, y - 43), (x, y - 65), 2)
        pygame.draw.line(surface, (189, 164, 113), (x, y - 39), (x, y - 9), 1)
        pygame.draw.line(surface, (109, 83, 57), (x - 24, y - 30), (x + 25, y - 30), 4)
        pygame.draw.circle(surface, GOLD, (x + 26, y - 30), 6, 2)


def wall_details(surface, left, y, width, key):
    rng = random.Random(sum((i + 1) * ord(c) for i, c in enumerate(key)))
    for _ in range(30):
        x, yy = rng.randrange(left + 12, left + width - 12), rng.randrange(y - 137, y - 34)
        pygame.draw.line(surface, (220, 199, 159), (x, yy), (x + rng.randrange(3, 9), yy), 1)
    for x in range(left + 1, left + width - 10, 23):
        pygame.draw.rect(surface, (166, 156, 128), (x, y - 36, 21, 12), border_radius=2)
        pygame.draw.line(surface, (199, 185, 151), (x + 2, y - 34), (x + 17, y - 34), 1)


def building_details(surface, x, y, width, key, roof):
    left = x - width // 2
    # Ridge caps, chimney brickwork and a small glazed roof vent.
    for xx in range(left - 5, left + width, 22):
        pygame.draw.rect(surface, tuple(min(255, c + 16) for c in roof), (xx, y - 208, 20, 5), border_radius=1)
    for yy in (y - 217, y - 210):
        pygame.draw.line(surface, (91, 79, 65), (left + width - 43, yy), (left + width - 23, yy), 1)
    if key in ("workshop", "grace_shop", "bakery") or key.startswith("home_"):
        pygame.draw.rect(surface, (83, 88, 76), (left + 29, y - 193, 30, 26), border_radius=2)
        pygame.draw.rect(surface, (127, 168, 162), (left + 34, y - 188, 20, 16), border_radius=1)
        pygame.draw.line(surface, (212, 193, 145), (left + 44, y - 188), (left + 44, y - 173), 2)
        pygame.draw.line(surface, (212, 193, 145), (left + 34, y - 180), (left + 53, y - 180), 2)
        pygame.draw.line(surface, (176, 147, 101), (left + 27, y - 195), (left + 61, y - 195), 3)
    # Small details stay on the facade, leaving the door and street uncovered.
    pygame.draw.line(surface, (74, 82, 68), (x + 32, y - 88), (x + 42, y - 88), 2)
    pygame.draw.rect(surface, (74, 82, 68), (x + 36, y - 87, 10, 15), border_radius=2)
    pygame.draw.rect(surface, (239, 198, 111), (x + 39, y - 84, 4, 9))
    for yy in (y - 70, y - 39):
        pygame.draw.line(surface, (72, 72, 59), (x - 19, yy), (x - 11, yy), 2)
    if key in ("workshop", "grace_shop") or key.startswith("home_"):
        vine_x = left + 13
        pygame.draw.lines(surface, (76, 116, 77), False, [(vine_x, y - 29), (vine_x + 3, y - 61), (vine_x, y - 104)], 2)
        for i in range(7):
            yy = y - 34 - i * 10
            pygame.draw.ellipse(surface, (97, 140, 86), (vine_x - 6 if i % 2 else vine_x + 1, yy, 7, 4))
    if key in ("bakery", "east_bakery"):
        pygame.draw.rect(surface, (144, 99, 62), (left + 16, y - 54, 52, 25), border_radius=3)
        for i in range(3):
            pygame.draw.ellipse(surface, (218, 173, 94), (left + 19 + i * 15, y - 62, 13, 20))
            for yy in (y - 58, y - 53):
                pygame.draw.line(surface, (247, 213, 143), (left + 23 + i * 15, yy), (left + 28 + i * 15, yy - 2), 1)
    if key in ("workshop", "parts_shop", "toolmaker", "grace_shop"):
        pygame.draw.rect(surface, (118, 91, 63), (left + 22, y - 60, 46, 6), border_radius=2)
        for i in range(3):
            xx = left + 29 + i * 14
            pygame.draw.line(surface, (78, 95, 90), (xx, y - 54), (xx, y - 32), 3)
            if i % 2:
                pygame.draw.line(surface, (158, 166, 145), (xx - 5, y - 51), (xx + 5, y - 51), 4)
            else:
                pygame.draw.circle(surface, (158, 166, 145), (xx, y - 48), 5, 2)
    if key == "sawmill":
        for dx, dy in ((-9, 0), (8, 0), (0, -13)):
            xx, yy = left + width - 29 + dx, y - 36 + dy
            pygame.draw.circle(surface, (100, 76, 53), (xx, yy), 9)
            pygame.draw.circle(surface, (196, 156, 96), (xx, yy), 7)
            pygame.draw.circle(surface, (142, 105, 65), (xx, yy), 3, 1)
    if key in ("market", "farm", "fuel_yard"):
        pygame.draw.rect(surface, (187, 164, 111), (left + 63, y - 50, 19, 26), border_radius=6)
        pygame.draw.line(surface, (111, 96, 67), (left + 67, y - 45), (left + 79, y - 45), 2)
