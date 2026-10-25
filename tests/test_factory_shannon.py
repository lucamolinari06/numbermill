"""Factory reactions remember milestones without consuming them off screen."""
import json
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
from types import SimpleNamespace
import unittest

import pygame
import factory_shannon as companion


class FactoryShannonTests(unittest.TestCase):
    def game(self, scene="factory", **totals):
        workshop = {"equipment": [{"kind": "bench", "status": "Ready"}], **totals}
        return SimpleNamespace(village=SimpleNamespace(manufacturing=workshop, day=1), scene=scene,
                               pause_menu_open=False)

    def test_milestones_queue_once_and_offscreen_time_does_not_spend_them(self):
        game = self.game("town", produced=4, auto_produced=2, sold=1)
        companion.update(game, 1000)
        state = game.village.manufacturing["shannon"]
        self.assertEqual(state["seen"], list(companion.LINES))
        self.assertEqual(len(state["queue"]), 4)
        for _ in range(20):
            companion.update(game, 1000)
        self.assertEqual(len(state["queue"]), 4)
        game.scene = "factory"
        companion.update(game, .1)
        self.assertEqual(companion.current_line(game.village), companion.LINES["first_machine"])
        self.assertEqual(len(state["queue"]), 3)

    def test_saved_queue_and_current_remark_resume_without_repeating(self):
        game = self.game(produced=1)
        companion.update(game, .1)
        for _ in range(3):
            companion.update(game, 1)
        saved = json.loads(json.dumps(game.village.manufacturing))
        loaded = self.game()
        loaded.village.manufacturing = saved
        self.assertEqual(companion.current_line(loaded.village), companion.current_line(game.village))
        self.assertEqual(saved["shannon"]["remaining"], 7)
        for _ in range(7):
            companion.update(loaded, 1)
        self.assertEqual(companion.current_line(loaded.village), companion.LINES["first_batch"])
        self.assertEqual(saved["shannon"]["queue"], [])
        self.assertFalse(companion.event(loaded.village, "first_machine"))

    def test_pause_freezes_reading_and_shortage_diagnostic_does_not_repeat(self):
        game = self.game()
        companion.update(game, 0)
        data = game.village.manufacturing["shannon"]
        game.pause_menu_open = True
        companion.update(game, 100)
        self.assertEqual(data["remaining"], companion.READ_SECONDS)
        game.pause_menu_open = False
        game.village.manufacturing["equipment"][0]["status"] = "Need metal, fuel"
        for _ in range(10):
            companion.update(game, 1)
        self.assertIn("metal, fuel", companion.current_line(game.village))
        for _ in range(100):
            companion.update(game, 1)
        self.assertEqual(data["line"], "")
        self.assertEqual(data["shortage"], "metal, fuel")
        game.village.manufacturing["equipment"][0]["status"] = "Ready"
        companion.update(game, 1)
        self.assertEqual(data["shortage"], "")

    def test_entry_greetings_cycle_across_save_without_losing_milestones(self):
        game = self.game(produced=1)
        companion.observe(game.village)
        queued = list(game.village.manufacturing['shannon']['queue'])
        greetings = []
        for _ in range(len(companion.GREETINGS)):
            companion.enter_workshop(game.village)
            greetings.append(companion.current_line(game.village))
            game.village.manufacturing = json.loads(json.dumps(game.village.manufacturing))
        self.assertEqual(len(set(greetings)), len(companion.GREETINGS))
        self.assertEqual(game.village.manufacturing['shannon']['queue'], queued)
        for _ in range(10):
            companion.update(game, 1)
        companion.update(game, 0)
        self.assertEqual(companion.current_line(game.village), queued[0])
        companion.enter_workshop(game.village)
        self.assertIn(companion.current_line(game.village), companion.GREETINGS)
        self.assertNotEqual(companion.current_line(game.village), greetings[-1])

    def test_draw_preserves_clip_and_handles_new_empty_workshop(self):
        pygame.init()
        try:
            game = self.game()
            game.village.manufacturing = {}
            game.screen = pygame.Surface((900, 200))
            game.small = pygame.font.Font(None, 20)
            clip = pygame.Rect(2, 2, 880, 190)
            game.screen.set_clip(clip)
            companion.draw(game, (10, 20, 760, 130))
            self.assertEqual(game.screen.get_clip(), clip)
            self.assertTrue(companion.current_line(game.village))
        finally:
            pygame.quit()


if __name__ == "__main__":
    unittest.main()
