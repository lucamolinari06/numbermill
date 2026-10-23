"""Deterministic, tick-based steam logic for the workshop floor."""

from __future__ import annotations

from collections import deque
from copy import deepcopy
from dataclasses import dataclass
from typing import Iterable
from functools import reduce
from operator import or_


WIDTH = 16
HEIGHT = 9
N, E, S, W = range(4)
VECTORS = ((0, -1), (1, 0), (0, 1), (-1, 0))
FIXED = {(1, 3): "A", (4, 6): "B", (9, 3): "LAMP"}
PLACEABLE = ("PIPE", "BEND", "SPLIT", "AND", "OR", "NOT", "XOR")
ARITHMETIC = ("ADD", "SUB", "MUL", "GT", "EQ")
ALL_PARTS = (*PLACEABLE, *ARITHMETIC, "DEVICE")
CONDUCTORS = {"PIPE", "BEND", "SPLIT"}


@dataclass(frozen=True)
class Part:
    kind: str
    rotation: int = 0
    device: dict | None = None

    def ports(self) -> tuple[tuple[int, ...], tuple[int, ...]]:
        """Return ports after clockwise rotation; pipes have no polarity."""
        base = {
            "PIPE": ((W, E), (W, E)),
            "BEND": ((W, N), (W, N)),
            "SPLIT": ((W, N, E), (W, N, E)),
            "AND": ((W, S), (E,)),
            "OR": ((W, S), (E,)),
            "XOR": ((W, S), (E,)),
            "NOT": ((W,), (E,)),
            "DEVICE": ((W, S), (E,)),
            **{kind: ((W, S), (E,)) for kind in ARITHMETIC},
            "A": ((), (E,)),
            "B": ((), (N,)),
            "LAMP": ((W,), ()),
        }[self.kind]
        return tuple((d + self.rotation) % 4 for d in base[0]), tuple(
            (d + self.rotation) % 4 for d in base[1]
        )


@dataclass(frozen=True)
class CommissionCase:
    a: bool
    b: bool
    expected: bool
    actual: bool
    stable: bool
    inputs: tuple[bool, ...] = ()

    @property
    def passed(self) -> bool:
        return self.stable and self.actual == self.expected


class Circuit:
    def __init__(self, parts: dict[tuple[int, int], Part] | None = None):
        self.parts = {pos: Part(kind) for pos, kind in FIXED.items()}
        if parts:
            for pos, part in parts.items():
                if pos not in FIXED and self.in_bounds(pos) and part.kind in ALL_PARTS:
                    if part.kind == "DEVICE":
                        validate_device(part.device)
                        part = Part(part.kind, part.rotation, deepcopy(part.device))
                    self.parts[pos] = part
        self.switches = {"A": False, "B": False}
        self.active: dict[tuple[int, int], bool] = {}
        self.tick_count = 0
        self.reset()

    @staticmethod
    def in_bounds(pos: tuple[int, int]) -> bool:
        x, y = pos
        return 0 <= x < WIDTH and 0 <= y < HEIGHT

    def set_part(self, pos: tuple[int, int], part: Part | None) -> bool:
        if not self.in_bounds(pos) or pos in FIXED:
            return False
        if part is not None and part.kind not in ALL_PARTS:
            return False
        if part and part.kind == "DEVICE":
            validate_device(part.device)
            part = Part(part.kind, part.rotation, deepcopy(part.device))
        if part is None:
            self.parts.pop(pos, None)
        else:
            self.parts[pos] = part
        self.reset()
        return True

    def reset(self) -> None:
        self.devices = {pos: Circuit.from_snapshot(part.device["parts"])
                        for pos, part in self.parts.items() if part.kind == "DEVICE"}
        self.active = {pos: False for pos in self.parts}
        self.tick_count = 0
        self.histories = {
            pos: [False]
            for pos, part in self.parts.items()
            if part.kind in self.switches or part.kind in ("AND", "OR", "NOT", "XOR", "DEVICE", *ARITHMETIC)
        }
        self.history_origin = 0
        self.routes = self._build_routes()
        self.max_route_distance = max(
            (distance for sources in self.routes.values() for _, distance in sources),
            default=0,
        )

    def _build_routes(self) -> dict[tuple[int, int], list[tuple[tuple[int, int], int]]]:
        """Find shortest travel time from each active source through connected pipes."""
        routes: dict[tuple[int, int], list[tuple[tuple[int, int], int]]] = {
            pos: [] for pos, part in self.parts.items() if part.kind in CONDUCTORS
        }
        for source_pos in self.histories:
            _, outputs = self.parts[source_pos].ports()
            queue = deque()
            seen = set()
            for direction in outputs:
                dx, dy = VECTORS[direction]
                neighbor = (source_pos[0] + dx, source_pos[1] + dy)
                part = self.parts.get(neighbor)
                if part and part.kind in CONDUCTORS and (direction + 2) % 4 in part.ports()[0]:
                    queue.append((neighbor, 1))
                    seen.add(neighbor)
            while queue:
                pos, distance = queue.popleft()
                routes[pos].append((source_pos, distance))
                for direction in self.parts[pos].ports()[0]:
                    dx, dy = VECTORS[direction]
                    neighbor = (pos[0] + dx, pos[1] + dy)
                    part = self.parts.get(neighbor)
                    if (
                        neighbor not in seen
                        and part
                        and part.kind in CONDUCTORS
                        and (direction + 2) % 4 in part.ports()[0]
                    ):
                        seen.add(neighbor)
                        queue.append((neighbor, distance + 1))
        return routes

    def input_value(self, pos: tuple[int, int], direction: int) -> bool:
        dx, dy = VECTORS[direction]
        neighbor = (pos[0] + dx, pos[1] + dy)
        source = self.parts.get(neighbor)
        if source is None:
            return False
        _, outputs = source.ports()
        return (direction + 2) % 4 in outputs and self.active.get(neighbor, False)

    def tick(self) -> None:
        next_active: dict[tuple[int, int], bool] = {}
        for pos, part in self.parts.items():
            if part.kind in CONDUCTORS:
                continue
            if part.kind in self.switches:
                value = int(self.switches[part.kind]) & 65535
            else:
                inputs, _ = part.ports()
                values = [self.input_value(pos, direction) for direction in inputs]
                if part.kind == "AND":
                    value = all(values)
                elif part.kind == "XOR":
                    value = bool(values[0]) != bool(values[1])
                elif part.kind in ARITHMETIC:
                    a, b = map(int, values)
                    value = {"ADD": lambda: (a + b) & 65535,
                             "SUB": lambda: max(0, a - b),
                             "MUL": lambda: (a * b) & 65535,
                             "GT": lambda: int(a > b),
                             "EQ": lambda: int(a == b)}[part.kind]()
                elif part.kind == "DEVICE":
                    child = self.devices[pos]
                    child.switches = {"A": values[0], "B": values[1]}
                    # Every nested layer advances once per outer tick. Pipes,
                    # gate delay and internal state use the same circuit rules.
                    value = child.output_value()
                    child.tick()
                elif part.kind == "NOT":
                    value = not values[0]
                elif part.kind == "LAMP":
                    value = int(values[0])
                else:
                    value = any(values)
            next_active[pos] = value
        next_tick = self.tick_count + 1
        for pos, value in next_active.items():
            if pos in self.histories:
                self.histories[pos].append(value)
        for pos, sources in self.routes.items():
            next_active[pos] = reduce(or_, (int(self.histories[source][next_tick - distance - self.history_origin])
                                           for source, distance in sources if next_tick >= distance), 0)
        self.active = next_active
        self.tick_count = next_tick
        excess = len(next(iter(self.histories.values()))) - (self.max_route_distance + 1)
        if excess > 0:
            for history in self.histories.values():
                del history[:excess]
            self.history_origin += excess

    def lamp_on(self) -> bool:
        return bool(self.output_value())

    def output_value(self) -> int:
        return int(self.active[(9, 3)])

    def evaluate(self, a, b):
        """Evaluate one request in isolation; preserve every live nested state."""
        state = deepcopy(self.__dict__)
        try:
            self.switches = {"A": int(a), "B": int(b)}
            self.reset()
            recent = deque(maxlen=8)
            for _ in range(self.settle_budget()):
                self.tick()
                recent.append(self.output_value())
            return self.output_value(), len(set(recent)) == 1
        finally:
            self.__dict__.update(state)

    def snapshot(self) -> list[dict]:
        return [
            {"x": x, "y": y, "kind": part.kind, "rotation": part.rotation,
             **({"device": deepcopy(part.device)} if part.kind == "DEVICE" else {})}
            for (x, y), part in sorted(self.parts.items())
            if (x, y) not in FIXED
        ]

    @classmethod
    def from_snapshot(cls, rows: Iterable[dict]) -> "Circuit":
        parts = {}
        for row in rows:
            try:
                pos = (int(row["x"]), int(row["y"]))
                kind = str(row["kind"])
                rotation = int(row["rotation"]) % 4
            except (KeyError, TypeError, ValueError):
                continue
            if cls.in_bounds(pos) and pos not in FIXED and kind in ALL_PARTS:
                definition = row.get("device") if kind == "DEVICE" else None
                if kind == "DEVICE":
                    validate_device(definition)
                parts[pos] = Part(kind, rotation, deepcopy(definition))
        return cls(parts)

    def commission_test_results(self, logic: str) -> list[CommissionCase]:
        """Run a supported truth table and restore the live machine state."""
        if logic not in ("AND", "OR", "NAND", "NOR", "AND_NOT", "MAJORITY"):
            raise ValueError(f"Unsupported commission logic: {logic}")
        saved_state = deepcopy(self.__dict__)
        results = []
        try:
            rows = (((a, b, c) for a in (False, True) for b in (False, True) for c in (False, True))
                    if logic == "MAJORITY" else
                    ((a, b) for a in (False, True) for b in (False, True)))
            for row in rows:
                a, b = row[:2]
                if logic == "MAJORITY":
                    a, b = row[0], row[1]
                    self.switches = {"A": any(row), "B": sum(row) >= 2}
                else:
                    self.switches = {"A": a, "B": b}
                self.reset()
                history = []
                # Longer nested signal paths need more settling time.
                for _ in range(self.settle_budget()):
                    self.tick()
                    history.append(self.lamp_on())
                expected = (sum(row) >= 2 if logic == "MAJORITY" else
                            (a and not b) if logic == "AND_NOT" else
                            (a and b) if logic == "AND" else
                            (a or b) if logic == "OR" else
                            not (a and b) if logic == "NAND" else not (a or b))
                results.append(CommissionCase(a, b, expected, history[-1], len(set(history[-8:])) == 1, tuple(row)))
            return results
        finally:
            self.__dict__.update(saved_state)

    def settle_budget(self):
        return WIDTH * HEIGHT * 2 + sum(child.settle_budget() for child in self.devices.values())

    def mill_test_results(self) -> list[CommissionCase]:
        return self.commission_test_results("AND")

    def test_mill_commission(self) -> tuple[bool, str]:
        results = self.mill_test_results()
        for case in results:
            if not case.passed:
                return False, f"Failed when A={int(case.a)}, B={int(case.b)}. Lamp should be {int(case.expected)}."
        return True, "All four mill safety checks passed."


def validate_device(definition):
    """Reject recursive definitions while allowing independent pinned copies."""
    stack = [(definition, frozenset())]
    while stack:
        node, ancestors = stack.pop()
        if not isinstance(node, dict) or not isinstance(node.get("parts"), list):
            raise ValueError("Device needs a saved floor plan")
        identity = (node.get("id"), node.get("version", 1))
        if id(node) in ancestors or (identity[0] is not None and identity in ancestors):
            raise ValueError("A device cannot contain its own version")
        path = ancestors | {id(node)} | ({identity} if identity[0] is not None else set())
        for row in node["parts"]:
            if not isinstance(row, dict):
                raise ValueError("Invalid device floor plan")
            if row.get("kind") == "DEVICE":
                stack.append((row.get("device"), path))
