"""Repeatable gameplay-scale town review using disposable saves only."""
import argparse
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

VIEWS=(('center',(850,690)),('west-mill-farm',(350,900)),
       ('artisan-street',(2110,690)),('river-west',(700,1360)),
       ('river-east',(2100,1360)),('north-shops',(975,350)),
       ('north-east',(2130,350)),('bridge-approach',(1120,1360)),
       ('fuel-yard',(500,350)))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='testing-screenshots/copperside-environment-review/after')
    parser.add_argument('--smoke',action='store_true')
    args=parser.parse_args()
    if not args.smoke:os.environ.setdefault('SDL_VIDEODRIVER','dummy')
    import pygame
    import scene_depth
    from game import Game
    from migration import HOMES,housing_state
    from town import LOCATIONS
    output=ROOT/args.output;output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as folder:
        root=Path(folder)
        with patch('game.SAVES_DIR',root/'saves'),patch('game.SAVE_FILE',root/'old.json'),patch('game.DESIGNS_FILE',root/'designs.json'):
            g=Game();g.start_slot(1)
            def capture(name,point):
                g.town.player_x,g.town.player_y=point
                g.town.companion.reset(point);g.draw()
                pygame.image.save(g.screen,str(output/(name+'.png')))
                if name=='center':
                    # Native-scale detail of the actual gameplay frame.
                    pygame.image.save(g.screen.subsurface((375,65,340,275)),str(output/'workshop-detail.png'))
                if name=='river-west':
                    pygame.image.save(g.screen.subsurface((490,270,560,260)),str(output/'cottage-roofs.png'))
            for name,point in VIEWS:capture(name,point)
            overview=g.town.background.copy()
            scene_depth.draw(overview,(0,0),g.town.scenery_props)
            pygame.image.save(overview,str(output/'overview-native.png'))
            pygame.image.save(pygame.transform.scale(overview,(1350,780)),str(output/'overview.png'))
            # Render all future cottages and the commercial building without
            # changing their production, population or construction mechanics.
            for home in HOMES:housing_state(g.village,home,True).update(cottage_built=True,housing_stage='vacant')
            g.village.businesses['east_bakery']={'name':"Jun's Bakery"}
            capture('developed-east',(2130,1360))
            capture('developed-north',(2130,350))
            # Native-sized architecture sheet also covers every future roof.
            sheet=pygame.Surface((1280,1350));sheet.fill((119,149,104))
            for index,key in enumerate(LOCATIONS):
                x=160+index%4*320;y=250+index//4*270
                g.town._building(sheet,(x,y),key,g.heading,g.small)
                label=g.small.render(key.replace('_',' ').title(),True,(239,228,190))
                sheet.blit(label,label.get_rect(center=(x,y+9)))
            pygame.image.save(sheet,str(output/'all-buildings.png'))
            if args.smoke:
                # Native presentation + movement with no economy fixture steps.
                from collections import defaultdict
                g.town.player_x,g.town.player_y=(650,690)
                g.town.companion.reset((650,690))
                start=pygame.time.get_ticks()
                while pygame.time.get_ticks()-start<6000:
                    for event in pygame.event.get():
                        if event.type==pygame.QUIT:break
                    dt=g.clock.tick(60)/1000
                    elapsed=(pygame.time.get_ticks()-start)/1000
                    keys=defaultdict(bool,{pygame.K_d:elapsed<3,pygame.K_a:elapsed>=3})
                    g.town.move(keys,dt);g.town.update_visuals(dt);g.draw()
                pygame.image.save(g.screen,str(output/'native-window.png'))
            pygame.quit()
    print(output)


if __name__=='__main__':main()
