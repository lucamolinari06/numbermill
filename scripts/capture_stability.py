"""Disposable visual checks for sandbox, later levels and developed housing."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pygame
from game import Game
from commissions import COMMISSIONS
from daily_life import update_continuous
import sandbox


def main():
    output = ROOT / 'testing-screenshots' / 'stability-milestone'
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp, patch('game.SAVES_DIR', Path(temp) / 'saves'), \
            patch('game.SAVE_FILE', Path(temp) / 'old.json'), patch('game.DESIGNS_FILE', Path(temp) / 'designs.json'):
        game = Game()
        game.start_slot(2)

        def capture(name):
            game.draw()
            pygame.image.save(game.screen, output / (name + '.png'))

        game.scene = 'workshop'
        sandbox.enter(game)
        capture('sandbox')
        sandbox.leave(game)
        game.open_contract_board()
        game.contract_page = 4
        capture('later-commissions')
        game.scene, game.ledger_tab = 'ledger', 'Map'
        capture('map-plots')
        # Install the original upgrades through the existing fixture helpers;
        # later offers are completed as their prerequisites and funding permit.
        for key in list(COMMISSIONS)[:6]:
            game.village.fulfill_job(key)
        for _ in range(180):
            for key in list(COMMISSIONS)[6:]:
                if game.village.offers.get(key, {}).get('status') in ('open', 'bid'):
                    game.village.fulfill_job(key)
            update_continuous(game.village, game.town, 180)
        capture('developed-map')
        game.scene = 'town'
        game.town.player_x, game.town.player_y = 1830, 1390
        game.town.update_visuals(1)
        capture('developed-homes')
        game.scene, game.ledger_tab = 'ledger', 'Overview'
        capture('developed-overview')
    pygame.quit()
    print(output)


if __name__ == '__main__':
    main()
