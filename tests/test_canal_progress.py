"""Canal progression respects real expedition, circuit, goods and saved state."""
import json
import unittest
from copy import deepcopy
from dataclasses import asdict

from circuit import Circuit, Part, edge_terminals
from economy import Village
import adventure
import boiler_tower
import canal_progress as canal
import manufacturing


def completed_village():
    village = Village()
    adventure.state(village)['expansion_complete'] = True
    boiler_tower.state(village)['complete'] = True
    manufacturing.state(village)['unlocks'] = ['precision_machine', 'steam_accumulator']
    return village


def boat_design():
    """Private test fixture only; no proposed board is supplied in the game."""
    circuit = Circuit(terminals=edge_terminals(('A', 'B', 'C')))
    ports = {port['name']: pos for pos, port in circuit.terminals.items()}
    number = 0

    def gate(name, kind, *sources, value=1):
        nonlocal number
        position = (2 + number // 4 * 2, 1 + number % 4 * 2)
        number += 1
        ports[name] = position
        circuit.parts[position] = Part(kind, value=value)
        for pin, source in enumerate(sources):
            circuit.connect(ports[source], position, pin)

    gate('minimum', 'CONSTANT', value=4)
    gate('maximum', 'CONSTANT', value=10)
    gate('one', 'CONSTANT', value=1)
    gate('low', 'GT', 'minimum', 'A')
    gate('high', 'GT', 'A', 'maximum')
    gate('bad', 'OR', 'low', 'high')
    gate('pressure', 'NOT', 'bad')
    gate('clear', 'EQ', 'C', 'one')
    gate('safe', 'AND', 'pressure', 'clear')
    gate('feed', 'MUL', 'B', 'safe')
    circuit.connect(ports['feed'], ports['OUT'], 0)
    return circuit


class CanalProgressTests(unittest.TestCase):
    def test_both_expanded_expeditions_and_permanent_rewards_are_required(self):
        village = Village()
        self.assertFalse(canal.unlocked(village))
        adventure.state(village)['artifact'] = True
        manufacturing.state(village)['unlocks'] = ['precision_machine', 'steam_accumulator']
        boiler_tower.state(village)['complete'] = True
        self.assertFalse(canal.unlocked(village))
        adventure.state(village)['expansion_complete'] = True
        self.assertTrue(canal.unlocked(village))
        for removed in ('precision_machine', 'steam_accumulator'):
            manufacturing.state(village)['unlocks'].remove(removed)
            self.assertFalse(canal.unlocked(village))
            manufacturing.state(village)['unlocks'].append(removed)

    def test_repair_consumes_exactly_one_real_gear_and_keeps_rewards(self):
        village = completed_village()
        workshop = manufacturing.state(village)
        self.assertFalse(canal.repair(village)[0])
        workshop['goods']['precision_gears'] = 2
        before = deepcopy(workshop['unlocks'])
        self.assertTrue(canal.repair(village)[0])
        self.assertEqual(workshop['goods']['precision_gears'], 1)
        self.assertEqual(workshop['unlocks'], before)
        self.assertFalse(canal.repair(village)[0])
        self.assertEqual(workshop['goods']['precision_gears'], 1)
        self.assertTrue(canal.state(village)['boat_repaired'])
        self.assertFalse(canal.can_travel(village))

    def test_certification_checks_every_pressure_request_and_status(self):
        circuit = boat_design()
        circuit.tick()
        before = deepcopy(circuit.runtime_snapshot())
        self.assertEqual(len(canal.cases()), 208)
        self.assertTrue(canal.certify(circuit.snapshot())[0])
        self.assertEqual(circuit.runtime_snapshot(), before)
        for pressure, request, status, expected in canal.cases():
            self.assertEqual(circuit.evaluate(pressure, request, status), (expected, True))
        for inputs, expected in (((4, 3, 1), 3), ((10, 3, 1), 3),
                                 ((3, 3, 1), 0), ((11, 3, 1), 0),
                                 ((8, 3, 3), 0), ((8, 0, 1), 0)):
            self.assertEqual(circuit.evaluate(*inputs), (expected, True))

    def test_flag_blank_or_departure_only_shortcut_never_unlocks_travel(self):
        village = completed_village()
        canal.state(village)['boat_repaired'] = True
        field = adventure.state(village)
        field[canal.KIND] = True
        self.assertFalse(canal.can_travel(village))
        circuit = Circuit(terminals=edge_terminals(('A', 'B', 'C')))
        self.assertFalse(canal.install(village, circuit.snapshot())[0])
        ports = {port['name']: pos for pos, port in circuit.terminals.items()}
        circuit.connect(ports['B'], ports['OUT'], 0)
        self.assertEqual(circuit.evaluate(*canal.DEPARTURE_READINGS), (2, True))
        field['designs'][canal.KIND] = circuit.snapshot()
        self.assertFalse(canal.can_travel(village))
        self.assertEqual(canal.output(village), 0)

    def test_installed_design_is_copied_and_rechecked_if_saved_board_changes(self):
        village = completed_village()
        canal.state(village)['boat_repaired'] = True
        snapshot = boat_design().snapshot()
        self.assertTrue(canal.install(village, snapshot)[0])
        snapshot.clear()
        self.assertTrue(canal.can_travel(village))
        self.assertEqual(canal.output(village, (8, 3, 3)), 0)
        self.assertEqual(canal.output(village, (10, 3, 1)), 3)
        saved = adventure.state(village)['designs'][canal.KIND]
        next(row for row in saved if row.get('kind') == 'CONSTANT' and row['value'] == 4)['value'] = 5
        self.assertFalse(canal.can_travel(village))

    def test_legacy_save_and_progress_roundtrip_keep_exact_state(self):
        village = completed_village()
        workshop = manufacturing.state(village)
        workshop['goods']['precision_gears'] = 1
        canal.repair(village)
        canal.install(village, boat_design().snapshot())
        current = canal.state(village)
        current.update(visited=True, position=[1700.25, 900.5], met=['Mara'], trips=2)
        current['market_bread'] = 4
        loaded = Village(**json.loads(json.dumps(asdict(village))))
        self.assertEqual(canal.state(loaded), current)
        self.assertTrue(canal.can_travel(loaded))
        self.assertEqual(loaded.manufacturing, village.manufacturing)
        self.assertFalse(canal.state(Village())['boat_repaired'])
        self.assertEqual(canal.state(Village())['met'], [])

    def test_request_moves_real_goods_and_budget_once_even_after_reload(self):
        village = completed_village()
        current = canal.state(village)
        current['visited'] = True
        workshop = manufacturing.state(village)
        workshop['goods'].update(repair_kits=3, steam_valves=1)
        total = village.coins + current['market_cash']
        self.assertTrue(canal.deliver_request(village)[0])
        self.assertEqual(village.coins + current['market_cash'], total)
        self.assertEqual(workshop['goods']['repair_kits'], 1)
        self.assertEqual(workshop['goods']['steam_valves'], 0)
        self.assertEqual(current['delivered_goods'], canal.REQUEST_GOODS)
        self.assertTrue(current['clue_found'])
        self.assertTrue(current['request_complete'])
        loaded = Village(**json.loads(json.dumps(asdict(village))))
        before = deepcopy(asdict(loaded))
        self.assertFalse(canal.deliver_request(loaded)[0])
        self.assertEqual(asdict(loaded), before)

    def test_request_failure_and_clue_observation_do_not_award_or_spend(self):
        village = completed_village()
        current = canal.state(village)
        workshop = manufacturing.state(village)
        workshop['goods'].update(repair_kits=2, steam_valves=0)
        self.assertFalse(canal.discover_clue(village))
        current['visited'] = True
        before = deepcopy(asdict(village))
        self.assertFalse(canal.deliver_request(village)[0])
        self.assertEqual(asdict(village), before)
        self.assertTrue(canal.discover_clue(village))
        self.assertFalse(canal.discover_clue(village))
        self.assertEqual(village.coins, before['coins'])
        self.assertFalse(current['request_complete'])

    def test_market_has_finite_saved_stock_and_conserves_cash(self):
        village = completed_village()
        current = canal.state(village)
        self.assertFalse(canal.buy_bread(village)[0])
        current['visited'] = True
        village.coins = 48
        total = village.coins + current['market_cash']
        for _ in range(6):
            self.assertTrue(canal.buy_bread(village)[0])
        self.assertEqual(village.player_bread, 6)
        self.assertEqual(current['market_bread'], 0)
        self.assertEqual(village.coins + current['market_cash'], total)
        before = deepcopy(asdict(village))
        self.assertFalse(canal.buy_bread(village)[0])
        self.assertEqual(asdict(village), before)


if __name__ == '__main__':
    unittest.main()
