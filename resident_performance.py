"""Read-only destination performances; movement and daily life remain authoritative."""
from dataclasses import dataclass
import math

import pygame

COATS = {
    'Boole': (39,107,104), 'Ada': (141,91,76), 'Bram': (96,119,87),
    'Agnes': (156,127,68), 'Dara': (91,115,148), 'Mely': (165,92,57),
    'Luca': (65,115,130), 'Grace': (122,94,138), 'Rowan': (109,132,94),
    'Saffron': (181,119,64), 'Felix': (85,112,135), 'Wren': (113,136,80),
    'Hugo': (131,100,77), 'Alma': (156,105,117), 'Perry': (101,119,124),
    'Cleo': (121,108,147), 'Jun': (143,132,81),
    'Iris': (126,137,82), 'Otto': (121,104,82), 'Tess': (75,129,122),
}


def coat_for(name):
    return COATS.get(name, (39,107,104))


@dataclass(frozen=True)
class Performance:
    action: str = 'idle'
    facing: str = 'south'


def facing_toward(origin, target, fallback='south'):
    dx, dy = target[0] - origin[0], target[1] - origin[1]
    if abs(dx) + abs(dy) < 1:
        return fallback
    return ('east' if dx > 0 else 'west') if abs(dx) > abs(dy) else ('south' if dy > 0 else 'north')


def performances(town, village, talking=None):
    """Use displayed arrival at the actual reserved slot, including wide groups.

    A stopped walker is not necessarily at work. Social gestures require an
    arrived companion at the same destination, not just a scheduled visit.
    Nothing here changes saved positions, needs, purchases or attendance.
    """
    from daily_life import FOOD_ACTIONS
    from town import LOCATIONS, GRACE_JOB_DESTINATIONS

    residents = {p['name']: p for p in village.citizens}
    points = {name: town.display_people.get(name, point) for name, point in town.people.items()
              if not town.indoors(name)}
    groups = {}
    for name, person in residents.items():
        groups.setdefault(person.get('destination') or person['home'], []).append(name)
    targets = {}
    for destination, names in groups.items():
        names.sort()
        for index, name in enumerate(names):
            center = LOCATIONS.get(destination, LOCATIONS[residents[name]['home']])
            targets[name] = (center[0] + (index - (len(names)-1)/2)*60,
                             center[1] + (20 if len(names) > 1 else 0))
    bid = next((key for key, offer in village.offers.items() if offer['status'] == 'bid'), None)
    targets['Grace'] = LOCATIONS[GRACE_JOB_DESTINATIONS.get(bid, 'grace_shop')]
    arrived = {name for name, point in points.items() if name in targets
               and name not in town.display_moving and math.dist(point, targets[name]) <= 3}
    result = {}
    for name, point in points.items():
        facing = town.display_facing.get(name, 'south')
        person = residents.get(name)
        action = 'idle'
        if person and person.get('activity') in FOOD_ACTIONS:
            action = 'basket'
        if name in arrived:
            if name == 'Grace':
                action = 'inspect'  # Her own shop or the actual bid destination.
            elif person:
                activity = person.get('activity')
                destination = person.get('destination') or person['home']
                firm = village.businesses.get(destination)
                if activity == 'working' and destination == person.get('workplace') and firm:
                    if firm.get('operating_state') == 'paused' or firm.get('workers', 0) <= 0:
                        action = 'inspect'
                    else:
                        action = ('sweep' if destination == 'market' else
                                  'tend' if destination == 'farm' else
                                  'inspect' if destination in ('bakery', 'east_bakery') else 'repair')
                elif activity in ('resting', 'at home') and destination == person['home']:
                    action = 'sit'
                elif activity in ('visiting neighbors', 'spending time with spouse'):
                    spouse = {'Mely': 'Luca', 'Luca': 'Mely'}.get(name)
                    company = [other for other in arrived if other != name and other in residents
                               and (residents[other].get('destination') or residents[other]['home']) == destination
                               and math.dist(point, points[other]) <= 140
                               and (activity != 'spending time with spouse' or other == spouse)]
                    if company:
                        other = min(company, key=lambda n: (math.dist(point, points[n]), n))
                        facing = facing_toward(point, points[other], facing)
                        action = 'sit_chat' if destination.startswith('home_') else 'chat'
        # A conversation turns a stationary actor toward Boole without rerouting.
        if name == talking and name not in town.display_moving:
            facing = facing_toward(point, (town.player_x, town.player_y), facing)
            action = 'chat'
        result[name] = Performance(action, facing)
    return result


def beat(seconds, name):
    """Authored held poses, staggered by identity rather than synchronized sine waves."""
    return int((seconds + sum(map(ord, name)) * .037) * 2) % 4


def hand_offsets(action, facing, frame):
    side = facing in ('east', 'west')
    sign = -1 if facing == 'west' else 1
    hands = [(-13, 2), (13, 2)]
    active = 0 if sign < 0 else 1
    if action in ('repair', 'tend', 'sweep'):
        hands[active] = (sign * (13 + (3 if frame in (1, 2) else 0)), -4 if frame == 1 else 2)
        if action == 'sweep':
            hands[1-active] = (sign * 8, -5)
    elif action == 'inspect':
        hands = [(sign*6, -7), (sign*15, -5)] if side else [(-8, -5), (9, -5)]
        if facing == 'north':
            hands = [(-8, 0), (19, -5)]
    elif action in ('chat', 'sit_chat') and frame in (1, 2):
        hands[active] = (sign*18, -9 if frame == 1 else -6)
    elif action in ('sit', 'sit_chat'):
        hands = [(-8, 6), (8, 6)]
    elif action == 'basket':
        hands[active] = (sign*15, 1)
    return hands


def stool(surface, x, y):
    pygame.draw.rect(surface, (82, 64, 47), (x-16, y+12, 32, 5))
    pygame.draw.rect(surface, (164, 121, 72), (x-15, y+11, 30, 3))
    for dx in (-14, 12):
        pygame.draw.rect(surface, (103, 76, 49), (x+dx, y+16, 3, 6))


def prop(surface, x, y, action, facing, frame, hands):
    """Props attach to posed hands and never imply unsimulated goods or rewards."""
    sign = -1 if facing == 'west' else 1
    hx, hy = hands[0 if sign < 0 else 1]
    hx, hy = x+hx, y+hy+2
    wood, brass, metal = (148, 105, 61), (216, 174, 98), (156, 176, 162)
    if action == 'basket':
        bx = hx-8
        pygame.draw.lines(surface, (101, 74, 47), False, [(hx-6,hy+5),(hx-6,hy-2),(hx+5,hy-2),(hx+5,hy+5)], 2)
        pygame.draw.rect(surface, wood, (bx,hy+4,16,10))
        pygame.draw.rect(surface, brass, (bx,hy+4,16,2))
        for dx in (3,7,11):
            pygame.draw.line(surface, (111,80,49), (bx+dx,hy+7), (bx+dx,hy+12))
    elif action == 'repair':
        tip = (hx+sign*3, hy-11+(3 if frame == 2 else 0))
        pygame.draw.line(surface, wood, (hx,hy), tip, 3)
        pygame.draw.line(surface, metal, (tip[0]-4,tip[1]), (tip[0]+4,tip[1]), 4)
    elif action in ('sweep', 'tend'):
        tip = (hx+sign*(2 if frame in (1,2) else 0), y+20)
        pygame.draw.line(surface, wood, (hx-sign*4,hy-10), tip, 2)
        if action == 'sweep':
            pygame.draw.polygon(surface, brass, [(tip[0]-3,tip[1]-6),(tip[0]+3,tip[1]-6),
                                                (tip[0]+6,tip[1]+1),(tip[0]-6,tip[1]+1)])
            for dx in (-3,0,3):
                pygame.draw.line(surface, wood, (tip[0]+dx,tip[1]-4),(tip[0]+dx,tip[1]+1))
        else:
            pygame.draw.line(surface, metal, (tip[0]-5,tip[1]), (tip[0]+5,tip[1]), 3)
    elif action == 'inspect':
        if facing == 'north':
            # The board faces its reader; show the wooden back beside the body.
            pygame.draw.rect(surface, wood, (x+12,y-12,12,18))
            pygame.draw.rect(surface, brass, (x+15,y-13,6,3))
            pygame.draw.line(surface, (110,80,50), (x+14,y-6),(x+21,y-6))
            return
        bx = x + (7 if facing == 'east' else -22 if facing == 'west' else -8)
        pygame.draw.rect(surface, wood, (bx-1,y-12,17,19))
        pygame.draw.rect(surface, (232,217,173), (bx,y-11,15,16))
        pygame.draw.rect(surface, brass, (bx+4,y-13,7,3))
        for dy in (-6,-2,2):
            pygame.draw.line(surface, (129,115,83), (bx+3,y+dy),(bx+10,y+dy))
