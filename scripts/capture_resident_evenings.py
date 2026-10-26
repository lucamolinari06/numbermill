"""Real evening routines in disposable saves; optional native entry/pause check."""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--smoke',action='store_true')
    args=parser.parse_args()
    if not args.smoke:os.environ.setdefault('SDL_VIDEODRIVER','dummy')
    import pygame
    from citizens import home_time
    from daily_life import state,update_continuous
    from game import Game
    output=ROOT/'testing-screenshots'/'resident-evenings';output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as folder:
        root=Path(folder)
        with patch('game.SAVES_DIR',root/'saves'),patch('game.SAVE_FILE',root/'old.json'), \
                patch('game.DESIGNS_FILE',root/'designs.json'),patch('chapter_ui.active',return_value=False):
            g=Game();g.start_slot(1);g.opening_screen=None
            pygame.display.set_caption('Numbermill - evening home entry (disposable)')

            def draw():
                g.town.draw(g.screen,(g.small,g.font,g.heading,g.big),g.village,None,'')

            def view(name):
                g.town.player_x,g.town.player_y=(800,1410)
                g.town.companion.reset((800,1410));draw()
                pygame.image.save(g.screen,output/(name+'.png'))

            snapshots=[]
            for hour,minute in ((17,30),(18,0),(18,30),(19,0),(19,56)):
                target=((hour*60+minute)-480)/4
                current=state(g.village)
                update_continuous(g.village,g.town,target-current['elapsed']-current['accumulator'])
                g.town.update_visuals(1.)
                label=f'{hour:02d}-{minute:02d}';view(label)
                snapshots.append(dict(clock=g.town.clock_time(g.village), residents=[
                    dict(name=p['name'],activity=p['activity'],destination=p['destination'],
                         indoors=g.town.indoors(p['name']),home_time=home_time(p['name'],g.village.day))
                    for p in g.village.citizens]))
            current=state(g.village)
            update_continuous(g.village,g.town,180-current['elapsed']-current['accumulator']+2.5)
            g.town.update_visuals(1.);view('next-morning')
            assert not any(g.town.indoors(p['name']) for p in g.village.citizens)
            report=dict(snapshots=snapshots,morning_return=True)
            if args.smoke:
                g.start_slot(2);g.opening_screen=None
                update_continuous(g.village,g.town,146.)
                g.town.update_visuals(1.)
                g.town.player_x,g.town.player_y=(800,1410)
                g.town.companion.reset((800,1410))
                entries=set()
                for _ in range(720):
                    pygame.event.pump();g.update(1/60);draw();g.viewport.present();g.clock.tick(60)
                    entries.update(p['name'] for p in g.village.citizens if g.town.indoors(p['name']))
                assert entries,'No native home entry observed'
                pygame.image.save(g.screen,output/'native-entry.png')
                g.handle_key(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE,mod=0,unicode=''))
                assert g.pause_menu_open
                before=deepcopy(vars(g.village));draw();frozen=pygame.image.tobytes(g.screen,'RGB')
                for _ in range(60):
                    pygame.event.pump();g.update(1/60);draw();g.viewport.present();g.clock.tick(60)
                    assert pygame.image.tobytes(g.screen,'RGB')==frozen
                assert vars(g.village)==before
                report.update(native_driver=pygame.display.get_driver(),native_frames=720,
                              observed_entries=sorted(entries),paused_frames=60,exact_pause=True)
            (output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            pygame.quit()
    print(output)


if __name__=='__main__':main()
