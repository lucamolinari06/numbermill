"""Observed triggers, atomic delivery, conserved funds and saved promises."""
import json
import unittest
from copy import deepcopy
from dataclasses import asdict
from economy import Village
from character_projects import DEFINITIONS, evaluate, accept, deliver, project_for


def ready():
    village = Village()
    village.businesses['east_bakery'] = {'name': "Jun's East Bakery", 'kind': 'bakery', 'cash': 0,
                                       'stock': {'bread': 0}, 'operating_state': 'paused'}
    village.businesses['parts_shop']['stock']['parts'] = 0
    village.last_day_report = {'day': 1, 'produced': {'bakery': 1},
                               'meals': {'home_1': {'bought': 0, 'needed': 1}}}
    evaluate(village)
    return village


def money(village):
    return village.coins + sum(firm['cash'] for firm in village.businesses.values())


class CharacterProjectTests(unittest.TestCase):
    def test_jun_promise_never_transfers_to_replacement_owner(self):
        village = ready()
        accept(village, 'recovery_salvage')
        village.material_inventory = DEFINITIONS['recovery_salvage']['bill'].copy()
        village.businesses['east_bakery']['owner'] = 'Anika'
        before = deepcopy(asdict(village))
        okay, message = deliver(village, 'recovery_salvage')
        self.assertFalse(okay)
        self.assertIn('Jun has left', message)
        self.assertEqual(asdict(village), before)
        village.character_projects = {}
        village.day += 1
        village.last_day_report['day'] = village.day
        evaluate(village)
        self.assertNotIn('recovery_salvage', village.character_projects)

    def test_projects_need_completed_observations_and_are_offered_once(self):
        village = Village()
        evaluate(village)
        self.assertFalse(village.character_projects)
        village.last_day_report = {'day': 1, 'produced': {'bakery': 4},
                                   'meals': {'home_1': {'bought': 1, 'needed': 1}}}
        village.businesses['parts_shop']['stock']['parts'] = 4
        evaluate(village)
        self.assertFalse(village.character_projects)
        village = ready()
        self.assertEqual(set(village.character_projects), set(DEFINITIONS))
        snapshot = asdict(village)
        evaluate(village)
        self.assertEqual(asdict(village), snapshot)

    def test_delivery_transforms_materials_and_conserves_cash_without_repeat_rewards(self):
        for key, definition in DEFINITIONS.items():
            with self.subTest(project=key):
                village = ready()
                village.businesses[definition['payer']]['cash'] = 100
                village.material_inventory = definition['bill'].copy()
                accept(village, key)
                cash_before = money(village)
                self.assertTrue(deliver(village, key)[0])
                self.assertEqual(money(village), cash_before)
                self.assertTrue(all(count == 0 for count in village.material_inventory.values()))
                snapshot = asdict(village)
                self.assertFalse(deliver(village, key)[0])
                self.assertEqual(asdict(village), snapshot)
                if key == 'pantry_shelf':
                    self.assertEqual(village.businesses['market']['pantry_protection'], 3)
                elif key == 'repair_kit':
                    self.assertEqual(village.businesses['parts_shop']['stock']['parts'], 3)
                else:
                    self.assertEqual(village.businesses['east_bakery']['cash'], 10)
                    self.assertEqual(village.businesses['parts_shop']['stock']['parts'], 2)
                    self.assertEqual(village.businesses['east_bakery']['operating_state'], 'paused')

    def test_missing_materials_or_customer_funds_never_consume_anything(self):
        village = ready()
        accept(village, 'pantry_shelf')
        village.material_inventory = {'timber': 2}
        snapshot = asdict(village)
        self.assertFalse(deliver(village, 'pantry_shelf')[0])
        self.assertEqual(asdict(village), snapshot)
        village.material_inventory['fittings'] = 1
        village.businesses['market']['cash'] = 7
        snapshot = asdict(village)
        self.assertFalse(deliver(village, 'pantry_shelf')[0])
        self.assertEqual(asdict(village), snapshot)

    def test_customer_commission_reservations_cannot_fund_personal_favors(self):
        village = ready()
        accept(village, 'repair_kit')
        village.material_reservations = {'mill': {'metal': 20, 'fittings': 20}}
        snapshot = asdict(village)
        self.assertFalse(deliver(village, 'repair_kit')[0])
        self.assertEqual(asdict(village), snapshot)

    def test_acceptance_and_completion_survive_save_and_build_one_relationship_memory(self):
        village = ready()
        accept(village, 'repair_kit')
        # Remove this synthetic entrant: production-model validation is tested elsewhere.
        del village.businesses['east_bakery']
        loaded = Village(**json.loads(json.dumps(asdict(village))))
        self.assertEqual(project_for(loaded, 'Luca')['status'], 'accepted')
        self.assertIsNone(project_for(loaded, 'Ada'))
        loaded.material_inventory = DEFINITIONS['repair_kit']['bill'].copy()
        loaded.businesses['parts_shop']['cash'] = 100
        luca = next(p for p in loaded.citizens if p['name'] == 'Luca')
        before = luca['relationships'].get('Boole', 20)
        self.assertTrue(deliver(loaded, 'repair_kit')[0])
        self.assertEqual(luca['relationships']['Boole'], before + 8)
        self.assertIn('Nothing worth wasting', luca['memories'][-1])
        reloaded = Village(**json.loads(json.dumps(asdict(loaded))))
        self.assertEqual(project_for(reloaded, 'Luca')['status'], 'completed')
        self.assertFalse(deliver(reloaded, 'repair_kit')[0])

    def test_old_save_gets_no_projects_or_invented_history(self):
        data = asdict(Village())
        data.pop('character_projects')
        data.pop('character_project_review_day')
        loaded = Village(**data)
        self.assertFalse(loaded.character_projects)
        self.assertEqual(loaded.character_project_review_day, 0)
