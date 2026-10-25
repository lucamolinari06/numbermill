"""Resident routines must work over actual travel and multiple calendar days."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
from dataclasses import asdict
import json
import unittest

from citizens import update_activity
from daily_life import DAY_SECONDS, SHIFT_SECONDS, state
from economy import Village
from game import village_from_data
from town import Town


class NpcWorkflowTests(unittest.TestCase):
    def test_finished_social_visits_do_not_freeze_everyone_at_one_house(self):
        v, town = Village(), Town()
        v.complete_mill_job()
        founders = {p['name'] for p in v.citizens}
        for _ in range(6):
            still_seconds = longest_still = 0
            for _ in range(int(DAY_SECONDS / .5)):
                before = {name: tuple(point) for name, point in town.people.items()
                          if name in founders}
                v.update_life(town, .5)
                moved = any(tuple(town.people[name]) != before.get(name) for name in founders)
                still_seconds = 0 if moved else still_seconds + .5
                longest_still = max(longest_still, still_seconds)
            # Normal visits take 12-24 seconds. A repeated shared-destination
            # loop previously kept the entire town still for over100 seconds.
            self.assertLess(longest_still, 30, f'All residents stalled on day {v.day}')
            for name in founders:
                self.assertEqual(state(v)['worked'].get(name), SHIFT_SECONDS)
            v.advance_day(town)

    def test_shift_fatigue_is_once_per_shift_across_short_visits_and_reload(self):
        for name in ('Ada', 'Bram', 'Agnes', 'Dara', 'Mely', 'Luca'):
            with self.subTest(name=name):
                v = Village()
                p = next(p for p in v.citizens if p['name'] == name)
                home = v.households[p['home']]
                home['bought'] = home['bread_need']
                p.update(activity='working', destination=p['workplace'], energy=90,
                         social_need=0, last_reason='Finishing shift')
                state(v)['worked'][name] = 12
                update_activity(p, home, v, 12, arrived=True)
                self.assertEqual(p['energy'], 90)
                state(v)['worked'][name] = SHIFT_SECONDS
                update_activity(p, home, v, 6, arrived=True)
                self.assertEqual(p['energy'], 68)
                loaded = village_from_data(json.loads(json.dumps(asdict(v))))
                p = next(p for p in loaded.citizens if p['name'] == name)
                p.update(activity='working', destination=p['workplace'])
                update_activity(p, loaded.households[p['home']], loaded, 30, arrived=True)
                self.assertEqual(p['energy'], 68)

    def test_spouse_visit_needs_spouse_present_not_just_a_shared_destination(self):
        for spouse_position in ((500, 500), (25, 25)):
            with self.subTest(spouse_position=spouse_position):
                v = Village()
                mely = next(p for p in v.citizens if p['name'] == 'Mely')
                luca = next(p for p in v.citizens if p['name'] == 'Luca')
                home = v.households[mely['home']]
                home['bought'] = home['bread_need']
                state(v)['worked']['Mely'] = SHIFT_SECONDS
                mely.update(activity='spending time with spouse', destination=mely['home'],
                            last_reason='Wants time with Luca', social_need=80,
                            energy=90, position=[0, 0])
                luca.update(destination=mely['home'], position=spouse_position)
                bond = mely['relationships']['Luca']
                update_activity(mely, home, v, 30, arrived=True)
                present = spouse_position == (25, 25)
                self.assertEqual(mely['relationships']['Luca'], bond + int(present))
                self.assertEqual(mely['social_need'], 49 if present else 94)

    def test_social_needs_do_not_prevent_daily_shifts_and_meals(self):
        v, town = Village(), Town()
        v.complete_mill_job()
        v.rival_busy_until = 99
        founders = [p['name'] for p in v.citizens]
        for _ in range(6):
            occupied_homes = {p['home'] for p in v.citizens}
            # Both normal needs and extreme loneliness must leave time to work.
            for person in v.citizens:
                person['social_need'] = 100
            v.update_life(town, DAY_SECONDS)
            for name in founders:
                self.assertEqual(state(v)['worked'].get(name), SHIFT_SECONDS,
                                 f'{name} did not finish the shift on day {v.day}')
            self.assertTrue(all(v.households[key]['bought'] == v.households[key]['bread_need']
                                for key in occupied_homes))
            v.advance_day(town)


if __name__ == '__main__':
    unittest.main()
