"""Mouse routes through the compact expedition instruments and recovery controls."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pygame
import adventure
import boiler_tower as tower
from game import Game
from test_adventure import design


class ExpeditionPresentationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.patches = [patch('game.SAVES_DIR', root / 'saves'),
                        patch('game.SAVE_FILE', root / 'old.json'),
                        patch('game.DESIGNS_FILE', root / 'designs.json')]
        for item in self.patches:
            item.start()
        self.g = Game()
        self.g.start_slot(1)

    def tearDown(self):
        pygame.quit()
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def test_receiver_instrument_buttons_turn_tune_and_open_own_circuit(self):
        g = self.g
        adventure.enter(g)
        s = adventure.state(g.village)
        s.update(receiver=True, decoder=True, survey_started=True, bearing=1, frequency=0)
        s['designs']['decoder'] = design('decoder').snapshot()
        adventure.close_notice(g)
        g.draw()
        g.handle_click((1048, 179), 1)
        self.assertEqual(s['bearing'], 2)
        g.draw()
        g.handle_click((1182, 179), 1)
        self.assertEqual(s['frequency'], 1)
        g.draw()
        g.handle_click((1120, 271), 1)
        self.assertEqual(g.scene, 'workshop')
        self.assertEqual(g.adventure_editor, 'decoder')

    def test_tower_compact_heal_and_recall_do_not_consume_extra_health(self):
        g = self.g
        s = adventure.state(g.village)
        s.update(expansion_complete=True, health=50)
        g.village.player_bread = 1
        tower.enter(g)
        adventure.close_notice(g)
        g.draw()
        g.handle_click((82, 131), 1)
        self.assertEqual(s['health'], 75)
        self.assertEqual(g.village.player_bread, 0)
        current = tower.state(g.village)
        current['position'] = [500., 5100.]
        g.draw()
        g.handle_click((230, 131), 1)
        self.assertEqual(current['position'], tower.landing_position(current['checkpoint']))
        self.assertEqual(s['health'], 75)
        self.assertFalse(g.tower_firing)


if __name__ == '__main__':
    unittest.main()
