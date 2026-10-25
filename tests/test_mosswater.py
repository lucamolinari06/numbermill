"""Receiver-driven survey progression, route reachability and old-save continuity."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
from collections import deque
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock,patch
import unittest
import pygame
import adventure
import manufacturing
import mosswater
from economy import Village
from test_adventure import design


def scan_at(g,position,frequency):
    current=adventure.state(g.village)
    current.update(position=list(position),frequency=frequency)
    current['bearing']=mosswater.payload(current,position)['direction']
    adventure.scan(g)


def complete_survey(g):
    current=adventure.state(g.village)
    current['position']=list(mosswater.POINTS['survey']);adventure.interact(g)
    g.adventure_modal=None
    for i,beacon in enumerate(mosswater.BEACONS):
        x,y=beacon['position']
        scan_at(g,(x-220,y),i)
        scan_at(g,(x,y-70),i)
    current['position']=list(mosswater.POINTS['range_lock']);adventure.interact(g)
    g.adventure_modal=None
    scan_at(g,(2980,1230),1);scan_at(g,(2980,1230),2)


class MosswaterTests(unittest.TestCase):
    def game(self):
        g=SimpleNamespace(village=Village(),save_game=Mock(),adventure_decoder_cache=None,
                          adventure_companion=SimpleNamespace(reset=Mock(),update=Mock()),
                          adventure_time=0.,adventure_cooldown=0.,adventure_speech_time=0.)
        s=adventure.state(g.village)
        s.update(receiver=True,decoder=True,interlock=True)
        s['designs']['decoder']=design('decoder').snapshot()
        return g,s

    def test_actual_receiver_obeys_manual_bearing_zero_range_and_saturation(self):
        g,s=self.game();s['position']=[780,420];s['bearing']=3
        reading=adventure.receiver_reading(g)
        self.assertFalse(reading['matched']);self.assertEqual(reading['low'],0)
        s['bearing']=1;reading=adventure.receiver_reading(g)
        self.assertTrue(reading['matched']);self.assertEqual((reading['low'],reading['high']),(90,100))
        s['position']=[1720,420];reading=adventure.receiver_reading(g)
        self.assertTrue(reading['matched']);self.assertEqual(reading['low'],0)
        s.update(survey_started=True,position=[100,690]);reading=adventure.receiver_reading(g)
        self.assertTrue(reading['overflow'])
        adventure.scan(g);self.assertEqual(s['survey_samples'],{})
        # The reading really comes from the installed board, not hidden arithmetic.
        s.update(position=[2000,430]);g.adventure_decoder_cache=None
        s['designs']['decoder']=design('interlock').snapshot()
        self.assertEqual(adventure.receiver_reading(g)['low'],0)

    def test_beacon_requires_two_separated_bearings_and_close_scan(self):
        g,s=self.game();s['survey_started']=True
        scan_at(g,(2160,430),0);scan_at(g,(2200,430),0)
        self.assertEqual(len(s['survey_samples']['crown']),1)
        scan_at(g,(2380,200),0)
        self.assertEqual(len(s['survey_samples']['crown']),2)
        self.assertEqual(s['survey_found'],[])
        scan_at(g,(2380,360),0);scan_at(g,(2380,360),0)
        self.assertEqual(s['survey_found'],['crown'])
        s['frequency']=1;s['bearing']=0
        adventure.scan(g);self.assertNotIn('fern',s['survey_samples'])

    def test_range_lock_requires_both_valid_returns_from_same_spot(self):
        g,s=self.game();s.update(survey_started=True,survey_found=['crown','fern','reed'],range_armed=True)
        scan_at(g,(2980,1230),1)
        self.assertEqual(set(s['range_reads']),{'fern'})
        scan_at(g,(2890,1220),2)  # Also in Reed's band, but a different location.
        self.assertFalse(s['range_gate']);self.assertEqual(set(s['range_reads']),{'reed'})
        scan_at(g,(2980,1230),1);self.assertFalse(s['range_gate'])
        scan_at(g,(2980,1230),2);self.assertTrue(s['range_gate'])
        self.assertEqual(s['frequency'],3)

    def test_range_lock_cannot_be_armed_before_survey_and_reward_stays_locked(self):
        g,s=self.game();s['position']=list(mosswater.POINTS['range_lock'])
        adventure.interact(g);self.assertFalse(s['range_armed'])
        s['position']=list(mosswater.POINTS['artifact']);adventure.interact(g)
        self.assertFalse(s['artifact'])

    def test_full_survey_and_older_focused_lens_both_complete(self):
        for old in (False,True):
            with self.subTest(old=old):
                g,s=self.game();s.update(artifact=old,receiver_upgrade=old)
                original=deepcopy(s['designs'])
                complete_survey(g)
                self.assertEqual(set(s['survey_found']),{'crown','fern','reed'})
                self.assertTrue(s['range_gate'])
                s['position']=list(mosswater.POINTS['artifact']);adventure.interact(g)
                self.assertTrue(s['expansion_complete']);self.assertTrue(s['receiver_upgrade'])
                self.assertTrue(manufacturing.equipment_unlocked(g.village,'precision_machine'))
                self.assertEqual(s['designs'],original)
                before=deepcopy(manufacturing.state(g.village));adventure.interact(g)
                self.assertEqual(manufacturing.state(g.village),before)

    def test_progress_roundtrips_through_village_save(self):
        g,s=self.game();s['survey_started']=True;scan_at(g,(2160,430),0)
        # Village's supported serialization is exercised by the integrated game test.
        saved=deepcopy(g.village.manufacturing);v=Village();v.manufacturing=saved
        restored=adventure.state(v)
        self.assertEqual(restored['survey_samples'],s['survey_samples'])
        self.assertEqual(restored['designs'],s['designs'])

    def test_routes_reach_all_survey_points_but_do_not_bypass_either_ravine(self):
        def reachable(start,closed):
            seen={start};queue=deque([start])
            while queue:
                x,y=queue.popleft()
                for nxt in ((x+10,y),(x-10,y),(x,y+10),(x,y-10)):
                    if nxt in seen or mosswater.blocked(*nxt):continue
                    if any(lo<=nxt[0]<=hi for lo,hi in closed):continue
                    seen.add(nxt);queue.append(nxt)
            return seen
        closed=reachable((100,690),((1180,1280),(3150,3260)))
        self.assertNotIn(mosswater.POINTS['survey'],closed)
        survey=reachable((100,690),((3150,3260),))
        for beacon in mosswater.BEACONS:
            x,y=beacon['position']
            for point in ((x,y),(x-220,y),(x,y-70)):
                self.assertIn(point,survey)
        self.assertIn((2980,1230),survey);self.assertNotIn(mosswater.POINTS['artifact'],survey)
        opened=reachable((2980,1230),())
        self.assertIn(mosswater.POINTS['artifact'],opened)

    def test_damage_cooldown_does_not_allow_walking_through_sealed_gate(self):
        pygame.init()
        try:
            for key,position,checkpoint in (('interlock',[1200,500],[1090.,540.]),('range_gate',[3200,1260],[3050.,1300.])):
                g,s=self.game();s[key]=False;s['position']=position;g.adventure_cooldown=1.
                with patch('pygame.key.get_pressed',return_value={k:False for k in (pygame.K_a,pygame.K_d,pygame.K_w,pygame.K_s,pygame.K_LEFT,pygame.K_RIGHT,pygame.K_UP,pygame.K_DOWN)}):
                    adventure.update(g,.1)
                self.assertEqual(s['position'],checkpoint);self.assertEqual(s['health'],100)
        finally:pygame.quit()
