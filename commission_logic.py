"""Truth-table specifications shared by authored jobs and the workshop tester."""
from itertools import product


# Each predicate accepts a tuple in A, B, C order. Descriptions specify behavior,
# rather than prescribing the gates a player must use.
COMMISSION_LOGIC = {
    "AND": (2, lambda r: all(r), "Activate only when both inputs are active."),
    "OR": (2, lambda r: any(r), "Activate when either or both inputs are active."),
    "NAND": (2, lambda r: not all(r), "Activate except when both inputs are active."),
    "NOR": (2, lambda r: not any(r), "Activate only when neither input is active."),
    "AND_NOT": (2, lambda r: r[0] and not r[1], "Activate when A is active and B is inactive."),
    "MAJORITY": (3, lambda r: sum(r) >= 2, "Activate when at least two of the three inputs are active."),
    "XOR": (2, lambda r: r[0] != r[1], "Activate when exactly one of A and B is active."),
    "XNOR": (2, lambda r: r[0] == r[1], "Activate when A and B agree: both active or both inactive."),
    "IMPLIES": (2, lambda r: not r[0] or r[1], "Activate unless A is active while B is inactive."),
    "ALL_THREE": (3, lambda r: all(r), "Activate only when all three inputs are active."),
    "ANY_THREE": (3, lambda r: any(r), "Activate when at least one of the three inputs is active."),
    "MUX": (3, lambda r: r[1] if r[2] else r[0], "Copy A when C is inactive; copy B when C is active."),
    "ODD_PARITY": (3, lambda r: sum(r) % 2 == 1, "Activate when one or three inputs are active."),
    "EXACTLY_ONE": (3, lambda r: sum(r) == 1, "Activate when exactly one of the three inputs is active."),
    "EXACTLY_TWO": (3, lambda r: sum(r) == 2, "Activate when exactly two of the three inputs are active."),
    "UNANIMOUS": (3, lambda r: len(set(r)) == 1, "Activate when all three inputs agree, including all inactive."),
    "INHIBITED_OR": (3, lambda r: (r[0] or r[1]) and not r[2], "Activate when A or B requests service, provided C is inactive."),
    "PRIORITY": (3, lambda r: r[0] or (r[1] and not r[2]), "A always activates the output. Otherwise activate only when B is active and C is inactive."),
}


def logic_arity(logic):
    return COMMISSION_LOGIC[logic][0]


def logic_description(logic):
    return COMMISSION_LOGIC[logic][2]


def truth_rows(logic):
    try:
        arity, predicate, _ = COMMISSION_LOGIC[logic]
    except KeyError as error:
        raise ValueError(f"Unsupported commission logic: {logic}") from error
    return [(row, bool(predicate(row))) for row in product((False, True), repeat=arity)]
