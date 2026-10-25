"""Display changes must preserve precise input, paused state and save isolation."""
import json
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pygame
import presentation
from game import Game, load_slot


class PresentationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.paths = [patch("game.SAVES_DIR", self.root/"saves"),
                      patch("game.SAVE_FILE", self.root/"old.json"),
                      patch("game.DESIGNS_FILE", self.root/"designs.json")]
        for item in self.paths:
            item.start()
        self.game = Game()

    def tearDown(self):
        pygame.quit()
        for item in reversed(self.paths):
            item.stop()
        self.temp.cleanup()

    def key(self, key, mod=0):
        self.game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, mod=mod, unicode=""))

    def test_mapping_wide_tall_and_native_windows_keeps_letterbox_outside(self):
        for size in ((1280, 760), (1920, 1080), (1000, 1000), (640, 380)):
            rect = presentation.viewport_rect(size)
            center = presentation.logical_position(rect.center, size)
            self.assertLessEqual(abs(center[0] - 640), 1)
            self.assertLessEqual(abs(center[1] - 380), 1)
            self.assertEqual(presentation.logical_position(rect.topleft, size), (0, 0))
            self.assertEqual(presentation.logical_position(rect.bottomright, size), (-1000, -1000))
            self.assertEqual(presentation.logical_position((-1, -1), size), (-1000, -1000))

    def test_sharp_fullscreen_uses_uniform_pixels_and_matching_input(self):
        for size, factor in (((3840, 2160), 2), ((2560, 1600), 2), ((1920, 1080), 1)):
            rect = presentation.viewport_rect(size, integer=True)
            self.assertEqual(rect.size, (1280 * factor, 760 * factor))
            self.assertEqual(rect.center, (size[0] // 2, size[1] // 2))
            self.assertEqual(presentation.logical_position(rect.center, size, integer=True), (640, 380))
            self.assertEqual(presentation.logical_position((0, 0), size, integer=True), (-1000, -1000))
        g = self.game
        g.settings["fullscreen"] = True
        g.viewport.window = pygame.display.set_mode((1920, 1080))
        self.assertEqual(g.viewport.pointer((0, 0)), (0, 0))
        self.assertEqual(g.viewport.pointer((960, 540)), (640, 380))
        self.assertEqual(g.viewport.pointer((1919, 1079)), (1279, 759))
        g.viewport.canvas.fill((183, 72, 41))
        g.viewport.present()
        for point in ((0, 0), (1919, 0), (0, 1079), (1919, 1079)):
            self.assertEqual(g.viewport.window.get_at(point)[:3], (183, 72, 41))
        g.settings["smooth_scaling"] = True
        self.assertEqual(g.viewport.pointer((960, 540)), (640, 380))

    def test_fullscreen_uses_selected_monitor_origin_and_restores_window_position(self):
        g = self.game
        geometry = {"monitor": pygame.Rect(-3840, 0, 3840, 2160),
                    "work": pygame.Rect(-3840, 0, 3840, 2100),
                    "window": pygame.Rect(-1920, 500, 1280, 760)}
        with patch("presentation.pygame.display.get_driver", return_value="windows"), \
                patch("presentation.window_display.geometry", return_value=geometry), \
                patch("presentation.window_display.position") as move:
            g.toggle_preference("fullscreen")
            self.assertEqual(g.viewport.window.get_size(), (3840, 2160))
            move.assert_called_with(geometry["monitor"], resize=True)
            g.toggle_preference("fullscreen")
            self.assertEqual(move.call_args.args[0].topleft, (-1920, 500))
            self.assertEqual(g.viewport.window.get_size(), (1280, 760))

    def test_resized_window_routes_real_mouse_event_to_same_button(self):
        g = self.game
        g.start_slot(1)
        g.pause_menu_open = True
        g.handle_event(pygame.event.Event(pygame.VIDEORESIZE, size=(1600, 1000), w=1600, h=1000))
        g.draw()
        self.assertEqual(g.screen.get_size(), (1280, 760))
        rect = presentation.viewport_rect(g.viewport.window.get_size())
        resume = g.pause_buttons()[0][0].center
        physical = (round(rect.x + resume[0]*rect.width/1280), round(rect.y + resume[1]*rect.height/760))
        g.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(5, 5), button=1))
        self.assertTrue(g.pause_menu_open)
        g.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=physical, button=1))
        self.assertFalse(g.pause_menu_open)

    def test_settings_and_controls_freeze_world_and_preserve_parent_pause(self):
        g = self.game
        g.start_slot(1)
        g.draw()
        g.pause_menu_open = True
        g.open_settings()
        g.draw()
        village = deepcopy(vars(g.village))
        g.update(90)
        self.assertEqual(vars(g.village), village)
        g.controls_open = True
        g.draw()
        self.key(pygame.K_ESCAPE)
        self.assertFalse(g.controls_open)
        self.assertTrue(g.settings_open)
        self.key(pygame.K_ESCAPE)
        self.assertFalse(g.settings_open)
        self.assertTrue(g.pause_menu_open)
        self.key(pygame.K_ESCAPE)
        self.assertFalse(g.pause_menu_open)

    def test_preferences_roundtrip_separate_from_save_and_skip_invalid_data(self):
        g = self.game
        g.start_slot(1)
        original = deepcopy(load_slot(1))
        g.toggle_preference("reduced_motion")
        g.toggle_preference("smooth_scaling")
        self.assertEqual(load_slot(1), original)
        loaded = Game()
        self.assertTrue(loaded.reduced_motion)
        self.assertTrue(loaded.settings["smooth_scaling"])
        g.preferences_path.write_text('{"fullscreen":"false","last_slot":99,"window_size":[-1,99999]}', encoding="utf-8")
        prefs = presentation.load_preferences(g.preferences_path)
        self.assertFalse(prefs["fullscreen"])
        self.assertIsNone(prefs["last_slot"])
        self.assertEqual(prefs["window_size"], [640, 2160])
        g.preferences_path.write_text("broken", encoding="utf-8")
        self.assertEqual(presentation.load_preferences(g.preferences_path), presentation.DEFAULTS)

    def test_new_game_uses_empty_slot_and_continue_remembers_selected_save(self):
        g = self.game
        self.assertIsNone(g.continue_slot())
        g.new_game()
        self.assertEqual(g.current_slot, 1)
        g.village.coins = 91
        g.save_game()
        g.new_game()
        self.assertEqual(g.current_slot, 2)
        self.assertEqual(load_slot(1)["village"]["coins"], 91)
        self.assertEqual(Game().continue_slot(), 2)
        for slot in range(3, 6):
            g.start_slot(slot)
        g.return_to_menu()
        before = [deepcopy(load_slot(slot)) for slot in range(1, 6)]
        g.new_game()
        self.assertEqual(g.menu_page, "slots")
        self.assertEqual([load_slot(slot) for slot in range(1, 6)], before)

    def test_keyboard_menu_focus_activates_settings_without_running_world(self):
        g = self.game
        g.start_slot(1)
        g.pause_menu_open = True
        g.draw()
        self.key(pygame.K_UP)
        self.assertEqual(g.focus_index, len(g.buttons) - 1)
        self.key(pygame.K_DOWN)
        self.assertEqual(g.focus_index, 0)
        self.key(pygame.K_TAB)
        self.key(pygame.K_RETURN)
        self.assertTrue(g.settings_open)
        self.assertTrue(g.pause_menu_open)
        g.draw()
        self.key(pygame.K_TAB)
        self.key(pygame.K_TAB)
        self.key(pygame.K_SPACE)
        self.assertTrue(g.settings["smooth_scaling"])

    def test_losing_window_focus_pauses_live_game(self):
        g = self.game
        g.start_slot(1)
        g.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.assertTrue(g.pause_menu_open)
        before = deepcopy(vars(g.village))
        g.update(5)
        self.assertEqual(vars(g.village), before)

    def test_preferences_survive_fullscreen_toggle_without_replacing_logical_canvas(self):
        g = self.game
        original = g.screen
        self.key(pygame.K_F11)
        self.assertTrue(g.settings["fullscreen"])
        self.key(pygame.K_F11)
        self.assertFalse(g.settings["fullscreen"])
        self.assertIs(g.screen, original)
        self.assertFalse(json.loads(g.preferences_path.read_text())["fullscreen"])

    def test_failed_fullscreen_switch_restores_windowed_play(self):
        g = self.game
        original = g.screen
        with patch.object(g.viewport, "configure", side_effect=[pygame.error("display rejected"), None]):
            self.key(pygame.K_F11)
        self.assertFalse(g.settings["fullscreen"])
        self.assertIs(g.screen, original)
        self.assertTrue(g.running)
        self.assertIn("Windowed mode restored", g.message)
        self.assertFalse(json.loads(g.preferences_path.read_text())["fullscreen"])

    def test_old_river_save_recovers_on_dry_bank_without_changing_progress(self):
        import town_water
        from town import WORLD_W, WORLD_H
        g = self.game
        g.start_slot(1)
        g.town.player_x, g.town.player_y = 500., 1500.
        g.village.coins = 93
        g.save_game()
        loaded = Game()
        loaded.start_slot(1)
        self.assertEqual(loaded.village.coins, 93)
        self.assertEqual(loaded.town.player_x, 500.)
        self.assertLess(abs(loaded.town.player_y - 1500), 100)
        self.assertFalse(town_water.blocked(loaded.town.player_x, loaded.town.player_y + 18, WORLD_W, WORLD_H))
        self.assertFalse(loaded.town._companion_blocked(*loaded.town.companion.position))


if __name__ == "__main__":
    unittest.main()
