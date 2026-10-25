import json
import unittest
from copy import deepcopy

from circuit import Circuit, Part, SEQUENTIAL, edge_terminals


def machine(kind, rotation=0):
    circuit = Circuit(terminals=edge_terminals(("A", "B")))
    circuit.set_part((5, 4), Part(kind, rotation))
    terminals = {port['name']: pos for pos, port in circuit.terminals.items()}
    if kind != 'CLOCK':
        circuit.connect(terminals['A'], (5, 4), 0)
        circuit.connect(terminals['B'], (5, 4), 1)
    circuit.connect((5, 4), terminals['OUT'], 0)
    return circuit


def run(circuit, a, b, ticks=4):
    circuit.switches.update(A=a, B=b)
    for _ in range(ticks):
        circuit.tick()
    return circuit.output_value()


class SequentialCircuitTests(unittest.TestCase):
    def test_clock_has_fixed_period_and_output_propagation(self):
        circuit = machine('CLOCK')
        local, output = [], []
        for _ in range(8):
            circuit.tick()
            local.append(circuit.active[(5, 4)])
            output.append(circuit.output_value())
        self.assertEqual(local, [0, 1, 1, 0, 0, 1, 1, 0])
        self.assertEqual(output, [0, 0, 1, 1, 0, 0, 1, 1])
        self.assertEqual(Part('CLOCK', 1).ports(), ((), (2,)))

    def test_register_holds_until_next_rising_edge_in_every_rotation(self):
        for rotation in range(4):
            with self.subTest(rotation=rotation):
                circuit = machine('REGISTER', rotation)
                self.assertEqual(run(circuit, 42, 0), 0)
                self.assertEqual(run(circuit, 42, 1), 42)
                self.assertEqual(run(circuit, 99, 1, 9), 42)
                self.assertEqual(run(circuit, 123, 0), 42)
                self.assertEqual(run(circuit, 65535, 1), 65535)
                self.assertEqual(run(circuit, 65536, 0), 65535)
                self.assertEqual(run(circuit, 65536, 1), 0)

    def test_counter_edges_reset_priority_and_held_reset_release(self):
        circuit = machine('COUNTER')
        self.assertEqual(run(circuit, 1, 0), 1)
        self.assertEqual(run(circuit, 1, 0, 20), 1)
        self.assertEqual(run(circuit, 0, 0), 1)
        self.assertEqual(run(circuit, 1, 0), 2)
        self.assertEqual(run(circuit, 0, 0), 2)
        self.assertEqual(run(circuit, 1, 1), 0)
        self.assertEqual(run(circuit, 1, 0), 0)
        self.assertEqual(run(circuit, 0, 0), 0)
        self.assertEqual(run(circuit, 1, 0), 1)

    def test_counter_wraps_and_reset_clears_memory_edges_and_clock_phase(self):
        circuit = machine('COUNTER')
        circuit.active[(5, 4)] = 65535
        self.assertEqual(run(circuit, 1, 0), 0)
        for kind in SEQUENTIAL:
            circuit = machine(kind)
            run(circuit, 5, 1, 7)
            circuit.reset()
            self.assertEqual(circuit.tick_count, 0)
            self.assertFalse(any(circuit.active.values()))
            self.assertFalse(any(circuit.edge_high.values()))

    def test_clock_drives_register_and_counter_using_previous_tick_signals(self):
        circuit = machine('COUNTER')
        circuit.set_part((3, 2), Part('CLOCK'))
        circuit.connect((3, 2), (5, 4), 0)
        self.assertEqual(run(circuit, 0, 0, 7), 1)
        circuit.tick()
        self.assertEqual(circuit.output_value(), 2)

    def test_runtime_json_roundtrip_continues_mid_edge_and_inflight_pipe_delay(self):
        for kind in SEQUENTIAL:
            with self.subTest(kind=kind):
                circuit = machine(kind)
                # Add an unconnected pipe route to retain delay histories.
                circuit.set_part((6, 4), Part('PIPE'))
                circuit.set_part((7, 4), Part('PIPE'))
                run(circuit, 24, 1, 3)
                restored = Circuit.from_snapshot(circuit.snapshot())
                restored.restore_runtime(json.loads(json.dumps(circuit.runtime_snapshot())))
                self.assertEqual(restored.runtime_snapshot(), circuit.runtime_snapshot())
                for a, b in ((2, 1), (0, 0), (55, 1), (1, 0)):
                    for _ in range(7):
                        run(circuit, a, b, 1)
                        run(restored, a, b, 1)
                        self.assertEqual(restored.runtime_snapshot(), circuit.runtime_snapshot())

    def test_nested_counters_are_independent_and_preserve_runtime(self):
        inner = machine('COUNTER')
        definition = {'id': 91, 'version': 1, 'parts': inner.snapshot()}
        outer = Circuit(terminals=edge_terminals(('A', 'B')))
        for pos in ((5, 3), (8, 5)):
            outer.set_part(pos, Part('DEVICE', device=definition))
        inputs = {port['name']: pos for pos, port in outer.terminals.items()}
        outer.connect(inputs['A'], (5, 3), 0)
        outer.connect(inputs['B'], (8, 5), 0)
        run(outer, 1, 0, 9)
        self.assertEqual(outer.devices[(5, 3)].output_value(), 1)
        self.assertEqual(outer.devices[(8, 5)].output_value(), 0)
        restored = Circuit.from_snapshot(outer.snapshot())
        restored.restore_runtime(json.loads(json.dumps(outer.runtime_snapshot())))
        for a, b in ((1, 1), (0, 1), (1, 0), (0, 0)):
            run(outer, a, b, 9)
            run(restored, a, b, 9)
            self.assertEqual(outer.runtime_snapshot(), restored.runtime_snapshot())
        outer.reset()
        self.assertEqual(outer.devices[(5, 3)].output_value(), 0)

    def test_library_schematic_copies_start_empty_without_changing_live_memory(self):
        original = machine('REGISTER')
        run(original, 54321, 1, 7)
        before = original.runtime_snapshot()
        schematic = json.loads(json.dumps(original.snapshot()))
        loaded = Circuit.from_snapshot(schematic)
        self.assertEqual(loaded.snapshot(), original.snapshot())
        self.assertEqual(loaded.tick_count, 0)
        self.assertEqual(loaded.output_value(), 0)
        placed = Circuit({(5, 4): Part('DEVICE', device={'parts': schematic})})
        self.assertEqual(placed.devices[(5, 4)].output_value(), 0)
        self.assertEqual(original.runtime_snapshot(), before)

    def test_runtime_rejects_bad_layout_or_history_without_partial_mutation(self):
        circuit = machine('REGISTER')
        run(circuit, 123, 1)
        before = circuit.runtime_snapshot()
        for change in ('layout', 'history', 'edge', 'switches', 'clock'):
            bad = deepcopy(before)
            if change == 'layout':
                bad['layout'] = []
            elif change == 'history':
                bad['histories']['5,4'] = []
            elif change == 'edge':
                bad['edge_high']['5,4'] = 10
            elif change == 'switches':
                bad['switches']['A'] = -1
            else:
                bad['tick_count'] = -1
            with self.assertRaises(ValueError):
                circuit.restore_runtime(bad)
            self.assertEqual(circuit.runtime_snapshot(), before)

    def test_timed_tests_check_holding_behavior_and_preserve_live_state(self):
        circuit = machine('REGISTER')
        run(circuit, 31, 1, 9)
        before = circuit.runtime_snapshot()
        rows = circuit.sequence_test_results([
            {'inputs': {'A': 12, 'B': 0}, 'ticks': 4, 'expected': 0},
            {'inputs': {'B': 1}, 'ticks': 4, 'expected': 12},
            {'inputs': {'A': 99}, 'ticks': 4, 'expected': 12},
            {'inputs': {'B': 0}, 'ticks': 4, 'expected': 12},
            {'inputs': {'B': 1}, 'ticks': 4, 'expected': 99},
        ])
        self.assertTrue(all(row.passed for row in rows))
        self.assertEqual([row.elapsed for row in rows], [4, 8, 12, 16, 20])
        self.assertEqual(circuit.runtime_snapshot(), before)
        with self.assertRaises(ValueError):
            circuit.sequence_test_results([{'inputs': {'C': 4}, 'ticks': 1, 'expected': 0}])
        self.assertEqual(circuit.runtime_snapshot(), before)

    def test_truth_tables_cannot_mistake_clock_or_memory_for_stable_logic(self):
        for kind in SEQUENTIAL:
            circuit = machine(kind)
            before = circuit.runtime_snapshot()
            self.assertFalse(circuit.evaluate(0, 0)[1])
            self.assertFalse(any(row.stable for row in circuit.commission_test_results('AND')))
            self.assertEqual(circuit.runtime_snapshot(), before)
        inner = machine('CLOCK')
        circuit = Circuit({(5, 4): Part('DEVICE', device={'parts': inner.snapshot()})})
        self.assertTrue(circuit.has_sequential())
        self.assertFalse(circuit.evaluate(0, 0)[1])


if __name__ == '__main__':
    unittest.main()
