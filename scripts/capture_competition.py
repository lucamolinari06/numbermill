"""Review natural business entry and interfaces in an isolated disposable save."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pygame
from game import Game
from town import LOCATIONS


def main():
    output = ROOT / 'testing-screenshots' / 'competition-polish'
    output.mkdir(parents=True, exist_ok=True)
    scratch = ROOT / '.test-tmp'
    scratch.mkdir(exist_ok=True)
    with TemporaryDirectory(dir=scratch) as directory, \
            patch('game.SAVES_DIR', Path(directory) / 'saves'), \
            patch('game.SAVE_FILE', Path(directory) / 'legacy.json'), \
            patch('game.DESIGNS_FILE', Path(directory) / 'designs.json'):
        game = Game()
        game.start_slot(2)

        def capture(name):
            game.draw()
            pygame.image.save(game.screen, output / f'{name}.png')

        game.town.player_x, game.town.player_y = LOCATIONS['east_bakery']
        game.interact_town()
        assert game.town_dialogue == 'east_bakery'
        capture('bakery-plot-dialogue')
        game.interact_town()
        # Commission completion is fixture setup; entry and all subsequent
        # production, shopping, walking and migration use the real simulation.
        game.village.complete_mill_job()
        days = []
        for _ in range(20):
            game.village.advance_day(game.town)
            days.append({'day': game.village.day, 'population': len(game.village.citizens),
                         'status': game.village.competition_status,
                         'produced': game.village.last_day_report.get('produced'),
                         'cash': {key: firm['cash'] for key, firm in game.village.businesses.items()}})
        assert 'east_bakery' in game.village.businesses, 'Natural business entry never occurred'
        game.town.update_visuals(0)
        game.town.player_x, game.town.player_y = LOCATIONS['east_bakery']
        capture('east-bakery-open')
        game.interact_town()
        capture('jun-dialogue')
        game.town_dialogue = 'person:Agnes'
        game.town_topic = 'town'
        capture('cora-competition-dialogue')
        game.town_dialogue = None
        game.open_ledger()
        for tab in ('Overview', 'Map', 'Businesses', 'People', 'Trade'):
            game.select_ledger_tab(tab)
            if tab == 'Businesses':
                game.ledger_index = list(game.village.businesses).index('east_bakery')
            capture('ledger-' + tab.lower())
        game.save_game()
        reloaded = Game()
        reloaded.start_slot(2)
        assert reloaded.village.competition_events == game.village.competition_events
        assert reloaded.village.businesses['east_bakery'] == game.village.businesses['east_bakery']
        (output / 'natural-growth.json').write_text(json.dumps(days, indent=2), encoding='utf-8')
        pygame.quit()
    print(output)


if __name__ == '__main__':
    main()
