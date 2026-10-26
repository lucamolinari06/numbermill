"""Visual motion regressions: real movement drives poses, not elapsed idle time."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
import unittest
from collections import defaultdict
import pygame
from town import Town


class TownAnimationTests(unittest.TestCase):
    def test_player_facing_and_distance_cycle(self):
        town = Town()
        keys = defaultdict(bool, {pygame.K_d: True})
        town.move(keys, 0.1)
        self.assertTrue(town._player_is_moving)
        self.assertEqual(town.player_facing, 'east')
        phase = town.walk_phase
        town.move(defaultdict(bool), 0.1)
        self.assertFalse(town._player_is_moving)
        self.assertEqual(town.walk_phase, phase)

    def test_every_npc_uses_travel_animation(self):
        for name in ('Ada', 'Bram', 'Agnes', 'Dara', 'Mely', 'Luca', 'Grace', 'Rowan'):
            town = Town()
            point = [600., 625.]
            town._travel(name, point, (700., 625.), 20)
            self.assertIn(name, town.people_moving)
            self.assertEqual(town.people_facing[name], 'east')
            self.assertGreater(town.people_walk_phase[name], 0)

    def test_walk_frames_and_directions_are_distinct(self):
        town = Town()
        frames = []
        for facing, phase in (('south', 0), ('south', 1.57), ('south', 4.71), ('north', 0), ('east', 0), ('west', 0)):
            surface = pygame.Surface((100, 110))
            town._villager(surface, 50, 65, (41, 102, 94), phase, True, facing, 'Boole')
            frames.append(pygame.image.tobytes(surface, 'RGB'))
        self.assertEqual(len(set(frames)), len(frames))

    def test_display_interpolates_each_frame_without_mutating_economy(self):
        town = Town()
        town.people['Ada'] = [655., 625.]
        town.display_people['Ada'] = [600., 625.]
        positions, phases = [], []
        for _ in range(15):
            town.update_visuals(1 / 60)
            positions.append(town.display_people['Ada'][0])
            phases.append(town.display_phase['Ada'])
        self.assertEqual(town.people['Ada'], [655., 625.])
        self.assertEqual(len(set(positions)), 15)
        self.assertEqual(len(set(phases)), 15)
        self.assertAlmostEqual(positions[-1], 627.5)
        self.assertEqual(town.display_facing['Ada'], 'east')
        town.update_visuals(.25)
        town.update_visuals(1 / 60)
        self.assertNotIn('Ada', town.display_moving)

    def test_hit_testing_tracks_displayed_person(self):
        town = Town()
        town.people['Ada'] = [655., 625.]
        town.display_people['Ada'] = [600., 625.]
        # Camera at initial player position is (115,310).
        self.assertEqual(town.person_at((485, 300)), 'Ada')
        self.assertIsNone(town.person_at((540, 300)))


class DistrictRenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_intersection_keeps_continuous_paving(self):
        from town import WORLD_W, WORLD_H
        surface = pygame.Surface((WORLD_W, WORLD_H))
        Town()._ground(surface)
        # Crossing the former north/south road edges must never expose grass.
        for x in range(1075, 1165):
            for y in range(605, 630):
                r,g,b=surface.get_at((x,y))[:3]
                self.assertGreater(r,g)
                self.assertGreater(g-b,12)

    def test_building_has_no_offset_green_shadow(self):
        surface = pygame.Surface((500, 400))
        surface.fill((1, 2, 3))
        font = pygame.font.SysFont('consolas', 16)
        Town()._building(surface, (250, 300), 'mill', font, font)
        # Old shadow extended past the east foundation and beneath the door.
        self.assertEqual(tuple(surface.get_at((390, 280)))[:3], (1, 2, 3))
        self.assertEqual(tuple(surface.get_at((250, 298)))[:3], (1, 2, 3))

    def test_goggle_lenses_follow_facing(self):
        lens = (91, 150, 150)
        for facing, expected in (('south', 2), ('north', 0), ('east', 1), ('west', 1)):
            surface = pygame.Surface((100, 110))
            Town()._villager(surface, 50, 65, (61, 121, 115), facing=facing, name='Boole')
            # A lens center in each expected horizontal location.
            actual = sum(tuple(surface.get_at((x, 29)))[:3] == lens for x in (41, 45, 55, 59))
            self.assertEqual(actual, expected, facing)

    def test_new_district_has_clear_front_door_access(self):
        from town import LOCATIONS, WORLD_W
        self.assertGreater(WORLD_W, 2400)
        for key in ('sawmill', 'foundry', 'toolmaker'):
            x, y = LOCATIONS[key]
            self.assertFalse(Town._inside_building(x, y + 25))
            self.assertTrue(Town._inside_building(x, y - 70))
