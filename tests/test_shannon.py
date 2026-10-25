"""Companion navigation uses the live town event handlers and isolated saves."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pygame
from game import Game
from daily_life import state, DAY_SECONDS
from shannon import BODY, ACTIONS, NODES, PANEL
from town import MINIMAP_RECT, Town, LOCATIONS
from ui_theme import GOLD


class ShannonTests(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).resolve().parents[1] / '.test-tmp'
        scratch.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        root = Path(self.temp.name)
        self.paths = [patch('game.SAVES_DIR', root / 'saves'),
                      patch('game.SAVE_FILE', root / 'legacy.json'),
                      patch('game.DESIGNS_FILE', root / 'designs.json')]
        for item in self.paths:
            item.start()
        self.game = Game()
        self.game.start_slot(2)

    def tearDown(self):
        pygame.quit()
        for item in reversed(self.paths):
            item.stop()
        self.temp.cleanup()

    def choose(self, action):
        game = self.game
        if not game.shannon.open:
            game.handle_click(game.shannon.body.center, 1)
        self.assertTrue(game.shannon.open)
        game.shannon.update(.3)
        game.draw()
        game.handle_click(NODES[ACTIONS.index(action)], 1)

    def test_radial_navigation_and_next_day_use_existing_actions(self):
        game = self.game
        for action, scene in [('ledger', 'ledger'), ('contracts', 'contracts'), ('map', 'ledger')]:
            game.scene = 'town'
            self.choose(action)
            self.assertEqual(game.scene, scene)
            self.assertFalse(game.shannon.open)
            if action == 'map':
                self.assertEqual(game.ledger_tab, 'Map')
        game.scene = 'town'
        day = game.village.day
        self.choose('next_day')
        self.assertEqual(game.village.day, day + 1)
        self.assertEqual(game.scene, 'town')

    def test_news_and_help_remain_open_and_context_action_visits_door(self):
        game = self.game
        game.town_dialogue = 'person:Mely'
        self.choose('news')
        self.assertIsNone(game.town_dialogue)
        self.assertEqual(game.shannon.page, 'news')
        game.draw()
        self.choose('help')
        self.assertEqual(game.shannon.page, 'help')
        game.draw()
        self.choose('news')
        game.town.player_x, game.town.player_y = LOCATIONS['market']
        game.handle_click((550, 696), 1)
        self.assertEqual(game.town_dialogue, 'market')
        self.assertFalse(game.shannon.open)

    def test_overlay_consumes_panel_and_dismissal_clicks(self):
        game = self.game
        self.choose('help')
        with patch.object(game.town, 'person_at', return_value='Mely') as hit:
            game.handle_click(PANEL.center, 1)
            self.assertTrue(game.shannon.open)
            game.handle_click((900, 400), 1)
            self.assertFalse(game.shannon.open)
            self.assertIsNone(game.town_dialogue)
            hit.assert_not_called()
            game.handle_click((900, 400), 1)
            self.assertEqual(game.town_dialogue, 'person:Mely')

    def test_escape_closes_companion_before_pausing_and_resuming_town(self):
        game = self.game
        key = lambda code: pygame.event.Event(pygame.KEYDOWN, key=code, mod=0)
        game.handle_key(key(pygame.K_h))
        self.assertTrue(game.shannon.open)
        game.handle_key(key(pygame.K_ESCAPE))
        self.assertFalse(game.shannon.open)
        self.assertEqual(game.scene, 'town')
        game.handle_key(key(pygame.K_ESCAPE))
        self.assertEqual(game.scene, 'town')
        self.assertTrue(game.pause_menu_open)
        game.handle_key(key(pygame.K_ESCAPE))
        self.assertEqual(game.scene, 'town')
        self.assertFalse(game.pause_menu_open)

    def test_walking_shannon_pauses_and_respawns_beside_loaded_player(self):
        from collections import defaultdict
        import math
        game = self.game
        game.town.move(defaultdict(bool, {pygame.K_d: True}), .1)
        companion = game.town.companion
        before = (companion.position, companion.phase, companion.seconds)
        game.pause_menu_open = True
        game.update(10)
        self.assertEqual((companion.position, companion.phase, companion.seconds), before)
        game.save_game()
        player = (game.town.player_x, game.town.player_y)
        game.start_slot(2)
        self.assertEqual((game.town.player_x, game.town.player_y), player)
        self.assertLessEqual(math.dist(game.town.companion.position, player), 49)
        self.assertFalse(game.town._companion_blocked(*game.town.companion.position))

    def test_minimap_opens_full_map_and_marker_tracks_player(self):
        game = self.game
        x, y = MINIMAP_RECT.x + 1, MINIMAP_RECT.y + 1
        for wx, wy in [(500, 700), (2300, 1100)]:
            game.town.player_x, game.town.player_y = wx, wy
            game.draw()
            point = (round(x + wx * 190 / 2700), round(y + wy * 110 / 1560))
            self.assertEqual(tuple(game.screen.get_at(point))[:3], GOLD)
        game.handle_click(MINIMAP_RECT.center, 1)
        self.assertEqual(game.scene, 'ledger')
        self.assertEqual(game.ledger_tab, 'Map')

    def test_long_news_remains_available_through_pages(self):
        game = self.game
        game.message = ' '.join(f'notice{i}' for i in range(180))
        self.choose('news')
        lines = game.shannon.news_lines(game)
        text = ' '.join(line for line, color in lines)
        for i in range(180):
            self.assertIn(f'notice{i}', text)
        for line, color in lines:
            self.assertLessEqual(game.small.render(line, True, color).get_width(), 440)
        pages = (len(lines) + 7) // 8
        for page in range(pages):
            self.assertEqual(game.shannon.news_page, page)
            game.draw()
            game.handle_click((730, 655), 1)
        self.assertEqual(game.shannon.news_page, pages - 1)
        game.handle_click((370, 655), 1)
        self.assertEqual(game.shannon.news_page, pages - 2)

    def test_companion_glides_out_and_reverses_without_jumping(self):
        from shannon import CENTER, OPEN_CENTER
        buddy = self.game.shannon
        self.assertEqual(buddy.center, CENTER)
        buddy.toggle(self.game)
        buddy.update(.15)
        halfway = buddy.center
        self.assertTrue(CENTER[0] < halfway[0] < OPEN_CENTER[0])
        buddy.toggle(self.game)
        self.assertEqual(buddy.center, halfway)
        buddy.update(.15)
        self.assertEqual(buddy.center, CENTER)
        buddy.toggle(self.game)
        buddy.update(.3)
        self.assertEqual(buddy.center, OPEN_CENTER)
        self.game.handle_click(buddy.body.center, 1)
        self.assertFalse(buddy.open)
        buddy.update(.3)
        self.assertEqual(buddy.center, CENTER)

    def test_clock_is_only_a_view_of_existing_day_progress(self):
        life = state(self.game.village)
        for elapsed, expected in [(0, '08:00'), (DAY_SECONDS / 2, '14:00'), (DAY_SECONDS, '20:00')]:
            life['elapsed'] = elapsed
            self.assertEqual(Town.clock_time(self.game.village), expected)
            self.assertEqual(life['elapsed'], elapsed)


if __name__ == '__main__':
    unittest.main()
