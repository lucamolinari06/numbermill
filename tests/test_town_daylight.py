"""Clock, production truth, seamless ground joins and calm/pause rendering."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pygame
from daily_life import DAY_SECONDS, state
from economy import Village
from town import Town, LOCATIONS, WORLD_W, WORLD_H, TOWN_READOUT_RECT, MINIMAP_RECT
import town_art
import town_atmosphere as atmosphere
import town_ground


class DaylightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        from ui_theme import make_font
        cls.fonts = tuple(make_font(size) for size in (16,18,24,32))

    def setUp(self):
        self.village, self.town = Village(), Town()
        self.surface = pygame.Surface((1280,760))
        state(self.village)

    def frame(self, hour=12, seconds=2.):
        state(self.village)['elapsed'] = (hour-8)/12*DAY_SECONDS
        self.town.visual_time = seconds
        self.town.draw(self.surface,self.fonts,self.village,None,'')
        return pygame.image.tobytes(self.surface,'RGB')

    def test_clock_and_light_share_actual_day_including_empty_legacy_state(self):
        for hour, expected in ((8,'08:00'),(12,'12:00'),(17,'17:00'),(20,'20:00')):
            self.frame(hour)
            self.assertEqual(self.town.clock_time(self.village),expected)
            self.assertAlmostEqual(atmosphere.clock_progress(self.village),(hour-8)/12)
        self.village.daily_life={}
        before=deepcopy(vars(self.village))
        self.town.draw(self.surface,self.fonts,self.village,None,'')
        self.assertEqual(vars(self.village),before)
        self.assertEqual(self.town.clock_time(self.village),'08:00')
        self.village.daily_life={'day':self.village.day-1,'elapsed':DAY_SECONDS}
        self.assertEqual(atmosphere.clock_progress(self.village),0.)

    def test_scene_changes_with_clock_not_wall_time_and_hud_map_keep_colors(self):
        self.frame(8)
        morning=self.surface.copy()
        self.frame(19.5)
        evening=self.surface.copy()
        self.assertNotEqual(pygame.image.tobytes(morning,'RGB'),pygame.image.tobytes(evening,'RGB'))
        # Clock text changes; the panel material, heading and map do not.
        for rect in (pygame.Rect(30,29,145,26), MINIMAP_RECT):
            self.assertEqual(pygame.image.tobytes(morning.subsurface(rect),'RGB'),
                             pygame.image.tobytes(evening.subsurface(rect),'RGB'))
        self.assertEqual(self.frame(19.5,3),self.frame(19.5,3))

    def test_evening_retains_pixel_contrast_and_lighting_changes_gradually(self):
        # No spatial blur: neighboring pixels retain their distinct channels.
        strip=pygame.Surface((2,1));strip.set_at((0,0),(40,60,80));strip.set_at((1,0),(200,180,160))
        atmosphere.apply_daylight(strip,1.)
        self.assertGreater(strip.get_at((1,0)).r-strip.get_at((0,0)).r,110)
        colors=[atmosphere.daylight(i/720) for i in range(721)]
        self.assertTrue(all(max(abs(x-y) for x,y in zip(a,b))<=1 for a,b in zip(colors,colors[1:])))

    def test_reduced_motion_holds_all_decoration_but_keeps_evening_windows(self):
        self.town.player_x,self.town.player_y=(700,1360)
        self.town.companion.reset((700,1360))
        self.town.reduced_motion=True
        evening=self.frame(19.5,0)
        self.assertEqual(evening,self.frame(19.5,33))
        self.assertNotEqual(evening,self.frame(12,33))

    def test_visible_glass_lighting_respects_mullions_shutters_and_market_awning(self):
        self.frame(19.5)
        for key in ('market','workshop','home_1'):
            bounds,light=self.town.window_lights[key]
            prop=next(prop for prop in self.town.scenery_props if prop.rect==bounds)
            glass={town_art.GLASS,(87,139,139),(175,205,186),(132,175,164)}
            lit=0
            for wx,wy,ww,wh,_,_ in town_art.facade_windows(LOCATIONS[key],key):
                for x in range(wx-bounds.x,wx-bounds.x+ww):
                    for y in range(wy-bounds.y,wy-bounds.y+wh):
                        if light.get_at((x,y)).a:
                            self.assertIn(prop.image.get_at((x,y))[:3],glass,(key,x,y))
                            lit+=1
            self.assertGreater(lit,80)

    def test_rendering_and_state_selection_leave_saves_and_cached_roofs_intact(self):
        self.frame()
        before=deepcopy(vars(self.village))
        roofs=[pygame.image.tobytes(p.image,'RGBA') for p in self.town.scenery_props]
        for hour in (8,17,20):
            state(self.village)['elapsed']=(hour-8)/12*DAY_SECONDS
            expected=deepcopy(vars(self.village))
            self.town.draw(self.surface,self.fonts,self.village,None,'')
            self.assertEqual(vars(self.village),expected)
        self.assertEqual(roofs,[pygame.image.tobytes(p.image,'RGBA') for p in self.town.scenery_props])
        self.assertEqual(self.village.citizens,before['citizens'])

    def test_leaf_lifetime_is_sparse_repeatable_and_calm_option_omits_it(self):
        layout=(('tree',100,150,''),)
        def count(seconds,reduced=False):
            image=pygame.Surface((250,250),pygame.SRCALPHA)
            atmosphere.leaves(image,(0,0),layout,seconds,reduced)
            return pygame.mask.from_surface(image).count()
        counts=[count(i*.1) for i in range(300)]
        self.assertGreater(max(counts),0)
        self.assertLessEqual(max(counts),10)
        self.assertLess(sum(bool(c) for c in counts)/len(counts),.25)
        self.assertTrue(all(count(i,True)==0 for i in range(30)))

    def test_garden_mouth_has_no_road_border_or_court_rim_across_it(self):
        surface=pygame.Surface((WORLD_W,WORLD_H));surface.fill((119,149,104))
        town_ground.soil(surface)
        point=(880,754)
        self.assertFalse(town_ground.road_mask(surface.get_size()).get_at(point))
        path_color=surface.get_at(point)[:3]
        town_ground.roads(surface)
        # Outside the road mask, the entry retains its path, no green curb line.
        self.assertEqual(surface.get_at(point)[:3],path_color)
        before=surface.copy()
        town_art.ground_details(surface)
        # A real entrance passes through the well court's outside rim.
        x,y=897,900
        self.assertTrue(town_ground.garden_mask(surface.get_size()).get_at((x,y)))
        self.assertEqual(surface.get_at((x,y)),before.get_at((x,y)))


class MachineryTruthTests(unittest.TestCase):
    def setUp(self):
        self.village,self.town=Village(),Town()
        state(self.village)['started']=True

    def place_worker(self,key):
        person=next(p for p in self.village.citizens if p['workplace']==key)
        person.update(activity='working',destination=key)
        self.town.update_people(self.village,0)
        name=person['name']
        self.town.display_people[name]=list(self.town.route_targets[name])
        return name

    def test_work_requires_arrival_and_stops_for_closure_quota_shortage_and_no_staff(self):
        name=self.place_worker('mill')
        self.assertTrue(atmosphere.working(self.town,self.village,'mill'))
        self.town.display_people[name][0]+=8
        self.assertFalse(atmosphere.working(self.town,self.village,'mill'))
        self.town.display_people[name][0]-=8
        firm=self.village.businesses['mill']
        for changes in ({'operating_state':'paused'},{'workers':0}):
            old=firm.copy();firm.update(changes)
            self.assertFalse(atmosphere.working(self.town,self.village,'mill'))
            firm.clear();firm.update(old)
        for reason in ('Waiting for grain deliveries','Boiler shutdown; a safety vent is needed','Daily capacity reached'):
            state(self.village)['reasons']['mill']=reason
            self.assertFalse(atmosphere.working(self.town,self.village,'mill'))
        state(self.village)['reasons'].clear()
        state(self.village)['produced']['mill']=self.village.capacity('mill')
        self.assertFalse(atmosphere.working(self.town,self.village,'mill'))

    def test_owner_operated_east_sites_and_player_batches_use_real_state(self):
        self.assertTrue(atmosphere.working(self.town,self.village,'foundry'))
        self.village.businesses['foundry']['stock']['metal']=8
        self.assertFalse(atmosphere.working(self.town,self.village,'foundry'))
        self.assertFalse(atmosphere.working(self.town,self.village,'workshop'))
        self.village.manufacturing['equipment']=[dict(busy=2)]
        self.assertTrue(atmosphere.working(self.town,self.village,'workshop'))
        self.village.manufacturing['equipment'][0]['busy']=0
        self.assertFalse(atmosphere.working(self.town,self.village,'workshop'))
        self.assertFalse(atmosphere.working(self.town,self.village,'grace_shop'))
        self.village.businesses['east_bakery']=dict(kind='fuel',owner_operated=True,
            workers=0,cash=100,stock={'fuel':0},machines=[],operating_state='open')
        self.assertFalse(atmosphere.working(self.town,self.village,'east_bakery'))

    def test_effects_animate_only_working_machinery_including_east_bakery(self):
        pygame.init()
        surface=pygame.Surface((600,450))
        for key in ('mill','bakery','east_bakery','foundry','sawmill','toolmaker','workshop'):
            def frame(seconds,active):
                surface.fill((15,25,20))
                town_art.building_effects(surface,(0,0),key,(300,350),seconds,active)
                return pygame.image.tobytes(surface,'RGB')
            self.assertEqual(frame(0,False),frame(2,False),key)
            self.assertNotEqual(frame(0,True),frame(2,True),key)


class GameAtmospherePauseTests(unittest.TestCase):
    def test_pause_focus_loss_settings_and_resume_hold_real_clock_and_exact_scene(self):
        from game import Game
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with patch('game.SAVES_DIR',root/'saves'),patch('game.SAVE_FILE',root/'old.json'),patch('game.DESIGNS_FILE',root/'designs.json'):
                g=Game();g.start_slot(1);g.opening_screen=None
                with patch('chapter_ui.active',return_value=False):
                    g.update(.1)
                    def scene():
                        g.town.draw(g.screen,(g.small,g.font,g.heading,g.big),g.village,None,'')
                        return pygame.image.tobytes(g.screen,'RGB')
                    for mode in ('pause','settings','focus'):
                        if mode=='settings':g.settings_open=True
                        elif mode=='focus':g.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
                        else:g.pause_menu_open=True
                        frozen=scene();before=deepcopy(vars(g.village));seconds=g.town.visual_time
                        for _ in range(4):g.update(.25)
                        self.assertEqual(vars(g.village),before)
                        self.assertEqual(g.town.visual_time,seconds)
                        self.assertEqual(scene(),frozen)
                        g.pause_menu_open=False;g.settings_open=False
                    g.update(.1)
                    self.assertGreater(g.town.visual_time,seconds)
                    state(g.village)['elapsed']=142.5
                    expected=atmosphere.daylight(atmosphere.clock_progress(g.village))
                    g.save_game();g.start_slot(1)
                    self.assertEqual(g.town.clock_time(g.village),'17:30')
                    self.assertEqual(atmosphere.daylight(atmosphere.clock_progress(g.village)),expected)
                pygame.quit()
