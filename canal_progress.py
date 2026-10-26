"""Saved canal access, boat controller and the first modest Reedhaven trade.

The two expedition rewards remain permanent capabilities. Only the replacement
gear and delivered workshop goods are consumed; travel itself has no toll.
"""
from collections import OrderedDict
from copy import deepcopy
import json

from circuit import Circuit, CONDUCTORS
import manufacturing

KIND = 'canal_boat'
DEPARTURE_READINGS = (8, 2, 1)
PORT_NAMES = {'A': 'Boiler pressure', 'B': 'Steam request',
              'C': 'Departure status', 'OUT': 'Steam feed'}
REQUEST_GOODS = {'repair_kits': 2, 'steam_valves': 1}
REQUEST_REWARD = 32
BREAD_PRICE = 8
_TRIALS = OrderedDict()


def state(village):
    current = manufacturing.state(village).setdefault('canal', {})
    for key, value in dict(visited=False, position=[2370., 460.],
                           boat_repaired=False, trips=0, request_complete=False,
                           clue_found=False, met=[], market_cash=80, market_bread=6,
                           delivered_goods={}, visual_time=0.).items():
        current.setdefault(key, deepcopy(value))
    return current


def unlocked(village):
    """A legacy archive award alone does not skip the expanded expeditions."""
    workshop = manufacturing.state(village)
    return bool(workshop.get('adventure', {}).get('expansion_complete')
                and workshop.get('boiler_tower', {}).get('complete')
                and {'precision_machine', 'steam_accumulator'} <= set(workshop['unlocks']))


def specification():
    return ('Canal boat / departure controller', (
        'A: boiler pressure (0–12). B: requested steam feed (0–3).',
        'C: departure status: 0 moored, 1 clear, 2 fault, 3 clear + fault.',
        'OUT must equal B when pressure is 4 through 10 and C is exactly 1.',
        'At every other pressure or status, OUT must be 0.',
        'Use a combinational circuit. Test before leaving the landing.'))


def cases():
    return [(a, b, c, b if 4 <= a <= 10 and c == 1 else 0)
            for a in range(13) for b in range(4) for c in range(4)]


def _trial(snapshot):
    """Cache only runtime objects; an exact snapshot change always rechecks it."""
    try:
        key = json.dumps(snapshot, sort_keys=True, separators=(',', ':'))
        if key in _TRIALS:
            _TRIALS.move_to_end(key)
            return _TRIALS[key]
        trial = Circuit.from_snapshot(snapshot)
        if trial.has_sequential():
            return None, 'This interface requires a combinational circuit.', {}
        if set(trial.switches) != {'A', 'B', 'C'}:
            return None, 'Keep the three boat input terminals.', {}
        if [p['name'] for p in trial.terminals.values() if p['output']] != ['OUT']:
            return None, 'Keep the boat OUT terminal.', {}
        outputs = {}
        # The same true fixed-point check as field certification, avoiding the
        # expensive history evaluator only for explicit, stateless gate traces.
        fast = trial.trace_mode and not any(p.kind in (*CONDUCTORS, 'DEVICE')
                                           for p in trial.parts.values())
        for a, b, c, expected in cases():
            if fast:
                trial.switches.update(A=a, B=b, C=c)
                trial.reset()
                stable = False
                for _ in range(trial.settle_budget()):
                    previous = trial.active
                    trial.tick()
                    if trial.active == previous:
                        stable = True
                        break
                actual = trial.output_value()
            else:
                actual, stable = trial.evaluate(a, b, c)
            if actual != expected or not stable:
                result = (None, f'A={a} B={b} C={c}: expected {expected}, got {actual}'
                          + (' (unstable)' if not stable else ''), {})
                break
            outputs[(a, b, c)] = actual
        else:
            result = (trial, f'{len(outputs)} operating conditions verified.', outputs)
        _TRIALS[key] = result
        while len(_TRIALS) > 12:
            _TRIALS.popitem(last=False)
        return result
    except (TypeError, ValueError, KeyError, AttributeError, RecursionError):
        return None, 'The saved boat controller could not be read. Rebuild it at the landing.', {}


def certify(snapshot):
    trial, message, _ = _trial(snapshot)
    return trial is not None, message


def repair(village):
    current = state(village)
    if not unlocked(village):
        return False, 'Finish Mosswater and Boiler Tower to restore the canal boat.'
    if current['boat_repaired']:
        return False, 'The replacement gear is already fitted.'
    goods = manufacturing.state(village)['goods']
    if goods['precision_gears'] < 1:
        return False, 'Make one precision gear in your workshop, then bring it to the landing.'
    goods['precision_gears'] -= 1
    current['boat_repaired'] = True
    manufacturing._event(village, 'Fitted a workshop-made precision gear to the canal boat. The recovered cutter and accumulator remain available in the workshop.')
    return True, 'Replacement gear fitted. Build and test the boat controller to depart.'


def install(village, snapshot):
    if not unlocked(village):
        return False, 'Finish Mosswater and Boiler Tower before restoring the boat.'
    ok, message = certify(snapshot)
    if not ok:
        return False, message
    # Keep the editor's field drafts and installed boards in their established
    # location, including nested device snapshots, instead of a second format.
    import adventure
    field = adventure.state(village)
    field[KIND] = True
    field['designs'][KIND] = deepcopy(snapshot)
    return True, message


def output(village, inputs=DEPARTURE_READINGS):
    snapshot = manufacturing.state(village).get('adventure', {}).get('designs', {}).get(KIND)
    if snapshot is None:
        return 0
    trial, _, outputs = _trial(snapshot)
    if trial is None or tuple(inputs) not in outputs:
        return 0
    return outputs[tuple(inputs)]


def can_travel(village):
    return bool(unlocked(village) and state(village)['boat_repaired']
                and output(village, DEPARTURE_READINGS) == DEPARTURE_READINGS[1])


def status(village):
    if not unlocked(village):
        return 'Finish Mosswater and Boiler Tower to open the canal route.'
    if not state(village)['boat_repaired']:
        return 'The boat needs one precision gear from your workshop.'
    if not can_travel(village):
        return 'Fit and test a departure controller at the boat.'
    return 'Boat ready. Travel to Reedhaven.'


def discover_clue(village):
    current = state(village)
    if not current['visited'] or current['clue_found']:
        return False
    current['clue_found'] = True
    manufacturing._event(village, 'Reedhaven records point upstream to the old waterworks pressure network.')
    return True


def deliver_request(village):
    current = state(village)
    if not current['visited']:
        return False, 'Visit Reedhaven to speak with its lockkeeper.'
    if current['request_complete']:
        return False, 'The cistern repair has already been supplied.'
    goods = manufacturing.state(village)['goods']
    if any(goods[key] < count for key, count in REQUEST_GOODS.items()):
        return False, 'The cistern needs two repair kits and one steam valve from your workshop.'
    if current['market_cash'] < REQUEST_REWARD:
        return False, 'Reedhaven cannot fund the repair yet.'
    for key, count in REQUEST_GOODS.items():
        goods[key] -= count
        current['delivered_goods'][key] = current['delivered_goods'].get(key, 0) + count
    current['market_cash'] -= REQUEST_REWARD
    village.coins += REQUEST_REWARD
    workshop = manufacturing.state(village)
    workshop['sold'] += sum(REQUEST_GOODS.values())
    workshop['earned'] += REQUEST_REWARD
    current['request_complete'] = True
    discover_clue(village)
    village._record_trade('Your Workshop', 'Reedhaven Cistern', 'cistern repair supplies',
                          sum(REQUEST_GOODS.values()), REQUEST_REWARD,
                          products=deepcopy(REQUEST_GOODS))
    manufacturing._event(village, 'Supplied Reedhaven cistern repairs for 32c; the lockkeeper shares the upstream waterworks records.')
    return True, 'Cistern supplies delivered. Received 32c and the upstream waterworks lead.'


def buy_bread(village):
    current = state(village)
    if not current['visited']:
        return False, 'Visit the Reedhaven market to buy bread.'
    if current['market_bread'] < 1:
        return False, 'Sela has sold the last loaf from this shipment.'
    if village.coins < BREAD_PRICE:
        return False, 'A loaf costs 8c.'
    village.coins -= BREAD_PRICE
    current['market_cash'] += BREAD_PRICE
    current['market_bread'] -= 1
    village.player_bread += 1
    village._record_trade('Reedhaven Market', 'Boole', 'bread', 1, BREAD_PRICE)
    return True, 'Bought one loaf for 8c.'
