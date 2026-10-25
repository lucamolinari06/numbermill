import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pygame
from circuit import Circuit, Part, edge_terminals
from game import Game
import sandbox
import timing_workshop


def register_floor():
    circuit = Circuit(terminals=edge_terminals(("A", "B")))
    circuit.set_part((6, 3), Part("REGISTER"))
    ports = {port["name"]: pos for pos, port in circuit.terminals.items()}
    circuit.connect(ports["A"], (6, 3), 0)
    circuit.connect(ports["B"], (6, 3), 1)
    circuit.connect((6, 3), ports["OUT"], 0)
    return circuit


class TimingWorkshopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.patches = [patch("game.SAVES_DIR", self.root / "saves"),
                        patch("game.SAVE_FILE", self.root / "save.json"),
                        patch("game.DESIGNS_FILE", self.root / "designs.json")]
        for item in self.patches:
            item.start()
        self.game = Game()
        self.game.start_slot(1)
        self.game.scene = "workshop"

    def tearDown(self):
        pygame.quit()
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def key(self, key):
        self.game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0))

    def test_goal_ui_certification_and_escape_restore_paid_floor(self):
        g = self.game
        original = g.circuit
        self.key(pygame.K_i)
        g.draw()
        g.handle_click((450, 445), 1)
        self.assertEqual(g.timing_key, "memory")
        g.circuit = register_floor()
        coins = g.village.coins
        self.key(pygame.K_t)
        self.assertIn("memory", g.village.sequential_records)
        self.assertEqual(g.village.coins, coins)
        self.assertFalse(g.submission_ready)
        g.draw()
        g.handle_click((850, 630), 1)
        self.assertTrue(g.task_help_open)
        self.key(pygame.K_ESCAPE)
        self.assertFalse(g.task_help_open)
        self.key(pygame.K_ESCAPE)
        self.assertIsNone(g.timing_results)
        self.key(pygame.K_ESCAPE)
        self.assertIsNone(g.timing_key)
        self.assertIs(g.circuit, original)

    def test_live_register_state_survives_save_load_draw_and_continues(self):
        g = self.game
        g.circuit = register_floor()
        g.circuit.switches.update(A=513, B=1)
        for _ in range(7):
            g.circuit.tick()
        g.circuit.switches.update(A=8)
        g.tick_interval = .4
        g.elapsed = .12
        g.paused = True
        expected = g.circuit.runtime_snapshot()
        g.save_game()
        loaded = Game()
        loaded.start_slot(1)
        loaded.scene = "workshop"
        loaded.draw()
        self.assertEqual(loaded.circuit.runtime_snapshot(), expected)
        self.assertEqual(loaded.elapsed, .12)
        self.assertEqual(loaded.tick_interval, .4)
        self.assertTrue(loaded.paused)
        for a, b in ((8, 1), (9, 0), (17, 1), (40, 1)):
            for game in (g, loaded):
                game.circuit.switches.update(A=a, B=b)
                game.circuit.tick()
            self.assertEqual(loaded.circuit.runtime_snapshot(), g.circuit.runtime_snapshot())

    def test_timing_draft_and_library_keep_job_and_memory_separate(self):
        g = self.game
        original = g.circuit
        timing_workshop.enter(g, "memory")
        g.circuit = register_floor()
        g.circuit.switches.update(A=109, B=1)
        for _ in range(5):
            g.circuit.tick()
        state = g.circuit.runtime_snapshot()
        g.save_copy("Memory")
        g.load_design(0)
        self.assertEqual(g.timing_key, "memory")
        self.assertIs(g.timing_context["circuit"], original)
        self.assertEqual(g.circuit.tick_count, 0)  # Library is a schematic.
        g.circuit.restore_runtime(state)
        g.return_to_menu()
        g.start_slot(1)
        timing_workshop.enter(g, "memory")
        g.draw()
        self.assertEqual(g.circuit.runtime_snapshot(), state)
        timing_workshop.leave(g)
        g.load_design(0)
        self.assertEqual(g.timing_key, "memory")
        self.assertEqual(g.circuit.tick_count, 0)

    def test_sandbox_probe_does_not_reset_a_clock_and_restores_runtime(self):
        g = self.game
        sandbox.enter(g)
        g.circuit.set_part((6, 3), Part("CLOCK"))
        for _ in range(7):
            g.circuit.tick()
        state = g.circuit.runtime_snapshot()
        sandbox.probe(g)
        self.assertEqual(g.circuit.runtime_snapshot(), state)
        self.assertIn("Live output", g.message)
        sandbox.leave(g)
        sandbox.enter(g)
        self.assertEqual(g.circuit.runtime_snapshot(), state)

    def test_old_save_without_runtime_or_new_fields_loads(self):
        g = self.game
        file = self.root / "saves" / "slot_1.json"
        saved = json.loads(file.read_text())
        for key in ("circuit_runtime", "circuit_elapsed", "circuit_paused"):
            saved.pop(key, None)
        for key in ("sequential_drafts", "sequential_records"):
            saved["village"].pop(key, None)
        file.write_text(json.dumps(saved))
        g.start_slot(1)
        self.assertEqual(g.circuit.tick_count, 0)
        self.assertEqual(g.village.sequential_records, {})
        timing_workshop.enter(g, "counter")
        g.draw()


if __name__ == "__main__":
    unittest.main()
