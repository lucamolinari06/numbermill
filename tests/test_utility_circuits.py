"""Utility blocks preserve numeric buses, delays, rotations, and saved state."""
import json
from copy import deepcopy
import unittest

from circuit import ARITHMETIC, UTILITY, Circuit, Part, N, E, S, W, edge_terminals


def wired(kind, rotation=0):
    names = ("A", "B", "C") if kind == "MUX" else ("A", "B")
    circuit = Circuit(terminals=edge_terminals(names))
    circuit.set_part((5, 3), Part(kind, rotation))
    terminals = {port["name"]: pos for pos, port in circuit.terminals.items()}
    for pin, name in enumerate(names):
        circuit.connect(terminals[name], (5, 3), pin)
    circuit.connect((5, 3), terminals["OUT"], 0)
    return circuit


def nested(circuit, number=1):
    outer = Circuit(terminals=edge_terminals(("A", "B")))
    outer.set_part((5, 3), Part("DEVICE", device={"id": number, "version": 1,
                                                   "name": "Utility controller", "parts": circuit.snapshot()}))
    ports = {port["name"]: pos for pos, port in outer.terminals.items()}
    outer.connect(ports["A"], (5, 3), 0)
    outer.connect(ports["B"], (5, 3), 1)
    outer.connect((5, 3), ports["OUT"], 0)
    return outer


class UtilityCircuitTests(unittest.TestCase):
    def test_unsigned_arithmetic_boundaries_and_zero_divisors(self):
        operations = {"DIV": lambda a, b: a // b if b else 0,
                      "MOD": lambda a, b: a % b if b else 0,
                      "MIN": min, "MAX": max}
        for kind, operation in operations.items():
            for a, b in ((0, 0), (0, 65535), (65535, 0), (65535, 1), (65535, 65535),
                         (29, 6), (5, 29), (256, 255), (65536, 2)):
                with self.subTest(kind=kind, a=a, b=b):
                    circuit = wired(kind)
                    actual, stable = circuit.evaluate(a, b)
                    self.assertEqual(actual, operation(a & 65535, b & 65535))
                    self.assertTrue(stable)

    def test_mux_selects_whole_bus_for_zero_and_any_nonzero_selection(self):
        circuit = wired("MUX")
        for a, b in ((0, 65535), (65535, 0), (255, 256), (7, 42)):
            for select in (0, 1, 2, 65535):
                with self.subTest(a=a, b=b, select=select):
                    actual, stable = circuit.evaluate(a, b, select)
                    self.assertEqual(actual, b if select else a)
                    self.assertTrue(stable)

    def test_rotated_mux_keeps_logical_pin_order(self):
        for rotation in range(4):
            part = Part("MUX", rotation)
            self.assertEqual(part.ports(), (tuple((direction + rotation) % 4 for direction in (W, S, N)),
                                            ((E + rotation) % 4,)))
            circuit = wired("MUX", rotation)
            self.assertEqual(circuit.evaluate(33, 8192, 0), (33, True))
            self.assertEqual(circuit.evaluate(33, 8192, 17), (8192, True))

    def test_each_utility_retains_component_propagation_delay(self):
        for kind in UTILITY:
            with self.subTest(kind=kind):
                circuit = wired(kind)
                circuit.switches.update(A=29, B=6)
                if kind == "MUX":
                    circuit.switches["C"] = 1
                expected = {"DIV": 4, "MOD": 5, "MIN": 6, "MAX": 29, "MUX": 6}[kind]
                for _ in range(2):
                    circuit.tick()
                    self.assertEqual(circuit.output_value(), 0)
                circuit.tick()
                self.assertEqual(circuit.output_value(), expected)

    def test_pipe_routes_receive_numeric_utility_history(self):
        for kind in ("DIV", "MOD", "MIN", "MAX"):
            circuit = Circuit()
            for x in (2, 3, 5, 6, 7, 8):
                circuit.set_part((x, 3), Part("PIPE"))
            for y in (4, 5):
                circuit.set_part((4, y), Part("PIPE", 1))
            circuit.set_part((4, 3), Part(kind))
            expected = {"DIV": 4, "MOD": 5, "MIN": 6, "MAX": 29}[kind]
            self.assertEqual(circuit.evaluate(29, 6), (expected, True))
            self.assertIn((4, 3), circuit.histories)

    def test_snapshot_and_nested_versions_preserve_utility_components(self):
        for kind in UTILITY:
            circuit = wired(kind)
            if kind == "MUX":
                # A two-port reusable controller can derive its selection
                # internally; here B doubles as the selection input.
                ports = {port["name"]: pos for pos, port in circuit.terminals.items()}
                circuit.connect(ports["B"], (5, 3), 2)
                circuit.layout_terminals(("A", "B"))
            expected = {"DIV": 4, "MOD": 5, "MIN": 6, "MAX": 29, "MUX": 6}[kind]
            for level in (1, 2):
                circuit = nested(circuit, level)
                restored = Circuit.from_snapshot(json.loads(json.dumps(circuit.snapshot())))
                self.assertEqual(restored.evaluate(29, 6), (expected, True))

    def test_runtime_midflight_restores_and_evaluation_preserves_live_state(self):
        for kind in UTILITY:
            circuit = wired(kind)
            circuit.switches.update(A=1025, B=8)
            if kind == "MUX":
                circuit.switches["C"] = 7
            circuit.tick()
            before = deepcopy(circuit.runtime_snapshot())
            circuit.evaluate(52, 9, 0)
            self.assertEqual(circuit.runtime_snapshot(), before)
            restored = Circuit.from_snapshot(circuit.snapshot())
            restored.restore_runtime(json.loads(json.dumps(before)))
            for _ in range(8):
                circuit.tick()
                restored.tick()
                self.assertEqual(circuit.runtime_snapshot(), restored.runtime_snapshot())

    def test_utility_blocks_do_not_require_arithmetic_invention_unlocks(self):
        from economy import Village
        from inventions import locked_blocks
        self.assertFalse(set(UTILITY) & set(ARITHMETIC))
        for kind in UTILITY:
            self.assertEqual(locked_blocks(Village(), wired(kind).snapshot()), set())


if __name__ == "__main__":
    unittest.main()
