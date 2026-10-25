"""Persistent motives and daily decisions for Copperside residents."""
from math import dist

TRAITS = {
    "Mely": {"drive": 18, "sociable": 9, "care": 15},
    "Luca": {"drive": 12, "sociable": 5, "care": 18},
    "Ada": {"drive": 12, "sociable": 11, "care": 5},
    "Bram": {"drive": 16, "sociable": 5, "care": 6},
    "Agnes": {"drive": 9, "sociable": 15, "care": 7},
    "Dara": {"drive": 11, "sociable": 13, "care": 8},
}
ASPIRATIONS = {
    "Mely": "Keep Copperside's steam reliable and affordable",
    "Luca": "Make repairs locally instead of waiting for imports",
    "Ada": "Keep the farm and her household secure",
    "Bram": "Build a mill that never runs short",
    "Agnes": "Feed every household in the village",
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
    """Choose visits from needs; rewards are earned only at the destination."""
    from daily_life import SHIFT_SECONDS, FOOD_ACTIONS
    prepare(person)
    if not arrived:
        return
    person["visit_seconds"] = person.get("visit_seconds", 0.0) + dt
    duration = 12 + sum(map(ord, person["name"])) % 13
    worked = village.daily_life.get("worked", {}).get(person["name"], 0.0)
    action = person["activity"]
    finished_work = action == "working" and worked >= SHIFT_SECONDS
    finished_shopping = action in FOOD_ACTIONS and home["bought"] >= home["bread_need"]
    if (person["last_reason"] != "Starting the day" and person["visit_seconds"] < duration
            and not finished_work and not finished_shopping):
        return
    completed_visit = person["visit_seconds"] >= duration
    person["visit_seconds"] = 0.0
    if action == "resting" and completed_visit:
        person["energy"] = min(100, person["energy"] + 45)
    elif action == "working" and finished_work and person.get("fatigue_day") != village.day:
        # A paid shift has one fatigue cost, even when its duration spans several
        # shorter activity visits or a save/reload.
        person["energy"] = max(0, person["energy"] - 22)
        person["fatigue_day"] = village.day
    elif action in ("visiting neighbors", "spending time with spouse") and completed_visit and social_company(person, village):
        person["social_need"] = max(0, person["social_need"] - 45)
        person["mood"] = min(100, person["mood"] + 3)
        if action == "spending time with spouse":
            spouse = "Luca" if person["name"] == "Mely" else "Mely"
            person["relationships"][spouse] = min(100, person["relationships"].get(spouse, 20) + 1)
    person["social_need"] = min(100, person["social_need"] + 14)
    cycle = person.get("activity_cycle", 0) + 1
    person["activity_cycle"] = cycle
    neighbors = [p for p in village.citizens if p["home"] != person["home"]]
    friend = neighbors[(cycle + sum(map(ord, person["name"]))) % len(neighbors)] if neighbors else person
    # Visit a neighbor where they currently intend to be, rather than always
    # standing at an empty workplace after their shift is over.
    meeting_place = friend.get("destination") or friend["home"]
    # Following destinations can draw the whole town to one cottage. Once a
    # visit finishes, do not renew that same visit forever just because the
    # next neighbor also intends to stay there. Call at another household;
    # social rewards still require real company when the resident arrives.
    if (completed_visit and action in ("visiting neighbors", "spending time with spouse")
            and meeting_place == person.get("destination")):
        alternatives = [p for p in neighbors if p["home"] != meeting_place]
        if alternatives:
            friend = alternatives[cycle % len(alternatives)]
            meeting_place = friend["home"]
    # Social needs must not trap a resident in endless visits while today's
    # short paid shift is unfinished. Hunger and exhaustion still take priority.
    choices = [(max(0, 70 - person["energy"]) * 2, "resting", person["home"], "Needs a break"),
               (min(70, 20 + person["social_need"] + person["traits"]["sociable"]), "visiting neighbors",
                meeting_place, f"Wants to catch up with {friend['name']}")]
    spouse = "Luca" if person["name"] == "Mely" else "Mely" if person["name"] == "Luca" else None
    spouse_person = next((p for p in village.citizens if p["name"] == spouse), None)
    if spouse_person and spouse_person.get("destination") == person["home"]:
        choices.append((min(75, 23 + person["social_need"] + person["traits"]["care"]), "spending time with spouse",
                        person["home"], f"Wants time with {spouse}"))
    employer = village.businesses.get(person["workplace"])
    if employer and employer["workers"] > 0 and worked < SHIFT_SECONDS:
        choices.append((70 + person["traits"]["drive"] + (20 if home["cash"] < 16 else 0),
                        "working", person["workplace"], "Finishing today's paid shift"))
    members = sorted(p["name"] for p in village.citizens if p["home"] == person["home"])
    shopper = members[village.day % len(members)]
    if person["name"] == shopper and home["bought"] < home["bread_need"]:
        affordable = home["cash"] >= village.bread_price
        available = village.businesses["market"]["stock"].get("bread", 0) > 1
        score = 140 + person["hunger"] if affordable and available else 100 if affordable and worked >= SHIFT_SECONDS else 20
        reason = "Buying the household's next meal" if available else "Waiting for fresh bread deliveries"
        choices.append((score, "seeking food", "market", reason))
    _, action, destination, reason = max(choices, key=lambda choice: choice[0])
    person.update(activity=action, destination=destination, last_reason=reason)


def social_company(person, village):
    """A visit only satisfies social needs when somebody is actually there."""
    spouse = ("Luca" if person["name"] == "Mely" else "Mely") if person["activity"] == "spending time with spouse" else None
    for other in village.citizens:
        if other is person or spouse and other["name"] != spouse:
            continue
        if other.get("destination") != person.get("destination"):
            continue
        if "position" in person and "position" in other:
            if dist(person["position"], other["position"]) > 140:
                continue
        elif other.get("activity") != "at home" or other["home"] != person.get("destination"):
            continue
        return True
    return False


def decide(person, home, village, *, day):
    """Settle a day's meals once; visiting rewards wait for actual arrival."""
    from daily_life import SHIFT_SECONDS
    prepare(person)
    missed = max(0, home["bread_need"] - home["bought"])
    person["hunger"] = max(0, min(100, person["hunger"] + (20 + 12 * missed if missed else -25)))
    person["social_need"] = min(100, person["social_need"] + 13)
    person["energy"] = max(0, person["energy"] - 8)
    person["mood"] = max(0, min(100, person["mood"] + (-5 if missed else 3)))
    worked = village.daily_life.get("worked", {}).get(person["name"], 0.0)
    paid = village.daily_life.get("paid", {}).get(person["name"], 0)
    if missed:
        can_shop = village.businesses["market"]["stock"].get("bread", 0) > 1 and home["cash"] >= village.bread_price
        person.update(activity="seeking food" if can_shop else "looking for help",
                      destination="market" if can_shop else person["home"], last_reason="Hungry after a missed meal")
    memory = f"Day {day}: worked {round(worked / SHIFT_SECONDS * 100)}%; earned {paid}c; home ate {home['bought']}/{home['bread_need']}."
    person["memories"] = (person["memories"] + [memory])[-6:]
