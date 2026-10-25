"""Exercise the live event path, including keys, clicks, and both wheel formats."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from collections import defaultdict
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import pygame

import computation
import ledger
from circuit import CommissionCase, Part
from commissions import COMMISSIONS
from game import Game
from town import LOCATIONS, WORLD_W, WORLD_H, WIDTH, HEIGHT


class InteractionRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.patches = [patch("game.SAVES_DIR", Path(self.temp.name) / "saves"),
                        patch("game.SAVE_FILE", Path(self.temp.name) / "save.json"),
                        patch("game.DESIGNS_FILE", Path(self.temp.name) / "designs.json")]
        for item in self.patches:
            item.start()
        self.game = Game()
        self.game.scene = "town"

    def tearDown(self):
        pygame.quit()
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def send(self, event):
        pygame.event.post(event)
        for queued in pygame.event.get():
            self.game.handle_event(queued)
        self.game.update(0)
        self.game.draw()

    def key(self, key):
        self.send(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode=""))

    def click(self, pos, button=1):
        self.send(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=button))

    def test_escape_never_exits_title_or_pause_menu(self):
        self.game.scene = 'menu'
        self.game.menu_page = 'title'
        for _ in range(3):
            self.key(pygame.K_ESCAPE)
        self.assertTrue(self.game.running)
        self.assertEqual(self.game.scene, 'menu')
        self.game.scene = 'town'
        self.game.pause_menu_open = True
        self.key(pygame.K_ESCAPE)
        self.assertFalse(self.game.pause_menu_open)
        self.assertEqual(self.game.scene, 'town')
        self.assertTrue(self.game.running)

    def test_factory_escape_cancels_subpage_then_pauses(self):
        self.game.open_factory()
        self.game.factory_page = 'equipment'
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
        self.game.handle_key(event)
        self.assertEqual(self.game.scene, 'factory')
        self.assertEqual(self.game.factory_page, 'floor')
        self.game.handle_key(event)
        self.assertEqual(self.game.scene, 'factory')
        self.assertTrue(self.game.pause_menu_open)
        self.game.handle_key(event)
        self.assertEqual(self.game.scene, 'factory')
        self.assertFalse(self.game.pause_menu_open)

    def test_e_visits_every_building_even_with_a_resident_at_its_door(self):
        for name, (x, y) in LOCATIONS.items():
            with self.subTest(place=name):
                self.game.scene = "town"
                self.game.town_dialogue = None
                self.game.town.player_x, self.game.town.player_y = x, y + 35
                self.game.town.people["Mely"] = [x, y + 30]
                self.assertEqual(self.game.town.nearby(), name)
                self.assertNotIn("talk", self.game.town.interaction_prompt())
                self.key(pygame.K_e)
                if name == "workshop":
                    self.assertEqual(self.game.scene, "factory")
                else:
                    self.assertEqual(self.game.town_dialogue, name)

    def test_walking_to_every_door_has_an_unblocked_interaction_approach(self):
        keys = defaultdict(bool, {pygame.K_w: True})
        for name, (x, y) in LOCATIONS.items():
            with self.subTest(place=name):
                self.game.town.player_x, self.game.town.player_y = x, y + 120
                for _ in range(3):
                    self.game.town.move(keys, .1)
                self.assertEqual(self.game.town.nearby_place(), name)

    def test_e_does_not_talk_to_people_but_click_and_topic_keys_work(self):
        town = self.game.town
        town.player_x, town.player_y = 1120, 1100
        town.people["Mely"] = [1140, 1120]
        self.key(pygame.K_e)
        self.assertIsNone(self.game.town_dialogue)
        camera_x = max(0, min(WORLD_W - WIDTH, int(town.player_x - WIDTH // 2)))
        camera_y = max(0, min(WORLD_H - HEIGHT, int(town.player_y - HEIGHT // 2)))
        self.click((1140 - camera_x, 1090 - camera_y))
        self.assertEqual(self.game.town_dialogue, "person:Mely")
        self.key(pygame.K_e)
        self.assertEqual(self.game.town_dialogue, "person:Mely")
        self.key(pygame.K_RETURN)
        self.key(pygame.K_2)
        self.assertEqual(self.game.town_topic, "family")
        self.key(pygame.K_ESCAPE)
        self.assertIsNone(self.game.town_dialogue)

    def test_market_keyboard_visit_purchase_and_exit(self):
        self.game.town.player_x, self.game.town.player_y = LOCATIONS["market"]
        self.game.village.advance_day()
        self.key(pygame.K_e)
        self.assertEqual(self.game.town_dialogue, "market")
        self.key(pygame.K_e)
        self.assertEqual(self.game.village.player_bread, 1)
        self.key(pygame.K_n)
        self.assertEqual(self.game.village.day, 3)
        self.key(pygame.K_ESCAPE)
        self.assertEqual(self.game.scene, "town")
        self.assertIsNone(self.game.town_dialogue)

    def test_building_commission_clears_a_previous_calculator_mode(self):
        self.game.active_compute = "fuel_quote"
        self.game.numeric_mode = True
        self.game.town.player_x, self.game.town.player_y = LOCATIONS["mill"]
        self.key(pygame.K_e)
        self.key(pygame.K_e)
        self.assertEqual(self.game.scene, "workshop")
        self.assertEqual(self.game.commission.key, "mill")
        self.assertIsNone(self.game.active_compute)
        self.assertFalse(self.game.numeric_mode)

    def test_all_ledger_sections_render_with_working_contextual_controls(self):
        for _ in range(3):
            self.game.village.advance_day()
        self.key(pygame.K_l)
        for tab in ledger.TABS:
            with self.subTest(tab=tab):
                self.game.select_ledger_tab(tab)
                with patch("ledger.label", wraps=ledger.label) as labels:
                    self.game.draw()
                footer = labels.call_args.args[1]
                self.assertIn("ESC", footer)
                if tab in ("People", "Businesses", "Trade", "Inventors"):
                    self.assertIn("UP / DOWN", footer)
                else:
                    self.assertNotIn("UP / DOWN", footer)
                if tab == "Map":
                    self.assertNotIn("M opens", footer)
                if tab in ("People", "Businesses"):
                    self.key(pygame.K_DOWN)
                    self.assertEqual(self.game.ledger_index, 1)
                if tab == "Trade":
                    self.key(pygame.K_UP)
                    self.assertEqual(self.game.trade_day_offset, 1)
                    self.key(pygame.K_DOWN)
                    self.assertEqual(self.game.trade_day_offset, 0)
                self.key(pygame.K_RIGHT)
                self.assertEqual(self.game.ledger_tab, ledger.TABS[(ledger.TABS.index(tab) + 1) % len(ledger.TABS)])
        self.key(pygame.K_ESCAPE)
        self.assertEqual(self.game.scene, "town")

    def test_r_rotates_held_components_and_y_erases_components(self):
        self.game.scene = "workshop"
        self.game.select_part("AND")
        self.key(pygame.K_r)
        self.assertEqual(self.game.rotation, 1)
        bx, by, cell = self.game.board_metrics()
        point = (bx + 5.5 * cell, by + 3.5 * cell)
        self.click(point)
        self.assertEqual(self.game.circuit.parts[(5, 3)].rotation, 1)
        self.key(pygame.K_y)
        self.assertEqual(self.game.selected, "ERASE")
        self.click(point)
        self.assertNotIn((5, 3), self.game.circuit.parts)

    def test_long_commission_table_scrolls_and_task_dialog_blocks_background_input(self):
        self.game.scene = "workshop"
        self.game.test_results = [CommissionCase(False, False, False, False, True, (False, False, False))] * 32
        self.game.draw()
        self.send(pygame.event.Event(pygame.MOUSEWHEEL, y=-40, x=0))
        self.assertEqual(self.game.test_scroll, 24)
        self.key(pygame.K_PAGEUP)
        self.assertEqual(self.game.test_scroll, 20)
        self.click((640, 400), button=4)
        self.assertEqual(self.game.test_scroll, 19)
        self.click((640, 646))
        self.assertTrue(self.game.task_help_open)
        self.send(pygame.event.Event(pygame.MOUSEWHEEL, y=20, x=0))
        self.assertEqual(self.game.test_scroll, 19)
        self.key(pygame.K_y)
        self.assertEqual(self.game.selected, "TRACE")
        self.key(pygame.K_ESCAPE)
        self.assertFalse(self.game.task_help_open)
        self.assertIsNotNone(self.game.test_results)
        self.key(pygame.K_ESCAPE)
        self.assertIsNone(self.game.test_results)

    def test_invention_scrolling_loads_the_visible_case(self):
        self.game.village.arithmetic_unlocks = ["ADD"]
        self.game.open_invention("multiplier")
        self.game.test_invention()
        expected = self.game.invention.rows[8]["bits"].copy()
        self.key(pygame.K_PAGEDOWN)
        self.key(pygame.K_PAGEDOWN)
        self.assertEqual(self.game.test_scroll, 8)
        self.click((620, 266))
        self.assertFalse(self.game.invention.show_results)
        self.assertEqual(self.game.invention.bits, expected)

    def test_task_details_exist_before_testing_and_fit_for_all_job_types(self):
        self.game.scene = "workshop"
        self.game.draw()
        self.click((1155, 698))
        self.assertTrue(self.game.task_help_open)
        self.key(pygame.K_ESCAPE)
        for key in COMMISSIONS:
            self.game.village.active_commission = key
            self.check_task_dialog()
        for key in computation.JOBS:
            self.game.scene = "compute"
            self.game.compute_key = key
            self.check_task_dialog()
        self.game.village.arithmetic_unlocks = ["ADD"]
        for key in ("adder", "subtractor", "comparator", "multiplier"):
            self.game.open_invention(key)
            self.check_task_dialog()
            self.game.close_invention()

    def check_task_dialog(self):
        self.game.task_help_open = True
        self.game.draw()
        lines = self.game.task_detail_lines()
        self.assertLess(270 + len(lines) * 23, 584)
        self.assertTrue(all(self.game.small.render(line, True, (0, 0, 0)).get_width() <= 636 for line in lines))
        self.assertTrue(all(pygame.Rect(280, 155, 720, 480).contains(rect) for rect, _ in self.game.buttons))
        body = " ".join(self.game.task_description()[1]).lower()
        self.assertNotIn("gate", body)
        self.assertNotIn("valve", body)
        self.key(pygame.K_ESCAPE)
        self.assertFalse(self.game.task_help_open)

    def test_save_and_reload_clear_transient_dialogs(self):
        self.game.start_slot(2)
        self.game.scene = "workshop"
        self.game.task_help_open = True
        self.game.test_scroll = 10
        self.key(pygame.K_ESCAPE)  # Close task details.
        self.key(pygame.K_ESCAPE)  # Pause.
        label, action = next(entry for entry in self.game.pause_entries() if entry[0] == 'Back to Main Menu')
        action()
        self.assertEqual(self.game.scene, "menu")
        self.key(pygame.K_RETURN)
        self.key(pygame.K_2)
        self.assertFalse(self.game.task_help_open)
        self.assertEqual(self.game.test_scroll, 0)
        self.key(pygame.K_e)
        self.assertEqual(self.game.scene, "factory")

    def test_window_close_from_a_modal_saves_and_exits(self):
        self.game.start_slot(2)
        self.game.scene = "workshop"
        self.game.invention_picker = True
        self.game.draw()
        self.send(pygame.event.Event(pygame.QUIT))
        self.assertEqual(self.game.scene, "menu")
        self.assertFalse(self.game.invention_picker)
        self.assertFalse(self.game.running)
