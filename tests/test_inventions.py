import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import json
import tempfile
import unittest
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
import pygame
import inventions
import computation
import workshop_floor
from circuit import Circuit, Part
from economy import Village
from game import Game


def solution(key):
    def g(kind, a, b=None):
        return {"kind":kind,"inputs":[a,b]}
    if key == "adder":
        gates=[g("XOR","A","B"),g("AND","A","B")]
        outputs={"SUM":"G0","CARRY":"G1"}
    elif key == "subtractor":
        gates=[g("XOR","A","B"),g("NOT","A"),g("AND","G1","B")]
        outputs={"DIFF":"G0","BORROW":"G2"}
    elif key == "comparator":
        gates=[g("NOT","B"),g("AND","A","G0"),g("XOR","A","B"),g("NOT","G2")]
        outputs={"GT":"G1","EQ":"G3"}
    else:
        gates=[g("AND","A0","B0"),g("AND","A1","B0"),g("AND","A0","B1"),g("AND","A1","B1"),
               g("XOR","G1","G2"),g("AND","G1","G2"),g("XOR","G3","G5"),g("AND","G3","G5")]
        outputs={"P0":"G0","P1":"G4","P2":"G6","P3":"G7"}
    return {"gates":gates,"outputs":outputs}


class InventionTests(unittest.TestCase):
    def test_new_village_starts_with_all_arithmetic_locked(self):
        self.assertEqual(Village().arithmetic_unlocks,[])

    def test_all_guided_prototypes_pass_exhaustive_binary_cases(self):
        village=Village()
        for key, challenge in inventions.CHALLENGES.items():
            village.invention_drafts[key]=solution(key)
            cases=inventions.test(village,key)
            self.assertEqual(len(cases), 16 if key == "multiplier" else 4)
            self.assertTrue(all(row["passed"] for row in cases),cases)
            self.assertTrue(set(challenge.unlocks).issubset(village.arithmetic_unlocks))
        self.assertEqual(set(village.arithmetic_unlocks),{"ADD","SUB","GT","EQ","MUL"})

    def test_wrong_gate_and_missing_output_do_not_unlock(self):
        village=Village(); design=solution("adder")
        design["gates"][0]["kind"]="OR"
        village.invention_drafts["adder"]=design
        rows=inventions.test(village,"adder")
        self.assertFalse(rows[-1]["passed"])
        self.assertEqual(village.arithmetic_unlocks,[])
        design["outputs"]["SUM"]=None
        self.assertTrue(all(not row["passed"] for row in inventions.test(village,"adder")))

    def test_arithmetic_shortcuts_cycles_and_invalid_positions_are_rejected(self):
        for variation in ("arithmetic","cycle","overlap"):
            village=Village(); design=solution("adder")
            if variation == "arithmetic": design["gates"][0]["kind"]="ADD"
            if variation == "cycle": design["gates"][0]["inputs"][0]="G0"
            if variation == "overlap":
                design["gates"][0]["pos"]=[1,1]
                design["gates"][1]["pos"]=[1,1]
            village.invention_drafts["adder"]=design
            self.assertTrue(all(not row["passed"] for row in inventions.test(village,"adder")))
            self.assertEqual(village.arithmetic_unlocks,[])

    def test_multiplier_requires_adder_and_unlocks_remain_after_edits(self):
        village=Village(); village.invention_drafts["multiplier"]=solution("multiplier")
        inventions.test(village,"multiplier")
        self.assertNotIn("MUL",village.arithmetic_unlocks)
        village.invention_drafts["adder"]=solution("adder")
        inventions.test(village,"adder"); inventions.test(village,"adder")
        self.assertEqual(village.arithmetic_unlocks,["ADD"])
        village.invention_drafts["adder"]["outputs"]["SUM"]=None
        inventions.test(village,"adder")
        self.assertIn("ADD",village.arithmetic_unlocks)
        inventions.test(village,"multiplier")
        self.assertIn("MUL",village.arithmetic_unlocks)

    def test_trace_exposes_gate_delay_and_binary_outputs(self):
        village=Village(); village.invention_drafts["subtractor"]=solution("subtractor")
        bench=inventions.Bench(village,"subtractor")
        bench.bits={"A":0,"B":1}; bench.edit()
        bench.tick()
        self.assertEqual(bench.circuit.active[(5,2)],1)
        self.assertEqual(bench.circuit.active[(7,2)],0)
        bench.tick()
        self.assertEqual(bench.circuit.active[(7,2)],1)
        actual,trace,error=inventions.evaluate("subtractor",bench.design,bench.bits)
        self.assertEqual(actual,{"DIFF":1,"BORROW":1})
        self.assertIsNone(error)

    def test_failed_case_can_be_loaded_for_tracing_and_gate_removal_disconnects(self):
        village=Village(); village.invention_drafts["adder"]=solution("adder")
        bench=inventions.Bench(village,"adder")
        bench.circuit.set_part((3,2),Part("OR"))
        bench.run_tests()
        bench.load_case(3)
        self.assertEqual(bench.bits,{"A":1,"B":1})
        self.assertFalse(bench.show_results)
        bench.tick(); bench.tick(); self.assertEqual(bench.circuit.active[(3,2)],1)
        bench.circuit.set_part((3,2),None)
        self.assertFalse(any(tuple(t["source"]) == (3,2) for t in bench.circuit.traces))


class InventionIntegrationTests(unittest.TestCase):
    def test_click_locked_palette_opens_lesson_and_leaves_floor_unchanged(self):
        game=Game(); game.scene="workshop"; game.draw(); floor=game.circuit.snapshot()
        game.handle_click((1090,450),1)  # Math group
        game.draw()
        game.handle_click((992,496),1)  # Locked ADD
        self.assertEqual(game.scene,"workshop")
        self.assertEqual(game.invention.key,"adder")
        self.assertEqual(game.invention_context["circuit"].snapshot(),floor)
        game.draw()

    def test_ui_can_construct_half_adder_wire_and_unlock(self):
        game=Game(); game.scene="workshop"; game.open_invention(); game.draw()
        # The same floor, palette and socket gestures as contracts and calculators.
        bx,by,cell=game.board_metrics()
        for kind, pos in (("XOR",(5,2)),("AND",(7,5))):
            game.select_part(kind)
            game.handle_click((bx+(pos[0]+.5)*cell,by+(pos[1]+.5)*cell),1)
        def wire(source,target,pin):
            start=workshop_floor.socket(game,source,game.circuit.parts[source].ports()[1][0])
            end=workshop_floor.socket(game,target,game.circuit.parts[target].ports()[0][pin])
            game.handle_click(start,1)
            game.handle_click((bx+4*cell,by+4*cell),1)
            game.handle_click(end,1)
        for gate in ((5,2),(7,5)):
            wire((0,3),gate,0)
            wire((0,6),gate,1)
        wire((5,2),(15,3),0)
        wire((7,5),(15,6),0)
        self.assertEqual(len(game.circuit.traces),6)
        self.assertTrue(all(t["points"] for t in game.circuit.traces))
        game.test_invention(); self.assertIn("ADD",game.village.arithmetic_unlocks)
        game.draw(); game.close_invention(); game.select_part("ADD")
        self.assertEqual(game.selected,"ADD")

    def test_earned_industrial_block_keeps_full_decimal_bus_values(self):
        from test_computation import calculator
        game=Game(); game.scene="workshop"
        game.village.invention_drafts["adder"]=solution("adder")
        inventions.test(game.village,"adder")
        game.select_part("ADD")
        game.circuit=calculator("ADD")
        self.assertEqual(game.circuit.evaluate(255,255),(510,True))

    def test_nested_device_loading_and_forged_selection_cannot_bypass_locks(self):
        game=Game(); game.scene="workshop"
        child=Circuit(); child.set_part((4,3),Part("MUL"))
        outer=Circuit(); outer.set_part((4,3),Part("DEVICE",device={"id":1,"version":1,"name":"Hidden","parts":child.snapshot()}))
        game.designs=[{"number":1,"name":"Hidden","parts":outer.snapshot()}]
        floor=game.circuit.snapshot(); game.load_design(0); game.select_device(0)
        self.assertEqual(game.circuit.snapshot(),floor); self.assertIsNone(game.held_device)
        game.selected="ADD"; game.handle_click((180,180),1)
        self.assertEqual(game.scene,"workshop")
        self.assertEqual(len(game.invention_context["circuit"].parts),3)
        self.assertFalse(any(p.kind in ("ADD", "DEVICE") for p in game.invention_context["circuit"].parts.values()))

    def test_compute_registration_and_running_require_earned_technology(self):
        game=Game(); game.circuit.set_part((4,3),Part("MUL"))
        before=deepcopy(vars(game.village))
        message,rows=computation.approve(game.village,"fuel_quote",game.circuit,{})
        self.assertIn("Invent",message); self.assertEqual(vars(game.village),before)
        game.scene="compute"; game.compute_key="fuel_quote"; game.build_compute()
        self.assertEqual(game.scene,"workshop"); self.assertEqual(game.invention.key,"adder")

    def test_save_reload_preserves_drafts_unlocks_and_evidence(self):
        with tempfile.TemporaryDirectory() as folder,patch("game.SAVES_DIR",Path(folder)):
            game=Game(); game.current_slot=2; game.scene="workshop"
            game.village.invention_drafts["adder"]=solution("adder")
            game.open_invention(); game.test_invention(); game.close_invention()
            game.village.invention_drafts["comparator"]=solution("comparator")
            game.village.invention_drafts["adder"]["floor"][-2]["points"]=[[5.5,4.5]]
            game.save_game()
            loaded=Game(); loaded.start_slot(2)
            self.assertEqual(loaded.village.arithmetic_unlocks,["ADD"])
            self.assertEqual(loaded.village.invention_drafts,game.village.invention_drafts)
            self.assertEqual(loaded.village.invention_records,game.village.invention_records)

    def test_legacy_save_preserves_used_technology_but_not_unused_blocks(self):
        with tempfile.TemporaryDirectory() as folder,patch("game.SAVES_DIR",Path(folder)):
            circuit=Circuit(); circuit.set_part((4,3),Part("MUL"))
            data={"version":4,"village":{"coins":31},"circuit":circuit.snapshot(),"designs":[]}
            Path(folder,"slot_2.json").write_text(json.dumps(data),encoding="utf-8")
            game=Game(); game.start_slot(2)
            self.assertEqual(game.village.arithmetic_unlocks,["MUL"])
            self.assertEqual(game.village.coins,31)
            self.assertEqual(game.circuit.snapshot(),circuit.snapshot())


if __name__ == "__main__": unittest.main()
