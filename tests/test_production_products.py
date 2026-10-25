"""Manufacturing chains, blueprint gates and bounded product sales."""
import json
import unittest
from dataclasses import asdict

from circuit import Circuit, edge_terminals
from economy import Village
import manufacturing as factory


class ProductTests(unittest.TestCase):
    def setUp(self):
        self.v = Village()
        self.v.coins = 500
        self.v.businesses['toolmaker']['stock']['fittings'] = 50
        self.v.material_inventory = {'metal': 30, 'fuel': 30, 'fittings': 30}

    def unit(self, kind):
        current = factory.state(self.v)
        okay, message = factory.buy_equipment(self.v, kind, (len(current['equipment']), 0))
        self.assertTrue(okay, message)
        return current['equipment'][-1]['id']

    def run_batch(self, machine):
        self.assertTrue(factory.start_batch(self.v, machine)[0])
        factory.update(self.v, 15)

    def test_chain_consumes_intermediates_and_yields_artifact_product(self):
        press, lathe = self.unit('press'), self.unit('lathe')
        self.run_batch(press)
        self.run_batch(lathe)
        self.assertFalse(factory.buy_equipment(self.v, 'precision_machine', (2, 0))[0])
        factory.unlock_equipment(self.v, 'precision_machine')
        factory.unlock_equipment(self.v, 'precision_machine')
        cutter = self.unit('precision_machine')
        self.run_batch(cutter)
        current = factory.state(self.v)
        self.assertEqual(current['unlocks'], ['precision_machine'])
        self.assertEqual(current['goods']['metal_plates'], 0)
        self.assertEqual(current['goods']['steam_valves'], 0)
        self.assertEqual(current['goods']['precision_gears'], 1)
        self.assertEqual(self.v.material_inventory, {'metal': 27, 'fuel': 27, 'fittings': 28})
        money = self.v.coins
        self.assertTrue(factory.sell_goods(self.v, 'export_precision_gears')[0])
        self.assertEqual(self.v.coins, money + 36)

    def test_exports_are_finite_saved_and_do_not_accumulate_missed_days(self):
        self.unit('press')
        factory.state(self.v)['goods']['metal_plates'] = 5
        for _ in range(2):
            self.assertTrue(factory.sell_goods(self.v, 'export_metal_plates')[0])
        self.assertFalse(factory.sell_goods(self.v, 'export_metal_plates')[0])
        loaded = Village(**json.loads(json.dumps(asdict(self.v))))
        self.assertFalse(factory.sell_goods(loaded, 'export_metal_plates')[0])
        loaded.day += 9
        offer = next(o for o in factory.offers(loaded) if o['id'] == 'export_metal_plates')
        self.assertEqual(offer['demand'], 2)
        self.assertEqual(factory.state(loaded)['exports']['metal_plates']['used'], 2)

    def test_storage_capacity_and_sensors_include_every_product(self):
        press = self.unit('press')
        rack = self.unit('storage')
        display = self.unit('display')
        current = factory.state(self.v)
        current['goods'].update(metal_plates=5, steam_valves=6)
        self.assertTrue(factory.start_batch(self.v, press)[0])
        self.assertEqual(factory.storage_values(self.v, rack)['free_space'], 0)
        self.assertFalse(factory.equipment_sell_quote(self.v, rack)['allowed'])
        self.assertEqual(factory.sensor_values(self.v, press)['stock'], 5)
        self.assertEqual(factory.storage_values(self.v, rack)['steam_valves'], 6)
        factory.configure_display(self.v, display, 'steam_valves')
        self.assertEqual(factory.display_reading(self.v, display)['value'], 6)

    def test_product_automation_needs_player_design_and_dispatch_selection(self):
        press = self.unit('press')
        self.assertFalse(factory.set_mode(self.v, press, True)[0])
        self.unit('controller')
        board = Circuit(terminals=edge_terminals(('A', 'B')))
        ports = {data['name']: pos for pos, data in board.terminals.items()}
        board.connect(ports['A'], ports['OUT'], 0)
        self.assertTrue(factory.install_controller(self.v, press, board)[0])
        self.assertTrue(factory.set_mode(self.v, press, True)[0])
        factory.update(self.v, 10)
        self.assertGreater(factory.state(self.v)['goods']['metal_plates'], 0)
        seller = self.unit('seller')
        self.assertFalse(factory.trade_once(self.v, seller)[0])
        self.assertTrue(factory.configure_trader(self.v, seller, product='metal_plates')[0])
        self.assertTrue(factory.trade_once(self.v, seller)[0])
        self.assertEqual(factory.state(self.v)['exports']['metal_plates']['delivered'], 1)

    def test_refinement_can_use_full_storage_without_double_reserving_inputs(self):
        factory.unlock_equipment(self.v, "precision_machine")
        unit = self.unit("precision_machine")
        current = factory.state(self.v)
        current["goods"].update(metal_plates=3, steam_valves=3)
        self.assertTrue(factory.start_batch(self.v, unit)[0])
        self.assertEqual(factory.total_stock(self.v), 4)
        factory.update(self.v, 10)
        self.assertEqual(factory.total_stock(self.v), 5)

    def test_partial_batch_round_trip_is_exact(self):
        unit = self.unit('lathe')
        factory.start_batch(self.v, unit)
        factory.update(self.v, 4.5)
        loaded = Village(**json.loads(json.dumps(asdict(self.v))))
        factory.update(self.v, 10.5)
        factory.update(loaded, 10.5)
        self.assertEqual(factory.state(loaded), factory.state(self.v))


if __name__ == '__main__':
    unittest.main()
