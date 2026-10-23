import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from copy import deepcopy
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
import pygame

from circuit import Circuit, Part, validate_device
from economy import Village
from game import Game, BOARD_X, BOARD_Y, CELL
from town import Town, WIDTH, HEIGHT, WORLD_W, WORLD_H


def controller(gate):
    circuit = Circuit()
    for x in (2, 3, 5, 6, 7, 8):
        circuit.set_part((x, 3), Part("PIPE"))
    for y in (4, 5):
        circuit.set_part((4, y), Part("PIPE", 1))
    circuit.set_part((4, 3), gate)
    return circuit


def definition(circuit, number=1, version=1):
    return {"id": number, "version": version, "name": "Controller",
            "parts": circuit.snapshot(), "ports": {"A": "Power", "B": "Safe", "OUT": "Run"}}


class DeviceTests(unittest.TestCase):
    def test_nested_devices_preserve_logic_delay_and_live_state(self):
        circuit = controller(Part("AND"))
        for layer in range(4):
            circuit = controller(Part("DEVICE", device=definition(circuit, layer + 1)))
        circuit.switches = {"A": True, "B": True}
        circuit.tick()
        self.assertFalse(circuit.lamp_on())
        for _ in range(80):
            circuit.tick()
        self.assertTrue(circuit.lamp_on())
        before = deepcopy(circuit.__dict__)
        self.assertTrue(all(case.passed for case in circuit.commission_test_results("AND")))
        self.assertEqual(circuit.tick_count, before["tick_count"])
        self.assertEqual(circuit.devices[(4, 3)].tick_count, before["devices"][(4, 3)].tick_count)
        restored = Circuit.from_snapshot(circuit.snapshot())
        self.assertTrue(all(case.passed for case in restored.commission_test_results("AND")))

    def test_instances_keep_independent_state_and_pinned_definition(self):
        original = controller(Part("OR"))
        saved = definition(original)
        outer = controller(Part("DEVICE", device=saved))
        saved["parts"].clear()
        original.set_part((4, 3), Part("AND"))
        self.assertTrue(all(case.passed for case in outer.commission_test_results("OR")))
        outer.set_part((7, 6), Part("DEVICE", device=definition(original, 2)))
        self.assertIsNot(outer.devices[(4, 3)], outer.devices[(7, 6)])

    def test_recursive_definitions_are_rejected(self):
        recursive = definition(Circuit())
        recursive["parts"].append({"kind": "DEVICE", "x": 3, "y": 3, "device": recursive})
        with self.assertRaises(ValueError):
            validate_device(recursive)
        with self.assertRaises(ValueError):
            Circuit().set_part((3, 3), Part("DEVICE", device=recursive))

    def test_slot_roundtrip_preserves_devices_and_root_while_inspecting(self):
        with tempfile.TemporaryDirectory() as directory, patch("game.SAVES_DIR", Path(directory)):
            game = Game()
            game.current_slot = 2
            game.circuit = controller(Part("DEVICE", device=definition(controller(Part("AND")))))
            game.port_names = {"A": "Power", "B": "Safe", "OUT": "Run"}
            snapshot = game.circuit.snapshot()
            game.inspect_device((4, 3))
            game.save_game()
            loaded = Game()
            loaded.start_slot(2)
            self.assertEqual(loaded.circuit.snapshot(), snapshot)
            self.assertEqual(loaded.port_names["B"], "Safe")
            self.assertTrue(all(case.passed for case in loaded.circuit.commission_test_results("AND")))

    def test_library_versions_placement_inspection_and_port_names(self):
        game = Game()
        game.scene = "workshop"
        game.circuit = controller(Part("AND"))
        game.port_names = {"A": "Power", "B": "Safe", "OUT": "Run"}
        game.save_copy(announce=False)
        game.load_design(0)
        game.circuit.set_part((4, 3), Part("OR"))
        game.save_copy(announce=False)
        self.assertEqual([d["version"] for d in game.designs], [1, 2])
        game.select_device(0)
        game.circuit = controller(Part("AND"))
        game.handle_click((BOARD_X + 4 * CELL + 15, BOARD_Y + 3 * CELL + 15), 1)
        self.assertTrue(all(c.passed for c in game.circuit.commission_test_results("AND")))
        root = game.circuit
        game.inspect_device((4, 3))
        self.assertEqual(game.port_names["B"], "Safe")
        game.draw()
        game.leave_device()
        self.assertIs(game.circuit, root)


class CitizenInteractionTests(unittest.TestCase):
    def test_camera_adjusted_click_opens_remote_npc_inspection(self):
        game = Game()
        game.scene = "town"
        game.town.player_x, game.town.player_y = 1000, 1180
        game.town.people["Mely"] = [800, 1150]
        camera_x = max(0, min(WORLD_W - WIDTH, int(1000 - WIDTH // 2)))
        camera_y = max(0, min(WORLD_H - HEIGHT, int(1180 - HEIGHT // 2)))
        game.handle_click((800 - camera_x, 1130 - camera_y), 1)
        self.assertEqual(game.town_dialogue, "person:Mely")
        self.assertEqual((game.town.player_x, game.town.player_y), (1000, 1180))

    def test_residents_continue_visits_without_advancing_economy(self):
        village = Village()
        town = Town()
        seen = {p["name"]: set() for p in village.citizens}
        before = (village.day, village.coins, deepcopy(village.businesses))
        for _ in range(2400):
            town.update_people(village, .1)
            for p in village.citizens:
                seen[p["name"]].add(p["destination"])
        self.assertTrue(all(len(destinations) >= 2 for destinations in seen.values()), seen)
        self.assertEqual((village.day, village.coins, village.businesses), before)


if __name__ == "__main__":
    unittest.main()
