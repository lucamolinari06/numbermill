"""Authored expedition backdrops. These drawings never define collision or puzzles."""
import math
import random
import pygame
import water_geometry


def field_ground(surface):
    """Large quiet color masses distinguish woods, wetland and the archive hills."""
    rng = random.Random(6503)
    width, height = surface.get_size()
    # A broad transition connects the regions; detail sits on top of this field.
    def blend(a, b, t):
        return tuple(round(x + (y - x) * t) for x, y in zip(a, b))
    for y in range(0, height, 48):
        wet = max(0, min(1, (y - 950) / 350))
        for x in range(0, width, 64):
            east = max(0, min(1, (x - 1750) / 450))
            archive = max(0, min(1, (x - 3060) / 300))
            color = blend((113, 141, 97), (118, 145, 100), east)
            color = blend(color, (103, 134, 111), wet * east * (1 - archive))
            color = blend(color, (119, 142, 103), archive)
            pygame.draw.rect(surface, color, (x, y, 64, 48))
    areas = (
        ((0, 0, 1910, height), (106, 134, 91), (121, 146, 103)),
        ((1910, 0, 1240, 1110), (110, 137, 94), (124, 149, 105)),
        ((1910, 1080, 1240, height - 1080), (98, 129, 106), (111, 140, 116)),
        ((3260, 0, width - 3260, height), (111, 135, 97), (126, 147, 109)),
    )
    for bounds, dark, light in areas:
        rect = pygame.Rect(bounds)
        old_clip = surface.get_clip()
        surface.set_clip(rect)
        for _ in range(rect.width * rect.height // 11000):
            x = rng.randrange(rect.left - 80, rect.right)
            y = rng.randrange(rect.top - 20, rect.bottom)
            color = dark if rng.random() < .58 else light
            pygame.draw.ellipse(surface, color, (x, y, rng.randrange(95, 270), rng.randrange(30, 85)))
        # Broken grass blades and fallen leaves read as material, not confetti.
        for _ in range(rect.width * rect.height // 1050):
            x, y = rng.randrange(rect.left, rect.right), rng.randrange(rect.top, rect.bottom)
            color = tuple(min(255, c + 14) for c in light) if rng.random() < .35 else dark
            pygame.draw.line(surface, color, (x, y), (x + 2, y - rng.randrange(3, 7)), 1)
            if rng.random() < .25:
                pygame.draw.line(surface, color, (x + 4, y), (x + 6, y - 3), 1)
        surface.set_clip(old_clip)


def water(surface, polygon, seed, river=False, bridge_y=None):
    """Render the exact collision contour, with a narrow soft bank outside it."""
    rng = random.Random(seed)
    rect = pygame.Rect(water_geometry.bounds(polygon))
    pygame.draw.lines(surface, (81, 109, 83), True, polygon, 22)
    pygame.draw.lines(surface, (64, 90, 75), True, polygon, 12)
    pygame.draw.polygon(surface, (47, 95, 98), polygon)
    if river:
        half = len(polygon) // 2
        centerline = [((a[0]+b[0])//2, a[1]) for a,b in zip(polygon[:half], reversed(polygon[half:]))]
        pygame.draw.lines(surface, (37, 76, 83), False, centerline, 32)
    else:
        cx, cy = rect.center
        inner = [(round(cx + (x-cx)*.77), round(cy+(y-cy)*.77)) for x,y in polygon]
        pygame.draw.polygon(surface, (39, 79, 84), inner)
    pygame.draw.lines(surface, (102, 144, 121), True, polygon, 2)
    for _ in range(rect.width * rect.height // 850):
        x, y = rng.randrange(rect.left + 8, rect.right - 8), rng.randrange(rect.top + 8, rect.bottom - 8)
        length = rng.randrange(6, 20)
        end = (x+3, y+length) if river else (x+length, y)
        if not water_geometry.contains((x,y),polygon) or not water_geometry.contains(end,polygon):continue
        pygame.draw.line(surface, rng.choice(((76, 121, 119), (61, 103, 107))), (x, y), end, 1)
        if not river and rng.random() < .15:
            pygame.draw.ellipse(surface, (105, 149, 105), (x, y, 15, 8))
            pygame.draw.line(surface, (40, 85, 79), (x + 7, y + 4), (x + 13, y + 4), 2)
            pygame.draw.circle(surface, (233, 191, 160), (x + 3, y + 1), 2)
    for index, (x, y) in enumerate(polygon):
        if bridge_y is not None and abs(y-bridge_y)<105:continue
        if index % 4 == 1:
            pygame.draw.ellipse(surface, (88, 108, 86), (x - 9, y - 4, 16, 8))
            pygame.draw.line(surface, (137, 147, 108), (x - 5, y - 3), (x + 3, y - 3), 1)
        if index % 4 == 0:
            for dx in (-5, 0, 5):
                top = y - rng.randrange(12, 31)
                pygame.draw.line(surface, (54, 89, 68), (x + dx, y + 3), (x + dx - 3, top), 2)
                pygame.draw.line(surface, (136, 122, 76), (x + dx - 3, top - 4), (x + dx - 3, top + 3), 3)


def forest_floor(surface, exclusion):
    """Place small grounded details only outside roads, ponds and machinery."""
    rng = random.Random(601)
    footprint = pygame.mask.Mask((36, 24), fill=True)
    width, height = surface.get_size()
    for _ in range(1750):
        x, y = rng.randrange(60, width - 60), rng.randrange(200, height - 110)
        if exclusion.overlap(footprint, (x - 18, y - 15)) is not None:
            continue
        # The southern survey basin has broad fern beds and marsh flowers.
        marsh = 1940 < x < 3090 and y > 1120
        if marsh or rng.random() < .38:
            for offset in (-8, 0, 9):
                tip = (x + offset, y - 13 - abs(offset) // 2)
                pygame.draw.line(surface, (63, 103, 74), (x, y), tip, 2)
                for t in (.35, .65):
                    xx, yy = round(x + offset * t), round(y + (tip[1] - y) * t)
                    pygame.draw.line(surface, (123, 151, 94), (xx - 4, yy - 3), (xx + 4, yy + 1), 2)
        elif rng.random() < .24:
            pygame.draw.ellipse(surface, (76, 98, 70), (x - 12, y - 3, 28, 9))
            pygame.draw.line(surface, (121, 94, 61), (x - 11, y - 5), (x + 12, y - 1), 6)
            pygame.draw.line(surface, (166, 133, 84), (x - 11, y - 7), (x + 11, y - 3), 2)
        else:
            for dx, dy in ((-6, 0), (0, -7), (7, -3)):
                pygame.draw.line(surface, (65, 106, 72), (x + dx, y), (x + dx, y + dy - 7), 1)
                pygame.draw.circle(surface, (204, 171, 140), (x + dx, y + dy - 8), 3)
                pygame.draw.circle(surface, (235, 211, 153), (x + dx, y + dy - 8), 1)


def ruin(surface, x, y, variant=0):
    """Broken service masonry, drawn within the existing ruin footprint."""
    pygame.draw.ellipse(surface, (72, 96, 70), (x - 39, y + 7, 88, 18))
    for col, height in enumerate((33, 20, 41)):
        xx = x - 36 + col * 24
        for yy in range(y - height, y + 12, 13):
            pygame.draw.rect(surface, (99, 113, 96), (xx, yy, 23, 12))
            pygame.draw.rect(surface, (148, 151, 120), (xx + 2, yy + 1, 20, 9))
            pygame.draw.line(surface, (184, 179, 141), (xx + 3, yy + 1), (xx + 19, yy + 1), 2)
    pygame.draw.lines(surface, (68, 91, 72), False, ((x - 30, y - 12), (x - 18, y - 2), (x - 22, y + 9)), 2)
    for dx in (-33, -5, 19):
        pygame.draw.ellipse(surface, (77, 115, 74), (x + dx, y + 3, 19, 8))
    if variant % 2:
        pygame.draw.rect(surface, (47, 75, 72), (x - 8, y - 13, 19, 16))
        pygame.draw.circle(surface, (170, 143, 85), (x + 1, y - 5), 6, 2)


def _wheel(surface, center, radius, color):
    cx, cy = center
    pygame.draw.circle(surface, (22, 34, 35), center, radius + 10)
    pygame.draw.circle(surface, color, center, radius, 9)
    for index in range(12):
        angle = index * math.tau / 12
        a = (round(cx + math.cos(angle) * 23), round(cy + math.sin(angle) * 23))
        b = (round(cx + math.cos(angle) * (radius - 5)), round(cy + math.sin(angle) * (radius - 5)))
        pygame.draw.line(surface, color, a, b, 8)
    pygame.draw.circle(surface, color, center, 23)
    pygame.draw.circle(surface, (26, 41, 41), center, 10)


def _window(surface, rect, high, seed):
    rng = random.Random(seed)
    pygame.draw.rect(surface, (19, 34, 38), rect.inflate(24, 24), border_radius=70)
    pygame.draw.rect(surface, (76, 91, 84), rect.inflate(12, 12), 5, border_radius=65)
    glass = pygame.Surface(rect.size)
    for y in range(0, rect.height, 4):
        t = y / rect.height
        color = tuple(round(a + (b - a) * t) for a, b in zip((111, 151, 155) if high else (71, 112, 119), (176, 177, 143) if high else (126, 151, 131)))
        pygame.draw.rect(glass, color, (0, y, rect.width, 4))
    for layer, color in enumerate(((98, 133, 137), (71, 111, 116), (49, 88, 96))):
        points = [(0, rect.height)]
        for x in range(-20, rect.width + 35, 35):
            points.append((x, rect.height * (.45 + layer * .14) - rng.randrange(15, 65)))
        points.append((rect.width, rect.height))
        pygame.draw.polygon(glass, color, points)
    mask = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255), mask.get_rect(), border_radius=60)
    mask.blit(glass, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    surface.blit(mask, rect)
    for xx in (rect.centerx - 3,):
        pygame.draw.rect(surface, (43, 63, 62), (xx, rect.top, 7, rect.height))
        pygame.draw.line(surface, (143, 152, 126), (xx, rect.top + 12), (xx, rect.bottom - 5), 1)
    for yy in (rect.top + 95, rect.top + rect.height * 2 // 3):
        pygame.draw.rect(surface, (42, 61, 61), (rect.left, yy, rect.width, 7))
    pygame.draw.rect(surface, (103, 118, 104), (rect.left - 15, rect.bottom - 2, rect.width + 30, 12))
    pygame.draw.line(surface, (156, 158, 125), (rect.left - 13, rect.bottom - 2), (rect.right + 12, rect.bottom - 2), 3)


def tower_backdrop(size, middle_y, upper_y):
    """Layered masonry, iron driveworks and an airy condenser crown."""
    width, height = size
    surface = pygame.Surface(size)
    rng = random.Random(225)
    palettes = (
        (0, upper_y, (41, 65, 67), ((47, 72, 73), (50, 75, 75), (43, 68, 70))),
        (upper_y, middle_y, (25, 40, 43), ((32, 49, 50), (36, 51, 50), (30, 46, 48))),
        (middle_y, height, (48, 42, 36), ((62, 51, 40), (57, 48, 38), (66, 54, 42))),
    )
    for top, bottom, mortar, bricks in palettes:
        pygame.draw.rect(surface, mortar, (0, top, width, bottom - top))
        for y in range(top, bottom, 32):
            for x in range(-95, width, 96):
                xx = x + (48 if y // 32 % 2 else 0)
                color = rng.choice(bricks)
                pygame.draw.rect(surface, color, (xx, y + 1, 92, 28), border_radius=2)
                if rng.random() < .35:
                    pygame.draw.line(surface, tuple(c + 5 for c in color), (xx + 6, y + 4), (xx + 61, y + 4), 1)
        # Tall structural piers create depth and prevent a flat wallpaper effect.
        for x in (20, 450, 940, 1390):
            pygame.draw.rect(surface, tuple(max(0, c - 5) for c in mortar), (x, top, 40, bottom - top))
            pygame.draw.line(surface, tuple(c + 14 for c in mortar), (x, top), (x, bottom), 3)
    # Crown windows open onto mountains; their landscape is safely behind platforms.
    for y in range(230, upper_y - 200, 530):
        for x in (120, 1040):
            _window(surface, pygame.Rect(x, y, 240, 340), True, x + y)
    # Large vertical condensers and bundled return pipes, cool and quiet.
    for x in (480, 870):
        pygame.draw.rect(surface, (26, 48, 52), (x, 130, 75, upper_y - 190), border_radius=32)
        pygame.draw.rect(surface, (60, 85, 84), (x + 8, 137, 53, upper_y - 205), border_radius=23)
        pygame.draw.rect(surface, (78, 108, 101), (x + 13, 170, 6, upper_y - 280))
        for y in range(185, upper_y - 80, 180):
            pygame.draw.rect(surface, (100, 106, 83), (x - 4, y, 81, 12))
            for xx in (x + 5, x + 63):
                pygame.draw.circle(surface, (156, 147, 104), (xx, y + 6), 2)
    # Driveworks gear trains and belts sit in dark service recesses.
    for y in range(upper_y + 150, middle_y - 100, 560):
        for x in (290, 1080):
            pygame.draw.rect(surface, (19, 31, 34), (x - 165, y - 90, 330, 480), border_radius=45)
            for xx in (x - 125, x + 125):
                pygame.draw.line(surface, (49, 57, 48), (xx, y + 20), (xx, y + 260), 14)
                pygame.draw.line(surface, (67, 69, 53), (xx - 3, y + 20), (xx - 3, y + 260), 2)
            _wheel(surface, (x, y + 20), 130, (67, 78, 65))
            _wheel(surface, (x, y + 260), 105, (62, 74, 63))
            for xx in (x - 160, x + 150):
                for yy in (y - 64, y + 350):
                    pygame.draw.rect(surface, (80, 86, 68), (xx, yy, 9, 9))
    # Boiler galleries: hot furnace mouths, reinforced arches and sooted masonry.
    for y in range(middle_y + 180, height - 100, 540):
        for x in (130, 1010):
            rect = pygame.Rect(x, y, 280, 250)
            pygame.draw.rect(surface, (32, 31, 28), rect.inflate(24, 24), border_radius=65)
            pygame.draw.rect(surface, (88, 69, 48), rect.inflate(14, 14), 8, border_radius=62)
            pygame.draw.rect(surface, (67, 46, 30), rect, border_radius=55)
            glow = pygame.Surface((280, 250), pygame.SRCALPHA)
            for radius in range(113, 15, -13):
                pygame.draw.circle(glow, (218, 126, 48, 20), (140, 190), radius)
            surface.blit(glow, rect)
            for xx in range(rect.left + 18, rect.right - 10, 25):
                pygame.draw.line(surface, (27, 31, 29), (xx, rect.top + 42), (xx, rect.bottom - 12), 9)
                pygame.draw.line(surface, (101, 78, 48), (xx - 2, rect.top + 42), (xx - 2, rect.bottom - 12), 2)
            pygame.draw.rect(surface, (98, 72, 45), (rect.left - 8, rect.bottom - 10, rect.width + 16, 18))
            for xx in range(rect.left + 4, rect.right, 40):
                pygame.draw.circle(surface, (164, 125, 67), (xx, rect.bottom - 1), 3)
    # Recessed courses sit below the maintenance floor, with no bright walkable lip.
    for y in (middle_y, upper_y):
        pygame.draw.rect(surface, (20, 33, 34), (0, y + 92, width, 24))
        pygame.draw.rect(surface, (35, 48, 45), (0, y + 98, width, 10))
        for x in range(30, width, 60):
            pygame.draw.circle(surface, (56, 65, 52), (x, y + 104), 2)
    return surface
