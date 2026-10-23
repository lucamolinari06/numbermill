"""Small binary inventions that earn permanent industrial arithmetic blocks."""
from copy import deepcopy
from dataclasses import dataclass
from itertools import product
import pygame
from circuit import ARITHMETIC

GATES = ("AND", "OR", "XOR", "NOT")


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
        "gates": [{"kind": None, "inputs": [None, None]} for _ in range(challenge.slots)],
        "outputs": {name: None for name in challenge.outputs}})


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
    challenge = CHALLENGES[key]
    gates = design.get("gates", [])
    if len(gates) != challenge.slots or set(design.get("outputs", {})) != set(challenge.outputs):
        return "Use the prototype's fixed grid and output terminals."
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
    error = validate(key, design)
    values, trace = dict(bits), []
    if error:
        return {}, trace, error
    for _ in range(CHALLENGES[key].slots + 2):
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


class Bench:
    def __init__(self, village, key):
        self.village, self.key = village, key
        self.challenge = CHALLENGES[key]
        self.design = draft(village, key)
        self.selected = "AND"
        self.source = None
        self.bits = {name: 0 for name in self.challenge.inputs}
        self.values = self.bits.copy()
        self.ticks = 0
        self.rows = []
        self.message = "Choose a gate, click a slot. Click a source dot, then a destination socket."
        self.show_results = False

    def edit(self):
        self.rows = []
        self.show_results = False
        self.values = self.bits.copy()
        self.ticks = 0

    def tick(self):
        self.show_results = False
        self.values = step(self.key, self.design, self.bits, self.values)
        self.ticks += 1

    def run_tests(self):
        self.rows = test(self.village, self.key)
        self.show_results = True
        passed = sum(row["passed"] for row in self.rows)
        if self.challenge.prerequisite and self.challenge.prerequisite not in self.village.arithmetic_unlocks:
            self.message = f"Complete {self.challenge.prerequisite} first; this lesson cannot grant its unlock yet."
            return
        self.message = (f"{passed}/{len(self.rows)} passed. Permanently unlocked {', '.join(self.challenge.unlocks)}!"
                        if passed == len(self.rows) else self.rows[0]["error"] or f"{passed}/{len(self.rows)} passed. Compare expected and actual output bits.")

    def click(self, point, button):
        if self.show_results:
            for i, row in enumerate(self.rows):
                if button == 1 and pygame.Rect(65, 218 + i * 26, 820, 26).collidepoint(point):
                    self.bits = row["bits"].copy()
                    self.edit()
                    self.message = "Test inputs loaded. Press . to trace one gate layer at a time."
                    break
            return
        for i, name in enumerate(self.challenge.inputs):
            x = 95 + i * 180
            if pygame.Rect(x - 15, 156, 140, 42).collidepoint(point) and button == 1:
                self.bits[name] ^= 1
                self.edit()
                return
            if pygame.Rect(x + 49, 202, 22, 22).collidepoint(point) and button == 1:
                self.source = name
                return
        for i, gate in enumerate(self.design["gates"]):
            x, y = 65 + i % 4 * 215, 260 + i // 4 * 150
            if pygame.Rect(x + 159, y + 38, 22, 22).collidepoint(point) and button == 1 and gate["kind"]:
                self.source = f"G{i}"
                return
            count = 1 if gate["kind"] == "NOT" else 2
            for pin in range(count):
                if pygame.Rect(x - 12, y + 18 + pin * 40, 24, 24).collidepoint(point):
                    if button == 3:
                        gate["inputs"][pin] = None
                    elif self.source and self.source != f"G{i}":
                        gate["inputs"][pin] = self.source
                    self.edit()
                    return
            if pygame.Rect(x + 19, y, 135, 100).collidepoint(point):
                gate["kind"] = self.selected if button == 1 else None
                if button == 3:
                    source = f"G{i}"
                    for other in self.design["gates"]:
                        other["inputs"] = [None if s == source else s for s in other["inputs"]]
                    for output, link in self.design["outputs"].items():
                        if link == source:
                            self.design["outputs"][output] = None
                    if self.source == source:
                        self.source = None
                self.edit()
                return
        for i, name in enumerate(self.challenge.outputs):
            x = 95 + i * 180
            if pygame.Rect(x - 12, 588, 24, 24).collidepoint(point):
                self.design["outputs"][name] = self.source if button == 1 else None
                self.edit()
                return


def screen(game):
    from game import rounded, text, PAPER, TEAL, INK, MUTED, GOLD, RED
    bench = game.invention
    challenge = bench.challenge
    surface = game.screen
    surface.fill((61, 85, 79))
    rounded(surface, PAPER, (25, 20, 1230, 710), 8)
    text(surface, game.big, f"INVENTION / {challenge.title.upper()}", 50, 39, TEAL)
    for i, key in enumerate(CHALLENGES):
        c = CHALLENGES[key]
        ready = c.prerequisite is None or c.prerequisite in game.village.arithmetic_unlocks
        done = all(b in game.village.arithmetic_unlocks for b in c.unlocks)
        label = f"{'+ ' if done else ''}{'/'.join(c.unlocks)}" + (f" / {c.prerequisite} first" if not ready else "")
        game.button((50 + i * 218, 89, 208, 34), label, lambda k=key: game.switch_invention(k), active=key == bench.key, enabled=ready, small=True)
    rounded(surface, (235, 225, 198), (935, 137, 296, 537), 5)
    text(surface, game.heading, "CHALLENGE", 950, 153, TEAL)
    for i, line in enumerate(challenge.lesson):
        text(surface, game.small, line, 950, 193 + i * 25)
    text(surface, game.tiny, f"Budget: {challenge.slots} logic gates", 950, 411, MUTED)
    text(surface, game.tiny, f"Tracing: one gate per step ({bench.ticks})", 950, 434, MUTED)
    text(surface, game.tiny, "Green wires = 1; muted wires = 0", 950, 457, MUTED)
    game.button((950, 632, 265, 30), "BACK [ESC]", game.close_invention, small=True)
    game.button((50, 681, 180, 31), "TEST ALL [T]", game.test_invention, active=True, small=True)
    game.button((244, 681, 140, 31), "STEP [.]", bench.tick, small=True)
    game.button((398, 681, 160, 31), "EDIT / TRACE", lambda: setattr(bench, "show_results", False), small=True)
    text(surface, game.tiny, bench.message[:90], 575, 691, TEAL)
    if bench.show_results:
        input_names = ("A1", "A0", "B1", "B0") if bench.key == "multiplier" else challenge.inputs
        input_label = "A1 A0 | B1 B0" if bench.key == "multiplier" else "A B"
        text(surface, game.small, f"{input_label:<16}EXPECTED             ACTUAL          RESULT", 65, 156, MUTED)
        names = (("P3", "P2", "P1", "P0") if bench.key == "multiplier" else
                 ("CARRY", "SUM") if bench.key == "adder" else
                 ("BORROW", "DIFF") if bench.key == "subtractor" else challenge.outputs)
        text(surface, game.tiny, "Output order: " + ", ".join(names), 65, 185, MUTED)
        text(surface, game.tiny, "Click a case to trace its inputs.", 455, 185, TEAL)
        for i, row in enumerate(bench.rows):
            inp = "".join(str(row["bits"][k]) for k in input_names)
            if bench.key == "multiplier":
                inp = inp[:2] + "|" + inp[2:]
            target = "".join(str(row["expected"][k]) for k in names)
            actual = "".join(str(row["actual"].get(k, "?")) for k in names)
            color = TEAL if row["passed"] else RED
            text(surface, game.small, f"{inp:<16}{target:<21}{actual:<16}{'PASS' if row['passed'] else 'FAIL'}", 65, 218 + i * 26, color)
        return
    source_points = {name: (155 + i * 180, 213) for i, name in enumerate(challenge.inputs)}
    source_points.update({f"G{i}": (235 + i % 4 * 215, 309 + i // 4 * 150) for i in range(challenge.slots)})
    def wire(source, end):
        if source in source_points:
            start = source_points[source]
            color = TEAL if bench.values.get(source, bench.bits.get(source, 0)) else (159, 154, 137)
            mid_y = end[1] - 12
            pygame.draw.lines(surface, color, False, (start, (start[0], mid_y), (end[0] - 15, mid_y), (end[0] - 15, end[1]), end), 3)
    for i, gate in enumerate(bench.design["gates"]):
        x, y = 65 + i % 4 * 215, 260 + i // 4 * 150
        for pin in range(1 if gate["kind"] == "NOT" else 2):
            wire(gate["inputs"][pin], (x, y + 30 + pin * 40))
    for i, name in enumerate(challenge.outputs):
        wire(bench.design["outputs"][name], (95 + i * 180, 600))
    for i, name in enumerate(challenge.inputs):
        x = 95 + i * 180
        game.button((x - 15, 156, 140, 42), f"{name} = {bench.bits[name]}", lambda n=name: (bench.bits.update({n: 1 - bench.bits[n]}), bench.edit()), small=True)
        pygame.draw.circle(surface, GOLD if bench.source == name else TEAL, (x + 60, 213), 8)
    for i, gate in enumerate(bench.design["gates"]):
        x, y = 65 + i % 4 * 215, 260 + i // 4 * 150
        rounded(surface, (220, 203, 166), (x + 19, y, 135, 100), 7)
        text(surface, game.small, f"G{i + 1}: {gate['kind'] or 'place gate'}", x + 25, y + 16)
        text(surface, game.small, str(bench.values.get(f"G{i}", 0)), x + 81, y + 62, TEAL)
        for pin in range(1 if gate["kind"] == "NOT" else 2):
            pygame.draw.circle(surface, TEAL if gate["inputs"][pin] else RED, (x, y + 30 + pin * 40), 7)
            label = gate["inputs"][pin]
            if label:
                label = f"G{int(label[1:]) + 1}" if label.startswith("G") else label
                text(surface, game.tiny, label, x + 23, y + 42 + pin * 19, MUTED)
        pygame.draw.circle(surface, GOLD if bench.source == f"G{i}" else TEAL, (x + 170, y + 49), 8)
    for i, name in enumerate(challenge.outputs):
        x = 95 + i * 180
        pygame.draw.circle(surface, TEAL if bench.design["outputs"][name] else RED, (x, 600), 8)
        text(surface, game.small, f"{name}: {bench.values.get(bench.design['outputs'][name], 0)}", x - 12, 626)
    for i, kind in enumerate(GATES):
        game.button((65 + i * 130, 223, 115, 26), kind, lambda k=kind: setattr(bench, "selected", k), active=bench.selected == kind, small=True)
    text(surface, game.tiny, "Right click a gate to remove it; right click a socket to disconnect.", 65, 660, MUTED)
