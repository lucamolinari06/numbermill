"""Live mornings preserve the same bounded economy and saved fractional time."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
import json
import unittest
from dataclasses import asdict
from unittest.mock import patch
from daily_life import update_continuous, DAY_SECONDS, state
from economy import Village
from game import Game, village_from_data
from town import Town


class ContinuousDaysTests(unittest.TestCase):
    def test_live_days_match_explicit_fast_forward(self):
        live, manual = Village(), Village()
        town = Town()
        manual_town = Town()
        self.assertEqual(update_continuous(live, town, DAY_SECONDS * 3), 3)
        for _ in range(3):
            manual.advance_day(manual_town)
        self.assertEqual(asdict(live), asdict(manual))
        self.assertEqual(live.day, 4)
        self.assertFalse(state(live)['settled'])

    def test_fractional_frame_and_reload_cross_midnight_without_losing_time(self):
        live, town = Village(), Town()
        update_continuous(live, town, 179.8)
        loaded = village_from_data(json.loads(json.dumps(asdict(live))))
        update_continuous(live, town, .4)
        update_continuous(loaded, Town(), .4)
        self.assertEqual(asdict(live), asdict(loaded))
        self.assertEqual(live.day, 2)
        self.assertAlmostEqual(state(live)['accumulator'], .2)
        update_continuous(live, town, .3)
        self.assertEqual(state(live)['elapsed'], .5)

    def test_loaded_settled_day_resumes_without_repeating_its_wages(self):
        live, town = Village(), Town()
        live.update_life(town, DAY_SECONDS)
        manual = village_from_data(json.loads(json.dumps(asdict(live))))
        manual.advance_day()
        manual.update_life(Town(), .5)
        self.assertEqual(update_continuous(live, town, .5), 1)
        self.assertEqual(asdict(live), asdict(manual))

    def test_game_rollover_autosaves_menu_pauses_and_suspend_does_not_skip_days(self):
        game = Game()
        game.scene = 'town'
        game.village.update_life(game.town, DAY_SECONDS - .5)
        with patch.object(game, 'save_game') as save:
            game.update(.5)
            self.assertEqual(game.village.day, 2)
            save.assert_called_once()
        before = asdict(game.village)
        game.scene = 'menu'
        game.update(1000)
        self.assertEqual(asdict(game.village), before)
        game.scene = 'town'
        game.update(1000)
        self.assertEqual(game.village.day, 2)
        self.assertEqual(state(game.village)['elapsed'], 1)
