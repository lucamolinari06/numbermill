"""Owner decisions respond to completed trading evidence, not wall-clock calls."""
import json
import unittest
from dataclasses import asdict
from competition import evaluate, KEY
from daily_life import produce, state
from economy import Village
from test_competition import prepared, enter


class LifecycleTests(unittest.TestCase):
    def closed_shop(self):
        v = prepared()
        firm = enter(v)
        for day in range(4, 7):
            v.day = day
            v.daily_life = {'produced': {}, 'reasons': {}}
            v.daily_trades = []
            evaluate(v)
        self.assertEqual(firm['operating_state'], 'paused')
        return v, firm

    def test_three_bad_days_close_but_inventory_can_be_liquidated(self):
        v, firm = self.closed_shop()
        self.assertEqual(len([e for e in v.competition_events if e['kind'] == 'closure']), 1)
        self.assertEqual(v.capacity(KEY), 0)
        self.assertEqual(v.capacity(KEY, nominal=True), 2)
        v.daily_life = {}
        state(v)['elapsed'] = 80
        v.businesses['mill']['stock']['flour'] = 10
        before = firm['cash']
        produce(v)
        self.assertNotIn(KEY, v.daily_life['produced'])
        self.assertEqual(firm['cash'], before)
        firm['stock']['bread'] = 1
        v.businesses['bakery']['stock']['bread'] = 0
        self.assertEqual(v._buy_input(v.businesses['market'], 'bread', 1, 7), 1)
        self.assertEqual(firm['cash'], before + 6)

    def test_reopening_waits_two_days_and_uses_outside_reserve_only_once(self):
        v, firm = self.closed_shop()
        firm['cash'] = 0
        v.day = 7
        evaluate(v)
        self.assertEqual(firm['recovery_days'], 1)
        self.assertEqual(firm['cash'], 0)
        saved = Village(**json.loads(json.dumps(asdict(v))))
        saved.day = 8
        evaluate(saved)
        firm = saved.businesses[KEY]
        self.assertEqual(firm['operating_state'], 'open')
        self.assertEqual(firm['cash'], 20)
        self.assertEqual(firm['owner_reserve'], 0)
        investments = [t for t in saved.daily_trades if t['good'] == 'owner capital']
        self.assertEqual(len(investments), 1)
        self.assertTrue(investments[0]['external'])
        for day in range(9, 12):
            saved.day = day
            saved.daily_trades = []
            evaluate(saved)
        firm['cash'] = 0
        for day in range(12, 17):
            saved.day = day
            evaluate(saved)
        self.assertEqual(firm['cash'], 0)
        self.assertEqual(firm['operating_state'], 'paused')
        self.assertIn('reserve already spent', firm['owner_decision'])

    def test_supply_or_demand_shortfall_resets_recovery(self):
        v, firm = self.closed_shop()
        for day, sold in ((7, 3), (8, 0), (9, 3)):
            v.day = day
            v.last_day_report['sold'] = sold
            evaluate(v)
        self.assertEqual(firm['operating_state'], 'paused')
        self.assertEqual(firm['recovery_days'], 1)
        v.day = 10
        evaluate(v)
        self.assertEqual(firm['operating_state'], 'open')
        self.assertFalse(firm['owner_reinvested'])

    def test_old_shop_starts_hardship_observation_without_retroactive_closure(self):
        v = prepared()
        firm = enter(v)
        for key in ('operating_state', 'hardship_days', 'recovery_days', 'review_cash', 'owner_reserve', 'owner_reinvested'):
            firm.pop(key)
        v.day = 100
        evaluate(v)
        self.assertEqual(firm['operating_state'], 'open')
        self.assertEqual(firm['hardship_days'], 1)
        evaluate(v)
        self.assertEqual(firm['hardship_days'], 1)


if __name__ == '__main__':
    unittest.main()
