"""Developer shortcuts must preserve real puzzle output and normal collision."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
import tempfile
import unittest
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pygame
import adventure
import boiler_tower as tower
import developer_mode as dev
import manufacturing
from game import Game


class DeveloperModeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.patches = [patch('game.SAVES_DIR', root/'saves'),
                        patch('game.SAVE_FILE', root/'old.json'),
                        patch('game.DESIGNS_FILE', root/'designs.json')]
        for item in self.patches: item.start()
        self.g = Game()
        self.g.start_slot(1)

    def tearDown(self):
        pygame.quit()
        for item in reversed(self.patches): item.stop()
        self.temp.cleanup()

    def enter_tower(self):
        adventure.state(self.g.village)['expansion_complete'] = True
        tower.enter(self.g)
        adventure.close_notice(self.g)

    def key(self, key):
        self.g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode=''))

    def test_all_generated_boards_pass_actual_exhaustive_certification(self):
        for kind in ('decoder', 'interlock', *tower.EDITOR_KEYS):
            with self.subTest(kind=kind):
                ok, message = adventure.certify(dev.solution(kind), kind)
                self.assertTrue(ok, message)

    def test_pause_toggle_uses_click_routing_and_freezes_world(self):
        g = self.g
        self.enter_tower()
        self.key(pygame.K_ESCAPE)
        self.assertTrue(g.pause_menu_open)
        self.assertFalse(dev.enabled(g))
        g.draw()
        rect, _ = g.pause_buttons()[-1]
        g.handle_click(rect.center, 1)
        self.assertTrue(dev.enabled(g))
        before = deepcopy(tower.state(g.village))
        g.update(.1)
        self.assertEqual(tower.state(g.village), before)
        self.key(pygame.K_RETURN)
        self.assertFalse(g.pause_menu_open)

    def test_tools_are_guarded_and_not_saved_as_enabled(self):
        g = self.g
        self.enter_tower()
        before = deepcopy(tower.state(g.village))
        self.assertFalse(dev.solve(g, 'jetpack_0'))
        dev.next_maintenance(g)
        self.assertEqual(tower.state(g.village), before)
        dev.toggle(g)
        dev.solve(g, 'jetpack_0')
        g.save_game()
        g.start_slot(1)
        self.assertFalse(dev.enabled(g))
        self.assertTrue(adventure.certify(dev.solution('jetpack_0'), 'jetpack_0')[0])
        self.assertIn('jetpack_0', adventure.state(g.village)['designs'])

    def test_tower_noclip_crosses_steel_shutters_and_curtain_without_damage(self):
        g = self.g
        self.enter_tower()
        dev.toggle(g)
        s = tower.state(g.village)
        # Fly upward through a deck's underside, with no installed jetpack.
        x, top = tower.landing_position(1)
        s['position'] = [x, top+80]
        for _ in range(30): tower.step(g, 1/60, thrust=True)
        self.assertLess(s['position'][1], top)
        # A locked section shutter and the closed exhaust curtain do not block.
        for barrier in (tower.layout.ceiling(0), tower.layout.VENT_Y+45):
            s['position'] = [600., barrier+10]
            tower.step(g, .1, thrust=True)
            self.assertLess(s['position'][1], barrier)
        health = adventure.state(g.village)
        for hazard in tower.layout.HAZARDS:
            s['hazard_time'] = 4.1-hazard['offset']
            r = tower.layout.hazard_state(hazard, s['hazard_time'])['rect']
            s['position'] = [float(r.centerx), float(r.centery)]
            tower.step(g, .01)
        tower.hurt(g, 'test')
        tower.fall(g)
        self.assertEqual(health['health'], 100)
        self.assertEqual(health['injuries'], 0)
        self.assertEqual(s['falls'], 0)
        self.assertEqual(g.scene, 'boiler_tower')

    def test_disabling_returns_to_checkpoint_and_restores_damage(self):
        g = self.g
        self.enter_tower()
        dev.toggle(g)
        s = tower.state(g.village)
        s['position'] = [570., 5170.]
        dev.toggle(g)
        self.assertEqual(s['position'], tower.landing_position(0))
        self.assertTrue(g.tower_grounded)
        tower.hurt(g, 'test')
        self.assertEqual(adventure.state(g.village)['health'], 75)

    def test_hud_buttons_advance_each_stage_and_keep_reward_one_time(self):
        g = self.g
        self.enter_tower()
        dev.toggle(g)
        for stage in range(3):
            self.assertEqual(tower.state(g.village)['stage'], stage)
            g.draw()
            g.handle_click((170, 337), 1)
            self.assertGreater(tower.output(g, f'jetpack_{stage}', (5, 0, 3)), 0)
            if stage == 2:
                g.draw()
                g.handle_click((170, 337), 1)
                self.assertEqual(tower.output(g, 'tower_vent', (9, 4, 1)), 5)
            g.draw()
            g.handle_click((170, 371), 1)
            self.assertEqual(tower.state(g.village)['checkpoint'], tower.STATIONS[stage+1])
            self.assertIsNotNone(g.adventure_modal)
            adventure.close_notice(g)
        tower.interact(g)
        self.assertTrue(tower.state(g.village)['complete'])
        self.assertEqual(manufacturing.state(g.village)['unlocks'].count('steam_accumulator'), 1)
        dev.next_maintenance(g)
        self.assertEqual(manufacturing.state(g.village)['unlocks'].count('steam_accumulator'), 1)

    def test_field_auto_solve_button_preserves_workshop_context(self):
        g = self.g
        self.enter_tower()
        dev.toggle(g)
        original = g.circuit.snapshot()
        tower.edit(g)
        self.key(pygame.K_ESCAPE)  # Close the specification first.
        g.draw()
        g.handle_click((1090, 610), 1)
        self.assertTrue(adventure.certify(g.circuit, 'jetpack_0')[0])
        self.assertIn('jetpack_0', adventure.state(g.village)['designs'])
        adventure.close_editor(g)
        self.assertEqual(g.circuit.snapshot(), original)

    def test_mosswater_noclip_skips_water_and_closed_ravine_then_restores_safety(self):
        g = self.g
        adventure.enter(g)
        dev.toggle(g)
        s = adventure.state(g.village)
        keys = defaultdict(bool, {pygame.K_d: True})
        with patch('pygame.key.get_pressed', return_value=keys):
            for point in ([1170., 500.], [2120., 700.]):
                s['position'] = point[:]
                adventure.update(g, .1)
                self.assertGreater(s['position'][0], point[0])
                self.assertEqual(s['position'][1], point[1])
        adventure.hurt(g, 100)
        self.assertEqual(s['health'], 100)
        dev.toggle(g)
        self.assertFalse(adventure.blocked(*s['position']))
        adventure.hurt(g, 25)
        self.assertEqual(s['health'], 75)

    def test_mosswater_skip_button_handles_each_puzzle_and_archive_unlocks_tower(self):
        g = self.g
        adventure.enter(g)
        dev.toggle(g)
        for expected in ('decoder', 'interlock', 'survey', 'range lock'):
            self.assertEqual(dev.mosswater_task(g), expected)
            g.draw()
            g.handle_click((170, 348), 1)
        self.assertIsNone(dev.mosswater_task(g))
        s = adventure.state(g.village)
        s['position'] = list(adventure.POINTS['artifact'])
        adventure.interact(g)
        self.assertTrue(tower.unlocked(g.village))


if __name__ == '__main__':
    unittest.main()
