"""Integration checks for attendance, purchases, and the shared economic clock."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from daily_life import DAY_SECONDS, SHIFT_SECONDS, state, pay_wages, produce, shop
from economy import Village
from game import Game, village_from_data
from town import Town, LOCATIONS


def money(v):
    return v.coins + v.rival_cash + sum(f['cash'] for f in v.businesses.values()) + sum(h['cash'] for h in v.households.values())


class DailyLifeTests(unittest.TestCase):
    def test_social_and_rest_rewards_wait_for_completed_arrival(self):
        from citizens import update_activity
        v = Village()
        mely = next(p for p in v.citizens if p['name'] == 'Mely')
        home = v.households[mely['home']]
        state(v)['worked']['Mely'] = SHIFT_SECONDS
        home['bought'] = home['bread_need']
        mely.update(activity='spending time with spouse', destination=mely['home'],
                    last_reason='Wants time with Luca', social_need=80, energy=90)
        before = mely['relationships']['Luca']
        update_activity(mely, home, v, 30, arrived=False)
        self.assertEqual(mely['relationships']['Luca'], before)
        update_activity(mely, home, v, 1, arrived=True)
        self.assertEqual(mely['relationships']['Luca'], before)
        update_activity(mely, home, v, 30, arrived=True)
        self.assertEqual(mely['relationships']['Luca'], before + 1)
        self.assertEqual(mely['activity'], 'spending time with spouse')
        mely.update(activity='resting', visit_seconds=0, last_reason='Starting the day', energy=10)
        update_activity(mely, home, v, 0, arrived=True)
        self.assertEqual(mely['energy'], 10)

    def test_travel_does_not_earn_wages_but_arrival_does(self):
        v, t = Village(), Town()
        ada = v.citizens[0]
        ada.update(activity='working', destination='farm', last_reason='Finishing shift')
        v.update_life(t, .5)
        self.assertEqual(state(v)['worked'].get('Ada', 0), 0)
        t.people['Ada'] = list(LOCATIONS['farm'])
        t.routes['Ada'] = []
        t.route_targets['Ada'] = LOCATIONS['farm']
        v.update_life(t, .5)
        self.assertEqual(state(v)['worked']['Ada'], .5)
        v.update_life(t, 5)
        self.assertGreater(state(v)['paid']['Ada'], 0)

    def test_partial_attendance_caps_goods_and_pay_and_preserves_money(self):
        v = Village()
        before = money(v)
        life = state(v)
        life['worked']['Ada'] = SHIFT_SECONDS / 2
        produce(v)
        pay_wages(v)
        self.assertEqual(life['produced']['farm'], 2)
        self.assertEqual(life['paid']['Ada'], 2)
        self.assertNotIn('mill', life['produced'])
        produce(v)
        pay_wages(v)
        self.assertEqual(life['produced']['farm'], 2)
        self.assertEqual(life['paid']['Ada'], 2)
        self.assertEqual(money(v), before)

    def test_arrived_shopper_transfers_cash_and_keeps_player_loaf(self):
        v, t = Village(), Town()
        bram = next(p for p in v.citizens if p['name'] == 'Bram')
        bram.update(activity='seeking food', destination='market', last_reason='Shopping')
        v.businesses['market']['stock']['bread'] = 2
        initial = deepcopy(v.households[bram['home']])
        before = money(v)
        v.update_life(t, .5)
        self.assertEqual(v.households[bram['home']]['bought'], 0)
        group = sorted(p['name'] for p in v.citizens if p['destination'] == 'market')
        center = LOCATIONS['market']
        target = (center[0] + (group.index('Bram') - (len(group) - 1) / 2) * 60,
                  center[1] + (20 if len(group) > 1 else 0))
        t.people['Bram'] = list(target)
        t.routes['Bram'] = []
        t.route_targets['Bram'] = target
        v.update_life(t, .5)
        home = v.households[bram['home']]
        self.assertEqual(home['bought'], 1)
        self.assertEqual(home['cash'], initial['cash'] - v.bread_price)
        self.assertEqual(state(v)['purchases'][0]['person'], 'Bram')
        self.assertFalse(shop(v, bram))
        other = next(p for p in v.citizens if p['home'] != bram['home'])
        self.assertFalse(shop(v, other))
        self.assertEqual(v.businesses['market']['stock']['bread'], 1)
        self.assertEqual(money(v), before)

    def test_unaffordable_food_and_wages_do_not_create_money(self):
        v = Village()
        p = v.citizens[0]
        home = v.households[p['home']]
        home['cash'] = 0
        before = deepcopy(v.businesses['market'])
        self.assertFalse(shop(v, p))
        self.assertEqual(v.businesses['market'], before)
        state(v)['worked'][p['name']] = SHIFT_SECONDS
        v.businesses['farm']['cash'] = 1
        pay_wages(v)
        self.assertEqual(state(v)['paid'][p['name']], 1)
        v.businesses['farm']['cash'] = 3
        pay_wages(v)
        pay_wages(v)
        self.assertEqual(state(v)['paid'][p['name']], 4)
        self.assertEqual(v.businesses['farm']['cash'], 0)

    def test_day_caps_and_settles_only_once_without_duplicate_trade_records(self):
        v, t = Village(), Town()
        before = money(v)
        v.update_life(t, DAY_SECONDS)
        snapshot = asdict(v)
        v.update_life(t, DAY_SECONDS * 2)
        self.assertEqual(asdict(v), snapshot)
        self.assertEqual(money(v), before)
        self.assertEqual(state(v)['elapsed'], DAY_SECONDS)
        self.assertTrue(all(s <= SHIFT_SECONDS for s in state(v)['worked'].values()))
        self.assertEqual(v.daily_trades, v.trade_history[-1]['entries'])
        self.assertEqual(len(state(v)['purchases']), 3)
        self.assertTrue(all('person' in e for e in v.daily_trades if e['good'] == 'work'))

    def test_fast_forward_equals_watching_the_day_and_resets_meals(self):
        watched, fast = Village(), Village()
        town = Town()
        for _ in range(1800):
            watched.update_life(town, .1)
        watched.advance_day(town)
        fast.advance_day()
        a, b = asdict(watched), asdict(fast)
        # Fractional input accumulation may retain only floating point roundoff.
        self.assertEqual(a, b)
        self.assertEqual(watched.day, 2)
        self.assertEqual(watched.last_day_report['day'], 1)
        self.assertEqual(watched.last_day_report['fed'], 3)
        self.assertTrue(all(h['bought'] == 0 for h in watched.households.values()))

    def test_midday_json_reload_continues_same_routes_goods_and_pay(self):
        uninterrupted, t = Village(), Town()
        uninterrupted.update_life(t, 47.3)
        loaded = village_from_data(json.loads(json.dumps(asdict(uninterrupted))))
        uninterrupted.update_life(t, 132.7)
        loaded.update_life(Town(), 132.7)
        self.assertEqual(asdict(uninterrupted), asdict(loaded))

    def test_legacy_save_is_already_settled_and_cannot_pay_twice(self):
        old = asdict(Village())
        old.pop('daily_life')
        v = village_from_data(old)
        snapshot = asdict(v)
        v.update_life(Town(), 90)
        self.assertEqual(asdict(v), snapshot)
        v.advance_day()
        self.assertEqual(v.day, 2)
        self.assertEqual(state(v)['worked'], {})

    def test_economy_runs_the_same_in_workshop_and_town_and_saves_clock(self):
        with tempfile.TemporaryDirectory() as directory, patch('game.SAVES_DIR', Path(directory)):
            town, workshop = Game(), Game()
            town.scene, workshop.scene = 'town', 'workshop'
            town.update(35.3)
            workshop.update(35.3)
            self.assertEqual(asdict(town.village), asdict(workshop.village))
            workshop.current_slot = 1
            workshop.save_game()
            loaded = Game()
            loaded.start_slot(1)
            self.assertEqual(loaded.village.daily_life, workshop.village.daily_life)
            self.assertEqual(loaded.village.citizens, workshop.village.citizens)

    def test_missing_worker_limits_flour_and_names_attendance_bottleneck(self):
        v = Village()
        v.citizens[1]['workplace'] = 'farm'
        v.update_life(Town(), DAY_SECONDS)
        self.assertEqual(state(v)['produced'].get('mill', 0), 0)
        self.assertEqual(state(v)['reasons']['mill'], 'No work attendance yet')
        self.assertLess(state(v)['produced']['bakery'], v.capacity('bakery'))

    def test_mill_upgrade_improves_food_price_and_household_outcomes(self):
        slow, improved = Village(), Village()
        improved.complete_mill_job()
        for v in (slow, improved):
            v.rival_busy_until = 99
            for _ in range(6):
                v.advance_day()
        self.assertLess(slow.last_day_report['fed'], improved.last_day_report['fed'])
        self.assertEqual(improved.last_day_report['fed'], 3)
        self.assertNotIn('home_4', improved.households)
        self.assertFalse(any(e['kind'] == 'arrival' for e in improved.migration_events))
        self.assertGreater(slow.bread_price, improved.bread_price)
        self.assertGreater(sum(h['missed_meals'] for h in slow.households.values()),
                           sum(h['missed_meals'] for h in improved.households.values()))
        self.assertTrue(any('Mill sent 4 flour' in line for line in improved.last_day_report['causes']))

    def test_royalties_and_service_only_charge_once_per_calendar_day(self):
        v, t = Village(), Town()
        v.complete_mill_job('license')
        v.toggle_service()
        v.advance_day(t)
        earned = v.coins
        self.assertEqual(v.licenses['mill']['total_paid'], 2)
        self.assertEqual(v.service_days, 1)
        v.update_life(t, 40)
        self.assertEqual(v.coins, earned)
        self.assertEqual(v.licenses['mill']['total_paid'], 2)
        self.assertEqual(v.service_days, 1)


if __name__ == '__main__':
    unittest.main()
