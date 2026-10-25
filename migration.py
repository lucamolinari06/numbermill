"""Observed housing growth and a rotating pool of prospective residents."""
from citizens import prepare

HOME = "home_4"
NAME = "Rowan"
HOMES = ("home_4", "home_5", "home_6")
NEWCOMERS = (
    {"name": "Rowan", "aspiration": "Learn a trade and put down roots", "traits": {"drive": 14, "sociable": 10, "care": 14}},
    {"name": "Saffron", "aspiration": "Make the village a welcoming place for visitors", "traits": {"drive": 11, "sociable": 18, "care": 12}},
    {"name": "Felix", "aspiration": "Keep every workshop supplied with reliable parts", "traits": {"drive": 18, "sociable": 7, "care": 10}},
    {"name": "Wren", "aspiration": "Grow food without wasting the land's gifts", "traits": {"drive": 12, "sociable": 9, "care": 18}},
    {"name": "Hugo", "aspiration": "Learn the craft well enough to teach an apprentice", "traits": {"drive": 16, "sociable": 12, "care": 12}},
    {"name": "Alma", "aspiration": "Build a home where friends always have a place", "traits": {"drive": 10, "sociable": 17, "care": 17}},
    {"name": "Perry", "aspiration": "Find useful work for every spare piece of metal", "traits": {"drive": 17, "sociable": 8, "care": 13}},
    {"name": "Cleo", "aspiration": "Turn patient daily work into a secure future", "traits": {"drive": 15, "sociable": 11, "care": 15}},
)


def housing_state(village, home, create=False):
    # Keep the original cottage fields intact for older saves and UI consumers.
    if home == HOME:
        return village.migration
    if create:
        return village.migration.setdefault("homes", {}).setdefault(home, {})
    return village.migration.get("homes", {}).get(home, {})


def next_resident(village):
    occupied = {p["name"] for p in village.citizens}
    cursor = village.migration.get("resident_cursor", 0)
    for offset in range(len(NEWCOMERS)):
        index = (cursor + offset) % len(NEWCOMERS)
        if NEWCOMERS[index]["name"] not in occupied:
            village.migration["resident_cursor"] = index + 1
            return NEWCOMERS[index]
    raise ValueError("The newcomer pool is smaller than the available housing")
WINDOW = 3
BUILD_DAYS = 2


def job_offer(village):
    """A vacancy must have working cash; a new job must cover its extra wage."""
    ordered = sorted(village.businesses.items(), key=lambda pair: pair[0] != 'fuel_yard')
    for key, firm in ordered:
        if firm.get("cash", 0) < 24 or (firm.get("workers", 0) <= 0 and not firm.get("owner_operated")):
            continue
        assigned = sum(p["workplace"] == key for p in village.citizens)
        if assigned < firm["workers"]:
            return key, False
        if (firm.get('hiring_surplus', 0) >= 8 and firm['cash'] >= 80
                and ((assigned == 1 and firm['workers'] == 1) or
                     (firm.get('owner_operated') and assigned == 0 and firm['workers'] == 0))):
            return key, True
    return None, False


def evaluate(village):
    """Review all reusable homes, with at most one new foundation per day."""
    if village.migration.get("evaluated_day", 0) >= village.day:
        return
    village.migration["evaluated_day"] = village.day
    statuses = []
    for home_id in HOMES:
        data = housing_state(village, home_id, create=True)
        # Later cottages develop only once the preceding site is occupied.
        if home_id != HOME and home_id not in village.households and HOMES[HOMES.index(home_id) - 1] not in village.households:
            continue
        _review_home(village, home_id, data)
        statuses.append(village.migration_status)
    occupied = sum(home in village.households for home in HOMES)
    focus = next((line for line in statuses if "considering leaving" in line), statuses[-1] if statuses else "Available homes await funded work and reliable food.")
    village.migration_status = f"{occupied}/{len(HOMES)} newcomer cottages occupied. {focus}"


def _review_home(village, home_id, data):
    """Idempotent per completed day; historical meals are never reconstructed."""
    data.setdefault("housing_stage", "occupied" if home_id in village.households else "plot")
    data.setdefault("cottage_built", home_id in village.households)
    if home_id in village.households:
        data.update(housing_stage="occupied", cottage_built=True)
        home = village.households[home_id]
        resident = next((p for p in village.citizens if p["home"] == home_id), None)
        name = resident["name"] if resident else "The newcomer"
        firm = village.businesses.get(resident["workplace"]) if resident else None
        if resident and resident.get('wage', 4) < 8:
            # Upgrade the old single-earner contract at the next daily review.
            # Prefer a viable vacancy instead of silently billing an unprofitable mill.
            replacement, added = job_offer(village)
            if replacement and replacement != resident['workplace']:
                if firm and data.get('added_worker'):
                    firm['workers'] = max(0, firm['workers'] - 1)
                firm = village.businesses[replacement]
                if added:
                    firm['workers'] += 1
                resident.update(workplace=replacement, destination=resident['home'], activity='at home')
                data['added_worker'] = added
                record(village, 'employment', f"{name} moved to paid work at {firm['name']}.")
            resident['wage'] = 8
        employed = bool(firm and firm.get("workers", 0) > 0 and firm["cash"] >= resident.get("wage", 8))
        hungry = home["bought"] < home["bread_need"]
        struggling = (hungry and home["cash"] < village.bread_price * 2) or not employed
        data["hardship_days"] = data.get("hardship_days", 0) + 1 if struggling else 0
        reason = "no funded job" if not employed else "missed meals and low savings"
        if data["hardship_days"] >= WINDOW:
            if firm and data.get("added_worker"):
                firm["workers"] = max(0, firm["workers"] - 1)
            village.citizens = [p for p in village.citizens if p["home"] != home_id]
            savings = home["cash"]
            if "resident_cursor" not in village.migration:
                village.migration["resident_cursor"] = next((i + 1 for i, profile in enumerate(NEWCOMERS) if profile["name"] == name), 0)
            del village.households[home_id]
            record(village, "departure", f"{name} left after {WINDOW} days of {reason}; took {savings}c savings.", savings=-savings)
            data.update(healthy_days=0, hardship_days=0, cooldown_until=village.day + WINDOW, housing_stage="vacant")
            village.migration_status = "Cottage vacant; waiting three days before another arrival review."
        elif struggling:
            village.migration_status = f"{name} is considering leaving: {reason} ({data['hardship_days']}/{WINDOW} days)."
        else:
            village.migration_status = f"{name} is settled; food, savings and work are reviewed daily."
        return
    if village.day < data.get("cooldown_until", 0):
        village.migration_status = "Cottage vacant; recent departure pauses arrival reviews."
        return
    if data["housing_stage"] == "construction":
        data["construction_days"] = min(BUILD_DAYS, data.get("construction_days", 0) + 1)
        if data["construction_days"] == BUILD_DAYS:
            data.update(housing_stage="ready", cottage_built=True)
            record(village, "construction", "The new cottage is finished; a household can move in when food and work are secure.")
    homes = list(village.households.values())
    healthy = bool(homes) and all(h["bought"] >= h["bread_need"] and h["cash"] >= village.bread_price * 2 for h in homes)
    # A newcomer must not take the last loaf reserved for the player's shopping.
    spare_food = village.businesses["market"]["stock"].get("bread", 0) >= 2
    job, added_worker = job_offer(village)
    data["healthy_days"] = data.get("healthy_days", 0) + 1 if healthy and spare_food and job else 0
    missing = []
    if not healthy:
        missing.append("fed households with two meals of savings")
    if not spare_food:
        missing.append("spare market bread")
    if not job:
        missing.append("a funded vacancy or profitable apprenticeship")
    village.migration_status = ("Arrival needs " + "; ".join(missing) + "." if missing else
                                f"Arrival conditions stable: {data['healthy_days']}/{WINDOW} days.")
    if data["housing_stage"] == "construction":
        village.migration_status = f"New cottage under construction: {data['construction_days']}/{BUILD_DAYS} building days. Food and work remain under review."
        return
    if data["healthy_days"] < WINDOW:
        return
    if not data["cottage_built"]:
        data.update(housing_stage="construction", construction_days=0)
        record(village, "construction", "Three stable food and work days: a newcomer-funded cottage is starting on an available site.")
        village.migration_status = f"Cottage foundations laid. Construction takes {BUILD_DAYS} more completed days; no player funds are charged."
        return
    firm = village.businesses[job]
    village.households[home_id] = {"cash": 48, "bread_need": 1, "missed_meals": 0, "bought": 0}
    candidate = next_resident(village)
    name = candidate["name"]
    person = {**candidate, "traits": candidate["traits"].copy(), "home": home_id, "workplace": job, "wage": 8}
    prepare(person)
    village.citizens.append(person)
    if added_worker:
        firm["workers"] += 1
    data.update(added_worker=added_worker, healthy_days=0, hardship_days=0, housing_stage="occupied")
    message = f"{name} arrived with 48c savings: three stable food days and paid work at {firm['name']}."
    person["memories"].append(f"Day {village.day}: moved here for reliable food and work at {firm['name']}.")
    record(village, "arrival", message, savings=48)
    village.migration_status = f"{name} moved into a cottage and starts work tomorrow."


def record(village, kind, message, **details):
    village.migration_events.append({"day": village.day, "kind": kind, "message": message, **details})
    village.migration_events[:] = village.migration_events[-24:]
    village.journal.insert(0, f"Day {village.day}: {message}")
