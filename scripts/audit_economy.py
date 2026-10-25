"""Repeatable headless economic soak checks; never reads or writes player saves."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
import json
import sys
from pathlib import Path
from dataclasses import asdict
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from economy import Village
from town import Town
from game import village_from_data
from daily_life import update_continuous, state, SHIFT_SECONDS


def cash(v):
    return v.coins + v.rival_cash + sum(f['cash'] for f in v.businesses.values()) + sum(h['cash'] for h in v.households.values())


def differences(a, b, path=''):
    if type(a) is not type(b):
        return [(path, a, b)]
    if isinstance(a, dict):
        return [item for key in a.keys() | b.keys() for item in differences(a.get(key), b.get(key), path + '/' + str(key))]
    if isinstance(a, list):
        if len(a) != len(b):
            return [(path + '/length', len(a), len(b))]
        return [item for i,(x,y) in enumerate(zip(a,b)) for item in differences(x,y,path + '/' + str(i))]
    return [] if a == b else [(path, a, b)]


def run(name, upgrades=(), service=False, days=365, deliver_later=False):
    v, town = Village(), Town()
    for job in upgrades:
        getattr(v, f'complete_{job}_job')()
    if service:
        v.toggle_service()
    result = {'scenario': name, 'days': days, 'violations': [], 'checkpoints': []}
    for index in range(days):
        day, before = v.day, cash(v)
        if deliver_later:
            for key, offer in list(v.offers.items()):
                if offer.get('status') in ('open', 'bid'):
                    v.fulfill_job(key)
        update_continuous(v, town, 180)
        entries = next(h['entries'] for h in v.trade_history if h['day'] == day)
        outside = sum(t.get('cash_delta', t['coins']) for t in entries if t['to'] == 'Traveling Mechanic' or t.get('external'))
        for event in v.migration_events:
            if event['day'] == day:
                if event['kind'] == 'arrival':
                    outside += event.get('savings', 0)
                elif event['kind'] == 'departure':
                    outside += event.get('savings', 0)
        if cash(v) - before != outside:
            result['violations'].append({'day': day, 'type': 'unexplained_cash_change', 'actual': cash(v)-before, 'expected': outside})
        for key, firm in v.businesses.items():
            if firm['cash'] < 0 or any(n < 0 for n in firm['stock'].values()):
                result['violations'].append({'day': day, 'type': 'negative_business_balance', 'firm': key})
        if any(h['cash'] < 0 for h in v.households.values()):
            result['violations'].append({'day': day, 'type': 'negative_household_cash'})
        if any(n > SHIFT_SECONDS for n in v.last_day_report['worked'].values()):
            result['violations'].append({'day': day, 'type': 'uncapped_shift'})
        if index + 1 in (7, 30, 90, 180, days):
            result['checkpoints'].append({'day': day, 'population': len(v.citizens),
                'household_cash': {k:h['cash'] for k,h in v.households.items()},
                'firm_cash': {k:f['cash'] for k,f in v.businesses.items()},
                'fed': v.last_day_report['fed'], 'homes': v.last_day_report['households'],
                'sold': v.last_day_report['sold'], 'produced': v.last_day_report['produced'],
                'bread_price': v.bread_price, 'delivered_contracts': sum(o.get('status') in ('player', 'rival') for o in v.offers.values()), 'jun': v.businesses.get('east_bakery', {}).get('operating_state'),
                'largest_stock': max((n, k, good) for k,f in v.businesses.items() for good,n in f['stock'].items())})
    loaded = village_from_data(json.loads(json.dumps(asdict(v))))
    result['load_differences'] = differences(asdict(v), asdict(loaded))[:15]
    update_continuous(v, town, 63.25)
    update_continuous(loaded, Town(), 63.25)
    result['save_continuation_equal'] = asdict(v) == asdict(loaded)
    result['continuation_differences'] = differences(asdict(v), asdict(loaded))[:15]
    a, b = asdict(v), asdict(loaded)
    a.pop('journal', None)
    b.pop('journal', None)
    result['economic_continuation_equal'] = a == b
    return result


def main():
    scenarios = [('unassisted', (), False), ('mill_upgrade', ('mill',), False),
                 ('all_upgrades', ('mill','bakery','vent','market','pump','sorter'), False),
                 ('all_upgrades_service', ('mill','bakery','vent','market','pump','sorter'), True),
                 ('all_18_player_deliveries', ('mill','bakery','vent','market','pump','sorter'), False),
                 ('all_18_player_service', ('mill','bakery','vent','market','pump','sorter'), True)]
    results = []
    for name, upgrades, service in scenarios:
        result = run(name, upgrades, service, deliver_later=name.startswith("all_18"))
        results.append(result)
        print(name, 'violations', len(result['violations']), 'save_equal', result['save_continuation_equal'], flush=True)
    output = ROOT / 'testing-screenshots' / 'economy-audit'
    output.mkdir(parents=True, exist_ok=True)
    (output / 'report.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(output / 'report.json')


if __name__ == '__main__':
    main()
