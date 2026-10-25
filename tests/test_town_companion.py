"""Walking companion continuity, corner following and player recognition."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import math
import unittest
from collections import defaultdict
import pygame
from town import Town
from town_companion import Companion


class WalkingCompanionTests(unittest.TestCase):
    def test_walking_shannon_is_clickable_with_camera_offset(self):
        from town import WORLD_W, WORLD_H, WIDTH, HEIGHT
        from dialogue import conversation
        from economy import Village
        town = Town()
        town.people = {}
        town.player_x, town.player_y = 1100, 700
        town.companion.position = (1052, 700)
        camera_x = max(0, min(WORLD_W - WIDTH, int(town.player_x - WIDTH // 2)))
        camera_y = max(0, min(WORLD_H - HEIGHT, int(town.player_y - HEIGHT // 2)))
        self.assertEqual(town.person_at((1052 - camera_x, 700 - camera_y)), 'Shannon')
        village = Village()
        paragraphs = [conversation(village, 'Shannon', topic)
                      for topic in ('work', 'family', 'town', 'hopes')]
        self.assertEqual(len({tuple(lines) for lines in paragraphs}), 4)
        self.assertTrue(all('away from the village' not in ' '.join(lines) for lines in paragraphs))

    def test_follows_at_a_gap_then_settles_without_idle_walking(self):
        follower = Companion((400, 400), lambda x, y: False, "east")
        for frame in range(1, 121):
            follower.update((400 + frame * 250 / 60, 400), 1 / 60)
        self.assertAlmostEqual(follower.position[0], 900 - follower.GAP)
        self.assertEqual(follower.facing, "east")
        self.assertTrue(follower.moving)
        position, phase = follower.position, follower.phase
        for _ in range(120):
            follower.update((900, 400), 1 / 60)
        self.assertEqual(follower.position, position)
        self.assertEqual(follower.phase, phase)
        self.assertFalse(follower.moving)
        self.assertLessEqual(len(follower.path), 3)

    def test_follows_around_corner_instead_of_cutting_diagonally(self):
        follower = Companion((400, 400), lambda x, y: False, "east")
        for x in range(405, 505, 5):
            follower.update((x, 400), .02)
        positions = []
        for y in range(405, 505, 5):
            follower.update((500, y), .02)
            positions.append(follower.position)
        self.assertTrue(all(abs(y - 400) < 1e-6 or abs(x - 500) < 1e-6 for x, y in positions))
        self.assertAlmostEqual(follower.position[1], 500 - follower.GAP)
        self.assertEqual(follower.facing, "south")

    def test_world_collision_slides_keep_shannon_on_walkable_trail(self):
        town = Town()
        for key, frames in ((pygame.K_d, 55), (pygame.K_w, 65), (pygame.K_a, 40), (pygame.K_s, 25)):
            for _ in range(frames):
                town.move(defaultdict(bool, {key: True}), 1 / 60)
                self.assertFalse(town._companion_blocked(*town.companion.position))
                self.assertLess(math.dist(town.companion.position, (town.player_x, town.player_y)), 80)
        for _ in range(60):
            town.rest(1 / 60)
        self.assertFalse(town._player_is_moving)
        self.assertFalse(town.companion.moving)

    def test_relocation_resets_trail_and_avoids_obstructed_spawn(self):
        town = Town()
        town.player_x, town.player_y = 1000, 290
        town.companion.update((1000, 290), .02)
        self.assertFalse(town._companion_blocked(*town.companion.position))
        self.assertLessEqual(math.dist(town.companion.position, (1000, 290)), 49)
        self.assertLessEqual(len(town.companion.path), 2)

    def test_player_differs_from_luca_in_every_direction_even_with_same_coat(self):
        town = Town()
        for facing in ("north", "south", "east", "west"):
            player, luca = pygame.Surface((100, 110)), pygame.Surface((100, 110))
            for surface, name in ((player, "Boole"), (luca, "Luca")):
                town._villager(surface, 50, 65, (61, 121, 115), facing=facing, name=name)
            self.assertNotEqual(pygame.image.tobytes(player, "RGB"), pygame.image.tobytes(luca, "RGB"))

    def test_companion_walk_poses_and_directions_render_distinctly(self):
        follower = Companion((400, 400), lambda x, y: False)
        frames = []
        for facing, phase in (("south", 0), ("south", 1.57), ("south", 4.71), ("north", 0), ("east", 0), ("west", 0)):
            follower.facing, follower.phase, follower.moving = facing, phase, True
            surface = pygame.Surface((80, 90))
            follower.draw(surface, 40, 50)
            frames.append(pygame.image.tobytes(surface, "RGB"))
        self.assertEqual(len(set(frames)), len(frames))


if __name__ == "__main__":
    unittest.main()
