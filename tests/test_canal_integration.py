"""Real game dispatch, field editing, travel, journal and saved canal continuity."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import json
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pygame
import adventure
import boiler_tower
import canal_departure
import canal_layout
import canal_progress
import canal_settlement
import chapter_ui
import manufacturing
import opening_chapter
from daily_life import state as daily_state
from game import Game, slot_path
from test_canal_progress import boat_design


class CanalIntegrationTests(unittest.TestCase):
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
        self.g.opening_screen = None
        self.g.opening_reveal = 0.

    def tearDown(self):
        pygame.quit()
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def key(self, value):
        self.g.handle_key(pygame.event.Event(pygame.KEYDOWN, key=value, mod=0, unicode=''))

    def complete_expeditions(self):
        village = self.g.village
        adventure.state(village).update(expansion_complete=True, artifact=True)
        boiler_tower.state(village)['complete'] = True
        workshop = manufacturing.state(village)
        workshop['unlocks'] = ['precision_machine', 'steam_accumulator']
        workshop['goods']['precision_gears'] = 1

    def landing(self):
        g = self.g
        g.town.player_x, g.town.player_y = canal_departure.LANDING
        self.key(pygame.K_e)
        self.assertTrue(g.canal_departure_open)

    def ready_boat(self):
        self.complete_expeditions()
        self.assertTrue(canal_progress.repair(self.g.village)[0])
        self.assertTrue(canal_progress.install(self.g.village, boat_design().snapshot())[0])

    def arrive(self):
        self.ready_boat()
        self.landing()
        self.key(pygame.K_e)
        self.assertEqual(self.g.scene, 'canal')

    def test_keyboard_and_click_cannot_skip_expeditions_or_repair(self):
        g = self.g
        self.landing()
        g.draw()
        self.key(pygame.K_g)
        self.assertIsNone(g.adventure_editor)
        self.key(pygame.K_r)
        self.assertFalse(canal_progress.state(g.village)['boat_repaired'])
        self.key(pygame.K_e)
        self.assertEqual(g.scene, 'town')
        g.handle_click((647, 566), 1)
        self.assertEqual(g.scene, 'town')
        self.assertFalse(canal_progress.state(g.village)['visited'])
        self.assertNotIn('canal_arrival', opening_chapter.observe(g.village)['evidence'])
        before = deepcopy(daily_state(g.village))
        g.update(2.)
        self.assertEqual(daily_state(g.village), before)
        self.key(pygame.K_ESCAPE)
        self.assertFalse(g.canal_departure_open)
        self.assertFalse(g.pause_menu_open)
        self.assertTrue(pygame.get_init())

    def test_real_editor_keeps_draft_restores_context_and_certifies_before_travel(self):
        g = self.g
        self.complete_expeditions()
        original_circuit = g.circuit
        original_names = deepcopy(g.port_names)
        self.landing()
        self.key(pygame.K_r)
        self.key(pygame.K_g)
        self.assertEqual(g.adventure_editor, canal_progress.KIND)
        self.assertEqual(g.scene, 'workshop')
        self.assertFalse(g.canal_departure_open)
        self.assertEqual(g.port_names, canal_progress.PORT_NAMES)
        self.assertFalse(adventure.validate(g)[0])
        g.circuit = boat_design()
        draft = g.circuit.snapshot()
        before = deepcopy(daily_state(g.village))
        g.update(2.)
        self.assertEqual(daily_state(g.village), before)
        g.save_game()
        saved = json.loads(slot_path(1).read_text(encoding='utf-8'))
        self.assertEqual(saved['village']['manufacturing']['adventure']['drafts'][canal_progress.KIND]['parts'], draft)
        self.assertEqual(saved['circuit'], original_circuit.snapshot())
        self.key(pygame.K_ESCAPE)  # Specification closes first.
        self.key(pygame.K_ESCAPE)
        self.assertEqual(g.scene, 'town')
        self.assertIs(g.circuit, original_circuit)
        self.assertEqual(g.port_names, original_names)
        self.assertFalse(canal_progress.can_travel(g.village))
        self.landing()
        self.key(pygame.K_g)
        self.assertEqual(g.circuit.snapshot(), draft)
        ok, message = adventure.validate(g)
        self.assertTrue(ok, message)
        self.assertIn('208', message)
        adventure.close_editor(g)
        self.assertTrue(canal_progress.can_travel(g.village))
        self.landing()
        g.draw()
        g.handle_click((647, 566), 1)
        self.assertEqual(g.scene, 'canal')
        self.assertFalse(g.canal_departure_open)

    def test_save_reload_resumes_canal_without_duplicate_trip_or_reward(self):
        g = self.g
        self.arrive()
        current = canal_progress.state(g.village)
        current['met'] = ['Mara', 'Ivo']
        canal_progress.discover_clue(g.village)
        g.update(.1)
        position = deepcopy(current['position'])
        trips = current['trips']
        gear_stock = manufacturing.state(g.village)['goods']['precision_gears']
        coins = g.village.coins
        g.save_game()
        g.start_slot(1)
        self.assertEqual(g.scene, 'canal')
        current = canal_progress.state(g.village)
        self.assertEqual(current['position'], position)
        self.assertEqual(current['trips'], trips)
        self.assertEqual(current['met'], ['Mara', 'Ivo'])
        self.assertTrue(current['clue_found'])
        self.assertEqual(g.village.coins, coins)
        self.assertEqual(manufacturing.state(g.village)['goods']['precision_gears'], gear_stock)
        self.assertIsNone(g.canal_dialogue)
        canal_settlement.leave(g)
        self.assertEqual(g.scene, 'town')
        self.assertEqual((g.town.player_x, g.town.player_y), canal_departure.RETURN_POSITION)
        self.assertEqual(g.town.safe_position(canal_departure.RETURN_POSITION), canal_departure.RETURN_POSITION)
        self.landing()
        self.key(pygame.K_e)
        self.assertEqual(g.scene, 'canal')
        self.assertEqual(canal_progress.state(g.village)['trips'], trips + 1)
        self.assertEqual(g.village.coins, coins)

    def test_paused_canal_holds_simulation_scenery_and_journal_is_modal(self):
        g = self.g
        self.arrive()
        self.assertTrue(canal_settlement.modal_active(g))
        self.key(pygame.K_b)
        self.assertFalse(chapter_ui.active(g))
        before = deepcopy(vars(g.village))
        g.update(.1)
        self.assertEqual(vars(g.village), before)
        self.key(pygame.K_ESCAPE)  # Dismiss the first-arrival introduction.
        self.assertFalse(canal_settlement.modal_active(g))
        self.assertFalse(g.pause_menu_open)
        self.key(pygame.K_ESCAPE)
        self.assertTrue(g.pause_menu_open)
        g.draw()
        state = deepcopy(vars(g.village))
        pixels = pygame.image.tobytes(g.screen, 'RGB')
        for _ in range(3):
            g.update(.4)
            g.draw()
        self.assertEqual(vars(g.village), state)
        self.assertEqual(pygame.image.tobytes(g.screen, 'RGB'), pixels)
        self.key(pygame.K_ESCAPE)
        self.assertFalse(g.pause_menu_open)
        self.key(pygame.K_b)
        self.assertTrue(chapter_ui.active(g))
        state = deepcopy(vars(g.village))
        self.key(pygame.K_e)
        g.update(1.)
        self.assertEqual(vars(g.village), state)
        self.assertEqual(g.scene, 'canal')
        self.key(pygame.K_ESCAPE)
        self.assertFalse(chapter_ui.active(g))

    def test_spoofed_saved_canal_scene_without_valid_boat_returns_to_town(self):
        g = self.g
        self.arrive()
        g.save_game()
        saved = json.loads(slot_path(1).read_text(encoding='utf-8'))
        saved['village']['manufacturing']['adventure']['designs'].pop(canal_progress.KIND)
        slot_path(1).write_text(json.dumps(saved), encoding='utf-8')
        g.start_slot(1)
        self.assertEqual(g.scene, 'town')
        self.assertFalse(canal_progress.can_travel(g.village))

    def test_local_trade_inputs_are_modal_and_closed_buttons_cannot_trade(self):
        g = self.g
        self.arrive()
        self.key(pygame.K_ESCAPE)
        current = canal_progress.state(g.village)
        current['position'] = list(canal_layout.POINTS['Sela'])
        g.village.coins = 80
        self.key(pygame.K_e)
        self.assertEqual(g.canal_runtime['modal'], 'Sela')
        g.draw()
        self.key(pygame.K_1)
        self.assertEqual(g.village.coins, 72)
        self.assertEqual(g.village.player_bread, 1)
        self.assertEqual(current['market_bread'], 5)
        self.key(pygame.K_ESCAPE)
        self.assertFalse(canal_settlement.modal_active(g))
        # An Escape and click can arrive in the same input batch before draw.
        before = deepcopy(vars(g.village))
        g.handle_click((396, 686), 1)
        self.assertEqual(vars(g.village), before)
        current['position'] = list(canal_layout.POINTS['Ivo'])
        manufacturing.state(g.village)['goods'].update(repair_kits=2, steam_valves=1)
        self.key(pygame.K_e)
        self.assertEqual(g.canal_runtime['modal'], 'Ivo')
        self.key(pygame.K_1)
        self.assertTrue(current['request_complete'])
        self.assertEqual(g.village.coins, 104)
        self.assertEqual(manufacturing.state(g.village)['sold'], 3)
        self.assertEqual(manufacturing.state(g.village)['earned'], 32)
        self.assertIn('canal_record', opening_chapter.observe(g.village)['evidence'])
        before = deepcopy(vars(g.village))
        self.key(pygame.K_1)
        self.assertEqual(vars(g.village), before)


if __name__ == '__main__':
    unittest.main()
