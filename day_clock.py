"""A rotating day/night disc driven entirely by the saved village clock."""
import math

import pygame

import town_atmosphere
from ui_theme import COPPER, GOLD, INK, PAPER, TEAL, draw_panel


CLOCK_RECT = pygame.Rect(208, 16, 104, 108)
DAY_FACE = (234, 195, 112)
NIGHT_FACE = (42, 73, 88)

# A full turn per economic day, with most play time in the light half. The
# compressed night occupies the last/first fifteen seconds. Hermite tangents
# keep the rotation smooth at sunrise, sunset and the day-number boundary.
PHASE_STOPS = ((0., 0., 4.), (.085, .25, .7), (.5, .5, .4),
               (.915, .75, .7), (1., 1., 4.))


def cycle_phase(progress):
    """Unwrapped turn: 0/1 midnight, .25 sunrise, .5 noon, .75 sunset."""
    progress = max(0., min(1., progress))
    for (start, a, slope_a), (end, b, slope_b) in zip(PHASE_STOPS, PHASE_STOPS[1:]):
        if progress <= end:
            t = (progress-start)/(end-start)
            return ((2*t**3-3*t*t+1)*a + (t**3-2*t*t+t)*(end-start)*slope_a
                    + (-2*t**3+3*t*t)*b + (t**3-t*t)*(end-start)*slope_b)
    return 1.


def phase_name(progress):
    if progress < .085:
        return 'Dawn'
    if progress < .75:
        return 'Day'
    if progress < .915:
        return 'Dusk'
    return 'Night'


def disc(progress):
    """Draw at half size then enlarge exactly, preserving hard pixel edges."""
    result = pygame.Surface((41, 41), pygame.SRCALPHA)
    angle = (cycle_phase(progress) % 1.)*math.tau
    sine, cosine = math.sin(angle), math.cos(angle)
    radius, center = 17, 20
    pygame.draw.circle(result, INK, (center, center), 20)
    pygame.draw.circle(result, COPPER, (center, center), 19)
    pygame.draw.circle(result, GOLD, (center, center), 18)
    # The face itself rotates; its surrounding copper mounting remains still.
    for y in range(-radius, radius+1):
        for x in range(-radius, radius+1):
            if x*x+y*y <= radius*radius:
                result.set_at((center+x, center+y),
                              DAY_FACE if x*sine+y*cosine >= 0 else NIGHT_FACE)

    def point(x, y):
        return round(center+x*cosine+y*sine), round(center-x*sine+y*cosine)

    sun = point(0, 9)
    pygame.draw.circle(result, (255, 238, 171), sun, 3)
    for x, y in ((0, 4), (0, 14), (-5, 9), (5, 9)):
        pygame.draw.rect(result, (255, 238, 171), (*point(x, y), 1, 1))
    moon = point(0, -9)
    pygame.draw.circle(result, (230, 235, 211), moon, 4)
    pygame.draw.circle(result, NIGHT_FACE, point(2, -10), 3)
    for x, y in ((-8, -8), (9, -7), (-5, -14), (7, -12)):
        result.set_at(point(x, y), (180, 210, 207))
    pygame.draw.circle(result, INK, (center, center), 2)
    pygame.draw.rect(result, GOLD, (center, center-1, 1, 2))
    return pygame.transform.scale(result, (82, 82))


def draw(surface, village, font, rect=None):
    """Fixed top pointer; optional bounds allow the same instrument in regions."""
    rect = pygame.Rect(rect or CLOCK_RECT)
    progress = town_atmosphere.clock_progress(village)
    draw_panel(surface, rect)
    center = (rect.centerx, rect.top+43)
    face = disc(progress)
    surface.blit(face, face.get_rect(center=center))
    # A dark outline makes the pointer legible over either half of the disc.
    x, y = center[0], rect.top+2
    pygame.draw.polygon(surface, INK, ((x-7, y), (x+7, y), (x, y+13)))
    pygame.draw.polygon(surface, PAPER, ((x-4, y+2), (x+4, y+2), (x, y+9)))
    label = font.render(phase_name(progress), True, TEAL)
    surface.blit(label, label.get_rect(center=(rect.centerx, rect.bottom-13)))
