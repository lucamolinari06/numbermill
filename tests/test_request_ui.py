import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pygame
from game import Game
from economy import Village
from daily_life import state, settle
from character_projects import evaluate


class RequestIntegrationTests(unittest.TestCase):
    def test_dialogue_to_request_accept_delivery_and_reload(self):
        with tempfile.TemporaryDirectory(dir='.test-tmp') as directory, \
                patch('game.SAVES_DIR', Path(directory) / 'saves'), \
                patch('game.SAVE_FILE', Path(directory) / 'legacy.json'), \
                patch('game.DESIGNS_FILE', Path(directory) / 'designs.json'):
            game = Game()
            game.start_slot(2)
            game.village.last_day_report = {'day': 1, 'produced': {}, 'meals': {}}
            evaluate(game.village)
            game.town_dialogue = 'person:Dara'
            game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_5, mod=0))
            self.assertEqual(game.scene, 'requests')
            game.draw()
            game.handle_click((550, 587), 1)
            self.assertEqual(game.village.character_projects['pantry_shelf']['status'], 'accepted')
            game.village.material_inventory.update(timber=2, fittings=1)
            game.draw()
            game.handle_click((550, 587), 1)
            self.assertEqual(game.village.character_projects['pantry_shelf']['status'], 'completed')
            loaded = Game()
            loaded.start_slot(2)
            self.assertEqual(loaded.village.businesses['market']['pantry_protection'], 3)
            game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0))
            self.assertEqual(game.scene, 'town')
            pygame.quit()

    def test_pantry_protection_only_consumed_by_actual_spoilage(self):
        village = Village()
        market = village.businesses['market']
        market.update(pantry_protection=3)
        for day, bread, charges in [(5, 4, 3), (6, 4, 2), (12, 0, 2), (18, 4, 1), (24, 4, 0), (30, 4, 0)]:
            village.day = day
            state(village)
            market['stock']['bread'] = bread
            settle(village)
            self.assertEqual(market['pantry_protection'], charges)
            self.assertEqual(market['stock']['bread'], 3 if day == 30 else bread)
            snapshot = market['pantry_protection']
            settle(village)
            self.assertEqual(market['pantry_protection'], snapshot)
