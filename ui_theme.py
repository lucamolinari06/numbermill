"""Shared copper, ivory and teal presentation for every screen."""
import math
from pathlib import Path
import pygame

INK = (39, 51, 49)
MUTED = (94, 108, 101)
PAPER = (249, 240, 217)
CREAM = (232, 219, 187)
TEAL = (39, 107, 104)
COPPER = (165, 92, 57)
GOLD = (220, 171, 81)
DEEP_TEAL = (24, 49, 51)
_BACKDROPS = {}


class GameTypeface:
    """Readable squared lettering with one bundled family across the game."""

    def __init__(self, size, bold=False):
        filename = "ChakraPetch-SemiBold.ttf" if bold else "ChakraPetch-Medium.ttf"
        path = Path(__file__).resolve().parent / "assets" / "fonts" / filename
        self.base = pygame.font.Font(str(path), size)

    def render(self, value, antialias, color, background=None):
        return self.base.render(self.label(value), True, color, background)

    @staticmethod
    def label(value):
        # Use familiar font-compatible prompts instead of missing-glyph boxes.
        return str(value).translate(str.maketrans({"↑": "UP", "↓": "DOWN", "←": "<",
            "→": ">", "↔": "<>", "▶": ">", "◀": "<", "●": "*", "✓": "OK",
            "✕": "X", "×": "x", "−": "-", "–": "-", "—": "-", "…": "..."}))

    def size(self, value):
        return self.base.size(self.label(value))

    def get_height(self):
        return self.base.get_height()


def make_font(size, bold=False):
    """One legible retro-shaped family for every interface and world label."""
    return GameTypeface(size, bold)


def elide(font, value, width):
    value = str(value)
    if font.render(value, True, INK).get_width() <= width:
        return value
    while value and font.render(value + '...', True, INK).get_width() > width:
        value = value[:-1]
    return value.rstrip() + '...' if value else ''


def fit_text(surface, font, value, x, y, width, color=INK):
    image = font.render(elide(font, value, width), True, color)
    return surface.blit(image, (x, y))


def wrapped_text(surface, font, value, x, y, width, color=INK, line_height=22, max_lines=None):
    lines = []
    for paragraph in str(value).split('\n'):
        line = ''
        for word in paragraph.split():
            candidate = (line + ' ' + word).strip()
            if line and font.render(candidate, True, color).get_width() > width:
                lines.append(line)
                line = word
            else:
                line = candidate
        lines.append(line)
    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = elide(font, lines[-1] + ' ...', width)
    for i, line in enumerate(lines):
        fit_text(surface, font, line, x, y + i * line_height, width, color)
    return y + len(lines) * line_height


def draw_panel(surface, rect):
    rect = pygame.Rect(rect)
    pygame.draw.rect(surface, (20, 39, 40), rect.move(0, 5), border_radius=7)
    pygame.draw.rect(surface, PAPER, rect, border_radius=6)
    pygame.draw.rect(surface, (163, 136, 91), rect, 1, border_radius=6)
    pygame.draw.line(surface, (255, 249, 232), (rect.left + 9, rect.top + 2), (rect.right - 10, rect.top + 2))
    # Short copper corner bindings leave text areas quiet.
    for x, direction in ((rect.left + 3, 1), (rect.right - 4, -1)):
        for y, vertical in ((rect.top + 4, 1), (rect.bottom - 5, -1)):
            pygame.draw.line(surface, COPPER, (x, y), (x + direction * 9, y), 2)
            pygame.draw.line(surface, COPPER, (x, y), (x, y + vertical * 8), 2)


def backdrop(surface):
    size = surface.get_size()
    if size not in _BACKDROPS:
        art = pygame.Surface(size)
        width, height = size
        for y in range(height):
            t = y / max(1, height)
            pygame.draw.line(art, (round(31 - 9*t), round(59 - 17*t), round(59 - 13*t)), (0, y), (width, y))
        for x in range(20, width, 36):
            for y in range(20, height, 36):
                pygame.draw.circle(art, (48, 72, 68), (x, y), 1)
        for cx, cy, radius in ((80, 130, 170), (width-80, height-90, 210)):
            pygame.draw.circle(art, (44, 69, 64), (cx, cy), radius, 2)
            pygame.draw.circle(art, (43, 66, 61), (cx, cy), radius-22, 1)
            for angle in range(0, 360, 30):
                a = math.radians(angle)
                pygame.draw.line(art, (43, 66, 61), (cx, cy),
                                 (round(cx+math.cos(a)*radius), round(cy+math.sin(a)*radius)), 1)
        pygame.draw.rect(art, (104, 110, 78), art.get_rect().inflate(-26, -26), 1, border_radius=5)
        if len(_BACKDROPS) > 3:
            _BACKDROPS.clear()
        _BACKDROPS[size] = art
    surface.blit(_BACKDROPS[size], (0, 0))


def button_face(surface, rect, *, active=False, hover=False, pressed=False, enabled=True, danger=False, focused=False):
    rect = pygame.Rect(rect)
    fill = ((207, 207, 188) if not enabled else (164, 71, 57) if danger else
            (39, 107, 104) if active else (239, 218, 171) if hover else (235, 225, 199))
    face = rect.move(0, 1 if pressed else 0)
    pygame.draw.rect(surface, (87, 79, 58), rect.move(0, 3), border_radius=4)
    pygame.draw.rect(surface, fill, face, border_radius=4)
    pygame.draw.rect(surface, GOLD if hover or focused else (158, 142, 108), face, 1, border_radius=4)
    top = (117, 183, 165) if active else (253, 244, 221)
    if enabled:
        pygame.draw.line(surface, top, (face.left+5, face.top+2), (face.right-6, face.top+2))
    if focused:
        pygame.draw.rect(surface, GOLD, rect.inflate(6, 6), 2, border_radius=6)
    return PAPER if (active or danger) and enabled else INK if enabled else MUTED


def mill_seal(surface, center, radius=30):
    import math
    cx, cy = center
    pygame.draw.circle(surface, (229, 210, 169), center, radius + 7)
    pygame.draw.circle(surface, COPPER, center, radius + 7, 1)
    pygame.draw.circle(surface, TEAL, center, radius, 3)
    for i in range(8):
        a = i * math.pi / 4
        start = (round(cx + math.cos(a) * 9), round(cy + math.sin(a) * 9))
        end = (round(cx + math.cos(a) * (radius - 3)), round(cy + math.sin(a) * (radius - 3)))
        pygame.draw.line(surface, COPPER, start, end, 4)
    pygame.draw.circle(surface, GOLD, center, 9)
    pygame.draw.circle(surface, COPPER, center, 9, 2)
