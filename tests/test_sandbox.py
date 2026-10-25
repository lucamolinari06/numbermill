import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import pygame
import sandbox
from circuit import Part
from game import Game


class SandboxTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.paths = [patch('game.SAVES_DIR', root / 'saves'),
                      patch('game.SAVE_FILE', root / 'save.json'),
                      patch('game.DESIGNS_FILE', root / 'designs.json')]
        for item in self.paths:
            item.start()
        self.game = Game()
        self.game.start_slot(1)
        self.game.scene = 'workshop'

    def tearDown(self):
        for item in reversed(self.paths):
            item.stop()
        pygame.quit()
        self.temp.cleanup()

    def test_free_components_clock_and_delivery_are_isolated(self):
        g = self.game
        original = g.circuit
        village = deepcopy(vars(g.village))
        g.draw()
        g.handle_click((1150, 650), 1)
        self.assertIsNotNone(g.sandbox_context)
        g.select_part('MUL')
        self.assertEqual(g.selected, 'MUL')
        self.assertIsNone(g.invention)
        g.circuit.set_part((5, 3), Part('MUL'))
        ports = {p['name']: pos for pos, p in g.circuit.terminals.items()}
        g.circuit.connect(ports['A'], (5, 3), 0)
        g.circuit.connect(ports['B'], (5, 3), 1)
        g.circuit.connect((5, 3), ports['OUT'], 0)
        g.circuit.switches.update(A=9, B=7)
        g.test_commission()
        self.assertIn('63 / stable', g.message)
        g.update(1)
        g.next_day()
        g.submit_design()
        self.assertEqual(vars(g.village), village)
        self.assertFalse(g.submission_ready)
        sandbox.leave(g)
        self.assertIs(g.circuit, original)
        g.select_part('MUL')
        self.assertIsNotNone(g.invention)

    def test_save_reload_preserves_both_floors_and_inputs(self):
        g = self.game
        g.circuit.set_part((3, 3), Part('AND'))
        original = g.circuit.snapshot()
        sandbox.enter(g)
        sandbox.toggle_inputs(g)
        g.circuit.set_part((6, 3), Part('XOR'))
        g.circuit.switches['C'] = True
        g.numeric_mode = True
        free = g.circuit.snapshot()
        g.save_game()
        g.start_slot(1)
        self.assertEqual(g.circuit.snapshot(), original)
        sandbox.enter(g)
        self.assertEqual(g.circuit.snapshot(), free)
        self.assertTrue(g.circuit.switches['C'])
        self.assertTrue(g.numeric_mode)
        g.draw()
        g.return_to_menu()
        g.start_slot(1)
        self.assertEqual(g.circuit.snapshot(), original)

    def test_library_cannot_bypass_earned_blocks(self):
        g = self.game
        sandbox.enter(g)
        g.circuit.set_part((6, 3), Part('ADD'))
        g.save_copy('Experiment')
        sandbox.leave(g)
        before = g.circuit.snapshot()
        g.load_design(0)
        self.assertEqual(g.circuit.snapshot(), before)
        self.assertIn('Invent', g.message)
        sandbox.enter(g)
        g.load_design(0)
        self.assertEqual(g.circuit.parts[(6, 3)].kind, 'ADD')


if __name__ == '__main__':
    unittest.main()
