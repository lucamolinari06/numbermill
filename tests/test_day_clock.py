"""Continuous day rollover, saved fractional time and the physical disc HUD."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

from copy import deepcopy
from dataclasses import asdict
import json
import math
import unittest

import pygame

import day_clock
import town_atmosphere as atmosphere
from daily_life import DAY_SECONDS, state, update_continuous
from economy import Village
from town import Town, TOWN_READOUT_RECT, MINIMAP_RECT


class DayClockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        from ui_theme import make_font
        cls.font = make_font(16)

    def setUp(self):
        self.village, self.town = Village(), Town()
        state(self.village)

    def test_night_palette_and_lamps_match_across_the_day_boundary(self):
        self.assertEqual(atmosphere.daylight(0), atmosphere.daylight(1))
        self.assertEqual(atmosphere.evening_light(0), atmosphere.evening_light(1))
        self.assertGreater(atmosphere.evening_light(0), .99)
        self.assertEqual(atmosphere.evening_light(.3), 0)
        self.assertGreater(atmosphere.daylight(.18)[0], atmosphere.daylight(0)[0])
        self.assertEqual(pygame.image.tobytes(day_clock.disc(0), 'RGBA'),
                         pygame.image.tobytes(day_clock.disc(1), 'RGBA'))

    def test_actual_rollover_advances_one_day_without_light_or_rotation_snap(self):
        # Exercise settlement and fractional carry, not a hand-built day reset.
        update_continuous(self.village, self.town, DAY_SECONDS-.01)
        before = atmosphere.clock_progress(self.village)
        day = self.village.day
        crossed = update_continuous(self.village, self.town, .02)
        after = atmosphere.clock_progress(self.village)
        self.assertEqual(crossed, 1)
        self.assertEqual(self.village.day, day+1)
        self.assertAlmostEqual(after, .01/DAY_SECONDS)
        self.assertEqual(atmosphere.daylight(before), atmosphere.daylight(after))
        self.assertLess(abs(atmosphere.evening_light(before)-atmosphere.evening_light(after)), .001)
        turn = 1-day_clock.cycle_phase(before)+day_clock.cycle_phase(after)
        self.assertLess(turn*math.tau, .004)

    def test_fractional_saved_time_drives_clock_without_mutating_state(self):
        current = state(self.village)
        current.update(elapsed=30., accumulator=.125)
        before = deepcopy(vars(self.village))
        self.assertAlmostEqual(atmosphere.clock_progress(self.village), 30.125/DAY_SECONDS)
        surface = pygame.Surface((1280, 760))
        day_clock.draw(surface, self.village, self.font)
        self.assertEqual(vars(self.village), before)
        from game import village_from_data
        loaded = village_from_data(json.loads(json.dumps(asdict(self.village))))
        self.assertEqual(atmosphere.clock_progress(loaded), atmosphere.clock_progress(self.village))
        second = pygame.Surface((1280, 760))
        day_clock.draw(second, loaded, self.font)
        self.assertEqual(pygame.image.tobytes(surface, 'RGB'), pygame.image.tobytes(second, 'RGB'))

    def test_disc_moves_forward_smoothly_and_has_short_nights(self):
        phases = [day_clock.cycle_phase(i/18000) for i in range(18001)]
        self.assertTrue(all(0 <= b-a < .0003 for a, b in zip(phases, phases[1:])))
        self.assertEqual(phases[0], 0)
        self.assertEqual(phases[-1], 1)
        self.assertAlmostEqual(day_clock.cycle_phase(.085), .25)
        self.assertAlmostEqual(day_clock.cycle_phase(.915), .75)
        for join in (.085, .5, .915):
            left = (day_clock.cycle_phase(join)-day_clock.cycle_phase(join-.00001))/.00001
            right = (day_clock.cycle_phase(join+.00001)-day_clock.cycle_phase(join))/.00001
            self.assertAlmostEqual(left, right, places=2)

    def test_hud_clock_is_separate_bounded_and_pointer_is_fixed(self):
        self.assertFalse(day_clock.CLOCK_RECT.colliderect(TOWN_READOUT_RECT))
        self.assertFalse(day_clock.CLOCK_RECT.colliderect(MINIMAP_RECT))
        self.assertLess(day_clock.CLOCK_RECT.right, 466)  # Journal control.
        surface = pygame.Surface((1280,760)); surface.fill((255,0,255))
        day_clock.draw(surface, self.village, self.font)
        pointer = pygame.Rect(day_clock.CLOCK_RECT.centerx-3, day_clock.CLOCK_RECT.top+3, 7, 3)
        fixed = pygame.image.tobytes(surface.subsurface(pointer), 'RGB')
        for elapsed in (40., 90., 170.):
            state(self.village)['elapsed'] = elapsed
            day_clock.draw(surface, self.village, self.font)
            self.assertEqual(pygame.image.tobytes(surface.subsurface(pointer), 'RGB'), fixed)
        self.assertEqual(surface.get_at((day_clock.CLOCK_RECT.right+5, 60))[:3], (255,0,255))

    def test_empty_and_stale_legacy_clocks_remain_read_only(self):
        for current in ({}, {'day':self.village.day-1, 'elapsed':180., 'accumulator':.4}):
            self.village.daily_life = current
            before = deepcopy(vars(self.village))
            self.assertEqual(atmosphere.clock_progress(self.village), 0.)
            day_clock.draw(pygame.Surface((1280,760)), self.village, self.font)
            self.assertEqual(vars(self.village), before)


if __name__ == '__main__':
    unittest.main()
