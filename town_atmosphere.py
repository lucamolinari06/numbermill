"""Copperside-only daylight and decoration; reads state, never advances it."""
import math
import pygame


def clock_progress(village):
    """Read the village clock without initializing/migrating a save while drawing."""
    from daily_life import DAY_SECONDS
    current = getattr(village, 'daily_life', {})
    if current.get('day') != village.day:
        return 0.
    # The economy advances in half-second steps. Its saved accumulator contains
    # the intervening frame time, so instruments and light need not tick/jump.
    return max(0., min(1., (current.get('elapsed', 0.)
                           + current.get('accumulator', 0.)) / DAY_SECONDS))


# Flat palette transforms preserve individual pixels and material texture.
# The boundary is the middle of a brief, readable night. The next day's first
# seconds continue through dawn, rather than replacing evening with daylight.
# Both endpoint colors and slopes agree; no extra timer or save state is needed.
LIGHT_STOPS = ((0., (193, 207, 222)), (.085, (232, 232, 228)),
              (.18, (255, 245, 226)), (.32, (255, 255, 255)),
              (.58, (255, 253, 246)), (.78, (255, 236, 210)),
              (.98, (193, 207, 222)), (1., (193, 207, 222)))


def smoothstep(value):
    value = max(0., min(1., value))
    return value*value*(3-2*value)


def daylight(progress):
    progress = max(0., min(1., progress))
    for (start, a), (end, b) in zip(LIGHT_STOPS, LIGHT_STOPS[1:]):
        if progress <= end:
            blend = smoothstep((progress-start)/(end-start))
            return tuple(round(x+(y-x)*blend) for x, y in zip(a, b))
    return LIGHT_STOPS[-1][1]


def evening_light(progress):
    progress = max(0., min(1., progress))
    # Lamps stay lit across rollover and gradually lose their warm glow in dawn.
    return max(1-smoothstep(progress/.16), smoothstep((progress-.70)/.27))


def apply_daylight(surface, progress):
    surface.fill(daylight(progress), special_flags=pygame.BLEND_RGB_MULT)


def working(town, village, key):
    """Use real batches, attendance, closures and reported production blocks."""
    if key == 'workshop':
        return any(item.get('busy', 0) > 0
                   for item in getattr(village, 'manufacturing', {}).get('equipment', ()))
    firm = village.businesses.get(key)
    if not firm or firm.get('operating_state') == 'paused':
        return False
    if key == 'east_bakery' and firm.get('kind') != 'bakery':
        # The reusable commercial site may later house fuel/parts traders.
        # Its old oven must not imply that a successor is baking bread.
        return False
    current = getattr(village, 'daily_life', {})
    if current.get('day') != village.day or current.get('settled'):
        return False
    reason = current.get('reasons', {}).get(key, '')
    if (reason.startswith(('Waiting for', 'Cannot afford', 'Boiler shutdown', 'No work attendance'))
            or reason in ('Daily capacity reached', 'Stock buffer is full', 'Fuel shortage; steam upgrade paused')):
        return False
    if current.get('produced', {}).get(key, 0) >= village.capacity(key):
        return False
    from economy import BUSINESS_TYPES
    recipe = BUSINESS_TYPES[firm['kind']]
    if recipe['input']:
        if firm.get('cash', 0) < recipe['input_price']:
            return False
        if not any(other is not firm and other.get('stock', {}).get(recipe['input'], 0) > 0
                   for other in village.businesses.values()):
            return False
    if firm.get('owner_operated'):
        # Regional owners work throughout the day; Jun's baker shift is shorter.
        # The production counters and stock cap also stop their machinery.
        output = recipe['output']
        cap = {'timber': 12, 'metal': 8, 'fittings': 6, 'bread': 4+village.stock_buffer_bonus(key)}.get(output)
        if cap is not None and firm.get('stock', {}).get(output, 0) >= cap:
            return False
        return bool(current.get('started'))
    if firm.get('workers', 0) <= 0:
        return False
    return any(person.get('activity') == 'working' and person.get('workplace') == key
               and person.get('destination') == key and person['name'] not in town.display_moving
               and person['name'] in town.route_targets
               and math.dist(town.display_people.get(person['name'], (-1000, -1000)),
                             town.route_targets[person['name']]) <= 3
               for person in village.citizens)


def leaves(surface, camera, layout, seconds, reduced_motion=False):
    """One tiny drifting leaf per occasional tree, inside its reserved envelope.

    Depth sorting happens with the source tree, so foliage cannot float over a
    foreground actor or a building. Reduced motion omits drifting decoration.
    """
    if reduced_motion:
        return
    ox, oy = camera
    for kind, x, y, _ in layout:
        if kind not in ('tree', 'birch'):
            continue
        seed = x*37+y*71
        age = (seconds+(seed % 997)/31) % (23+seed % 7)
        if age >= 4.:
            continue
        xx = x-12+round(age*5+math.sin(age*2+seed)*4)-ox
        yy = y-70+round(age*16)-oy
        if not surface.get_rect().inflate(8, 8).collidepoint(xx, yy):
            continue
        color = (166, 159, 86) if seed % 2 else (136, 157, 86)
        pygame.draw.rect(surface, color, (xx, yy, 4 if int(age*3) % 2 else 2, 2))
        pygame.draw.rect(surface, (194, 173, 105), (xx+1, yy+2, 2, 1))
