"""Small binary inventions that earn permanent industrial arithmetic blocks."""
from copy import deepcopy
from dataclasses import dataclass
from itertools import product
from circuit import ARITHMETIC, Circuit, Part, edge_terminals

GATES = ("AND", "OR", "XOR", "NOT")
GRID_X, GRID_Y, GRID_W, GRID_H = 75, 263, 115, 66
GRID_COLS, GRID_ROWS = 7, 5
MAX_GATES = GRID_COLS * GRID_ROWS


def gate_pos(gate, index):
    return gate.get("pos", [index % 4 * 2, index // 4 * 2])


@dataclass(frozen=True)
class Challenge:
    key: str
    title: str
    unlocks: tuple[str, ...]
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    slots: int
    prerequisite: str | None
    lesson: tuple[str, ...]


CHALLENGES = {
    "adder": Challenge("adder", "Half-adder", ("ADD",), ("A", "B"), ("SUM", "CARRY"), 2, None,
        ("Add two single-bit inputs.", "Output the low sum bit", "and a separate carry bit.")),
    "subtractor": Challenge("subtractor", "Difference and borrow", ("SUB",), ("A", "B"), ("DIFF", "BORROW"), 3, "ADD",
        ("Subtract B from A.", "Output the difference bit", "and a separate borrow bit.", "Borrow indicates that a", "higher bit is needed.")),
    "comparator": Challenge("comparator", "Binary comparison", ("GT", "EQ"), ("A", "B"), ("GT", "EQ"), 4, None,
        ("Compare two single-bit inputs.", "GT is 1 when A exceeds B.", "EQ is 1 when they match.")),
    "multiplier": Challenge("multiplier", "2-bit multiplication", ("MUL",), ("A0", "A1", "B0", "B1"), ("P0", "P1", "P2", "P3"), 8, "ADD",
        ("Multiply two 2-bit numbers.", "A0/B0 are the low bits.", "A1/B1 are the high bits.", "P3 to P0 is the product,", "from highest to lowest bit.")),
}
FOR_BLOCK = {block: key for key, challenge in CHALLENGES.items() for block in challenge.unlocks}


def required_blocks(rows):
    """Inspect embedded versions too: nested devices cannot bypass invention."""
    found = set()
    stack = list(rows)
    while stack:
        row = stack.pop()
        if not isinstance(row, dict):
            continue
        if row.get("kind") in ARITHMETIC:
            found.add(row["kind"])
        if row.get("kind") == "DEVICE" and isinstance(row.get("device"), dict):
            stack.extend(row["device"].get("parts", []))
    return found


def locked_blocks(village, rows):
    return required_blocks(rows) - set(village.arithmetic_unlocks)


def draft(village, key):
    challenge = CHALLENGES[key]
    return village.invention_drafts.setdefault(key, {
        "gates": [], "outputs": {name: None for name in challenge.outputs}, "routes": {}})


def expected(key, bits):
    if key == "multiplier":
        a, b = bits["A0"] + 2 * bits["A1"], bits["B0"] + 2 * bits["B1"]
        return {f"P{i}": (a * b >> i) & 1 for i in range(4)}
    a, b = bits["A"], bits["B"]
    if key == "adder":
        return {"SUM": (a + b) & 1, "CARRY": (a + b) >> 1}
    if key == "subtractor":
        return {"DIFF": (a - b) & 1, "BORROW": int(a < b)}
    return {"GT": int(a > b), "EQ": int(a == b)}


def validate(key, design):
    if "floor" in design:
        return validate_floor(key, design["floor"])
    challenge = CHALLENGES[key]
    gates = design.get("gates", [])
    if len(gates) > MAX_GATES or set(design.get("outputs", {})) != set(challenge.outputs):
        return "The canvas is full or an output terminal is missing."
    positions = [tuple(gate_pos(gate, i)) for i, gate in enumerate(gates) if gate.get("kind")]
    if len(positions) != len(set(positions)) or any(not (0 <= x < GRID_COLS and 0 <= y < GRID_ROWS) for x, y in positions):
        return "Move gates into separate canvas cells."
    sources = set(challenge.inputs) | {f"G{i}" for i, gate in enumerate(gates) if gate.get("kind") in GATES}
    dependencies = {}
    for i, gate in enumerate(gates):
        kind = gate.get("kind")
        if kind is None:
            continue
        if kind not in GATES:
            return "Only binary AND, OR, XOR and NOT gates are allowed."
        count = 1 if kind == "NOT" else 2
        if len(gate.get("inputs", [])) != 2 or any(source not in sources for source in gate["inputs"][:count]):
            return f"Connect every input of G{i + 1}."
        dependencies[f"G{i}"] = [s for s in gate["inputs"][:count] if s.startswith("G")]
    if any(source not in sources for source in design["outputs"].values()):
        return "Connect each fixed output terminal."
    visited, active = set(), set()
    def visit(node):
        if node in active:
            return False
        if node in visited:
            return True
        active.add(node)
        if not all(visit(other) for other in dependencies[node]):
            return False
        active.remove(node)
        visited.add(node)
        return True
    if not all(visit(node) for node in dependencies):
        return "Feedback loop detected. Build a forward binary prototype."
    return None


def step(key, design, bits, previous):
    values = {**{name: 0 for name in CHALLENGES[key].inputs}, **bits, **previous}
    current = dict(bits)
    for i, gate in enumerate(design["gates"]):
        a, b = [bool(values.get(source, 0)) for source in gate["inputs"]]
        kind = gate["kind"]
        current[f"G{i}"] = int({"AND": a and b, "OR": a or b, "XOR": a != b, "NOT": not a}.get(kind, 0))
    return current


def evaluate(key, design, bits):
    if "floor" in design:
        error = validate_floor(key, design["floor"])
        if error:
            return {}, [], error
        circuit = Circuit.from_snapshot(design["floor"])
        circuit.switches.update(bits)
        trace = []
        for _ in range(len(circuit.parts) + 2):
            circuit.tick()
            trace.append(dict(circuit.active))
        return {name: circuit.output_value(name) for name in CHALLENGES[key].outputs}, trace, None
    error = validate(key, design)
    values, trace = dict(bits), []
    if error:
        return {}, trace, error
    for _ in range(len(design["gates"]) + 2):
        values = step(key, design, bits, values)
        trace.append(values.copy())
    return {name: values[source] for name, source in design["outputs"].items()}, trace, None


def test(village, key):
    challenge, design = CHALLENGES[key], draft(village, key)
    rows = []
    for combination in product((0, 1), repeat=len(challenge.inputs)):
        bits = dict(zip(challenge.inputs, combination))
        actual, trace, error = evaluate(key, design, bits)
        target = expected(key, bits)
        rows.append({"bits": bits, "expected": target, "actual": actual,
                     "passed": error is None and actual == target, "error": error})
    prerequisite_met = not challenge.prerequisite or challenge.prerequisite in village.arithmetic_unlocks
    if prerequisite_met and all(row["passed"] for row in rows):
        for block in challenge.unlocks:
            if block not in village.arithmetic_unlocks:
                village.arithmetic_unlocks.append(block)
        village.invention_records[key] = {"day": village.day, "design": deepcopy(design), "cases": len(rows)}
    return rows


def floor_from_draft(key, design):
    """Bring older slot and sandbox prototypes onto the shared workshop floor."""
    if "floor" in design:
        circuit = Circuit.from_snapshot(design["floor"])
        circuit.layout_terminals(CHALLENGES[key].inputs, CHALLENGES[key].outputs)
        return circuit
    challenge = CHALLENGES[key]
    terminals = edge_terminals(challenge.inputs, challenge.outputs)
    positions = {f"G{i}": (3 + gate_pos(gate, i)[0], 2 + gate_pos(gate, i)[1])
                 for i, gate in enumerate(design.get("gates", [])) if gate.get("kind") in GATES}
    sources = {port["name"]: pos for pos, port in terminals.items() if not port["output"]}
    sources.update(positions)
    circuit = Circuit({positions[f"G{i}"]: Part(gate["kind"]) for i, gate in enumerate(design.get("gates", []))
                       if f"G{i}" in positions}, terminals=terminals)
    circuit.trace_mode = True
    def link(source, target, pin, route_key):
        if source in sources:
            points = [[max(2, min(13, 3 + (x - GRID_X) / GRID_W)),
                       max(.5, min(8.5, 2 + (y - GRID_Y) / GRID_H))]
                      for x, y in design.get("routes", {}).get(route_key, [])]
            circuit.connect(sources[source], target, pin, points)
    for i, gate in enumerate(design.get("gates", [])):
        if f"G{i}" in positions:
            for pin, source in enumerate(gate["inputs"][:1 if gate["kind"] == "NOT" else 2]):
                link(source, positions[f"G{i}"], pin, f"G{i}:{pin}")
    for pos, port in terminals.items():
        if port["output"]:
            link(design.get("outputs", {}).get(port["name"]), pos, 0, f"O:{port['name']}")
    return circuit


def validate_floor(key, rows):
    try:
        circuit = Circuit.from_snapshot(rows)
    except (ValueError, TypeError, KeyError):
        return "This prototype contains an invalid floor plan."
    challenge = CHALLENGES[key]
    inputs = [port["name"] for port in circuit.terminals.values() if not port["output"]]
    outputs = [port["name"] for port in circuit.terminals.values() if port["output"]]
    if sorted(inputs) != sorted(challenge.inputs) or sorted(outputs) != sorted(challenge.outputs):
        return "Use this invention's named input and output terminals."
    for pos, part in circuit.parts.items():
        if pos not in circuit.terminals and part.kind not in GATES:
            return "Invent using AND, OR, XOR and NOT gates."
        for pin in range(len(part.ports()[0])):
            if not any(tuple(t["target"]) == pos and t["pin"] == pin for t in circuit.traces):
                return "Connect every gate input and output terminal."
    dependencies = {pos: [tuple(t["source"]) for t in circuit.traces if tuple(t["target"]) == pos]
                    for pos in circuit.parts}
    visited, active = set(), set()
    def visit(pos):
        if pos in active:
            return False
        if pos in visited:
            return True
        active.add(pos)
        if not all(visit(source) for source in dependencies[pos]):
            return False
        active.remove(pos)
        visited.add(pos)
        return True
    if not all(visit(pos) for pos in dependencies):
        return "Feedback loop detected. Build a forward binary prototype."
    return None


class Bench:
    """Invention objectives and evidence; editing uses the main workshop UI."""
    def __init__(self, village, key):
        self.village, self.key = village, key
        self.challenge = CHALLENGES[key]
        previous = draft(village, key)
        self.circuit = floor_from_draft(key, previous)
        self.design = {"floor": self.circuit.snapshot(), "port_names": previous.get("port_names", {}).copy()}
        village.invention_drafts[key] = self.design
        self.rows = []
        self.message = "Place gates and draw traces on the workshop floor."
        self.show_results = False

    @property
    def bits(self):
        return self.circuit.switches

    @bits.setter
    def bits(self, values):
        self.circuit.switches.update(values)

    @property
    def ticks(self):
        return self.circuit.tick_count

    def sync(self):
        self.design["floor"] = self.circuit.snapshot()

    def edit(self):
        self.rows = []
        self.show_results = False
        self.circuit.reset()
        self.sync()

    def tick(self):
        self.show_results = False
        self.circuit.tick()

    def run_tests(self):
        self.sync()
        self.rows = test(self.village, self.key)
        self.show_results = True
        passed = sum(row["passed"] for row in self.rows)
        if self.challenge.prerequisite and self.challenge.prerequisite not in self.village.arithmetic_unlocks:
            self.message = f"Complete {self.challenge.prerequisite} first."
        elif passed == len(self.rows):
            self.message = f"{passed}/{len(self.rows)} passed. Unlocked {', '.join(self.challenge.unlocks)}!"
        else:
            self.message = self.rows[0]["error"] or f"{passed}/{len(self.rows)} passed. Check the failing cases."

    def load_case(self, index):
        self.bits = self.rows[index]["bits"]
        self.edit()
        self.message = "Case loaded. Step through the workshop signals."
