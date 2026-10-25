"""Render the expanded expedition using disposable saves."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
import tempfile
from unittest.mock import patch
import pygame
from game import Game
from test_adventure import design
from test_mosswater import complete_survey
import adventure
import mosswater
import scene_depth


def main():
    output=ROOT/'testing-screenshots'/'mosswater-expansion';output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as directory:
        root=Path(directory)
        with patch('game.SAVES_DIR',root/'saves'),patch('game.SAVE_FILE',root/'save.json'),patch('game.DESIGNS_FILE',root/'designs.json'):
            g=Game();g.start_slot(1);adventure.enter(g)
            s=adventure.state(g.village);s.update(receiver=True,decoder=True,interlock=True)
            s['designs']['decoder']=design('decoder').snapshot()
            def capture(name,position,silence=True):
                s['position']=list(position);g.adventure_companion.reset(position)
                if silence:g.adventure_speech_time=0
                g.draw()
                pygame.image.save(g.screen,str(output/(name+'.png')))
            for key,position in (('interlock',(1080,560)),('range_gate',(3050,1300))):
                s[key]=False
                for i,seconds in enumerate((0.,.45)):
                    g.adventure_time=seconds;capture(key+'-active-'+str(i),position)
                s[key]=True;capture(key+'-safe',position)
            s['range_gate']=False
            capture('western-outside-forest',(800,810))
            capture('northern-outside-forest',(2550,185))
            s['position']=list(mosswater.POINTS['survey']);adventure.interact(g)
            capture('survey-instructions',(1730,420))
            adventure.close_notice(g)
            capture('survey-reaction',(1730,420),silence=False)
            capture('woodland',(2280,490))
            s['frequency']=1;capture('fern-pond',(2720,1050))
            s['frequency']=2;capture('reed-marsh',(2800,1500))
            s.update(survey_found=['crown','fern','reed'],position=list(mosswater.POINTS['range_lock']))
            adventure.interact(g);capture('range-instructions',(3050,1260));adventure.close_notice(g)
            capture('range-lock',(2980,1230))
            complete_survey(g);g.adventure_modal=None
            capture('archive',(3650,1450))
            s['position']=list(mosswater.POINTS['artifact']);adventure.interact(g)
            capture('reward',mosswater.POINTS['artifact'])
            adventure.close_notice(g)
            capture('reward-reaction',mosswater.POINTS['artifact'],silence=False)
            overview=g.adventure_background.copy();scene_depth.draw(overview,(0,0),g.adventure_props)
            pygame.image.save(pygame.transform.smoothscale(overview,(1680,740)),str(output/'overview.png'))
            pygame.quit()
    print(output)


if __name__=='__main__':main()
