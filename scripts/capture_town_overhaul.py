"""Disposable Copperside visual review; no personal saves are read or written."""
import argparse
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
    import scene_depth
    from game import Game
    from town import WORLD_W, WORLD_H, LOCATIONS
    output = ROOT/'testing-screenshots'/'town-overhaul'
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as folder:
        root = Path(folder)
        with patch('game.SAVES_DIR',root/'saves'), patch('game.SAVE_FILE',root/'old.json'), patch('game.DESIGNS_FILE',root/'designs.json'):
            g=Game();g.start_slot(1)
            for _ in range(80):g.update(.5)
            for name, point in (('workshop',(755,690)),('mill',(300,650)),
                                ('garden-market',(1010,900)),('artisan-street',(2110,690)),
                                ('river-cottages',(800,1360)),('north-workshops',(1110,350))):
                g.town.player_x,g.town.player_y=point
                g.town.companion.reset(point)
                g.draw()
                pygame.image.save(g.screen,str(output/(name+'.png')))
            overview=g.town.background.copy()
            scene_depth.draw(overview,(0,0),g.town.scenery_props)
            pygame.image.save(pygame.transform.scale(overview,(1350,780)),str(output/'overview.png'))
            sheet=pygame.Surface((1000,350));sheet.fill((237,224,188))
            colors={'Boole':(61,121,115),'Luca':(65,115,130),'Mely':(170,95,63),
                    'Grace':(122,94,138),'Ada':(141,91,76),'Bram':(96,119,87),
                    'Agnes':(156,127,68),'Dara':(91,115,148)}
            for index,(name,coat) in enumerate(colors.items()):
                x=62+index*125
                for row,facing in enumerate(('south','north')):
                    sprite=pygame.Surface((60,85),pygame.SRCALPHA)
                    g.town._villager(sprite,30,50,coat,facing=facing,name=name)
                    sheet.blit(pygame.transform.scale(sprite,(90,128)),(x-45,25+row*155))
                label=g.small.render(name,True,(43,61,52))
                sheet.blit(label,label.get_rect(center=(x,332)))
            pygame.image.save(sheet,str(output/'residents.png'))
            buildings=pygame.Surface((1280,1350));buildings.fill((119,149,104))
            for index,key in enumerate(LOCATIONS):
                x=160+index%4*320;y=250+index//4*270
                g.town._building(buildings,(x,y),key,g.heading,g.small)
                label=g.small.render(key.replace('_',' ').title(),True,(239,228,190))
                buildings.blit(label,label.get_rect(center=(x,y+9)))
            pygame.image.save(buildings,str(output/'all-buildings.png'))
            if args.smoke:
                g.town.player_x,g.town.player_y=(755,690)
                g.town.companion.reset((755,690))
                start=pygame.time.get_ticks()
                while g.running and pygame.time.get_ticks()-start < 4500:
                    for event in pygame.event.get():g.handle_event(event)
                    g.update(g.clock.tick(60)/1000);g.draw()
                pygame.image.save(g.screen,str(output/'live-window.png'))
            pygame.quit()
    print(output)


if __name__=='__main__':
    main()
