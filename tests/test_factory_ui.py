import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pygame
from circuit import Circuit, edge_terminals
from game import Game
import factory_ui
import manufacturing


class FactoryUITests(unittest.TestCase):
    def setUp(self):
        Path(".test-tmp").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=".test-tmp")
        root = Path(self.temp.name)
        self.patches = [patch("game.SAVES_DIR", root / "saves"),
                        patch("game.SAVE_FILE", root / "old.json"),
                        patch("game.DESIGNS_FILE", root / "designs.json")]
        for item in self.patches:
            item.start()
        self.game = Game()
        self.game.start_slot(1)
        self.game.open_factory()
        self.draw()

    def tearDown(self):
        pygame.quit()
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def draw(self):
        self.game.buttons.clear()
        factory_ui.draw(self.game)

    def click(self, point):
        factory_ui.click(self.game, point, 1)

    def test_purchase_placement_cancel_and_collisions_are_atomic(self):
        g = self.game
        self.draw()
        self.click((950, 175))  # Equipment tab.
        self.draw()
        self.click(factory_ui.icon_rect(0).center)  # Open bench details.
        self.draw()
        self.click((780, 625))  # Choose placement.
        self.draw()
        self.assertEqual(g.factory_placing, "bench")
        self.assertEqual(g.village.coins, 12)
        self.assertTrue(factory_ui.handle_key(g, pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)))
        self.assertIsNone(g.factory_placing)
        self.assertEqual(g.village.coins, 12)
        factory_ui.place(g, "bench")
        self.click(factory_ui.tile_rect((2, 2)).center)
        state = manufacturing.state(g.village)
        self.assertEqual(g.village.coins, 8)
        self.assertEqual(len(state["equipment"]), 1)
        self.assertEqual(state["equipment"][0]["pos"], [2, 2])
        factory_ui.place(g, "storage")
        self.click(factory_ui.tile_rect((2, 2)).center)
        self.assertEqual(g.village.coins, 8)
        self.assertEqual(len(state["equipment"]), 1)
        self.assertEqual(g.factory_placing, "storage")
        self.click(factory_ui.tile_rect((3, 2)).center)
        self.assertEqual(g.village.coins, 2)
        self.assertEqual(len(state["equipment"]), 2)
        bench = state["equipment"][0]
        factory_ui.move(g, bench)
        self.click(factory_ui.tile_rect((3, 2)).center)
        self.assertEqual(bench["pos"], [2, 2])
        self.click(factory_ui.tile_rect((1, 3)).center)
        self.assertEqual(bench["pos"], [1, 3])

    def test_manual_supply_production_and_customer_ui_work_from_starting_cash(self):
        g = self.game
        factory_ui.place(g, "bench")
        self.click(factory_ui.tile_rect((2, 2)).center)
        g.factory_page = "supplies"
        self.draw()
        for index in range(3):
            self.click(factory_ui.icon_rect(index).center)
            self.draw()
            self.click((780, 625))
            factory_ui.close_dialog(g)
            self.draw()
        self.assertEqual(g.village.coins, 0)
        self.assertEqual(g.village.material_inventory, {"metal": 1, "fittings": 1, "fuel": 1})
        g.factory_page = "floor"
        self.draw()
        self.click((900, 450))
        bench = manufacturing.state(g.village)["equipment"][0]
        self.assertGreater(bench["busy"], 0)
        manufacturing.update(g.village, manufacturing.BATCH_SECONDS)
        g.factory_page = "orders"
        self.draw()
        self.click((1000, 370))
        self.assertEqual(g.village.coins, 10)
        self.assertEqual(manufacturing.state(g.village)["sold"], 1)
        self.assertEqual(manufacturing.state(g.village)["goods"]["repair_kits"], 0)

    def test_signal_controls_and_equipment_render_without_overlapping_buttons(self):
        g = self.game
        g.village.coins = 100
        g.village.businesses["toolmaker"]["stock"]["fittings"] = 20
        g.village.coins = 500
        manufacturing.unlock_equipment(g.village, "precision_machine")
        for i, kind in enumerate(manufacturing.CATALOG):
            self.assertTrue(manufacturing.buy_equipment(g.village, kind, (i, 2))[0])
        bench = manufacturing.state(g.village)["equipment"][0]
        circuit = Circuit(terminals=edge_terminals(("A", "B")))
        self.assertTrue(manufacturing.install_controller(g.village, bench["id"], circuit)[0])
        g.factory_selected = bench["id"]
        factory_ui.open_route(g, unit_id=bench["id"])
        self.draw()
        self.click((905, 315))
        self.click((780, 625))
        self.assertEqual(bench["controller"]["inputs"]["A"], "stock")
        factory_ui.open_dialog(g, "settings", item_id=bench["id"])
        self.draw()
        self.click((905, 275))
        self.assertEqual(manufacturing.state(g.village)["target"], 7)
        factory_ui.close_dialog(g)
        for page in factory_ui.PAGES:
            g.factory_page = page
            self.draw()
            rects = [rect for rect, action in g.buttons]
            for index, rect in enumerate(rects):
                self.assertTrue(g.screen.get_rect().contains(rect))
                self.assertFalse(any(rect.colliderect(other) for other in rects[index + 1:]), (page, rect))

    def test_escape_closes_subpage_or_placement_before_pause(self):
        g = self.game
        factory_ui.prepare(g)
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
        g.factory_page = "supplies"
        self.assertTrue(factory_ui.handle_key(g, event))
        self.assertEqual(g.factory_page, "floor")
        self.assertFalse(factory_ui.handle_key(g, event))
        factory_ui.place(g, "display")
        self.assertTrue(factory_ui.handle_key(g, event))
        self.assertFalse(factory_ui.handle_key(g, event))

    def test_customer_pagination_reaches_fourth_buyer_without_clickthrough(self):
        g = self.game
        factory_ui.prepare(g)
        g.factory_page = "orders"
        manufacturing.state(g.village)["goods"]["repair_kits"] = 1
        offers = [{"id": f"customer_{i}", "name": f"Customer {i + 1}", "price": 10,
                   "demand": 1, "reason": "One funded kit delivery."} for i in range(4)]
        with patch("manufacturing.offers", return_value=offers), \
                patch("manufacturing.sell_goods", return_value=(True, "Delivered one kit.")) as sell:
            self.draw()
            self.click((1150, 630))
            self.assertEqual(g.factory_order_page, 1)
            sell.assert_not_called()
            self.draw()
            rects = [rect for rect, action in g.buttons]
            for index, rect in enumerate(rects):
                self.assertFalse(any(rect.colliderect(other) for other in rects[index + 1:]))
            self.click((1000, 370))
            sell.assert_called_once_with(g.village, "customer_3")
            self.click((860, 630))
            self.assertEqual(g.factory_order_page, 0)
            self.draw()
            self.assertEqual(sell.call_count, 1)
        # A restored or altered list safely clamps a previously selected page.
        g.factory_order_page = 99
        with patch("manufacturing.offers", return_value=offers[:2]):
            self.draw()
            self.assertEqual(g.factory_order_page, 0)


if __name__ == "__main__":
    unittest.main()
