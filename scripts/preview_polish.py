"""Isolated visual review; --live opens a disposable village, never player saves."""
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if '--live' not in sys.argv:
    os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
import pygame
from game import Game
from town import LOCATIONS
import ledger


def main():
    output = ROOT / 'testing-screenshots' / 'polish'
    output.mkdir(parents=True, exist_ok=True)
    scratch = ROOT / '.test-tmp'
    scratch.mkdir(exist_ok=True)
    with TemporaryDirectory(dir=scratch) as directory, \
            patch('game.SAVES_DIR', Path(directory) / 'saves'), \
            patch('game.SAVE_FILE', Path(directory) / 'legacy.json'), \
            patch('game.DESIGNS_FILE', Path(directory) / 'designs.json'):
        game = Game()
        if '--live' in sys.argv:
            pygame.display.set_caption('Numbermill - Polish Review (disposable save)')
            game.run()
            return

        def capture(name):
            game.draw()
            pygame.image.save(game.screen, output / f'{name}.png')

        capture('menu')
        game.start_slot(2)
        game.town.update_people(game.village, 12)
        capture('town')
        game.shannon.toggle(game)
        game.shannon.update(.3)
        capture('shannon-menu')
        for page in ('news', 'help'):
            game.shannon.page = page
            capture('shannon-' + page)
        game.shannon.toggle(game)
        for shop in ('sawmill', 'foundry', 'toolmaker'):
            game.town.player_x, game.town.player_y = LOCATIONS[shop]
            game.town_dialogue = shop
            capture(shop + '-counter')
        game.shannon.update(.3)
        game.town.player_x, game.town.player_y = LOCATIONS['workshop']
        game.town_dialogue = 'person:Mely'
        for topic in ('work', 'family', 'town', 'hopes'):
            game.town_topic = topic
            capture('dialogue-' + topic)
        game.town_dialogue = None
        game.scene = 'workshop'
        capture('workshop')
        game.help_open = True
        capture('help')
        game.help_open = False
        game.task_help_open = True
        capture('task-details')
        game.task_help_open = False
        game.save_copy('Mill controller')
        game.tab = 'LIBRARY'
        capture('library')
        game.edit_ports()
        capture('ports')
        game.port_editor = None
        game.tab = 'BUILD'
        game.open_contract_board()
        for page in (0, 1):
            game.contract_page = page
            capture(f'contracts-{page + 1}')
        game.open_compute()
        capture('compute')
        game.open_ledger()
        for tab in ledger.TABS:
            game.select_ledger_tab(tab)
            capture(f'ledger-{tab.lower()}')
        game.village.complete_mill_job()
        for _ in range(5):
            game.village.advance_day(game.town)
            game.town.update_visuals(0)
            if game.village.migration.get('housing_stage') == 'construction':
                game.scene = 'town'
                game.town.player_x, game.town.player_y = LOCATIONS['home_4']
                capture('cottage-construction')
        game.scene = 'ledger'
        game.select_ledger_tab('People')
        game.ledger_index = 6
        capture('migration-people')
        game.scene = 'town'
        game.town.player_x, game.town.player_y = LOCATIONS['home_4']
        capture('new-cottage')
        game.town_dialogue = 'person:Rowan'
        game.town_topic = 'town'
        capture('new-neighbor')
        pygame.quit()
    print(output)


if __name__ == '__main__':
    main()
