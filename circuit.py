"""Deterministic, tick-based steam logic for the workshop floor."""

from __future__ import annotations

from collections import deque
from copy import deepcopy
from dataclasses import dataclass
from typing import Iterable
from functools import reduce
from operator import or_
from commission_logic import truth_rows


WIDTH = 16
HEIGHT = 9
N, E, S, W = range(4)
VECTORS = ((0, -1), (1, 0), (0, 1), (-1, 0))
FIXED = {(1, 3): "A", (4, 6): "B", (9, 3): "LAMP"}
DEFAULT_TERMINALS = {pos: {"name": "OUT" if kind == "LAMP" else kind, "output": kind == "LAMP"}
                     for pos, kind in FIXED.items()}
PLACEABLE = ("PIPE", "BEND", "SPLIT", "AND", "OR", "NOT", "XOR")
ARITHMETIC = ("ADD", "SUB", "MUL", "GT", "EQ")
SEQUENTIAL = ("CLOCK", "REGISTER", "COUNTER")
UTILITY = ("DIV", "MOD", "MIN", "MAX", "MUX")
ALL_PARTS = (*PLACEABLE, *ARITHMETIC, *SEQUENTIAL, *UTILITY, "DEVICE")
CONDUCTORS = {"PIPE", "BEND", "SPLIT"}


def edge_terminals(inputs, outputs=("OUT",)):
    terminals = {}
    for names, column, output in ((inputs, 0, False), (outputs, WIDTH - 1, True)):
        for i, name in enumerate(names):
            terminals[(column, (i + 1) * HEIGHT // (len(names) + 1))] = {"name": name, "output": output}
    return terminals


def standard_device_ports(rows):
    ports = [row for row in rows if row.get("kind") == "PORT"]
    return not ports or (sorted(p["name"] for p in ports if not p.get("output")) == ["A", "B"]
                         and [p["name"] for p in ports if p.get("output")] == ["OUT"])


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
            "CLOCK": ((), (E,)),
            "REGISTER": ((W, S), (E,)),
            "COUNTER": ((W, S), (E,)),
            **{kind: ((W, S), (E,)) for kind in ARITHMETIC},
            **{kind: ((W, S), (E,)) for kind in UTILITY if kind != "MUX"},
            "MUX": ((W, S, N), (E,)),
            "A": ((), (E,)),
            "B": ((), (N,)),
            "LAMP": ((W,), ()),
            "INPUT": ((), (E,)),
            "OUTPUT": ((W,), ()),
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


@dataclass(frozen=True)
class SequenceCase:
    inputs: dict[str, int]
    ticks: int
    expected: int
    actual: int
    elapsed: int

    @property
    def passed(self) -> bool:
        return self.actual == self.expected


class Circuit:
    def __init__(self, parts: dict[tuple[int, int], Part] | None = None, *, terminals=None, traces=None):
        self.terminals = deepcopy(terminals if terminals is not None else DEFAULT_TERMINALS)
        self.parts = {pos: Part("OUTPUT" if port["output"] else "INPUT")
                      for pos, port in self.terminals.items()} if terminals is not None else {
                          pos: Part(kind) for pos, kind in FIXED.items()}
        self.traces = deepcopy(traces or [])
        self.trace_mode = bool(traces)
        if parts:
            for pos, part in parts.items():
                if pos not in self.terminals and self.in_bounds(pos) and part.kind in ALL_PARTS:
                    if part.kind == "DEVICE":
                        validate_device(part.device)
                        part = Part(part.kind, part.rotation, deepcopy(part.device))
                    self.parts[pos] = part
        self.switches = {port["name"]: False for port in self.terminals.values() if not port["output"]}
        self.active: dict[tuple[int, int], bool] = {}
        self.tick_count = 0
        self.reset()

    @staticmethod
    def in_bounds(pos: tuple[int, int]) -> bool:
        x, y = pos
        return 0 <= x < WIDTH and 0 <= y < HEIGHT

    def set_part(self, pos: tuple[int, int], part: Part | None) -> bool:
        if not self.in_bounds(pos) or pos in self.terminals:
            return False
        if part is not None and part.kind not in ALL_PARTS:
            return False
        if part and part.kind == "DEVICE":
            validate_device(part.device)
            part = Part(part.kind, part.rotation, deepcopy(part.device))
        if part is None:
            self.parts.pop(pos, None)
            self.traces = [trace for trace in self.traces if tuple(trace["source"]) != pos and tuple(trace["target"]) != pos]
        else:
            old = self.parts.get(pos)
            if old and old.kind != part.kind:
                self.traces = [trace for trace in self.traces
                               if not (tuple(trace["source"]) == pos and not part.ports()[1])
                               and not (tuple(trace["target"]) == pos and trace["pin"] >= len(part.ports()[0]))]
            self.parts[pos] = part
        self.reset()
        return True

    def _index_traces(self):
        self.trace_inputs = {}
        for trace in self.traces:
            self.trace_inputs.setdefault((tuple(trace["target"]), trace["pin"]), []).append(tuple(trace["source"]))

    def reset(self) -> None:
        self._index_traces()
        self.devices = {pos: Circuit.from_snapshot(part.device["parts"])
                        for pos, part in self.parts.items() if part.kind == "DEVICE"}
        self.active = {pos: False for pos in self.parts}
        self.tick_count = 0
        self.edge_high = {pos: False for pos, part in self.parts.items()
                          if part.kind in ("REGISTER", "COUNTER")}
        self.histories = {
            pos: [False]
            for pos, part in self.parts.items()
            if (pos in self.terminals and not self.terminals[pos]["output"]) or part.kind in ("AND", "OR", "NOT", "XOR", "DEVICE", *ARITHMETIC, *SEQUENTIAL, *UTILITY)
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
        pin = self.parts[pos].ports()[0].index(direction)
        links = self.trace_inputs.get((pos, pin), [])
        if links:
            return reduce(or_, (int(self.active.get(source, 0)) for source in links), 0)
        if self.trace_mode:
            return 0
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
            if pos in self.terminals and not self.terminals[pos]["output"]:
                value = int(self.switches[self.terminals[pos]["name"]]) & 65535
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
                elif part.kind == "MUX":
                    # Logical pin order is data A, data B, select in every
                    # rotation. Nonzero selects B; selected data stays numeric.
                    value = int(values[1] if values[2] else values[0]) & 65535
                elif part.kind in UTILITY:
                    a, b = (int(value) & 65535 for value in values)
                    value = {"DIV": lambda: a // b if b else 0,
                             "MOD": lambda: a % b if b else 0,
                             "MIN": lambda: min(a, b),
                             "MAX": lambda: max(a, b)}[part.kind]()
                elif part.kind == "CLOCK":
                    # Reset is tick zero, low. Each low/high phase lasts two
                    # ticks; the first rising edge is produced on tick two.
                    value = ((self.tick_count + 1) // 2) % 2
                elif part.kind in ("REGISTER", "COUNTER"):
                    edge = bool(values[1] if part.kind == "REGISTER" else values[0])
                    rising = edge and not self.edge_high[pos]
                    value = int(self.active[pos])
                    if part.kind == "REGISTER" and rising:
                        value = int(values[0]) & 65535
                    elif part.kind == "COUNTER":
                        if values[1]:
                            value = 0
                        elif rising:
                            value = (value + 1) & 65535
                    # Track the pulse even during reset, so releasing reset
                    # while a pulse stays high cannot create a false edge.
                    self.edge_high[pos] = edge
                elif part.kind == "DEVICE":
                    child = self.devices[pos]
                    child.switches = {"A": values[0], "B": values[1]}
                    # Every nested layer advances once per outer tick. Pipes,
                    # gate delay and internal state use the same circuit rules.
                    value = child.output_value()
                    child.tick()
                elif part.kind == "NOT":
                    value = not values[0]
                elif part.kind in ("LAMP", "OUTPUT"):
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
        excess = max((len(history) for history in self.histories.values()), default=1) - (self.max_route_distance + 1)
        if excess > 0:
            for history in self.histories.values():
                del history[:excess]
            self.history_origin += excess

    def lamp_on(self) -> bool:
        return bool(self.output_value())

    def output_value(self, name=None) -> int:
        return next((int(self.active.get(pos, 0)) for pos, port in self.terminals.items()
                     if port["output"] and (name is None or port["name"] == name)), 0)

    def connect(self, source, target, pin, points=()):
        """One explicit source per input socket; crossed traces never join."""
        source, target = tuple(source), tuple(target)
        if source == target or source not in self.parts or target not in self.parts:
            return False
        if not self.parts[source].ports()[1] or not 0 <= pin < len(self.parts[target].ports()[0]):
            return False
        self.traces = [t for t in self.traces if tuple(t["target"]) != target or t["pin"] != pin]
        self.traces.append({"source": list(source), "target": list(target), "pin": pin,
                            "points": [list(point) for point in points]})
        self.trace_mode = True
        self.reset()
        return True

    def disconnect(self, target, pin):
        self.traces = [t for t in self.traces if tuple(t["target"]) != tuple(target) or t["pin"] != pin]
        self.reset()

    def layout_terminals(self, inputs, outputs=("OUT",)):
        """Move named anchors to the boundary and retain every valid connection."""
        terminals = edge_terminals(inputs, outputs)
        if terminals == self.terminals:
            return True
        self.convert_pipes()
        by_name = {port["name"]: pos for pos, port in terminals.items()}
        moves = {pos: by_name[port["name"]] for pos, port in self.terminals.items() if port["name"] in by_name}
        parts = {pos: part for pos, part in self.parts.items() if pos not in self.terminals}
        for pos in terminals:
            if pos not in parts:
                continue
            free = [(x, y) for y in range(HEIGHT) for x in range(1, WIDTH - 1)
                    if (x, y) not in parts and (x, y) not in terminals]
            if not free:
                return False
            destination = min(free, key=lambda p: (abs(p[0] - pos[0]) + abs(p[1] - pos[1]), p[1], p[0]))
            parts[destination] = parts.pop(pos)
            moves[pos] = destination
        removed = set(self.terminals) - set(moves)
        traces = []
        for trace in self.traces:
            source, target = tuple(trace["source"]), tuple(trace["target"])
            if source in removed or target in removed:
                continue
            traces.append({**deepcopy(trace), "source": list(moves.get(source, source)),
                           "target": list(moves.get(target, target))})
        self.terminals = terminals
        self.parts = {**parts, **{pos: Part("OUTPUT" if port["output"] else "INPUT") for pos, port in terminals.items()}}
        self.switches = {name: self.switches.get(name, False) for name in inputs}
        self.traces = traces
        self.reset()
        return True

    def convert_pipes(self):
        """Preserve legacy pipe paths as explicit traces, including fan-out."""
        conductors = {pos for pos, part in self.parts.items() if part.kind in CONDUCTORS}
        if self.trace_mode and not conductors:
            return
        for target, part in list(self.parts.items()):
            if target in conductors:
                continue
            for pin, direction in enumerate(part.ports()[0]):
                if any(tuple(t["target"]) == target and t["pin"] == pin for t in self.traces):
                    continue
                dx, dy = VECTORS[direction]
                neighbor = (target[0] + dx, target[1] + dy)
                incoming = (direction + 2) % 4
                queue = deque([(neighbor, incoming, [])])
                seen = set()
                while queue:
                    pos, entry, path = queue.popleft()
                    if pos in seen:
                        continue
                    seen.add(pos)
                    candidate = self.parts.get(pos)
                    if candidate is None:
                        continue
                    if pos not in conductors:
                        if entry in candidate.ports()[1]:
                            self.traces.append({"source": list(pos), "target": list(target), "pin": pin,
                                                "points": [[x + .5, y + .5] for x, y in reversed(path)]})
                        continue
                    if entry not in candidate.ports()[0]:
                        continue
                    for side in candidate.ports()[0]:
                        sx, sy = VECTORS[side]
                        queue.append(((pos[0] + sx, pos[1] + sy), (side + 2) % 4, path + [pos]))
        self.parts = {pos: part for pos, part in self.parts.items() if pos not in conductors}
        self.trace_mode = True
        self.reset()

    def evaluate(self, a, b, c=0):
        """Evaluate one request in isolation; preserve every live nested state."""
        state = deepcopy(self.__dict__)
        try:
            self.switches = {name: 0 for name in self.switches}
            self.switches.update({"A": int(a), "B": int(b)})
            if "C" in self.switches:
                self.switches["C"] = int(c)
            self.reset()
            recent = deque(maxlen=8)
            for _ in range(self.settle_budget()):
                self.tick()
                recent.append(self.output_value())
            return self.output_value(), not self.has_sequential() and len(set(recent)) == 1
        finally:
            self.__dict__.update(state)

    def has_sequential(self):
        """Truth tables cannot certify machines whose result depends on time."""
        return any(part.kind in SEQUENTIAL for part in self.parts.values()) or any(
            child.has_sequential() for child in self.devices.values())

    def sequence_test_results(self, frames):
        """Check timed input frames from reset without changing the live machine.

        Each frame supplies inputs, a positive tick duration, and expected OUT.
        Inputs omitted from a frame retain their last value. Signals still have
        their normal one-tick-per-component delay, including input/output ports.
        """
        saved = deepcopy(self.__dict__)
        results = []
        try:
            self.switches = dict.fromkeys(self.switches, 0)
            self.reset()
            for frame in frames:
                ticks, expected = frame["ticks"], frame["expected"]
                inputs = frame.get("inputs", {})
                if (type(ticks) is not int or ticks <= 0 or
                        type(expected) is not int or not 0 <= expected <= 65535 or
                        any(name not in self.switches or type(value) not in (bool, int)
                            or not 0 <= value <= 65535 for name, value in inputs.items())):
                    raise ValueError("Invalid timed test frame")
                self.switches.update(inputs)
                for _ in range(ticks):
                    self.tick()
                results.append(SequenceCase(dict(self.switches), ticks, expected,
                                            self.output_value(), self.tick_count))
            return results
        finally:
            self.__dict__.update(saved)

    def runtime_snapshot(self):
        """JSON-safe live state, separate from reusable schematic snapshots."""
        key = lambda pos: f"{pos[0]},{pos[1]}"
        return {"version": 1, "layout": self.snapshot(), "tick_count": self.tick_count,
                "switches": dict(self.switches), "history_origin": self.history_origin,
                "active": {key(pos): value for pos, value in self.active.items()},
                "histories": {key(pos): list(values) for pos, values in self.histories.items()},
                "edge_high": {key(pos): value for pos, value in self.edge_high.items()},
                "devices": {key(pos): child.runtime_snapshot() for pos, child in self.devices.items()}}

    def restore_runtime(self, state):
        """Restore exact continuation atomically; reject corrupt/mismatched state.

        Call after loading the schematic. Older saves can omit runtime entirely
        and simply retain the freshly reset circuit.
        """
        candidate = Circuit.from_snapshot(self.snapshot())
        try:
            candidate._restore_runtime(state)
        except (KeyError, TypeError, ValueError, AttributeError) as error:
            raise ValueError("Invalid circuit runtime state") from error
        self.__dict__.update(candidate.__dict__)

    def _restore_runtime(self, state):
        def integer(value, minimum=0, maximum=None):
            if type(value) not in (bool, int) or value < minimum or (maximum is not None and value > maximum):
                raise ValueError("Invalid runtime number")
            return int(value)

        def positions(mapping, expected):
            names = {f"{pos[0]},{pos[1]}": pos for pos in expected}
            if not isinstance(mapping, dict) or set(mapping) != set(names):
                raise ValueError("Runtime positions do not match the layout")
            return {names[name]: value for name, value in mapping.items()}

        if state["version"] != 1 or state["layout"] != self.snapshot():
            raise ValueError("Runtime layout does not match the circuit")
        tick = integer(state["tick_count"])
        origin = integer(state["history_origin"], maximum=tick)
        expected_length = min(tick + 1, self.max_route_distance + 1) if self.histories else tick + 1
        if tick - origin + 1 != expected_length:
            raise ValueError("Runtime history length is invalid")
        if set(state["switches"]) != set(self.switches):
            raise ValueError("Runtime input ports do not match")
        self.switches = {name: integer(value, maximum=65535) for name, value in state["switches"].items()}
        self.active = {pos: integer(value, maximum=65535)
                       for pos, value in positions(state["active"], self.active).items()}
        histories = positions(state["histories"], self.histories)
        for pos, history in histories.items():
            if not isinstance(history, list) or len(history) != expected_length:
                raise ValueError("Runtime history length is invalid")
            self.histories[pos] = [integer(value, maximum=65535) for value in history]
        self.edge_high = {pos: bool(integer(value, maximum=1))
                          for pos, value in positions(state["edge_high"], self.edge_high).items()}
        for pos, child_state in positions(state["devices"], self.devices).items():
            self.devices[pos]._restore_runtime(child_state)
            if self.devices[pos].tick_count != tick:
                raise ValueError("Nested runtime clocks must advance together")
        self.tick_count, self.history_origin = tick, origin

    def snapshot(self) -> list[dict]:
        rows = [
            {"x": x, "y": y, "kind": part.kind, "rotation": part.rotation,
             **({"device": deepcopy(part.device)} if part.kind == "DEVICE" else {})}
            for (x, y), part in sorted(self.parts.items())
            if (x, y) not in self.terminals
        ]
        if self.terminals != DEFAULT_TERMINALS:
            rows.extend({"kind": "PORT", "x": x, "y": y, **port} for (x, y), port in sorted(self.terminals.items()))
        rows.extend({"kind": "TRACE", **deepcopy(trace)} for trace in self.traces)
        if self.trace_mode:
            rows.append({"kind": "WIRING", "mode": "traces"})
        return rows

    @classmethod
    def from_snapshot(cls, rows: Iterable[dict]) -> "Circuit":
        rows = list(rows)
        port_rows = [row for row in rows if row.get("kind") == "PORT"]
        terminals = None
        if port_rows:
            terminals = {}
            for row in port_rows:
                pos = (int(row["x"]), int(row["y"]))
                if not cls.in_bounds(pos) or not isinstance(row.get("name"), str):
                    raise ValueError("Invalid terminal")
                terminals[pos] = {"name": row["name"], "output": bool(row.get("output"))}
        fixed = terminals if terminals is not None else FIXED
        parts = {}
        for row in rows:
            try:
                pos = (int(row["x"]), int(row["y"]))
                kind = str(row["kind"])
                rotation = int(row["rotation"]) % 4
            except (KeyError, TypeError, ValueError):
                continue
            if cls.in_bounds(pos) and pos not in fixed and kind in ALL_PARTS:
                definition = row.get("device") if kind == "DEVICE" else None
                if kind == "DEVICE":
                    validate_device(definition)
                parts[pos] = Part(kind, rotation, deepcopy(definition))
        circuit = cls(parts, terminals=terminals)
        circuit.trace_mode = any(row.get("kind") in ("TRACE", "WIRING") for row in rows)
        for row in rows:
            if row.get("kind") != "TRACE":
                continue
            try:
                source, target, pin = tuple(row["source"]), tuple(row["target"]), int(row["pin"])
                points = row.get("points", [])
                if (source not in circuit.parts or target not in circuit.parts or source == target
                        or not circuit.parts[source].ports()[1]
                        or not 0 <= pin < len(circuit.parts[target].ports()[0])
                        or any(len(point) != 2 or any(not isinstance(v, (int, float)) for v in point) for point in points)):
                    raise ValueError("Invalid trace")
                circuit.traces.append({"source": list(source), "target": list(target), "pin": pin, "points": deepcopy(points)})
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError("Invalid trace") from error
        circuit._index_traces()
        return circuit

    def commission_test_results(self, logic: str) -> list[CommissionCase]:
        """Run a supported truth table and restore the live machine state."""
        rows = truth_rows(logic)
        saved_state = deepcopy(self.__dict__)
        results = []
        try:
            for row, expected in rows:
                a, b = row[:2]
                input_names = {port["name"] for port in self.terminals.values() if not port["output"]}
                available = all(name in input_names for name in ("A", "B", "C")[:len(row)])
                self.switches = {name: False for name in self.switches}
                self.switches.update(dict(zip(("A", "B", "C"), row)))
                self.reset()
                history = []
                # Longer nested signal paths need more settling time.
                for _ in range(self.settle_budget()):
                    self.tick()
                    history.append(self.lamp_on())
                results.append(CommissionCase(a, b, expected, history[-1], available and not self.has_sequential() and len(set(history[-8:])) == 1, tuple(row)))
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
