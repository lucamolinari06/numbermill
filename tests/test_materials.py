from copy import deepcopy
from dataclasses import asdict
import json
import unittest

from economy import Village
from materials import (SHOPS, material_bill, material_status, buy_material,
                       advance_materials, deliver_project, reconcile_reservations)


def wealth(village):
    return (village.coins + village.rival_cash + sum(f['cash'] for f in village.businesses.values())
            + sum(h['cash'] for h in village.households.values()))


class MaterialTests(unittest.TestCase):
    def purchase_bill(self, village, key='mill'):
        for shop, item in SHOPS.items():
            for _ in range(material_bill(key).get(item['good'], 0)):
                buy_material(village, shop)

    def test_affordable_first_project_and_atomic_delivery(self):
        village = Village()
        total = wealth(village)
        self.purchase_bill(village)
        self.assertEqual(village.coins, 6)
        self.assertEqual(wealth(village), total)
        self.assertIn('Ready to deliver', material_status(village, 'mill'))
        ok, _ = deliver_project(village, 'mill')
        self.assertTrue(ok)
        self.assertEqual(village.coins, 30)
        self.assertTrue(all(value == 0 for value in village.material_inventory.values()))
        self.assertEqual(wealth(village), total)
        snapshot = deepcopy(asdict(village))
        self.assertFalse(deliver_project(village, 'mill')[0])
        self.assertEqual(asdict(village), snapshot)

    def test_failed_purchase_or_delivery_preserves_goods_and_money(self):
        village = Village()
        snapshot = deepcopy(asdict(village))
        self.assertFalse(deliver_project(village, 'mill')[0])
        self.assertEqual(asdict(village), snapshot)
        village.coins = 0
        snapshot = deepcopy(asdict(village))
        buy_material(village, 'toolmaker')
        self.assertEqual(asdict(village), snapshot)
        village.coins = 12
        self.purchase_bill(village)
        village.businesses['mill']['cash'] = 0
        snapshot = deepcopy(asdict(village))
        self.assertFalse(deliver_project(village, 'mill')[0])
        self.assertEqual(asdict(village), snapshot)

    def test_customer_advance_recovers_broke_player_without_minting_money(self):
        village = Village(coins=0)
        total = wealth(village)
        message = advance_materials(village, 'mill')
        self.assertIn('6c', message)
        self.assertEqual(village.material_inventory, {})
        self.assertEqual(village.material_advances['mill'], 6)
        self.assertEqual(village.businesses['mill']['cash'], 114)
        self.assertEqual(wealth(village), total)
        saved = Village(**json.loads(json.dumps(asdict(village))))
        advance_materials(saved, 'mill')
        self.assertEqual(saved.material_advances['mill'], 6)
        ok, message = deliver_project(saved, 'mill', 'license')
        self.assertTrue(ok)
        self.assertEqual(saved.coins, 6)
        self.assertEqual(saved.businesses['mill']['cash'], 108)
        self.assertEqual(saved.material_reservations, {})
        self.assertEqual(saved.material_advances, {})
        self.assertEqual(wealth(saved), total)

    def test_advance_validates_whole_order_and_customer_keeps_cancelled_stock(self):
        village = Village()
        village.businesses['toolmaker']['stock']['fittings'] = 0
        before = deepcopy(asdict(village))
        self.assertIn('lacks stock', advance_materials(village, 'mill'))
        self.assertEqual(asdict(village), before)
        village.businesses['toolmaker']['stock']['fittings'] = 3
        advance_materials(village, 'mill')
        total = wealth(village)
        village.offers['mill']['status'] = 'rival'
        reconcile_reservations(village)
        self.assertEqual(village.material_inventory, {})
        self.assertEqual(village.businesses['mill']['stock']['fittings'], 1)
        self.assertEqual(village.material_advances, {})
        self.assertEqual(wealth(village), total)

    def test_new_trades_restock_with_real_interfirm_purchases(self):
        village = Village()
        total = wealth(village)
        village.advance_day()
        self.assertGreater(village.businesses['toolmaker']['stock']['fittings'], 4)
        entries = village.trade_history[-2]['entries']
        self.assertTrue(any(e['from'] == "Iris's Timber Yard" and e['to'] == "Otto's Foundry" and e['coins'] > 0 for e in entries))
        self.assertTrue(any(e['from'] == "Otto's Foundry" and e['to'] == "Tess's Toolworks" and e['coins'] > 0 for e in entries))
        self.assertEqual(wealth(village), total)
        self.assertEqual(village.capacity('toolmaker'), 2)
        for _ in range(3):
            village.advance_day()
        self.assertLessEqual(village.businesses['toolmaker']['stock']['fittings'], 6)

    def test_old_business_saves_gain_new_shops_and_inventory_defaults(self):
        original = asdict(Village())
        for field in ('material_inventory', 'material_reservations', 'material_advances'):
            original.pop(field)
        for key in SHOPS:
            original['businesses'].pop(key)
        village = Village(**original)
        self.assertEqual(village.material_inventory, {})
        self.assertTrue(all(key in village.businesses for key in SHOPS))

    def test_conversation_topics_gain_trust_once_per_day_and_survive_reload(self):
        village = Village()
        person = next(p for p in village.citizens if p['name'] == 'Ada')
        village.talk_to('Ada', 'hopes')
        self.assertEqual(person['relationships']['Boole'], 22)
        village = Village(**json.loads(json.dumps(asdict(village))))
        village.talk_to('Ada', 'hopes')
        person = next(p for p in village.citizens if p['name'] == 'Ada')
        self.assertEqual(person['relationships']['Boole'], 22)
        village.talk_to('Ada', 'work')
        self.assertEqual(person['relationships']['Boole'], 24)
        village.talk_to('Ada', 'made-up-topic')
        self.assertEqual(person['relationships']['Boole'], 24)
