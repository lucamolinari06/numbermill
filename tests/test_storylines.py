"""Authored arcs keep real choices, funds, and observed-day progression."""
import json
import os
import tempfile
import unittest
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
from economy import Village
from character_projects import STORY_DEFINITIONS, accept, choose, deliver, evaluate, project_for, story_next
from dialogue import conversation


def observe(village, day):
    village.day = day
    village.last_day_report = {'day': day, 'produced': {'bakery': 4}, 'meals': {}}
    evaluate(village)


def fund(village, key):
    definition = STORY_DEFINITIONS[key]
    village.businesses[definition['payer']]['cash'] = 100
    village.material_inventory = definition['bill'].copy()


def cash(village):
    return village.coins + sum(f['cash'] for f in village.businesses.values()) + sum(h['cash'] for h in village.households.values())


class StorylineTests(unittest.TestCase):
    def test_offer_requires_observed_day_and_next_chapter_waits(self):
        v = Village()
        v.day = 3
        evaluate(v)
        self.assertNotIn('mely_bins', v.character_projects)
        observe(v, 3)
        self.assertEqual(project_for(v, 'Mely')['key'], 'mely_bins')
        self.assertNotIn('mely_plan', v.character_projects)
        fund(v, 'mely_bins'); accept(v, 'mely_bins'); self.assertTrue(deliver(v, 'mely_bins')[0])
        evaluate(v)
        self.assertNotIn('mely_plan', v.character_projects)
        observe(v, 4)
        self.assertEqual(project_for(v, 'Mely')['key'], 'mely_plan')
        self.assertNotIn('mely_memory', v.character_projects)

    def test_both_arcs_and_every_choice_conserve_cash_and_cannot_repeat(self):
        for name, keys, branch, certificate in (
            ('Mely', ('mely_bins','mely_plan','mely_memory'), 'customers','memory'),
            ('Mely', ('mely_bins','mely_plan','mely_memory'), 'home','memory'),
            ('Luca', ('luca_sort','luca_share','luca_counter'), 'repairs','counter'),
            ('Luca', ('luca_sort','luca_share','luca_counter'), 'pantry','counter')):
            with self.subTest(name=name, branch=branch):
                v = Village(); observe(v, 3)
                for chapter, key in enumerate(keys, 1):
                    if chapter == 3:
                        observe(v, v.day + 1)
                        self.assertNotIn(key, v.character_projects)
                        previous = project_for(v, name)
                        self.assertIn('timing goal', story_next(v, previous))
                        v.sequential_records = {certificate: {'day': v.day}}
                    if chapter > 1:
                        observe(v, v.day + 1)
                    fund(v, key)
                    if chapter == 2:
                        before = deepcopy(v.character_projects[key])
                        self.assertIn('Choose', accept(v, key))
                        self.assertEqual(v.character_projects[key], before)
                        self.assertTrue(choose(v, key, branch)[0])
                    accept(v, key)
                    if chapter == 2:
                        self.assertFalse(choose(v, key, branch)[0])
                    before = cash(v)
                    self.assertTrue(deliver(v, key)[0])
                    self.assertEqual(cash(v), before)
                    snapshot = deepcopy(asdict(v))
                    self.assertFalse(deliver(v, key)[0])
                    self.assertEqual(asdict(v), snapshot)
                self.assertEqual(project_for(v, name)['chapter'], 3)
                self.assertEqual(project_for(v, name)['status'], 'completed')
                self.assertIn('Story complete', story_next(v, project_for(v, name)))
                if branch == 'pantry':
                    self.assertEqual(v.businesses['market']['pantry_protection'], 2)
                if branch == 'home':
                    self.assertIn('6c', v.character_projects['mely_plan']['outcome'])
                person = next(p for p in v.citizens if p['name'] == name)
                self.assertEqual(len([m for m in person['memories'] if 'Boole helped' in m]), 3)
                self.assertIn('home' if name == 'Luca' else 'evening', conversation(v, name, 'family')[0])

    def test_choice_and_pending_promise_survive_save_reload(self):
        v = Village(); observe(v, 3)
        fund(v,'mely_bins'); accept(v,'mely_bins'); deliver(v,'mely_bins'); observe(v,4)
        choose(v, 'mely_plan', 'home'); accept(v, 'mely_plan')
        loaded = Village(**json.loads(json.dumps(asdict(v))))
        project = project_for(loaded, 'Mely')
        self.assertEqual((project['key'],project['status'],project['choice']), ('mely_plan','accepted','home'))
        fund(loaded, 'mely_plan')
        loaded.businesses['fuel_yard']['cash'] = 11  # Reward plus household transfer costs 12.
        before = deepcopy(asdict(loaded))
        self.assertFalse(deliver(loaded, 'mely_plan')[0])
        self.assertEqual(asdict(loaded), before)
        loaded.businesses['fuel_yard']['cash'] = 12
        self.assertTrue(deliver(loaded, 'mely_plan')[0])

    def test_requests_show_each_neighbor_once_and_choice_click_is_saved(self):
        import pygame
        from game import Game
        from project_ui import visible
        Path('.test-tmp').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir='.test-tmp') as directory, \
                patch('game.SAVES_DIR', Path(directory)/'saves'), \
                patch('game.SAVE_FILE', Path(directory)/'old.json'), \
                patch('game.DESIGNS_FILE', Path(directory)/'designs.json'):
            game = Game(); game.start_slot(2)
            v=game.village; observe(v,3)
            fund(v,'mely_bins'); accept(v,'mely_bins'); deliver(v,'mely_bins'); observe(v,4)
            game.open_requests('Mely'); game.draw()
            names=[p['npc'] for p in visible(v)]
            self.assertEqual(len(names),len(set(names)))
            game.handle_click((900,535),1)
            self.assertEqual(v.character_projects['mely_plan']['choice'],'home')
            game.handle_click((550,585),1)
            self.assertEqual(v.character_projects['mely_plan']['status'],'accepted')
            reloaded=Game(); reloaded.start_slot(2)
            self.assertEqual(reloaded.village.character_projects['mely_plan']['choice'],'home')
            pygame.quit()


    def test_continuous_village_days_offer_stories_without_synthetic_reports(self):
        from daily_life import DAY_SECONDS, update_continuous
        from town import Town
        v, town = Village(), Town()
        update_continuous(v, town, DAY_SECONDS * 2)
        self.assertNotIn('mely_bins', v.character_projects)
        self.assertNotIn('luca_sort', v.character_projects)
        update_continuous(v, town, DAY_SECONDS)
        self.assertEqual(v.day, 4)
        for key in ('mely_bins', 'luca_sort'):
            self.assertEqual(v.character_projects[key]['offered_day'], 3)
            self.assertEqual(v.character_projects[key]['status'], 'offered')

    def test_real_workshop_certificates_unlock_final_chapters_and_survive_reload(self):
        import pygame
        import timing_workshop
        from circuit import Part
        from game import Game
        Path('.test-tmp').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir='.test-tmp') as directory, \
                patch('game.SAVES_DIR', Path(directory)/'saves'), \
                patch('game.SAVE_FILE', Path(directory)/'old.json'), \
                patch('game.DESIGNS_FILE', Path(directory)/'designs.json'):
            game=Game(); game.start_slot(2)
            for _ in range(3):
                game.next_day()
            def finish(key, branch=None):
                fund(game.village,key)
                if branch:
                    self.assertTrue(choose(game.village,key,branch)[0])
                game.act_on_request(key)
                self.assertEqual(game.village.character_projects[key]['status'],'accepted')
                game.act_on_request(key)
                self.assertEqual(game.village.character_projects[key]['status'],'completed')
            finish('mely_bins'); finish('luca_sort')
            for _ in range(2):
                game.next_day()
            finish('mely_plan','home'); finish('luca_share','pantry')
            for _ in range(2):
                game.next_day()
            self.assertNotIn('mely_memory',game.village.character_projects)
            self.assertNotIn('luca_counter',game.village.character_projects)
            for goal,kind in (('memory','REGISTER'),('counter','COUNTER')):
                timing_workshop.enter(game,goal)
                # Empty drafts cannot award a certificate.
                timing_workshop.test(game)
                self.assertNotIn(goal,game.village.sequential_records)
                circuit=game.circuit
                circuit.set_part((6,3),Part(kind))
                positions={port['name']:pos for pos,port in circuit.terminals.items()}
                circuit.connect(positions['A'],(6,3),0)
                circuit.connect(positions['B'],(6,3),1)
                circuit.connect((6,3),positions['OUT'],0)
                timing_workshop.test(game)
                self.assertTrue(all(row.passed for row in game.timing_results))
                self.assertIn(goal,game.village.sequential_records)
                timing_workshop.leave(game)
            game.next_day()
            finish('mely_memory'); finish('luca_counter')
            game.save_game()
            loaded=Game(); loaded.start_slot(2)
            for key,goal in (('mely_memory','memory'),('luca_counter','counter')):
                self.assertEqual(loaded.village.character_projects[key]['status'],'completed')
                self.assertEqual(loaded.village.character_projects[key]['certificate'],goal)
                self.assertIn(goal,loaded.village.sequential_records)
            self.assertEqual(loaded.village.character_projects['mely_plan']['choice'],'home')
            self.assertEqual(loaded.village.character_projects['luca_share']['choice'],'pantry')
            pygame.quit()

    def test_completed_family_arc_is_remembered_with_older_pending_favor(self):
        v=Village()
        v.character_projects={
            'repair_kit':{'status':'accepted','offered_day':1,'accepted_day':1,'reason':'Old promise'},
            'luca_counter':{'status':'completed','offered_day':7,'completed_day':8,'reason':'Trial',
                            'outcome':STORY_DEFINITIONS['luca_counter']['outcome']},
        }
        # The unfinished favor should still be the actionable request.
        self.assertEqual(project_for(v,'Luca')['key'],'repair_kit')
        self.assertIn('came home to Mely',conversation(v,'Luca','family')[0])
