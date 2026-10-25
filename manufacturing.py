"""Player-owned manufacturing with real inputs, customers, and live controllers.

The daily-life clock calls update; the editor never advances an installed PLC.
Only JSON state lives in Village. A weak runtime cache avoids rebuilding a
controller on every simulation step while preserving exact saved continuation.
"""
from copy import deepcopy
import math
import weakref

from circuit import Circuit, standard_device_ports

GRID_W, GRID_H = 9, 6
STEP_SECONDS = .5
BATCH_SECONDS = 12.0
TRADE_SECONDS = 2.0
PRODUCTION = ("bench", "press", "lathe", "precision_machine")
CONTROLLABLE = (*PRODUCTION, "buyer", "seller")
KIT_PRICE = 10
MAINTENANCE_DAYS = 6
SUPPLIES = {
    "metal": {"seller": "foundry", "price": 2, "name": "Metal"},
    "fittings": {"seller": "toolmaker", "price": 3, "name": "Fittings"},
    "fuel": {"seller": "fuel_yard", "price": 3, "name": "Fuel"},
}
RECIPE = {"metal": 1, "fittings": 1, "fuel": 1}
CATALOG = {
    "bench": {"name": "Assembly bench", "price": 24, "seller": "toolmaker", "fittings": 2},
    "storage": {"name": "Storage rack", "price": 6, "seller": "toolmaker", "fittings": 1},
    "controller": {"name": "Controller cabinet", "price": 6, "seller": "toolmaker", "fittings": 1},
    "display": {"name": "Production display", "price": 4, "seller": "toolmaker", "fittings": 1},
    "buyer": {"name": "Procurement unit", "price": 8, "seller": "toolmaker", "fittings": 1},
    "seller": {"name": "Dispatch unit", "price": 8, "seller": "toolmaker", "fittings": 1},
}
PRODUCTS = {
    "repair_kits": {"name": "Repair kits", "machine": "bench", "recipe": RECIPE, "seconds": 12.0, "price": 10},
    "metal_plates": {"name": "Metal plates", "machine": "press", "recipe": {"metal": 2, "fuel": 1}, "seconds": 9.0, "price": 11},
    "steam_valves": {"name": "Steam valves", "machine": "lathe", "recipe": {"metal": 1, "fittings": 2, "fuel": 1}, "seconds": 15.0, "price": 16},
    "precision_gears": {"name": "Precision gears", "machine": "precision_machine", "recipe": {"metal_plates": 1, "steam_valves": 1, "fuel": 1}, "seconds": 10.0, "price": 36},
}
CATALOG.update({
    "press": {"name": "Metal press", "price": 18, "seller": "toolmaker", "fittings": 2},
    "lathe": {"name": "Valve lathe", "price": 28, "seller": "toolmaker", "fittings": 2},
    "precision_machine": {"name": "Precision gear cutter", "price": 44, "seller": "toolmaker", "fittings": 3, "unlock": "precision_machine"},
})
EXPORT_NAMES = {"metal_plates": "Bridgewright shipment", "steam_valves": "Canal pump shipment", "precision_gears": "Survey instrument shipment"}
SENSOR_NAMES = {
    "ready": "Ready to produce", "stock": "Unit product stock", "target": "Stock target",
    "completed": "Unit total", "pulse": "Completion pulse", "busy": "Unit busy",
    "materials": "Complete input sets", "fuel": "Stored fuel", "cash": "Workshop coins",
    "metal": "Stored metal", "fittings": "Stored fittings", "free_space": "Free output spaces",
    "selectedstock": "Selected supply stock", "supplierstock": "Supplier stock",
    "price": "Trading price", "demand": "Available customers", "reserve": "Cash reserve",
}
STORAGE_SENSORS = ("metal", "fittings", "fuel", "stock", "materials", "free_space")
DISPLAY_SOURCES = {"stock": "Finished kits", "cash": "Coins", "metal": "Metal", "fittings": "Fittings",
                   "fuel": "Fuel", "produced": "Produced", "sold": "Sold", "signal": "Controller OUT"}
SENSOR_NAMES.update({key: value["name"] for key, value in PRODUCTS.items()})
STORAGE_SENSORS += tuple(PRODUCTS)
DISPLAY_SOURCES.update({key: value["name"] for key, value in PRODUCTS.items()})
BUYERS = ("sawmill", "foundry", "toolmaker")
_RUNTIME_CACHE = {}


def state(village):
    if not isinstance(getattr(village, "manufacturing", None), dict):
        village.manufacturing = {}
    current = village.manufacturing
    defaults = {"equipment": [], "goods": {"repair_kits": 0}, "target": 6,
                "produced": 0, "auto_produced": 0, "sold": 0, "earned": 0,
                "spent": 0, "unlocks": [], "exports": {}, "accumulator": 0.0, "maintenance": {},
                "starter_bench_bought": False, "next_id": 1, "events": [],
                "controller_drafts": {}, "resale_stock": {}, "equipment_resale_earned": 0,
                "road_crew": {"stock": 0, "order_day": 0, "used": 0, "last_day": village.day}}
    for name, value in defaults.items():
        current.setdefault(name, deepcopy(value))
    for product in PRODUCTS:
        current["goods"].setdefault(product, 0)
    # Migration never invents a generous refund for old equipment receipts.
    current["next_id"] = max(current["next_id"], max((item["id"] for item in current["equipment"]), default=0) + 1)
    for item in current["equipment"]:
        item.setdefault("purchase_price", 4 if item["kind"] == "bench" else CATALOG[item["kind"]]["price"])
        item.setdefault("salvage_fittings", 0)  # Unknown old fittings stay inside returned equipment.
        if item["kind"] in CONTROLLABLE:
            item.setdefault("config", _trader_defaults(item["kind"]))
            for key, value in _trader_defaults(item["kind"]).items():
                item["config"].setdefault(key, value)
            item.setdefault("trade_day", village.day)
            item.setdefault("daily_spent", 0)
            item.setdefault("transactions", 0)
            item.setdefault("trade_wait", 0.0)
            if item.get("controller"):
                item["controller"].setdefault("sources", {"A": None, "B": None})
        if item["kind"] == "display":
            item.setdefault("display", {"source": "stock", "machine_id": None})
    return current


def _trader_defaults(kind):
    if kind == "buyer":
        return {"good": "metal", "target": 2, "reserve": 8, "daily_budget": 24, "max_price": 3}
    if kind == "seller":
        return {"buyer": "any", "product": "repair_kits", "keep_stock": 0, "min_price": 10}
    return {}


def unlock_equipment(village, key):
    if key != "precision_machine":
        return False, "Unknown blueprint."
    unlocks = state(village)["unlocks"]
    if key not in unlocks:
        unlocks.append(key)
        _event(village, "Recovered the precision gear cutter blueprint.")
    return True, "Precision gear cutter available at Tess's Toolworks."


def equipment_unlocked(village, kind):
    unlock = CATALOG[kind].get("unlock")
    return unlock is None or unlock in state(village)["unlocks"]


def product_for(machine):
    return next((key for key, data in PRODUCTS.items() if data["machine"] == machine["kind"]), machine.get("config", {}).get("product", "repair_kits"))


def production_seconds(village, product):
    """Recovered accumulator improves future batches; materials remain real costs."""
    return PRODUCTS[product]['seconds'] * (.8 if 'steam_accumulator' in state(village)['unlocks'] else 1.)


def ingredient_stock(village, good):
    return state(village)["goods"].get(good, 0) if good in PRODUCTS else village.material_inventory.get(good, 0)


def recipe_for(machine):
    return PRODUCTS[product_for(machine)]["recipe"]


def total_stock(village):
    return sum(state(village)["goods"].values())


def get_machine(village, machine_id):
    return next((item for item in state(village)["equipment"] if item["id"] == machine_id), None)


def equipment_price(village, kind):
    if kind == "bench" and not state(village)["starter_bench_bought"]:
        return 4
    return CATALOG[kind]["price"]


def stock_capacity(village):
    return 6 + 6 * sum(item["kind"] == "storage" for item in state(village)["equipment"])


def _event(village, message):
    current = state(village)
    current["events"] = (current["events"] + [f"Day {village.day}: {message}"])[-12:]


def _valid_position(village, pos, excluding=None):
    return (isinstance(pos, (tuple, list)) and len(pos) == 2 and
            all(type(n) is int for n in pos) and 0 <= pos[0] < GRID_W and 0 <= pos[1] < GRID_H and
            not any(item["id"] != excluding and item["pos"] == list(pos) for item in state(village)["equipment"]))


def buy_equipment(village, kind, pos):
    if kind not in CATALOG or not _valid_position(village, pos):
        return False, "Choose an empty workshop floor tile."
    if not equipment_unlocked(village, kind):
        return False, "Recover the gear cutter blueprint beyond the village first."
    current, specification = state(village), CATALOG[kind]
    price = equipment_price(village, kind)
    seller = village.businesses.get(specification["seller"])
    if seller is None:
        return False, "Tess's Toolworks is unavailable."
    starter = kind == "bench" and not current["starter_bench_bought"]
    reused = current["resale_stock"].get(kind, [])
    fittings = 0 if starter or reused else specification["fittings"]
    if village.coins < price:
        return False, f"{specification['name']} costs {price}c."
    if seller["stock"].get("fittings", 0) < fittings:
        return False, f"Tess needs {fittings} fittings to assemble this equipment. Let the toolworks restock."
    village.coins -= price
    seller["cash"] += price
    seller["stock"]["fittings"] = seller["stock"].get("fittings", 0) - fittings
    current["spent"] += price
    returned = reused.pop(0) if reused and not starter else None
    machine = {"id": current["next_id"], "kind": kind, "pos": list(pos), "purchase_price": price,
               "salvage_fittings": returned.get("salvage_fittings", 0) if returned else fittings}
    current["next_id"] += 1
    if kind in CONTROLLABLE:
        machine.update(busy=0.0, mode="manual", produced=0, signal=0, pulse=0,
                       status="Ready", controller=None, batch_auto=False)
        machine.update(config=_trader_defaults(kind), trade_day=village.day, daily_spent=0, transactions=0, trade_wait=0.0)
        if kind == "bench":
            current["starter_bench_bought"] = True
    elif kind == "display":
        machine["display"] = {"source": "stock", "machine_id": None}
    elif kind == "controller":
        machine["machine_id"] = None
    current["equipment"].append(machine)
    village._record_trade(seller["name"], "Your Workshop", "refurbished assembly bench" if starter else specification["name"], 1, price)
    _event(village, f"Bought {specification['name']} for {price}c.")
    return True, f"Placed {specification['name']}. " + ("One metal, one fitting and one fuel make a repair kit." if kind == "bench" else "Equipment is ready.")


def move_equipment(village, machine_id, pos):
    item = get_machine(village, machine_id)
    if item is None or not _valid_position(village, pos, machine_id):
        return False, "Choose an empty workshop floor tile."
    item["pos"] = list(pos)
    return True, f"Moved {CATALOG[item['kind']]['name']}."


def buy_supply(village, good, count=1):
    if good not in SUPPLIES or type(count) is not int or count <= 0:
        return False, "Choose a positive supply quantity."
    listing = SUPPLIES[good]
    seller = village.businesses.get(listing["seller"])
    price = listing["price"] * count
    if seller is None or seller["stock"].get(good, 0) < count:
        return False, f"The supplier lacks {count} {good}. Let the village produce more."
    if village.coins < price:
        return False, f"Buying {count} {good} costs {price}c."
    village.coins -= price
    seller["cash"] += price
    seller["stock"][good] -= count
    village.material_inventory[good] = village.material_inventory.get(good, 0) + count
    state(village)["spent"] += price
    village._record_trade(seller["name"], "Your Workshop", good, count, price, purpose="Manufacturing supplies")
    return True, f"Bought {count} {good} for {price}c."


def _start_reason(village, machine):
    if machine is None or machine["kind"] not in PRODUCTION:
        return "Select a production machine."
    if machine["busy"] > 0:
        return "Working"
    current = state(village)
    reserved = sum(item.get("busy", 0) > 0 for item in current["equipment"])
    consumed_goods = sum(count for good, count in recipe_for(machine).items() if good in PRODUCTS)
    if sum(current["goods"].values()) - consumed_goods + reserved + 1 > stock_capacity(village):
        return "Output storage full"
    missing = [good for good, count in recipe_for(machine).items() if ingredient_stock(village, good) < count]
    return "Need " + ", ".join(good.replace("_", " ") for good in missing) if missing else ""


def _start(village, machine, automatic=False):
    reason = _start_reason(village, machine)
    if reason:
        if machine and machine["kind"] in PRODUCTION:
            machine["status"] = reason
        return False, reason
    for good, count in recipe_for(machine).items():
        inventory = state(village)["goods"] if good in PRODUCTS else village.material_inventory
        inventory[good] -= count
    machine.update(busy=production_seconds(village, product_for(machine)), status="Working", batch_auto=automatic)
    return True, "Batch started; inputs reserved."


def start_batch(village, machine_id):
    machine = get_machine(village, machine_id)
    if machine and machine.get("mode") == "auto":
        return False, "Switch to manual control before starting a batch by hand."
    return _start(village, machine)


def storage_values(village, storage_id):
    rack = get_machine(village, storage_id)
    if not rack or rack["kind"] != "storage":
        return {sensor: 0 for sensor in STORAGE_SENSORS}
    current = state(village)
    reserved = sum(item.get("busy", 0) > 0 for item in current["equipment"])
    return {"metal": village.material_inventory.get("metal", 0),
            "fittings": village.material_inventory.get("fittings", 0),
            "fuel": village.material_inventory.get("fuel", 0),
            "stock": current["goods"]["repair_kits"],
            "materials": min(village.material_inventory.get(g, 0) // n for g, n in RECIPE.items()),
            "free_space": max(0, stock_capacity(village) - sum(current["goods"].values()) - reserved),
            **{key: current["goods"].get(key, 0) for key in PRODUCTS}}


def sensor_values(village, machine_id):
    machine = get_machine(village, machine_id)
    if machine is None or machine["kind"] not in CONTROLLABLE:
        return {}
    current = state(village)
    config = machine["config"]
    good = config.get("good", "metal")
    listing = SUPPLIES[good]
    customer_offers = _eligible_offers(village, machine) if machine["kind"] == "seller" else [offer for offer in offers(village) if offer.get("product", "repair_kits") == product_for(machine)]
    price = listing["price"] if machine["kind"] == "buyer" else PRODUCTS[product_for(machine)]["price"]
    reserved = sum(item.get("busy", 0) > 0 for item in current["equipment"])
    reason = _start_reason(village, machine) if machine["kind"] in PRODUCTION else _trade_reason(village, machine)
    return {"ready": int(not reason), "stock": current["goods"][product_for(machine)],
            "target": config.get("target", current["target"]), "completed": machine["produced"] & 65535,
            "pulse": machine.get("pulse", 0), "busy": int(machine["busy"] > 0),
            "materials": min(ingredient_stock(village, g) // n for g, n in recipe_for(machine).items()),
            "fuel": village.material_inventory.get("fuel", 0), "cash": village.coins,
            "metal": village.material_inventory.get("metal", 0), "fittings": village.material_inventory.get("fittings", 0),
            "free_space": max(0, stock_capacity(village) - sum(current["goods"].values()) - reserved),
            **{key: current["goods"].get(key, 0) for key in PRODUCTS},
            "selectedstock": village.material_inventory.get(good, 0),
            "supplierstock": village.businesses.get(listing["seller"], {}).get("stock", {}).get(good, 0),
            "price": price, "demand": sum(offer["demand"] for offer in customer_offers),
            "reserve": config.get("reserve", 0)}


def input_values(village, machine_id):
    machine = get_machine(village, machine_id)
    if not machine or not machine.get("controller"):
        return {}
    native = sensor_values(village, machine_id)
    result = {}
    for port, sensor in machine["controller"]["inputs"].items():
        source = machine["controller"].get("sources", {}).get(port)
        values = native if source is None else storage_values(village, source)
        result[port] = min(65535, max(0, int(values.get(sensor, 0))))
    return result


def set_input_source(village, machine_id, port, source_id=None, sensor="metal"):
    machine = get_machine(village, machine_id)
    source = get_machine(village, source_id) if source_id is not None else None
    if not machine or not machine.get("controller") or port not in ("A", "B") or sensor not in SENSOR_NAMES:
        return False, "Install a controller and choose a valid input."
    if source_id is not None and (not source or source["kind"] != "storage" or sensor not in STORAGE_SENSORS):
        return False, "Storage connections expose material stocks, finished kits and free spaces."
    machine["controller"]["sources"][port] = source_id
    machine["controller"]["inputs"][port] = sensor
    reset_controller(village, machine_id)
    return True, f"{port} connected to {'storage #' + str(source_id) if source else 'unit sensors'}: {SENSOR_NAMES[sensor]}."


def _cache(village):
    key = id(village)
    entry = _RUNTIME_CACHE.get(key)
    if entry is None or entry[0]() is not village:
        def expire(reference):
            if _RUNTIME_CACHE.get(key, (None,))[0] is reference:
                _RUNTIME_CACHE.pop(key, None)
        entry = (weakref.ref(village, expire), {})
        _RUNTIME_CACHE[key] = entry
    return entry[1]


def _live_circuit(village, machine):
    controller = machine["controller"]
    cached = _cache(village).get(machine["id"])
    if cached is None or cached[0] is not controller:
        circuit = Circuit.from_snapshot(controller["parts"])
        if controller.get("runtime"):
            circuit.restore_runtime(controller["runtime"])
        cached = (controller, circuit)
        _cache(village)[machine["id"]] = cached
    return cached[1]


def install_controller(village, machine_id, circuit, inputs=None, sources=None):
    machine = get_machine(village, machine_id)
    if machine is None or machine["kind"] not in CONTROLLABLE:
        return False, "Select a production or trading unit."
    if not isinstance(circuit, Circuit) or not standard_device_ports(circuit.snapshot()):
        return False, "Controllers need A and B inputs and one OUT output."
    mapping = inputs or (machine["controller"]["inputs"] if machine.get("controller") else {"A": "selectedstock" if machine["kind"] == "buyer" else "ready", "B": "target" if machine["kind"] == "buyer" else "stock"})
    if set(mapping) != {"A", "B"} or any(sensor not in SENSOR_NAMES for sensor in mapping.values()):
        return False, "Choose valid A and B sensor sources."
    source_map = dict(sources if sources is not None else machine.get("controller", {}).get("sources", {}) if machine.get("controller") else {})
    source_map = {"A": source_map.get("A"), "B": source_map.get("B")}
    for port, source_id in source_map.items():
        if source_id is not None:
            rack = get_machine(village, source_id)
            if not rack or rack["kind"] != "storage" or mapping[port] not in STORAGE_SENSORS:
                return False, "A storage input is disconnected or has an unavailable signal."
    cabinet = next((item for item in state(village)["equipment"] if item["kind"] == "controller" and item.get("machine_id") == machine_id), None)
    if cabinet is None:
        cabinet = next((item for item in state(village)["equipment"] if item["kind"] == "controller" and item.get("machine_id") is None), None)
    if cabinet is None:
        return False, "Buy and place a controller cabinet for this unit first."
    fresh = Circuit.from_snapshot(circuit.snapshot())
    cabinet["machine_id"] = machine_id
    machine["controller"] = {"parts": fresh.snapshot(), "runtime": fresh.runtime_snapshot(), "inputs": dict(mapping), "sources": source_map}
    machine.update(signal=0, status="Controller installed")
    _cache(village).pop(machine_id, None)
    return True, "Controller installed from reset. Enable Auto to let OUT request actions; safety limits remain active."


def set_sensor(village, machine_id, port, sensor):
    machine = get_machine(village, machine_id)
    if not machine or not machine.get("controller") or port not in ("A", "B") or sensor not in SENSOR_NAMES:
        return False, "Install a controller and select a valid sensor."
    if machine["controller"].get("sources", {}).get(port) is not None and sensor not in STORAGE_SENSORS:
        return False, "This storage connection does not expose that signal. Select a native source first."
    machine["controller"]["inputs"][port] = sensor
    reset_controller(village, machine_id)
    return True, f"{port} reads {SENSOR_NAMES[sensor]}. Controller reset after rewiring."


def reset_controller(village, machine_id):
    machine = get_machine(village, machine_id)
    if not machine or not machine.get("controller"):
        return False, "This unit has no controller."
    circuit = Circuit.from_snapshot(machine["controller"]["parts"])
    machine["controller"]["runtime"] = circuit.runtime_snapshot()
    machine["signal"] = 0
    _cache(village).pop(machine_id, None)
    return True, "Controller memory and clock reset. A running batch will still finish."


def set_mode(village, machine_id, auto):
    machine = get_machine(village, machine_id)
    if not machine or machine["kind"] not in CONTROLLABLE:
        return False, "Select a production or trading unit."
    if auto and not machine.get("controller"):
        return False, "Install a controller before enabling Auto."
    if auto:
        for source_id in machine["controller"].get("sources", {}).values():
            source = get_machine(village, source_id) if source_id is not None else None
            if source_id is not None and (not source or source["kind"] != "storage"):
                return False, "Reconnect the missing storage input before enabling Auto."
    machine["mode"] = "auto" if auto else "manual"
    return True, "Auto enabled: OUT permits this unit to act within configured limits." if auto else "Manual control. Any current batch will finish."


def set_target(village, value):
    if type(value) is not int or not 0 <= value <= 65535:
        return False, "Choose a stock target from 0 to 65535."
    state(village)["target"] = value
    return True, f"Stock-target sensor set to {value}. Your circuit decides how to use it."


def configure_trader(village, machine_id, **changes):
    machine = get_machine(village, machine_id)
    if not machine or machine["kind"] not in ("buyer", "seller"):
        return False, "Select a procurement or dispatch unit."
    defaults = _trader_defaults(machine["kind"])
    if not set(changes).issubset(defaults):
        return False, "Unknown trading setting."
    config = {**machine["config"], **changes}
    for name, value in config.items():
        if name == "good":
            valid = value in SUPPLIES
        elif name == "buyer":
            valid = value in ("any", *BUYERS, "road_crew", *("export_" + key for key in EXPORT_NAMES))
        elif name == "product":
            valid = value in PRODUCTS
        else:
            valid = type(value) is int and 0 <= value <= 65535
        if not valid:
            return False, "Choose a valid trading setting between 0 and 65535."
    machine["config"] = config
    # Reconfiguration cannot renew today's spending allowance.
    return True, "Trading settings saved. Targets are sensor values; your controller decides when to act."


def _roll_trader_day(village, machine):
    if machine["trade_day"] != village.day:
        machine["trade_day"] = village.day
        machine["daily_spent"] = 0


def _eligible_offers(village, machine):
    config = machine["config"]
    return [offer for offer in offers(village)
            if config["buyer"] in ("any", offer["id"]) and offer.get("product", "repair_kits") == config.get("product", "repair_kits") and offer["price"] >= config["min_price"]]


def _trade_reason(village, machine):
    _roll_trader_day(village, machine)
    config = machine["config"]
    if machine["kind"] == "buyer":
        listing = SUPPLIES[config["good"]]
        price = listing["price"]
        if price > config["max_price"]:
            return "Supplier price exceeds limit"
        if machine["daily_spent"] + price > config["daily_budget"]:
            return "Daily purchasing budget reached"
        if village.coins - price < config["reserve"]:
            return "Cash reserve protected"
        supplier = village.businesses.get(listing["seller"], {})
        if supplier.get("stock", {}).get(config["good"], 0) < 1:
            return "Supplier stock empty"
    else:
        if state(village)["goods"][config.get("product", "repair_kits")] <= config["keep_stock"]:
            return "Finished-stock reserve protected"
        if not any(offer["demand"] for offer in _eligible_offers(village, machine)):
            return "No funded customer at the minimum price"
    return ""


def _trade(village, machine):
    reason = _trade_reason(village, machine)
    if reason:
        machine["status"] = reason
        return False, reason
    if machine["kind"] == "buyer":
        good = machine["config"]["good"]
        result = buy_supply(village, good)
        if result[0]:
            machine["daily_spent"] += SUPPLIES[good]["price"]
    else:
        buyer = next(offer["id"] for offer in _eligible_offers(village, machine) if offer["demand"])
        result = sell_goods(village, buyer)
    if result[0]:
        machine["transactions"] += 1
        machine["produced"] += 1  # The generic completed sensor counts unit actions.
        machine["pulse"] = 1
        machine["status"] = "Purchase completed" if machine["kind"] == "buyer" else "Sale completed"
    return result


def trade_once(village, machine_id):
    machine = get_machine(village, machine_id)
    if not machine or machine["kind"] not in ("buyer", "seller"):
        return False, "Select a procurement or dispatch unit."
    if machine["mode"] != "manual":
        return False, "Switch to manual before ordering a transaction by hand."
    return _trade(village, machine)


def configure_display(village, display_id, source, machine_id=None):
    item = get_machine(village, display_id)
    if not item or item["kind"] != "display" or source not in DISPLAY_SOURCES:
        return False, "Choose a display and a valid reading."
    if source == "signal":
        target = get_machine(village, machine_id)
        if not target or target["kind"] not in CONTROLLABLE:
            return False, "Select a production or trading unit for this display."
    item["display"] = {"source": source, "machine_id": machine_id if source == "signal" else None}
    return True, f"Display now reads {DISPLAY_SOURCES[source]}."


def display_reading(village, display_id):
    item = get_machine(village, display_id)
    if not item or item["kind"] != "display":
        return {"label": "No display", "value": 0, "unit": "", "source": None, "machine_id": None}
    current = state(village)
    config = item["display"]
    source = config["source"]
    value = {"stock": current["goods"]["repair_kits"], "cash": village.coins,
             "produced": current["produced"], "sold": current["sold"],
             **{good: village.material_inventory.get(good, 0) for good in SUPPLIES},
             **current["goods"]}.get(source, 0)
    if source == "signal":
        target = get_machine(village, config["machine_id"])
        value = target.get("signal", 0) if target else 0
    return {"label": DISPLAY_SOURCES[source], "value": int(value),
            "unit": "c" if source == "cash" else "", **config}


def equipment_sell_quote(village, machine_id):
    item = get_machine(village, machine_id)
    if not item:
        return {"price": 0, "allowed": False, "reason": "Equipment no longer exists.", "name": "Equipment"}
    specification = CATALOG[item["kind"]]
    price = max(0, min(item["purchase_price"], specification["price"]) // 2)
    reason = ""
    if item.get("busy", 0) > 0:
        reason = "Let the running batch finish before selling this unit."
    elif item["kind"] == "storage":
        current = state(village)
        reserved = sum(machine.get("busy", 0) > 0 for machine in current["equipment"])
        if sum(current["goods"].values()) + reserved > stock_capacity(village) - 6:
            reason = "Sell finished goods or finish batches before reducing storage capacity."
    buyer = village.businesses.get(specification["seller"])
    if not reason and (not buyer or buyer["cash"] < price):
        reason = "Tess cannot afford this equipment today."
    return {"price": price, "allowed": not bool(reason), "reason": reason or "Tess buys the whole used unit; connected controller links are removed.",
            "name": specification["name"]}


def sell_equipment(village, machine_id):
    quote = equipment_sell_quote(village, machine_id)
    if not quote["allowed"]:
        return False, quote["reason"]
    current = state(village)
    item = get_machine(village, machine_id)
    buyer = village.businesses[CATALOG[item["kind"]]["seller"]]
    buyer["cash"] -= quote["price"]
    village.coins += quote["price"]
    current["equipment_resale_earned"] += quote["price"]
    # The fittings remain in the intact returned hardware. A future sale of
    # that hardware reuses it, and must not consume another fitting set.
    current["resale_stock"].setdefault(item["kind"], []).append({"salvage_fittings": item["salvage_fittings"]})
    if item["kind"] == "controller":
        target = get_machine(village, item.get("machine_id"))
        if target:
            target.update(controller=None, mode="manual", signal=0, status="Controller cabinet removed")
            _cache(village).pop(target["id"], None)
    for other in current["equipment"]:
        if item["kind"] == "storage" and other.get("controller") and machine_id in other["controller"].get("sources", {}).values():
            other.update(mode="manual", signal=0, status="Storage input disconnected; reconnect before Auto")
        if other["kind"] == "controller" and other.get("machine_id") == machine_id:
            other["machine_id"] = None
    current["equipment"] = [other for other in current["equipment"] if other["id"] != machine_id]
    current["controller_drafts"].pop(str(machine_id), None)
    current["controller_drafts"].pop(machine_id, None)
    _cache(village).pop(machine_id, None)
    village._record_trade("Your Workshop", buyer["name"], "used " + quote["name"], 1, quote["price"], purpose="Equipment resale")
    _event(village, f"Sold {quote['name']} to Tess for {quote['price']}c.")
    return True, f"Sold {quote['name']} for {quote['price']}c. Fittings remain inside Tess's returned equipment."


def _review_maintenance(village):
    current = state(village)
    produced = getattr(village, "daily_life", {}).get("produced", {})
    crew = current["road_crew"]
    if crew["last_day"] != village.day:
        # The external road crew uses yesterday's delivery on its machinery.
        # A missed day never creates accumulated orders or catch-up payments.
        crew["used"] += crew["stock"]
        crew["stock"] = 0
        crew["last_day"] = village.day
    for key, service in current["maintenance"].items():
        if service["last_day"] != village.day:
            if service.get("used_day") == service["last_day"]:
                service["remaining"] = max(0, service["remaining"] - 1)
            service["last_day"] = village.day
            service["baseline"] = 0
        if produced.get(key, 0) > service.get("baseline", 0) and service["remaining"] > 0:
            service["used_day"] = village.day


def capacity_bonus(village, business_id):
    current = getattr(village, "manufacturing", {})
    service = current.get("maintenance", {}).get(business_id, {})
    remaining = service.get("remaining", 0)
    if service.get("last_day") != village.day and service.get("used_day") == service.get("last_day"):
        remaining -= 1
    return 2 if remaining > 0 else 0


def offers(village):
    _review_maintenance(village)
    result = []
    current = state(village)
    for key in BUYERS:
        buyer = village.businesses.get(key)
        if not buyer:
            continue
        # These three shops are owner-operated and have no resident wage bill.
        # Keep three nominal days of raw-input costs (at least 12c), rather
        # than the general payroll reserve that would block every first sale.
        from economy import BUSINESS_TYPES
        recipe = BUSINESS_TYPES[buyer["kind"]]
        reserve = max(12, recipe["capacity"] * recipe["input_price"] * 3)
        service = current["maintenance"].get(key, {})
        remaining = service.get("remaining", 0)
        good = {"sawmill": "timber", "foundry": "metal", "toolmaker": "fittings"}[key]
        # Avoid servicing an idle shop sitting on a full shelf.
        stock_limit = {"sawmill": 12, "foundry": 8, "toolmaker": 6}[key]
        if remaining > 0:
            reason = f"Serviced: {remaining} productive days left"
        elif buyer.get("operating_state") == "paused":
            reason = "Business is paused"
        elif buyer["stock"].get(good, 0) >= stock_limit:
            reason = "Output shelf is full; no maintenance order"
        elif buyer["cash"] < reserve + KIT_PRICE:
            reason = f"Needs {KIT_PRICE}c above operating reserve"
        else:
            reason = "+2 daily capacity for six productive days"
        ready = reason.startswith("+2")
        result.append({"id": key, "name": buyer["name"], "price": KIT_PRICE,
                       "demand": int(ready), "reason": reason})
    crew = current["road_crew"]
    ready = crew["order_day"] != village.day and crew["stock"] == 0
    result.append({"id": "road_crew", "name": "Road Crew Mechanic", "price": KIT_PRICE,
                   "demand": int(ready),
                   "reason": "Funded road work: one kit/day, used next morning" if ready else "Today's road-work order is filled"})
    for product, name in EXPORT_NAMES.items():
        if not any(item["kind"] == PRODUCTS[product]["machine"] for item in current["equipment"]) and not current["goods"][product]:
            continue
        order = current["exports"].setdefault(product, {"day": village.day, "delivered": 0, "used": 0})
        if order["day"] != village.day:
            order.update(day=village.day, used=order["used"] + order["delivered"], delivered=0)
        demand = max(0, 2 - order["delivered"])
        result.append({"id": "export_" + product, "name": name, "product": product,
                       "price": PRODUCTS[product]["price"], "demand": demand,
                       "reason": PRODUCTS[product]["name"] + ": two funded exports per day" if demand else "Today's shipment is filled"})
    return result


def sell_goods(village, buyer_id, count=1):
    if type(count) is not int or count != 1:
        return False, "Deliver one product per transaction."
    offer = next((offer for offer in offers(village) if offer["id"] == buyer_id), None)
    if not offer or not offer["demand"]:
        return False, offer["reason"] if offer else "Choose a local maintenance customer."
    current = state(village)
    if buyer_id.startswith("export_"):
        product = offer["product"]
        if current["goods"][product] < 1:
            return False, "Produce " + PRODUCTS[product]["name"].lower() + " first."
        current["goods"][product] -= 1
        current["exports"][product]["delivered"] += 1
        village.coins += offer["price"]
        current["sold"] += 1
        current["earned"] += offer["price"]
        village._record_trade("Your Workshop", offer["name"], product, 1, offer["price"], external=True,
                              purpose="Funded daily shipment; consumed by outside industry")
        return True, f"Shipped {PRODUCTS[product]['name'].lower()} for {offer['price']}c."
    if current["goods"]["repair_kits"] < 1:
        return False, "Make a repair kit before selling it."
    if buyer_id == "road_crew":
        crew = current["road_crew"]
        crew["stock"] += 1
        crew["order_day"] = village.day
        village.coins += KIT_PRICE
        current["goods"]["repair_kits"] -= 1
        current["sold"] += 1
        current["earned"] += KIT_PRICE
        village._record_trade("Your Workshop", "Road Crew Mechanic", "repair kit", 1, KIT_PRICE,
                              external=True, purpose="One funded road-maintenance order per day; kit used next morning")
        _event(village, f"Sold one kit to the Road Crew Mechanic for {KIT_PRICE}c.")
        return True, "Sold one kit for 10c. The road crew uses it next morning; one funded order per day."
    buyer = village.businesses[buyer_id]
    buyer["cash"] -= KIT_PRICE
    village.coins += KIT_PRICE
    current["goods"]["repair_kits"] -= 1
    current["sold"] += 1
    current["earned"] += KIT_PRICE
    current["maintenance"][buyer_id] = {"remaining": MAINTENANCE_DAYS, "used_day": None, "last_day": village.day,
                                               "baseline": village.daily_life.get("produced", {}).get(buyer_id, 0)}
    village._record_trade("Your Workshop", buyer["name"], "repair kit", 1, KIT_PRICE,
                          purpose="Installed maintenance: +2 capacity for six productive days")
    _event(village, f"Sold one repair kit to {buyer['name']} for {KIT_PRICE}c.")
    return True, f"Sold one kit for {KIT_PRICE}c. {buyer['name']} gains +2 capacity for six productive days."


def _step(village):
    current = state(village)
    _review_maintenance(village)
    for machine in current["equipment"]:
        if machine["kind"] not in CONTROLLABLE:
            continue
        previous_pulse = machine.get("pulse", 0)
        machine["pulse"] = 0
        if machine["kind"] not in PRODUCTION:
            _roll_trader_day(village, machine)
            machine["trade_wait"] = max(0.0, machine["trade_wait"] - STEP_SECONDS)
        elif machine["busy"] > 0:
            machine["busy"] = max(0.0, machine["busy"] - STEP_SECONDS)
            if machine["busy"] == 0:
                current["goods"][product_for(machine)] += 1
                current["produced"] += 1
                machine["produced"] += 1
                machine["pulse"] = 1
                if machine["batch_auto"]:
                    current["auto_produced"] += 1
                _event(village, "Finished " + PRODUCTS[product_for(machine)]["name"].lower() + ".")
        # Trading actions happen after their controller tick. Present their
        # previous-step completion pulse exactly once on the following tick.
        if machine["kind"] not in PRODUCTION:
            machine["pulse"] = previous_pulse
        if machine.get("controller"):
            try:
                circuit = _live_circuit(village, machine)
                circuit.switches.update(input_values(village, machine["id"]))
                circuit.tick()
                machine["signal"] = circuit.output_value()
                machine["controller"]["runtime"] = circuit.runtime_snapshot()
            except (ValueError, KeyError, TypeError, RecursionError):
                machine["mode"] = "manual"
                machine["status"] = "Controller invalid; reinstall a valid design"
                machine["signal"] = 0
                continue
        if machine["kind"] not in PRODUCTION:
            machine["pulse"] = 0
            if machine["mode"] == "auto" and machine.get("controller") and machine["signal"]:
                if machine["trade_wait"] <= 0:
                    _trade(village, machine)
                    machine["trade_wait"] = TRADE_SECONDS
            else:
                machine["status"] = _trade_reason(village, machine) or ("Controller idle" if machine["mode"] == "auto" else "Manual trading")
        elif machine["busy"] > 0:
            machine["status"] = "Working"
        elif machine["mode"] == "auto" and machine.get("controller") and machine["signal"]:
            _start(village, machine, automatic=True)
        else:
            machine["status"] = _start_reason(village, machine) or ("Controller idle" if machine["mode"] == "auto" else "Ready")


def update(village, dt):
    # Untouched saves do not acquire new economic state merely by advancing.
    if not getattr(village, "manufacturing", None) or not math.isfinite(dt) or dt <= 0:
        return
    current = state(village)
    current["accumulator"] += dt
    while current["accumulator"] + 1e-9 >= STEP_SECONDS:
        current["accumulator"] -= STEP_SECONDS
        if abs(current["accumulator"]) < 1e-9:
            current["accumulator"] = 0.0
        _step(village)
