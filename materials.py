"""Physical project supplies; drawing and testing circuits remains free."""
from math import floor
from commissions import COMMISSIONS

SHOPS = {
    "sawmill": {"good": "timber", "price": 1, "description": "Iris cuts local timber for frames and foundry charcoal."},
    "foundry": {"good": "metal", "price": 2, "description": "Otto buys timber for charcoal and smelts local ore into metal."},
    "toolmaker": {"good": "fittings", "price": 3, "description": "Tess buys metal and shapes precision fittings for machines."},
}
BILLS = {
    "mill": {"timber": 1, "metal": 1, "fittings": 1},
    "bakery": {"timber": 2, "metal": 2, "fittings": 1},
    "vent": {"metal": 2, "fittings": 1},
    "market": {"timber": 2, "metal": 1, "fittings": 1},
    "pump": {"timber": 1, "metal": 2, "fittings": 2},
    "sorter": {"timber": 2, "metal": 1, "fittings": 2},
}
BILLS.update({key: dict(job.materials) for key, job in COMMISSIONS.items() if job.materials})


def material_bill(key):
    return BILLS.get(key, {}).copy()


def available(village, key, good):
    return village.material_inventory.get(good, 0) + village.material_reservations.get(key, {}).get(good, 0)


def missing_materials(village, key):
    return {good: count - available(village, key, good) for good, count in material_bill(key).items()
            if available(village, key, good) < count}


def material_status(village, key):
    bill = material_bill(key)
    if not bill:
        return "Prototyping is free. Materials are needed only for machine delivery."
    labels = ", ".join(f"{good} {available(village, key, good)}/{count}" for good, count in bill.items())
    prices = {shop["good"]: shop["price"] for shop in SHOPS.values()}
    cost = sum(prices[good] * count for good, count in missing_materials(village, key).items())
    note = f"Need {cost}c of supplies" if cost else "Ready to deliver"
    advance = village.material_advances.get(key, 0)
    if advance:
        note += f"; {advance}c advance deducted from payment"
    return f"{labels}. {note}."


def buy_material(village, business_id):
    if business_id not in SHOPS:
        return "This business does not sell project supplies."
    firm = village.businesses[business_id]
    good, price = SHOPS[business_id]["good"], SHOPS[business_id]["price"]
    if firm["stock"].get(good, 0) < 1:
        return f"{firm['name']} has no {good}; production resumes during the day."
    if village.coins < price:
        return f"One {good} costs {price}c. Request customer supplies in Delivery if funds are short."
    village.coins -= price
    firm["cash"] += price
    firm["stock"][good] -= 1
    village.material_inventory[good] = village.material_inventory.get(good, 0) + 1
    village._record_trade(firm["name"], "Your Workshop", good, 1, price)
    return f"Bought 1 {good} for {price}c. Workshop stock: {village.material_inventory[good]}."


def advance_materials(village, key):
    """Customer purchases reserved supplies; delivery pays only the remainder.

    Reserved stock cannot be sold or used on another job. If Grace wins the job,
    the customer retains those goods rather than leaving the player in debt.
    """
    from economy import CONTRACTS
    offer = village.offers.get(key)
    if key not in BILLS or not offer or offer.get("status") not in ("open", "bid"):
        return "Customer supplies are available only for an open contract."
    missing = missing_materials(village, key)
    if not missing:
        return "All delivery supplies are already available."
    customer = village.businesses[CONTRACTS[key][0]]
    orders = [(village.businesses[shop], item["good"], missing[item["good"]], item["price"])
              for shop, item in SHOPS.items() if item["good"] in missing]
    cost = sum(count * price for _, _, count, price in orders)
    if any(firm["stock"].get(good, 0) < count for firm, good, count, _ in orders):
        return "A supplier lacks stock. Let the trades work, then request supplies again."
    # Even the lower-paying license option must retain a positive payment.
    if cost + village.material_advances.get(key, 0) >= CONTRACTS[key][2] // 2:
        return "The customer cannot advance more than the minimum delivery payment."
    if customer["cash"] < cost:
        return "The customer cannot fund supplies today."
    reserved = village.material_reservations.setdefault(key, {})
    for firm, good, count, price in orders:
        firm["stock"][good] -= count
        firm["cash"] += count * price
        customer["cash"] -= count * price
        reserved[good] = reserved.get(good, 0) + count
        village._record_trade(firm["name"], customer["name"], good, count, count * price,
                              purpose=f"Reserved for your {key} project")
    village.material_advances[key] = village.material_advances.get(key, 0) + cost
    return f"Customer bought {cost}c of reserved supplies; deducted from this job's payment."


def deliver_project(village, key, mode="install"):
    """Validate both material and commercial conditions before consuming stock."""
    from economy import CONTRACTS
    if key not in CONTRACTS:
        return False, "Unknown project."
    if mode not in ("install", "sell", "license"):
        return False, "Unknown delivery agreement."
    offer = village.offers.get(key)
    if not offer or offer.get("status") not in ("open", "bid"):
        return False, "This contract is no longer open. Your supplies were kept."
    if missing_materials(village, key):
        return False, "Missing delivery supplies. " + material_status(village, key)
    customer = village.businesses[CONTRACTS[key][0]]
    advance = village.material_advances.get(key, 0)
    before_coins = village.coins
    # fulfill_job settles gross price; the customer already paid the advance.
    customer["cash"] += advance
    try:
        fulfilled = village.fulfill_job(key, mode)
    except Exception:
        customer["cash"] -= advance
        raise
    if not fulfilled:
        customer["cash"] -= advance
        return False, "The customer cannot complete this agreement today. Your supplies were kept."
    village.coins -= advance
    reserve = village.material_reservations.get(key, {})
    for good, needed in material_bill(key).items():
        from_reserve = min(needed, reserve.get(good, 0))
        village.material_inventory[good] = village.material_inventory.get(good, 0) - (needed - from_reserve)
    village.material_reservations.pop(key, None)
    village.material_advances.pop(key, None)
    offer["materials_used"] = material_bill(key)
    offer["material_advance"] = advance
    received = village.coins - before_coins
    if advance:
        village.journal[0] += f" Received {received}c after {advance}c supplies advance."
    return True, f"Supplies installed. Received {received}c" + (f" after {advance}c advance." if advance else ".")


def reconcile_reservations(village):
    """A closed job's customer retains its previously purchased materials."""
    from economy import CONTRACTS
    for key in list(village.material_reservations):
        if village.offers.get(key, {}).get("status") in ("open", "bid"):
            continue
        if key in CONTRACTS:
            customer = village.businesses[CONTRACTS[key][0]]
            for good, count in village.material_reservations[key].items():
                customer["stock"][good] = customer["stock"].get(good, 0) + count
            village.journal.insert(0, f"{customer['name']} kept its reserved {key} supplies after the job closed.")
        village.material_reservations.pop(key, None)
        village.material_advances.pop(key, None)


def produce(village, current):
    """Owner-operated trades work a bounded day, buying actual supplier stock.

    These owners commute from outside Copperside; they are not anonymous paid
    resident workers and do not add unexplained household demand or wages.
    """
    from daily_life import DAY_SECONDS, STEP_SECONDS
    from economy import BUSINESS_TYPES
    fraction = min(1.0, (current["elapsed"] + STEP_SECONDS) / DAY_SECONDS)
    for shop, item in SHOPS.items():
        good = item["good"]
        firm = village.businesses[shop]
        if not firm.get("owner_operated"):
            continue
        recipe = BUSINESS_TYPES[firm["kind"]]
        done = current["produced"].get(shop, 0)
        allowance = max(0, floor(village.capacity(shop) * fraction + 1e-8) - done)
        allowance = min(allowance, max(0, {"timber": 12, "metal": 8, "fittings": 6}[good] - firm["stock"].get(good, 0)))
        if not allowance:
            current["reasons"][shop] = "Owner's workday / stock buffer limits output"
            continue
        amount = allowance
        if recipe["input"]:
            amount = village._buy_input(firm, recipe["input"], allowance, recipe["input_price"])
        if amount:
            firm["stock"][good] = firm["stock"].get(good, 0) + amount
            current["produced"][shop] = done + amount
        current["reasons"][shop] = ("Owner produced supplies for local projects" if amount == allowance else
                                    f"Waiting for affordable {recipe['input']}")
