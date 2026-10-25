"""The player can build a livelihood with ordinary town stocks and starting cash."""
import unittest

from circuit import Circuit, edge_terminals
from daily_life import update_continuous, DAY_SECONDS
from economy import Village
from town import Town
import manufacturing as factory


class ManufacturingFlowTests(unittest.TestCase):
    def setUp(self):
        self.village = Village()
        self.town = Town()

    def advance(self, seconds):
        update_continuous(self.village, self.town, seconds)

    def supplies(self):
        for good, count in factory.RECIPE.items():
            for _ in range(count):
                for attempt in range(13):
                    okay, message = factory.buy_supply(self.village, good)
                    if okay:
                        break
                    self.assertGreaterEqual(self.village.coins, factory.SUPPLIES[good]['price'], message)
                    self.advance(15)
                self.assertTrue(okay, message)

    def sell(self):
        for _ in range(13):
            offer = next((item for item in factory.offers(self.village) if item['demand']), None)
            if offer:
                okay, message = factory.sell_goods(self.village, offer['id'])
                self.assertTrue(okay, message)
                return
            self.advance(DAY_SECONDS)
        self.fail('No real customer returned within twelve days: ' + str(factory.offers(self.village)))

    def test_initial_twelve_coins_fund_first_machine_and_profitable_sale(self):
        village = self.village
        self.assertEqual(village.coins, 12)
        self.assertTrue(factory.buy_equipment(village, 'bench', (1, 1))[0])
        machine = factory.state(village)['equipment'][0]['id']
        self.supplies()
        self.assertEqual(village.coins, 0)
        self.assertTrue(factory.start_batch(village, machine)[0])
        self.advance(factory.BATCH_SECONDS)
        # A first sale must be available now, without a commission or gift.
        offer = next((item for item in factory.offers(village) if item['demand']), None)
        self.assertIsNotNone(offer, factory.offers(village))
        self.assertTrue(factory.sell_goods(village, offer['id'])[0])
        self.assertEqual(village.coins, factory.KIT_PRICE)
        self.assertGreater(factory.KIT_PRICE, sum(factory.SUPPLIES[g]['price'] * n for g, n in factory.RECIPE.items()))
        self.assertFalse(village.mill_machine)
        self.assertEqual(factory.state(village)['sold'], 1)

    def test_manufacturing_profit_can_buy_and_run_first_controller(self):
        village = self.village
        self.assertTrue(factory.buy_equipment(village, 'bench', (1, 1))[0])
        machine = factory.state(village)['equipment'][0]['id']
        for _ in range(3):
            self.supplies()
            self.assertTrue(factory.start_batch(village, machine)[0])
            self.advance(factory.BATCH_SECONDS)
            self.sell()
        okay, message = factory.buy_equipment(village, 'controller', (2, 1))
        if not okay and 'fittings' in message:
            self.advance(DAY_SECONDS)
            okay, message = factory.buy_equipment(village, 'controller', (2, 1))
        self.assertTrue(okay, message)
        self.supplies()
        circuit = Circuit(terminals=edge_terminals(('A', 'B')))
        ports = {port['name']: pos for pos, port in circuit.terminals.items()}
        circuit.connect(ports['A'], ports['OUT'], 0)
        self.assertTrue(factory.install_controller(village, machine, circuit, inputs={'A': 'ready', 'B': 'stock'})[0])
        self.assertTrue(factory.set_mode(village, machine, True)[0])
        self.advance(factory.BATCH_SECONDS + 3)
        self.assertEqual(factory.state(village)['auto_produced'], 1)
        self.assertEqual(village.arithmetic_unlocks, [])
        self.assertFalse(village.mill_machine)

    def test_customers_return_without_unlocking_regional_contracts(self):
        village = self.village
        self.assertTrue(factory.buy_equipment(village, 'bench', (1, 1))[0])
        machine = factory.state(village)['equipment'][0]['id']
        for _ in range(7):
            self.supplies()
            self.assertTrue(factory.start_batch(village, machine)[0])
            self.advance(factory.BATCH_SECONDS)
            self.sell()
        self.assertEqual(factory.state(village)['sold'], 7)
        self.assertFalse(village.mill_machine)
        self.assertGreater(village.coins, 12)

    def test_twenty_days_of_manufacturing_fund_real_equipment_without_commissions(self):
        village = self.village
        self.assertTrue(factory.buy_equipment(village, 'bench', (1, 1))[0])
        machine = factory.state(village)['equipment'][0]['id']
        bought = set()
        for day in range(20):
            self.supplies()
            bench = factory.get_machine(village, machine)
            if bench['mode'] == 'manual':
                self.assertTrue(factory.start_batch(village, machine)[0])
            self.advance(factory.BATCH_SECONDS + 3)
            self.assertGreater(factory.state(village)['goods']['repair_kits'], 0)
            self.sell()
            # Preserve the next recipe's eight coins when investing profits.
            for kind, pos in (('controller', (2, 1)), ('display', (3, 1)), ('storage', (4, 1))):
                if kind not in bought and village.coins >= 8 + factory.equipment_price(village, kind):
                    okay, message = factory.buy_equipment(village, kind, pos)
                    if okay:
                        bought.add(kind)
                        if kind == 'controller':
                            circuit = Circuit(terminals=edge_terminals(('A', 'B')))
                            ports = {port['name']: pos for pos, port in circuit.terminals.items()}
                            circuit.connect(ports['A'], ports['OUT'], 0)
                            self.assertTrue(factory.install_controller(village, machine, circuit)[0])
                            self.assertTrue(factory.set_mode(village, machine, True)[0])
            village.advance_day(self.town)
        self.assertEqual(factory.state(village)['sold'], 20)
        self.assertGreater(factory.state(village)['auto_produced'], 10)
        self.assertEqual(bought, {'controller', 'display', 'storage'})
        self.assertGreaterEqual(village.coins, 8)
        self.assertEqual(village.compute_earned, 0)
        self.assertEqual(village.service_earned, 0)
        self.assertFalse(any(offer.get('status') == 'player' for offer in village.offers.values()))


if __name__ == '__main__':
    unittest.main()
