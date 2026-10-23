"""Two-dimensional Copperside village with moving residents."""

from __future__ import annotations

import math
import pygame
from citizens import update_activity

WIDTH, HEIGHT = 1280, 760
WORLD_W, WORLD_H = 1840, 1560
HUB_X = 1120
HOME_STREET_Y = 1320
LOCATIONS = {
    "mill": (285, 625), "workshop": (755, 625), "bakery": (1280, 625),
    "market": (1290, 970), "farm": (270, 970),
    "fuel_yard": (425, 290), "parts_shop": (975, 290), "nell_shop": (1540, 290),
    "home_1": (190, HOME_STREET_Y), "home_2": (700, HOME_STREET_Y), "home_3": (990, HOME_STREET_Y),
}
LABELS = {
    "mill": "Mill", "workshop": "Workshop", "bakery": "Bakery", "market": "Market",
    "farm": "Farm", "fuel_yard": "Mely's Fuel Yard", "parts_shop": "Luca's Repair Shop",
    "nell_shop": "Nell's Workshop", "home_1": "Ada & Bram's Home",
    "home_2": "Cora & Dara's Home", "home_3": "Mely & Luca's Home",
}
ROOFS = {
    "mill": (136, 79, 60), "workshop": (91, 105, 112), "bakery": (170, 99, 74),
    "market": (105, 125, 85), "farm": (134, 115, 74),
    "fuel_yard": (117, 82, 59), "parts_shop": (85, 118, 126),
    "nell_shop": (105, 91, 125),
}
INK, PAPER = (43, 48, 45), (251, 240, 211)
COPPER, TEAL, GOLD = (170, 95, 63), (61, 121, 115), (237, 183, 79)


def words(surface, font, value, x, y, color=INK):
    surface.blit(font.render(str(value), True, color), (x, y))


def rectangle(surface, color, rect, radius=8, border=0):
    pygame.draw.rect(surface, color, rect, border, border_radius=radius)


class Town:
    def __init__(self):
        self.player_x, self.player_y = 755.0, 690.0
        self.walk_phase = 0.0
        self.people: dict[str, list[float]] = {}
        self.routes: dict[str, list[tuple[float, float]]] = {}
        self.route_targets: dict[str, tuple[int, int]] = {}
        self.background = None

    def move(self, keys, dt):
        dx = int(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - int(keys[pygame.K_a] or keys[pygame.K_LEFT])
        dy = int(keys[pygame.K_s] or keys[pygame.K_DOWN]) - int(keys[pygame.K_w] or keys[pygame.K_UP])
        if dx or dy:
            length = math.hypot(dx, dy)
            new_x = min(WORLD_W - 45, max(45, self.player_x + dx / length * 250 * dt))
            new_y = min(WORLD_H - 45, max(145, self.player_y + dy / length * 250 * dt))
            if not self._inside_building(new_x, self.player_y):
                self.player_x = new_x
            if not self._inside_building(self.player_x, new_y):
                self.player_y = new_y
            self.walk_phase += dt * 12

    @staticmethod
    def _inside_building(x, y):
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

    def update_people(self, village, dt):
        for person in village.citizens:
            point = self.people.get(person["name"])
            arrived = point is None or not self.routes.get(person["name"])
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
            self._travel(name, current, target, 110 * dt)
        nell = self.people.setdefault("Nell", [1540.0, 290.0])
        bid = next((key for key, offer in village.offers.items() if offer["status"] == "bid"), None)
        destination = {"mill": "mill", "bakery": "bakery", "vent": "bakery", "market": "market"}.get(bid, "nell_shop")
        self._travel("Nell", nell, LOCATIONS[destination], 130 * dt)

    def _travel(self, name, point, target, step):
        if self.route_targets.get(name) != target:
            self.route_targets[name] = target
            current_road = min((290, 625, 970, HOME_STREET_Y), key=lambda y: abs(y - point[1]))
            self.routes[name] = ([] if math.dist(point, target) <= 2 else [target] if abs(point[1] - target[1]) < 55 else
                                 [(point[0], float(current_road)),
                                  (float(HUB_X), float(current_road)), (float(HUB_X), float(target[1])),
                                  (float(target[0]), float(target[1]))])
        route = self.routes[name]
        while route and step > 0:
            waypoint = route[0]
            distance = math.dist(point, waypoint)
            moved = min(distance, step)
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
        candidates = [(math.dist((self.player_x, self.player_y), point), key)
                      for key, point in LOCATIONS.items()]
        candidates += [(math.dist((self.player_x, self.player_y), point), f"person:{name}")
                       for name, point in self.people.items()]
        distance, key = min(candidates)
        return key if distance < 92 else None

    def person_at(self, mouse):
        if mouse[1] <= 74 or mouse[1] >= 632:
            return None
        camera_x = max(0, min(WORLD_W - WIDTH, int(self.player_x - WIDTH // 2)))
        camera_y = max(0, min(WORLD_H - HEIGHT, int(self.player_y - HEIGHT // 2)))
        for name, point in sorted(self.people.items(), key=lambda item: item[1][1], reverse=True):
            rect = pygame.Rect(point[0] - camera_x - 25, point[1] - camera_y - 62, 50, 88)
            if rect.collidepoint(mouse):
                return name
        return None

    def draw(self, surface, fonts, village, dialogue, message, topic="work"):
        small, regular, heading, title = fonts
        if self.background is None:
            self.background = pygame.Surface((WORLD_W, WORLD_H))
            self._ground(self.background)
            for key, point in LOCATIONS.items():
                self._building(self.background, point, key, heading, small)
        camera_x = max(0, min(WORLD_W - WIDTH, int(self.player_x - WIDTH // 2)))
        camera_y = max(0, min(WORLD_H - HEIGHT, int(self.player_y - HEIGHT // 2)))
        surface.blit(self.background, (0, 0), (camera_x, camera_y, WIDTH, HEIGHT))
        for person in village.citizens:
            point = self.people.get(person["name"], LOCATIONS[person["home"]])
            coat = (170, 101, 68) if person["name"] == "Mely" else (71, 119, 131) if person["name"] == "Luca" else (110, 118, 100)
            x, y = int(point[0] - camera_x), int(point[1] - camera_y)
            self._villager(surface, x, y, coat)
            if person["name"] in ("Mely", "Luca"):
                words(surface, small, person["name"], x - 20, y - 60, PAPER)
        nell = self.people.get("Nell", LOCATIONS["nell_shop"])
        nx, ny = int(nell[0] - camera_x), int(nell[1] - camera_y)
        self._villager(surface, nx, ny, (116, 88, 131))
        words(surface, small, "Nell", nx - 17, ny - 60, PAPER)
        px, py = int(self.player_x - camera_x), int(self.player_y - camera_y)
        self._villager(surface, px, py, TEAL)
        pygame.draw.circle(surface, GOLD, (px, py - 40), 6)
        rectangle(surface, (50, 72, 66), (24, 12, 1232, 62), 12)
        rectangle(surface, PAPER, (30, 18, 1220, 50), 9)
        words(surface, title, "Copperside Village", 135, 27)
        self._town_chip(surface, small, "DAY", str(village.day), 437, 26, 112)
        self._town_chip(surface, small, "COINS", f"{village.coins}c", 563, 26, 136)
        self._town_chip(surface, small, "PEOPLE", str(len(village.citizens)), 713, 26, 132)
        if dialogue:
            self._dialogue(surface, fonts, village, dialogue, message, topic)
        else:
            self._status(surface, fonts, village, message)

    @staticmethod
    def _town_chip(surface, font, label, value, x, y, width):
        rectangle(surface, (237, 226, 198), (x, y, width, 34), 7)
        words(surface, font, label, x + 9, y + 10, (103, 103, 87))
        rendered = font.render(value, True, INK)
        surface.blit(rendered, (x + width - rendered.get_width() - 9, y + 10))

    def _ground(self, surface):
        surface.fill((112, 148, 104))
        # A square and short connecting streets keep destinations close.
        for rect in ((88, 535, 1660, 235), (1085, 120, 70, 1300),
                     (100, 930, 1530, 120), (90, HOME_STREET_Y - 30, 1110, 100),
                     (280, 265, 1320, 103)):
            rectangle(surface, (148, 143, 126), rect, 18)
        for y in range(290, HOME_STREET_Y, 47):
            rectangle(surface, (162, 154, 135), (1101, y, 38, 40), 4)
        for x in range(120, 1700, 62):
            rectangle(surface, (162, 154, 135), (x, 625, 53, 36), 4)
        for x, y in ((90, 190), (1700, 190), (1650, 850), (70, 810), (1510, 1370), (430, 1400)):
            rectangle(surface, (99, 68, 49), (x - 6, y - 15, 12, 29), 3)
            pygame.draw.circle(surface, (54, 115, 81), (x, y - 28), 34)
            pygame.draw.circle(surface, (76, 140, 93), (x - 14, y - 37), 23)
        rectangle(surface, (69, 129, 145), (35, WORLD_H - 80, WORLD_W - 70, 30), 9)

    def _building(self, surface, point, key, heading, small):
        x, door_y = point
        width = 255 if not key.startswith("home_") else 180
        left = x - width // 2
        roof = ROOFS.get(key, (135, 96, 78))
        rectangle(surface, (73, 65, 55), (left + 6, door_y - 184, width, 174), 7)
        rectangle(surface, (224, 201, 156), (left, door_y - 190, width, 175), 7)
        rectangle(surface, roof, (left - 10, door_y - 208, width + 20, 65), 6)
        rectangle(surface, (105, 69, 49), (x - 25, door_y - 77, 50, 62), 3)
        for wx in (left + 27, left + width - 57):
            rectangle(surface, (71, 125, 134), (wx, door_y - 110, 30, 34), 3)
        label = LABELS[key]
        if len(label) > 18:
            label = label.replace("'s ", " ")
        sign = heading if len(label) < 15 else small
        rendered = sign.render(label.upper(), True, PAPER)
        rectangle(surface, (76, 59, 47), (x - rendered.get_width() // 2 - 10, door_y - 155,
                                          rendered.get_width() + 20, 34), 3)
        surface.blit(rendered, rendered.get_rect(center=(x, door_y - 138)))
        if key == "fuel_yard":
            for dx in (-88, 78):
                rectangle(surface, (94, 78, 65), (x + dx, door_y - 27, 24, 25), 3)
        elif key == "parts_shop":
            pygame.draw.circle(surface, GOLD, (x + 82, door_y - 35), 14, 4)

    def _villager(self, surface, x, y, coat):
        pygame.draw.ellipse(surface, (81, 87, 71), (x - 15, y + 15, 30, 8))
        for dx in (-8, 5):
            rectangle(surface, (69, 56, 49), (x + dx, y + 5, 7, 17), 2)
        rectangle(surface, coat, (x - 13, y - 14, 26, 27), 4)
        rectangle(surface, (218, 169, 124), (x - 10, y - 33, 20, 21), 3)
        rectangle(surface, (69, 53, 43), (x - 12, y - 37, 24, 8), 2)

    def _status(self, surface, fonts, village, message):
        small, regular, _, _ = fonts
        rectangle(surface, (55, 76, 69), (40, 632, 1200, 88), 4)
        rectangle(surface, PAPER, (48, 640, 1184, 72), 3)
        nearby = self.nearby()
        label = nearby[7:] if nearby and nearby.startswith("person:") else LABELS.get(nearby, "")
        prompt = f"E  Talk to {label}" if nearby else "Walk to a person or building and press E"
        if nearby == "workshop":
            prompt = "E  Enter workshop"
        words(surface, regular, prompt, 67, 650, TEAL)
        words(surface, small, "Click NPCs / WASD move / E interact / M map / C compute", 67, 683)
        words(surface, small, village.market_note[:52], 691, 653, COPPER)
        words(surface, small, (message or village.journal[0])[:59], 691, 683)

    def _dialogue(self, surface, fonts, village, location, message, topic="work"):
        small, regular, heading, _ = fonts
        rectangle(surface, (55, 70, 62), (275, 500, 730, 219), 4)
        rectangle(surface, PAPER, (283, 508, 714, 203), 3)
        if location.startswith("person:"):
            name = location[7:]
            if name == "Nell":
                bid = next((key for key, offer in village.offers.items() if offer["status"] == "bid"), None)
                lines = (f"I'm building the {bid} job. The Inventors ledger has the due day.",
                         "I take jobs when the customer can support the work.") if bid else (
                         "I'm looking for the next useful machine to build.",
                         "The contract board shows what firms need and who has bid.")
            else:
                person = next((p for p in village.citizens if p["name"] == name), None)
                if person and topic == "family":
                    home = village.households[person["home"]]
                    family = ", ".join(p["name"] for p in village.citizens if p["home"] == person["home"] and p != person)
                    lines = (f"I share a home with {family or 'no one'}. We have {home['cash']} coins.",
                             f"Meals missed: {home['missed_meals']}. I feel {person['mood']}/100 today.")
                elif person and topic == "town":
                    memory = next((line for line in reversed(person["memories"]) if "spoke with you" not in line), None)
                    lines = (village.market_note,
                             memory or "I'm still settling in.")
                elif person and name == "Mely":
                    stock = village.businesses["fuel_yard"]["stock"].get("fuel", 0)
                    lines = (f"I keep the steam running. Fuel on hand: {stock}.",
                             f"Today I'm {person['activity'].lower()}. {person['last_reason']}.")
                elif person and name == "Luca":
                    stock = village.businesses["parts_shop"]["stock"].get("parts", 0)
                    lines = (f"I build parts from Mely's fuel. Parts ready: {stock}.",
                             f"Today I'm {person['activity'].lower()}. {person['last_reason']}.")
                else:
                    lines = (f"I'm {person['activity']}: {person['last_reason']}.",
                             f"I work at {LABELS.get(person['workplace'], person['workplace'])}. Mood {person['mood']}/100.") if person else (
                             "I live here in Copperside.", "The village changes with its businesses.")
            who = name
        else:
            who = LABELS.get(location, location)
            if location == "market":
                stock = village.businesses["market"]["stock"].get("bread", 0)
                lines = (f"Counter: {stock} bread at {village.bread_price} coins each.",
                         f"Your purse: {village.coins} coins. Pantry: {village.player_bread} bread.")
            elif location in village.households:
                home = village.households[location]
                names = ", ".join(p["name"] for p in village.citizens if p["home"] == location)
                lines = (f"{names} live here. Savings: {home['cash']} coins.",
                         f"Bread today: {home['bought']}/{home['bread_need']}. Missed meals: {home['missed_meals']}.")
            elif location == "fuel_yard":
                firm = village.businesses[location]
                lines = (f"Mely keeps {firm['stock'].get('fuel', 0)} fuel ready for town.",
                         "Workshop service buys fuel here when a customer orders.")
            elif location == "parts_shop":
                firm = village.businesses[location]
                lines = (f"Luca has {firm['stock'].get('parts', 0)} repair parts in stock.",
                         "He buys fuel from Mely to make more each day.")
            elif location == "nell_shop":
                lines = ("Nell is the other inventor in Copperside.",
                         "Open the Inventors ledger to track her bids and deliveries.")
            elif location == "farm":
                lines = ("The farm grows grain for the mill.",
                         "Open Businesses in the ledger to follow its stock and cash.")
            else:
                firm = village.businesses.get(location, {})
                lines = (f"{who} has {firm.get('cash', 0)} coins for wages and supplies.",
                         "Its machines and capacity are listed in the Town Ledger.")
        words(surface, heading, who, 307, 524)
        for row, line in enumerate(lines):
            clipped = line
            length = len(line)
            while regular.render(clipped, True, INK).get_width() > 656 and length > 4:
                length -= 1
                clipped = line[:length] + "..."
            words(surface, regular, clipped, 307, 572 + row * 30)
        if location == "market":
            words(surface, small, message[:70], 307, 636, COPPER)
        prompt = ("1 work   2 family   3 town   E / Esc close" if location.startswith("person:") else
                  "E buy bread   N next day   Esc close" if location == "market" else "E / Esc close")
        words(surface, small, prompt, 307, 670, TEAL)
