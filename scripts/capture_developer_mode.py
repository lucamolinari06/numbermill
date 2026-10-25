"""Capture developer controls with disposable saves; --smoke uses a real window."""
import argparse
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--smoke', action='store_true')
    args = parser.parse_args()
    if not args.smoke: os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
    import pygame
    import adventure
    import boiler_tower as tower
    import developer_mode as dev
    from game import Game
    output = ROOT/'testing-screenshots'/'developer-mode'
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as folder:
        root = Path(folder)
        with patch('game.SAVES_DIR', root/'saves'), patch('game.SAVE_FILE', root/'old.json'), patch('game.DESIGNS_FILE', root/'designs.json'):
            g = Game()
            g.start_slot(1)
            adventure.state(g.village)['expansion_complete'] = True
            tower.enter(g)
            adventure.close_notice(g)
            g.adventure_speech_time = 0

            def capture(name):
                g.draw()
                pygame.image.save(g.screen, str(output/(name+'.png')))

            g.pause_menu_open = True
            g.handle_click(g.pause_buttons()[-1][0].center, 1)
            capture('pause')
            g.pause_menu_open = False
            capture('tower')
            tower.edit(g)
            g.adventure_spec = False
            dev.solve(g)
            capture('editor')
            # Workshop pause has one extra row: check the longest menu too.
            g.pause_menu_open = True
            capture('editor-pause')
            g.pause_menu_open = False
            adventure.close_editor(g)
            adventure.enter(g)
            g.adventure_speech_time = 0
            capture('mosswater')
            if args.smoke:
                tower.enter(g)
                adventure.close_notice(g)
                start = pygame.time.get_ticks()
                while pygame.time.get_ticks()-start < 2500:
                    for event in pygame.event.get(): g.handle_event(event)
                    dt = g.clock.tick(60)/1000
                    tower.step(g, dt, horizontal=1, thrust=True)
                    g.update(dt)
                    g.draw()
                capture('live-flight')
            pygame.quit()


if __name__ == '__main__': main()
