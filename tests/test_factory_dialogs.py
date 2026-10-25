"""Factory icons, deliberate resale, and physical sensor connections."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pygame
from game import Game
from circuit import Circuit, edge_terminals
import factory_ui
import manufacturing


class FactoryDialogTests(unittest.TestCase):
    def setUp(self):
        Path(".test-tmp").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=".test-tmp")
        root = Path(self.temp.name)
        self.patches = [patch("game.SAVES_DIR", root / "saves"), patch("game.SAVE_FILE", root / "old.json"),
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

    def equip(self, kind, pos):
        g = self.game
        g.village.coins = 100
        g.village.businesses["toolmaker"]["stock"]["fittings"] = 30
        self.assertTrue(manufacturing.buy_equipment(g.village, kind, pos)[0])
        return manufacturing.state(g.village)["equipment"][-1]

    def test_icon_opens_details_without_purchase_and_modal_blocks_floor(self):
        g = self.game
        g.factory_page = "equipment"
        self.draw()
        self.click(factory_ui.icon_rect(0).center)
        self.assertEqual(g.factory_dialog["equipment"], "bench")
        self.assertEqual(g.village.coins, 12)
        self.draw()
        self.click(factory_ui.tile_rect((2, 2)).center)
        self.assertEqual(manufacturing.state(g.village)["equipment"], [])
        self.assertIsNone(g.factory_placing)
        self.assertTrue(factory_ui.handle_key(g, pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)))
        self.assertIsNone(g.factory_dialog)
        self.assertFalse(g.pause_menu_open)
        # Old modal and underlying buttons are invalid until the new view draws.
        self.click((780, 625))
        self.assertIsNone(g.factory_placing)
        self.assertEqual(g.village.coins, 12)

    def test_supply_grid_has_icon_only_buttons_and_actual_data_in_detail(self):
        g = self.game
        g.factory_page = "supplies"
        with patch.object(g, "button", wraps=g.button) as button:
            self.draw()
            icons = [call for call in button.call_args_list if pygame.Rect(call.args[0]).top == 224]
            self.assertEqual(len(icons), 3)
            self.assertTrue(all(call.args[1] == "" for call in icons))
        self.click(factory_ui.icon_rect(1).center)
        self.draw()
        self.assertEqual(g.factory_dialog["good"], "fittings")
        self.click((780, 625))
        self.assertEqual(g.village.material_inventory["fittings"], 1)
        self.assertEqual(g.village.coins, 9)

    def test_sale_requires_confirmation_and_obeys_busy_restriction(self):
        g = self.game
        bench = self.equip("bench", (2, 2))
        g.village.material_inventory.update(metal=1, fittings=1, fuel=1)
        manufacturing.start_batch(g.village, bench["id"])
        factory_ui.open_dialog(g, "sell", item_id=bench["id"])
        self.draw()
        before = g.village.coins
        self.click((780, 625))
        self.assertIsNotNone(manufacturing.get_machine(g.village, bench["id"]))
        self.assertEqual(g.village.coins, before)
        manufacturing.update(g.village, manufacturing.BATCH_SECONDS)
        self.draw()
        quote = manufacturing.equipment_sell_quote(g.village, bench["id"])
        self.assertTrue(quote["allowed"])
        self.click((780, 625))
        self.assertIsNone(manufacturing.get_machine(g.village, bench["id"]))
        self.assertEqual(g.village.coins, before + quote["price"])
        self.assertIsNone(g.factory_dialog)
        self.click((780, 625))
        self.assertEqual(g.village.coins, before + quote["price"])

    def test_storage_output_connects_to_selected_controller_port(self):
        g = self.game
        bench = self.equip("bench", (1, 2))
        rack = self.equip("storage", (2, 2))
        self.equip("controller", (3, 2))
        self.assertTrue(manufacturing.install_controller(g.village, bench["id"], Circuit(terminals=edge_terminals(("A", "B"))))[0])
        factory_ui.open_route(g, storage_id=rack["id"])
        self.draw()
        self.click((905, 445))  # Controller input B.
        self.draw()
        self.assertEqual(g.factory_dialog["port"], "B")
        self.assertEqual(g.factory_dialog["storage_id"], rack["id"])
        self.click((780, 625))
        self.assertEqual(bench["controller"]["sources"]["B"], rack["id"])
        self.assertEqual(bench["controller"]["inputs"]["B"], "metal")
        g.village.material_inventory["metal"] = 17
        self.assertEqual(manufacturing.input_values(g.village, bench["id"])["B"], 17)
        factory_ui.close_dialog(g)
        with patch("factory_ui._cable", wraps=factory_ui._cable) as cable:
            self.draw()
            self.assertEqual(cable.call_count, 2)  # Rack -> cabinet -> unit.

    def test_trader_and_display_settings_render_and_preserve_full_number(self):
        g = self.game
        buyer = self.equip("buyer", (1, 1))
        seller = self.equip("seller", (2, 1))
        display = self.equip("display", (3, 1))
        for item in (buyer, seller, display):
            factory_ui.open_dialog(g, "settings", item_id=item["id"])
            self.draw()
            for i, (rect, _) in enumerate(g.factory_dialog_buttons):
                self.assertTrue(pygame.Rect(310, 125, 660, 550).contains(rect))
                self.assertFalse(any(rect.colliderect(other) for other, _ in g.factory_dialog_buttons[i + 1:]))
        factory_ui.open_dialog(g, "settings", item_id=buyer["id"])
        self.draw()
        self.click((905, 250))
        self.assertEqual(buyer["config"]["good"], "fittings")
        manufacturing.configure_display(g.village, display["id"], "cash")
        g.village.coins = 12345
        g.factory_selected = display["id"]
        factory_ui.close_dialog(g)
        g.factory_page = "floor"
        with patch("factory_ui.fit_text", wraps=factory_ui.fit_text) as text:
            self.draw()
            self.assertTrue(any(call.args[2] == "12345" for call in text.call_args_list))
        a, b = pygame.Surface((80, 70)), pygame.Surface((80, 70))
        factory_ui.equipment_sprite(a, "display", a.get_rect(), value=12345)
        factory_ui.equipment_sprite(b, "display", b.get_rect(), value=99)
        self.assertNotEqual(pygame.image.tostring(a, "RGB"), pygame.image.tostring(b, "RGB"))


if __name__ == "__main__":
    unittest.main()
