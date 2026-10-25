"""Migration decisions require observed consecutive days and survive saves."""
from dataclasses import asdict
import unittest
from economy import Village
from migration import evaluate


class MigrationTests(unittest.TestCase):
    def healthy(self, v):
        for home in v.households.values():
            home.update(cash=60, bought=home['bread_need'])
        v.businesses['market']['stock']['bread'] = 3
        v.businesses['mill']['machines'] = ['mill_controller']
        v.businesses['mill']['cash'] = 100
        v.businesses['mill']['hiring_surplus'] = 8

    def test_three_consecutive_days_and_idempotent_review(self):
        v = Village()
        self.healthy(v)
        evaluate(v)
        evaluate(v)
        self.assertEqual(v.migration['healthy_days'], 1)
        self.assertNotIn('home_4', v.households)
        v.day += 1
        self.healthy(v)
        evaluate(v)
        v = Village(**asdict(v))
        v.day += 1
        self.healthy(v)
        evaluate(v)
        self.assertEqual(v.migration['housing_stage'], 'construction')
        self.assertNotIn('home_4', v.households)
        for _ in range(2):
            v.day += 1
            self.healthy(v)
            evaluate(v)
            v = Village(**asdict(v))
        self.assertEqual(v.migration['housing_stage'], 'occupied')
        self.assertEqual(len(v.citizens), 7)
        self.assertEqual(v.households['home_4']['cash'], 48)
        self.assertEqual(v.businesses['mill']['workers'], 2)
        self.assertEqual(v.migration_events[-1]['kind'], 'arrival')
        for _ in range(8):
            v.day += 1
            self.healthy(v)
            evaluate(v)
        self.assertEqual(len(v.citizens), 7)

    def test_shortage_resets_streak_and_no_job_blocks_arrival(self):
        v = Village()
        self.healthy(v)
        evaluate(v)
        v.day += 1
        v.households['home_1']['bought'] = 0
        evaluate(v)
        self.assertEqual(v.migration['healthy_days'], 0)
        v.day += 1
        self.healthy(v)
        v.businesses['mill']['machines'] = []
        v.businesses['mill']['hiring_surplus'] = 0
        evaluate(v)
        self.assertIn('funded vacancy', v.migration_status)
        self.assertEqual(v.migration['healthy_days'], 0)

    def test_departure_requires_persistent_hardship_preserves_founders(self):
        v = Village()
        for _ in range(5):
            self.healthy(v)
            evaluate(v)
            v.day += 1
        for day in range(3):
            v.households['home_4'].update(cash=0, bought=0)
            evaluate(v)
            if day < 2:
                self.assertIn('home_4', v.households)
            v.day += 1
        self.assertNotIn('home_4', v.households)
        self.assertEqual(len(v.citizens), 6)
        self.assertEqual(v.businesses['mill']['workers'], 1)
        self.assertIn('missed meals', v.migration_events[-1]['message'])
        loaded = Village(**asdict(v))
        self.assertEqual(len(loaded.citizens), 6)
        self.healthy(loaded)
        evaluate(loaded)
        self.assertEqual(loaded.migration['healthy_days'], 0)

    def test_existing_vacancy_does_not_create_worker_slot(self):
        v = Village()
        v.businesses['farm']['workers'] = 2
        for _ in range(5):
            self.healthy(v)
            evaluate(v)
            v.day += 1
        self.assertEqual(next(p for p in v.citizens if p['name'] == 'Rowan')['workplace'], 'farm')
        self.assertEqual(v.businesses['farm']['workers'], 2)
        self.assertFalse(v.migration['added_worker'])

    def test_natural_arrival_and_midday_save_reload_are_equivalent(self):
        from game import village_from_data
        from town import Town
        import json
        v = Village()
        for job in ('mill', 'bakery', 'vent', 'market', 'pump', 'sorter'):
            v.fulfill_job(job)
        v.rival_busy_until = 99
        town = Town()
        v.advance_day(town)
        v.update_life(town, 37)
        loaded = village_from_data(json.loads(json.dumps(asdict(v))))
        resumed = Town()
        for _ in range(30):
            v.advance_day(town)
            loaded.advance_day(resumed)
        self.assertEqual(asdict(v), asdict(loaded))
        self.assertEqual(len(v.citizens), 7)
        self.assertEqual(v.last_day_report['fed'], 4)
        rowan = next(p for p in loaded.citizens if p['name'] == 'Rowan')
        self.assertIn('position', rowan)
        self.assertIn('Rowan', resumed.people)
        loaded.talk_to('Rowan', 'family')
        self.assertEqual(rowan['relationships']['Boole'], 22)
        self.assertTrue(any('spoke with you' in line for line in rowan['memories']))

    def test_departure_and_rearrival_restore_slots_and_account_for_external_savings(self):
        def money(v):
            return v.coins + v.rival_cash + sum(f['cash'] for f in v.businesses.values()) + sum(h['cash'] for h in v.households.values())
        v = Village()
        for _ in range(5):
            self.healthy(v)
            before = money(v)
            evaluate(v)
            if 'home_4' in v.households:
                self.assertEqual(money(v) - before, v.migration_events[-1]['savings'])
            v.day += 1
        for _ in range(3):
            v.households['home_4'].update(cash=5, bought=0)
            before = money(v)
            evaluate(v)
            if 'home_4' not in v.households:
                self.assertEqual(money(v) - before, -5)
                self.assertEqual(v.migration_events[-1]['savings'], -5)
            v.day += 1
        self.assertEqual(v.businesses['mill']['workers'], 1)
        v = Village(**asdict(v))
        for _ in range(5):
            self.healthy(v)
            evaluate(v)
            v.day += 1
        self.assertEqual(v.businesses['mill']['workers'], 2)
        self.assertEqual(len(v.citizens), 7)
        self.assertEqual([e['kind'] for e in v.migration_events if e['kind'] != 'construction'], ['arrival', 'departure', 'arrival'])

    def test_old_save_defaults_without_retrospective_migration(self):
        v = Village(day=40)
        self.assertEqual(v.migration, {})
        self.assertNotIn('home_4', v.households)
        evaluate(v)
        self.assertNotIn('home_4', v.households)

    def test_finished_cottage_waits_for_food_and_survives_reload(self):
        v = Village()
        for _ in range(3):
            self.healthy(v)
            evaluate(v)
            v.day += 1
        self.assertEqual(v.migration['housing_stage'], 'construction')
        for _ in range(2):
            v.households['home_1']['bought'] = 0
            evaluate(v)
            v = Village(**asdict(v))
            v.day += 1
        self.assertEqual(v.migration['housing_stage'], 'ready')
        self.assertTrue(v.migration['cottage_built'])
        self.assertNotIn('home_4', v.households)
        self.assertIn('fed households', v.migration_status)
        for _ in range(3):
            self.healthy(v)
            evaluate(v)
            v.day += 1
        self.assertIn('home_4', v.households)
        self.assertEqual(len([event for event in v.migration_events if event['kind'] == 'construction']), 2)


if __name__ == '__main__':
    unittest.main()
