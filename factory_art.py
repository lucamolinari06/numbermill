"""Workshop scenery and hand-drawn equipment; no simulation state lives here."""
import math
import random
from functools import lru_cache

import pygame

IRON = (38, 56, 55)
IRON_LIGHT = (100, 128, 119)
TEAL = (59, 111, 103)
BRASS = (198, 151, 82)
BRASS_LIGHT = (237, 200, 126)
COPPER = (164, 94, 61)
PAPER = (243, 232, 204)


def plate(surface, rect, color=TEAL, radius=2):
    rect = pygame.Rect(rect)
    pygame.draw.rect(surface, IRON, rect.move(1, 3), border_radius=radius)
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    bright = tuple(min(255, c + 27) for c in color)
    pygame.draw.line(surface, bright, (rect.left + 2, rect.top + 1), (rect.right - 3, rect.top + 1))
    pygame.draw.line(surface, tuple(max(0, c - 32) for c in color),
                     (rect.right - 2, rect.top + 3), (rect.right - 2, rect.bottom - 2), 2)


def gauge(surface, center, radius=7, phase=.4):
    x, y = center
    pygame.draw.circle(surface, IRON, (x, y + 1), radius + 2)
    pygame.draw.circle(surface, BRASS, center, radius + 1)
    pygame.draw.circle(surface, PAPER, center, radius - 1)
    for angle in (-2.4, -1.6, -.8, 0):
        pygame.draw.circle(surface, (126, 110, 77),
                           (x + round(math.cos(angle) * (radius - 3)), y + round(math.sin(angle) * (radius - 3))), 1)
    angle = -2.4 + phase * 2.4
    pygame.draw.line(surface, COPPER, center,
                     (x + round(math.cos(angle) * (radius - 2)), y + round(math.sin(angle) * (radius - 2))), 1)
    pygame.draw.circle(surface, IRON, center, 1)


def wheel(surface, center, radius, phase=0):
    x, y = center
    pygame.draw.circle(surface, IRON, (x + 1, y + 1), radius + 1)
    pygame.draw.circle(surface, BRASS, center, radius, 2)
    for i in range(4):
        a = phase + i * math.pi / 2
        pygame.draw.line(surface, BRASS, center,
                         (x + round(math.cos(a) * (radius - 2)), y + round(math.sin(a) * (radius - 2))), 2)
    pygame.draw.circle(surface, BRASS_LIGHT, center, 2)


def crate(surface, rect):
    rect = pygame.Rect(rect)
    plate(surface, rect, (153, 110, 65), 1)
    pygame.draw.rect(surface, (83, 65, 45), rect, 1)
    for offset in (8, 16):
        pygame.draw.line(surface, (111, 79, 46), (rect.x + 1, rect.y + offset), (rect.right - 2, rect.y + offset))
    pygame.draw.line(surface, (214, 172, 105), (rect.x + 3, rect.y + 3), (rect.right - 4, rect.bottom - 4), 3)
    for x, y in ((rect.x + 3, rect.y + 3), (rect.right - 4, rect.bottom - 4)):
        pygame.draw.circle(surface, IRON, (x, y), 1)


def equipment(surface, kind, rect, *, working=False, value=0, phase=0):
    """Furniture remains inside the original 76 by 64 placement cell."""
    cx, cy = pygame.Rect(rect).center
    pygame.draw.ellipse(surface, (86, 73, 54), (cx - 28, cy + 19, 56, 10))
    speed = phase * 5 if working else .45
    if kind == "bench":
        for x in (cx - 25, cx + 17):
            plate(surface, (x, cy + 4, 8, 20), (103, 71, 47), 1)
        plate(surface, (cx - 31, cy - 1, 62, 9), (174, 119, 65), 1)
        pygame.draw.line(surface, BRASS_LIGHT, (cx - 28, cy), (cx + 27, cy))
        plate(surface, (cx - 24, cy - 25, 31, 24))
        pygame.draw.rect(surface, IRON, (cx - 17, cy - 20, 18, 18))
        travel = round((math.sin(speed) + 1) * 4) if working else 2
        plate(surface, (cx - 11, cy - 26 + travel, 6, 15), COPPER, 1)
        plate(surface, (cx - 17, cy - 13 + travel, 18, 4), BRASS, 1)
        wheel(surface, (cx + 21, cy - 12), 10, speed)
        plate(surface, (cx + 8, cy - 3, 14, 4), IRON_LIGHT, 1)
        pygame.draw.circle(surface, (173, 224, 154) if working else (80, 97, 79), (cx - 20, cy - 20), 2)
        pygame.draw.line(surface, IRON, (cx - 21, cy + 17), (cx + 20, cy + 17), 3)
    elif kind == "press":
        plate(surface, (cx - 28, cy + 15, 56, 9), IRON_LIGHT)
        for x in (cx - 23, cx + 17):
            plate(surface, (x, cy - 25, 7, 39))
        plate(surface, (cx - 26, cy - 27, 52, 8))
        travel = round((math.sin(speed) + 1) * 5) if working else 2
        plate(surface, (cx - 5, cy - 26, 10, 17 + travel), COPPER, 1)
        plate(surface, (cx - 16, cy - 10 + travel, 32, 6), BRASS, 1)
        plate(surface, (cx - 19, cy + 10, 38, 4), IRON_LIGHT, 1)
        pygame.draw.line(surface, PAPER, (cx - 14, cy + 9), (cx + 14, cy + 9), 2)
        gauge(surface, (cx + 19, cy - 19), 5, .5)
    elif kind == "lathe":
        for x in (cx - 25, cx + 17):
            plate(surface, (x, cy + 4, 9, 20), IRON_LIGHT)
        plate(surface, (cx - 29, cy - 1, 58, 12))
        pygame.draw.line(surface, BRASS, (cx - 26, cy + 3), (cx + 26, cy + 3), 2)
        plate(surface, (cx - 27, cy - 23, 17, 23))
        plate(surface, (cx + 14, cy - 18, 12, 18))
        pygame.draw.line(surface, IRON_LIGHT, (cx - 12, cy - 11), (cx + 17, cy - 11), 7)
        pygame.draw.line(surface, PAPER, (cx - 10, cy - 13), (cx + 16, cy - 13))
        for dx in (-5, 7):
            pygame.draw.line(surface, COPPER, (cx + dx, cy - 14), (cx + dx + 3, cy - 8), 2)
        wheel(surface, (cx - 19, cy - 12), 7, speed)
        wheel(surface, (cx + 5, cy + 7), 6, speed * .4)
        if working and math.sin(speed) > .5:
            pygame.draw.line(surface, BRASS_LIGHT, (cx + 5, cy - 7), (cx + 9, cy - 3))
    elif kind == "precision_machine":
        plate(surface, (cx - 26, cy + 15, 52, 9), IRON_LIGHT)
        plate(surface, (cx - 24, cy - 27, 48, 42))
        pygame.draw.rect(surface, IRON, (cx - 18, cy - 19, 36, 30), border_radius=4)
        for x in (cx - 16, cx + 15):
            pygame.draw.line(surface, BRASS, (x, cy - 17), (x, cy + 8), 2)
        wheel(surface, (cx, cy + 1), 11, speed * .6)
        slide = round(math.sin(speed) * 7) if working else 0
        plate(surface, (cx - 6 + slide, cy - 23, 12, 11), COPPER)
        pygame.draw.circle(surface, (156, 224, 211), (cx + slide, cy - 17), 3)
        if working:
            pygame.draw.line(surface, (148, 201, 170), (cx + slide, cy - 12), (cx + slide, cy - 5))
        for x in (cx - 20, cx + 20):
            pygame.draw.circle(surface, BRASS_LIGHT, (x, cy - 24), 1)
    elif kind == "storage":
        for x in (cx - 29, cx + 25):
            plate(surface, (x, cy - 28, 5, 53), IRON_LIGHT, 1)
        for y in (cy - 4, cy + 20):
            plate(surface, (cx - 29, y, 59, 4), (131, 92, 56), 1)
        crate(surface, (cx - 24, cy - 26, 24, 22))
        crate(surface, (cx + 3, cy - 21, 21, 17))
        crate(surface, (cx - 20, cy, 25, 20))
        plate(surface, (cx + 9, cy + 4, 13, 14), (83, 126, 115), 1)
        pygame.draw.rect(surface, PAPER, (cx - 16, cy + 5, 9, 5))
    elif kind == "controller":
        plate(surface, (cx - 23, cy + 17, 46, 7), IRON_LIGHT)
        plate(surface, (cx - 25, cy - 28, 50, 47), COPPER, 4)
        plate(surface, (cx - 20, cy - 23, 40, 37), TEAL, 2)
        gauge(surface, (cx - 8, cy - 12), 8, .38 + (.15 * math.sin(speed) if working else 0))
        for i, color in enumerate((BRASS_LIGHT, (150, 208, 170))):
            pygame.draw.circle(surface, IRON, (cx + 13, cy - 17 + i * 9), 4)
            pygame.draw.circle(surface, color, (cx + 13, cy - 17 + i * 9), 2)
        for y in (cy + 2, cy + 7):
            pygame.draw.line(surface, IRON, (cx - 12, y), (cx + 14, y), 2)
        for x in (cx - 19, cx, cx + 19):
            plate(surface, (x - 3, cy + 15, 6, 6), BRASS, 1)
    elif kind in ("buyer", "seller"):
        incoming = kind == "buyer"
        color = TEAL if incoming else COPPER
        plate(surface, (cx - 28, cy + 13, 56, 11), IRON_LIGHT)
        for x in range(cx - 22, cx + 24, 8):
            pygame.draw.circle(surface, IRON, (x, cy + 18), 3)
            pygame.draw.circle(surface, BRASS, (x, cy + 18), 1)
        plate(surface, (cx - 25, cy - 24, 50, 37), color, 3)
        pygame.draw.rect(surface, (221, 218, 182), (cx - 18, cy - 17, 36, 18), border_radius=2)
        direction = 1 if incoming else -1
        pygame.draw.line(surface, color, (cx - 11, cy - 8), (cx + 11, cy - 8), 3)
        tip = cx + direction * 13
        pygame.draw.polygon(surface, color, ((tip, cy - 8), (tip - direction * 8, cy - 14), (tip - direction * 8, cy - 2)))
        for x in (cx - 13, cx, cx + 13):
            pygame.draw.circle(surface, IRON, (x, cy + 7), 3)
            pygame.draw.circle(surface, BRASS_LIGHT, (x, cy + 7), 1)
    elif kind == "display":
        plate(surface, (cx - 4, cy + 5, 8, 16), COPPER)
        plate(surface, (cx - 20, cy + 20, 40, 5), IRON_LIGHT)
        plate(surface, (cx - 29, cy - 27, 58, 36), COPPER, 4)
        pygame.draw.rect(surface, (17, 40, 38), (cx - 24, cy - 22, 48, 25), border_radius=3)
        pygame.draw.line(surface, (57, 94, 77), (cx - 21, cy - 19), (cx + 19, cy - 19))
        font = display_font()
        digits = str(max(0, int(value))).rjust(2, "0")
        image = font.render(digits, False, (175, 228, 170))
        if image.get_width() > 43:
            image = pygame.transform.scale(image, (43, image.get_height()))
        surface.blit(image, image.get_rect(center=(cx, cy - 9)))
        pygame.draw.circle(surface, BRASS_LIGHT, (cx + 24, cy + 4), 1)


def display_font():
    from ui_theme import make_font
    return make_font(17, bold=True)


@lru_cache(maxsize=1)
def room_background():
    """A cached physical room; grid coordinates and usable area stay unchanged."""
    s = pygame.Surface((710, 466))
    s.fill((35, 51, 48))
    # Shallow rear wall: limewashed brick, copper steam main and tall windows.
    for y in range(0, 65, 15):
        for x in range(-30, 710, 54):
            rect = (x + (27 if y // 15 % 2 else 0), y, 52, 13)
            pygame.draw.rect(s, (77, 94, 82) if y % 2 else (83, 100, 86), rect)
    pygame.draw.line(s, (43, 57, 50), (0, 61), (709, 61), 7)
    pygame.draw.line(s, (170, 118, 71), (0, 59), (709, 59), 3)
    for x in (430, 574):
        pygame.draw.rect(s, (36, 48, 42), (x - 4, 7, 119, 49))
        pygame.draw.rect(s, (150, 177, 152), (x, 10, 111, 40))
        pygame.draw.rect(s, (180, 196, 161), (x + 2, 12, 107, 17))
        pygame.draw.polygon(s, (116, 150, 127), ((x + 2, 47), (x + 31, 26), (x + 55, 45), (x + 80, 32), (x + 108, 47)))
        for xx in (x + 35, x + 74):
            pygame.draw.line(s, (94, 75, 52), (xx, 10), (xx, 50), 4)
        pygame.draw.line(s, (94, 75, 52), (x, 30), (x + 111, 30), 3)
        pygame.draw.rect(s, (176, 127, 75), (x - 5, 50, 121, 5))
    pygame.draw.rect(s, (73, 54, 40), (5, 64, 700, 396), border_radius=3)
    pygame.draw.rect(s, (193, 144, 83), (9, 67, 692, 390), 2, border_radius=2)
    rng = random.Random(412)
    for row in range(18):
        y = 70 + row * 22
        for col in range(-1, 6):
            x = 12 + col * 152 + (76 if row % 2 else 0)
            r = pygame.Rect(x, y, 150, 21).clip(pygame.Rect(12, 70, 684, 384))
            shade = rng.choice(((158, 120, 77), (164, 126, 80), (170, 132, 86), (160, 122, 79)))
            pygame.draw.rect(s, shade, r)
            if r.w > 12:
                pygame.draw.line(s, (185, 143, 91), (r.x + 2, r.y + 2), (r.right - 3, r.y + 2))
                for offset in (7, 13, 17):
                    start = r.x + rng.randrange(2, max(3, r.w // 3))
                    end = min(r.right - 3, start + rng.randrange(15, 70))
                    if y + offset < r.bottom:
                        pygame.draw.line(s, (146, 107, 68), (start, y + offset), (end, y + offset))
                for xx in (r.x + 4, r.right - 5):
                    pygame.draw.circle(s, (99, 80, 56), (xx, r.centery), 1)
    # Fine registration marks preserve precise placement without a checkerboard.
    for row in range(7):
        for col in range(10):
            x, y = 12 + col * 76, 70 + row * 64
            pygame.draw.line(s, (114, 93, 63), (x - 3, y), (x + 3, y))
            pygame.draw.line(s, (114, 93, 63), (x, y - 3), (x, y + 3))
    # Broad daylight sits below the equipment, so it never masks a live signal.
    light = pygame.Surface(s.get_size(), pygame.SRCALPHA)
    for x in (430, 574):
        pygame.draw.polygon(light, (255, 222, 153, 16), ((x, 66), (x + 110, 66), (x - 5, 310), (x - 115, 310)))
    s.blit(light, (0, 0))
    return s


def room(surface, *, accumulator=False):
    surface.blit(room_background(), (62, 140))
    if accumulator:
        # The permanent tower reward has a physical place on the rear wall.
        x, y = 422, 170
        plate(surface, (x - 17, y - 24, 34, 46), COPPER, 7)
        plate(surface, (x - 12, y - 20, 24, 38), IRON_LIGHT, 6)
        for yy in (y - 14, y + 12):
            pygame.draw.rect(surface, BRASS, (x - 16, yy, 32, 4))
        gauge(surface, (x, y - 4), 7, .6)
        pygame.draw.lines(surface, BRASS, False, ((x - 16, y + 17), (x - 31, y + 17), (x - 31, y + 30)), 3)


def selection(surface, rect, color):
    rect = pygame.Rect(rect).inflate(-6, -6)
    for x, sign_x in ((rect.left, 1), (rect.right, -1)):
        for y, sign_y in ((rect.top, 1), (rect.bottom, -1)):
            pygame.draw.line(surface, color, (x, y), (x + sign_x * 12, y), 2)
            pygame.draw.line(surface, color, (x, y), (x, y + sign_y * 10), 2)
