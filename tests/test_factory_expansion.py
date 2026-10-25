"""Trading automation, explicit storage wiring, displays and safe resale."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import json
import unittest
from copy import deepcopy
from dataclasses import asdict

from circuit import Circuit, Part, edge_terminals
from economy import Village
from daily_life import update_continuous, DAY_SECONDS
from town import Town
import manufacturing as factory


def wiring(kind="wire"):
    circuit = Circuit(terminals=edge_terminals(("A", "B")))
    ports = {p["name"]: pos for pos, p in circuit.terminals.items()}
    if kind == "wire":
        circuit.connect(ports["A"], ports["OUT"], 0)
    elif kind == "restock":
        circuit.set_part((6, 3), Part("GT"))
        circuit.connect(ports["B"], (6, 3), 0)  # Target > selected stock.
        circuit.connect(ports["A"], (6, 3), 1)
        circuit.connect((6, 3), ports["OUT"], 0)
    return circuit


def money(village):
    return village.coins + sum(firm["cash"] for firm in village.businesses.values())


class FactoryExpansionTests(unittest.TestCase):
    def setUp(self):
        self.v = Village()
        self.v.coins = 500
        self.v.businesses["toolmaker"]["stock"]["fittings"] = 40

    def equipment(self, kind):
        current = factory.state(self.v)
        occupied = {tuple(item["pos"]) for item in current["equipment"]}
        pos = next((x, y) for y in range(6) for x in range(9) if (x, y) not in occupied)
        okay, message = factory.buy_equipment(self.v, kind, pos)
        self.assertTrue(okay, message)
        return current["equipment"][-1]["id"]

    def controlled(self, kind, circuit=None, mapping=None):
        unit = self.equipment(kind)
        self.equipment("controller")
        okay, message = factory.install_controller(self.v, unit, circuit or wiring(), inputs=mapping)
        self.assertTrue(okay, message)
        return unit

    def test_buying_requires_user_circuit_and_targets_do_not_make_decisions(self):
        v = self.v
        unit = self.equipment("buyer")
        factory.configure_trader(v, unit, target=0, reserve=0, daily_budget=20, good="metal")
        before = v.material_inventory.copy()
        self.assertFalse(factory.set_mode(v, unit, True)[0])
        factory.update(v, 20)
        self.assertEqual(v.material_inventory, before)
        self.equipment("controller")
        factory.install_controller(v, unit, wiring("blank"))
        factory.set_mode(v, unit, True)
        factory.update(v, 20)
        self.assertEqual(v.material_inventory, before)
        # A manually wired high-ready signal buys despite target=0. Target is
        # information, not a hidden replenishment algorithm.
        factory.install_controller(v, unit, wiring(), inputs={"A": "ready", "B": "target"})
        factory.update(v, 3)
        self.assertGreater(v.material_inventory.get("metal", 0), 0)

    def test_purchase_limits_survive_reconfiguration_mode_changes_and_reload(self):
        v = self.v
        unit = self.controlled("buyer", mapping={"A": "ready", "B": "stock"})
        factory.configure_trader(v, unit, reserve=0, daily_budget=4, max_price=2)
        before = money(v)
        factory.set_mode(v, unit, True)
        factory.update(v, 15)
        self.assertEqual(v.material_inventory["metal"], 2)
        self.assertEqual(money(v), before)
        factory.set_mode(v, unit, False)
        factory.configure_trader(v, unit, good="metal", daily_budget=4)
        factory.set_mode(v, unit, True)
        loaded = Village(**json.loads(json.dumps(asdict(v))))
        factory.update(loaded, 10)
        self.assertEqual(loaded.material_inventory["metal"], 2)
        loaded.day += 1
        factory.update(loaded, 10)
        self.assertEqual(loaded.material_inventory["metal"], 4)
        self.assertEqual(factory.get_machine(loaded, unit)["daily_spent"], 4)

    def test_price_and_cash_safeguards_block_an_always_permitted_purchase(self):
        unit = self.controlled("buyer", mapping={"A": "cash", "B": "stock"})
        v = self.v
        factory.configure_trader(v, unit, max_price=1, reserve=0)
        factory.set_mode(v, unit, True)
        factory.update(v, 10)
        self.assertEqual(v.material_inventory, {})
        factory.configure_trader(v, unit, max_price=2, reserve=v.coins)
        factory.update(v, 10)
        self.assertEqual(v.material_inventory, {})

    def test_explicit_storage_wires_read_stocks_and_disconnect_when_removed(self):
        unit = self.controlled("buyer")
        rack = self.equipment("storage")
        self.v.material_inventory["metal"] = 321
        self.assertTrue(factory.set_input_source(self.v, unit, "A", rack, "metal")[0])
        self.assertEqual(factory.input_values(self.v, unit)["A"], 321)
        self.assertFalse(factory.set_sensor(self.v, unit, "A", "cash")[0])
        self.assertTrue(factory.install_controller(self.v, unit, wiring())[0])
        self.assertEqual(factory.get_machine(self.v, unit)["controller"]["sources"]["A"], rack)
        self.assertEqual(factory.input_values(self.v, unit)["A"], 321)
        self.assertFalse(factory.set_input_source(self.v, unit, "A", rack, "cash")[0])
        factory.set_mode(self.v, unit, True)
        self.assertTrue(factory.sell_equipment(self.v, rack)[0])
        self.assertEqual(factory.input_values(self.v, unit)["A"], 0)
        self.assertEqual(factory.get_machine(self.v, unit)["mode"], "manual")
        self.assertFalse(factory.set_mode(self.v, unit, True)[0])
        inventory = self.v.material_inventory.copy()
        factory.update(self.v, 20)
        self.assertEqual(self.v.material_inventory, inventory)
        self.assertEqual(factory.get_machine(self.v, unit)["controller"]["sources"]["A"], rack)

    def test_auto_trade_timing_and_runtime_continue_exactly_after_reload(self):
        unit = self.controlled("buyer", mapping={"A": "ready", "B": "cash"})
        factory.configure_trader(self.v, unit, reserve=0, daily_budget=24)
        factory.set_mode(self.v, unit, True)
        factory.update(self.v, 3.3)
        loaded = Village(**json.loads(json.dumps(asdict(self.v))))
        factory.update(self.v, 11.7)
        for dt in (.2, 2.4, 6.1, 3):
            factory.update(loaded, dt)
        self.assertEqual(loaded.manufacturing, self.v.manufacturing)
        self.assertEqual(loaded.material_inventory, self.v.material_inventory)
        self.assertEqual(loaded.coins, self.v.coins)
        self.assertEqual(loaded.daily_trades, self.v.daily_trades)

    def test_dispatch_obeys_minimum_price_stock_reserve_and_actual_demand(self):
        unit = self.controlled("seller", mapping={"A": "stock", "B": "demand"})
        v = self.v
        factory.state(v)["goods"]["repair_kits"] = 3
        factory.configure_trader(v, unit, buyer="road_crew", keep_stock=1, min_price=11)
        factory.set_mode(v, unit, True)
        factory.update(v, 10)
        self.assertEqual(factory.state(v)["sold"], 0)
        factory.configure_trader(v, unit, min_price=10)
        factory.update(v, 10)
        self.assertEqual(factory.state(v)["sold"], 1)
        loaded = Village(**json.loads(json.dumps(asdict(v))))
        factory.update(loaded, 20)
        self.assertEqual(factory.state(loaded)["sold"], 1)
        loaded.day += 1
        factory.update(loaded, 10)
        self.assertEqual(factory.state(loaded)["sold"], 2)
        loaded.day += 1
        factory.update(loaded, 10)
        self.assertEqual(factory.state(loaded)["goods"]["repair_kits"], 1)

    def test_full_supply_production_and_sales_chain_runs_on_real_village_clock(self):
        v = self.v
        for good in factory.RECIPE:
            unit = self.controlled("buyer", wiring("restock"))
            factory.configure_trader(v, unit, good=good, target=2, reserve=8, daily_budget=12)
            factory.set_mode(v, unit, True)
        bench = self.controlled("bench")
        seller = self.controlled("seller")
        factory.configure_trader(v, seller, buyer="any", keep_stock=0)
        factory.set_mode(v, bench, True)
        factory.set_mode(v, seller, True)
        # Fixtures provide setup capital and equipment components only.
        # After configuration every input purchase, batch and sale is automatic.
        v.businesses["toolmaker"]["stock"]["fittings"] = 4
        town = Town()
        update_continuous(v, town, DAY_SECONDS * 3)
        self.assertGreaterEqual(factory.state(v)["sold"], 3)
        self.assertGreaterEqual(factory.state(v)["auto_produced"], 3)
        self.assertTrue(all(v.material_inventory.get(good, 0) >= 0 for good in factory.RECIPE))
        entries = [entry for day in v.trade_history for entry in day["entries"]]
        for good in factory.RECIPE:
            self.assertTrue(any(entry["good"] == good and entry["to"] == "Your Workshop" for entry in entries))
        self.assertFalse(any(offer.get("status") == "player" for offer in v.offers.values()))

    def test_equipment_resale_conserves_cash_prevents_starter_exploit_and_reuses_hardware(self):
        v = self.v
        before = money(v)
        bench = self.equipment("bench")
        self.assertEqual(factory.equipment_sell_quote(v, bench)["price"], 2)
        self.assertTrue(factory.sell_equipment(v, bench)[0])
        self.assertFalse(factory.sell_equipment(v, bench)[0])
        self.assertEqual(factory.equipment_price(v, "bench"), 24)
        stock = v.businesses["toolmaker"]["stock"]["fittings"]
        later = self.equipment("bench")
        self.assertGreater(later, bench)
        self.assertEqual(v.businesses["toolmaker"]["stock"]["fittings"], stock)
        self.assertEqual(factory.equipment_sell_quote(v, later)["price"], 12)
        self.assertEqual(money(v), before)
        v.businesses["toolmaker"]["cash"] = 0
        snapshot = deepcopy(asdict(v))
        self.assertFalse(factory.sell_equipment(v, later)[0])
        self.assertEqual(asdict(v), snapshot)

    def test_busy_bench_storage_overflow_and_cabinet_removal_are_safe(self):
        v = self.v
        bench = self.controlled("bench")
        cabinet = next(item["id"] for item in factory.state(v)["equipment"] if item["kind"] == "controller")
        rack = self.equipment("storage")
        v.material_inventory = {good: 2 for good in factory.RECIPE}
        factory.state(v)["goods"]["repair_kits"] = 6
        self.assertTrue(factory.start_batch(v, bench)[0])
        self.assertFalse(factory.sell_equipment(v, bench)[0])
        self.assertFalse(factory.sell_equipment(v, rack)[0])
        factory.set_mode(v, bench, True)
        self.assertTrue(factory.sell_equipment(v, cabinet)[0])
        machine = factory.get_machine(v, bench)
        self.assertEqual(machine["mode"], "manual")
        self.assertIsNone(machine["controller"])
        factory.update(v, 20)
        self.assertEqual(factory.state(v)["produced"], 1)
        factory.state(v)["controller_drafts"][str(bench)] = {"parts": []}
        self.assertTrue(factory.sell_equipment(v, bench)[0])
        self.assertNotIn(str(bench), factory.state(v)["controller_drafts"])

    def test_display_configuration_and_old_save_migration_are_idempotent(self):
        v = self.v
        bench = self.controlled("bench")
        display = self.equipment("display")
        v.material_inventory["metal"] = 1234
        self.assertTrue(factory.configure_display(v, display, "metal")[0])
        self.assertEqual(factory.display_reading(v, display)["value"], 1234)
        factory.get_machine(v, bench)["signal"] = 65535
        self.assertTrue(factory.configure_display(v, display, "signal", bench)[0])
        self.assertEqual(factory.display_reading(v, display)["value"], 65535)
        self.assertTrue(factory.sell_equipment(v, bench)[0])
        self.assertEqual(factory.display_reading(v, display)["value"], 0)
        for item in factory.state(v)["equipment"]:
            item.pop("purchase_price", None)
            item.pop("display", None)
        loaded = Village(**json.loads(json.dumps(asdict(v))))
        factory.state(loaded)
        snapshot = deepcopy(asdict(loaded))
        factory.state(loaded)
        self.assertEqual(asdict(loaded), snapshot)


if __name__ == "__main__":
    unittest.main()
