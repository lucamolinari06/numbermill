"""Evidence-led entrants on a reusable site, with accountable owner capital."""

KEY = 'east_bakery'
ENTRY_DAYS = 3
CAPITAL = 80
RECOVERY_CAPITAL = 20

# A site has no assigned trade. Candidate profiles differ in output, price and scale.
ENTREPRENEURS = (
    {'owner': 'Jun', 'kind': 'bakery', 'name': "Jun's East Bakery", 'capacity': 2, 'price': 6},
    {'owner': 'Anika', 'kind': 'fuel', 'name': "Anika's Fuel Depot", 'capacity': 4, 'price': 2},
    {'owner': 'Silas', 'kind': 'parts', 'name': "Silas's Repair Works", 'capacity': 2, 'price': 4},
    {'owner': 'Mei', 'kind': 'bakery', 'name': "Mei's Hearth", 'capacity': 3, 'price': 5},
    {'owner': 'Orson', 'kind': 'fuel', 'name': "Orson's Steam Supply", 'capacity': 3, 'price': 2},
    {'owner': 'Bea', 'kind': 'parts', 'name': "Bea's Parts Counter", 'capacity': 3, 'price': 5},
)
EXIT_DAYS = 18


def candidate_for(village):
    """After the first tenant, favour a trade whose actual stock is scarce."""
    from economy import BUSINESS_TYPES
    review = village.competition
    cursor = review.get('candidate_cursor', 1)
    choices = []
    for offset in range(len(ENTREPRENEURS)):
        index = (cursor + offset) % len(ENTREPRENEURS)
        profile = ENTREPRENEURS[index]
        if profile['owner'] == review.get('last_owner'):
            continue
        good = BUSINESS_TYPES[profile['kind']]['output']
        stock = sum(f['stock'].get(good, 0) for f in village.businesses.values())
        if profile['kind'] == 'bakery':
            ready = (village.last_day_report.get('sold', 0) >= 3
                     and sum(h['bread_need'] for h in village.households.values()) >= profile['capacity'] + 2
                     and village.businesses['mill']['stock'].get('flour', 0) >= 2)
            need = 8 - stock
        elif profile['kind'] == 'fuel':
            ready = any(f.get('machines') for f in village.businesses.values())
            need = 12 - stock
        else:
            ready = village.day >= 7 and village.businesses['fuel_yard']['stock'].get('fuel', 0) >= 2
            need = 6 - stock
        if ready and need > 0:
            choices.append((need, -offset, index, profile))
    return max(choices, key=lambda choice: choice[:2])[2:] if choices else (None, None)


def release_site(village, firm):
    cash = firm['cash']
    owner = firm['owner']
    # Unsold goods go with their owner, rather than becoming free local stock.
    village._record_trade(firm['name'], f'{owner} (departing owner)', 'capital withdrawal', 1,
                          cash, external=True, cash_delta=-cash, purpose='Owner leaves with remaining cash and inventory')
    event(village, 'departure', f"{owner} left after {EXIT_DAYS} closed days; the site is available to another trade. Took {cash}c and remaining inventory.", -cash)
    del village.businesses[KEY]
    village.competition.update(cooldown_until=village.day + 3, qualifying_days=0, last_owner=owner,
                               has_had_tenant=True, candidate_owner=None)
    village.competition_status = 'The site is vacant. New applicants will review demand after three days.'


def review_successor(village, firm):
    """Retained cash may bridge slow days, but cannot indefinitely hold a site."""
    from economy import BUSINESS_TYPES
    lifecycle_defaults(firm)
    good = BUSINESS_TYPES[firm['kind']]['output']
    sold = sum(t['units'] for t in village.daily_trades if t['from'] == firm['name'] and t['good'] == good)
    losses = firm['cash'] < firm['review_cash']
    firm['hardship_days'] = firm['hardship_days'] + 1 if losses or sold == 0 else 0
    if firm['operating_state'] == 'open' and firm['hardship_days'] >= 5:
        firm.update(operating_state='paused', recovery_days=0)
        event(village, 'closure', f"{firm['owner']} paused {firm['name']} after five unprofitable trading days.")
    if firm['operating_state'] == 'paused':
        # Stock clearance can establish a real paying order; no repeated rescue grants.
        firm['recovery_days'] = firm['recovery_days'] + 1 if sold and firm['cash'] >= 10 else 0
        if firm['recovery_days'] >= 2:
            firm.update(operating_state='open', hardship_days=0, closed_days=0)
            event(village, 'reopening', f"{firm['owner']} reopened using retained cash after two days of paid orders.")
    firm['review_cash'] = firm['cash']
    firm['owner_decision'] = f"Paying {2 if firm['kind'] == 'bakery' else 1}c daily site rent; orders must cover supplies and rent."
    firm['operating_status'] = f"{sold} {good} sold; {firm['operating_state']}; hardship {firm['hardship_days']}/5"
    village.competition_status = f"{firm['name']}: {firm['operating_status']}."


def review_occupant(village, firm):
    landlord = village.businesses['bakery' if firm['kind'] == 'bakery' else 'market']
    rent = min(2 if firm['kind'] == 'bakery' else 1, firm['cash'])
    if rent:
        firm['cash'] -= rent
        landlord['cash'] += rent
        village._record_trade(firm['name'], landlord['name'], 'site lease', 1, rent,
                              purpose='Daily newcomer trading-site rent')
    if firm.get('owner', 'Jun') == 'Jun' and firm['kind'] == 'bakery':
        review_business(village, firm)
    else:
        review_successor(village, firm)
    firm['closed_days'] = firm.get('closed_days', 0) + 1 if firm.get('operating_state') == 'paused' else 0
    if firm['closed_days'] >= EXIT_DAYS:
        release_site(village, firm)


def open_successor(village, index, profile):
    from economy import BUSINESS_TYPES
    good = BUSINESS_TYPES[profile['kind']]['output']
    firm = {'kind': profile['kind'], 'name': profile['name'], 'owner': profile['owner'], 'parent_id': None,
            'cash': CAPITAL, 'workers': 0, 'owner_operated': True, 'capacity_override': profile['capacity'],
            'stock': {good: 0}, 'machines': [], 'wholesale_price': profile['price'], 'opened_day': village.day,
            'operating_status': 'Opens tomorrow'}
    lifecycle_defaults(firm)
    village.businesses[KEY] = firm
    village.competition.update(candidate_cursor=index + 1, qualifying_days=0, has_had_tenant=True)
    message = f"{profile['owner']} opened {profile['name']} on the vacant site with {CAPITAL}c outside savings after three days of unmet {good} demand."
    event(village, 'entry', message, CAPITAL)
    village._record_trade(f"{profile['owner']} (outside savings)", firm['name'], 'owner capital', 1, CAPITAL,
                          external=True, purpose='New business investment')
    village.competition_status = message


def lifecycle_defaults(firm):
    """Old shops start observing hardship now, without invented history."""
    for key, value in {'operating_state': 'open', 'hardship_days': 0, 'recovery_days': 0,
                       'owner_reinvested': False, 'owner_reserve': RECOVERY_CAPITAL,
                       'review_cash': firm['cash'], 'owner_decision': 'Trading independently'}.items():
        firm.setdefault(key, value)


def event(village, kind, message, capital=0):
    village.competition_events.append({'day': village.day, 'kind': kind, 'message': message, 'capital': capital})
    village.competition_events[:] = village.competition_events[-24:]
    village.journal.insert(0, f'Day {village.day}: {message}')


def review_business(village, firm):
    lifecycle_defaults(firm)
    made = village.daily_life.get('produced', {}).get(KEY, 0)
    sold = sum(t['units'] for t in village.daily_trades
               if t['from'] == firm['name'] and t['good'] == 'bread')
    reason = village.daily_life.get('reasons', {}).get(KEY, 'Opening tomorrow')
    report = village.last_day_report
    if firm['operating_state'] == 'paused':
        viable = (report.get('sold', 0) >= 3 and report.get('produced', {}).get('mill', 0) >= 3
                  and village.businesses['market']['cash'] >= 14)
        funded = firm['cash'] >= 10 or not firm['owner_reinvested'] and firm['owner_reserve'] >= RECOVERY_CAPITAL
        firm['recovery_days'] = firm['recovery_days'] + 1 if viable and funded else 0
        if firm['recovery_days'] >= 2:
            if firm['cash'] < 10:
                firm['owner_reserve'] -= RECOVERY_CAPITAL
                firm['cash'] += RECOVERY_CAPITAL
                firm['owner_reinvested'] = True
                village._record_trade('Jun (outside reserve)', firm['name'], 'owner capital', 1,
                                      RECOVERY_CAPITAL, external=True, purpose='One-time reopening investment')
                event(village, 'investment', 'Jun invested his final 20c reserve to restart the bakery.', RECOVERY_CAPITAL)
                firm['owner_decision'] = 'Reinvested final 20c reserve; no further outside rescue'
            else:
                firm['owner_decision'] = 'Reopening with retained business cash'
            firm.update(operating_state='open', hardship_days=0, recovery_days=0)
            reason = 'Reopens tomorrow after two viable trading days'
            event(village, 'reopening', 'Jun will reopen East Bakery tomorrow: paying demand and flour supply have recovered.')
        else:
            needs = ('cash for two flour orders; owner reserve already spent' if not funded else
                     'three household purchases, mill output of three, and 14c market funds')
            firm['owner_decision'] = f'Waiting for {needs}. Unsold bread can fund reopening.'
            reason = f'Closed temporarily; recovery {firm["recovery_days"]}/2. ' + ('Needs working cash.' if not funded else 'Waiting for steady orders and flour.')
    else:
        losses = firm['cash'] < firm['review_cash']
        blocked = made == 0 and sold == 0
        firm['hardship_days'] = firm['hardship_days'] + 1 if losses or blocked else 0
        if firm['hardship_days'] >= 3:
            firm.update(operating_state='paused', recovery_days=0)
            firm['owner_decision'] = 'Protecting remaining cash; keeping the shop for a possible reopening'
            reason = 'Closed temporarily after three days of losses or no production and sales. Remaining stock can sell.'
            event(village, 'closure', 'Jun temporarily closed East Bakery after three difficult trading days; he retains ownership and can reopen.')
        elif firm['hardship_days']:
            reason += f'; hardship {firm["hardship_days"]}/3'
    firm['review_cash'] = firm['cash']
    firm['operating_status'] = reason
    village.competition_status = f'Day {village.day}: Jun baked {made}/2 and sold {sold} loaves. {reason}.'


def evaluate(village):
    """Review completed evidence once per day; never infer missed history."""
    review = village.competition
    if review.get('evaluated_day', 0) >= village.day:
        return
    review['evaluated_day'] = village.day
    if KEY in village.businesses:
        firm = village.businesses[KEY]
        review_occupant(village, firm)
        return
    if review.get('has_had_tenant'):
        if village.day < review.get('cooldown_until', 0):
            village.competition_status = 'The site is vacant; applicants are reviewing local trade.'
            return
        index, profile = candidate_for(village)
        owner = profile['owner'] if profile else None
        review['qualifying_days'] = review.get('qualifying_days', 0) + 1 if owner and owner == review.get('candidate_owner') else 1 if owner else 0
        review['candidate_owner'] = owner
        if profile and review['qualifying_days'] >= ENTRY_DAYS:
            open_successor(village, index, profile)
        else:
            village.competition_status = (f"{owner} is reviewing demand: {review['qualifying_days']}/{ENTRY_DAYS} days." if owner else
                                          'The site is available; no applicant sees sustained unmet demand yet.')
        return
    report = village.last_day_report
    demand = sum(h['bread_need'] for h in village.households.values())
    mill = village.businesses['mill']
    flour_today = report.get('produced', {}).get('mill', 0)
    conditions = {
        'an occupied newcomer cottage': 'home_4' in village.households,
        'three daily household bread purchases': report.get('sold', 0) >= 3 and demand >= 4,
        'enough flour for two bakers': flour_today >= 4 or flour_today >= 3 and mill['stock'].get('flour', 0) >= 1,
        'a market able to fund orders': village.businesses['market']['cash'] >= 14,
    }
    missing = [name for name, ready in conditions.items() if not ready]
    review['qualifying_days'] = review.get('qualifying_days', 0) + 1 if not missing else 0
    if missing:
        village.competition_status = 'Jun is watching for ' + '; '.join(missing) + '.'
        return
    village.competition_status = f"Jun's bakery review: {review['qualifying_days']}/{ENTRY_DAYS} stable days of demand and flour supply."
    if review['qualifying_days'] < ENTRY_DAYS:
        return
    village.businesses[KEY] = {
        'kind': 'bakery', 'name': "Jun's East Bakery", 'owner': 'Jun', 'parent_id': None,
        'cash': CAPITAL, 'workers': 0, 'owner_operated': True, 'capacity_override': 2,
        'stock': {'bread': 0}, 'machines': [], 'wholesale_price': 6,
        'opened_day': village.day, 'operating_status': 'Opens for work tomorrow',
    }
    lifecycle_defaults(village.businesses[KEY])
    message = f"Jun opened East Bakery with {CAPITAL}c outside savings after three days of paying demand and sufficient flour."
    village.competition_events.append({'day': village.day, 'kind': 'entry', 'message': message, 'capital': CAPITAL})
    village.competition_events[:] = village.competition_events[-24:]
    village.journal.insert(0, f'Day {village.day}: {message}')
    village._record_trade('Jun (outside savings)', "Jun's East Bakery", 'owner capital', 1, CAPITAL,
                          external=True, purpose='New business investment')
    village.competition_status = "Jun's East Bakery opens tomorrow. Jun commutes in, buys flour, and competes for market orders."


def buy_competitive_input(village, buyer, good, needed, default_price):
    """Buy affordable stock at the best price, rotating equal-price suppliers.

    Retailers and incidental stockholders cannot resell the same loaf between
    shops. The saved cursor also prevents repeated one-unit orders favouring
    the first firm in dictionary order.
    """
    from economy import BUSINESS_TYPES
    suppliers = [(key, firm) for key, firm in village.businesses.items()
                 if firm is not buyer and BUSINESS_TYPES[firm['kind']]['output'] == good
                 and not (good == 'bread' and firm['kind'] != 'bakery')]
    if not suppliers:
        return 0
    cursors = buyer.setdefault('supplier_cursors', {})
    last = cursors.get(good)
    keys = [key for key, _ in suppliers]
    start = (keys.index(last) + 1) % len(keys) if last in keys else 0
    purchased = {}
    total = 0
    while total < needed:
        available_prices = [max(1, int(firm.get('wholesale_price', default_price)))
                            for _, firm in suppliers if firm['stock'].get(good, 0) > 0
                            and buyer['cash'] >= max(1, int(firm.get('wholesale_price', default_price)))]
        if not available_prices:
            break
        best_price = min(available_prices)
        found = False
        for offset in range(len(suppliers)):
            index = (start + offset) % len(suppliers)
            key, firm = suppliers[index]
            price = max(1, int(firm.get('wholesale_price', default_price)))
            if price != best_price or firm['stock'].get(good, 0) < 1 or buyer['cash'] < price:
                continue
            firm['stock'][good] -= 1
            firm['cash'] += price
            buyer['cash'] -= price
            previous_count, previous_cost = purchased.get(key, (0, 0))
            purchased[key] = (previous_count + 1, previous_cost + price)
            total += 1
            cursors[good] = key
            start = (index + 1) % len(suppliers)
            found = True
            break
        if not found:
            break
    for key, (count, cost) in purchased.items():
        village._record_trade(village.businesses[key]['name'], buyer['name'], good, count, cost)
    return total


