"""Destination truth, presentation isolation and four-facing character envelopes."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
from copy import deepcopy
import unittest

import pygame

from economy import Village
from town import Town, LOCATIONS
from town_companion import Companion
from resident_performance import performances, coat_for


class ResidentPerformanceTests(unittest.TestCase):
    def setUp(self):
        self.village, self.town = Village(), Town()

    def place(self, name, activity, destination, point=None):
        person = next(p for p in self.village.citizens if p['name'] == name)
        person.update(activity=activity, destination=destination)
        self.town.people[name] = list(point or LOCATIONS[destination])
        self.town.display_people[name] = self.town.people[name].copy()
        return person

    def poses(self):
        return performances(self.town, self.village)

    def test_work_waits_for_displayed_arrival_and_current_destination(self):
        self.place('Ada', 'working', 'farm')
        self.assertEqual(self.poses()['Ada'].action, 'tend')
        self.town.display_people['Ada'][0] += 15
        self.assertEqual(self.poses()['Ada'].action, 'idle')
        self.town.display_people['Ada'] = list(LOCATIONS['farm'])
        self.town.display_moving.add('Ada')
        self.assertEqual(self.poses()['Ada'].action, 'idle')
        self.town.display_moving.clear()
        self.place('Ada', 'working', 'mill')
        self.assertEqual(self.poses()['Ada'].action, 'idle')

    def test_shopping_basket_travels_but_paused_workplace_only_gets_inspection(self):
        self.place('Dara', 'seeking food', 'market', (900,625))
        self.town.display_moving.add('Dara')
        self.assertEqual(self.poses()['Dara'].action, 'basket')
        self.town.display_moving.clear()
        self.place('Dara', 'working', 'market')
        self.assertEqual(self.poses()['Dara'].action, 'sweep')
        self.village.businesses['market']['operating_state'] = 'paused'
        self.assertEqual(self.poses()['Dara'].action, 'inspect')

    def test_social_pose_needs_arrived_company_and_faces_them(self):
        # Isolate the pair so a third person's scheduled visit cannot mask it.
        self.village.citizens = [p for p in self.village.citizens if p['name'] in ('Mely','Luca')]
        destination = self.village.citizens[0]['home']
        x,y = LOCATIONS[destination]
        self.place('Luca', 'at home', destination, (x-30,y+20))
        self.place('Mely', 'spending time with spouse', destination, (x+30,y+20))
        self.assertEqual(self.poses()['Mely'].action, 'sit_chat')
        self.assertEqual(self.poses()['Mely'].facing, 'west')
        self.town.display_people['Luca'][0] -= 20
        self.assertEqual(self.poses()['Mely'].action, 'idle')
        self.town.display_people['Luca'][0] += 20
        self.town.display_moving.add('Luca')
        self.assertEqual(self.poses()['Mely'].action, 'idle')

    def test_wide_destination_groups_use_reserved_slots_not_building_radius(self):
        # Use the actual home key, not an assumed map identifier.
        destination = self.village.citizens[0]['home']
        x,y = LOCATIONS[destination]
        names = sorted(p['name'] for p in self.village.citizens)
        for index,name in enumerate(names):
            self.place(name,'visiting neighbors',destination,(x+(index-(len(names)-1)/2)*60,y+20))
        self.assertTrue(all(p.action=='sit_chat' for p in self.poses().values()))

    def test_conversation_turn_and_rendering_do_not_change_simulation_or_paths(self):
        self.place('Ada','working','farm')
        self.town.player_x,self.town.player_y = self.town.people['Ada'][0]+90,self.town.people['Ada'][1]
        before = deepcopy(vars(self.village))
        town_before = deepcopy((self.town.people,self.town.display_people,self.town.routes,self.town.display_facing))
        pose = performances(self.town,self.village,'Ada')['Ada']
        self.assertEqual((pose.action,pose.facing),('chat','east'))
        surface=pygame.Surface((100,110),pygame.SRCALPHA)
        for seconds in (0.,.5,1.,4.8):
            self.town._villager(surface,50,65,coat_for('Ada'),name='Ada',action=pose.action,facing=pose.facing,seconds=seconds)
        self.assertEqual(vars(self.village),before)
        self.assertEqual((self.town.people,self.town.display_people,self.town.routes,self.town.display_facing),town_before)

    def test_every_facing_and_performance_fits_actor_envelope_and_grace_keeps_wooden_leg(self):
        for name in ('Boole','Mely','Luca','Grace','Ada','Bram','Agnes','Dara','Rowan','Jun'):
            for facing in ('north','south','east','west'):
                for action in ('idle','basket','repair','inspect','sweep','tend','sit','chat','sit_chat'):
                    for seconds in (0.,.5,1.,1.5):
                        with self.subTest(name=name,facing=facing,action=action,seconds=seconds):
                            surface=pygame.Surface((100,110),pygame.SRCALPHA)
                            self.town._villager(surface,50,65,coat_for(name),name=name,facing=facing,action=action,seconds=seconds)
                            self.assertTrue(pygame.Rect(25,3,50,88).contains(surface.get_bounding_rect()))
                            if name=='Grace':
                                colors={surface.get_at((x,y))[:3] for x in range(25,75) for y in range(75,90)}
                                self.assertIn((172,122,69),colors)

    def test_reduced_motion_shannon_freezes_decoration_but_keeps_walk_and_attention(self):
        follower=Companion((400,400),lambda x,y:False)
        def frame(seconds, reduced=True, attentive=False):
            follower.seconds=seconds
            surface=pygame.Surface((90,100),pygame.SRCALPHA)
            follower.draw(surface,45,60,reduced_motion=reduced,attentive=attentive)
            return pygame.image.tobytes(surface,'RGBA')
        self.assertEqual(frame(0),frame(4.6))
        self.assertNotEqual(frame(0,False),frame(4.6,False))
        self.assertNotEqual(frame(0),frame(0,attentive=True))
        follower.moving=True
        first=frame(0)
        follower.phase=1.57
        self.assertNotEqual(first,frame(0))


if __name__ == '__main__':
    unittest.main()
