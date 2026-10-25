"""Opening chapter continuity, honest evidence, input isolation and text bounds."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pygame
import adventure
import boiler_tower
import chapter_ui
import opening_chapter as story
from economy import Village
from game import Game, village_from_data
from daily_life import state as daily_state


class EvidenceTests(unittest.TestCase):
    def test_discoveries_never_expose_future_clues(self):
        village = Village()
        self.assertEqual(set(story.observe(village)['evidence']), {'search'})
        self.assertEqual(story.available_scenes(village), ['opening'])
        adventure.state(village)['receiver'] = True
        self.assertEqual(set(story.observe(village)['evidence']), {'search', 'receiver'})
        self.assertNotIn('southern', ' '.join(story.topic(village, 'Luca')))
        adventure.state(village)['artifact'] = True
        self.assertIn('mosswater_home', story.available_scenes(village))
        self.assertNotIn('tower_home', story.available_scenes(village))
        self.assertNotIn('tower route', story.pages(village, 'mosswater_home')[-1][1])
        adventure.state(village)['expansion_complete'] = True
        self.assertIn('tower_route', story.observe(village)['evidence'])

    def test_old_completed_save_gets_followups_without_replaying_rewards(self):
        village = Village()
        field = adventure.state(village)
        field.update(artifact=True, expansion_complete=True, receiver=True, health=64)
        boiler_tower.state(village).update(complete=True, pack_broken=True)
        village.manufacturing['unlocks'] += ['precision_machine', 'steam_accumulator']
        original = deepcopy(vars(village))
        loaded = village_from_data(json.loads(json.dumps(original)))
        story.observe(loaded)
        self.assertEqual(story.pending(loaded), 'mosswater_home')
        self.assertIn('tower_home', story.available_scenes(loaded))
        for _ in range(3):
            for key in ('mosswater_home', 'tower_home'):
                story.complete_scene(loaded, key)
        self.assertEqual(loaded.coins, village.coins)
        self.assertEqual(loaded.manufacturing['unlocks'], village.manufacturing['unlocks'])
        self.assertEqual(loaded.manufacturing['adventure'], original['manufacturing']['adventure'])
        self.assertEqual(loaded.manufacturing['boiler_tower'], original['manufacturing']['boiler_tower'])
        self.assertNotIn('day', story.state(loaded)['evidence']['accumulator'])
        self.assertIn('tower_home', story.state(loaded)['evidence'])

    def test_only_finished_conversations_become_evidence(self):
        village = Village()
        adventure.state(village)['artifact'] = True
        story.scene_progress(village, 'mosswater_home')['page'] = 2
        self.assertNotIn('mosswater_home', story.observe(village)['evidence'])
        story.complete_scene(village, 'mosswater_home')
        self.assertIn('mosswater_home', story.observe(village)['evidence'])

    def test_everyday_scene_requires_actual_personal_progress(self):
        village = Village()
        adventure.state(village)['artifact'] = True
        story.complete_scene(village, 'mosswater_home')
        self.assertNotIn('well_evening', story.available_scenes(village))
        village.character_projects['mely_bins'] = {'status': 'accepted'}
        self.assertNotIn('well_evening', story.available_scenes(village))
        village.character_projects['mely_bins']['status'] = 'completed'
        self.assertIn('well_evening', story.available_scenes(village))

    def test_topics_reflect_evidence_and_existing_arcs(self):
        village = Village()
        before = story.topic(village, 'Shannon')
        adventure.state(village)['artifact'] = True
        self.assertNotEqual(story.topic(village, 'Shannon'), before)
        village.manufacturing['unlocks'].append('steam_accumulator')
        self.assertIn('southern', ' '.join(story.topic(village, 'Luca')))
        village.character_projects['mely_memory'] = {'status': 'completed'}
        self.assertIn('trial you helped finish', story.topic(village, 'Mely')[1])
        village.character_projects['luca_counter'] = {'status': 'completed'}
        self.assertIn('finished trial', story.topic(village, 'Luca')[1])


class ChapterUITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.patches = [patch('game.SAVES_DIR', root / 'saves'),
                        patch('game.SAVE_FILE', root / 'old.json'),
                        patch('game.DESIGNS_FILE', root / 'designs.json')]
        for item in self.patches:
            item.start()
        self.g = Game()
        self.g.start_slot(1)

    def tearDown(self):
        pygame.quit()
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def key(self, value):
        self.g.handle_key(pygame.event.Event(pygame.KEYDOWN, key=value, mod=0))

    def test_journal_opens_by_button_and_keyboard_and_blocks_world_input(self):
        g = self.g
        g.draw()
        g.handle_click(chapter_ui.JOURNAL_BUTTON.center, 1)
        self.assertTrue(chapter_ui.active(g))
        before = deepcopy(daily_state(g.village))
        position = (g.town.player_x, g.town.player_y)
        g.update(30)
        self.assertEqual(daily_state(g.village), before)
        self.assertEqual((g.town.player_x, g.town.player_y), position)
        self.key(pygame.K_n)
        self.assertEqual(daily_state(g.village), before)
        g.draw()
        with patch.object(g.town, 'person_at') as hit:
            g.handle_click((50, 200), 1)
            hit.assert_not_called()
        self.key(pygame.K_ESCAPE)
        self.assertFalse(chapter_ui.active(g))
        self.assertFalse(g.pause_menu_open)
        self.key(pygame.K_b)
        self.assertTrue(chapter_ui.active(g))

    def test_partial_scene_resumes_after_real_slot_roundtrip_then_replays(self):
        g = self.g
        adventure.state(g.village).update(artifact=True, expansion_complete=True)
        self.key(pygame.K_RETURN)
        self.assertEqual(g.chapter_view['key'], 'mosswater_home')
        self.key(pygame.K_RETURN)
        self.key(pygame.K_RETURN)
        self.key(pygame.K_ESCAPE)
        g.return_to_menu()
        g.start_slot(1)
        self.assertIsNone(g.chapter_view)
        self.key(pygame.K_RETURN)
        self.assertEqual(g.chapter_view['index'], 2)
        while chapter_ui.active(g):
            self.key(pygame.K_RETURN)
        self.assertTrue(story.state(g.village)['scenes']['mosswater_home']['complete'])
        coins, field, designs = g.village.coins, deepcopy(adventure.state(g.village)), deepcopy(g.designs)
        chapter_ui.start_scene(g, 'mosswater_home')
        self.assertEqual(g.chapter_view['index'], 0)
        while chapter_ui.active(g):
            self.key(pygame.K_RETURN)
        self.assertEqual((g.village.coins, adventure.state(g.village), g.designs), (coins, field, designs))
        g.start_slot(2)
        self.assertEqual(story.available_scenes(g.village), ['opening'])
        self.assertEqual(story.state(g.village)['scenes'], {})

    def test_field_journal_freezes_tower_physics_and_restores_controls(self):
        g = self.g
        adventure.state(g.village)['expansion_complete'] = True
        boiler_tower.enter(g)
        self.key(pygame.K_b)
        self.assertFalse(chapter_ui.active(g))  # Arrival instructions take priority.
        adventure.close_notice(g)
        g.draw()
        g.handle_click(chapter_ui.JOURNAL_BUTTON.center, 1)
        before = deepcopy(boiler_tower.state(g.village))
        time = g.tower_time
        g.update(5)
        self.key(pygame.K_r)
        self.assertEqual(boiler_tower.state(g.village), before)
        self.assertEqual(g.tower_time, time)
        self.key(pygame.K_ESCAPE)
        self.assertEqual(g.scene, 'boiler_tower')
        self.key(pygame.K_r)
        self.assertNotEqual(boiler_tower.state(g.village)['throttle'], before['throttle'])

    def test_homecoming_waits_for_home_but_memories_can_be_replayed_in_field(self):
        g = self.g
        adventure.state(g.village).update(artifact=True, expansion_complete=True)
        g.scene = 'adventure'
        chapter_ui.open_journal(g)
        self.assertFalse(chapter_ui.start_scene(g, 'mosswater_home'))
        self.assertEqual(g.chapter_view['mode'], 'journal')
        g.scene = 'town'
        self.assertTrue(chapter_ui.start_scene(g, 'mosswater_home'))
        while chapter_ui.active(g):
            chapter_ui.advance(g)
        g.scene = 'adventure'
        self.assertTrue(chapter_ui.start_scene(g, 'mosswater_home'))
        self.assertTrue(g.chapter_view['replay'])

    def test_journal_mouse_and_keyboard_pages_do_not_scroll_circuit_results(self):
        g = self.g
        field = adventure.state(g.village)
        field.update(receiver=True, artifact=True, expansion_complete=True)
        g.village.manufacturing['unlocks'].append('steam_accumulator')
        story.complete_scene(g.village, 'mosswater_home')
        story.complete_scene(g.village, 'tower_home')
        self.key(pygame.K_b)
        self.key(pygame.K_RIGHT)
        self.assertEqual(g.chapter_view['index'], 5)
        g.draw()
        g.handle_click((235, 646), 1)
        self.assertEqual(g.chapter_view['index'], 0)
        self.key(pygame.K_RIGHT)
        original_scroll = g.test_scroll
        g.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, y=1))
        self.assertEqual(g.chapter_view['index'], 4)
        self.assertEqual(g.test_scroll, original_scroll)
        self.key(pygame.K_TAB)
        self.assertEqual(g.chapter_view['tab'], 'Moments')
        self.key(pygame.K_RETURN)
        self.assertEqual(g.chapter_view['key'], 'opening')

    def test_journey_topic_click_and_key_follow_actual_progress(self):
        g = self.g
        g.town_dialogue = 'person:Luca'
        g.draw()
        g.handle_click((920, 447), 1)
        self.assertEqual(g.town_topic, 'journey')
        self.assertEqual(story.state(g.village)['topics']['Luca'], 'search')
        g.village.manufacturing.setdefault('unlocks', []).append('steam_accumulator')
        self.key(pygame.K_6)
        self.assertEqual(story.state(g.village)['topics']['Luca'], 'tower')
        self.key(pygame.K_1)
        self.assertEqual(g.town_topic, 'work')

    def test_focus_loss_settings_and_close_preserve_scene_page(self):
        g = self.g
        chapter_ui.start_scene(g, 'opening')
        self.key(pygame.K_RETURN)
        g.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        g.draw()
        self.key(pygame.K_RETURN)
        self.assertEqual(g.chapter_view['index'], 1)
        self.assertFalse(g.pause_menu_open)
        g.draw()
        self.key(pygame.K_ESCAPE)
        self.assertEqual(story.state(g.village)['scenes']['opening']['page'], 1)

    def test_all_authored_text_fits_without_truncation(self):
        g = self.g
        def height(value, width, font, leading):
            surface = pygame.Surface((1280, 900))
            return chapter_ui.wrapped_text(surface, font, value, 0, 0, width, line_height=leading)
        for scene, (_, _, rows) in story.SCENES.items():
            for _, paragraph in rows:
                self.assertLessEqual(431 + height(paragraph, 770, g.font, 29), 580, scene)
        for _, (_, _, observation, question) in story.EVIDENCE.items():
            end = 345 + height(observation, 560, g.font, 25)
            self.assertLessEqual(max(510, end + 53) + height(question, 560, g.font, 25), 618)
        for stage in ('search', 'mosswater', 'tower'):
            if stage == 'mosswater':
                adventure.state(g.village)['artifact'] = True
            elif stage == 'tower':
                g.village.manufacturing['unlocks'].append('steam_accumulator')
            for person in story.PEOPLE:
                bottom = 483 + sum(height(row, 750, g.font, 23) + 12 for row in story.topic(g.village, person))
                self.assertLessEqual(bottom, 674, (stage, person))


if __name__ == '__main__':
    unittest.main()
