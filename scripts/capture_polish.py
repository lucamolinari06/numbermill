"""Render the complete interface catalogue without touching player saves."""
import os
import sys
from pathlib import Path
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import pygame
from game import Game
from commissions import COMMISSIONS
import inventions


def main():
    out = ROOT / 'testing-screenshots' / 'polish'
    out.mkdir(parents=True, exist_ok=True)
    game = Game()
    def capture(name):
        game.draw()
        pygame.image.save(game.screen, out / (name + '.png'))
    with patch.object(game, 'save_game'):
        capture('menu')
        game.pending_delete = 2
        capture('delete-save')
        game.pending_delete = None
        for scene in ('town', 'contracts', 'compute', 'workshop'):
            game.scene = scene
            capture(scene)
        game.contract_page = 1
        game.scene = 'contracts'
        capture('contracts-page-2')
        game.scene = 'workshop'
        for tab in ('VILLAGE', 'LIBRARY', 'BUILD'):
            game.tab = tab
            capture(tab.lower())
        game.save_copy('A very long saved controller name to check the shelf')
        game.tab = 'LIBRARY'
        capture('library-filled')
        game.pending_design_delete = 0
        capture('delete-design')
        game.pending_design_delete = None
        game.tab = 'BUILD'
        for attr, name in [('help_open', 'help'), ('task_help_open', 'task-details'), ('delivery_open', 'delivery'), ('invention_picker', 'invention-goals')]:
            setattr(game, attr, True)
            capture(name)
            setattr(game, attr, False)
        game.test_commission()
        capture('contract-tests')
        game.test_results = None
        game.success_job = COMMISSIONS['mill']
        game.success_payout = 24
        capture('success')
        game.success_job = None
        game.edit_ports()
        capture('ports')
        game.port_editor = None
        game.village.arithmetic_unlocks = ['ADD', 'SUB', 'GT', 'EQ', 'MUL']
        for key in inventions.CHALLENGES:
            game.open_invention(key)
            capture('invention-' + key)
            game.test_invention()
            capture('tests-' + key)
            game.invention.show_results = False
            game.task_help_open = True
            capture('details-' + key)
            game.task_help_open = False
            game.close_invention()
        game.scene = 'compute'
        game.compute_results = [dict(a=255, b=255, expected=65025, actual=65025, passed=True) for _ in range(8)]
        capture('compute-tests')
        game.scene = 'ledger'
        for tab in ('Overview', 'Map', 'People', 'Businesses', 'Trade', 'Inventors', 'Workshop'):
            game.ledger_tab = tab
            capture('ledger-' + tab.lower())
    pygame.quit()
    print('Saved interface catalogue to', out)


if __name__ == '__main__':
    main()
