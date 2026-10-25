"""Manual terminal editing uses the full unsigned sixteen-bit input range."""
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import pygame
from circuit import Circuit, edge_terminals
import workshop_floor


class NumericInputTests(unittest.TestCase):
    def setUp(self):
        circuit = Circuit(terminals=edge_terminals(("A", "B")))
        circuit.trace_mode = True
        self.game = SimpleNamespace(
            circuit=circuit, numeric_mode=True, sandbox_context={}, invention=None,
            selected="TRACE", trace_source=None, trace_points=[],
            board_metrics=lambda: (0, 0, 40), board_pos=lambda xy: (int(xy[0] // 40), int(xy[1] // 40)))
        self.positions = {port["name"]: pos for pos, port in circuit.terminals.items()}

    def click(self, name="A", button=1, mods=0):
        x, y = self.positions[name]
        with patch("pygame.key.get_mods", return_value=mods):
            workshop_floor.click(self.game, ((x + .5) * 40, (y + .5) * 40), button)

    def test_click_can_cross_previous_eight_bit_boundary(self):
        self.game.circuit.switches["A"] = 255
        self.click()
        self.assertEqual(self.game.circuit.switches["A"], 256)

    def test_left_and_right_click_wrap_at_sixteen_bits(self):
        self.game.circuit.switches["A"] = 65535
        self.click()
        self.assertEqual(self.game.circuit.switches["A"], 0)
        self.click(button=3)
        self.assertEqual(self.game.circuit.switches["A"], 65535)

    def test_shift_and_control_accelerate_in_both_directions(self):
        for mods, step in ((pygame.KMOD_SHIFT, 16), (pygame.KMOD_CTRL, 256),
                           (pygame.KMOD_CTRL | pygame.KMOD_SHIFT, 256)):
            with self.subTest(mods=mods):
                self.game.circuit.switches["B"] = 0
                self.click("B", mods=mods)
                self.assertEqual(self.game.circuit.switches["B"], step)
                self.click("B", button=3, mods=mods)
                self.assertEqual(self.game.circuit.switches["B"], 0)
                self.click("B", button=3, mods=mods)
                self.assertEqual(self.game.circuit.switches["B"], 65536 - step)

    def test_binary_mode_keeps_toggle_and_ignores_right_click(self):
        self.game.numeric_mode = False
        self.click(mods=pygame.KMOD_CTRL)
        self.assertIs(self.game.circuit.switches["A"], True)
        self.click(button=3)
        self.assertIs(self.game.circuit.switches["A"], True)
        self.click()
        self.assertIs(self.game.circuit.switches["A"], False)

    def test_output_terminal_does_not_create_an_input(self):
        before = self.game.circuit.switches.copy()
        self.click("OUT", mods=pygame.KMOD_CTRL)
        self.assertEqual(self.game.circuit.switches, before)


if __name__ == "__main__":
    unittest.main()
