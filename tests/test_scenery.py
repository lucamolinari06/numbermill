"""Street clearances cover the artwork, including foliage and sign boards."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
import unittest
import pygame
from town import (Town, LOCATIONS, WORLD_W, WORLD_H, decoration_bounds,
                  decoration_layout, scenery_exclusions)


class SceneryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_decorations_leave_streets_and_entrances_clear(self):
        layout = decoration_layout()
        self.assertGreaterEqual(len(layout), 25)
        blocked = scenery_exclusions()
        previous = []
        for kind, x, y, label in layout:
            rect = decoration_bounds(kind, x, y)
            with self.subTest(kind=kind, position=(x, y)):
                self.assertFalse(any(rect.colliderect(other) for other in blocked))
                self.assertFalse(any(rect.colliderect(other) for other in previous))
            previous.append(rect)
        self.assertEqual([entry[3] for entry in layout if entry[0] == 'sign'],
                         ['ARTISANS >', '< CENTER'])

    def test_rendered_art_fits_reserved_bounds(self):
        import random
        surface = pygame.Surface((WORLD_W, WORLD_H), pygame.SRCALPHA)
        for kind, x, y, label in decoration_layout():
            surface.fill((0, 0, 0, 0))
            Town._decoration(surface, random.Random(42), kind, x, y, label)
            with self.subTest(kind=kind, position=(x, y)):
                self.assertTrue(decoration_bounds(kind, x, y).contains(surface.get_bounding_rect()))

    def test_well_court_has_clear_space_and_keeps_its_surrounding_furniture(self):
        import town_art
        layout = decoration_layout()
        for entry in (("well", 880, 868, ""), ("lamp", 970, 885, ""),
                      ("bench", 730, 815, ""), ("planter", 730, 870, ""),
                      ("planter", 1000, 850, "")):
            self.assertIn(entry, layout)
        for kind, x, y, _ in layout:
            if kind != "well":
                self.assertFalse(decoration_bounds(kind, x, y).colliderect(
                    town_art.WELL_COURT.inflate(16, 16)), (kind, x, y))

    def test_bakery_opening_rebuilds_cached_town(self):
        from economy import Village
        village = Village()
        town = Town()
        surface = pygame.Surface((1280, 760))
        fonts = tuple(pygame.font.SysFont('consolas', size) for size in (14, 18, 24, 32))
        town.draw(surface, fonts, village, None, '')
        before = town.background
        village.businesses['east_bakery'] = {}
        town.draw(surface, fonts, village, None, '')
        self.assertIsNot(before, town.background)
        x, y = LOCATIONS['east_bakery']
        rect = pygame.Rect(x - 130, y - 230, 260, 230)
        self.assertNotEqual(pygame.image.tobytes(before.subsurface(rect), 'RGB'),
                            pygame.image.tobytes(town.background.subsurface(rect), 'RGB'))
        self.assertFalse(town._inside_building(x, y + 25))
        self.assertTrue(town._inside_building(x, y - 70))

    def test_bakery_routes_from_every_door_stay_clear(self):
        destination = LOCATIONS['east_bakery']
        for origin in LOCATIONS.values():
            for start, end in ((origin, destination), (destination, origin)):
                town = Town()
                point = list(map(float, start))
                with self.subTest(start=start, end=end):
                    for _ in range(1000):
                        town._travel('Jun', point, end, 11)
                        self.assertFalse(town._inside_building(*point), point)
                        if not town.routes['Jun']:
                            break
                    self.assertLess(pygame.Vector2(point).distance_to(end), 3)

    def test_eastern_trips_use_eastern_connector(self):
        town = Town()
        point = list(map(float, LOCATIONS['home_6']))
        town._travel('Jun', point, LOCATIONS['east_bakery'], 0)
        self.assertEqual(town.routes['Jun'][1][0], 1630)
        self.assertEqual(town.routes['Jun'][2][0], 1630)

    def test_grace_visits_client_for_every_available_job(self):
        from economy import Village
        from commissions import COMMISSIONS
        from town import GRACE_JOB_DESTINATIONS
        self.assertTrue(set(COMMISSIONS).issubset(GRACE_JOB_DESTINATIONS))
        for job, destination in GRACE_JOB_DESTINATIONS.items():
            village = Village()
            for key, offer in village.offers.items():
                offer['status'] = 'bid' if key == job else 'locked'
            village.offers[job] = {'status': 'bid'}
            town = Town()
            town.update_people(village, .5)
            self.assertEqual(town.route_targets['Grace'], LOCATIONS[destination])
