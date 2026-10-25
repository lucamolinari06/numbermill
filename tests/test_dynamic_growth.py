"""Reusable housing and businesses retain causes and cash across saved games."""
import json
import unittest
from dataclasses import asdict
from economy import Village
from migration import evaluate as review_homes, HOMES, NEWCOMERS, job_offer
from competition import evaluate as review_shops, KEY, CAPITAL, EXIT_DAYS, open_successor
from town import location_label


def cash(v):
    return v.coins + v.rival_cash + sum(f['cash'] for f in v.businesses.values()) + sum(h['cash'] for h in v.households.values())


class DynamicGrowthTests(unittest.TestCase):
    def healthy(self, v):
        for h in v.households.values():
            h.update(cash=100, bought=h['bread_need'])
        v.businesses['market']['stock']['bread'] = 5

    def test_three_homes_use_distinct_candidates_and_saved_profiles(self):
        v = Village()
        # Explicit funded vacancies, rather than speculative loss-making jobs.
        for key in ('farm', 'mill', 'fuel_yard'):
            v.businesses[key]['workers'] = 2
        for day in range(1, 19):
            v.day = day
            self.healthy(v)
            before = cash(v)
            review_homes(v)
            arrivals = [e for e in v.migration_events if e['day'] == day and e['kind'] == 'arrival']
            self.assertEqual(cash(v) - before, sum(e['savings'] for e in arrivals))
            v = Village(**json.loads(json.dumps(asdict(v))))
        names = [p['name'] for p in v.citizens if p['home'] in HOMES]
        self.assertEqual(names, ['Rowan', 'Saffron', 'Felix'])
        self.assertEqual(len(v.citizens), 9)
        self.assertEqual(len({p['aspiration'] for p in v.citizens if p['home'] in HOMES}), 3)
        self.assertTrue(all(v.migration.get('homes', {}).get(h, v.migration)['cottage_built'] for h in HOMES))
        self.assertGreater(len(NEWCOMERS), len(HOMES))

    def test_persistent_hardship_reuses_home_for_another_person(self):
        v = Village()
        v.businesses['fuel_yard']['workers'] = 2
        for day in range(1, 6):
            v.day = day
            self.healthy(v)
            review_homes(v)
        for day in range(6, 9):
            v.day = day
            v.households['home_4'].update(cash=0, bought=0)
            review_homes(v)
        self.assertNotIn('home_4', v.households)
        for day in range(9, 17):
            v.day = day
            self.healthy(v)
            review_homes(v)
        self.assertEqual(next(p['name'] for p in v.citizens if p['home'] == 'home_4'), 'Saffron')
        self.assertTrue({'Ada', 'Bram', 'Agnes', 'Dara', 'Mely', 'Luca'}.issubset(p['name'] for p in v.citizens))

    def test_apprentice_requires_profit_to_cover_a_whole_meal(self):
        v = Village()
        v.businesses['mill'].update(cash=1000, machines=['mill_controller'], hiring_surplus=7)
        self.assertEqual(job_offer(v), (None, False))
        v.businesses['fuel_yard'].update(cash=100, hiring_surplus=8)
        self.assertEqual(job_offer(v), ('fuel_yard', True))

    def test_long_closed_site_exits_then_changes_trade_and_owner(self):
        v = Village(day=20)
        profile = {'owner': 'Jun', 'kind': 'bakery', 'name': "Jun's East Bakery", 'capacity': 2, 'price': 6}
        open_successor(v, 0, profile)
        firm = v.businesses[KEY]
        firm.update(operating_state='paused', closed_days=EXIT_DAYS-1, owner_reinvested=True, owner_reserve=0)
        v.last_day_report = {'sold': 0, 'produced': {}}
        before = cash(v)
        review_shops(v)
        departure = v.competition_events[-1]
        self.assertEqual(departure['kind'], 'departure')
        self.assertEqual(cash(v) - before, departure['capital'])
        self.assertNotIn(KEY, v.businesses)
        self.assertEqual(location_label(v, KEY), '')
        v.businesses['mill']['machines'] = ['mill_controller']
        v.businesses['fuel_yard']['stock']['fuel'] = 1
        for day in range(21, 27):
            v.day = day
            before = cash(v)
            review_shops(v)
            if KEY in v.businesses:
                self.assertEqual(cash(v)-before, CAPITAL)
                break
            v = Village(**json.loads(json.dumps(asdict(v))))
        self.assertEqual(v.businesses[KEY]['kind'], 'fuel')
        self.assertEqual(v.businesses[KEY]['owner'], 'Anika')
        self.assertIn('Anika', location_label(v, KEY))
        self.assertNotIn('bakery', location_label(v, KEY).lower())

    def test_lower_price_wins_orders_then_remaining_suppliers_can_sell(self):
        from competition import ENTREPRENEURS
        v = Village()
        open_successor(v, 3, ENTREPRENEURS[3])
        cheap, established, market = v.businesses[KEY], v.businesses['bakery'], v.businesses['market']
        cheap['stock']['bread'] = established['stock']['bread'] = 2
        market['cash'] = 30
        self.assertEqual(v._buy_input(market, 'bread', 1, 6), 1)
        self.assertEqual((cheap['stock']['bread'], established['stock']['bread']), (1, 2))
        self.assertEqual(v._buy_input(market, 'bread', 3, 6), 3)
        self.assertEqual((cheap['stock']['bread'], established['stock']['bread']), (0, 0))
        self.assertEqual(market['cash'], 8)

    def test_expensive_parts_wait_for_cheaper_stock_to_sell(self):
        from competition import ENTREPRENEURS
        v = Village()
        open_successor(v, 2, ENTREPRENEURS[2])
        affordable = v.businesses[KEY]
        established = v.businesses['parts_shop']
        affordable['stock']['parts'] = 1
        established['stock']['parts'] = 3
        established['wholesale_price'] = 5
        buyer = v.businesses['market']
        buyer['cash'] = 20
        self.assertEqual(v._buy_input(buyer, 'parts', 1, 5), 1)
        self.assertEqual(established['stock']['parts'], 3)
        self.assertEqual(v._buy_input(buyer, 'parts', 1, 5), 1)
        self.assertEqual(established['stock']['parts'], 2)
        self.assertEqual(buyer['cash'], 11)

    def test_late_controllers_naturally_fund_all_homes_and_resume_after_save(self):
        from economy import CONTRACTS
        from town import Town
        v = Village()
        # Completed-installation fixture: no invented cash, stock, jobs or residents.
        for key, (business, machine, _) in CONTRACTS.items():
            if machine not in v.businesses[business]['machines']:
                v.businesses[business]['machines'].append(machine)
            v.offers.setdefault(key, {})['status'] = 'player'
        v = Village(**asdict(v))  # Normalize legacy machine flags in the fixture.
        town = Town()
        for _ in range(35):
            v.advance_day(town)
        self.assertEqual(len(v.citizens), 9)
        self.assertTrue(set(HOMES).issubset(v.households))
        self.assertEqual(v.last_day_report['fed'], 6)
        saved = Village(**json.loads(json.dumps(asdict(v))))
        resumed = Town()
        for _ in range(5):
            v.advance_day(town)
            saved.advance_day(resumed)
            self.assertEqual(v.last_day_report['fed'], 6)
            self.assertTrue(all(f['cash'] >= 0 for f in v.businesses.values()))
        self.assertEqual(asdict(v), asdict(saved))
        for p in v.citizens[6:]:
            self.assertEqual(v.last_day_report['paid'][p['name']], 8)
            self.assertGreaterEqual(v.last_day_report['worked'][p['name']], 18)

    def test_vacant_sites_have_no_assigned_labels(self):
        v = Village()
        for key in (*HOMES, KEY):
            self.assertEqual(location_label(v, key), '')


if __name__ == '__main__':
    unittest.main()
