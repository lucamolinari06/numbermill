import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import pygame

from circuit import Circuit, Part, WIDTH, edge_terminals
from game import Game
import inventions
from test_traces import traced


def terminal(circuit, name):
    return next(pos for pos, port in circuit.terminals.items() if port["name"] == name)


def majority():
    circuit = Circuit(terminals=edge_terminals(("A", "B", "C")))
    for pos, kind in (((4, 2), "AND"), ((4, 4), "AND"), ((4, 6), "AND"),
                      ((7, 3), "OR"), ((10, 4), "OR")):
        circuit.set_part(pos, Part(kind))
    for target, names in (((4, 2), ("A", "B")), ((4, 4), ("A", "C")), ((4, 6), ("B", "C"))):
        for pin, name in enumerate(names):
            circuit.connect(terminal(circuit, name), target, pin)
    circuit.connect((4, 2), (7, 3), 0)
    circuit.connect((4, 4), (7, 3), 1)
    circuit.connect((7, 3), (10, 4), 0)
    circuit.connect((4, 6), (10, 4), 1)
    circuit.connect((10, 4), terminal(circuit, "OUT"), 0)
    return circuit


class TerminalLayoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        for name, value in (("SAVES_DIR", root / "saves"), ("SAVE_FILE", root / "old.json"),
                            ("DESIGNS_FILE", root / "designs.json")):
            context = patch("game." + name, value)
            context.start()
            self.addCleanup(context.stop)

    def tearDown(self):
        pygame.quit()

    def test_majority_uses_three_independent_live_inputs(self):
        circuit = majority()
        circuit.switches.update({"A": True, "B": False, "C": True})
        for _ in range(8):
            circuit.tick()
        state = deepcopy(circuit.__dict__)
        rows = circuit.commission_test_results("MAJORITY")
        self.assertEqual(len(rows), 8)
        self.assertEqual([row.inputs for row in rows],
                         [(a, b, c) for a in (False, True) for b in (False, True) for c in (False, True)])
        self.assertTrue(all(row.passed for row in rows))
        self.assertEqual(circuit.switches, state["switches"])
        self.assertEqual(circuit.active, state["active"])
        self.assertEqual(circuit.tick_count, state["tick_count"])
        self.assertEqual(circuit.evaluate(1, 0, 0), (0, True))
        self.assertEqual(circuit.evaluate(1, 0, 1), (1, True))
        restored = Circuit.from_snapshot(circuit.snapshot())
        self.assertTrue(all(row.passed for row in restored.commission_test_results("MAJORITY")))

    def test_a_single_input_wire_cannot_pass_majority(self):
        for name in ("A", "B", "C"):
            circuit = Circuit(terminals=edge_terminals(("A", "B", "C")))
            circuit.connect(terminal(circuit, name), terminal(circuit, "OUT"), 0)
            self.assertFalse(all(row.passed for row in circuit.commission_test_results("MAJORITY")))
        circuit = Circuit()
        circuit.connect((4, 6), (9, 3), 0)
        self.assertFalse(any(row.passed for row in circuit.commission_test_results("MAJORITY")))

    def test_edge_migration_preserves_routes_and_a_block_on_the_destination(self):
        circuit = traced("ADD")
        circuit.set_part((0, 3), Part("NOT"))
        corners = [trace["points"] for trace in circuit.traces]
        circuit.layout_terminals(("A", "B"))
        self.assertTrue(all(pos[0] in (0, WIDTH - 1) for pos in circuit.terminals))
        self.assertEqual(circuit.parts[(1, 3)].kind, "NOT")
        self.assertEqual([trace["points"] for trace in circuit.traces], corners)
        self.assertEqual(circuit.evaluate(255, 255), (510, True))
        self.assertEqual(Circuit.from_snapshot(circuit.snapshot()).evaluate(8, 12), (20, True))

    def test_sorter_grid_toggle_c_and_sidebar_describe_the_same_third_input(self):
        game = Game()
        game.scene = "workshop"
        game.village.active_commission = "sorter"
        game.draw()
        self.assertEqual(set(game.circuit.switches), {"A", "B", "C"})
        point = terminal(game.circuit, "C")
        self.assertEqual(point[0], 0)
        bx, by, cell = game.board_metrics()
        game.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                           pos=(bx + (point[0] + .5) * cell, by + (point[1] + .5) * cell)))
        self.assertTrue(game.circuit.switches["C"])
        self.assertIn("Input C: delivery queue busy", " ".join(game.task_description()[1]))
        game.test_commission()
        self.assertEqual(len(game.test_results), 8)
        self.assertEqual(game.circuit.switches["C"], True)
        game.draw()

    def test_every_builder_places_all_anchors_on_the_boundary(self):
        game = Game()
        game.scene = "workshop"
        game.draw()
        self.assert_edges(game.circuit)
        game.village.arithmetic_unlocks = ["ADD", "MUL"]
        game.open_compute()
        game.build_compute()
        self.assert_edges(game.circuit)
        for key in inventions.CHALLENGES:
            game.open_invention(key)
            game.draw()
            self.assert_edges(game.circuit)
            game.close_invention()

    def assert_edges(self, circuit):
        for pos, port in circuit.terminals.items():
            self.assertEqual(pos[0], WIDTH - 1 if port["output"] else 0)

    def test_two_input_edge_design_still_places_as_a_nested_device(self):
        game = Game()
        game.scene = "workshop"
        game.village.arithmetic_unlocks = ["ADD"]
        game.circuit = traced("ADD")
        game.draw()
        game.save_copy("Adder", announce=False)
        game.select_device(0)
        self.assertEqual(game.selected, "DEVICE")
        outer = traced()
        outer.set_part((5, 3), Part("DEVICE", device=game.held_device))
        self.assertEqual(outer.evaluate(10, 20), (30, True))

    def test_save_reload_and_library_keep_c_and_existing_connections(self):
        with tempfile.TemporaryDirectory() as folder, patch("game.SAVES_DIR", Path(folder) / "saves"):
            game = Game()
            game.current_slot = 2
            game.scene = "workshop"
            game.village.active_commission = "sorter"
            game.village.complete_mill_job()
            game.village.complete_bakery_job()
            game.village.complete_market_job()
            game.circuit = majority()
            game.draw()
            game.save_copy("Three inputs", announce=False)
            game.save_game()
            loaded = Game()
            loaded.start_slot(2)
            loaded.scene = "workshop"
            loaded.draw()
            self.assertEqual(set(loaded.circuit.switches), {"A", "B", "C"})
            self.assertTrue(all(row.passed for row in loaded.circuit.commission_test_results("MAJORITY")))
            loaded.load_design(0)
            self.assertTrue(all(row.passed for row in loaded.circuit.commission_test_results("MAJORITY")))
