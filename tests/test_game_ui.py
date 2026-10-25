import os
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from circuit import Part
from economy import Village
from game import Game
from town import LOCATIONS
from materials import material_bill


class GameUITests(unittest.TestCase):
    def test_library_delete_cancel_confirm_and_reload_preserve_floor(self):
        from copy import deepcopy
        from game import PANEL_X
        game = Game()
        game.start_slot(1)
        game.scene, game.tab = "workshop", "LIBRARY"
        game.save_copy("Keep")
        game.save_copy("Remove")
        game.draw()
        floor = deepcopy(game.circuit.snapshot())
        game.handle_click((PANEL_X + 380, 430), 1)
        self.assertEqual(game.pending_design_delete, 1)
        game.draw()
        game.handle_click((PANEL_X + 100, 340), 1)
        game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_s, mod=0))
        self.assertEqual(len(game.designs), 2)
        game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0))
        self.assertIsNone(game.pending_design_delete)
        self.assertEqual(len(game.designs), 2)
        game.request_delete_design(1)
        game.draw()
        game.handle_click((780, 445), 1)
        self.assertEqual([d['name'] for d in game.designs], ['Keep'])
        self.assertEqual(game.circuit.snapshot(), floor)
        loaded = Game()
        loaded.start_slot(1)
        self.assertEqual([d['name'] for d in loaded.designs], ['Keep'])
        self.assertEqual(loaded.circuit.snapshot(), floor)

    def test_library_deletion_keeps_device_copies_and_delivered_machines(self):
        from copy import deepcopy
        game = Game()
        game.start_slot(1)
        game.scene = 'workshop'
        game.save_copy('Controller')
        game.select_device(0)
        game.circuit.set_part((6, 3), Part('DEVICE', device=game.held_device))
        game.village.complete_mill_job('license')
        floor = deepcopy(game.circuit.snapshot())
        business = deepcopy(game.village.businesses)
        licenses = deepcopy(game.village.licenses)
        game.request_delete_design(0)
        game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0))
        self.assertEqual(game.designs, [])
        self.assertEqual(game.circuit.snapshot(), floor)
        self.assertEqual(game.village.businesses, business)
        self.assertEqual(game.village.licenses, licenses)
        loaded = Game()
        loaded.start_slot(1)
        self.assertEqual(loaded.designs, [])
        self.assertEqual(loaded.circuit.snapshot(), floor)

    def test_deleted_versions_and_ids_are_not_reused_and_last_page_clamps(self):
        game = Game()
        game.start_slot(1)
        game.scene = 'workshop'
        game.save_copy('Original')
        game.save_copy()
        original_id = game.designs[0]['device_id']
        game.request_delete_design(1)
        game.confirm_delete_design()
        loaded = Game()
        loaded.start_slot(1)
        loaded.scene = 'workshop'
        loaded.load_design(0)
        loaded.save_copy()
        self.assertEqual(loaded.designs[-1]['version'], 3)
        self.assertEqual(loaded.designs[-1]['device_id'], original_id)
        for i in range(3):
            loaded.save_copy(f'Extra {i}')
        loaded.library_page = 1
        loaded.request_delete_design(0)
        loaded.confirm_delete_design()
        self.assertEqual(loaded.library_page, 0)
        highest = max(d['number'] for d in loaded.designs)
        while loaded.designs:
            loaded.request_delete_design(0)
            loaded.confirm_delete_design()
        loaded.draw()
        reloaded = Game()
        reloaded.start_slot(1)
        reloaded.save_copy('Fresh')
        self.assertGreater(reloaded.designs[0]['device_id'], highest)

    def test_help_overlay_blocks_building_and_closes_with_escape(self):
        game = Game()
        game.start_slot(1)
        game.scene = "workshop"
        game.draw()
        game.handle_click((1000, 696), 1)
        self.assertTrue(game.help_open)
        game.draw()
        game.handle_click((76 + 2 * 59 + 15, 154 + 2 * 59 + 15), 1)
        self.assertNotIn((2, 2), game.circuit.parts)
        game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0))
        self.assertFalse(game.help_open)
        self.assertEqual(game.scene, "workshop")

    def test_contract_board_respects_prerequisites_and_keeps_floor(self):
        game = Game()
        game.start_slot(1)
        game.circuit.set_part((2, 3), Part("PIPE"))
        floor = game.circuit.snapshot()
        game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_j, mod=0))
        self.assertEqual(game.scene, "contracts")
        game.choose_contract("bakery")
        self.assertEqual(game.scene, "contracts")
        self.assertEqual(game.commission.key, "mill")
        game.update(1.0)
        self.assertEqual(game.circuit.tick_count, 0)
        game.draw()
        game.handle_click((1000, 270), 1)
        self.assertEqual(game.scene, "workshop")
        self.assertEqual(game.circuit.snapshot(), floor)
        game.village.complete_mill_job()
        game.open_contract_board()
        game.choose_contract("bakery")
        self.assertEqual(game.commission.key, "bakery")
        self.assertEqual(game.circuit.snapshot(), floor)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.paths = [
            patch("game.SAVES_DIR", root / "saves"),
            patch("game.SAVE_FILE", root / "save.json"),
            patch("game.DESIGNS_FILE", root / "designs.json"),
        ]
        for path in self.paths:
            path.start()

    def tearDown(self):
        pygame.quit()
        for path in reversed(self.paths):
            path.stop()
        self.temp.cleanup()

    def test_test_button_reports_or_failure_and_y_selects_eraser(self):
        game = Game()
        game.village = Village()
        game.scene = "workshop"
        for x in (2, 3):
            game.circuit.set_part((x, 3), Part("PIPE"))
        for y in (4, 5):
            game.circuit.set_part((4, y), Part("PIPE", 1))
        game.circuit.set_part((4, 3), Part("OR"))
        for x in (5, 6, 7, 8):
            game.circuit.set_part((x, 3), Part("PIPE"))

        game.draw()
        game.handle_click((1000, 326), 1)
        self.assertEqual([case.passed for case in game.test_results], [True, False, False, True])
        game.draw()  # The results panel itself must render.

        game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0))
        game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_y, mod=0))
        self.assertEqual(game.selected, "ERASE")

    def test_town_unlocks_bakery_after_mill(self):
        game = Game()
        game.start_slot(1)
        game.town.player_x, game.town.player_y = 285, 625
        game.interact_town()
        self.assertEqual(game.town_dialogue, "mill")
        game.interact_town()
        self.assertEqual(game.scene, "workshop")
        self.assertEqual(game.commission.key, "mill")

        game.village.complete_mill_job()
        game.scene = "town"
        game.town.player_x, game.town.player_y = 1280, 625
        game.interact_town()
        game.interact_town()
        self.assertEqual(game.commission.key, "bakery")
        self.assertEqual(game.scene, "workshop")

        for x in (2, 3, 5, 6, 7, 8):
            game.circuit.set_part((x, 3), Part("PIPE"))
        for y in (4, 5):
            game.circuit.set_part((4, y), Part("PIPE", 1))
        game.circuit.set_part((4, 3), Part("OR"))
        game.test_commission()
        self.assertFalse(game.village.bakery_machine)
        self.assertEqual(game.village.coins, 36)
        game.test_results = None
        game.village.material_inventory.update(material_bill(game.commission.key))
        game.submit_design()
        self.assertTrue(game.village.bakery_machine)
        self.assertEqual(game.village.coins, 66)
        game.draw()  # Completion celebration renders.

    def test_third_contract_unlocks_and_can_be_selected(self):
        game = Game()
        game.start_slot(1)
        game.village.complete_mill_job()
        game.village.complete_bakery_job()
        game.open_contract_board()
        game.draw()
        game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_3, mod=0))
        self.assertEqual(game.commission.key, "vent")
        self.assertEqual(game.scene, "workshop")
        game.draw()

    def test_third_contract_submits_a_working_nand_design(self):
        game = Game()
        game.start_slot(1)
        game.village.complete_mill_job()
        game.village.complete_bakery_job()
        game.choose_contract("vent")
        for x in (2, 3, 5, 7, 8):
            game.circuit.set_part((x, 3), Part("PIPE"))
        for y in (4, 5):
            game.circuit.set_part((4, y), Part("PIPE", 1))
        game.circuit.set_part((4, 3), Part("AND"))
        game.circuit.set_part((6, 3), Part("NOT"))
        game.test_commission()
        self.assertTrue(game.submission_ready)
        game.village.material_inventory.update(material_bill(game.commission.key))
        game.submit_design()
        self.assertTrue(game.village.vent_machine)
        self.assertEqual(game.village.coins, 86)
        self.assertEqual(game.village.offers["vent"]["status"], "player")

    def test_fourth_contract_is_on_next_board_page(self):
        game = Game()
        game.start_slot(1)
        game.village.complete_mill_job()
        game.village.complete_bakery_job()
        game.open_contract_board()
        game.draw()
        game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT, mod=0))
        self.assertEqual(game.contract_page, 1)
        game.draw()
        game.handle_click((1000, 270), 1)
        self.assertEqual(game.commission.key, "market")
        self.assertEqual(game.scene, "workshop")

    def test_delivery_choice_saves_copy_ownership_and_survives_reload(self):
        game = Game()
        game.start_slot(1)
        for x in (2, 3, 5, 6, 7, 8):
            game.circuit.set_part((x, 3), Part("PIPE"))
        for y in (4, 5):
            game.circuit.set_part((4, y), Part("PIPE", 1))
        game.circuit.set_part((4, 3), Part("AND"))
        game.scene = "workshop"
        game.test_commission()
        game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0))
        self.assertTrue(game.delivery_open)
        self.assertFalse(game.village.mill_machine)
        game.village.material_inventory.update(material_bill(game.commission.key))
        game.draw()
        game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_2, mod=0))
        self.assertTrue(game.village.mill_machine)
        self.assertEqual(game.village.coins, 44)
        self.assertEqual(game.designs[-1]["owner"], "Boole")
        self.assertIn("Miller owns one copy", game.designs[-1]["rights_note"])
        game.return_to_menu()
        game.start_slot(1)
        self.assertEqual(game.village.offers["mill"]["copy_owner"], "Miller")
        self.assertEqual(game.designs[-1]["owner"], "Boole")

    def test_license_survives_reload_and_pays_next_day(self):
        game = Game()
        game.start_slot(1)
        self.assertTrue(game.village.complete_mill_job("license"))
        game.return_to_menu()
        game.start_slot(1)
        self.assertEqual(game.village.offers["mill"]["delivery_mode"], "license")
        self.assertEqual(game.village.capacity("mill", nominal=True), 4)
        before = game.village.coins
        game.next_day()
        self.assertEqual(game.village.coins, before + 2)
        self.assertEqual(game.village.capacity("mill", nominal=True), 4)
        game.village.update_life(game.town, 180)
        self.assertEqual(game.village.capacity("mill"), 4)

    def test_workshop_door_opens_on_one_interaction(self):
        game = Game()
        game.start_slot(1)
        self.assertEqual(game.town.nearby(), "workshop")
        game.interact_town()
        self.assertEqual(game.scene, "factory")

    def test_ledger_and_named_residents_are_visible_and_saved(self):
        game = Game()
        game.start_slot(1)
        game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_l, mod=0))
        self.assertEqual(game.scene, "ledger")
        game.select_ledger_tab("People")
        game.draw()
        game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0))
        self.assertEqual(game.scene, "town")
        game.town.player_x, game.town.player_y = LOCATIONS["home_3"]
        game.town.people["Mely"] = list(LOCATIONS["home_3"])
        game.interact_town()
        self.assertEqual(game.town_dialogue, "home_3")
        game.town_dialogue = "person:Mely"
        game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_2, mod=0))
        self.assertEqual(game.town_topic, "family")
        game.draw()
        game.return_to_menu()
        game.start_slot(1)
        mely = next(person for person in game.village.citizens if person["name"] == "Mely")
        self.assertEqual(mely["relationships"]["Boole"], 22)

    def test_market_is_reachable_and_does_not_open_workshop(self):
        game = Game()
        game.start_slot(1)
        game.village.advance_day()
        game.town.player_x, game.town.player_y = 1290, 970
        self.assertEqual(game.town.nearby(), "market")
        game.draw()  # Camera follows the player into the new street.
        game.interact_town()
        self.assertEqual(game.town_dialogue, "market")
        game.interact_town()
        self.assertEqual(game.town_dialogue, "market")
        self.assertEqual(game.scene, "town")
        self.assertEqual(game.village.player_bread, 1)
        game.return_to_menu()
        game.start_slot(1)
        self.assertEqual(game.town.player_x, 1290)
        self.assertEqual(game.village.player_bread, 1)

    def test_editing_after_pass_requires_retest_before_submission(self):
        game = Game()
        game.village = Village()
        game.scene = "workshop"
        for x in (2, 3, 5, 6, 7, 8):
            game.circuit.set_part((x, 3), Part("PIPE"))
        for y in (4, 5):
            game.circuit.set_part((4, y), Part("PIPE", 1))
        game.circuit.set_part((4, 3), Part("AND"))
        game.test_commission()
        self.assertTrue(game.submission_ready)
        self.assertEqual(game.village.coins, 12)
        game.circuit.set_part((4, 3), Part("OR"))
        self.assertFalse(game.submission_ready)
        game.village.material_inventory.update(material_bill(game.commission.key))
        game.submit_design()
        self.assertFalse(game.village.mill_machine)

    def test_save_slots_keep_progress_and_designs_separate(self):
        game = Game()
        self.assertEqual(game.scene, "menu")
        game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0))
        game.draw()
        game.handle_click((940, 229), 1)
        self.assertEqual(game.current_slot, 1)
        game.village.coins = 47
        game.village.advance_day()
        farm_cash = game.village.businesses["farm"]["cash"]
        game.village.player_bread = 3
        game.village.households["home_1"]["cash"] = 11
        game.circuit.set_part((2, 3), Part("PIPE"))
        game.save_copy("First plan")
        game.return_to_menu()
        self.assertEqual(game.scene, "menu")
        self.assertTrue(game.running)
        game.start_slot(2)
        self.assertEqual(game.village.coins, 12)
        self.assertEqual(game.designs, [])
        game.return_to_menu()
        game.start_slot(1)
        self.assertEqual(game.village.coins, 47)
        self.assertEqual(game.village.day, 2)
        self.assertEqual(game.village.businesses["farm"]["cash"], farm_cash)
        self.assertEqual(game.village.player_bread, 3)
        self.assertEqual(game.village.households["home_1"]["cash"], 11)
        self.assertEqual(game.designs[0]["name"], "First plan")
        self.assertEqual(game.circuit.parts[(2, 3)].kind, "PIPE")

    def test_existing_save_appears_in_first_slot_without_overwriting_original(self):
        from game import SAVE_FILE, DESIGNS_FILE, load_slot

        original = {"day": 9, "coins": 83, "mill_machine": True}
        SAVE_FILE.write_text(json.dumps(original), encoding="utf-8")
        DESIGNS_FILE.write_text(json.dumps([{"name": "Old plan", "parts": []}]), encoding="utf-8")
        self.assertTrue(load_slot(1)["legacy"])
        game = Game()
        game.start_slot(1)
        self.assertEqual(game.village.day, 9)
        self.assertEqual(game.designs[0]["name"], "Old plan")
        self.assertEqual(game.village.capacity("mill"), 4)
        self.assertIn("market", game.village.businesses)
        game.return_to_menu()
        self.assertEqual(json.loads(SAVE_FILE.read_text(encoding="utf-8")), original)
        self.assertFalse(load_slot(1).get("legacy", False))

    def test_delete_requires_confirmation_and_frees_a_slot(self):
        from game import load_slot, slot_path

        game = Game()
        game.start_slot(2)
        game.village.coins = 99
        game.return_to_menu()
        game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0))
        game.draw()
        game.handle_click((1004, 313), 1)
        self.assertEqual(game.pending_delete, 2)
        game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0))
        self.assertIsNotNone(load_slot(2))
        game.draw()
        game.handle_click((1004, 313), 1)
        game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0))
        self.assertIsNone(load_slot(2))
        self.assertFalse(slot_path(2).exists())
        game.start_slot(2)
        self.assertEqual(game.village.coins, 12)

    def test_deleting_slot_one_does_not_resurrect_legacy_save(self):
        from game import SAVE_FILE, DESIGNS_FILE, load_slot

        original = {"day": 8, "coins": 71}
        SAVE_FILE.write_text(json.dumps(original), encoding="utf-8")
        DESIGNS_FILE.write_text("[]", encoding="utf-8")
        game = Game()
        game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0))
        game.draw()
        game.handle_click((1004, 229), 1)
        self.assertEqual(game.pending_delete, 1)
        game.handle_click((780, 443), 1)
        self.assertIsNone(load_slot(1))
        self.assertEqual(json.loads(SAVE_FILE.read_text(encoding="utf-8")), original)
        game.start_slot(1)
        self.assertEqual(game.village.day, 1)

    def test_q_never_exits_or_changes_screens(self):
        game = Game()
        game.start_slot(1)
        for scene in ("town", "workshop", "compute", "contracts", "ledger", "requests", "menu"):
            game.scene = scene
            for page in ("title", "slots"):
                game.menu_page = page
                game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_q, mod=0))
                self.assertEqual(game.scene, scene)
                self.assertTrue(game.running)

    def test_pause_freezes_simulation_blocks_input_and_resumes(self):
        from copy import deepcopy
        game = Game()
        game.start_slot(1)
        for scene in ("town", "workshop"):
            game.scene = scene
            game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0))
            self.assertTrue(game.pause_menu_open)
            game.draw()  # Initialize lazily created display/readout state.
            village = deepcopy(game.village.__dict__)
            circuit = deepcopy(game.circuit.snapshot())
            position = (game.town.player_x, game.town.player_y)
            game.draw()
            self.assertEqual(len(game.buttons), len(game.pause_entries()))
            game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_n, mod=0))
            game.handle_click((150, 200), 1)
            game.update(10)
            self.assertEqual(game.village.__dict__, village)
            self.assertEqual(game.circuit.snapshot(), circuit)
            self.assertEqual((game.town.player_x, game.town.player_y), position)
            game.handle_click(game.pause_buttons()[0][0].center, 1)
            self.assertFalse(game.pause_menu_open)
        game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0))
        game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0))
        self.assertEqual(game.scene, "workshop")
        self.assertFalse(game.pause_menu_open)
        self.assertTrue(game.running)
        game.pause_menu_open = True
        index = next(i for i, (label, _) in enumerate(game.pause_entries()) if label == "Back to Main Menu")
        game.handle_click(game.pause_buttons()[index][0].center, 1)
        self.assertEqual(game.scene, "menu")

    def test_pause_exit_saves_progress(self):
        game = Game()
        game.start_slot(1)
        game.village.coins = 123
        game.pause_menu_open = True
        index = next(i for i, (label, _) in enumerate(game.pause_entries()) if label == "Exit Game")
        game.handle_click(game.pause_buttons()[index][0].center, 1)
        self.assertFalse(game.running)
        loaded = Game()
        loaded.start_slot(1)
        self.assertEqual(loaded.village.coins, 123)


if __name__ == "__main__":
    unittest.main()
