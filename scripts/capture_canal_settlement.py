"""Disposable Reedhaven review and optional real-window movement check."""
import argparse
from collections import defaultdict
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'tests'))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--smoke',action='store_true')
    args=parser.parse_args()
    if not args.smoke:os.environ.setdefault('SDL_VIDEODRIVER','dummy')
    os.environ.setdefault('SDL_AUDIODRIVER','dummy')
    import pygame
    from game import Game
    import adventure
    import boiler_tower
    import canal_layout
    import canal_progress
    import canal_settlement
    import manufacturing
    import scene_depth
    from daily_life import state as daily_state
    from test_canal_progress import boat_design
    output=ROOT/'testing-screenshots'/'canal-settlement';output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as folder:
        root=Path(folder)
        with patch('game.SAVES_DIR',root/'saves'),patch('game.SAVE_FILE',root/'old.json'),patch('game.DESIGNS_FILE',root/'designs.json'):
            g=Game();g.start_slot(1);g.opening_screen=None;g.opening_reveal=0.;g.chapter_view=None
            adventure.state(g.village).update(expansion_complete=True,artifact=True)
            boiler_tower.state(g.village)['complete']=True
            workshop=manufacturing.state(g.village)
            workshop['unlocks']=['precision_machine','steam_accumulator']
            workshop['goods']['precision_gears']=1
            assert canal_progress.repair(g.village)[0]
            assert canal_progress.install(g.village,boat_design().snapshot())[0]
            canal_settlement.enter(g);g.opening_reveal=0.
            current=canal_progress.state(g.village)
            daily_state(g.village)['elapsed']=65.
            def capture(name,position=None,modal=None):
                if position is not None:
                    current['position']=list(position)
                    g.canal_runtime['companion'].reset(position)
                g.canal_runtime['modal']=modal
                g.draw();pygame.image.save(g.screen,output/(name+'.png'))
            capture('01-arrival',modal='arrival')
            capture('02-landing',(2370,460))
            capture('03-footbridge',(860,670))
            capture('04-lockhouse',(460,940))
            capture('05-market-square',(1080,1020))
            capture('06-chandlery',(1510,980))
            capture('07-homes',(950,1340))
            capture('08-upstream',(230,685),modal='waterworks')
            for name in canal_layout.RESIDENTS:
                capture('conversation-'+name.lower(),canal_layout.POINTS[name],modal=name)
            workshop['goods'].update(repair_kits=2,steam_valves=1)
            assert canal_progress.deliver_request(g.village)[0]
            capture('09-repaired-cistern',(1080,1020))
            for label,elapsed in (('10-dawn',9.),('11-dusk',150.),('12-night',178.)):
                daily_state(g.village).update(elapsed=elapsed,accumulator=0.)
                capture(label,(1080,1020))
            daily_state(g.village).update(elapsed=65.,accumulator=0.)
            ground,props,_=g.canal_art_cache
            overview=ground.copy();scene_depth.draw(overview,(0,0),props)
            import canal_art
            canal_art.cistern(overview,980,1038,True)
            canal_art.boat(overview,2285,625)
            canal_art.survey_plate(overview,230,680)
            pygame.image.save(overview,output/'overview-native.png')
            pygame.image.save(pygame.transform.scale(overview,(1400,850)),output/'overview.png')
            if args.smoke:
                pygame.display.set_caption('Numbermill - Reedhaven (disposable)')
                current['position']=list(canal_layout.ARRIVAL)
                g.canal_runtime['modal']=None;g.canal_runtime['companion'].reset(current['position'])
                frames=0
                for target in ((2370,300),(860,250),(860,670),(850,950),(1090,950),(1090,900)):
                    for _ in range(900):
                        x,y=current['position'];dx=target[0]-x;dy=target[1]-y
                        if abs(dx)<4 and abs(dy)<4:break
                        keys=defaultdict(bool)
                        if abs(dx)>=4:keys[pygame.K_d if dx>0 else pygame.K_a]=True
                        if abs(dy)>=4:keys[pygame.K_s if dy>0 else pygame.K_w]=True
                        with patch('pygame.key.get_pressed',return_value=keys):g.update(1/60)
                        assert not canal_layout.blocked(*current['position'])
                        assert not canal_layout.blocked(*g.canal_runtime['companion'].position)
                        pygame.event.pump();g.draw();g.clock.tick(60);frames+=1
                    else:raise AssertionError(f'Route stopped before {target}: {current["position"]}')
                g.handle_key(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE,mod=0,unicode=''))
                before=deepcopy(current);day=deepcopy(g.village.daily_life)
                g.draw();pixels=pygame.image.tobytes(g.screen,'RGB')
                for _ in range(60):
                    pygame.event.pump();g.update(1/60);g.draw();g.clock.tick(60)
                    assert current==before and g.village.daily_life==day
                    assert pygame.image.tobytes(g.screen,'RGB')==pixels
                pygame.image.save(g.screen,output/'native-paused.png')
                g.handle_key(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE,mod=0,unicode=''))
                canal_settlement.update(g,0.)
                g.reduced_motion=True;g.draw();pixels=pygame.image.tobytes(g.screen,'RGB')
                # Decoration itself holds; daylight remains authoritative.
                canal_settlement.update(g,.1);g.draw()
                assert pygame.image.tobytes(g.screen,'RGB')==pixels
                g.save_game();position=list(current['position']);g.start_slot(1)
                assert g.scene=='canal' and canal_progress.state(g.village)['position']==position
                (output/'native-check.json').write_text(json.dumps(dict(movement_frames=frames,
                    pause_frames=60,route='arrival towpath bridge market',companion_collision=True,
                    reduced_motion=True,save_reload=True),indent=2),encoding='utf-8')
            items=[p.name for p in output.glob('*.png') if p.name!='overview-native.png']
            html='<meta charset="utf-8"><title>Reedhaven review</title><style>body{background:#233b39;color:#eee4c9;font:16px sans-serif}img{max-width:100%;image-rendering:pixelated}figure{margin:28px 0}</style><h1>Reedhaven — disposable review</h1>'
            html+=''.join(f'<figure><figcaption>{name}</figcaption><img src="{name}"></figure>' for name in items)
            (output/'review.html').write_text(html,encoding='utf-8')
            pygame.quit()
    print(output)


if __name__=='__main__':main()
