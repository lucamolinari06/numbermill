"""Behavioral checks for player-facing timed workshop exercises."""

from copy import deepcopy
import unittest

from circuit import Circuit, Part, edge_terminals
import sequential


def solution(kind):
    circuit = Circuit(terminals=edge_terminals(("A", "B")))
    circuit.set_part((6, 3), Part(kind))
    positions = {port["name"]: pos for pos, port in circuit.terminals.items()}
    if kind != "CLOCK":
        circuit.connect(positions["A"], (6, 3), 0)
        circuit.connect(positions["B"], (6, 3), 1)
    circuit.connect((6, 3), positions["OUT"], 0)
    return circuit


def nested(inner):
    circuit = Circuit(terminals=edge_terminals(("A", "B")))
    circuit.set_part((6, 3), Part("DEVICE", device={"id": "timing-test", "version": 1,
                                                   "name": "Timing device", "parts": inner.snapshot()}))
    positions = {port["name"]: pos for pos, port in circuit.terminals.items()}
    circuit.connect(positions["A"], (6, 3), 0)
    circuit.connect(positions["B"], (6, 3), 1)
    circuit.connect((6, 3), positions["OUT"], 0)
    return circuit


class SequentialChallengeTests(unittest.TestCase):
    def assert_passes(self, circuit, key):
        rows = sequential.run_tests(circuit, key)
        self.assertGreater(len(rows), 1)
        self.assertTrue(all(row.passed for row in rows), [(row.label, row.expected, row.actual) for row in rows if not row.passed])

    def test_authored_challenges_accept_their_basic_solutions(self):
        for key, challenge in sequential.CHALLENGES.items():
            with self.subTest(key=key):
                self.assert_passes(solution(challenge.required_kind), key)

    def test_nested_devices_allow_propagation_and_clock_phase(self):
        for key, challenge in sequential.CHALLENGES.items():
            with self.subTest(key=key):
                self.assert_passes(nested(solution(challenge.required_kind)), key)

    def test_no_live_state_or_nested_memory_changes_during_tests(self):
        for key, challenge in sequential.CHALLENGES.items():
            with self.subTest(key=key):
                circuit = nested(solution(challenge.required_kind))
                circuit.switches.update(A=53, B=1)
                for _ in range(23):
                    circuit.tick()
                state = deepcopy(circuit.runtime_snapshot())
                design = circuit.snapshot()
                sequential.run_tests(circuit, key)
                self.assertEqual(circuit.runtime_snapshot(), state)
                self.assertEqual(circuit.snapshot(), design)

    def test_disconnected_required_parts_do_not_pass(self):
        for key, challenge in sequential.CHALLENGES.items():
            with self.subTest(key=key):
                circuit = solution(challenge.required_kind)
                out = next(pos for pos, port in circuit.terminals.items() if port["output"])
                circuit.disconnect(out, 0)
                self.assertFalse(all(row.passed for row in sequential.run_tests(circuit, key)))

    def test_missing_component_and_nonstandard_terminals_are_explained(self):
        rows = sequential.run_tests(Circuit(), "memory")
        self.assertEqual(rows[0].actual, "Missing component")
        circuit = Circuit(terminals=edge_terminals(("A",), ("X",)))
        rows = sequential.run_tests(circuit, "counter")
        self.assertEqual(rows[0].actual, "Missing terminal")

    def test_register_data_bypass_is_not_memory(self):
        circuit = solution("REGISTER")
        positions = {port["name"]: pos for pos, port in circuit.terminals.items()}
        circuit.connect(positions["A"], positions["OUT"], 0)
        rows = sequential.run_tests(circuit, "memory")
        self.assertFalse(all(row.passed for row in rows))
        self.assertFalse(rows[1].passed)
        self.assertFalse(rows[3].passed)

    def test_counter_signal_bypass_does_not_count_edges(self):
        circuit = solution("COUNTER")
        positions = {port["name"]: pos for pos, port in circuit.terminals.items()}
        circuit.connect(positions["A"], positions["OUT"], 0)
        rows = sequential.run_tests(circuit, "counter")
        self.assertFalse(all(row.passed for row in rows))
        self.assertFalse(next(row for row in rows if row.label == "Second delivery").passed)

    def test_clock_must_remain_independent_of_manual_inputs(self):
        circuit = solution("CLOCK")
        positions = {port["name"]: pos for pos, port in circuit.terminals.items()}
        circuit.set_part((9, 3), Part("AND"))
        circuit.connect((6, 3), (9, 3), 0)
        circuit.connect(positions["A"], (9, 3), 1)
        circuit.connect((9, 3), positions["OUT"], 0)
        self.assertFalse(all(row.passed for row in sequential.run_tests(circuit, "clock")))

    def test_clock_can_be_inverted_without_imposing_a_fixed_phase(self):
        circuit = solution("CLOCK")
        out = next(pos for pos, port in circuit.terminals.items() if port["output"])
        circuit.set_part((9, 3), Part("NOT"))
        circuit.connect((6, 3), (9, 3), 0)
        circuit.connect((9, 3), out, 0)
        self.assert_passes(circuit, "clock")


if __name__ == "__main__":
    unittest.main()
