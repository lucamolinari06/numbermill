"""Authored timing exercises for the shared workshop floor.

Unlike a truth table, these checks retain memory between input changes. Each
check uses an isolated copy so testing cannot advance the player's machine.
"""

from dataclasses import dataclass, field
from circuit import Circuit


@dataclass(frozen=True)
class TimingChallenge:
    key: str
    title: str
    customer: str
    description: tuple[str, ...]
    port_names: dict[str, str]
    required_kind: str


CHALLENGES = {
    "memory": TimingChallenge(
        "memory", "Remember a fuel batch", "Mely",
        ("A is the requested fuel quantity; B is the capture signal.",
         "Start with OUT at zero. When B changes from low to high,",
         "remember A at OUT, including quantities up to 65535.",
         "Keep that quantity when A changes or B stays high.",
         "A later rising capture signal replaces the remembered quantity.",
         "Tests allow signal travel, then check that OUT stays steady."),
        {"A": "Fuel quantity", "B": "Capture", "OUT": "Remembered quantity"}, "REGISTER"),
    "counter": TimingChallenge(
        "counter", "Count repair deliveries", "Luca",
        ("A is the delivery signal; B clears the count.",
         "Start with OUT at zero. Count each low-to-high change of A.",
         "Holding A high must count only once; falling A adds nothing.",
         "While B is high, OUT must be zero, even when A rises.",
         "Releasing B with A still high must not invent a delivery.",
         "Tests allow signal travel, then check that OUT stays steady."),
        {"A": "Delivery pulse", "B": "Clear count", "OUT": "Delivery count"}, "COUNTER"),
    "clock": TimingChallenge(
        "clock", "A steady workshop beat", "Grace",
        ("Create a repeating timing signal at OUT without manual pulses.",
         "After startup, OUT must alternate two ticks low, two ticks high.",
         "A and B are unused; changing them must not change the beat.",
         "Tests accept any starting phase and allow signal travel.",
         "The full pattern is checked across several cycles.",
         "Use Pause and Step to inspect individual simulation ticks."),
        {"A": "Unused A", "B": "Unused B", "OUT": "Timing signal"}, "CLOCK"),
}


@dataclass(frozen=True)
class TimingCase:
    label: str
    expected: int | str
    actual: int | str
    passed: bool
    inputs: dict[str, int] = field(default_factory=dict)
    ticks: int = 0


def _kinds(circuit):
    kinds = set()
    pending = list(circuit.snapshot())
    while pending:
        row = pending.pop()
        kinds.add(row.get("kind"))
        if row.get("kind") == "DEVICE":
            pending.extend(row["device"]["parts"])
    return kinds


def _validation(circuit, challenge):
    inputs = {port["name"] for port in circuit.terminals.values() if not port["output"]}
    outputs = {port["name"] for port in circuit.terminals.values() if port["output"]}
    if not {"A", "B"}.issubset(inputs) or "OUT" not in outputs:
        return TimingCase("Workshop terminals", "A, B and OUT", "Missing terminal", False)
    if challenge.required_kind not in _kinds(circuit):
        return TimingCase("Timing component", challenge.required_kind, "Missing component", False)
    return None


def _steady_frames(key):
    if key == "memory":
        return (
            ("Starts empty", 0, 0, 0),
            ("Data alone does not capture", 37, 0, 0),
            ("First rising capture", 37, 1, 37),
            ("Hold while capture stays high", 91, 1, 37),
            ("Falling capture keeps memory", 91, 0, 37),
            ("Second rising capture", 91, 1, 91),
            ("Prepare largest quantity", 65535, 0, 91),
            ("Capture all sixteen bits", 65535, 1, 65535),
            ("Zero data still holds memory", 0, 1, 65535),
            ("Prepare zero quantity", 0, 0, 65535),
            ("Capture zero quantity", 0, 1, 0),
            ("Prepare next quantity", 256, 0, 0),
            ("Any nonzero capture is high", 256, 7, 256),
            ("High-to-high is not a new edge", 511, 1, 256),
        )
    return (
        ("Starts at zero", 0, 0, 0),
        ("First delivery", 1, 0, 1),
        ("Held signal counts once", 1, 0, 1),
        ("Falling signal adds nothing", 0, 0, 1),
        ("Second delivery", 1, 0, 2),
        ("Clear while delivery is high", 1, 1, 0),
        ("Release clear, no phantom delivery", 1, 0, 0),
        ("Ready for another delivery", 0, 0, 0),
        ("Any nonzero delivery is high", 7, 0, 1),
        ("High-to-high adds nothing", 1, 0, 1),
        ("Clear with delivery low", 0, 1, 0),
        ("Clear wins over rising delivery", 1, 1, 0),
        ("Leave clear safely", 0, 0, 0),
        ("Counting resumes", 1, 0, 1),
    )


def run_tests(circuit: Circuit, key: str) -> list[TimingCase]:
    """Test a schematic from reset, preserving every live state and switch.

    Input phases last one full settle_budget plus an eight-tick observation
    window. This allows pipe routes and nested devices to propagate changes
    without dictating a particular layout. All eight observations must match;
    passing at a single coincidental tick is insufficient.
    """
    challenge = CHALLENGES[key]
    invalid = _validation(circuit, challenge)
    if invalid:
        return [invalid]
    test = Circuit.from_snapshot(circuit.snapshot())
    test.switches = {name: 0 for name in test.switches}
    test.reset()
    travel = test.settle_budget()
    results = []
    if key == "clock":
        # Pin phase after the first observation. Subsequent input changes must
        # preserve that same phase, not merely restart a valid-looking cycle.
        phase = None
        elapsed = 0
        for label, a, b in (("Free-running beat", 0, 0), ("A does not change the beat", 1, 0),
                            ("B does not change the beat", 0, 1), ("Both inputs high", 1, 1)):
            test.switches.update(A=a, B=b)
            for _ in range(travel):
                test.tick()
            elapsed += travel
            observed = []
            for _ in range(16):
                test.tick()
                observed.append(test.output_value("OUT"))
            if phase is None:
                phase = next((offset for offset in range(4)
                              if observed == [((elapsed + i + offset) // 2) % 2 for i in range(16)]), -1)
            expected = [((elapsed + i + phase) // 2) % 2 for i in range(16)] if phase >= 0 else [0, 0, 1, 1] * 4
            results.append(TimingCase(label, "".join(map(str, expected)),
                                      ",".join(map(str, observed)) if any(v not in (0, 1) for v in observed)
                                      else "".join(map(str, observed)),
                                      phase >= 0 and observed == expected, {"A": a, "B": b}, travel + 16))
            elapsed += 16
        return results
    for label, a, b, expected in _steady_frames(key):
        test.switches.update(A=a, B=b)
        for _ in range(travel):
            test.tick()
        observed = []
        for _ in range(8):
            test.tick()
            observed.append(test.output_value("OUT"))
        steady = len(set(observed)) == 1
        actual = observed[-1] if steady else "Changing: " + ",".join(map(str, observed))
        results.append(TimingCase(label, expected, actual, steady and observed[-1] == expected,
                                  {"A": a, "B": b}, travel + 8))
    return results
