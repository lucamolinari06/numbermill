import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
from copy import deepcopy
import pygame

import computation
from circuit import Circuit, Part, WIDTH, HEIGHT
from economy import Village
from game import Game, BOARD_X, BOARD_Y, CELL


def calculator(kind):
    circuit = Circuit()
    for x in (2, 3, 5, 6, 7, 8):
        circuit.set_part((x, 3), Part("PIPE"))
    for y in (4, 5):
        circuit.set_part((4, y), Part("PIPE", 1))
    circuit.set_part((4, 3), Part(kind))
    return circuit


class ArithmeticTests(unittest.TestCase):
    def test_numeric_bus_boundaries_and_all_operations(self):
        for kind, a, b, expected in (("ADD",255,255,510), ("MUL",255,255,65025),
                                      ("SUB",3,9,0), ("SUB",9,3,6), ("GT",4,4,0),
                                      ("GT",5,4,1), ("EQ",4,4,1), ("EQ",4,5,0),
                                      ("ADD",65535,1,0), ("MUL",256,256,0)):
            with self.subTest(kind=kind, a=a, b=b):
                self.assertEqual(calculator(kind).evaluate(a,b), (expected, True))

    def test_nested_numeric_device_carries_full_result_and_state_is_restored(self):
        inner = calculator("MUL")
        outer = calculator("ADD")
        outer.set_part((4,3), Part("DEVICE", device={"id":1,"version":1,"name":"Multiply","parts":inner.snapshot()}))
        outer.switches = {"A":12,"B":3}
        for _ in range(60): outer.tick()
        before = (outer.output_value(), outer.tick_count, outer.devices[(4,3)].tick_count)
        self.assertEqual(outer.evaluate(255,255),(65025,True))
        self.assertEqual((outer.output_value(), outer.tick_count, outer.devices[(4,3)].tick_count),before)
        restored = Circuit.from_snapshot(outer.snapshot())
        self.assertEqual(restored.evaluate(12,3),(36,True))


class ComputeEconomyTests(unittest.TestCase):
    def setUp(self):
        self.village = Village()
        self.village.arithmetic_unlocks = ["ADD", "SUB", "MUL", "GT", "EQ"]

    def approve(self, key):
        job = computation.JOBS[key]
        _, results = computation.approve(self.village,key,calculator(job.operation),{"A":"A","B":"B","OUT":"Result"})
        self.assertTrue(all(r["passed"] for r in results))

    def test_invalid_design_is_rejected_without_payment(self):
        before = deepcopy(vars(self.village))
        _, cases = computation.approve(self.village,"fuel_quote",calculator("ADD"),{})
        self.assertFalse(all(r["passed"] for r in cases))
        self.assertEqual(vars(self.village),before)

    def test_registration_pays_once_and_runs_transfer_funds_consume_fuel(self):
        self.approve("fuel_quote")
        after_setup = self.village.coins
        self.approve("fuel_quote")
        self.assertEqual(self.village.coins,after_setup)
        before_cash = self.village.businesses["fuel_yard"]["cash"]
        computation.run_order(self.village,"fuel_quote")
        self.assertEqual(self.village.coins,after_setup+5)
        self.assertEqual(self.village.businesses["fuel_yard"]["cash"],before_cash-8+2)
        self.assertEqual(self.village.businesses["fuel_yard"]["stock"]["fuel"],1)
        receipt = self.village.compute_orders[-1]
        self.assertEqual(receipt["result"],receipt["a"]*receipt["b"])
        self.assertEqual(self.village.compute_earned,5)
        self.assertTrue(any(e["good"] == "calculation" for e in self.village.trade_history[-1]["entries"]))

    def test_per_customer_and_daily_capacity_limits_and_next_day_reset(self):
        for key in computation.JOBS: self.approve(key)
        self.village.businesses["fuel_yard"]["stock"]["fuel"]=10
        computation.run_order(self.village,"fuel_quote")
        once = deepcopy(vars(self.village))
        self.assertIn("already completed",computation.run_order(self.village,"fuel_quote"))
        self.assertEqual(vars(self.village),once)
        computation.run_order(self.village,"repair_quote")
        twice = deepcopy(vars(self.village))
        self.assertIn("slots",computation.run_order(self.village,"stock_check"))
        self.assertEqual(vars(self.village),twice)
        self.village.advance_day()
        self.assertIn("Earned",computation.run_order(self.village,"stock_check"))

    def test_shortages_and_bankruptcy_preserve_resources(self):
        self.approve("repair_quote")
        for field in ("fuel", "player", "customer"):
            village = deepcopy(self.village)
            if field == "fuel": village.businesses["fuel_yard"]["stock"]["fuel"]=0
            if field == "player": village.coins=0
            if field == "customer": village.businesses["parts_shop"]["cash"]=0
            before = deepcopy(vars(village))
            computation.run_order(village,"repair_quote")
            self.assertEqual(vars(village),before)

    def test_planning_bonus_affects_next_production_and_expires(self):
        self.approve("fuel_quote")
        computation.run_order(self.village,"fuel_quote")
        self.assertEqual(self.village.capacity("fuel_yard"),8)
        self.village.advance_day()
        self.assertEqual(self.village.capacity("fuel_yard"),8)
        self.village.advance_day()
        self.assertEqual(self.village.capacity("fuel_yard"),7)


class WorkbenchUITests(unittest.TestCase):
    def test_symbol_palette_places_arithmetic_in_expanded_area(self):
        game=Game(); game.scene="workshop"; game.village.arithmetic_unlocks=["ADD"]; game.draw()
        game.handle_click((1080,510),1)
        self.assertEqual(game.selected,"ADD")
        game.handle_click((BOARD_X+15*CELL+15,BOARD_Y+8*CELL+15),1)
        self.assertEqual(game.circuit.parts[(15,8)].kind,"ADD")
        self.assertEqual((WIDTH,HEIGHT),(16,9))

    def test_full_compute_flow_and_save_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory,patch("game.SAVES_DIR",Path(directory)):
            game=Game(); game.current_slot=2; game.scene="workshop"; game.village.arithmetic_unlocks=["MUL"]
            game.open_compute(); game.build_compute()
            game.circuit=calculator("MUL"); game.draw()
            game.test_commission()
            self.assertEqual(game.scene,"compute")
            self.assertTrue(all(r["passed"] for r in game.compute_results))
            game.approve_compute(); game.run_compute(); game.draw()
            loaded=Game(); loaded.start_slot(2)
            self.assertEqual(loaded.active_compute,"fuel_quote")
            self.assertEqual(loaded.village.compute_orders,game.village.compute_orders)
            self.assertEqual(loaded.village.compute_designs,game.village.compute_designs)
            self.assertTrue(loaded.numeric_mode)

    def test_numeric_inputs_increment_and_decrement(self):
        game=Game(); game.scene="workshop"; game.numeric_mode=True
        point=(BOARD_X+CELL+20,BOARD_Y+3*CELL+20)
        game.handle_click(point,1)
        self.assertEqual(game.circuit.switches["A"],1)
        game.handle_click(point,3)
        self.assertEqual(game.circuit.switches["A"],0)


if __name__ == "__main__": unittest.main()
