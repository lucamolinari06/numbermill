"""Capture authored request states in a disposable village."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pygame
from game import Game
from character_projects import evaluate, DEFINITIONS


def main():
    output = ROOT / 'testing-screenshots' / 'character-requests'
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=ROOT / '.test-tmp') as directory, \
            patch('game.SAVES_DIR', Path(directory) / 'saves'), \
            patch('game.SAVE_FILE', Path(directory) / 'legacy.json'), \
            patch('game.DESIGNS_FILE', Path(directory) / 'designs.json'):
        game = Game()
        game.start_slot(2)
        game.village.complete_mill_job()
        for _ in range(10):
            game.village.advance_day(game.town)
        # Explicit fixtures for all three situations; never edit the user's save.
        game.village.last_day_report = {'day': game.village.day, 'produced': {}, 'meals': {}}
        game.village.businesses['parts_shop']['stock']['parts'] = 0
        game.village.businesses['east_bakery']['operating_state'] = 'paused'
        evaluate(game.village)
        game.open_requests()
        for index, (key, definition) in enumerate(DEFINITIONS.items()):
            game.request_index = index
            game.draw()
            pygame.image.save(game.screen, output / f'{key}-offered.png')
            game.act_on_request(key)
            game.village.material_inventory.update(definition['bill'])
            game.act_on_request(key)
            game.draw()
            pygame.image.save(game.screen, output / f'{key}-completed.png')
        game.scene = 'town'
        game.town_dialogue = 'person:Dara'
        game.town_topic = 'hopes'
        game.draw()
        pygame.image.save(game.screen, output / 'dara-reflection.png')
        pygame.quit()
    print(output)


if __name__ == '__main__':
    main()
