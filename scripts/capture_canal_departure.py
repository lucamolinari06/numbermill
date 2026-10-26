"""Review the southern boat's locked, repair and controller UI using disposable saves."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'tests'))

import pygame
import adventure
import boiler_tower
import canal_departure
import canal_progress
import manufacturing
from daily_life import state
from game import Game
from test_canal_progress import boat_design


def main():
    output = ROOT/'testing-screenshots'/'canal-settlement'
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as folder:
        root = Path(folder)
        with patch('game.SAVES_DIR', root/'saves'), patch('game.SAVE_FILE', root/'old.json'), \
                patch('game.DESIGNS_FILE', root/'designs.json'):
            g = Game(); g.start_slot(1); g.opening_screen = None
            g.town.player_x, g.town.player_y = canal_departure.RETURN_POSITION
            g.town.companion.reset(canal_departure.RETURN_POSITION)
            state(g.village)['elapsed'] = 65.

            def capture(name):
                g.draw()
                pygame.image.save(g.screen, output/(name+'.png'))

            capture('boat-01-southern-landing')
            canal_departure.open_panel(g)
            capture('boat-02-locked')
            adventure.state(g.village).update(expansion_complete=True, artifact=True)
            boiler_tower.state(g.village)['complete'] = True
            workshop = manufacturing.state(g.village)
            workshop['unlocks'] = ['precision_machine', 'steam_accumulator']
            workshop['goods']['precision_gears'] = 1
            capture('boat-03-repair')
            canal_departure.repair(g)
            capture('boat-04-gear-fitted')
            canal_departure.build(g)
            capture('boat-05-specification')
            adventure.close_editor(g)
            assert canal_progress.install(g.village, boat_design().snapshot())[0]
            canal_departure.open_panel(g)
            capture('boat-06-ready')
            g.open_settings(); g.controls_open = True
            capture('boat-07-controls')
            pygame.quit()
    print(output)


if __name__ == '__main__':
    main()
