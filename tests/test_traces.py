import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import pygame

from circuit import Circuit, Part, CONDUCTORS
from game import Game
import inventions
import workshop_floor


def traced(kind="AND"):
    circuit = Circuit()
    circuit.set_part((5, 3), Part(kind))
    circuit.connect((1, 3), (5, 3), 0, [(3, 3.5)])
    circuit.connect((4, 6), (5, 3), 1, [(5.5, 6)])
    circuit.connect((5, 3), (9, 3), 0, [(7, 3.5)])
    return circuit


class TraceCircuitTests(unittest.TestCase):
    def test_explicit_connections_numeric_buses_and_roundtrip(self):
        circuit = traced("ADD")
        self.assertEqual(circuit.evaluate(255, 255), (510, True))
        snapshot = circuit.snapshot()
        restored = Circuit.from_snapshot(snapshot)
        self.assertEqual(restored.snapshot(), snapshot)
        self.assertEqual(restored.evaluate(255, 255), (510, True))
        circuit = traced()
        circuit.tick()
        self.assertEqual(circuit.active[(5, 3)], 0)
        self.assertTrue(all(case.passed for case in circuit.commission_test_results("AND")))

    def test_crossings_and_neighboring_components_do_not_connect(self):
        circuit = traced("XOR")
        for trace in circuit.traces:
            trace["points"] = [[7.5, 7.5]]
        self.assertEqual(circuit.evaluate(1, 1), (0, True))
        self.assertEqual(circuit.evaluate(1, 0), (1, True))
        circuit.disconnect((9, 3), 0)
        circuit.set_part((8, 3), Part("NOT"))
        self.assertEqual(circuit.evaluate(0, 0), (0, True))

    def test_deleting_component_cleans_links_and_bad_socket_is_rejected(self):
        circuit = traced()
        circuit.set_part((5, 3), None)
        self.assertEqual(circuit.traces, [])
        circuit = traced()
        rows = circuit.snapshot()
        next(row for row in rows if row["kind"] == "TRACE")["pin"] = 9
        with self.assertRaises(ValueError):
            Circuit.from_snapshot(rows)

    def test_nested_traced_devices_keep_timing_and_numeric_values(self):
        child = traced("ADD")
        outer = traced()
        outer.set_part((5, 3), Part("DEVICE", device={"id": 1, "name": "Adder", "parts": child.snapshot()}))
        self.assertEqual(outer.evaluate(255, 255), (510, True))
        self.assertEqual(Circuit.from_snapshot(outer.snapshot()).evaluate(5, 7), (12, True))

    def test_legacy_pipe_migration_preserves_truth_tables_and_waypoints(self):
        for kind in ("AND", "OR", "XOR", "ADD"):
            circuit = Circuit()
            for x in (2, 3, 5, 6, 7, 8):
                circuit.set_part((x, 3), Part("PIPE"))
            for y in (4, 5):
                circuit.set_part((4, y), Part("PIPE", 1))
            circuit.set_part((4, 3), Part(kind))
            expected = [circuit.evaluate(a, b) for a, b in ((0, 0), (0, 1), (1, 0), (1, 1), (255, 255))]
            circuit.convert_pipes()
            self.assertFalse(any(p.kind in CONDUCTORS for p in circuit.parts.values()))
            self.assertEqual(len(circuit.traces), 3)
            self.assertTrue(all(trace["points"] for trace in circuit.traces))
            self.assertEqual([circuit.evaluate(a, b) for a, b in ((0, 0), (0, 1), (1, 0), (1, 1), (255, 255))], expected)

    def test_migration_preserves_direct_connections_without_pipes(self):
        circuit = Circuit()
        for x in range(2, 9):
            circuit.set_part((x, 3), Part("OR"))
        self.assertEqual(circuit.evaluate(1, 0), (1, True))
        circuit.convert_pipes()
        self.assertEqual(len(circuit.traces), 8)
        self.assertEqual(circuit.evaluate(1, 0), (1, True))


class SharedFloorTests(unittest.TestCase):
    def test_contract_and_compute_use_identical_grid_and_socket_gestures(self):
        game = Game()
        game.scene = "workshop"
        game.draw()
        metrics = game.board_metrics()
        game.select_part("AND")
        bx, by, cell = metrics
        game.handle_click((bx + 5.5 * cell, by + 3.5 * cell), 1)
        game.handle_click(workshop_floor.socket(game, (0, 3), 1), 1)
        game.handle_click((bx + 3 * cell, by + 2 * cell), 1)
        game.handle_click(workshop_floor.socket(game, (5, 3), 3), 1)
        self.assertEqual(game.circuit.traces[0]["points"], [[3, 2]])
        game.handle_click(workshop_floor.socket(game, (5, 3), 3), 3)
        self.assertEqual(game.circuit.traces, [])
        game.village.arithmetic_unlocks = ["MUL"]
        game.open_compute()
        game.build_compute()
        self.assertEqual(game.scene, "workshop")
        self.assertEqual(game.board_metrics(), metrics)
        game.draw()

    def test_invention_save_keeps_root_and_library_named_ports(self):
        with tempfile.TemporaryDirectory() as directory, patch("game.SAVES_DIR", Path(directory)):
            game = Game()
            game.current_slot = 2
            game.scene = "workshop"
            game.circuit = traced()
            root = game.circuit.snapshot()
            game.open_invention()
            game.circuit.set_part((5, 2), Part("XOR"))
            game.port_names["SUM"] = "Low bit"
            game.save_copy("Prototype", announce=False)
            game.save_game()
            saved_floor = deepcopy(game.circuit.snapshot())
            loaded = Game()
            loaded.start_slot(2)
            self.assertEqual(loaded.circuit.snapshot(), root)
            loaded.load_design(0)
            self.assertEqual(loaded.scene, "workshop")
            self.assertEqual(loaded.circuit.snapshot(), saved_floor)
            self.assertEqual(loaded.port_names["SUM"], "Low bit")
            loaded.close_invention()
            self.assertEqual(loaded.circuit.snapshot(), root)
            loaded.open_invention()
            self.assertEqual(loaded.port_names["SUM"], "Low bit")

    def test_legacy_inventions_migrate_and_all_unlocks_still_pass(self):
        from test_inventions import solution
        game = Game()
        game.scene = "workshop"
        metrics = game.board_metrics()
        for key in inventions.CHALLENGES:
            game.village.invention_drafts[key] = solution(key)
            game.open_invention(key)
            self.assertEqual(game.board_metrics(), metrics)
            game.test_invention()
            self.assertTrue(all(row["passed"] for row in game.invention.rows))
            game.draw()
            game.close_invention()
        self.assertEqual(set(game.village.arithmetic_unlocks), {"ADD", "SUB", "GT", "EQ", "MUL"})
