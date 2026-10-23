import unittest

from circuit import Circuit, Part
from economy import Village


class CircuitTests(unittest.TestCase):
    def build_mill_controller(self):
        circuit = Circuit()
        # A runs east into the first gate input.
        for x in (2, 3):
            circuit.set_part((x, 3), Part("PIPE"))
        # B runs north into the second gate input.
        for y in (4, 5):
            circuit.set_part((4, y), Part("PIPE", 1))
        circuit.set_part((4, 3), Part("AND"))
        for x in (5, 6, 7, 8):
            circuit.set_part((x, 3), Part("PIPE"))
        return circuit

    def test_propagation_takes_multiple_steps(self):
        circuit = self.build_mill_controller()
        circuit.switches = {"A": True, "B": True}
        circuit.tick()
        self.assertFalse(circuit.lamp_on())
        for _ in range(20):
            circuit.tick()
        self.assertTrue(circuit.lamp_on())

    def test_commission_checks_truth_table(self):
        circuit = self.build_mill_controller()
        self.assertEqual(circuit.test_mill_commission()[0], True)
        circuit.set_part((4, 3), Part("OR"))
        passed, explanation = circuit.test_mill_commission()
        self.assertFalse(passed)
        self.assertIn("Failed when", explanation)

    def test_second_commission_accepts_or_and_rejects_and(self):
        circuit = self.build_mill_controller()
        self.assertFalse(all(case.passed for case in circuit.commission_test_results("OR")))
        circuit.set_part((4, 3), Part("OR"))
        self.assertTrue(all(case.passed for case in circuit.commission_test_results("OR")))

    def test_safety_vent_requires_nand(self):
        circuit = self.build_mill_controller()
        circuit.set_part((6, 3), Part("NOT"))
        self.assertEqual([case.expected for case in circuit.commission_test_results("NAND")],
                         [True, True, True, False])
        self.assertTrue(all(case.passed for case in circuit.commission_test_results("NAND")))

    def test_market_cooler_requires_nor(self):
        circuit = self.build_mill_controller()
        circuit.set_part((4, 3), Part("OR"))
        circuit.set_part((6, 3), Part("NOT"))
        self.assertEqual([case.expected for case in circuit.commission_test_results("NOR")],
                         [True, False, False, False])
        self.assertTrue(all(case.passed for case in circuit.commission_test_results("NOR")))

    def test_design_snapshot_is_an_independent_copy(self):
        original = self.build_mill_controller()
        copy = Circuit.from_snapshot(original.snapshot())
        copy.set_part((4, 3), Part("OR"))
        self.assertEqual(original.parts[(4, 3)].kind, "AND")
        self.assertEqual(copy.parts[(4, 3)].kind, "OR")

    def test_bend_accepts_steam_from_either_end_and_clears(self):
        circuit = Circuit()
        # Rotated bend's old output faces A; steam must flow in that end.
        circuit.set_part((2, 3), Part("BEND", 3))
        circuit.set_part((2, 4), Part("PIPE", 1))
        circuit.switches["A"] = True
        for _ in range(5):
            circuit.tick()
        self.assertTrue(circuit.active[(2, 3)])
        self.assertTrue(circuit.active[(2, 4)])
        circuit.switches["A"] = False
        for _ in range(5):
            circuit.tick()
        self.assertFalse(circuit.active[(2, 3)])
        self.assertFalse(circuit.active[(2, 4)])
        for _ in range(300):
            circuit.tick()
        self.assertLessEqual(
            max(len(history) for history in circuit.histories.values()),
            circuit.max_route_distance + 1,
        )

    def test_splitter_accepts_steam_from_any_connected_end(self):
        circuit = Circuit()
        circuit.set_part((2, 3), Part("SPLIT", 2))
        circuit.set_part((3, 3), Part("PIPE"))
        circuit.switches["A"] = True
        for _ in range(5):
            circuit.tick()
        self.assertTrue(circuit.active[(3, 3)])


class VillageTests(unittest.TestCase):
    def test_mely_luca_firms_history_and_motives_survive_days(self):
        village = Village()
        self.assertEqual(village.businesses["fuel_yard"]["owner"], "Mely")
        self.assertEqual(village.businesses["parts_shop"]["owner"], "Luca")
        mely = next(person for person in village.citizens if person["name"] == "Mely")
        luca = next(person for person in village.citizens if person["name"] == "Luca")
        self.assertEqual(mely["home"], luca["home"])
        self.assertEqual(mely["relationships"]["Luca"], 80)
        before_fuel_cash = village.businesses["fuel_yard"]["cash"]
        village.advance_day()
        self.assertEqual(len(village.history), 2)
        self.assertGreater(village.businesses["fuel_yard"]["cash"], before_fuel_cash)
        self.assertGreater(village.businesses["parts_shop"]["stock"]["parts"], 0)
        self.assertTrue(any(entry["from"] == "Mely's Fuel Yard" and entry["to"] == "Luca's Repair Shop"
                            for entry in village.trade_history[-1]["entries"]))
        self.assertTrue(mely["memories"])
        self.assertIn(mely["activity"], ("working", "resting", "visiting neighbors",
                                         "spending time with spouse", "seeking food", "looking for help"))

    def test_workshop_service_uses_local_supplies_and_pays_net_income(self):
        active, control = Village(), Village()
        for village in (active, control):
            village.complete_mill_job()
        self.assertIn("opened", active.toggle_service())
        active.advance_day()
        control.advance_day()
        self.assertEqual(active.coins - control.coins, 2)
        # The customer also buys one extra grain to use its tuned capacity.
        self.assertEqual(active.businesses["mill"]["cash"] - control.businesses["mill"]["cash"], -9)
        self.assertEqual(active.businesses["mill"]["stock"]["flour"] -
                         control.businesses["mill"]["stock"]["flour"], 1)
        self.assertEqual(active.businesses["fuel_yard"]["cash"] - control.businesses["fuel_yard"]["cash"], 3)
        self.assertEqual(active.businesses["parts_shop"]["cash"] - control.businesses["parts_shop"]["cash"], 2)
        self.assertEqual(active.service_days, 1)

    def test_food_shortage_changes_personal_action_and_memory(self):
        village = Village()
        village.households["home_3"]["bread_need"] = 10
        village.advance_day()
        mely = next(person for person in village.citizens if person["name"] == "Mely")
        self.assertGreater(mely["hunger"], 25)
        self.assertIn(mely["activity"], ("seeking food", "looking for help"))
        self.assertIn("Day 2", mely["memories"][-1])

    def test_fuel_shortage_pauses_installed_steam_machine(self):
        village = Village()
        village.complete_mill_job()
        village.businesses["fuel_yard"]["workers"] = 0
        village.businesses["fuel_yard"]["stock"]["fuel"] = 0
        village.advance_day()
        self.assertEqual(village.capacity("mill"), 1)
        self.assertTrue(any("lacked fuel" in line for line in village.journal))

    def test_sell_copy_pays_more_and_records_both_owners(self):
        village = Village()
        before = village.businesses["mill"]["cash"] + village.coins
        self.assertTrue(village.complete_mill_job("sell"))
        self.assertEqual(village.coins, 44)
        self.assertEqual(village.businesses["mill"]["cash"] + village.coins, before)
        self.assertEqual(village.offers["mill"]["design_owner"], "You")
        self.assertEqual(village.offers["mill"]["copy_owner"], "Miller")
        self.assertEqual(village.offers["mill"]["delivery_mode"], "sell")
        self.assertFalse(village.complete_mill_job("sell"))

    def test_license_pays_daily_and_pauses_machine_when_unpaid(self):
        village = Village()
        self.assertTrue(village.complete_mill_job("license"))
        self.assertEqual(village.coins, 24)
        self.assertEqual(village.capacity("mill"), 4)
        village.advance_day()
        self.assertEqual(village.coins, 26)
        self.assertEqual(village.licenses["mill"]["total_paid"], 2)
        village.businesses["mill"]["cash"] = 0
        village.advance_day()
        self.assertEqual(village.coins, 26)
        self.assertEqual(village.capacity("mill"), 1)
        self.assertIn("machine paused", village.last_contract_event)

    def test_market_controller_prevents_spoilage(self):
        unsafe = Village()
        safe = Village()
        for village in (unsafe, safe):
            village.complete_mill_job()
            village.complete_bakery_job()
            village.rival_busy_until = 99
        self.assertTrue(safe.complete_market_job())
        for _ in range(5):
            unsafe.advance_day()
            safe.advance_day()
        self.assertEqual(safe.day, 6)
        self.assertTrue(any("lost one loaf" in line for line in unsafe.journal))
        self.assertFalse(any("lost one loaf" in line for line in safe.journal))
        self.assertEqual(safe.bread, unsafe.bread + 1)

    def test_safety_vent_prevents_seventh_day_shutdown(self):
        unsafe = Village()
        safe = Village()
        for village in (unsafe, safe):
            village.complete_mill_job()
            village.complete_bakery_job()
            village.rival_busy_until = 99
        safe.complete_vent_job()
        for _ in range(6):
            unsafe.advance_day()
            safe.advance_day()
        self.assertTrue(any("boiler shut down" in line for line in unsafe.journal))
        self.assertFalse(any("boiler shut down" in line for line in safe.journal))
        self.assertGreater(safe.bread, unsafe.bread)

    def test_business_posts_job_and_rival_delivers_after_visible_bid(self):
        village = Village()
        self.assertEqual(village.offers["mill"]["status"], "open")
        self.assertIn("mill capacity", village.offers["mill"]["reason"])
        for _ in range(3):
            village.advance_day()
        self.assertEqual(village.offers["mill"]["status"], "bid")
        self.assertEqual(village.offers["mill"]["finish_day"], village.day + 2)
        before = sum(f["cash"] for f in village.businesses.values()) + village.coins + village.rival_cash + sum(h["cash"] for h in village.households.values())
        village.advance_day()
        self.assertFalse(village.mill_machine)
        village.advance_day()
        self.assertTrue(village.mill_machine)
        self.assertEqual(village.offers["mill"]["status"], "rival")
        self.assertEqual(village.rival_cash, 24)
        self.assertIn("bakery", village.offers)
        after = sum(f["cash"] for f in village.businesses.values()) + village.coins + village.rival_cash + sum(h["cash"] for h in village.households.values())
        self.assertEqual(after, before)

    def test_player_can_win_after_rival_bid(self):
        village = Village()
        for _ in range(3):
            village.advance_day()
        village.complete_mill_job()
        self.assertEqual(village.offers["mill"]["status"], "player")
        for _ in range(3):
            village.advance_day()
        self.assertEqual(village.rival_cash, 0)
        self.assertEqual(village.offers["mill"]["status"], "player")

    def test_missed_deadline_has_a_visible_business_decision(self):
        village = Village()
        self.assertEqual(village.offers["mill"]["due_day"], 5)
        for _ in range(5):
            village.advance_day()
        self.assertTrue(village.offers["mill"]["missed_deadline"])
        self.assertEqual(village.offers["mill"]["status"], "rival")
        self.assertTrue(any("chose to wait for Nell" in line for line in village.journal))

    def test_unaffordable_rival_delivery_postpones_without_debt(self):
        village = Village()
        for _ in range(3):
            village.advance_day()
        village.businesses["mill"]["cash"] = 0
        village.advance_day()
        village.advance_day()
        self.assertFalse(village.mill_machine)
        self.assertEqual(village.rival_cash, 0)
        self.assertEqual(village.offers["mill"]["status"], "open")
        self.assertIn("could not afford Nell", village.last_contract_event)

    def test_unbid_expired_offer_is_renewed_without_ending_save(self):
        village = Village()
        village.rival_busy_until = 99
        for _ in range(5):
            village.advance_day()
        self.assertEqual(village.offers["mill"]["status"], "open")
        self.assertEqual(village.offers["mill"]["due_day"], village.day + 3)
        self.assertIn("postponed expansion", village.last_contract_event)

    def test_household_trade_conserves_money_and_leaves_player_stock(self):
        village = Village()
        def money():
            return village.coins + sum(f["cash"] for f in village.businesses.values()) + sum(h["cash"] for h in village.households.values())
        before = money()
        village.advance_day()
        self.assertEqual(money(), before)
        self.assertTrue(all(h["bought"] == 1 for h in village.households.values()))
        stock = village.businesses["market"]["stock"]["bread"]
        coins = village.coins
        village.buy_bread()
        self.assertEqual(village.player_bread, 1)
        self.assertEqual(village.coins, coins - village.bread_price)
        self.assertEqual(village.businesses["market"]["stock"]["bread"], stock - 1)
        self.assertEqual(money(), before)

    def test_unaffordable_bread_does_not_remove_goods_or_money(self):
        village = Village()
        village.advance_day()
        village.coins = 0
        stock = village.businesses["market"]["stock"]["bread"]
        village.buy_bread()
        self.assertEqual(village.player_bread, 0)
        self.assertEqual(village.businesses["market"]["stock"]["bread"], stock)

    def test_market_buys_from_bakery_before_selling_to_villagers(self):
        village = Village()
        village.advance_day()
        self.assertGreater(village.businesses["bakery"]["cash"], 120)
        deliveries = [entry for entry in village.trade_history[-1]["entries"]
                      if entry["from"] == "Copperside Bakery" and entry["to"] == "Copperside Market"]
        self.assertEqual(deliveries[0]["units"], 3)
        self.assertEqual(deliveries[0]["coins"], 21)
        self.assertEqual(village.businesses["market"]["stock"]["bread"], 2)
        self.assertIn("market sold 3 bread", village.journal[0])

    def test_goods_and_payments_move_between_independent_firms(self):
        village = Village()
        farm_cash = village.businesses["farm"]["cash"]
        mill_cash = village.businesses["mill"]["cash"]
        village.advance_day()
        self.assertEqual(village.businesses["farm"]["cash"], farm_cash + 2 - 4)
        self.assertEqual(village.businesses["mill"]["cash"], mill_cash - 2 + 2 * 5 - 4)
        self.assertEqual(village.grain, village.businesses["farm"]["stock"]["grain"])
        self.assertEqual(village.flour, village.businesses["mill"]["stock"]["flour"])

    def test_same_business_type_can_have_separate_owner_and_stock(self):
        village = Village()
        village.businesses["bakery_rival"] = {
            "kind": "bakery", "name": "Rival Bakery", "owner": "Rival Inventor",
            "parent_id": "mill", "cash": 90, "workers": 1,
            "stock": {"bread": 0}, "machines": [],
        }
        village.complete_mill_job()
        village.businesses["bakery"]["workers"] = 0
        village.advance_day()
        self.assertEqual(village.businesses["bakery_rival"]["parent_id"], "mill")
        self.assertGreater(village.businesses["bakery_rival"]["cash"], 90 - 4 * 4)
        self.assertEqual(village.businesses["bakery"]["stock"]["bread"], 0)

    def test_controller_improves_supply_and_price(self):
        slow = Village()
        improved = Village()
        improved.complete_mill_job()
        for _ in range(4):
            slow.advance_day()
            improved.advance_day()
        self.assertLess(improved.bread_price, slow.bread_price)
        self.assertIn("market sold 3 bread", improved.journal[0])
        self.assertEqual(improved.coins, 36)

    def test_bakery_selector_increases_sales(self):
        old_ovens = Village()
        old_ovens.complete_mill_job()
        new_ovens = Village()
        new_ovens.complete_mill_job()
        new_ovens.complete_bakery_job()
        for village in (old_ovens, new_ovens):
            for home in village.households.values():
                home["bread_need"] = 2
        for _ in range(4):
            old_ovens.advance_day()
            new_ovens.advance_day()
        self.assertGreaterEqual(new_ovens.businesses["market"]["stock"]["bread"], 1)
        self.assertLess(new_ovens.bread_price, old_ovens.bread_price)
        self.assertEqual(new_ovens.coins, 66)


if __name__ == "__main__":
    unittest.main()
