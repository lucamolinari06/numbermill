"""Natural water contours, safe old positions and actual guarded crossings."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
from collections import deque, defaultdict
import math
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pygame
import adventure
import mosswater
from economy import Village
from town_companion import Companion


class MosswaterShorelineTests(unittest.TestCase):
    def field(self,position):
        g=SimpleNamespace(village=Village(),save_game=Mock(),adventure_time=0.,
                          adventure_cooldown=0.,adventure_speech_time=0.,adventure_phase=0.)
        s=adventure.state(g.village)
        s.update(position=list(position),interlock=True,range_gate=True)
        g.adventure_companion=Companion(position,adventure.blocked)
        return g,s

    def test_pond_centres_are_water_but_old_rectangular_corners_are_walkable(self):
        for left, top, width, height in mosswater.PONDS:
            self.assertTrue(mosswater.water_blocked(left + width / 2, top + height / 2))
            for point in ((left + 4, top + 4), (left + width - 4, top + 4),
                          (left + 4, top + height - 4), (left + width - 4, top + height - 4)):
                self.assertFalse(mosswater.blocked(*point), point)

    def test_rasterized_water_and_collision_share_every_contour(self):
        surface = pygame.Surface((mosswater.WIDTH, mosswater.HEIGHT), pygame.SRCALPHA)
        for polygon in mosswater.WATER_POLYGONS:
            pygame.draw.polygon(surface, 'white', polygon)
        checked = 0
        for left, top, width, height in mosswater.WATER_BOUNDS:
            for y in range(max(4, top), min(mosswater.HEIGHT - 4, top + height), 9):
                for x in range(max(4, left - 8), min(mosswater.WIDTH - 4, left + width + 8), 9):
                    samples = [surface.get_at((x + dx, y + dy)).a > 0
                               for dx, dy in ((0, 0), (-3, 0), (3, 0), (0, -3), (0, 3))]
                    # Ignore the one-pixel rasterization fringe at polygon edges.
                    if len(set(samples)) != 1:
                        continue
                    self.assertEqual(mosswater.water_blocked(x, y), samples[0], (x, y))
                    checked += 1
        self.assertGreater(checked, 5000)

    def test_new_river_banks_relocate_old_positions_locally_without_crossing(self):
        candidates = [(x, y) for y in range(240, 820, 5) for x in range(1130, 1330, 5)
                      if not 1180 <= x <= 1280 and mosswater.water_blocked(x, y)]
        self.assertTrue(candidates)
        for old in candidates[::max(1, len(candidates) // 20)]:
            new = mosswater.safe_bank_position(old)
            self.assertFalse(mosswater.blocked(*new), (old, new))
            self.assertLessEqual(math.dist(old, new), 200)
            self.assertGreaterEqual((old[0] - 1230) * (new[0] - 1230), 0)

    def test_player_and_follower_feet_stop_on_the_visible_pond_bank(self):
        g,s=self.field((2355.,600.))
        with patch('pygame.key.get_pressed',return_value=defaultdict(bool,{pygame.K_s:True})):
            for _ in range(80):
                adventure.update(g,.01)
                x,y=s['position']
                self.assertFalse(mosswater.water_blocked(x,y+adventure.FOOT_OFFSET))
                cx,cy=g.adventure_companion.position
                self.assertFalse(mosswater.water_blocked(cx,cy+adventure.FOOT_OFFSET))
        self.assertGreater(s['position'][1],600)
        self.assertLess(s['position'][1],628-adventure.FOOT_OFFSET)

    def test_legacy_anchors_recover_to_a_dry_foot_position(self):
        for old in ((2355.,627.),(2570.,1239.),(3535.,824.)):
            self.assertFalse(mosswater.blocked(*old))
            self.assertTrue(adventure.blocked(*old))
            new=adventure.safe_position(old)
            self.assertFalse(adventure.blocked(*new))
            self.assertLess(math.dist(old,new),40)
            follower=Companion(new,adventure.blocked)
            self.assertFalse(adventure.blocked(*follower.position))

    def test_upper_and_lower_bridge_edges_trigger_real_gate_recovery(self):
        cases=(('interlock',(1170.,422.),(1090.,540.)),
               ('interlock',(1170.,542.),(1090.,540.)),
               ('range_gate',(3138.,1182.),(3050.,1300.)),
               ('range_gate',(3138.,1322.),(3050.,1300.)))
        for key,position,checkpoint in cases:
            for cooldown in (0.,1.):
                with self.subTest(gate=key,position=position,cooldown=cooldown):
                    g,s=self.field(position)
                    s[key]=False
                    g.adventure_cooldown=cooldown
                    with patch('pygame.key.get_pressed',return_value=defaultdict(bool,{pygame.K_d:True})):
                        adventure.update(g,.1)
                    self.assertEqual(s['position'],list(checkpoint))
                    self.assertEqual(s['health'],100 if cooldown else 75)
                    self.assertFalse(adventure.blocked(*s['position']))
                    self.assertFalse(adventure.blocked(*g.adventure_companion.position))

    def test_closed_bridge_hazard_areas_cannot_be_bypassed_around_curved_banks(self):
        def reachable(start, closed):
            seen, queue = {start}, deque([start])
            while queue:
                x, y = queue.popleft()
                for nxt in ((x + 10, y), (x - 10, y), (x, y + 10), (x, y - 10)):
                    if nxt in seen or adventure.blocked(*nxt):
                        continue
                    if any(left < nxt[0] < right and top < nxt[1]+adventure.FOOT_OFFSET < bottom
                           for left, right, top, bottom in closed):
                        continue
                    seen.add(nxt)
                    queue.append(nxt)
            return seen
        first = (1180, 1285, 435, 565)
        second = (3150, 3265, 1195, 1345)
        west = reachable((100, 690), (first, second))
        self.assertNotIn(mosswater.POINTS['survey'], west)
        basin = reachable((1730, 420), (second,))
        self.assertNotIn(mosswater.POINTS['artifact'], basin)
        for beacon in mosswater.BEACONS:
            self.assertIn(beacon['position'], basin)
        opened = reachable((2980, 1230), ())
        self.assertIn(mosswater.POINTS['artifact'], opened)


if __name__ == '__main__':
    unittest.main()
