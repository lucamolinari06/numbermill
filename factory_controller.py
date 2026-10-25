"""An isolated editor for installed factory controllers, using the existing bench."""
from circuit import Circuit, edge_terminals
import manufacturing
import sandbox
import timing_workshop
import workshop_floor


def machine(game):
    return next((item for item in manufacturing.state(game.village)["equipment"]
                 if item["id"] == game.factory_machine_id), None)


def wiring(village, unit_id):
    item = manufacturing.get_machine(village, unit_id)
    defaults = {"A": "selectedstock", "B": "target"} if item and item["kind"] == "buyer" else {"A": "ready", "B": "stock"}
    draft = manufacturing.state(village).get("controller_drafts", {}).get(str(unit_id), {})
    saved = (item.get("controller") or draft) if item else {}
    return {"inputs": dict(saved.get("inputs", defaults)), "sources": dict(saved.get("sources", {"A": None, "B": None}))}


def mappings(game):
    return wiring(game.village, game.factory_machine_id)["inputs"]


def configure_input(village, unit_id, port, source_id, sensor):
    item = manufacturing.get_machine(village, unit_id)
    if item and item.get("controller"):
        return manufacturing.set_input_source(village, unit_id, port, source_id, sensor)
    if not item or item["kind"] not in manufacturing.CONTROLLABLE or port not in ("A", "B") or sensor not in manufacturing.SENSOR_NAMES:
        return False, "Choose a machine, an input and a sensor."
    if source_id is not None:
        source = manufacturing.get_machine(village, source_id)
        if not source or source["kind"] != "storage" or sensor not in manufacturing.STORAGE_SENSORS:
            return False, "Choose an available storage output."
    config = wiring(village, unit_id)
    config["inputs"][port], config["sources"][port] = sensor, source_id
    manufacturing.state(village)["controller_drafts"].setdefault(str(unit_id), {}).update(config)
    return True, f"{port} connected in draft. Install your board to run it."


def action(game):
    item = machine(game)
    return {"buyer": "purchase", "seller": "sale"}.get(item["kind"] if item else "bench", "batch")


def title(game):
    item = machine(game)
    return manufacturing.CATALOG[item["kind"]]["name"] + " controller" if item else "Factory controller"


def port_info(game, port):
    """Readable sources for the editor; these describe live wiring, not test values."""
    item = machine(game)
    if port == "OUT":
        return {"label": {"batch": "Start batch", "purchase": "Buy material", "sale": "Sell product"}[action(game)],
                "source": f"Unit #{item['id']}" if item else "Unit", "value": game.circuit.output_value()}
    sensor = mappings(game)[port]
    source_id = wiring(game.village, game.factory_machine_id)["sources"].get(port)
    source = f"Rack #{source_id}" if source_id is not None else "Unit sensor"
    if source_id is not None and manufacturing.get_machine(game.village, source_id) is None:
        source = "Disconnected"
    return {"label": manufacturing.SENSOR_NAMES.get(sensor, sensor), "source": source,
            "value": game.circuit.switches.get(port, 0)}


def purpose(game):
    item = machine(game)
    if not item:
        return "Factory controller"
    if item["kind"] in manufacturing.PRODUCTION:
        return "Make " + manufacturing.PRODUCTS[manufacturing.product_for(item)]["name"].lower()
    return "Buy " + item.get("config", {}).get("good", "metal") if item["kind"] == "buyer" else "Sell " + manufacturing.PRODUCTS[manufacturing.product_for(item)]["name"].lower()


def load_live_inputs(game):
    item = machine(game)
    if not item:
        return
    values = manufacturing.input_values(game.village, item["id"])
    if not values:
        config = wiring(game.village, item["id"])
        values = {}
        for port, sensor in config["inputs"].items():
            source_id = config["sources"].get(port)
            sensors = (manufacturing.sensor_values(game.village, item["id"]) if source_id is None else
                       manufacturing.storage_values(game.village, source_id))
            values[port] = max(0, min(65535, int(sensors.get(sensor, 0))))
    game.circuit.reset()
    game.circuit.switches.update(values)
    game.toast("Live readings copied to test inputs.")


def edit_connections(game):
    import factory_ui
    unit_id = game.factory_machine_id
    leave(game)
    game.factory_selected = unit_id
    factory_ui.open_route(game, unit_id=unit_id)


def sync(game):
    if game.factory_context is None:
        return
    circuit, ports = game.device_stack[0][:2] if game.device_stack else (game.circuit, game.port_names)
    config = wiring(game.village, game.factory_machine_id)
    manufacturing.state(game.village).setdefault("controller_drafts", {})[str(game.factory_machine_id)] = {
        **config,
        "parts": circuit.snapshot(), "runtime": circuit.runtime_snapshot(), "ports": ports.copy(),
        "elapsed": game.elapsed, "tick_interval": game.tick_interval, "paused": game.paused,
    }


def enter(game, machine_id):
    if game.factory_context is not None:
        leave(game)
    item = next((item for item in manufacturing.state(game.village)["equipment"]
                 if item["id"] == machine_id and item["kind"] in manufacturing.CONTROLLABLE), None)
    if item is None:
        game.toast("Select a production or trading unit first.")
        return
    if game.sandbox_context is not None:
        sandbox.leave(game)
    if game.timing_key is not None:
        timing_workshop.leave(game)
    if game.invention:
        game.close_invention()
    game.factory_context = {key: getattr(game, key) for key in sandbox.CONTEXT}
    game.factory_machine_id = machine_id
    draft = manufacturing.state(game.village).setdefault("controller_drafts", {}).get(str(machine_id), {})
    installed = item.get("controller") or {}
    parts = draft.get("parts", installed.get("parts"))
    game.circuit = Circuit.from_snapshot(parts) if parts is not None else Circuit(terminals=edge_terminals(("A", "B")))
    game.active_compute = None
    game.numeric_mode = True
    game.paused = draft.get("paused", True)
    game.elapsed = draft.get("elapsed", 0.0)
    game.tick_interval = draft.get("tick_interval", .22)
    game.device_stack = []
    game.port_names = {port: manufacturing.SENSOR_NAMES.get(sensor, sensor) for port, sensor in mappings(game).items()}
    game.port_names["OUT"] = "Permit next " + action(game)
    game.port_editor = None
    game.design_source = game.held_device = None
    game.test_results = game.tested_job = game.tested_snapshot = game.success_job = None
    game.delivery_open = game.help_open = game.task_help_open = game.invention_picker = False
    game.selected, game.tab, game.scene = "TRACE", "BUILD", "workshop"
    game.palette_page = 0
    game.factory_component_group = "Logic"
    game.rotation = 0
    workshop_floor.cancel(game)
    workshop_floor.prepare(game)
    if draft.get("runtime"):
        try:
            game.circuit.restore_runtime(draft["runtime"])
        except ValueError:
            game.circuit.reset()
    game.toast("Controller draft: village time paused. Enter installs; Esc returns to your floor.")
    game.save_game()


def leave(game):
    if game.factory_context is None:
        return
    sync(game)
    game.factory_selected = game.factory_machine_id
    for key, value in game.factory_context.items():
        setattr(game, key, value)
    game.factory_context = None
    game.factory_machine_id = None
    game.task_help_open = False
    game.port_editor = None
    game.scene = "factory"
    game.factory_page = "floor"
    workshop_floor.cancel(game)
    game.save_game()


def install(game):
    workshop_floor.prepare(game)
    okay, message = manufacturing.install_controller(game.village, game.factory_machine_id, game.circuit,
                                                     inputs=mappings(game), sources=wiring(game.village, game.factory_machine_id)["sources"])
    game.toast(message)
    game.save_game()
    return okay


def preview(game):
    """A sandbox readout, not a claim that arbitrary automation is correct."""
    test = Circuit.from_snapshot(game.circuit.snapshot())
    test.switches.update(game.circuit.switches)
    for _ in range(12):
        test.tick()
    game.toast(f"Preview after 12 ticks: OUT={test.output_value()}. Nonzero permits a {action(game)}. Inputs are test values.")


def description(game):
    inputs = mappings(game)
    return title(game), [
        f"A: {inputs['A']}. B: {inputs['B']}. Connect storage outputs from the floor.",
        f"OUT > 0 permits a {action(game)}; zero waits. Your circuit makes the decision.",
        "Signals take time. Material, storage, cash and customer limits still apply.",
        "Live controllers tick every 0.5 seconds. Enter installs; Auto runs it. T previews test inputs. Editing pauses village time.",
    ]
