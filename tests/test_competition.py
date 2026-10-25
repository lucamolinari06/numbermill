"""Evidence-based entry, actual wholesale transfers and save continuity."""
import json
import unittest
from copy import deepcopy
from dataclasses import asdict
from competition import evaluate, KEY, CAPITAL
from daily_life import state, produce, SHIFT_SECONDS
from economy import Village


def prepared():
    village = Village()
    village.households['home_4'] = deepcopy(village.households['home_1'])
    village.last_day_report = {'sold': 3, 'produced': {'mill': 4}}
    return village


def enter(village):
    for day in range(1, 4):
        village.day = day
        evaluate(village)
    return village.businesses[KEY]


class CompetitionTests(unittest.TestCase):
    def test_entry_uses_three_observed_days_and_explicit_outside_capital(self):
        v = prepared()
        before = sum(f['cash'] for f in v.businesses.values())
        evaluate(v)
        evaluate(v)
        self.assertEqual(v.competition['qualifying_days'], 1)
        self.assertNotIn(KEY, v.businesses)
        v.day = 2
        evaluate(v)
        saved = Village(**json.loads(json.dumps(asdict(v))))
        saved.day = 3
        evaluate(saved)
        self.assertEqual(sum(f['cash'] for f in saved.businesses.values()), before + CAPITAL)
        self.assertEqual(saved.businesses[KEY]['stock']['bread'], 0)
        self.assertTrue(saved.businesses[KEY]['owner_operated'])
        self.assertTrue(saved.daily_trades[-1]['external'])
        evaluate(saved)
        self.assertEqual(len(saved.competition_events), 1)

    def test_struggling_town_or_old_save_cannot_infer_qualifying_history(self):
        for sold, flour, cash in [(0, 4, 100), (3, 0, 100), (3, 4, 0)]:
            v = prepared()
            v.last_day_report = {'sold': sold, 'produced': {'mill': flour}}
            v.businesses['mill']['stock']['flour'] = 0
            v.businesses['market']['cash'] = cash
            for day in range(40, 45):
                v.day = day
                evaluate(v)
            self.assertNotIn(KEY, v.businesses)
            self.assertEqual(v.competition['qualifying_days'], 0)
        v = prepared()
        v.day = 100
        evaluate(v)
        self.assertNotIn(KEY, v.businesses)
        self.assertEqual(v.competition['qualifying_days'], 1)

    def test_market_orders_rotate_and_respect_prices_cash_and_producers(self):
        v = prepared()
        newcomer = enter(v)
        incumbent, market = v.businesses['bakery'], v.businesses['market']
        incumbent['stock']['bread'] = newcomer['stock']['bread'] = 5
        market['cash'] = 24
        for _ in range(4):
            self.assertEqual(v._buy_input(market, 'bread', 1, 6), 1)
        self.assertEqual((incumbent['stock']['bread'], newcomer['stock']['bread']), (3, 3))
        self.assertEqual(market['cash'], 0)
        self.assertEqual(v._buy_input(market, 'bread', 1, 6), 0)
        market['stock']['bread'] = 100
        incumbent['stock']['bread'] = newcomer['stock']['bread'] = 0
        newcomer['cash'] = 100
        self.assertEqual(v._buy_input(newcomer, 'bread', 2, 7), 0)
        incumbent['stock']['bread'] = 1
        incumbent['wholesale_price'] = 9
        newcomer['cash'] = 8
        self.assertEqual(v._buy_input(newcomer, 'bread', 1, 7), 0)
        newcomer['cash'] = 9
        self.assertEqual(v._buy_input(newcomer, 'bread', 1, 7), 1)
        self.assertEqual(newcomer['cash'], 0)

    def test_owner_shift_consumes_paid_flour_and_stops_at_capacity(self):
        v = prepared()
        firm = enter(v)
        life = state(v)
        life['elapsed'] = SHIFT_SECONDS
        v.businesses['mill']['stock']['flour'] = 10
        before = v.businesses['mill']['cash']
        produce(v)
        produce(v)
        self.assertEqual(life['produced'][KEY], 2)
        self.assertEqual(firm['cash'], CAPITAL - 8)
        self.assertEqual(v.businesses['mill']['cash'], before + 8)
        self.assertNotIn('Jun', life['paid'])
        life['produced'][KEY] = 0
        firm['cash'] = 0
        produce(v)
        self.assertEqual(life['produced'][KEY], 0)
        self.assertEqual(firm['cash'], 0)

    def test_natural_growth_competes_and_survives_saved_continuation(self):
        v = Village()
        for job in ('mill', 'bakery', 'vent', 'market', 'pump', 'sorter'):
            v.fulfill_job(job)
        v.rival_busy_until = 999
        for _ in range(30):
            v.advance_day()
        self.assertIn(KEY, v.businesses)
        self.assertIn('home_4', v.households)
        saved = Village(**json.loads(json.dumps(asdict(v))))
        for _ in range(20):
            v.advance_day()
            saved.advance_day()
            for firm in v.businesses.values():
                self.assertGreaterEqual(firm['cash'], 0)
                self.assertTrue(all(count >= 0 for count in firm['stock'].values()))
            self.assertLessEqual(v.businesses[KEY]['stock']['bread'], 4)
            self.assertLessEqual(v.businesses['bakery']['stock']['bread'], 4)
        self.assertEqual(asdict(v), asdict(saved))
        self.assertGreater(v.businesses[KEY]['cash'], CAPITAL)
        self.assertGreater(v.businesses['bakery']['cash'], 0)
        sellers = {t['from'] for day in v.trade_history for t in day['entries'] if t['to'] == v.businesses['market']['name'] and t['good'] == 'bread'}
        self.assertIn(v.businesses[KEY]['name'], sellers)
        self.assertIn(v.businesses['bakery']['name'], sellers)


if __name__ == '__main__':
    unittest.main()


