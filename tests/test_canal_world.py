"""Reachable landing/town routes, matching water boundaries and safe rendering."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
from collections import deque,defaultdict
from copy import deepcopy
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import pygame
from economy import Village
from town import Town
import canal_layout as layout
import canal_progress
import canal_settlement
import canal_art
import ui_theme


class CanalWorldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_all_residents_and_interactions_reachable_from_arrival(self):
        # Search actual walkable space, not the decorative path graph.
        step=20;start=(round(layout.ARRIVAL[0]/step),round(layout.ARRIVAL[1]/step))
        todo=deque([start]);seen={start};targets=set(layout.POINTS)
        while todo and targets:
            cell=todo.popleft();point=(cell[0]*step,cell[1]*step)
            for key in tuple(targets):
                if ((point[0]-layout.POINTS[key][0])**2+(point[1]-layout.POINTS[key][1])**2)<45**2:targets.remove(key)
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                next_cell=(cell[0]+dx,cell[1]+dy)
                if next_cell in seen:continue
                xx,yy=next_cell[0]*step,next_cell[1]*step
                if layout.blocked(xx,yy) or layout.blocked((xx+point[0])/2,(yy+point[1])/2):continue
                seen.add(next_cell);todo.append(next_cell)
        self.assertFalse(targets,f'Unreachable interactions: {targets}')

    def test_bank_collision_and_crossing_exceptions_share_contour(self):
        for x,y in ((600,420),(1280,450),(2070,960),(2600,940)):
            self.assertTrue(layout.wet(x,y))
            self.assertTrue(layout.blocked(x,y-layout.FOOT_OFFSET))
        for x,y in ((860,420),(2370,550)):
            self.assertTrue(layout.wet(x,y))
            self.assertFalse(layout.blocked(x,y-layout.FOOT_OFFSET))
        for name,point in layout.POINTS.items():self.assertFalse(layout.blocked(*point),name)
        for key in layout.BUILDINGS:
            rect=layout.building_rect(key)
            self.assertTrue(layout.blocked(rect.centerx,rect.centery-layout.FOOT_OFFSET))
        self.assertTrue(layout.blocked(1060,850-layout.FOOT_OFFSET))
        self.assertFalse(layout.blocked(*layout.POINTS['Sela']))

    def test_invalid_saved_positions_recover_to_landing(self):
        for point in ((float('nan'),100),('bad',None),(-200,-300),(2600,900),None):
            self.assertEqual(layout.safe_position(point),list(layout.ARRIVAL))
        self.assertEqual(layout.safe_position((1080,1020)),[1080.,1020.])

    def test_scene_movement_cannot_cross_water_and_pause_modal_is_exact(self):
        village=Village();current=canal_progress.state(village)
        current['position']=[1500.,660.]
        g=SimpleNamespace(village=village,canal_runtime=None)
        keys=defaultdict(bool,{pygame.K_w:True})
        with patch('pygame.key.get_pressed',return_value=keys):
            for _ in range(90):canal_settlement.update(g,1.)
        self.assertFalse(layout.blocked(*current['position']))
        self.assertGreater(current['position'][1],570)
        self.assertFalse(layout.blocked(*g.canal_runtime['companion'].position))
        g.canal_runtime['modal']='Ivo';before=deepcopy(current)
        with patch('pygame.key.get_pressed',return_value=keys):canal_settlement.update(g,12.)
        self.assertEqual(current,before)

    def test_art_and_collision_preserve_lake_and_do_not_mutate_save(self):
        ground,props,lights=canal_art.build_scene()
        self.assertEqual(ground.get_size(),(layout.WIDTH,layout.HEIGHT))
        self.assertGreater(len(props),65)
        self.assertEqual(len(lights),len(layout.BUILDINGS))
        for x,y in ((600,420),(1280,450),(2070,960),(2600,940)):
            color=ground.get_at((x,y))
            self.assertGreater(color.b,color.r)
        # Opposite banks are connected by the one visible crossing.
        self.assertFalse(layout.blocked(860,420))
        self.assertGreater(ground.get_at((860,420)).r,ground.get_at((860,420)).b)

    def test_entire_paving_texture_is_clipped_at_edges_and_junctions(self):
        coverage,shoulder,paving=canal_art.road_layers()
        road=pygame.mask.from_surface(coverage);paint=pygame.mask.from_surface(paving)
        self.assertEqual(road.count(),paint.count())
        self.assertEqual(paint.overlap_area(road,(0,0)),paint.count())
        # All authored street joints and rounded branch tips contain paving,
        # with no separate border line cutting across a shared connection.
        for point in ((860,210),(850,660),(850,950),(1100,950),(980,1350),
                      (2390,410),(1680,1100),(230,685)):
            x,y=point
            for dx,dy in ((0,0),(-9,0),(9,0),(0,-9),(0,9)):
                self.assertEqual(paving.get_at((x+dx,y+dy)).a,255,point)
        # The distant lawn and water do not acquire fragments from any brick.
        for point in ((2220,1500),(690,820),(1800,1450)):
            self.assertEqual(paving.get_at(point).a,0)

    def test_night_glazing_preserves_frames_shutters_and_market_awning(self):
        _,props,lights=canal_art.build_scene()
        for index,(key,((x,y),width,_,_)) in enumerate(layout.BUILDINGS.items()):
            building=props[index];light=lights[index]
            left=x-width//2
            count=0
            for wx in (left+25,left+width-60):
                for xx in range(wx,wx+34):
                    for yy in range(y-105,y-67):
                        local=(xx-building.rect.x,yy-building.rect.y)
                        original=building.image.get_at(local)
                        glowing=light.image.get_at(local).a>0
                        self.assertEqual(glowing,tuple(original)[:3] in canal_art.GLASS_LIGHTS,(key,local))
                        count+=int(glowing)
            self.assertGreater(count,100,key)

    def test_every_dialogue_fits_without_clipping_or_hidden_lines(self):
        g=SimpleNamespace(village=Village(),town=Town(),screen=pygame.Surface((1280,760)),
                          font=ui_theme.make_font(18),heading=ui_theme.make_font(24),
                          small=ui_theme.make_font(16),tiny=ui_theme.make_font(14),buttons=[],canal_runtime=None)
        g.button=lambda *args,**kwargs:None
        rt=canal_settlement._runtime(g);current=canal_progress.state(g.village)
        draw_text=ui_theme.wrapped_text
        for complete in (False,True):
            current.update(request_complete=complete,clue_found=complete)
            for key in ('arrival','boat','cistern','waterworks',*layout.RESIDENTS):
                rt['modal']=key
                def check(*args,**kwargs):
                    kwargs['max_lines']=None
                    bottom=draw_text(*args,**kwargs)
                    self.assertLessEqual(bottom,628,(key,complete))
                    return bottom
                with patch('ui_theme.wrapped_text',side_effect=check):canal_settlement._dialogue(g)


if __name__=='__main__':unittest.main()
