"""Render level two and optionally open an interactive, disposable preview.

No real save is loaded or edited. --play opens at the first blank controller;
rendered walkthrough frames use test-only boards to verify every landing.
"""
import argparse
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tests')]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--play',action='store_true')
    parser.add_argument('--smoke',action='store_true',help='Show a real window for a short event-loop check.')
    args=parser.parse_args()
    if not (args.play or args.smoke):
        os.environ.setdefault('SDL_VIDEODRIVER','dummy')
    import pygame
    import adventure
    import boiler_tower as tower
    from game import Game
    output=ROOT/'testing-screenshots'/'boiler-tower'
    output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as folder:
        root=Path(folder)
        with patch('game.SAVES_DIR',root/'saves'),patch('game.SAVE_FILE',root/'old.json'),patch('game.DESIGNS_FILE',root/'designs.json'):
            g=Game();g.start_slot(1)
            adventure.state(g.village)['expansion_complete']=True
            tower.enter(g)
            if args.play:
                g.run()
                return
            if args.smoke:
                adventure.close_notice(g);g.adventure_speech_time=0
                tower.state(g.village).update(position=tower.landing_position(1),hazard_time=2.4)
                tower.reset_motion(g);tower.reset_rail(g)
                started=pygame.time.get_ticks()
                captured=False
                while pygame.time.get_ticks()-started < 4000:
                    for event in pygame.event.get():g.handle_event(event)
                    g.update(g.clock.tick(60)/1000);g.draw()
                    if not captured and pygame.time.get_ticks()-started > 1800:
                        pygame.image.save(g.screen,str(output/'live-hazard.png'));captured=True
                pygame.image.save(g.screen,str(output/'live-window.png'))
                pygame.quit()
                return
            # Imported only after selecting dummy video, never in the live game.
            from test_boiler_tower import design,fly_to
            def capture(name):
                g.draw()
                pygame.image.save(g.screen,str(output/(name+'.png')))
            capture('arrival')
            adventure.close_notice(g);g.adventure_speech_time=0
            capture('service-dock')
            s=tower.state(g.village)
            seen_hazards=set()
            for i in range(1,len(tower.PLATFORMS)):
                if i-1 in tower.STATIONS[:-1]:
                    tower.edit(g)
                    capture('controller-'+str(s['stage']))
                    g.circuit=design(tower.editor_key(s))
                    assert adventure.validate(g)[0]
                    adventure.close_editor(g)
                    if s['stage']==2:
                        capture('exhaust-closed')
                        tower.edit(g,True)
                        g.circuit=design('tower_vent')
                        assert adventure.validate(g)[0]
                        adventure.close_editor(g)
                for hazard in tower.layout.HAZARDS:
                    if hazard['target'] != i or hazard['kind'] in seen_hazards:continue
                    seen_hazards.add(hazard['kind'])
                    old_time=s['hazard_time']
                    for phase in (1.,3.2,4.3):
                        s['hazard_time']=phase-hazard['offset']
                        capture(hazard['kind']+'-'+str(phase))
                    s['hazard_time']=old_time
                def flight_frame(frame):
                    g.tower_time += 1/120
                    if i in (2,14,26) and frame==65:
                        capture('flight-'+str(i))
                fly_to(g,i,on_frame=flight_frame)
                if i in tower.STATIONS:
                    capture('landing-'+str(i))
                    adventure.close_notice(g);g.adventure_speech_time=0
                    capture('deck-'+str(i))
            tower.interact(g);capture('reward')
            adventure.close_notice(g);g.adventure_speech_time=0
            capture('return-cage')
            pygame.image.save(pygame.transform.scale(g.tower_background,(730,2750)),str(output/'overview.png'))
            pygame.quit()
    print(output)


if __name__=='__main__':main()
