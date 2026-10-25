"""Schematic cues must agree with real input/output directions at every rotation."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
import unittest
import pygame
from circuit import Part, VECTORS
from gate_symbols import GATES, symbol_image, LESSONS
from game import PixelFont


class GateSymbolTests(unittest.TestCase):
    def test_rotated_leads_match_actual_sockets(self):
        for kind in GATES:
            for rotation in range(4):
                icon = symbol_image(kind, 100, (255, 255, 255), rotation, True)
                inputs, outputs = Part(kind, rotation).ports()
                for direction, (dx, dy) in enumerate(VECTORS):
                    x, y = round(49.5 + dx * 47), round(49.5 + dy * 47)
                    ink = any(icon.get_at((xx, yy)).a > 100
                              for xx in range(x-2, x+3) for yy in range(y-2, y+3))
                    self.assertEqual(ink, direction in inputs + outputs, (kind, rotation, direction))

    def test_inversion_bubble_and_xor_curve_are_distinct(self):
        inverter = symbol_image('NOT', 100, (255, 255, 255))
        self.assertLess(inverter.get_at((77, 50)).a, 20)
        self.assertGreater(inverter.get_at((77, 43)).a, 100)
        shapes = {pygame.image.tobytes(symbol_image(kind, 100, (255, 255, 255)), 'RGBA') for kind in GATES}
        self.assertEqual(len(shapes), 4)
        xor = symbol_image('XOR', 100, (255, 255, 255))
        either = symbol_image('OR', 100, (255, 255, 255))
        # Exclusive OR has an additional arc behind the OR input edge.
        self.assertGreater(xor.get_at((29, 50)).a, either.get_at((29, 50)).a)

    def test_gate_lessons_fit_the_selected_tool_area(self):
        pygame.font.init()
        font = PixelFont(14)
        for lesson in LESSONS.values():
            self.assertLessEqual(font.render(lesson, True, (0, 0, 0)).get_width(), 244)
