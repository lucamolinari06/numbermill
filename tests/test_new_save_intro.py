"""Player-facing new-save paths show context without spending village time."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pygame
from game import Game, load_slot


class NewSaveIntroTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.patches = [patch("game.SAVES_DIR", root / "saves"),
                        patch("game.SAVE_FILE", root / "legacy.json"),
                        patch("game.DESIGNS_FILE", root / "designs.json")]
        for item in self.patches:
            item.start()
        self.game = Game()

    def tearDown(self):
        pygame.quit()
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def key(self, key):
        self.game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode=""))

    def test_new_game_scroll_pauses_world_and_begin_enters_town(self):
        g = self.game
        g.new_game()
        self.assertEqual((g.scene, g.menu_page), ("menu", "new_save"))
        self.assertIsInstance(load_slot(1), dict)
        state = deepcopy(g.village.__dict__)
        for key in (pygame.K_n, pygame.K_e, pygame.K_b, pygame.K_2):
            self.key(key)
            g.update(1)
        self.assertEqual(g.village.__dict__, state)
        self.assertIsNone(load_slot(2))
        g.draw()
        self.key(pygame.K_RETURN)
        self.assertEqual(g.scene, "town")
        self.assertIsNone(g.chapter_view)
        self.assertEqual(g.village.__dict__, state)

    def test_slot_keyboard_creation_shows_scroll_but_reload_skips_it(self):
        g = self.game
        g.menu_page = "slots"
        self.key(pygame.K_3)
        self.assertEqual(g.menu_page, "new_save")
        self.assertEqual(g.current_slot, 3)
        self.key(pygame.K_ESCAPE)
        g.return_to_menu()
        g.menu_page = "slots"
        self.key(pygame.K_3)
        self.assertEqual(g.scene, "town")

    def test_slot_create_button_and_scroll_begin_button(self):
        g = self.game
        g.menu_page = "slots"
        g.draw()
        g.handle_click((900, 230), 1)
        self.assertEqual(g.menu_page, "new_save")
        g.draw()
        self.assertEqual(len(g.buttons), 1)
        g.handle_click((10, 10), 1)
        self.assertEqual(g.menu_page, "new_save")
        g.handle_click(g.buttons[0][0].center, 1)
        self.assertEqual(g.scene, "town")

    def test_closing_during_scroll_preserves_created_save(self):
        g = self.game
        g.new_game()
        saved = deepcopy(load_slot(1))
        g.handle_event(pygame.event.Event(pygame.QUIT))
        self.assertFalse(g.running)
        self.assertEqual(load_slot(1), saved)
        loaded = Game()
        loaded.start_slot(1, introduce=True)
        self.assertEqual(loaded.scene, "town")
