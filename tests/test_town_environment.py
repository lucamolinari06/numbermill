"""Road reshaping preserves movement, future plots and scenery clearance."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
from collections import defaultdict
import unittest

import pygame
from town import Town, LOCATIONS, WORLD_W, WORLD_H, decoration_layout, decoration_bounds
import town_ground


class EnvironmentRouteTests(unittest.TestCase):
    def test_every_resident_trip_remains_on_road_and_outside_buildings(self):
        mask=town_ground.road_mask((WORLD_W,WORLD_H))
        for origin in LOCATIONS.values():
            for target in LOCATIONS.values():
                town=Town();point=list(map(float,origin))
                for _ in range(900):
                    town._travel('review',point,target,17)
                    self.assertFalse(town._inside_building(*point),(origin,target,point))
                    # Include the visible feet, not just the actor origin.
                    self.assertTrue(mask.get_at((round(point[0]),round(point[1]+18))),
                                    (origin,target,point))
                    if not town.routes['review']:break
                self.assertLess(pygame.Vector2(point).distance_to(target),3)

    def test_road_is_connected_and_doors_have_visible_waiting_space(self):
        mask=town_ground.road_mask((WORLD_W,WORLD_H))
        self.assertEqual(len(mask.connected_components()),1)
        for key,(x,y) in LOCATIONS.items():
            for dx in (-30,0,30):
                for dy in (18,38):
                    self.assertTrue(mask.get_at((x+dx,y+dy)),(key,dx,dy))

    def test_full_scenery_bounds_clear_paving_and_future_buildings(self):
        future=('home_4','home_5','home_6','east_bakery')
        for kind,x,y,_ in decoration_layout():
            bounds=decoration_bounds(kind,x,y)
            self.assertTrue(town_ground.clears_road(bounds),(kind,x,y))
            if kind != 'well':
                self.assertTrue(town_ground.clears_garden(bounds),(kind,x,y))
            for key in future:
                bx,by=LOCATIONS[key];width=200 if key.startswith('home_') else 275
                self.assertFalse(bounds.colliderect(pygame.Rect(bx-width//2,by-231,width,225)),
                                 (key,kind,x,y))

    def test_garden_paths_join_streets_and_keep_furniture(self):
        mask=town_ground.garden_mask((WORLD_W,WORLD_H))
        roads=town_ground.road_mask((WORLD_W,WORLD_H))
        for x,y in ((880,731),(575,972),(1120,903),(900,975)):
            self.assertTrue(mask.get_at((x,y)))
            self.assertTrue(roads.get_at((x,y)),(x,y))
        self.assertEqual(len(mask.connected_components()),1)
        layout=decoration_layout()
        self.assertIn(('bench',730,815,''),layout)
        self.assertIn(('planter',730,870,''),layout)

    def test_player_walks_junctions_garden_and_bridge_with_companion(self):
        town=Town()
        for start,keys,steps in (((700,690),{pygame.K_d:True},180),
                                 ((1120,350),{pygame.K_s:True},330),
                                 ((880,745),{pygame.K_s:True},45),
                                 ((1120,1390),{pygame.K_s:True},30)):
            town.player_x,town.player_y=start;town.companion.reset(start)
            for _ in range(steps):
                town.move(defaultdict(bool,keys),1/60)
                self.assertFalse(town._inside_building(town.player_x,town.player_y))
                self.assertFalse(town._companion_blocked(*town.companion.position))
            self.assertGreater(pygame.Vector2(start).distance_to((town.player_x,town.player_y)),100)


if __name__=='__main__':unittest.main()
