"""Authored later jobs are solvable with the existing physical gate set."""
from copy import deepcopy
from dataclasses import asdict
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from circuit import Circuit, Part, edge_terminals
from commission_logic import logic_arity, truth_rows
from commissions import COMMISSIONS, EXTENDED_CONTRACTS, post_extended_offers
from materials import material_bill, advance_materials, deliver_project
from economy import Village


def funded_village():
    """A late-game delivery fixture; funding is set before conservation checks."""
    village = Village()
    village.day = 100
    for firm in village.businesses.values():
        firm["cash"] = 1000
    for shop, good in (("sawmill", "timber"), ("foundry", "metal"), ("toolmaker", "fittings")):
        village.businesses[shop]["stock"][good] = 100
    for key in ("mill", "bakery", "vent", "market", "pump", "sorter"):
        if not village.fulfill_job(key):
            raise AssertionError(f"Fixture prerequisite {key} could not be installed")
    return village


def wealth(village):
    return (village.coins + village.rival_cash + sum(firm["cash"] for firm in village.businesses.values())
            + sum(home["cash"] for home in village.households.values()))


def gate(kind, *inputs):
    return (kind, *inputs)


A, B, C = "A", "B", "C"
ALL = gate("AND", gate("AND", A, B), C)
MAJORITY = gate("OR", gate("OR", gate("AND", A, B), gate("AND", A, C)), gate("AND", B, C))
PARITY = gate("XOR", gate("XOR", A, B), C)
SOLUTIONS = {
    "XOR": gate("XOR", A, B),
    "XNOR": gate("NOT", gate("XOR", A, B)),
    "IMPLIES": gate("OR", gate("NOT", A), B),
    "ALL_THREE": ALL,
    "ANY_THREE": gate("OR", gate("OR", A, B), C),
    "MUX": gate("OR", gate("AND", A, gate("NOT", C)), gate("AND", B, C)),
    "ODD_PARITY": PARITY,
    "EXACTLY_ONE": gate("AND", PARITY, gate("NOT", ALL)),
    "EXACTLY_TWO": gate("AND", MAJORITY, gate("NOT", ALL)),
    "UNANIMOUS": gate("OR", ALL, gate("NOT", gate("OR", gate("OR", A, B), C))),
    "INHIBITED_OR": gate("AND", gate("OR", A, B), gate("NOT", C)),
    "PRIORITY": gate("OR", A, gate("AND", B, gate("NOT", C))),
}

# Independent truth tables in binary input order (000, 001, ...).
EXPECTED = {
    "XOR": "0110", "XNOR": "1001", "IMPLIES": "1101",
    "ALL_THREE": "00000001", "ANY_THREE": "01111111",
    "MUX": "00011011", "ODD_PARITY": "01101001",
    "EXACTLY_ONE": "01101000", "EXACTLY_TWO": "00010110",
    "UNANIMOUS": "10000001", "INHIBITED_OR": "00101010",
    "PRIORITY": "00101111",
}


def solution(logic):
    circuit = Circuit(terminals=edge_terminals((A, B, C)[:logic_arity(logic)]))
    nodes = {port["name"]: pos for pos, port in circuit.terminals.items()}
    count = 0

    def place(expression):
        nonlocal count
        if expression in nodes:
            return nodes[expression]
        kind, *sources = expression
        sources = [place(source) for source in sources]
        pos = (2 + count % 11, 1 + count // 11)
        count += 1
        circuit.set_part(pos, Part(kind))
        for pin, source in enumerate(sources):
            circuit.connect(source, pos, pin)
        nodes[expression] = pos
        return pos

    output = place(SOLUTIONS[logic])
    circuit.connect(output, nodes["OUT"], 0)
    return circuit


class ExtendedCommissionTests(unittest.TestCase):
    def test_all_twelve_new_behaviors_have_correct_exhaustive_tables(self):
        self.assertEqual(len(COMMISSIONS), 18)
        self.assertEqual(len(EXTENDED_CONTRACTS), 12)
        for logic, expected in EXPECTED.items():
            with self.subTest(logic=logic):
                self.assertEqual("".join(str(int(value)) for _, value in truth_rows(logic)), expected)

    def test_each_job_has_a_working_existing_gate_solution_and_save_roundtrip(self):
        for key in EXTENDED_CONTRACTS:
            job = COMMISSIONS[key]
            with self.subTest(key=key):
                circuit = solution(job.logic)
                circuit.tick()
                before = deepcopy(circuit.snapshot()), circuit.tick_count, deepcopy(circuit.switches)
                rows = circuit.commission_test_results(job.logic)
                self.assertEqual(len(rows), 2 ** logic_arity(job.logic))
                self.assertTrue(all(row.passed for row in rows))
                self.assertEqual((circuit.snapshot(), circuit.tick_count, circuit.switches), before)
                restored = Circuit.from_snapshot(circuit.snapshot())
                self.assertTrue(all(row.passed for row in restored.commission_test_results(job.logic)))
                restored.disconnect(next(pos for pos, port in restored.terminals.items() if port["output"]), 0)
                self.assertFalse(all(row.passed for row in restored.commission_test_results(job.logic)))

    def test_three_input_jobs_cannot_pass_with_an_absent_terminal(self):
        for logic in EXPECTED:
            if logic_arity(logic) == 3:
                with self.subTest(logic=logic):
                    self.assertFalse(any(row.passed for row in Circuit().commission_test_results(logic)))

    def test_authored_metadata_materials_and_prerequisites_are_complete(self):
        seen = set()
        for key, job in COMMISSIONS.items():
            self.assertEqual(job.level, len(seen) + 1)
            self.assertIn(job.prerequisite, seen | {None})
            self.assertEqual(3 if job.input_c else 2, logic_arity(job.logic))
            self.assertTrue(material_bill(key))
            if key in EXTENDED_CONTRACTS:
                self.assertEqual(EXTENDED_CONTRACTS[key], (job.business_id, job.machine, job.reward))
            seen.add(key)

    def village(self, day=100):
        return SimpleNamespace(day=day, offers={"sorter": {"status": "player"}},
                               businesses={business: {"cash": 200} for business, _, _ in EXTENDED_CONTRACTS.values()},
                               journal=[], last_contract_event="")

    def test_offers_respect_day_prerequisite_and_customer_budget(self):
        village = self.village(day=7)
        post_extended_offers(village)
        self.assertNotIn("fuel_diverter", village.offers)
        village.day = 8
        village.businesses["fuel_yard"]["cash"] = 35
        post_extended_offers(village)
        self.assertNotIn("fuel_diverter", village.offers)
        village.businesses["fuel_yard"]["cash"] = 36
        village.offers["sorter"]["status"] = "open"
        post_extended_offers(village)
        self.assertNotIn("fuel_diverter", village.offers)
        village.offers["sorter"]["status"] = "rival"
        post_extended_offers(village)
        self.assertEqual(village.offers["fuel_diverter"]["status"], "open")
        self.assertEqual(village.offers["fuel_diverter"]["due_day"], 16)

    def test_progression_posts_only_one_new_job_at_a_time(self):
        village = self.village()
        for key in EXTENDED_CONTRACTS:
            before = len(village.offers)
            post_extended_offers(village)
            self.assertEqual(len(village.offers), before + 1)
            self.assertEqual(village.offers[key]["status"], "open")
            post_extended_offers(village)
            self.assertEqual(len(village.offers), before + 1)
            village.offers[key]["status"] = "player"
        self.assertEqual(len(village.offers), 13)

    def test_actual_customer_funded_deliveries_preserve_money_materials_and_saved_flags(self):
        village = funded_village()
        total = wealth(village)
        for index, key in enumerate(EXTENDED_CONTRACTS):
            with self.subTest(key=key):
                advance_materials(village, key)
                self.assertEqual(village.material_reservations[key], material_bill(key))
                self.assertEqual(wealth(village), total)
                mode = ("install", "sell", "license")[index % 3]
                self.assertTrue(deliver_project(village, key, mode)[0])
                self.assertEqual(wealth(village), total)
                self.assertNotIn(key, village.material_reservations)
                self.assertEqual(village.offers[key]["materials_used"], material_bill(key))
                self.assertFalse(deliver_project(village, key, mode)[0])
                village = Village(**json.loads(json.dumps(asdict(village))))
                self.assertTrue(getattr(village, f"{key}_machine"))
                self.assertEqual(village.offers[key]["delivery_mode"], mode)
                self.assertEqual(wealth(village), total)
        for business_id, _, _ in EXTENDED_CONTRACTS.values():
            self.assertEqual(village.stock_buffer_bonus(business_id), 2)

    def test_game_can_test_deliver_reload_and_revisit_a_new_three_input_job(self):
        import pygame
        from game import Game
        try:
            with tempfile.TemporaryDirectory() as folder, patch("game.SAVES_DIR", Path(folder)):
                game = Game()
                game.current_slot = 2
                game.village = funded_village()
                target = "parts_selector"
                for key in EXTENDED_CONTRACTS:
                    if key == target:
                        break
                    advance_materials(game.village, key)
                    self.assertTrue(deliver_project(game.village, key)[0])
                game.choose_contract(target)
                game.circuit = solution(COMMISSIONS[target].logic)
                game.draw()
                game.test_commission()
                self.assertTrue(game.submission_ready)
                self.assertEqual(len(game.test_results), 8)
                game.request_material_advance()
                game.submit_design()
                self.assertTrue(game.contract_complete(target))
                self.assertEqual(game.village.offers[target]["status"], "player")
                game.save_game()
                loaded = Game()
                loaded.start_slot(2)
                loaded.choose_contract(target)
                loaded.draw()
                loaded.test_commission()
                self.assertEqual(loaded.commission.key, target)
                self.assertTrue(loaded.contract_complete(target))
                self.assertEqual(set(loaded.circuit.switches), {"A", "B", "C"})
                self.assertTrue(all(row.passed for row in loaded.test_results))
                self.assertFalse(loaded.submission_ready)
        finally:
            pygame.quit()


if __name__ == "__main__":
    unittest.main()
