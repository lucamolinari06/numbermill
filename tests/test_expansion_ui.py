"""Play-facing supply purchases, funded delivery, and richer conversations."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pygame
from game import Game
from circuit import Part
from town import LOCATIONS, Town
from materials import SHOPS, material_bill
from dialogue import conversation, PERSONAL_LINES, VOICES


class ExpansionUITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.patches = [patch('game.SAVES_DIR', Path(self.temp.name) / 'saves'),
                        patch('game.SAVE_FILE', Path(self.temp.name) / 'old.json'),
                        patch('game.DESIGNS_FILE', Path(self.temp.name) / 'old-designs.json')]
        for item in self.patches:
            item.start()
        self.game = Game()
        self.game.start_slot(2)

    def tearDown(self):
        pygame.quit()
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def key(self, key):
        self.game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode=''))

    def test_shop_visit_and_buy_transfer_real_stock_and_cash_and_reload(self):
        game = self.game
        for shop, details in SHOPS.items():
            good, price = details["good"], details["price"]
            game.town_dialogue = None
            game.town.player_x, game.town.player_y = LOCATIONS[shop]
            firm = game.village.businesses[shop]
            before = (game.village.coins, firm['cash'], firm['stock'][good])
            self.key(pygame.K_e)
            self.assertEqual(game.town_dialogue, shop)
            game.draw()
            self.key(pygame.K_e)
            self.assertEqual(game.village.coins, before[0] - price)
            self.assertEqual(firm['cash'], before[1] + price)
            self.assertEqual(firm['stock'][good], before[2] - 1)
            self.assertEqual(game.village.material_inventory[good], 1)
            self.assertIn('Bought', game.message)
        game.return_to_menu()
        game.start_slot(2)
        self.assertEqual(game.village.material_inventory, material_bill('mill'))

    def test_delivery_blocks_without_materials_then_customer_advance_completes(self):
        game = self.game
        game.scene = 'workshop'
        for x in (2, 3, 5, 6, 7, 8):
            game.circuit.set_part((x, 3), Part('PIPE'))
        for y in (4, 5):
            game.circuit.set_part((4, y), Part('PIPE', 1))
        game.circuit.set_part((4, 3), Part('AND'))
        game.test_commission()
        self.assertTrue(game.submission_ready)
        self.key(pygame.K_RETURN)
        self.key(pygame.K_1)
        self.assertTrue(game.delivery_open)
        self.assertFalse(game.village.mill_machine)
        self.assertIn('Missing delivery supplies', game.delivery_error)
        self.assertEqual(game.village.coins, 12)
        game.draw()
        game.handle_click((480, 602), 1)
        self.assertEqual(game.village.material_reservations['mill'], material_bill('mill'))
        self.assertEqual(game.village.coins, 12)
        self.key(pygame.K_1)
        self.assertTrue(game.village.mill_machine)
        self.assertEqual(game.success_payout, 18)
        self.assertEqual(game.village.coins, 30)
        self.assertEqual(game.village.offers['mill']['material_advance'], 6)
        self.assertNotIn('mill', game.village.material_reservations)
        game.draw()

    def test_fourth_topic_is_authored_and_preserves_saved_conversation(self):
        game = self.game
        game.town_dialogue = 'person:Mely'
        work = conversation(game.village, 'Mely', 'work')
        self.key(pygame.K_4)
        self.assertEqual(game.town_topic, 'hopes')
        hopes = conversation(game.village, 'Mely', 'hopes')
        self.assertNotEqual(work, hopes)
        self.assertIn(hopes[0], (VOICES['Mely'][1], *PERSONAL_LINES['Mely']['hopes']))
        self.assertEqual(conversation(game.village, 'Mely', 'hopes'), hopes)
        game.draw()
        game.return_to_menu()
        game.start_slot(2)
        mely = next(p for p in game.village.citizens if p['name'] == 'Mely')
        self.assertTrue(any('hopes' in memory for memory in mely['memories']))

    def test_artisan_street_routes_have_no_building_barriers(self):
        # Player can follow the connected east-west streets to every new shop.
        for shop in SHOPS:
            x, y = LOCATIONS[shop]
            for px in range(1120, x + 1, 10):
                self.assertFalse(Town._inside_building(px, y + 30), (shop, px))
