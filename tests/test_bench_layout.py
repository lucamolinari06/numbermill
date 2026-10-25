"""Rendered text and controls must keep their own space across bench modes."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pygame
from game import Game
import sandbox
import ui_theme
import workbench


class BenchLayoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.paths = [patch("game.SAVES_DIR", root / "saves"),
                      patch("game.SAVE_FILE", root / "save.json"),
                      patch("game.DESIGNS_FILE", root / "designs.json")]
        for item in self.paths:
            item.start()
        self.game = Game()
        self.game.start_slot(1)
        self.game.scene = "workshop"

    def tearDown(self):
        pygame.quit()
        for item in reversed(self.paths):
            item.stop()
        self.temp.cleanup()

    def check_layout(self, left):
        g = self.game
        text_boxes = []
        original = ui_theme.fit_text

        def capture(*args, **kwargs):
            rect = original(*args, **kwargs)
            if rect.left >= left and 136 <= rect.top < 724 and rect.width:
                text_boxes.append((rect, str(args[2])))
            return rect

        with patch("ui_theme.fit_text", side_effect=capture), patch("pygame.mouse.get_pos", return_value=(0, 0)):
            g.draw()
        buttons = [rect for rect, _ in g.buttons if rect.left >= left and 136 <= rect.top < 724]
        for i, (rect, label) in enumerate(text_boxes):
            self.assertLessEqual(rect.right, 1228, label)
            self.assertLessEqual(rect.bottom, 724, label)
            for other, other_label in text_boxes[i + 1:]:
                self.assertFalse(rect.colliderect(other), (label, other_label))
            for button in buttons:
                self.assertFalse(rect.colliderect(button), (label, button))
        for i, rect in enumerate(buttons):
            for other in buttons[i + 1:]:
                self.assertFalse(rect.colliderect(other), (rect, other))

    def test_build_groups_with_contract_and_three_input_sandbox(self):
        g = self.game
        for free in (False, True):
            if free:
                sandbox.enter(g)
                sandbox.toggle_inputs(g)
            for group, parts in workbench.COMPONENT_GROUPS.items():
                g.bench_component_group = group
                for kind in parts:
                    g.selected = kind
                    self.check_layout(956)

    def test_library_with_full_page_and_long_names_and_village(self):
        g = self.game
        for i in range(5):
            g.save_copy("Long controller name for a production machine " + str(i))
        g.port_names = {name: "An exceptionally long signal description " + name for name in ("A", "B", "OUT")}
        g.tab = "LIBRARY"
        self.check_layout(770)
        g.tab = "VILLAGE"
        self.check_layout(770)

    def test_every_math_component_has_a_distinct_working_button(self):
        g = self.game
        sandbox.enter(g)
        g.bench_component_group = "Math"
        for i, kind in enumerate(workbench.COMPONENT_GROUPS["Math"]):
            g.draw()
            g.handle_click((992 + i % 5 * 49, 496 + i // 5 * 46), 1)
            self.assertEqual(g.selected, kind)

    def test_invention_compute_and_timing_panels(self):
        import computation
        import inventions
        import sequential
        import timing_workshop
        from circuit import ARITHMETIC
        g = self.game
        g.village.arithmetic_unlocks = list(ARITHMETIC)
        for key in inventions.CHALLENGES:
            g.open_invention(key)
            self.check_layout(956)
            g.close_invention()
        for key in computation.JOBS:
            g.select_compute(key)
            g.build_compute()
            self.check_layout(956)
        for key in sequential.CHALLENGES:
            timing_workshop.enter(g, key)
            self.check_layout(956)
            timing_workshop.leave(g)

    def test_field_editor_groups_with_long_validation_result(self):
        import adventure
        g = self.game
        for kind in adventure.TITLES:
            adventure.enter_editor(g, kind)
            g.adventure_spec = False
            g.adventure_result = "A=65535 B=65535 C=65535: expected 65535, got 65535 (unstable)"
            for group, parts in workbench.COMPONENT_GROUPS.items():
                g.adventure_group = group
                g.selected = parts[-1]
                self.check_layout(956)
            adventure.close_editor(g)

    def test_field_specification_text_stays_inside_modal(self):
        import adventure
        g = self.game
        original = ui_theme.fit_text
        for kind in adventure.TITLES:
            adventure.enter_editor(g, kind)
            g.buttons.clear()
            boxes = []

            def capture(*args, **kwargs):
                rect = original(*args, **kwargs)
                boxes.append(rect)
                return rect

            with patch("ui_theme.fit_text", side_effect=capture):
                adventure.draw_specification(g)
            for i, rect in enumerate(boxes):
                self.assertTrue(pygame.Rect(240, 218, 800, 380).contains(rect))
                for other in boxes[i + 1:]:
                    self.assertFalse(rect.colliderect(other))
                for button, _ in g.buttons:
                    self.assertFalse(rect.colliderect(button))
            adventure.close_editor(g)


if __name__ == "__main__":
    unittest.main()
