import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
import json
import unittest
from dataclasses import asdict
from game import Game, village_from_data
from economy import Village
from inventor_roster import roster, contracts, name_for_offer
import pygame


class InventorRosterTests(unittest.TestCase):
    def test_profiles_and_contracts_remain_separate_after_reload(self):
        v = Village()
        v.inventor_profiles['ada_lovelace'] = {'name': 'Ada Lovelace', 'specialty': 'Calculation', 'earned': 25}
        v.offers['mill'].update(status='bid', inventor_id='ada_lovelace', finish_day=5)
        loaded = village_from_data(json.loads(json.dumps(asdict(v))))
        self.assertEqual(len(roster(loaded)), 2)
        self.assertEqual(contracts(loaded, 'grace'), [])
        self.assertEqual(contracts(loaded, 'ada_lovelace')[0][0], 'mill')
        self.assertEqual(name_for_offer(loaded, loaded.offers['mill']), 'Ada Lovelace')
        loaded.offers['mill'].pop('inventor_id')
        self.assertEqual(contracts(loaded, 'grace')[0][0], 'mill')

    def test_directory_pages_select_and_render_additional_inventors(self):
        game = Game()
        game.scene = 'ledger'
        game.ledger_tab = 'Inventors'
        for i in range(8):
            game.village.inventor_profiles[f'inventor_{i}'] = {'name': f'Inventor {i}'}
        for _ in range(7):
            game.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN, mod=0))
        self.assertEqual(game.ledger_index, 7)
        game.draw()
        game.handle_click((200, 312), 1)
        self.assertEqual(game.ledger_index, 6)
        game.draw()
        pygame.quit()
