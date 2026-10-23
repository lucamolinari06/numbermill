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
        description=("Send a loaf to the household counter when", "either the east or west street is busy.", "A shared signal needs a splitter."),
        input_a="east street busy",
        input_b="west street busy",
        output="counter replenishes",
        logic="MAJORITY",
        reward=26,
        benefit="A small market reserve helps serve busy shopping days.",
        prerequisite="market",
    ),
}
