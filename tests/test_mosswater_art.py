"""Rendered road continuity, foliage clearance and live trap feedback."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pygame
import adventure
import adventure_art as art
import mosswater
import scenery
from game import Game


class MosswaterArtTests(unittest.TestCase):
    def test_every_tree_including_border_trees_clears_roads_and_water(self):
        seen=[];original=scenery.tree
        def capture(surface,x,y,kind):
            seen.append((x,y));original(surface,x,y,kind)
        with patch('scenery.tree',side_effect=capture):art.build_scene()
        self.assertGreater(len(seen),100)  # Preserve the woodland, not just remove it.
        # Mosswater should have real groves inside each playable region.
        for bounds,minimum in (((130,1900,280,820),50),
                               ((1930,3110,250,1730),40),
                               ((3300,4100,250,1710),75)):
            left,right,top,bottom=bounds
            self.assertGreaterEqual(sum(left<x<right and top<y<bottom for x,y in seen),minimum,bounds)
        # The visible backdrop must continue beyond the actual collision edge.
        for bounds,minimum in (((70,1850,900,1250),100),
                               ((70,1850,0,230),60),
                               ((1950,4100,0,180),45),
                               ((1950,4100,1750,1850),30)):
            left,right,top,bottom=bounds
            forest=[(x,y) for x,y in seen if left<x<right and top<y<bottom]
            self.assertGreaterEqual(len(forest),minimum,bounds)
            self.assertTrue(all(mosswater.blocked(x,y) for x,y in forest),bounds)
        ground=pygame.Surface((art.WIDTH,art.HEIGHT),pygame.SRCALPHA)
        art.draw_roads(ground)
        for polygon in art.mosswater.WATER_POLYGONS:
            pygame.draw.polygon(ground,'white',polygon)
        protected=pygame.mask.from_surface(ground)
        for x,y in seen:
            sprite=pygame.Surface((104,134),pygame.SRCALPHA)
            # Conservative entire crown/shadow bounds, including transparent margin.
            sprite.fill('white')
            self.assertIsNone(protected.overlap(pygame.mask.from_surface(sprite),(x-50,y-108)),(x,y))

    def test_forks_have_continuous_inner_surface_and_round_caps(self):
        surface=pygame.Surface((art.WIDTH,art.HEIGHT));surface.fill('black');art.draw_roads(surface)
        inner=art.ROAD_LAYERS[-1][1]
        for x,y in ((1875,600),(1730,420),(2060,940),(2760,1120),(2960,1230)):
            for dx,dy in ((0,0),(-8,0),(8,0),(0,-8),(0,8)):
                self.assertEqual(surface.get_at((x+dx,y+dy))[:3],inner,(x,y,dx,dy))
        self.assertEqual(surface.get_at((40,690))[:3],inner)
        self.assertEqual(surface.get_at((60,646))[:3],art.ROAD_LAYERS[0][1])

    def test_cached_ground_keeps_vegetation_off_the_new_road_centers(self):
        ground,_=art.build_scene()
        inner=art.ROAD_LAYERS[-1][1]
        for route in art.ROAD_ROUTES[1:]:
            for x,y in route:
                if 3130<x<3290:continue  # The timber bridge replaces the dirt.
                self.assertEqual(ground.get_at((x,y))[:3],inner,(x,y))

    def test_both_traps_animate_only_while_armed_and_repeat_when_time_is_frozen(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with patch('game.SAVES_DIR',root/'saves'),patch('game.SAVE_FILE',root/'save.json'),patch('game.DESIGNS_FILE',root/'designs.json'):
                g=Game();g.start_slot(1);adventure.enter(g);s=adventure.state(g.village)
                g.adventure_speech_time=0
                try:
                    for key,position in (('interlock',(1080,560)),('range_gate',(3050,1300))):
                        s['position']=list(position);g.adventure_companion.reset(position)
                        def frame(seconds):
                            g.adventure_time=seconds;g.buttons=[];adventure.draw(g)
                            return pygame.image.tobytes(g.screen,'RGB')
                        s[key]=False
                        active=frame(0.)
                        self.assertNotEqual(active,frame(.45),key)
                        self.assertEqual(frame(.45),frame(.45),key)
                        s[key]=True
                        self.assertEqual(frame(0.),frame(.45),key)
                        self.assertNotEqual(active,frame(0.),key)
                finally:pygame.quit()
