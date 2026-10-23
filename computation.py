"""Validated calculation orders paid by real village businesses."""
from dataclasses import dataclass
from copy import deepcopy
from circuit import Circuit
from inventions import locked_blocks


@dataclass(frozen=True)
class ComputeJob:
    key: str
    title: str
    owner: str
    customer: str
    operation: str
    inputs: tuple[str, str]
    output: str
    reward: int
    fee: int
    description: str

    def expected(self, a, b):
        return {"ADD": lambda: a + b, "MUL": lambda: a * b,
                "GT": lambda: int(a > b)}[self.operation]()


JOBS = {
    "fuel_quote": ComputeJob("fuel_quote", "Fuel order calculator", "Mely", "fuel_yard", "MUL",
                             ("Fuel units", "Price per unit"), "Invoice total", 12, 8,
                             "Multiply fuel units by price to quote a delivery."),
    "repair_quote": ComputeJob("repair_quote", "Repair estimate calculator", "Luca", "parts_shop", "ADD",
                               ("Parts cost", "Labor cost"), "Repair estimate", 12, 8,
                               "Add parts and labor to prepare repair estimates."),
    "stock_check": ComputeJob("stock_check", "Parts stock comparison", "Luca", "parts_shop", "GT",
                              ("Parts on hand", "Reserve target"), "Above reserve", 10, 7,
                              "Return 1 only when stock exceeds the reserve target."),
}
CASES = ((0, 0), (0, 1), (1, 0), (5, 7), (7, 5), (15, 15), (255, 1), (255, 255))
DAILY_CAPACITY = 2


def trade(village, seller, buyer, good, units, coins):
    village._record_trade(seller, buyer, good, units, coins)
    if village.trade_history and village.trade_history[-1]["day"] == village.day:
        village.trade_history[-1]["entries"].append(deepcopy(village.daily_trades[-1]))


def check(circuit, key):
    job = JOBS[key]
    results = []
    for a, b in CASES:
        actual, stable = circuit.evaluate(a, b)
        expected = job.expected(a, b)
        results.append({"a": a, "b": b, "expected": expected, "actual": actual,
                        "stable": stable, "passed": stable and actual == expected})
    return results


def approve(village, key, circuit, ports):
    locked = locked_blocks(village, circuit.snapshot())
    if JOBS[key].operation not in village.arithmetic_unlocks:
        locked.add(JOBS[key].operation)
    if locked:
        return f"Invent {', '.join(sorted(locked))} in the binary prototype bench first.", []
    results = check(circuit, key)
    if not all(row["passed"] for row in results):
        return "Fix the failing cases before registering this calculator.", results
    job = JOBS[key]
    customer = village.businesses[job.customer]
    existing = village.compute_designs.get(key)
    if not existing and customer["cash"] < job.reward:
        return f"{job.owner} needs {job.reward}c to commission the design.", results
    if not existing:
        customer["cash"] -= job.reward
        village.coins += job.reward
        trade(village, "Your Workshop", customer["name"], "calculator design", 1, job.reward)
    village.compute_designs[key] = {"parts": deepcopy(circuit.snapshot()), "ports": ports.copy(),
                                    "revision": existing.get("revision", 0) + 1 if existing else 1}
    return (f"{job.owner} registered your calculator. " +
            (f"Paid {job.reward}c. Daily orders are ready." if not existing else "Updated the service design; no repeat setup payment.")), results


def request_inputs(village, key):
    completed = next((entry for entry in reversed(village.compute_orders)
                      if entry["day"] == village.day and entry["job"] == key), None)
    if completed:
        return completed["a"], completed["b"]
    job = JOBS[key]
    if key == "fuel_quote":
        return min(255, village.businesses[job.customer]["stock"].get("fuel", 0)), 2 + village.day % 3
    if key == "repair_quote":
        return min(255, village.businesses[job.customer]["stock"].get("parts", 0) * 2), 3 + village.day % 6
    return min(255, village.businesses[job.customer]["stock"].get("parts", 0)), 2 + village.day % 4


def run_order(village, key):
    if key not in village.compute_designs:
        return "Register a tested calculator first."
    locked = locked_blocks(village, village.compute_designs[key]["parts"])
    if JOBS[key].operation not in village.arithmetic_unlocks:
        locked.add(JOBS[key].operation)
    if locked:
        return f"Invent {', '.join(sorted(locked))} before running this calculator."
    today = [entry for entry in village.compute_orders if entry["day"] == village.day]
    if any(entry["job"] == key for entry in today):
        return "This customer's order is already completed today."
    if len(today) >= DAILY_CAPACITY:
        return "Both workshop calculation slots are used. Advance a day for more."
    job = JOBS[key]
    customer, fuel = village.businesses[job.customer], village.businesses["fuel_yard"]
    # The fuel purchase is a real 2c transfer; maintenance consumes 1c.
    if fuel["stock"].get("fuel", 0) < 1:
        return "Mely has no fuel available. Advance a day for a delivery."
    if village.coins < 3:
        return "Need 3c up front: 2c for fuel and 1c maintenance."
    if customer["cash"] < job.fee:
        return f"{job.owner} cannot afford the {job.fee}c order today."
    a, b = request_inputs(village, key)
    circuit = Circuit.from_snapshot(village.compute_designs[key]["parts"])
    actual, stable = circuit.evaluate(a, b)
    if not stable or actual != job.expected(a, b):
        return "The registered calculator failed this order. Rebuild and register a working version."
    fuel["stock"]["fuel"] -= 1
    fuel["cash"] += 2
    customer["cash"] -= job.fee
    village.coins += job.fee - 3
    village.compute_earned += job.fee - 3
    trade(village, fuel["name"], "Your Workshop", "fuel", 1, 2)
    trade(village, "Workshop maintenance", "Your Workshop", "maintenance", 1, 1)
    trade(village, "Your Workshop", customer["name"], "calculation", 1, job.fee)
    customer["compute_day"] = village.day
    village.compute_orders.append({"day": village.day, "job": key, "a": a, "b": b, "result": actual,
                                   "fee": job.fee, "cost": 3, "net": job.fee - 3,
                                   "revision": village.compute_designs[key].get("revision", 1)})
    village.compute_orders[:] = village.compute_orders[-120:]
    message = f"{job.owner}: {a} {job.operation} {b} = {actual}. Earned {job.fee - 3}c net; +1 capacity for the next production run."
    village.journal.insert(0, message)
    return message
