"""Disposable character sheets, animated review and a real-window walking smoke check."""
import argparse
from collections import defaultdict
import math
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--smoke',action='store_true')
    args=parser.parse_args()
    if not args.smoke:
        os.environ.setdefault('SDL_VIDEODRIVER','dummy')
    import pygame
    from PIL import Image
    from game import Game
    from town import LOCATIONS
    from resident_performance import coat_for, performances
    from town_companion import Companion
    output=ROOT/'testing-screenshots'/'resident-performance'
    output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as folder:
        root=Path(folder)
        with patch('game.SAVES_DIR',root/'saves'),patch('game.SAVE_FILE',root/'old.json'),patch('game.DESIGNS_FILE',root/'designs.json'):
            g=Game();g.start_slot(1)
            g.opening_screen=None
            # Render directly through Town so optional opening narration cannot hide the review.
            def draw_town():
                g.town.draw(g.screen,(g.small,g.font,g.heading,g.big),g.village,None,'')
            names=('Boole','Luca','Mely','Grace','Ada','Bram','Agnes','Dara','Rowan','Saffron','Felix','Wren','Hugo','Alma','Perry','Cleo','Jun')
            sheet=pygame.Surface((1280,730));sheet.fill((239,227,194))
            for index,name in enumerate(names):
                col,row=index%9,index//9
                x,y=col*140+65,row*360+34
                label=g.small.render(name,True,(39,51,49))
                sheet.blit(label,label.get_rect(center=(x,y)))
                for face_index,facing in enumerate(('south','north','east','west')):
                    g.town._villager(sheet,x,y+55+face_index*73,coat_for(name),name=name,facing=facing)
            pygame.image.save(sheet,output/'all-facings.png')
            cast=(('Ada','tend'),('Bram','repair'),('Agnes','inspect'),('Dara','sweep'),
                  ('Mely','sit_chat'),('Luca','sit_chat'),('Grace','inspect'),('Rowan','basket'))
            animation=[]
            for frame in range(48):
                seconds=frame/12
                sheet=pygame.Surface((1000,420));sheet.fill((239,227,194))
                for index,(name,action) in enumerate(cast):
                    x=62+125*index
                    label=g.small.render(name,True,(39,51,49))
                    sheet.blit(label,label.get_rect(center=(x,22)))
                    for row,facing in enumerate(('south','east','west','north')):
                        g.town._villager(sheet,x,85+row*86,coat_for(name),name=name,
                                        action=action,facing=facing,seconds=seconds)
                    label=g.tiny.render(action.replace('_',' '),True,(76,95,85))
                    sheet.blit(label,label.get_rect(center=(x,408)))
                if frame==12:
                    pygame.image.save(sheet,output/'destination-poses.png')
                animation.append(Image.frombytes('RGB',sheet.get_size(),pygame.image.tobytes(sheet,'RGB')))
            animation[0].save(output/'destination-motion.gif',save_all=True,append_images=animation[1:],duration=83,loop=0)

            sheet=pygame.Surface((1000,380));sheet.fill((239,227,194))
            for index,facing in enumerate(('south','north','east','west')):
                for row,name in enumerate(('Boole','Grace','Shannon')):
                    for step,phase in enumerate((0.,math.pi/2,math.pi,3*math.pi/2)):
                        x,y=35+index*250+step*58,85+row*113
                        if name=='Shannon':
                            follower=Companion((400,400),lambda x,y:False,facing)
                            follower.phase=phase;follower.moving=True
                            follower.draw(sheet,x,y)
                        else:
                            g.town._villager(sheet,x,y,coat_for(name),phase,True,facing,name)
                sheet.blit(g.small.render(facing,True,(39,51,49)),(index*250+80,12))
            pygame.image.save(sheet,output/'walking-poses.png')

            # Exercise the real activity selector with actual reserved destination slots.
            for p in g.village.citizens:
                p.update(activity='working',destination=p['workplace'])
            g.town.update_people(g.village,0)
            for name,target in g.town.route_targets.items():
                g.town.people[name]=list(target)
                g.town.display_people[name]=list(target)
            g.town.display_moving.clear()
            g.town.visual_time=1.5
            for label,point in (('market-work',(1000,865)),('north-work',(1110,350)),('mill-work',(300,650))):
                g.town.player_x,g.town.player_y=point;g.town.companion.reset(point)
                draw_town();pygame.image.save(g.screen,output/(label+'.png'))
            pair=[p for p in g.village.citizens if p['name'] in ('Mely','Luca')]
            for p in pair:p.update(activity='spending time with spouse',destination=p['home'])
            g.town.update_people(g.village,0)
            for p in pair:
                name=p['name'];point=g.town.route_targets[name]
                g.town.people[name]=list(point);g.town.display_people[name]=list(point)
            home=LOCATIONS[pair[0]['home']]
            g.town.player_x,g.town.player_y=home[0],home[1]+120
            g.town.companion.reset((g.town.player_x,g.town.player_y))
            assert all(performances(g.town,g.village)[p['name']].action=='sit_chat' for p in pair)
            draw_town();pygame.image.save(g.screen,output/'home-company.png')

            if args.smoke:
                g.town.player_x,g.town.player_y=(755,690)
                g.town.companion.reset((755,690))
                start=(g.town.player_x,g.town.player_y)
                for frame in range(180):
                    pygame.event.pump()
                    keys=defaultdict(bool,{pygame.K_d:frame<70,pygame.K_a:90<=frame<160})
                    g.town.move(keys,1/60)
                    g.town.update_visuals(1/60)
                    draw_town();g.viewport.present()
                    assert not g.town._companion_blocked(*g.town.companion.position)
                    g.clock.tick(60)
                assert math.dist(start,(g.town.player_x,g.town.player_y))<1
                pygame.image.save(g.screen,output/'native-window.png')
                (output/'smoke.log').write_text('180 native-window frames; walking, return and Shannon collision checks passed.\n',encoding='utf-8')
            pygame.quit()
    (output/'review.html').write_text('''<!doctype html><meta charset="utf-8"><title>Copperside character review</title>
<style>body{background:#233b35;color:#f1e4c2;font:18px system-ui;margin:24px}img{display:block;image-rendering:pixelated;max-width:none;margin:16px 0}button{font:inherit;padding:6px 14px} .detail{zoom:2}</style>
<h1>Copperside characters</h1><p>Native pixels. The motion sheet shows four facings of the destination performances. These are staged developer captures; gameplay chooses actions from resident routines.</p>
<button onclick="document.querySelector('#motion').src='destination-motion.gif'">Play motion</button>
<button onclick="document.querySelector('#motion').src='destination-poses.png'">Still frame</button>
<img id="motion" src="destination-motion.gif"><h2>Walking: Boole, Grace, Shannon</h2><img src="walking-poses.png">
<h2>All residents, all facings</h2><img src="all-facings.png"><h2>In town</h2>
<img src="market-work.png"><img src="north-work.png"><img src="mill-work.png"><img src="home-company.png">''',encoding='utf-8')
    print(output)


if __name__=='__main__':
    main()
