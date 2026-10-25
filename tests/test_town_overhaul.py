"""World-art envelope, animation-state and rendering purity regressions."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
from copy import deepcopy
import unittest
import pygame
from economy import Village
from town import Town, LOCATIONS
import town_art
import town_water
from town import WORLD_W,WORLD_H
from collections import defaultdict


class TownOverhaulTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.fonts=tuple(pygame.font.SysFont('consolas',size) for size in (14,18,24,32))

    def test_each_architecture_fits_existing_cache_and_leaves_door_approach_clear(self):
        surface=pygame.Surface((600,450),pygame.SRCALPHA)
        town=Town()
        for key in LOCATIONS:
            surface.fill((0,0,0,0))
            town._building(surface,(300,350),key,self.fonts[2],self.fonts[0])
            with self.subTest(building=key):
                self.assertTrue(pygame.Rect(140,110,320,250).contains(surface.get_bounding_rect()))
                # Roof changes must not paint over the player's doorway approach.
                self.assertEqual(surface.get_at((300,344)).a,0)
                self.assertFalse(Town._inside_building(*LOCATIONS[key]))

    def test_river_animation_is_repeatable_reduced_motion_and_rendering_is_read_only(self):
        village=Village();town=Town()
        town.player_x,town.player_y=800.,1400.
        town.companion.reset((800.,1400.))
        surface=pygame.Surface((1280,760))
        town.draw(surface,self.fonts,village,None,'')
        before=deepcopy(vars(village))
        def frame(seconds):
            town.visual_time=seconds
            town.draw(surface,self.fonts,village,None,'')
            return pygame.image.tobytes(surface,'RGB')
        first=frame(0.)
        self.assertNotEqual(first,frame(1.7))
        self.assertEqual(frame(1.7),frame(1.7))
        town.reduced_motion=True
        self.assertEqual(frame(0.),frame(1.7))
        self.assertEqual(vars(village),before)

    def test_mill_animation_depends_on_working_state(self):
        surface=pygame.Surface((600,450))
        def frame(seconds,working):
            surface.fill((15,25,20))
            town_art.building_effects(surface,(0,0),'mill',(300,350),seconds,working)
            return pygame.image.tobytes(surface,'RGB')
        self.assertEqual(frame(0.,False),frame(1.7,False))
        self.assertNotEqual(frame(0.,True),frame(1.7,True))

    def test_visual_clock_only_advances_on_updates_and_clamps_long_frames(self):
        town=Town()
        self.assertEqual(town.visual_time,0.)
        town.update_visuals(.1)
        self.assertAlmostEqual(town.visual_time,.1)
        town.update_visuals(-10)
        self.assertAlmostEqual(town.visual_time,.1)
        town.update_visuals(120)
        self.assertAlmostEqual(town.visual_time,1.1)

    def test_natural_river_water_and_collision_share_the_curving_bank(self):
        surface=pygame.Surface((WORLD_W,WORLD_H));surface.fill((1,2,3))
        town_water.draw(surface,WORLD_W,WORLD_H)
        heights=[]
        for x in (100,300,500,700,900,1350,1600,1900,2200,2500):
            bank=town_water.north_bank(x,WORLD_W,WORLD_H);heights.append(bank)
            with self.subTest(x=x):
                self.assertFalse(town_water.blocked(x,bank-3,WORLD_W,WORLD_H))
                self.assertTrue(town_water.blocked(x,bank+3,WORLD_W,WORLD_H))
                self.assertEqual(surface.get_at((x,round(bank+9)))[:3],(62,116,128))
                self.assertFalse(Town._inside_building(x,bank-22))
                self.assertTrue(Town._inside_building(x,bank-15))
        self.assertGreater(max(heights)-min(heights),15)

    def test_bridge_is_crossable_and_long_frames_cannot_skip_the_river(self):
        town=Town();town.player_x,town.player_y=500.,1400.
        town.companion.reset((500.,1400.))
        town.move(defaultdict(bool,{pygame.K_s:True}),2.)
        self.assertFalse(town_water.blocked(town.player_x,town.player_y+18,WORLD_W,WORLD_H))
        self.assertLess(town.player_y,1460)
        town.player_x,town.player_y=1120.,1400.;town.companion.reset((1120.,1400.))
        town.move(defaultdict(bool,{pygame.K_s:True}),2.)
        self.assertAlmostEqual(town.player_y,WORLD_H-45)
        town.move(defaultdict(bool,{pygame.K_a:True}),1.)
        self.assertGreaterEqual(town.player_x,1060)
        self.assertFalse(town._companion_blocked(*town.companion.position))

    def test_legacy_river_position_moves_to_nearby_dry_bank_and_bridge_is_retained(self):
        original=(500.,1500.)
        safe=Town.safe_position(original)
        self.assertEqual(safe[0],original[0])
        self.assertLess(abs(safe[1]-original[1]),100)
        self.assertFalse(Town._inside_building(*safe))
        for point in ((1120.,1500.),(755.,690.),(2075.,1225.)):
            self.assertEqual(Town.safe_position(point),point)


if __name__=='__main__':unittest.main()
