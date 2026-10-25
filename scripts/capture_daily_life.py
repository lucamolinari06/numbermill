"""Capture the attendance/food chain in isolated villages; never touch player saves."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pygame
from game import Game
from economy import Village
from town import Town


def main():
    output = ROOT / 'testing-screenshots' / 'daily-life'
    output.mkdir(parents=True, exist_ok=True)
    comparison = {}
    with tempfile.TemporaryDirectory() as directory, patch('game.SAVES_DIR', Path(directory)):
        game = Game()
        for upgraded in (False, True):
            v, town = Village(), Town()
            v.rival_busy_until = 99
            if upgraded:
                v.complete_mill_job()
            reports = []
            for day in range(5):
                v.update_life(town, 180)
                reports.append({'day': v.day, 'fed': v.last_day_report['fed'],
                                'bread_price': v.bread_price, 'produced': v.last_day_report['produced'],
                                'paid': v.last_day_report['paid'],
                                'missed_meals': sum(h['missed_meals'] for h in v.households.values())})
                if day < 4:
                    v.advance_day(town)
            name = 'upgraded-mill' if upgraded else 'slow-mill'
            comparison[name] = reports
            game.village, game.town = v, town
            game.scene = 'ledger'
            for tab in ('Overview', 'People', 'Businesses', 'Trade'):
                game.select_ledger_tab(tab)
                if tab == 'Businesses':
                    game.ledger_index = list(v.businesses).index('bakery')
                game.draw()
                pygame.image.save(game.screen, output / f'{name}-{tab.lower()}.png')
        game.scene = 'town'
        game.draw()
        pygame.image.save(game.screen, output / 'town-clock.png')
        pygame.quit()
    (output / 'comparison.json').write_text(json.dumps(comparison, indent=2), encoding='utf-8')
    print(output)


if __name__ == '__main__':
    main()
