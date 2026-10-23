"""Persistent motives and daily decisions for Copperside residents."""

TRAITS = {
    "Mely": {"drive": 18, "sociable": 9, "care": 15},
    "Luca": {"drive": 12, "sociable": 5, "care": 18},
    "Ada": {"drive": 12, "sociable": 11, "care": 5},
    "Bram": {"drive": 16, "sociable": 5, "care": 6},
    "Cora": {"drive": 9, "sociable": 15, "care": 7},
    "Dara": {"drive": 11, "sociable": 13, "care": 8},
}
ASPIRATIONS = {
    "Mely": "Keep Copperside's steam reliable and affordable",
    "Luca": "Make repairs locally instead of waiting for imports",
    "Ada": "Keep the farm and her household secure",
    "Bram": "Build a mill that never runs short",
    "Cora": "Feed every household in the village",
    "Dara": "Make the market welcoming to everyone",
}


def prepare(person):
    traits = TRAITS.get(person["name"], {"drive": 10, "sociable": 10, "care": 10})
    person.setdefault("traits", traits.copy())
    person.setdefault("aspiration", ASPIRATIONS.get(person["name"], "Build a good life in Copperside"))
    person.setdefault("energy", 70)
    person.setdefault("mood", 65)
    person.setdefault("hunger", 15)
    person.setdefault("social_need", 25)
    person.setdefault("activity", "at home")
    person.setdefault("destination", person["home"])
    person.setdefault("last_reason", "Starting the day")
    person.setdefault("relationships", {})
    person.setdefault("memories", [])
    if person["name"] in ("Mely", "Luca"):
        spouse = "Luca" if person["name"] == "Mely" else "Mely"
        person["relationships"].setdefault(spouse, 80)


def update_activity(person, home, village, dt, arrived):
    """Resolve a short stay, then plan another need-driven visit.

    Real time changes energy and company needs. Meals, wages and purchases
    remain on the economic day, so walking cannot create free goods or money.
    """
    prepare(person)
    if not arrived:
        return
    person["visit_seconds"] = person.get("visit_seconds", 0.0) + dt
    duration = 12 + sum(map(ord, person["name"])) % 13
    if person["last_reason"] != "Starting the day" and person["visit_seconds"] < duration:
        return
    person["visit_seconds"] = 0.0
    action = person["activity"]
    if action == "resting":
        person["energy"] = min(100, person["energy"] + 45)
    elif action == "working":
        person["energy"] = max(0, person["energy"] - 22)
    elif action in ("visiting neighbors", "spending time with spouse"):
        person["social_need"] = max(0, person["social_need"] - 45)
    person["social_need"] = min(100, person["social_need"] + 14)
    cycle = person.get("activity_cycle", 0) + 1
    person["activity_cycle"] = cycle
    neighbors = [p for p in village.citizens if p["home"] != person["home"]]
    friend = neighbors[(cycle + sum(map(ord, person["name"]))) % len(neighbors)] if neighbors else person
    choices = [
        (45 + person["traits"]["drive"] + (20 if home["cash"] < 16 else 0),
         "working", person["workplace"], "Helping at the business"),
        (max(0, 85 - person["energy"]) * 2, "resting", person["home"], "Needs a break"),
        (person["social_need"] + person["traits"]["sociable"], "visiting neighbors",
         friend["workplace"], f"Wants to catch up with {friend['name']}"),
    ]
    if person["hunger"] >= 25 and person.get("checked_food_day") != village.day:
        choices.append((80 + person["hunger"], "checking food supplies", "market", "Looking for the next meal"))
    # Avoid choosing the same place indefinitely, even when money is low.
    options = [c for c in choices if c[2] != person["destination"]] or choices
    _, action, destination, reason = max(options, key=lambda c: c[0])
    if action == "checking food supplies":
        person["checked_food_day"] = village.day
    person.update(activity=action, destination=destination, last_reason=reason)


def decide(person, home, village, *, day):
    """Choose the highest-scoring feasible action; keep the reason visible."""
    prepare(person)
    missed = home["bought"] < home["bread_need"]
    person["hunger"] = min(100, person["hunger"] + (32 if missed else -20))
    person["hunger"] = max(0, person["hunger"])
    person["social_need"] = min(100, person["social_need"] + 13)
    person["energy"] = max(0, person["energy"] - 8)
    traits = person["traits"]
    spouse = "Luca" if person["name"] == "Mely" else "Mely" if person["name"] == "Luca" else None
    market = village.businesses["market"]
    can_shop = market["stock"].get("bread", 0) > 0 and home["cash"] >= village.bread_price
    choices = [
        (25 + traits["drive"] + (25 if home["cash"] < 16 else 0), "working",
         person["workplace"], "Household income needs attention"),
        (25 + max(0, 70 - person["energy"]) * 2, "resting",
         person["home"], "Needs to recover energy"),
        (15 + person["social_need"] + traits["sociable"], "visiting neighbors",
         "home_3" if person["home"] != "home_3" else "home_1", "Wants company"),
    ]
    if spouse:
        choices.append((23 + person["social_need"] + traits["care"], "spending time with spouse",
                        person["home"], f"Wants time with {spouse}"))
    if person["hunger"] >= 25:
        choices.append((30 + person["hunger"] * 2, "seeking food" if can_shop else "looking for help",
                        "market" if can_shop else person["home"],
                        "Hungry after a missed meal" if missed else "Food is running low"))
    # Stable tie breaker makes decisions reproducible for saved games.
    _, action, destination, reason = max(choices, key=lambda choice: choice[0])
    person["activity"] = action
    person["destination"] = destination
    person["last_reason"] = reason
    if action == "resting":
        person["energy"] = min(100, person["energy"] + 47)
    elif action == "working":
        person["energy"] = max(0, person["energy"] - 16)
    elif action in ("visiting neighbors", "spending time with spouse"):
        person["social_need"] = max(0, person["social_need"] - 48)
        person["mood"] = min(100, person["mood"] + 5)
        if spouse and action == "spending time with spouse":
            person["relationships"][spouse] = min(100, person["relationships"][spouse] + 1)
    elif action == "looking for help":
        person["mood"] = max(0, person["mood"] - 7)
    if missed:
        person["mood"] = max(0, person["mood"] - 5)
    memory = f"Day {day}: {action} because {reason.lower()}."
    if not person["memories"] or person["memories"][-1] != memory:
        person["memories"].append(memory)
        person["memories"] = person["memories"][-6:]
