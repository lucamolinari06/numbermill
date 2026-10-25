"""Hand-authored jobs. Future generated jobs can use this same contract."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Commission:
    key: str
    level: int
    title: str
    customer: str
    description: tuple[str, str, str]
    input_a: str
    input_b: str
    output: str
    logic: str
    reward: int
    benefit: str
    prerequisite: str | None = None
    input_c: str | None = None
    business_id: str | None = None
    machine: str | None = None
    materials: tuple[tuple[str, int], ...] = ()
    unlock_day: int = 1


COMMISSIONS = {
    "mill": Commission(
        key="mill",
        level=1,
        title="Mill safety controller",
        customer="Miller",
        description=(
            "The mill runs only when grain is present",
            "AND the boiler is ready. Connect A and B",
            "to the lamp through a machine.",
        ),
        input_a="grain present",
        input_b="boiler ready",
        output="mill runs",
        logic="AND",
        reward=24,
        benefit="Mill capacity: 1 to 4 flour/day. More flour reaches bakers.",
    ),
    "bakery": Commission(
        key="bakery",
        level=2,
        title="Bakery steam selector",
        customer="Baker",
        description=(
            "The ovens run when the main boiler OR",
            "the backup boiler is ready. Reuse a saved",
            "floor plan and adapt its central valve.",
        ),
        input_a="main boiler",
        input_b="backup boiler",
        output="ovens run",
        logic="OR",
        reward=30,
        benefit="Oven capacity: 3 to 5 bread/day, when flour is available.",
        prerequisite="mill",
    ),
    "vent": Commission(
        key="vent",
        level=3,
        title="Bakery safety vent",
        customer="Baker",
        description=(
            "The vent stays on unless both the oven and",
            "pressure switches are active. Build AND, then",
            "invert its output with a NOT valve.",
        ),
        input_a="oven switch",
        input_b="pressure switch",
        output="vent open",
        logic="NAND",
        reward=20,
        benefit="Prevents the bakery's seventh-day boiler shutdown.",
        prerequisite="bakery",
    ),
    "market": Commission(
        key="market",
        level=4,
        title="Market cooling controller",
        customer="Merchant",
        description=(
            "Cool the storeroom when neither the delivery",
            "door nor hot boiler is active. Combine OR",
            "with a NOT valve to protect bread stock.",
        ),
        input_a="delivery door",
        input_b="hot boiler",
        output="cooling on",
        logic="NOR",
        reward=22,
        benefit="Prevents one loaf from spoiling every sixth day.",
        prerequisite="bakery",
    ),
    "pump": Commission(
        key="pump",
        level=5,
        title="Farm pump interlock",
        customer="Farmer",
        description=("Run the pump when the river is high and", "the mill is not drawing water. Combine", "AND with an inverted mill switch."),
        input_a="river high",
        input_b="mill drawing",
        output="pump runs",
        logic="AND_NOT",
        reward=28,
        benefit="Irrigation pump adds one grain on days 2, 4, and 6.",
        prerequisite="mill",
    ),
    "sorter": Commission(
        key="sorter",
        level=6,
        title="Market order sorter",
        customer="Merchant",
        description=("Replenish the counter when at least two", "of the east street, west street, and", "delivery queue signals are active."),
        input_a="east street busy",
        input_b="west street busy",
        input_c="delivery queue busy",
        output="counter replenishes",
        logic="MAJORITY",
        reward=26,
        benefit="A small market reserve helps serve busy shopping days.",
        prerequisite="market",
    ),
}


# Later jobs practice distinct behaviors using the existing gates and routed
# traces. A linear prerequisite keeps one new brief in focus at a time.
_LATER_JOBS = (
    ("fuel_diverter", "Fuel siding diverter", "Mely", "fuel_yard", "XOR",
     ("north wagon", "south wagon"), "siding opens",
     ("Open the siding for one waiting wagon.", "Close it if both sidings are occupied", "or if neither wagon has arrived.")),
    ("mill_agreement", "Mill belt synchronizer", "Bram", "mill", "XNOR",
     ("upper belt running", "lower belt running"), "belts synchronized",
     ("The two belt sensors must agree.", "Signal safe when both belts run", "or when both belts have stopped.")),
    ("bakery_inspection", "Bakery tray inspection", "Agnes", "bakery", "IMPLIES",
     ("tray present", "tray inspected"), "line safe",
     ("An occupied tray must be inspected.", "An empty line is safe, regardless", "of the inspection switch.")),
    ("farm_release", "Farm sluice release", "Ada", "farm", "ALL_THREE",
     ("water available", "channel clear", "sluice lock secured"), "sluice opens",
     ("Release water only with all three", "safety signals active. A missing", "signal must keep the sluice shut.")),
    ("market_bell", "Market service bell", "Dara", "market", "ANY_THREE",
     ("east counter waiting", "west counter waiting", "delivery waiting"), "bell rings",
     ("Ring the service bell if any counter", "or delivery needs attention. Silence", "it only when all three are quiet.")),
    ("parts_selector", "Repair bench selector", "Luca", "parts_shop", "MUX",
     ("hand-bench request", "lathe request", "lathe selected"), "work authorized",
     ("The selector chooses a work request.", "C off: follow the hand bench (A).", "C on: follow the lathe request (B).")),
    ("fuel_parity", "Fuel tally checker", "Mely", "fuel_yard", "ODD_PARITY",
     ("first tally bit", "second tally bit", "third tally bit"), "odd tally",
     ("Check the three-bit tally signal.", "Light the output for one or three", "active bits; otherwise leave it off.")),
    ("mill_single_feed", "Mill single-feed guard", "Bram", "mill", "EXACTLY_ONE",
     ("hopper A feeding", "hopper B feeding", "hopper C feeding"), "feed accepted",
     ("Accept exactly one feeding hopper.", "Reject an empty feed and reject", "any two or three hoppers together.")),
    ("bakery_pairing", "Bakery batch pairing", "Agnes", "bakery", "EXACTLY_TWO",
     ("batch A ready", "batch B ready", "batch C ready"), "pair dispatched",
     ("Dispatch only a pair of ready batches.", "Exactly two signals must be active;", "one, none, or all three must wait.")),
    ("farm_consensus", "Farm sensor consensus", "Ada", "farm", "UNANIMOUS",
     ("north sensor", "field sensor", "south sensor"), "sensors agree",
     ("Approve the three sensors only when", "they all agree. All off is valid", "as well as all on; mixtures fail.")),
    ("market_dispatch", "Market dispatch interlock", "Dara", "market", "INHIBITED_OR",
     ("counter requests stock", "delivery requests stock", "loading dock blocked"), "dispatch allowed",
     ("Serve either stock request when the", "loading dock is clear. A blocked", "dock must stop every dispatch.")),
    ("parts_priority", "Repair priority controller", "Luca", "parts_shop", "PRIORITY",
     ("urgent repair", "routine repair", "bench reserved"), "repair authorized",
     ("An urgent repair always proceeds.", "A routine repair proceeds only if", "the bench has not been reserved.")),
)

for index, (key, title, customer, business, logic, inputs, output, description) in enumerate(_LATER_JOBS):
    COMMISSIONS[key] = Commission(
        key=key, level=7 + index, title=title, customer=customer,
        description=description, input_a=inputs[0], input_b=inputs[1],
        input_c=inputs[2] if len(inputs) == 3 else None, output=output,
        logic=logic, reward=20 + 2 * index,
        benefit=("Daily capacity +1 and working stock +1; capped at two later controllers." if business in ("farm", "mill", "bakery", "market") else
                 "Stock +1; timber-kit orders can fund a packing job." if key == "parts_selector" else
                 "Stock +1; metal-kit orders can fund a packing job." if key == "parts_priority" else
                 "Working stock buffer +1; production rate unchanged."),
        prerequisite="sorter" if index == 0 else _LATER_JOBS[index - 1][0],
        business_id=business, machine=f"{key}_controller",
        materials=(("timber", 1), ("metal", 1 + index // 6), ("fittings", 1)),
        unlock_day=8 + index * 4,
    )

EXTENDED_CONTRACTS = {
    key: (job.business_id, job.machine, job.reward)
    for key, job in COMMISSIONS.items() if job.business_id
}


def post_extended_offers(village):
    """Offer one affordable later job after its prerequisite and opening day.

    Installation lists, rather than transient convenience attributes, are the
    source of truth so old and new saves share the same unlock behavior.
    """
    if any(village.offers.get(key, {}).get("status") in ("open", "bid")
           for key in EXTENDED_CONTRACTS):
        return
    for key, (business_id, _machine, reward) in EXTENDED_CONTRACTS.items():
        job = COMMISSIONS[key]
        if key in village.offers or village.day < job.unlock_day:
            continue
        prerequisite = village.offers.get(job.prerequisite, {})
        if prerequisite.get("status") not in ("player", "rival"):
            continue
        firm = village.businesses.get(business_id)
        if not firm or firm.get("cash", 0) < reward + 16:
            continue
        village.offers[key] = {
            "status": "open", "posted_day": village.day, "due_day": village.day + 8,
            "reason": job.benefit,
        }
        village.last_contract_event = f"{job.customer} posted {job.title.lower()}."
        village.journal.insert(0, village.last_contract_event)
        return
