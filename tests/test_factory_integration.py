"""Live event, clock and save checks for the manufacturing workshop."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pygame
from circuit import Part
from game import Game, village_from_data
import manufacturing
import factory_controller
import sandbox
import timing_workshop


class FactoryIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.patches = [patch("game.SAVES_DIR", root / "saves"),
                        patch("game.SAVE_FILE", root / "save.json"),
                        patch("game.DESIGNS_FILE", root / "designs.json")]
        for item in self.patches:
            item.start()
        self.game = Game()
        self.game.start_slot(1)
        self.game.open_factory()

    def tearDown(self):
        pygame.quit()
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def key(self, code):
        self.game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=code, mod=0))

    def equip(self):
        g = self.game
        g.village.coins = 100
        self.assertTrue(manufacturing.buy_equipment(g.village, "bench", (2, 2))[0])
        self.assertTrue(manufacturing.buy_equipment(g.village, "controller", (4, 2))[0])
        return manufacturing.state(g.village)["equipment"][0]["id"]

    def test_factory_door_pause_and_existing_bench_access(self):
        g = self.game
        g.scene = "town"
        self.key(pygame.K_e)
        self.assertEqual(g.scene, "factory")
        g.draw()
        self.key(pygame.K_q)
        self.assertEqual(g.scene, "factory")
        self.assertTrue(g.running)
        self.key(pygame.K_ESCAPE)
        self.assertTrue(g.pause_menu_open)
        state = deepcopy(vars(g.village))
        g.update(10)
        self.assertEqual(vars(g.village), state)
        self.key(pygame.K_RETURN)
        self.assertFalse(g.pause_menu_open)
        g.open_circuit_bench()
        g.draw()
        self.assertEqual(g.scene, "workshop")
        g.open_factory()
        self.assertEqual(g.scene, "factory")

    def test_controller_edit_freezes_world_preserves_floor_and_installs_copy(self):
        g = self.game
        machine_id = self.equip()
        original = g.circuit
        g.edit_factory_controller(machine_id)
        self.assertEqual(g.scene, "workshop")
        self.assertFalse(g.submission_ready)
        g.select_part("GT")
        self.assertIsNone(g.invention)
        self.assertEqual(g.selected, "GT")
        g.draw()
        state = deepcopy(vars(g.village))
        g.update(10)
        g.next_day()
        self.assertEqual(vars(g.village), state)
        # The physical cabinet supplies arithmetic without old invention gates.
        circuit = g.circuit
        circuit.set_part((6, 3), Part("GT"))
        ports = {port["name"]: pos for pos, port in circuit.terminals.items()}
        circuit.connect(ports["A"], (6, 3), 0)
        circuit.connect(ports["B"], (6, 3), 1)
        circuit.connect((6, 3), ports["OUT"], 0)
        self.key(pygame.K_RETURN)
        machine = manufacturing.get_machine(g.village, machine_id)
        self.assertIsNotNone(machine["controller"])
        installed = deepcopy(machine["controller"]["parts"])
        circuit.set_part((6, 3), Part("NOT"))
        self.assertEqual(machine["controller"]["parts"], installed)
        self.key(pygame.K_ESCAPE)
        self.assertIs(g.circuit, original)
        self.assertEqual(g.scene, "factory")
        g.edit_factory_controller(machine_id)
        self.assertEqual(g.circuit.parts[(6, 3)].kind, "NOT")  # Uninstalled draft retained.

    def test_work_while_away_save_reload_and_pause_do_not_duplicate_batches(self):
        g = self.game
        machine_id = self.equip()
        for good in manufacturing.RECIPE:
            self.assertTrue(manufacturing.buy_supply(g.village, good)[0])
        self.assertTrue(manufacturing.start_batch(g.village, machine_id)[0])
        for _ in range(5):
            g.update(.5)
        g.pause_menu_open = True
        before = deepcopy(manufacturing.state(g.village))
        g.update(50)
        self.assertEqual(manufacturing.state(g.village), before)
        g.pause_menu_open = False
        g.save_game()
        loaded = Game()
        loaded.start_slot(1)
        self.assertEqual(manufacturing.state(loaded.village), manufacturing.state(g.village))
        g.scene = loaded.scene = "town"
        for _ in range(25):
            g.update(.5)
            loaded.update(.5)
        self.assertEqual(manufacturing.state(loaded.village), manufacturing.state(g.village))
        self.assertEqual(manufacturing.state(g.village)["produced"], 1)
        self.assertEqual(manufacturing.state(g.village)["goods"]["repair_kits"], 1)

    def test_trading_editor_preserves_player_board_and_storage_wiring(self):
        g = self.game
        g.village.coins = 200
        for kind, pos in (("buyer", (1, 1)), ("controller", (2, 1)), ("storage", (3, 1))):
            self.assertTrue(manufacturing.buy_equipment(g.village, kind, pos)[0])
        unit, _, rack = manufacturing.state(g.village)["equipment"]
        g.edit_factory_controller(unit["id"])
        self.assertEqual(factory_controller.mappings(g), {"A": "selectedstock", "B": "target"})
        # The player designs B > A, comparing the desired amount with stored metal.
        circuit = g.circuit
        ports = {port["name"]: pos for pos, port in circuit.terminals.items()}
        circuit.set_part((6, 3), Part("GT"))
        circuit.connect(ports["B"], (6, 3), 0)
        circuit.connect(ports["A"], (6, 3), 1)
        circuit.connect((6, 3), ports["OUT"], 0)
        self.key(pygame.K_RETURN)
        self.key(pygame.K_ESCAPE)
        self.assertTrue(manufacturing.set_input_source(g.village, unit["id"], "A", rack["id"], "metal")[0])
        g.edit_factory_controller(unit["id"])
        self.key(pygame.K_RETURN)
        self.assertEqual(unit["controller"]["sources"]["A"], rack["id"])
        self.assertEqual(unit["controller"]["inputs"]["A"], "metal")
        self.key(pygame.K_ESCAPE)
        manufacturing.set_mode(g.village, unit["id"], True)
        for _ in range(30):
            manufacturing.update(g.village, .5)
        self.assertGreater(unit["transactions"], 0)
        self.assertEqual(manufacturing.input_values(g.village, unit["id"])["A"], g.village.material_inventory["metal"])
        g.save_game()
        loaded = Game()
        loaded.start_slot(1)
        self.assertEqual(manufacturing.get_machine(loaded.village, unit["id"])["controller"], unit["controller"])

    def test_new_palette_page_and_trading_titles_render(self):
        g = self.game
        g.village.coins = 100
        self.assertTrue(manufacturing.buy_equipment(g.village, "seller", (1, 1))[0])
        unit = manufacturing.state(g.village)["equipment"][0]
        g.edit_factory_controller(unit["id"])
        self.assertIn("Dispatch", factory_controller.title(g))
        g.draw()
        g.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(1090, 220)))
        self.assertEqual(g.factory_component_group, "Math")
        g.draw()
        g.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(1050, 330)))
        self.assertEqual(g.selected, "DIV")
        g.select_part("MUX")
        g.circuit.set_part((6, 3), Part("MUX"))
        g.task_help_open = True
        g.draw()
        self.assertLess(len(g.task_detail_lines()), 14)

    def test_sensor_wiring_can_be_prepared_before_installing_first_board(self):
        g = self.game
        machine_id = self.equip()
        self.assertTrue(manufacturing.buy_equipment(g.village, "storage", (5, 2))[0])
        rack = manufacturing.state(g.village)["equipment"][-1]
        g.village.material_inventory["metal"] = 23
        self.assertTrue(factory_controller.configure_input(g.village, machine_id, "A", rack["id"], "metal")[0])
        self.assertIsNone(manufacturing.get_machine(g.village, machine_id)["controller"])
        g.edit_factory_controller(machine_id)
        self.assertEqual(factory_controller.port_info(g, "A")["label"], "Stored metal")
        self.assertEqual(factory_controller.port_info(g, "A")["source"], f"Rack #{rack['id']}")
        factory_controller.load_live_inputs(g)
        self.assertEqual(g.circuit.switches["A"], 23)
        factory_controller.leave(g)
        g.save_game()
        g.start_slot(1)
        g.edit_factory_controller(machine_id)
        self.assertEqual(factory_controller.mappings(g)["A"], "metal")
        self.assertTrue(factory_controller.install(g))
        controller = manufacturing.get_machine(g.village, machine_id)["controller"]
        self.assertEqual(controller["sources"]["A"], rack["id"])
        self.assertEqual(controller["inputs"]["A"], "metal")

    def test_component_groups_fit_and_test_controls_do_not_change_installed_board(self):
        import workbench
        import workshop_floor
        g = self.game
        machine_id = self.equip()
        g.edit_factory_controller(machine_id)
        self.assertTrue(factory_controller.install(g))
        installed = deepcopy(manufacturing.get_machine(g.village, machine_id)["controller"])
        for group, kinds in workbench.COMPONENT_GROUPS.items():
            g.factory_component_group = group
            for kind in kinds:
                g.select_part(kind)
                g.draw()
                for i, (rect, _) in enumerate(g.buttons):
                    self.assertTrue(g.screen.get_rect().contains(rect))
                    self.assertFalse(any(rect.colliderect(other) for other, _ in g.buttons[i + 1:]))
        factory_controller.load_live_inputs(g)
        self.assertEqual(manufacturing.get_machine(g.village, machine_id)["controller"], installed)
        for rotation in range(4):
            self.assertEqual(workshop_floor.socket_label(Part("MUX", rotation), False, 2), "Select")
        factory_controller.edit_connections(g)
        self.assertEqual(g.scene, "factory")
        self.assertEqual(g.factory_selected, machine_id)
        self.assertEqual(g.factory_dialog["unit_id"], machine_id)

    def test_mode_switches_restore_context_and_old_save_defaults(self):
        g = self.game
        machine_id = self.equip()
        original = g.circuit
        for switch in (lambda: sandbox.enter(g), lambda: timing_workshop.enter(g, "memory"),
                       lambda: g.open_invention(), lambda: g.open_compute()):
            g.open_factory()
            g.edit_factory_controller(machine_id)
            switch()
            self.assertIsNone(g.factory_context)
            g.open_factory()
            self.assertIs(g.circuit, original)
        old = village_from_data({"coins": 12})
        self.assertEqual(manufacturing.state(old)["equipment"], [])
        restored = village_from_data(json.loads(json.dumps(vars(g.village))))
        self.assertEqual(restored.manufacturing, g.village.manufacturing)


if __name__ == "__main__":
    unittest.main()
