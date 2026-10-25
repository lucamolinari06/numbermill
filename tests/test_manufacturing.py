"""Production and controller behavior conserve stock, money and saved time."""
import json
import unittest
from copy import deepcopy
from dataclasses import asdict

from economy import Village
from circuit import Circuit, Part, edge_terminals
import manufacturing as factory


def cash(village):
    return village.coins + sum(firm["cash"] for firm in village.businesses.values())


def ready_controller():
    circuit = Circuit(terminals=edge_terminals(("A", "B")))
    ports = {p["name"]: pos for pos, p in circuit.terminals.items()}
    circuit.connect(ports["A"], ports["OUT"], 0)
    return circuit


class ManufacturingTests(unittest.TestCase):
    def setUp(self):
        self.village = Village()

    def bench(self, position=(1, 1)):
        ok, message = factory.buy_equipment(self.village, "bench", position)
        self.assertTrue(ok, message)
        return factory.state(self.village)["equipment"][-1]["id"]

    def supplies(self, count=1):
        for good in factory.RECIPE:
            ok, message = factory.buy_supply(self.village, good, count)
            self.assertTrue(ok, message)

    def test_starting_twelve_coins_buy_bench_inputs_and_profitable_goods(self):
        v = self.village
        before = cash(v)
        bench = self.bench()
        self.supplies()
        self.assertEqual(v.coins, 0)
        self.assertEqual(cash(v), before)
        self.assertTrue(factory.start_batch(v, bench)[0])
        self.assertEqual(v.material_inventory, {"metal": 0, "fittings": 0, "fuel": 0})
        factory.update(v, 11.5)
        self.assertEqual(factory.state(v)["goods"]["repair_kits"], 0)
        factory.update(v, .5)
        self.assertEqual(factory.state(v)["goods"]["repair_kits"], 1)
        base = v.capacity("foundry")
        self.assertTrue(factory.sell_goods(v, "foundry")[0])
        self.assertEqual(v.coins, 10)
        self.assertEqual(cash(v), before)
        self.assertEqual(v.capacity("foundry"), base + 2)
        self.assertEqual(factory.state(v)["sold"], 1)
        self.assertEqual(v.daily_trades[-1]["coins"], 10)

    def test_failed_purchases_and_starts_do_not_spend(self):
        v = self.village
        bench = self.bench()
        before = deepcopy(asdict(v))
        self.assertFalse(factory.buy_supply(v, "fuel", 100)[0])
        self.assertFalse(factory.buy_supply(v, "metal", -1)[0])
        self.assertFalse(factory.buy_equipment(v, "bench", (1, 1))[0])
        self.assertFalse(factory.buy_equipment(v, "bench", (-1, 2))[0])
        self.assertEqual(asdict(v), before)
        self.assertFalse(factory.start_batch(v, bench)[0])
        self.assertEqual(v.coins, before["coins"])
        self.assertEqual(v.material_inventory, {})

    def test_starter_bench_is_once_and_later_equipment_uses_fittings(self):
        v = self.village
        self.bench()
        self.assertEqual(factory.equipment_price(v, "bench"), 24)
        v.coins = 100
        stock = v.businesses["toolmaker"]["stock"]["fittings"]
        self.bench((2, 1))
        self.assertEqual(v.businesses["toolmaker"]["stock"]["fittings"], stock - 2)
        self.assertTrue(factory.move_equipment(v, 1, (3, 1))[0])
        self.assertFalse(factory.move_equipment(v, 1, (2, 1))[0])
        self.assertEqual(factory.get_machine(v, 1)["pos"], [3, 1])

    def test_multiple_running_benches_reserve_output_space(self):
        v = self.village
        first = self.bench()
        v.coins = 100
        second = self.bench((2, 1))
        v.material_inventory = {good: 10 for good in factory.RECIPE}
        factory.state(v)["goods"]["repair_kits"] = 5
        self.assertTrue(factory.start_batch(v, first)[0])
        stock = v.material_inventory.copy()
        self.assertFalse(factory.start_batch(v, second)[0])
        self.assertEqual(v.material_inventory, stock)
        factory.update(v, 12)
        self.assertEqual(factory.state(v)["goods"]["repair_kits"], 6)
        self.assertTrue(factory.buy_equipment(v, "storage", (3, 1))[0])
        self.assertEqual(factory.stock_capacity(v), 12)
        self.assertTrue(factory.start_batch(v, second)[0])

    def test_auto_controller_really_permits_and_denies_starts(self):
        v = self.village
        bench = self.bench()
        v.coins = 100
        v.material_inventory = {good: 10 for good in factory.RECIPE}
        self.assertFalse(factory.install_controller(v, bench, ready_controller())[0])
        self.assertTrue(factory.buy_equipment(v, "controller", (2, 1))[0])
        self.assertTrue(factory.install_controller(v, bench, ready_controller())[0])
        self.assertTrue(factory.set_mode(v, bench, True)[0])
        factory.update(v, 28)
        self.assertGreaterEqual(factory.state(v)["auto_produced"], 1)
        # Manual mode prevents new starts but lets the existing batch finish.
        factory.set_mode(v, bench, False)
        factory.update(v, 20)
        count = factory.state(v)["produced"]
        factory.update(v, 20)
        self.assertEqual(factory.state(v)["produced"], count)
        blank = Circuit(terminals=edge_terminals(("A", "B")))
        factory.install_controller(v, bench, blank)
        factory.set_mode(v, bench, True)
        factory.update(v, 20)
        self.assertEqual(factory.state(v)["produced"], count)

    def test_counter_memory_fractional_time_and_midbatch_save_continue_exactly(self):
        v = self.village
        bench = self.bench()
        v.coins = 100
        v.material_inventory = {good: 20 for good in factory.RECIPE}
        factory.buy_equipment(v, "controller", (2, 1))
        circuit = ready_controller()
        circuit.set_part((6, 3), Part("COUNTER"))
        positions = {p["name"]: pos for pos, p in circuit.terminals.items()}
        circuit.connect(positions["B"], (6, 3), 0)
        self.assertTrue(factory.install_controller(v, bench, circuit, {"A": "ready", "B": "pulse"})[0])
        factory.set_mode(v, bench, True)
        factory.update(v, 15.3)
        loaded = Village(**json.loads(json.dumps(asdict(v))))
        factory.update(v, 21.7)
        for dt in (1.2, .3, 10, 10.2):
            factory.update(loaded, dt)
        self.assertEqual(loaded.manufacturing, v.manufacturing)
        self.assertEqual(loaded.material_inventory, v.material_inventory)
        live = factory.get_machine(v, bench)["controller"]["runtime"]
        self.assertGreater(live["active"]["6,3"], 0)
        factory.set_mode(v, bench, False)
        self.assertEqual(factory.get_machine(v, bench)["controller"]["runtime"], live)

    def test_customers_reject_duplicates_full_stock_and_reserve_spending(self):
        v = self.village
        factory.state(v)["goods"]["repair_kits"] = 5
        self.assertTrue(factory.sell_goods(v, "foundry")[0])
        self.assertFalse(factory.sell_goods(v, "foundry")[0])
        v.businesses["sawmill"]["cash"] = 0
        self.assertFalse(factory.sell_goods(v, "sawmill")[0])
        v.businesses["toolmaker"]["stock"]["fittings"] = 6
        self.assertFalse(factory.sell_goods(v, "toolmaker")[0])
        self.assertEqual(factory.state(v)["goods"]["repair_kits"], 4)

    def test_maintenance_only_uses_productive_days_and_preserves_last_day_bonus(self):
        v = self.village
        factory.state(v)["goods"]["repair_kits"] = 2
        v.daily_life = {"produced": {"foundry": 2}}
        self.assertTrue(factory.sell_goods(v, "foundry")[0])

        # Output before purchase does not spend a day of the installed kit.
        factory.update(v, .5)
        v.day += 1
        v.daily_life = {"produced": {}}
        factory.update(v, .5)
        self.assertEqual(factory.state(v)["maintenance"]["foundry"]["remaining"], 6)
        for _ in range(6):
            self.assertEqual(factory.capacity_bonus(v, "foundry"), 2)
            v.daily_life = {"produced": {"foundry": 1}}
            factory.update(v, .5)
            self.assertEqual(factory.capacity_bonus(v, "foundry"), 2)
            v.day += 1
            v.daily_life = {"produced": {}}
            factory.update(v, .5)
        self.assertEqual(factory.capacity_bonus(v, "foundry"), 0)
        self.assertTrue(factory.sell_goods(v, "foundry")[0])

    def test_road_crew_is_finite_accounted_and_uses_kits_after_day_change(self):
        v = self.village
        factory.state(v)["goods"]["repair_kits"] = 4
        before = cash(v)
        self.assertTrue(factory.sell_goods(v, "road_crew")[0])
        self.assertEqual(cash(v) - before, 10)
        self.assertTrue(v.daily_trades[-1]["external"])
        loaded = Village(**json.loads(json.dumps(asdict(v))))
        self.assertFalse(factory.sell_goods(loaded, "road_crew")[0])
        for _ in range(3):
            factory.offers(loaded)
        self.assertEqual(loaded.manufacturing["road_crew"]["used"], 0)
        self.assertEqual(loaded.manufacturing["road_crew"]["stock"], 1)
        loaded.day += 1
        factory.update(loaded, .5)
        self.assertEqual(loaded.manufacturing["road_crew"]["used"], 1)
        self.assertEqual(loaded.manufacturing["road_crew"]["stock"], 0)
        self.assertTrue(factory.sell_goods(loaded, "road_crew")[0])
        self.assertFalse(factory.sell_goods(loaded, "road_crew")[0])



if __name__ == "__main__":
    unittest.main()
