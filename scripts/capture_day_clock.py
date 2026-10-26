"""Reproduce dawn/clock views with disposable state; optional native rollover."""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--smoke', action='store_true')
    args = parser.parse_args()
    if not args.smoke:
        os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
    import pygame
    from daily_life import state, update_continuous, DAY_SECONDS
    from economy import Village
    from town import Town
    from ui_theme import make_font
    import day_clock
    import town_atmosphere

    pygame.init()
    output = ROOT/'testing-screenshots'/'day-clock'
    output.mkdir(parents=True, exist_ok=True)
    fonts = tuple(make_font(size) for size in (16,18,24,32))
    village, town = Village(), Town()
    town.player_x, town.player_y = 800,1410
    town.companion.reset((800,1410))
    surface = pygame.Surface((1280,760))
    sheet = pygame.Surface((1280,1140))
    for i, progress in enumerate((.94,.995,0.,.04,.085,.18)):
        state(village)['elapsed'] = progress*DAY_SECONDS
        town.draw(surface, fonts, village, None, '')
        pygame.image.save(surface, output/f'{i+1:02d}-{day_clock.phase_name(progress).lower()}.png')
        sheet.blit(pygame.transform.scale(surface,(640,380)), ((i%2)*640,(i//2)*380))
    pygame.image.save(sheet,output/'rollover-sheet.png')

    report = dict(palette_boundary_continuous=town_atmosphere.daylight(0)==town_atmosphere.daylight(1),
                  lamp_boundary_continuous=town_atmosphere.evening_light(0)==town_atmosphere.evening_light(1))
    if args.smoke:
        from game import Game
        with tempfile.TemporaryDirectory(dir=output) as folder:
            root = Path(folder)
            with patch('game.SAVES_DIR',root/'saves'), patch('game.SAVE_FILE',root/'old.json'), \
                    patch('game.DESIGNS_FILE',root/'designs.json'), patch('chapter_ui.active',return_value=False):
                g = Game(); g.start_slot(1); g.opening_screen = None
                pygame.display.set_caption('Numbermill - clock and dawn (disposable)')
                g.town.player_x,g.town.player_y = 800,1410
                g.town.companion.reset((800,1410))
                update_continuous(g.village,g.town,DAY_SECONDS-3.)
                start_day = g.village.day
                colors = []
                def draw():
                    g.town.draw(g.screen,(g.small,g.font,g.heading,g.big),g.village,None,'')
                for _ in range(1140):
                    pygame.event.pump();g.update(1/60);draw();g.viewport.present();g.clock.tick(60)
                    colors.append(town_atmosphere.daylight(town_atmosphere.clock_progress(g.village)))
                assert g.village.day == start_day+1
                assert max(max(abs(x-y) for x,y in zip(a,b)) for a,b in zip(colors,colors[1:])) <= 1
                pygame.image.save(g.screen,output/'native-dawn.png')
                g.pause_menu_open = True
                before = deepcopy(vars(g.village));draw();frozen=pygame.image.tobytes(g.screen,'RGB')
                for _ in range(60):
                    pygame.event.pump();g.update(1/60);draw();g.viewport.present();g.clock.tick(60)
                    assert pygame.image.tobytes(g.screen,'RGB') == frozen
                assert vars(g.village) == before
                report.update(native_driver=pygame.display.get_driver(),native_frames=1140,
                              rollover_days=1,paused_frames=60,exact_pause=True)
    (output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    pygame.quit()
    print(output)


if __name__ == '__main__':
    main()
