"""Startup transitions must not dispatch the begin key into the menu."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

import pygame
from game import Game
from opening_screen import OpeningScreen


class OpeningScreenTests(unittest.TestCase):
    def test_wrap_and_blend_are_continuous(self):
        screen = OpeningScreen("assets/loading")
        self.assertEqual(len(screen.paths), 8)
        screen.elapsed = 6
        self.assertEqual(screen.frame(), (0, 0))
        screen.elapsed = 7
        self.assertAlmostEqual(screen.frame()[1], .5)
        screen.elapsed = 8
        self.assertEqual(screen.frame(), (1, 0))
        screen.elapsed = 8 * len(screen.paths)
        self.assertEqual(screen.frame(), (0, 0))

    def test_begin_event_is_consumed_and_quit_remains_available(self):
        game = Game.__new__(Game)
        game.opening_screen = OpeningScreen("assets/loading")
        game.handle_key = Mock()
        game.exit_game = Mock()
        game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        game.handle_key.assert_not_called()
        game.handle_event(pygame.event.Event(pygame.QUIT))
        game.exit_game.assert_called_once()
        for _ in range(6):
            game.opening_screen.update(.1)
        self.assertTrue(game.opening_screen.finished)

    def test_reduced_motion_is_static_and_immediately_dismissible(self):
        screen = OpeningScreen("assets/loading", True)
        screen.update(30)
        self.assertEqual(screen.elapsed, 0)
        screen.begin()
        screen.update(.01)
        self.assertTrue(screen.finished)

    def test_missing_art_has_a_drawable_fallback(self):
        pygame.init()
        pygame.display.set_mode((320, 200))
        try:
            with tempfile.TemporaryDirectory() as directory:
                screen = OpeningScreen(directory)
                screen.draw(pygame.Surface((320, 200)), pygame.font.Font(None, 16))
                Path(directory, "broken.png").write_bytes(b"bad image")
                screen = OpeningScreen(directory)
                screen.draw(pygame.Surface((320, 200)), pygame.font.Font(None, 16))
        finally:
            pygame.quit()
