"""Staggered home journeys, real-door entry, morning return and save continuity."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
from dataclasses import asdict
import json
import unittest
from unittest.mock import patch
import pygame

from citizens import home_time, night_due, social_company, update_activity
from daily_life import state, update_continuous, DAY_SECONDS
from economy import Village
from game import village_from_data
from town import Town, LOCATIONS, WORLD_W, WORLD_H


class ResidentEveningTests(unittest.TestCase):
    def setUp(self):
        self.village,self.town=Village(),Town()
        state(self.village)

    def clock(self,minute):
        state(self.village)['elapsed']=(minute-480)/720*DAY_SECONDS

    def test_departures_are_individual_stable_and_vary_by_day(self):
        times=[home_time(p['name'],1) for p in self.village.citizens]
        self.assertEqual(len(set(times)),len(times))
        self.assertGreater(max(times)-min(times),40)
        for p in self.village.citizens:
            self.assertTrue(1065<=home_time(p['name'],1)<=1125)
            self.assertEqual(home_time(p['name'],1),home_time(p['name'],1))
            self.assertNotEqual(home_time(p['name'],1),home_time(p['name'],2))

    def test_bedtime_interrupts_travel_but_does_not_teleport_the_resident(self):
        p=self.village.citizens[0]
        self.town.update_people(self.village,0)
        p.update(activity='visiting neighbors',destination='home_3')
        self.town.people[p['name']]=[1120.,970.]
        self.town.display_people[p['name']]=[1120.,970.]
        self.clock(home_time(p['name'],1))
        self.town.update_people(self.village,0)
        self.assertEqual(p['activity'],'heading home')
        self.assertEqual(p['destination'],p['home'])
        self.assertEqual(self.town.route_targets[p['name']],LOCATIONS[p['home']])
        self.assertEqual(self.town.people[p['name']],[1120.,970.])
        self.assertFalse(self.town.indoors(p['name']))

    def test_shared_home_entry_uses_actual_door_and_waits_for_displayed_arrival(self):
        p=self.village.citizens[0];name=p['name'];door=LOCATIONS[p['home']]
        self.clock(19*60)
        self.town.update_people(self.village,0)
        self.town.people[name]=list(door)
        self.town.display_people[name]=[door[0]+20.,door[1]]
        self.town.update_people(self.village,0)
        self.assertEqual(p['activity'],'sleeping')
        self.assertFalse(self.town.indoors(name))
        self.town.update_visuals(.25)
        self.assertTrue(self.town.indoors(name))

    def test_hidden_residents_have_no_outdoor_sprite_or_click_target(self):
        pygame.init()
        p=self.village.citizens[0];name=p['name'];door=LOCATIONS[p['home']]
        self.clock(19*60)
        self.town.update_people(self.village,0)
        self.town.people[name]=list(door);self.town.display_people[name]=list(door)
        self.town.update_people(self.village,0)
        self.town.player_x,self.town.player_y=door[0],door[1]+100
        ox=max(0,min(WORLD_W-1280,int(self.town.player_x-640)))
        oy=max(0,min(WORLD_H-760,int(self.town.player_y-380)))
        self.assertNotEqual(self.town.person_at((door[0]-ox,door[1]-oy-20)),name)
        fonts=tuple(pygame.font.SysFont('consolas',s) for s in (16,18,24,32))
        with patch.object(self.town,'_villager') as draw:
            self.town.draw(pygame.Surface((1280,760)),fonts,self.village,None,'')
        self.assertNotIn(name,[call.args[7] for call in draw.call_args_list])

    def test_sleeping_residents_do_not_supply_imaginary_social_company(self):
        p=next(p for p in self.village.citizens if p['name']=='Mely')
        other=next(p for p in self.village.citizens if p['name']=='Luca')
        p.update(activity='spending time with spouse',destination=p['home'],position=[990,1320])
        other.update(activity='sleeping',destination=p['home'],position=[990,1320])
        self.assertFalse(social_company(p,self.village))

    def test_morning_resumes_normal_choices_and_removes_indoor_hit_filter(self):
        self.clock(19*60)
        self.town.update_people(self.village,0)
        for p in self.village.citizens:
            self.town.people[p['name']]=list(LOCATIONS[p['home']])
            self.town.display_people[p['name']]=self.town.people[p['name']].copy()
        self.town.update_people(self.village,0)
        self.assertTrue(all(self.town.indoors(p['name']) for p in self.village.citizens))
        self.village.day+=1;self.village.daily_life={};state(self.village)
        self.town.update_people(self.village,0)
        self.assertFalse(any(self.town.indoors(p['name']) for p in self.village.citizens))
        self.assertTrue(all(p['activity'] not in ('heading home','sleeping') for p in self.village.citizens))

    def test_full_evening_walk_and_reload_continue_identically(self):
        update_continuous(self.village,self.town,170.)
        loaded=village_from_data(json.loads(json.dumps(asdict(self.village))))
        second=Town();second.update_people(loaded,0)
        update_continuous(self.village,self.town,9.)
        update_continuous(loaded,second,9.)
        self.assertEqual(asdict(self.village),asdict(loaded))
        self.town.update_visuals(1.)
        self.assertTrue(all(self.town.indoors(p['name']) for p in self.village.citizens))
        self.assertTrue(self.town.indoors('Grace'))


if __name__=='__main__':unittest.main()
