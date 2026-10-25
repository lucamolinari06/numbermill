"""Long-horizon food, cash flow, and optional-spending regression checks."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import json
import unittest
from dataclasses import asdict

from daily_life import DAY_SECONDS, update_continuous, state, produce, SHIFT_SECONDS
from economy import Village, CONTRACTS
from town import Town


def money(village):
    return village.coins + village.rival_cash + sum(f["cash"] for f in village.businesses.values()) + sum(h["cash"] for h in village.households.values())


class EconomyStabilityTests(unittest.TestCase):
    def test_year_of_food_and_service_has_funded_meals_and_accounted_cash(self):
        village, town = Village(), Town()
        for key in ("mill", "bakery", "vent", "market", "pump", "sorter"):
            self.assertTrue(village.fulfill_job(key))
        village.toggle_service()
        for _ in range(365):
            before, day = money(village), village.day
            update_continuous(village, town, DAY_SECONDS)
            entries = next(row["entries"] for row in village.trade_history if row["day"] == day)
            external = sum(t.get("cash_delta", t["coins"]) for t in entries if t.get("external"))
            external += sum(event.get("savings", 0) for event in village.migration_events if event["day"] == day)
            self.assertEqual(money(village) - before, external, f"Day {day}: unexplained cash flow")
            for firm in village.businesses.values():
                self.assertGreaterEqual(firm["cash"], 0)
                self.assertTrue(all(0 <= units <= 22 for units in firm["stock"].values()))
            if day >= 60:
                self.assertEqual(village.last_day_report["fed"], village.last_day_report["households"], f"Day {day}")
                self.assertTrue(all(home["cash"] >= village.bread_price for home in village.households.values()))
        self.assertGreater(village.service_days, 100)
        self.assertTrue(all(village.businesses[key]["cash"] >= 12 for key in ("farm", "mill", "bakery", "market")))
        self.assertGreater(len(village.citizens), 6)
        self.assertTrue(any(t.get("external") for row in village.trade_history for t in row["entries"]))

    def test_distressed_save_credit_is_funded_finite_and_repaid(self):
        village = Village()
        for key in ("farm", "mill", "bakery", "market"):
            village.businesses[key]["cash"] = 0
        village.businesses["fuel_yard"]["cash"] = 500
        before = money(village)
        village._review_working_capital()
        self.assertEqual(money(village), before)
        for key in ("farm", "mill", "bakery", "market"):
            self.assertEqual(village.businesses[key]["cash"], 36)
            self.assertEqual(village.businesses[key]["working_credit"]["owed"], 36)
            village.businesses[key]["cash"] = 0
        lender_cash = village.businesses["fuel_yard"]["cash"]
        village._review_working_capital()
        self.assertEqual(village.businesses["fuel_yard"]["cash"], lender_cash)
        village.businesses["farm"]["cash"] = 100
        before = money(village)
        village._review_working_capital()
        village._review_working_capital()
        self.assertEqual(village.businesses["farm"]["working_credit"]["owed"], 32)
        self.assertEqual(village.businesses["farm"]["cash"], 96)
        self.assertEqual(money(village), before)

    def test_export_kits_consume_materials_and_wait_for_hired_worker(self):
        village = Village()
        village.offers["parts_selector"] = {"status": "player"}
        firm = village.businesses["sawmill"]
        firm["workers"] = 1
        village.citizens.append({"name": "Packing worker", "workplace": "sawmill"})
        before_cash, before_stock = firm["cash"], firm["stock"]["timber"]
        village._sell_regional_kits()
        self.assertEqual(firm["cash"], before_cash)
        state(village)["worked"]["Packing worker"] = SHIFT_SECONDS
        village._sell_regional_kits()
        village._sell_regional_kits()
        self.assertEqual(firm["cash"], before_cash + 10)
        self.assertEqual(firm["stock"]["timber"], before_stock - 1)
        self.assertTrue(village.daily_trades[-1]["external"])
        village.day += 1
        firm["stock"]["timber"] = 4
        state(village)["worked"]["Packing worker"] = SHIFT_SECONDS
        village._sell_regional_kits()
        self.assertEqual(firm["stock"]["timber"], 4)

    def test_load_keeps_eight_entry_journal_intact(self):
        village = Village()
        village.journal = [f"Saved event {i}" for i in range(8)]
        loaded = Village(**json.loads(json.dumps(asdict(village))))
        self.assertEqual(loaded.journal, village.journal)

    def test_contract_and_license_cash_are_visible_in_trade_ledger(self):
        village = Village()
        village.fulfill_job("mill", "license")
        machine = next(t for t in village.daily_trades if t["good"] == "machine")
        self.assertEqual(machine["coins"], 12)
        village.day += 1
        village._pay_royalties()
        payment = next(t for t in village.daily_trades if t["good"] == "license")
        self.assertEqual(payment["coins"], 2)
        self.assertEqual(payment["contract"], "mill")

    def test_optional_service_and_royalties_preserve_operating_reserve(self):
        village = Village()
        village.fulfill_job("mill", "license")
        village.toggle_service()
        village.day += 1
        village.businesses["mill"]["cash"] = 48
        village._pay_royalties()
        village._run_service()
        self.assertEqual(village.businesses["mill"]["cash"], 48)
        self.assertNotEqual(village.licenses["mill"]["paid_day"], village.day)
        self.assertEqual(village.service_days, 0)

    def test_service_does_not_spend_the_next_commissions_budget(self):
        village = Village()
        village.offers["parts_selector"] = {"status": "player"}
        village.service_active = True
        village.service_open_day = 0
        firm = village.businesses["parts_shop"]
        firm["cash"] = 58
        self.assertEqual(village.operating_reserve(firm), 58)
        village._run_service()
        self.assertEqual(firm["cash"], 58)
        self.assertEqual(village.service_days, 0)

    def test_buffer_controllers_do_not_add_production_or_fuel_expense(self):
        from commissions import EXTENDED_CONTRACTS
        village = Village()
        key, (_, machine, _) = next((key, row) for key, row in EXTENDED_CONTRACTS.items() if row[0] == "fuel_yard")
        firm = village.businesses["fuel_yard"]
        before = village.capacity("fuel_yard")
        firm["machines"].append(machine)
        self.assertEqual(village.capacity("fuel_yard"), before)
        self.assertEqual(village.stock_buffer_bonus("fuel_yard"), 1)
        cash = firm["cash"]
        village._supply_steam(firm)
        self.assertEqual(firm["cash"], cash)
        self.assertTrue(village.machine_ready("fuel_yard", machine))


if __name__ == "__main__":
    unittest.main()
