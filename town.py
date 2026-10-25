"""Two-dimensional Copperside village with moving residents."""

from __future__ import annotations

import math
import pygame
import scenery
import scene_depth
import town_art
import town_water
from citizens import update_activity

WIDTH, HEIGHT = 1280, 760
WORLD_W, WORLD_H = 2700, 1560
TOWN_READOUT_RECT = pygame.Rect(16, 16, 180, 108)
MINIMAP_RECT = pygame.Rect(WIDTH - 208, 16, 192, 112)
HUB_X = 1120
TRAIL_ENTRANCE = (1120, 145)
HOME_STREET_Y = 1320
CONNECTOR_XS = (HUB_X, 1630)
GRACE_JOB_DESTINATIONS = {"mill": "mill", "bakery": "bakery", "vent": "bakery",
                         "market": "market", "pump": "farm", "sorter": "market"}
from commissions import COMMISSIONS
GRACE_JOB_DESTINATIONS.update({key: job.business_id for key, job in COMMISSIONS.items() if job.business_id})
LOCATIONS = {
    "mill": (285, 625), "workshop": (755, 625), "bakery": (1280, 625),
    "market": (1290, 970), "farm": (270, 970),
    "fuel_yard": (425, 290), "parts_shop": (900, 290), "grace_shop": (1540, 290),
    "sawmill": (1920, 625), "foundry": (2410, 625), "toolmaker": (2110, 970),
    "east_bakery": (2130, 290),
    "home_5": (1830, HOME_STREET_Y), "home_6": (2310, HOME_STREET_Y),
    "home_1": (190, HOME_STREET_Y), "home_2": (700, HOME_STREET_Y), "home_3": (990, HOME_STREET_Y), "home_4": (1330, HOME_STREET_Y),
}
LABELS = {
    "east_bakery": "Jun's Bakery",
    "sawmill": "Sawmill", "foundry": "Foundry", "toolmaker": "Toolmaker",
    "home_5": "East Cottage", "home_6": "Orchard Cottage",
    "mill": "Mill", "workshop": "Workshop", "bakery": "Bakery", "market": "Market",
    "farm": "Farm", "fuel_yard": "Mely's Fuel Yard", "parts_shop": "Luca's Repair Shop",
    "grace_shop": "Grace's Workshop", "home_1": "Ada & Bram's Home",
    "home_2": "Agnes & Dara's Home", "home_3": "Mely & Luca's Home", "home_4": "Rowan's Cottage",
}


def location_label(village, key):
    """Vacant sites have no promised occupant or trade."""
    if key == 'east_bakery':
        return village.businesses.get(key, {}).get('name', '')
    if key.startswith('home_'):
        residents = [p['name'] for p in village.citizens if p['home'] == key]
        return (' & '.join(residents) + "'s Home") if residents else ''
    return LABELS.get(key, key)

ROOFS = {
    "east_bakery": (160, 111, 86),
    "sawmill": (148, 111, 65), "foundry": (103, 110, 119), "toolmaker": (74, 119, 115),
    "mill": (136, 79, 60), "workshop": (91, 105, 112), "bakery": (170, 99, 74),
    "market": (105, 125, 85), "farm": (134, 115, 74),
    "fuel_yard": (117, 82, 59), "parts_shop": (85, 118, 126),
    "grace_shop": (105, 91, 125),
    "home_1": (151, 105, 78), "home_2": (110, 133, 94),
    "home_3": (157, 106, 83), "home_4": (85, 120, 129),
    "home_5": (133, 119, 78), "home_6": (86, 122, 99),
}
ROAD_RECTS = ((88, 535, 2510, 235), (1085, 120, 70, 1300),
              (100, 930, 2390, 120), (90, HOME_STREET_Y - 30, 2390, 100),
              (280, 265, 2240, 103), (1595, 265, 70, 1155))

# All decorative bounds include canopies, shadows and posts, not just anchors.
# Reserve the complete street and doorstep before placing any scenery.
DECORATION_CANDIDATES = (
    ("sign", 1505, 810, "ARTISANS >"), ("sign", 1810, 810, "< CENTER"),
    *(("tree", x, y, "") for x, y in (
        (80, 210), (1730, 210), (1700, 875), (55, 875), (1510, 1200),
        (430, 1190), (1710, 1160), (1480, 1140), (75, 1130), (530, 470), (1510, 470), (2170, 470), (700, 210),
        (1750, 470), (2600, 470), (2540, 1160), (1910, 1120), (2640, 1370))),
    *(("lamp", x, y, "") for x, y in (
        (650, 885), (970, 885), (1390, 885), (1180, 1180), (560, 1190), (2320, 885))),
    *(("bench", x, y, "") for x, y in ((730, 815), (1460, 1085), (300, 1420), (2360, 1080))),
    *(("flowers", x, y, "") for x, y in (
        (65, 350), (470, 1100), (1320, 1420), (1460, 875), (670, 880),
        (1860, 860), (2360, 820), (2480, 1420))),
    ("well", 880, 868, ""),
    *(("birch", x, y, "") for x, y in ((335, 1190), (605, 200), (350, 1180), (610, 1160), (1240, 1190),
        (2000, 1160), (2460, 1180), (1400, 455), (1780, 860), (590, 480))),
    *(("pine", x, y, "") for x, y in ((80, 460), (1770, 160), (2630, 220),
        (2650, 480), (2635, 860), (60, 1190), (2640, 1150))),
    *(("planter", x, y, "") for x, y in ((635, 828), (1000, 850), (1170, 860),
        (200, 1100), (820, 1100), (1160, 1410), (2110, 1400), (1970, 850), (2250, 1100))),
    *(("barrel", x, y, "") for x, y in ((1840, 823), (2340, 832), (2490, 875), (380, 850))),
    *(("flowers", x, y, "") for x, y in ((800, 890), (650, 400), (1200, 400),
        (1800, 420), (2240, 415), (890, 1100), (400, 1420), (1550, 1410))),
    *(("shrub", x, y, "") for y in (400, 845, 1120, 1425) for x in range(105, 2610, 240)),
    *(("rocks", x, y, "") for x, y in ((105, 250), (590, 1100), (1000, 885),
        (1430, 420), (1800, 1090), (2230, 1420), (2580, 400), (2550, 1090))),
    *(("planter", x, y, "") for x, y in ((730, 870), (1890, 820), (2130, 1100))),
    *(("flowers", x, y, "") for x, y in ((1760, 860), (2420, 1190), (860, 1410))),
    ("logpile",205,220,""), ("cart",1310,220,""),
    ("baskets",1880,230,""), ("baskets",451,512,""),
    ("garden",487,1248,""), ("cart",2075,1225,""),
    ("logpile",2460,1269,""), ("garden",2360,1434,""),
    ("baskets",1060,1110,""), ("baskets",1510,1110,""),
)


def decoration_bounds(kind, x, y):
    offsets = {"tree": (-46, -90, 96, 111), "lamp": (-15, -88, 34, 103),
               "bench": (0, -5, 70, 31), "flowers": (0, 0, 94, 32),
               "sign": (-65, -24, 130, 66), "birch": (-38, -105, 78, 126),
               "pine": (-35, -100, 73, 121), "shrub": (-20, -20, 45, 37),
               "rocks": (-20, -12, 46, 30), "planter": (0, -20, 76, 45),
               "barrel": (-16, -32, 34, 49), "well": (-35, -68, 74, 90),
               "logpile": (-36,-39,74,50), "cart": (-43,-48,88,69),
               "baskets": (-22,-29,49,40), "garden": (0,-35,85,43)}
    dx, dy, width, height = offsets[kind]
    return pygame.Rect(x + dx, y + dy, width, height)


def scenery_exclusions():
    reserved = [pygame.Rect(rect).inflate(12, 12) for rect in ROAD_RECTS]
    for key, (x, y) in LOCATIONS.items():
        width = 180 if key.startswith("home_") else 255
        reserved.append(pygame.Rect(x - width // 2 - 14, y - 231, width + 28, 225))
        reserved.append(pygame.Rect(x - 42, y - 23, 84, 88))
    reserved.append(pygame.Rect(435, 803, 180, 110))  # cultivated farm rows
    return reserved


def decoration_layout():
    reserved = scenery_exclusions()
    accepted = []
    for entry in DECORATION_CANDIDATES:
        bounds = decoration_bounds(*entry[:3])
        # The well's paving belongs to its composition too, even though it is
        # flat ground rather than part of the depth-sorted well sprite.
        if entry[0] != "well" and bounds.colliderect(town_art.WELL_COURT.inflate(16, 16)):
            continue
        if not pygame.Rect(0, 0, WORLD_W, WORLD_H - 102).contains(bounds):
            continue
        if any(bounds.colliderect(rect) for rect in reserved):
            continue
        accepted.append(entry)
        reserved.append(bounds.inflate(12, 12))
    return tuple(accepted)


from ui_theme import INK, PAPER, COPPER, TEAL, GOLD, draw_panel, make_font


def words(surface, font, value, x, y, color=INK):
    surface.blit(font.render(str(value), True, color), (x, y))


def clipped(font, value, width):
    value = str(value)
    if font.render(value, True, INK).get_width() <= width:
        return value
    while value and font.render(value + "...", True, INK).get_width() > width:
        value = value[:-1]
    return value + "..."


def rectangle(surface, color, rect, radius=8, border=0):
    pygame.draw.rect(surface, color, rect, border, border_radius=radius)


class Town:
    def __init__(self):
        self.player_x, self.player_y = 755.0, 690.0
        self.walk_phase = 0.0
        self.visual_time = 0.0
        self.reduced_motion = False
        self._player_is_moving = False
        self.player_facing = "south"
        from town_companion import Companion
        self.companion = Companion((self.player_x, self.player_y), self._companion_blocked)
        self.people_facing = {}
        self.people_walk_phase: dict[str, float] = {}
        self.people_moving: set[str] = set()
        self.people: dict[str, list[float]] = {}
        # Display state is deliberately separate from saved economic positions.
        self.display_people: dict[str, list[float]] = {}
        self.display_phase: dict[str, float] = {}
        self.display_facing: dict[str, str] = {}
        self.display_moving: set[str] = set()
        self.routes: dict[str, list[tuple[float, float]]] = {}
        self.route_targets: dict[str, tuple[int, int]] = {}
        self.background = None
        self.scenery_props = ()
        self._background_homes = None

    def move(self, keys, dt):
        old_x, old_y = self.player_x, self.player_y
        footsteps = []
        dx = int(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - int(keys[pygame.K_a] or keys[pygame.K_LEFT])
        dy = int(keys[pygame.K_s] or keys[pygame.K_DOWN]) - int(keys[pygame.K_w] or keys[pygame.K_UP])
        self._player_is_moving = False
        if dx or dy:
            length = math.hypot(dx, dy)
            old_x, old_y = self.player_x, self.player_y
            new_x = min(WORLD_W - 45, max(45, self.player_x + dx / length * 250 * dt))
            new_y = min(WORLD_H - 45, max(145, self.player_y + dy / length * 250 * dt))
            # Follow the actual bank at small intervals, including long frames.
            # Endpoint-only checks can leap from one bank to another.
            steps = max(1, math.ceil(max(abs(new_x-old_x),abs(new_y-old_y))/6))
            step_x,step_y=(new_x-old_x)/steps,(new_y-old_y)/steps
            for _ in range(steps):
                if not self._inside_building(self.player_x+step_x,self.player_y):
                    self.player_x += step_x
                    footsteps.append((self.player_x,self.player_y))
                if not self._inside_building(self.player_x,self.player_y+step_y):
                    self.player_y += step_y
                    footsteps.append((self.player_x,self.player_y))
            self._player_is_moving = (self.player_x != old_x or self.player_y != old_y)
            if self._player_is_moving:
                self.walk_phase += math.hypot(self.player_x - old_x, self.player_y - old_y) * 0.11
                self.player_facing = self._facing(self.player_x - old_x, self.player_y - old_y)
        # Follow the actual collision-resolved steps, including the corner of
        # an axis slide, so Shannon never cuts straight through a building.
        self.companion.update((self.player_x, self.player_y), dt, via=footsteps)

    def rest(self, dt):
        self._player_is_moving = False
        self.companion.update((self.player_x, self.player_y), dt)

    @classmethod
    def _companion_blocked(cls, x, y):
        return not (45 <= x <= WORLD_W - 45 and 145 <= y <= WORLD_H - 45) or cls._inside_building(x, y)

    @staticmethod
    def _inside_building(x, y):
        # Actors are anchored above their feet; use the actual ground contact.
        if town_water.blocked(x,y+18,WORLD_W,WORLD_H):
            return True
        # Several footprints touch at street corners; preserve a walkable
        # approach at each marked front door even where those bounds overlap.
        if any(abs(x - bx) < 34 and door_y - 10 <= y <= door_y + 55
               for bx, door_y in LOCATIONS.values()):
            return False
        for key, (bx, door_y) in LOCATIONS.items():
            # Block the whole visible footprint, including the roof overhang.
            # Leave a clear approach below the front wall for interaction.
            width = 275 if not key.startswith("home_") else 200
            if bx - width / 2 - 10 < x < bx + width / 2 + 10 and door_y - 208 < y < door_y - 10:
                return True
        return False

    @classmethod
    def safe_position(cls, position):
        """Move a legacy river save to its nearby dry bank without losing state."""
        x,y=map(float,position)
        x=max(45.,min(WORLD_W-45.,x))
        y=max(145.,min(WORLD_H-45.,y))
        if town_water.blocked(x,y+18,WORLD_W,WORLD_H):
            y=town_water.north_bank(x,WORLD_W,WORLD_H)-21
        return x,y

    def update_people(self, village, dt, economic=False):
        self.people_moving.clear()
        present = {p["name"] for p in village.citizens} | {"Grace"}
        for name in set(self.people) - present:
            for mapping in (self.people, self.routes, self.route_targets, self.people_facing, self.people_walk_phase, self.display_people, self.display_phase, self.display_facing):
                mapping.pop(name, None)
        for person in village.citizens:
            home = LOCATIONS.get(person["home"], LOCATIONS["workshop"])
            members = sorted(p["name"] for p in village.citizens if p["home"] == person["home"])
            offset = (members.index(person["name"]) - (len(members) - 1) / 2) * 60
            self.people.setdefault(person["name"], list(person.get("position", (home[0] + offset, home[1] + 18))))
            if person["name"] not in self.routes and "path_target" in person:
                self.routes[person["name"]] = [tuple(point) for point in person.get("path", [])]
                self.route_targets[person["name"]] = tuple(person["path_target"])
        before_groups = {}
        for person in village.citizens:
            before_groups.setdefault(person.get("destination") or person["home"], []).append(person["name"])
        for person in village.citizens:
            destination = person.get("destination") or person["home"]
            group = sorted(before_groups[destination])
            center = LOCATIONS.get(destination, LOCATIONS[person["home"]])
            target = (center[0] + (group.index(person["name"]) - (len(group) - 1) / 2) * 60,
                      center[1] + (20 if len(group) > 1 else 0))
            point = self.people[person["name"]]
            arrived = math.dist(point, target) <= 3
            if economic and arrived:
                village.record_visit(person, dt)
            update_activity(person, village.households[person["home"]], village, dt, arrived)
        groups = {}
        for person in village.citizens:
            destination = person.get("destination") or person["home"]
            groups.setdefault(destination, []).append(person["name"])
        slots = {}
        for destination, names in groups.items():
            names.sort()
            for index, name in enumerate(names):
                # Give everyone at a shared door their own visible waiting spot.
                slots[name] = ((index - (len(names) - 1) / 2) * 60, 20 if len(names) > 1 else 0)
        for person in village.citizens:
            name = person["name"]
            home = LOCATIONS.get(person["home"], LOCATIONS["workshop"])
            home_group = sorted(p["name"] for p in village.citizens if p["home"] == person["home"])
            home_index = home_group.index(name)
            initial_offset = (home_index - (len(home_group) - 1) / 2) * 60
            current = self.people.setdefault(name, [float(home[0] + initial_offset), float(home[1] + 18 if len(home_group) > 1 else home[1])])
            destination = person.get("destination") or person["home"]
            target = LOCATIONS.get(destination, home)
            offset = slots.get(name, (0, 0))
            target = (target[0] + offset[0], target[1] + offset[1])
            self.display_people.setdefault(name, current.copy())
            self._travel(name, current, target, 110 * dt)
            person["position"] = current.copy()
            person["path"] = [list(point) for point in self.routes[name]]
            person["path_target"] = list(self.route_targets[name])
        grace = self.people.setdefault("Grace", [1540.0, 290.0])
        self.display_people.setdefault("Grace", grace.copy())
        bid = next((key for key, offer in village.offers.items() if offer["status"] == "bid"), None)
        destination = GRACE_JOB_DESTINATIONS.get(bid, "grace_shop")
        self._travel("Grace", grace, LOCATIONS[destination], 130 * dt)

    def update_visuals(self, dt):
        """Smooth the half-second economy steps without changing simulation time.

        Display motion trails the authoritative position by at most one normal
        simulation step. Fast-forward jumps snap instead of crossing the map.
        """
        self.visual_time += max(0., min(float(dt), 1.))
        self.display_moving.clear()
        for name, target in self.people.items():
            point = self.display_people.setdefault(name, target.copy())
            distance = math.dist(point, target)
            if distance > 180:
                point[:] = target
                continue
            moved = min(distance, max(0., dt) * (130 if name == "Grace" else 110))
            if moved > 0.001:
                dx, dy = target[0] - point[0], target[1] - point[1]
                self.display_facing[name] = self._facing(dx, dy)
                point[0] += dx / distance * moved
                point[1] += dy / distance * moved
                self.display_phase[name] = self.display_phase.get(name, 0.) + moved * .11
                self.display_moving.add(name)

    def _travel(self, name, point, target, step):
        if self.route_targets.get(name) != target:
            self.route_targets[name] = target
            current_road = min((290, 625, 970, HOME_STREET_Y), key=lambda y: abs(y - point[1]))
            connector = min(CONNECTOR_XS, key=lambda x: abs(point[0] - x) + abs(target[0] - x))
            self.routes[name] = ([] if math.dist(point, target) <= 2 else [target] if abs(point[1] - target[1]) < 55 else
                                 [(point[0], float(current_road)),
                                  (float(connector), float(current_road)), (float(connector), float(target[1])),
                                  (float(target[0]), float(target[1]))])
        route = self.routes[name]
        while route and step > 0:
            waypoint = route[0]
            distance = math.dist(point, waypoint)
            moved = min(distance, step)
            if moved > 0.15:
                self.people_moving.add(name)
                self.people_facing[name] = self._facing(waypoint[0] - point[0], waypoint[1] - point[1])
                self.people_walk_phase[name] = self.people_walk_phase.get(name, 0.0) + moved * 0.11
            self._walk(point, waypoint, moved)
            step -= moved
            if distance <= moved + 2:
                route.pop(0)

    @staticmethod
    def _walk(point, target, step):
        distance = math.dist(point, target)
        if distance > 2:
            step = min(distance, step)
            point[0] += (target[0] - point[0]) / distance * step
            point[1] += (target[1] - point[1]) / distance * step

    def nearby(self):
        place = self.nearby_place()
        if place:
            return place
        candidates = [(math.dist((self.player_x, self.player_y), point), f"person:{name}")
                      for name, point in self.people.items()]
        if not candidates:
            return None
        distance, key = min(candidates)
        return key if distance < 92 else None

    def nearby_place(self):
        """Residents at a doorway must not hide the building's interaction."""
        if math.dist((self.player_x, self.player_y), TRAIL_ENTRANCE) < 78:
            return "adventure"
        candidates = [(math.dist((self.player_x, self.player_y), point), key)
                      for key, point in LOCATIONS.items()]
        distance, key = min(candidates)
        return key if distance < 92 else None

    def person_at(self, mouse):
        if TOWN_READOUT_RECT.collidepoint(mouse) or MINIMAP_RECT.collidepoint(mouse):
            return None
        camera_x = max(0, min(WORLD_W - WIDTH, int(self.player_x - WIDTH // 2)))
        camera_y = max(0, min(WORLD_H - HEIGHT, int(self.player_y - HEIGHT // 2)))
        actors = [(name, self.display_people.get(name, point)) for name, point in self.people.items()]
        actors.append(("Shannon", self.companion.position))
        for name, point in sorted(actors, key=lambda item: item[1][1], reverse=True):
            rect = pygame.Rect(point[0] - camera_x - 25, point[1] - camera_y - 62, 50, 88)
            if rect.collidepoint(mouse):
                return name
        return None

    def draw(self, surface, fonts, village, dialogue, message, topic="work"):
        small, regular, heading, title = fonts
        growth = getattr(village, "migration", {})
        stage = growth.get("housing_stage", "plot")
        from migration import housing_state
        self.location_labels = {key: location_label(village, key) for key in LOCATIONS}
        homes = (tuple(sorted(self.location_labels.items())), tuple(sorted(village.businesses)), stage, growth.get("construction_days", 0),
                 growth.get("cottage_built", False), str(growth.get('homes', {})))
        if self.background is None or self._background_homes != homes:
            self._background_homes = homes
            self.background = pygame.Surface((WORLD_W, WORLD_H))
            cache = scene_depth.Cache((WORLD_W, WORLD_H))
            self._ground(self.background, small, cache)
            for key, point in LOCATIONS.items():
                if key == "east_bakery" and key not in village.businesses:
                    x, y = point
                    rectangle(self.background, (101, 136, 90), (x - 110, y - 175, 220, 150), 12)
                    for xx in range(x - 105, x + 110, 25):
                        rectangle(self.background, (192, 170, 122), (xx, y - 60, 7, 30), 2)
                    rectangle(self.background, (192, 170, 122), (x - 105, y - 52, 212, 5), 1)
                    continue
                if key.startswith("home_") and key not in village.households and not housing_state(village, key).get("cottage_built"):
                    x, y = point
                    rectangle(self.background, (101, 136, 90), (x - 85, y - 170, 170, 145), 12)
                    for xx in range(x - 80, x + 90, 20):
                        rectangle(self.background, (192, 170, 122), (xx, y - 55, 7, 28), 2)
                    rectangle(self.background, (192, 170, 122), (x - 80, y - 48, 168, 5), 1)
                    if housing_state(village, key).get("housing_stage") == "construction":
                        for xx in (x - 65, x + 55):
                            rectangle(self.background, (155, 120, 81), (xx, y - 180, 10, 150), 1)
                        for yy in (y - 165, y - 105):
                            rectangle(self.background, (155, 120, 81), (x - 65, yy, 130, 9), 1)
                    continue
                x, y = point
                cache.capture((x-160,y-240,320,250), y-12,
                              lambda target, point=point, key=key:self._building(target,point,key,heading,small,self.location_labels[key]))
            self.scenery_props = cache.finish()
        camera_x = max(0, min(WORLD_W - WIDTH, int(self.player_x - WIDTH // 2)))
        camera_y = max(0, min(WORLD_H - HEIGHT, int(self.player_y - HEIGHT // 2)))
        surface.blit(self.background, (0, 0), (camera_x, camera_y, WIDTH, HEIGHT))
        seconds = 0. if self.reduced_motion else self.visual_time
        town_art.river_motion(surface, (camera_x, camera_y), WORLD_W, WORLD_H, seconds)
        # Sort by feet so people crossing one another remain spatially readable.
        actors = []
        coats = {"Ada": (141, 91, 76), "Bram": (96, 119, 87), "Agnes": (156, 127, 68),
                 "Dara": (91, 115, 148), "Mely": COPPER, "Luca": (65, 115, 130), "Grace": (122, 94, 138)}
        for person in village.citizens:
            name = person["name"]
            point = self.display_people.get(name, self.people.get(name, LOCATIONS[person["home"]]))
            actors.append((point[1], point[0], name, coats.get(name, TEAL)))
        grace = self.display_people.get("Grace", self.people.get("Grace", LOCATIONS["grace_shop"]))
        actors.append((grace[1], grace[0], "Grace", coats["Grace"]))
        actors.append((self.player_y, self.player_x, "Boole", TEAL))
        actors.append((self.companion.position[1], self.companion.position[0], "Shannon", TEAL))
        def draw_actor(actor):
            wy, wx, name, coat = actor
            x, y = int(wx - camera_x), int(wy - camera_y)
            if name == "Shannon":
                self.companion.draw(surface, x, y)
                return
            player = name == "Boole"
            self._villager(surface, x, y, coat,
                           self.walk_phase if player else self.display_phase.get(name, 0),
                           self._player_is_moving if player else name in self.display_moving,
                           self.player_facing if player else self.display_facing.get(name, "south"), name)
            if not player:
                person = next((p for p in village.citizens if p['name'] == name), None)
                if person is not None:
                    target = LOCATIONS.get(person.get('destination'))
                    arrived = target is not None and math.dist((wx, wy), target) < 85
                    if person.get('activity') == 'seeking food' or arrived:
                        town_art.activity_prop(surface, x, y, person, seconds, name in self.display_moving)
            if not player and math.dist((wx, wy), (self.player_x, self.player_y)) < 190:
                rendered = small.render(name, True, PAPER)
                badge = rendered.get_rect(center=(x, y - 52)).inflate(12, 6)
                rectangle(surface, (48, 68, 61), badge, 5)
                surface.blit(rendered, rendered.get_rect(center=badge.center))
        jobs = [(actor[0]+18, lambda actor=actor:draw_actor(actor)) for actor in actors]
        evening = max(0., min(1., (getattr(village, 'daily_life', {}).get('elapsed', 0.) / 180. - .65) / .35))
        viewport = pygame.Rect(camera_x, camera_y, WIDTH, HEIGHT)
        for key, point in LOCATIONS.items():
            if key not in village.businesses and key not in village.households and key not in ('workshop', 'grace_shop'):
                continue
            if not pygame.Rect(point[0]-160, point[1]-290, 320, 300).colliderect(viewport):
                continue
            working = any(p.get('activity') == 'working' and p.get('destination') == key
                          and math.dist(p.get('position', point), point) < 85 for p in village.citizens)
            if key == 'workshop':
                working = any(item.get('busy', 0) > 0 for item in getattr(village, 'manufacturing', {}).get('equipment', []))
            if key == 'grace_shop':
                working = math.dist(grace, point) < 60 and 'Grace' not in self.display_moving
            jobs.append((point[1]-11, lambda key=key, point=point, working=working:
                         town_art.building_effects(surface, (camera_x, camera_y), key, point, seconds, working, evening)))
        if village.businesses.get('east_bakery', {}).get('operating_state') == 'paused':
            bx, by = LOCATIONS['east_bakery']
            notice = small.render('CLOSED', True, PAPER)
            box = notice.get_rect(center=(bx - camera_x, by - camera_y - 92)).inflate(16, 12)
            def draw_closed():
                rectangle(surface, COPPER, box, 4)
                surface.blit(notice, notice.get_rect(center=box.center))
            jobs.append((by-11,draw_closed))
        scene_depth.draw(surface,(camera_x,camera_y),self.scenery_props,jobs)
        self._readout(surface, small, village, heading)
        self._minimap(surface, small, village, camera_x, camera_y)
        if dialogue:
            self._dialogue(surface, fonts, village, dialogue, message, topic)

    @staticmethod
    def clock_time(village):
        """Display a twelve-hour village day without changing simulation timing."""
        from daily_life import progress
        minutes = 8 * 60 + int(max(0, min(1, progress(village))) * 12 * 60)
        return f"{minutes // 60:02d}:{minutes % 60:02d}"

    def _readout(self, surface, font, village, heading=None):
        draw_panel(surface, TOWN_READOUT_RECT)
        x, y = TOWN_READOUT_RECT.x + 14, TOWN_READOUT_RECT.y + 14
        words(surface, heading or font, "Copperside", x, y - 4, TEAL)
        words(surface, font, f"Day {village.day}  {self.clock_time(village)}", x, y + 27)
        words(surface, font, f"Coins  {village.coins}c", x, y + 54, COPPER)

    def _minimap(self, surface, font, village, camera_x, camera_y):
        """North-up overview with a live camera footprint and player marker."""
        x, y = MINIMAP_RECT.x + 1, MINIMAP_RECT.y + 1
        map_rect = pygame.Rect(x, y, 190, 110)
        pygame.draw.rect(surface, (119, 149, 104), map_rect)
        sx, sy = map_rect.width / WORLD_W, map_rect.height / WORLD_H
        def position(wx, wy):
            return round(x + wx * sx), round(y + wy * sy)
        old_clip=surface.get_clip()
        surface.set_clip(map_rect)
        pygame.draw.polygon(surface,(62,116,128),[position(wx,wy) for wx,wy in town_water.polygon(WORLD_W,WORLD_H)])
        pygame.draw.line(surface,(177,133,78),position(1120,WORLD_H-102),position(1120,WORLD_H-9),5)
        for rx, ry, rw, rh in ROAD_RECTS:
            pygame.draw.rect(surface, (207, 193, 153), (*position(rx, ry), max(2, round(rw * sx)), max(2, round(rh * sy))))
        for key, (wx, wy) in LOCATIONS.items():
            active = key in village.businesses or key in village.households or key in ('workshop', 'grace_shop')
            from migration import housing_state
            if key.startswith('home_') and housing_state(village, key).get('cottage_built'):
                active = True
            marker = pygame.Rect(0, 0, 9 if key.startswith('home_') else 13, 7)
            marker.midbottom = position(wx, wy - 10)
            pygame.draw.rect(surface, ROOFS.get(key, (154, 111, 75)), marker, 0 if active else 1)
        viewport = pygame.Rect(*position(camera_x, camera_y), round(WIDTH * sx), round(HEIGHT * sy))
        pygame.draw.rect(surface, (247, 235, 197), viewport.clip(map_rect), 1)
        player = position(self.player_x, self.player_y)
        trail = position(*TRAIL_ENTRANCE)
        pygame.draw.polygon(surface, PAPER, [(trail[0], trail[1] - 4),
                                           (trail[0] - 4, trail[1] + 3), (trail[0] + 4, trail[1] + 3)])
        pygame.draw.circle(surface, INK, player, 5)
        pygame.draw.circle(surface, GOLD, player, 3)
        surface.set_clip(old_clip)
        pygame.draw.rect(surface, (112, 94, 63), MINIMAP_RECT, 1)

    def _ground(self, surface, sign_font=None, cache=None):
        import random
        rng = random.Random(42)
        surface.fill((119, 149, 104))
        scenery.grass(surface, WORLD_W, WORLD_H)
        # Seeded, cached details keep the scenery stable and inexpensive to draw.
        for _ in range(2600):
            x, y = rng.randrange(WORLD_W), rng.randrange(WORLD_H)
            color = rng.choice(((128, 157, 109), (111, 142, 98), (141, 163, 115)))
            pygame.draw.line(surface, color, (x, y), (x + 3, y - 3), 2)
        # Pave the union once. One world-aligned brick grid means intersections
        # have neither an interior edge nor a competing row alignment.
        mask_surface = pygame.Surface((WORLD_W, WORLD_H), pygame.SRCALPHA)
        for rect in ROAD_RECTS:
            rectangle(mask_surface, (255, 255, 255, 255), rect, 20)
        # A single exterior curb follows the union, leaving intersections open.
        edge = pygame.mask.from_surface(mask_surface).outline(3)
        if edge:
            pygame.draw.lines(surface, (96, 115, 83), True, edge, 11)
            pygame.draw.lines(surface, (155, 149, 111), True, edge, 6)
        paving = pygame.Surface((WORLD_W, WORLD_H), pygame.SRCALPHA)
        paving.fill((183, 168, 139, 255))
        for y in range(0, WORLD_H, 24):
            offset = 21 if (y // 24) % 2 else 0
            for x in range(-42, WORLD_W, 42):
                rectangle(paving, (192, 178, 151), (x + offset, y, 38, 20), 4)
        paving.blit(mask_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surface.blit(paving, (0, 0))
        town_art.ground_details(surface)
        layout = decoration_layout()
        planting_exclusions = scenery_exclusions() + [town_art.WELL_COURT.inflate(16, 16)]
        planting_exclusions.extend(decoration_bounds(*entry[:3]).inflate(6, 6) for entry in layout)
        town_art.planting_clusters(surface, layout, planting_exclusions)
        if cache is None:
            self._trail_sign(surface, sign_font)
        else:
            cache.capture((1140,124,120,84),204,lambda target:self._trail_sign(target,sign_font))
        # Natural banks and collision use the same river polygon.
        town_water.draw(surface,WORLD_W,WORLD_H)
        for x in range(1060, 1185, 15):
            rectangle(surface, (147, 106, 71), (x, WORLD_H - 102, 13, 93), 2)
        for y in (WORLD_H - 94, WORLD_H - 17):
            pygame.draw.line(surface, (83, 65, 49), (1055, y), (1190, y), 5)
        scenery.riverbank(surface, WORLD_W, WORLD_H)
        for kind, x, y, label in decoration_layout():
            if cache is None or kind == "flowers":
                self._decoration(surface, rng, kind, x, y, label)
            else:
                foot = y + {"sign":40,"bench":24,"planter":22,"lamp":0}.get(kind,16)
                cache.capture(decoration_bounds(kind,x,y),foot,
                              lambda target, kind=kind, x=x, y=y, label=label:self._decoration(target,rng,kind,x,y,label))
        # Farm rows and supplies make each district visually identifiable.
        for y in range(810, 910, 20):
            rectangle(surface, (135, 112, 74), (440, y, 170, 13), 4)
            for x in range(450, 605, 17):
                pygame.draw.line(surface, (216, 188, 97), (x, y + 7), (x + 2, y - 2), 3)
                for dx, dy in ((-3, 1), (3, -1), (-2, -3)):
                    pygame.draw.ellipse(surface, (232, 201, 111), (x + dx, y + dy, 5, 3))

    @staticmethod
    def _trail_sign(surface, sign_font=None):
        # A real sign at the north road marks the footpath out of Copperside.
        rectangle(surface, (106, 79, 53), (1190, 150, 7, 54), 2)
        rectangle(surface, (70, 92, 75), (1146, 130, 106, 31), 3)
        rectangle(surface, (185, 154, 99), (1146, 130, 106, 31), 3, 1)
        font = sign_font if sign_font is not None else make_font(16)
        label = font.render("MOSSWATER", True, PAPER)
        surface.blit(label, label.get_rect(center=(1199, 145)))
        pygame.draw.polygon(surface, PAPER, [(1193, 166), (1187, 175), (1199, 175)])

    @staticmethod
    def _decoration(surface, rng, kind, x, y, label):
        if kind in ("tree", "birch", "pine"):
            scenery.tree(surface, x, y, kind)
        elif kind in ("shrub", "rocks", "planter", "barrel", "well", "logpile", "cart", "baskets", "garden"):
            scenery.small_prop(surface, rng, kind, x, y)
        elif kind == "lamp":
            pygame.draw.ellipse(surface, (102, 123, 87), (x - 15, y + 5, 34, 10))
            pygame.draw.line(surface, (67, 77, 67), (x, y), (x, y - 65), 5)
            rectangle(surface, (67, 77, 67), (x - 11, y - 78, 22, 25), 4)
            rectangle(surface, (243, 202, 111), (x - 7, y - 74, 14, 17), 2)
            pygame.draw.polygon(surface, (67, 77, 67), [(x - 15, y - 79), (x, y - 88), (x + 15, y - 79)])
        elif kind == "bench":
            for yy in (y, y + 8):
                rectangle(surface, (143, 101, 64), (x, yy, 70, 6), 2)
            for xx in (x + 7, x + 58):
                pygame.draw.line(surface, (64, 79, 66), (xx, y - 3), (xx, y + 24), 4)
        elif kind == "flowers":
            scenery.flowers(surface, rng, x, y)
        elif kind == "sign":
            rectangle(surface, (106, 83, 59), (x - 4, y, 8, 40), 1)
            rectangle(surface, (62, 87, 75), (x - 65, y - 24, 130, 29), 3)
            text = make_font(15).render(label, True, PAPER)
            surface.blit(text, text.get_rect(center=(x, y - 10)))

    def _building(self, surface, point, key, heading, small, display_label=None):
        """Distinct trade architecture within the existing movement envelope."""
        town_art.building(surface, point, key, heading, small,
                          ROOFS.get(key, (149, 99, 77)),
                          display_label if display_label is not None else LABELS[key])

    @staticmethod
    def _facing(dx, dy):
        return ("east" if dx > 0 else "west") if abs(dx) > abs(dy) else ("south" if dy > 0 else "north")

    def _villager(self, surface, x, y, coat, phase=0.0, moving=False, facing="south", name="", *, shadow_color=(83, 104, 78)):
        """Distance-driven four-direction walk, with alternating feet and arms."""
        if shadow_color is not None:
            pygame.draw.ellipse(surface, shadow_color, (x - 17, y + 15, 34, 10))
        stride = round(math.sin(phase) * 6) if moving else 0
        bob = -round(abs(math.sin(phase)) * 2) if moving else 0
        y += bob
        dark = tuple(max(0, c - 29) for c in coat)
        skin = (226, 180, 136)
        hair = (71, 55, 46) if name not in ("Agnes", "Grace") else (157, 108, 66)
        side = facing in ("east", "west")
        sign = 1 if facing == "east" else -1
        for leg in (-1, 1):
            foot_x = x + (stride * leg if side else leg * 6)
            foot_y = y + 19 + (0 if side else stride * leg // 2)
            if name == "Grace" and leg == 1:
                # One wooden prosthesis, with a brass socket and ferrule. Keep
                # the same footfall and silhouette in every walking direction.
                knee = (x + leg * 5, y + 10)
                pygame.draw.line(surface, (83, 64, 52), (x + leg * 5, y + 5), knee, 7)
                pygame.draw.line(surface, (172, 122, 69), knee, (foot_x, foot_y + 2), 4)
                pygame.draw.line(surface, (221, 175, 99), knee, (foot_x, foot_y), 1)
                pygame.draw.circle(surface, (191, 150, 77), knee, 3)
                rectangle(surface, (99, 85, 66), (foot_x - 2, foot_y + 1, 5, 3), 1)
                continue
            pygame.draw.line(surface, (77, 67, 57), (x + leg * 5, y + 5), (foot_x, foot_y), 6)
            rectangle(surface, (49, 53, 48), (foot_x - 4, foot_y - 1, 9, 5), 2)
        rectangle(surface, dark, (x - 13, y - 16, 26, 27), 5)
        rectangle(surface, coat, (x - 10, y - 16, 20, 23), 4)
        for arm in (-1, 1):
            ax = x + arm * 13 + (stride * arm // 2 if side else 0)
            ay = y + 2 + (stride * arm // 2 if not side else 0)
            pygame.draw.line(surface, dark, (x + arm * 10, y - 11), (ax, ay), 5)
            rectangle(surface, skin, (ax - 2, ay, 5, 5), 2)
        rectangle(surface, skin, (x - 9, y - 35, 18, 21), 5)
        rectangle(surface, hair, (x - 11, y - 39, 22, 9), 3)
        if facing == "north":
            rectangle(surface, hair, (x - 10, y - 33, 20, 17), 4)
            rectangle(surface, dark, (x - 7, y - 13, 14, 14), 2)
        elif side:
            rectangle(surface, hair, (x - sign * 7 - 3, y - 32, 6, 13), 2)
            pygame.draw.rect(surface, INK, (x + sign * 5, y - 28, 2, 3))
            rectangle(surface, skin, (x + sign * 9 - 2, y - 26, 5, 5), 1)
        else:
            rectangle(surface, hair, (x - 11, y - 32, 4, 8), 1)
            for ex in (-5, 4):
                pygame.draw.rect(surface, INK, (x + ex, y - 28, 2, 3))
            pygame.draw.line(surface, (173, 112, 88), (x - 2, y - 20), (x + 3, y - 20), 1)
            pygame.draw.line(surface, PAPER, (x - 5, y - 14), (x, y - 8), 2)
            pygame.draw.circle(surface, GOLD, (x + 2, y - 2), 2)
        if name in ("Boole", "Luca"):
            rectangle(surface, (94, 73, 53), (x - 12, y - 39, 24, 6), 2)
            if facing == "north":
                # Back of the leather strap and a small clasp; lenses face away.
                rectangle(surface, (179, 142, 84), (x - 2, y - 38, 4, 4), 1)
            else:
                for gx in ((sign * 9,) if side else (-5, 5)):
                    pygame.draw.circle(surface, GOLD, (x + gx, y - 36), 4)
                    pygame.draw.circle(surface, (91, 150, 150), (x + gx, y - 36), 2)
        if name == "Boole":
            # Rust scarf and a pale tool satchel remain distinct from Luca's
            # blue work coat, even when the player is facing away.
            scarf = (211, 91, 61)
            rectangle(surface, scarf, (x - 10, y - 17, 20, 5), 2)
            tail = x - sign * 9 if side else x + 6
            pygame.draw.polygon(surface, scarf, [(tail, y - 14), (tail + 5, y - 14),
                                                (tail + 5 + stride // 2, y + 1), (tail + stride // 2, y - 2)])
            if facing == "north":
                rectangle(surface, (197, 162, 104), (x - 7, y - 11, 14, 19), 3)
                pygame.draw.line(surface, GOLD, (x - 5, y - 6), (x + 5, y - 6), 2)
            else:
                bag_x = x - sign * 10 if side else x + 10
                pygame.draw.line(surface, (197, 162, 104), (x - 7, y - 12), (bag_x, y + 4), 2)
                rectangle(surface, (197, 162, 104), (bag_x - 4, y - 2, 9, 12), 2)
                pygame.draw.rect(surface, GOLD, (bag_x - 1, y, 3, 3))
        # Individual work clothes, hats and accessories make residents legible
        # without requiring a name label above every distant person.
        town_art.clothing(surface, x, y, name, facing, moving, phase)

    def interaction_prompt(self):
        nearby = self.nearby()
        label = nearby[7:] if nearby and nearby.startswith("person:") else getattr(self, "location_labels", LABELS).get(nearby, "")
        if nearby and nearby.startswith("person:"):
            return f"Click to talk to {label}"
        elif nearby == "workshop":
            return "E  Enter workshop"
        elif nearby == "adventure":
            return "E  Follow the Mosswater trail"
        elif nearby:
            return f"E  Visit {label or 'site'}"
        else:
            return "Click a person to talk / approach a place to visit"

    def _dialogue(self, surface, fonts, village, location, message, topic="work"):
        from dialogue import draw_dialogue
        draw_dialogue(surface, fonts, village, location, message, topic)
