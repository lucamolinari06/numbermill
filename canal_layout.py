"""Reedhaven's authored banks, routes and footprints share one geometry.

The canal and northeast landing follow the player's layout sketch. Actor
positions use the same above-feet anchor as Copperside and Mosswater.
"""
import math
import pygame
from water_geometry import contains, smooth_polygon

WIDTH, HEIGHT = 2800, 1700
FOOT_OFFSET = 18
ARRIVAL = (2370., 460.)
WATER = smooth_polygon(((-150, 285), (400, 320), (1100, 330), (1590, 365),
    (1780, 405), (1860, 520), (1890, 690), (2020, 725), (2150, 680),
    (2270, 510), (2400, 420), (2850, 410), (2900, 1350), (2520, 1370),
    (2220, 1310), (1990, 1180), (1850, 990), (1830, 770), (1750, 680),
    (1580, 620), (1100, 550), (350, 540), (-150, 585)), 2)
BRIDGE = pygame.Rect(795, 230, 130, 430)
DOCK = pygame.Rect(2325, 385, 95, 250)
WALKWAYS = (BRIDGE, DOCK)

# Ground-contact anchor, width, height, architectural identity.
BUILDINGS = {
    'lockhouse': ((430, 835), 254, 142, 'lockhouse'),
    'market': ((1060, 840), 270, 145, 'market'),
    'chandlery': ((1510, 855), 286, 124, 'chandlery'),
    'west_home': ((650, 1260), 210, 130, 'home'),
    'east_home': ((1270, 1280), 225, 130, 'home'),
    'boathouse': ((2580, 330), 240, 135, 'boathouse'),
}
POINTS = {'boat': (2370, 550), 'Mara': (2470, 400), 'Ivo': (450, 890),
          'Sela': (1090, 895), 'Orrin': (1500, 920),
          'cistern': (980, 1055), 'waterworks': (230, 685)}
RESIDENTS = {
    'Mara': dict(coat=(169, 102, 67), role='Boatwright', action='notes'),
    'Ivo': dict(coat=(71, 112, 119), role='Lockkeeper', action='inspect'),
    'Sela': dict(coat=(151, 118, 71), role='Canal trader', action='basket'),
    'Orrin': dict(coat=(102, 116, 84), role='Water surveyor', action='notes'),
}
# Route mouths flare into the square, while narrow towpaths hug the canal.
PATHS = (((2390, 410), (2390, 265), (2050, 245), (1630, 220), (1180, 205), (860, 210)),
         ((860, 210), (860, 660), (850, 950), (980, 1080)),
         ((230, 685), (430, 650), (670, 650), (850, 660), (1150, 665), (1490, 690), (1680, 750)),
         ((610, 650), (610, 915), (850, 950), (1100, 950), (1510, 970), (1680, 1100)),
         ((1060, 840), (1060, 950)), ((1510, 855), (1510, 970)),
         ((650, 1260), (650, 1340), (980, 1350), (980, 1080)),
         ((1270, 1280), (1270, 1350), (980, 1350)),
         ((980, 1080), (1510, 1100), (1680, 1100)),
         ((2390, 365), (2580, 365)),
         ((430, 835), (430, 915), (610, 915)))
SQUARE = pygame.Rect(880, 895, 370, 245)


def distance_to_path(point):
    x, y = point
    best = float('inf')
    for path in PATHS:
        for (ax, ay), (bx, by) in zip(path, path[1:]):
            ux, uy = bx-ax, by-ay
            blend = max(0., min(1., ((x-ax)*ux+(y-ay)*uy)/(ux*ux+uy*uy)))
            best = min(best, math.hypot(x-ax-blend*ux, y-ay-blend*uy))
    return best


def building_rect(key):
    (x, y), width, height, _ = BUILDINGS[key]
    return pygame.Rect(x-width//2, y-height, width, height)


def wet(x, y):
    return contains((x, y), WATER)


def blocked(x, y):
    foot = (x, y+FOOT_OFFSET)
    if not (30 <= foot[0] <= WIDTH-30 and 45 <= foot[1] <= HEIGHT-30):
        return True
    if any(building_rect(key).inflate(12, 8).collidepoint(foot) for key in BUILDINGS):
        return True
    (mx,my),market_width,_,_=BUILDINGS['market']
    if pygame.Rect(mx-market_width//2+10,my-3,market_width-20,31).inflate(12,8).collidepoint(foot):
        return True
    # Physical stone cistern, not a painted obstacle.
    if pygame.Rect(936, 986, 88, 52).inflate(10, 8).collidepoint(foot):
        return True
    if any(area.inflate(-16, -8).collidepoint(foot) for area in WALKWAYS):
        return False
    return any(wet(foot[0]+dx, foot[1]+dy) for dx, dy in ((0,0),(-8,0),(8,0),(0,5)))


def safe_position(position):
    try:
        x, y = map(float, position)
        if math.isfinite(x) and math.isfinite(y) and not blocked(x,y):
            return [x,y]
    except (ValueError, TypeError):
        pass
    return list(ARRIVAL)


def camera(position, size=(1280,760)):
    return (round(max(0, min(WIDTH-size[0], position[0]-size[0]/2))),
            round(max(0, min(HEIGHT-size[1], position[1]-size[1]*.53))))
