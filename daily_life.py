"""A bounded economic day driven by the same residents shown in town."""
from math import floor

DAY_SECONDS = 180.0
SHIFT_SECONDS = 18.0
STEP_SECONDS = .5
FOOD_ACTIONS = {"seeking food", "checking food supplies", "shopping"}


def state(village):
    current = village.daily_life
    if not isinstance(current, dict) or current.get("day") != village.day:
        current = {"day": village.day, "elapsed": 0.0, "accumulator": 0.0, "started": False,
                   "settled": False, "worked": {}, "paid": {}, "produced": {}, "sold": 0,
                   "reasons": {}, "purchases": []}
        village.daily_life = current
    return current


def progress(village):
    return min(1.0, state(village)["elapsed"] / DAY_SECONDS)


def begin(village):
    current = state(village)
    if current["started"] or current["settled"]:
        return
    current["started"] = True
    current["opening_cash"] = {key: firm["cash"] for key, firm in village.businesses.items()}
    village._review_working_capital()
    village.power_checked_day = village.day
    village._pay_royalties()
    village._run_service()
    from materials import reconcile_reservations
    reconcile_reservations(village)


def record_visit(village, person, dt):
    """Called only after arrival at the resident's actual destination."""
    current = state(village)
    if current["settled"]:
        return
    employer = village.businesses.get(person["workplace"])
    if (person["activity"] == "working" and person["destination"] == person["workplace"]
            and employer and employer["workers"] > 0):
        name = person["name"]
        current["worked"][name] = min(SHIFT_SECONDS, current["worked"].get(name, 0.0) + dt)
    if person["destination"] == "market" and (person["activity"] in FOOD_ACTIONS or
            person["activity"] == "working" and person["workplace"] == "market"):
        shop(village, person)


def shop(village, person):
    current = state(village)
    home = village.households[person["home"]]
    if current["settled"] or home["bought"] >= home["bread_need"]:
        return False
    market = village.businesses["market"]
    if home["cash"] < village.bread_price:
        person["last_reason"] = f"Bread costs {village.bread_price}c; household has {home['cash']}c"
        return False
    if market["stock"].get("bread", 0) <= 1:
        person["last_reason"] = "Waiting for household bread; one loaf kept for walk-in shoppers"
        return False
    home["cash"] -= village.bread_price
    market["cash"] += village.bread_price
    market["stock"]["bread"] -= 1
    home["bought"] += 1
    current["sold"] += 1
    receipt = {"person": person["name"], "home": person["home"], "price": village.bread_price}
    current["purchases"].append(receipt)
    village._record_trade(market["name"], person["home"].replace("_", " ").title(),
                          "bread", 1, village.bread_price, person=person["name"])
    person["last_reason"] = f"Bought household bread for {village.bread_price}c"
    person["memories"] = (person["memories"] + [f"Day {village.day}: bought bread for the household."])[-6:]
    if home["bought"] >= home["bread_need"]:
        person["checked_food_day"] = village.day
    totals(village)
    return True


def pay_wages(village):
    current = state(village)
    for person in village.citizens:
        name = person["name"]
        employer = village.businesses.get(person["workplace"])
        if not employer:
            continue
        earned = floor(person["wage"] * current["worked"].get(name, 0.0) / SHIFT_SECONDS + 1e-8)
        paid = current["paid"].get(name, 0)
        amount = min(max(0, earned - paid), max(0, employer["cash"]))
        if not amount:
            continue
        employer["cash"] -= amount
        village.households[person["home"]]["cash"] += amount
        current["paid"][name] = paid + amount
        village._record_trade(employer["name"], person["home"].replace("_", " ").title(),
                              "work", 1, amount, person=name)


def produce(village):
    # Import at use time: economy owns recipes, this module owns their timing.
    from economy import BUSINESS_TYPES
    current = state(village)
    demand = sum(home["bread_need"] for home in village.households.values())
    for kind in ("fuel", "farm", "mill", "bakery", "market", "parts"):
        firms = list(village.businesses.items())
        if kind == "bakery" and village.day % 2 == 0:
            firms.reverse()  # Rotate first access to a scarce flour delivery.
        for business_id, firm in firms:
            if firm["kind"] != kind:
                continue
            if firm.get('operating_state') == 'paused':
                current['reasons'][business_id] = 'Temporarily closed; owner is reviewing recovery'
                continue
            workers = [p for p in village.citizens if p["workplace"] == business_id]
            attendance = sum(current["worked"].get(p["name"], 0.0) for p in workers)
            fraction = min(1.0, attendance / (max(1, firm["workers"]) * SHIFT_SECONDS)) if firm["workers"] else 0.0
            if firm.get("owner_operated"):
                # Jun commutes from outside the resident simulation. His own
                # shift is explicit, bounded, and does not mint resident wages.
                fraction = min(1.0, (current["elapsed"] + STEP_SECONDS) / SHIFT_SECONDS)
            done = current["produced"].get(business_id, 0)
            if not fraction:
                current["reasons"][business_id] = "No work attendance yet"
                continue
            if firm.get("powered_day") != village.day:
                village._supply_steam(firm)
            quota = village.capacity(business_id)
            if kind == "farm" and village.machine_ready(business_id, "farm_pump") and village.day % 2 == 0:
                quota += 1
            if (kind == "bakery" and "bakery_selector" in firm["machines"]
                    and not village.machine_ready(business_id, "bakery_vent") and village.day % 7 == 0):
                current["reasons"][business_id] = "Boiler shutdown; a safety vent is needed"
                if firm.get("shutdown_noted_day") != village.day:
                    firm["shutdown_noted_day"] = village.day
                    village.journal.insert(0, f"Day {village.day}: bakery boiler shut down; no bread was baked.")
                continue
            allowance = max(0, floor(quota * fraction + 1e-8) - done)
            recipe = BUSINESS_TYPES[kind]
            output = recipe["output"]
            if done >= quota:
                current["reasons"][business_id] = ("Fuel shortage; steam upgrade paused"
                    if firm.get("fuel_shortage_noted_day") == village.day and firm.get("powered_day") != village.day
                    else "Daily capacity reached")
                continue
            if not allowance:
                current["reasons"][business_id] = "More time at work is needed"
                continue
            # Stop paying for inputs that cannot be sold: a modest working
            # buffer absorbs timing differences without unbounded stockpiles.
            buffer_bonus = village.stock_buffer_bonus(business_id)
            if kind in ("farm", "mill"):
                allowance = min(allowance, max(0, (demand + 3) * 2 + buffer_bonus - firm["stock"].get(output, 0)))
            if kind in ("fuel", "parts"):
                allowance = min(allowance, max(0, (12 if kind == "fuel" else 6) + buffer_bonus - firm["stock"].get(output, 0)))
            if kind == "bakery":
                allowance = min(allowance, max(0, 4 + buffer_bonus - firm["stock"].get(output, 0)))
            if kind == "market":
                allowance = min(allowance, max(0, demand + 2 + buffer_bonus - firm["stock"].get("bread", 0)))
            if not allowance:
                current["reasons"][business_id] = "Stock buffer is full"
                continue
            amount = allowance
            if recipe["input"]:
                amount = village._buy_input(firm, recipe["input"], allowance, recipe["input_price"])
            if amount:
                firm["stock"][output] = firm["stock"].get(output, 0) + amount
                current["produced"][business_id] = done + amount
            if amount < allowance:
                current["reasons"][business_id] = (f"Cannot afford {recipe['input']}" if firm["cash"] < recipe["input_price"]
                                                    else f"Waiting for {recipe['input']} deliveries")
            else:
                current["reasons"][business_id] = "Daily capacity reached" if done + amount >= quota else "Working through the daily shift"


def totals(village):
    for good in ("grain", "flour", "bread"):
        setattr(village, good, sum(firm["stock"].get(good, 0) for firm in village.businesses.values()))


def settle(village):
    from citizens import decide
    current = state(village)
    if current["settled"]:
        return
    pay_wages(village)
    village._sell_traveler_parts()
    village._sell_surplus_fuel()
    village._sell_regional_kits()
    for home in village.households.values():
        home["missed_meals"] += max(0, home["bread_need"] - home["bought"])
    for business_id, firm in village.businesses.items():
        if (firm["kind"] == "market" and village.day % 6 == 0 and firm["stock"].get("bread", 0) > 0
                and not village.machine_ready(business_id, "market_cooler")):
            if firm.get('pantry_protection', 0) > 0:
                firm['pantry_protection'] -= 1
                village.journal.insert(0, f"Day {village.day}: Dara's new shelves protected a loaf from spoilage.")
            else:
                firm["stock"]["bread"] -= 1
                village.journal.insert(0, f"Day {village.day}: {firm['name']} lost one loaf to spoilage.")
    for person in village.citizens:
        decide(person, village.households[person["home"]], village, day=village.day)
    totals(village)
    produced_bread = sum(current["produced"].get(key, 0) for key, firm in village.businesses.items() if firm["kind"] == "bakery")
    demand = sum(home["bread_need"] for home in village.households.values())
    village.bread_price = 8 + max(0, demand + 1 - produced_bread) // 2 + max(0, 2 - village.bread)
    fed = sum(home["bought"] >= home["bread_need"] for home in village.households.values())
    bakers = "bakeries" if "east_bakery" in village.businesses else "bakery"
    causes = [f"Mill sent {current['produced'].get('mill', 0)} flour -> {bakers} made {produced_bread} bread.",
              f"Residents bought {current['sold']} bread -> {fed}/{len(village.households)} households fed."]
    for key in ("farm", "mill", "bakery", "market"):
        firm = village.businesses[key]
        made = current["produced"].get(key, 0)
        if made < village.capacity(key, nominal=True):
            causes.append(f"{firm['name'].replace('Copperside ', '')}: {current['reasons'].get(key, 'No attendance')}.")
    village.market_note = (f"Bread pressure: {produced_bread} made for {demand + 1} wanted."
                           if produced_bread < demand + 1 else "Bread supply meets today's demand.")
    village.last_day_report = {"day": village.day, "worked": current["worked"].copy(), "paid": current["paid"].copy(),
                               "produced": current["produced"].copy(), "reasons": current["reasons"].copy(),
                               "sold": current["sold"], "fed": fed, "households": len(village.households), "causes": causes,
                               "meals": {key: {"bought": home["bought"], "needed": home["bread_need"]} for key, home in village.households.items()}}
    village.journal = ([f"Day {village.day}: mill sent {current['produced'].get('mill', 0)} flour; market sold {current['sold']} bread."]
                       + village.journal)[:8]
    for key, firm in village.businesses.items():
        opening = current.get("opening_cash", {}).get(key, firm["cash"])
        margins = (firm.get("operating_margins", []) + [firm["cash"] - opening])[-3:]
        firm["operating_margins"] = margins
        firm["hiring_surplus"] = min(margins) if len(margins) == 3 else 0
    from migration import evaluate
    evaluate(village)
    from competition import evaluate as review_competition
    review_competition(village)
    from character_projects import evaluate as review_requests
    review_requests(village)
    village._post_offers()
    if village.history and village.history[-1]["day"] == village.day:
        village.history.pop()
    village.record_history()
    current["settled"] = True


def update(village, town, dt):
    if dt <= 0:
        town.update_people(village, 0)
        return
    current = state(village)
    if current["settled"]:
        return
    begin(village)
    current["accumulator"] += min(dt, DAY_SECONDS - current["elapsed"])
    while current["accumulator"] + 1e-8 >= STEP_SECONDS and current["elapsed"] < DAY_SECONDS:
        current["accumulator"] -= STEP_SECONDS
        town.update_people(village, STEP_SECONDS, economic=True)
        produce(village)
        from materials import produce as produce_materials
        produce_materials(village, current)
        from manufacturing import update as update_manufacturing
        update_manufacturing(village, STEP_SECONDS)
        pay_wages(village)
        totals(village)
        current["elapsed"] = min(DAY_SECONDS, current["elapsed"] + STEP_SECONDS)
    if current["elapsed"] >= DAY_SECONDS:
        settle(village)


def update_continuous(village, town, dt):
    """Run the live clock across mornings; explicit fast-forward stays bounded.

    Account for fractional steps at the boundary so wages and meals are settled
    once and no frame time disappears when a new day starts.
    """
    remaining = max(0.0, dt)
    crossed = 0
    while remaining > 1e-8:
        current = state(village)
        if current['settled']:
            advance(village, town)
            crossed += 1
            current = state(village)
        duration = min(remaining, max(0.0, DAY_SECONDS - current['elapsed'] - current['accumulator']))
        if duration <= 1e-8:
            settle(village)
            continue
        update(village, town, duration)
        remaining -= duration
        if state(village)['settled']:
            advance(village, town)
            crossed += 1
    return crossed


def advance(village, town=None):
    if town is None:
        from town import Town
        town = Town()
    current = state(village)
    if not current['settled']:
        update(village, town, DAY_SECONDS - current["elapsed"])
    settle(village)
    village.day += 1
    village.daily_life = {}
    village.daily_trades = []
    village.last_contract_event = ""
    for home in village.households.values():
        home["bought"] = 0
    for person in village.citizens:
        person["visit_seconds"] = 0.0
        person["last_reason"] = "Starting the day"
    village._resolve_deadlines()
    village._advance_rival()
    village._post_offers()
    state(village)
    village.trade_history.append({"day": village.day, "entries": []})
    village.trade_history = village.trade_history[-120:]
    begin(village)
    village.record_history()


