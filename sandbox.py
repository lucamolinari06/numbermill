"""An isolated, saved workshop floor for free experimentation."""
from circuit import Circuit, edge_terminals
import workshop_floor

CONTEXT = ("circuit", "port_names", "active_compute", "numeric_mode", "tab", "selected",
           "paused", "design_source", "device_stack", "rotation", "held_device", "elapsed", "tick_interval",
           "test_results", "tested_job", "tested_snapshot", "test_message", "success_job",
           "delivery_open", "help_open")


def sync(game):
    if game.sandbox_context is None:
        return
    circuit, names = (game.device_stack[0][:2] if game.device_stack else
                      (game.circuit, game.port_names))
    game.sandbox_draft = {"parts": circuit.snapshot(), "ports": names.copy(),
                          "numeric": game.numeric_mode, "inputs": dict(circuit.switches),
                          "runtime": circuit.runtime_snapshot(), "elapsed": game.elapsed, "tick_interval": game.tick_interval}


def enter(game):
    if game.factory_context is not None:
        import factory_controller
        factory_controller.leave(game)
    if game.timing_key is not None:
        import timing_workshop
        timing_workshop.leave(game)
    if game.sandbox_context is not None:
        game.scene = "workshop"
        return
    if game.invention:
        game.close_invention()
    game.sandbox_context = {name: getattr(game, name) for name in CONTEXT}
    draft = game.sandbox_draft
    game.circuit = (Circuit.from_snapshot(draft["parts"]) if draft else
                    Circuit(terminals=edge_terminals(("A", "B"))))
    game.port_names = draft.get("ports", {}).copy()
    game.numeric_mode = bool(draft.get("numeric", False))
    game.circuit.switches.update({k: v for k, v in draft.get("inputs", {}).items()
                                  if k in game.circuit.switches})
    game.active_compute = None
    game.device_stack = []
    game.design_source = game.held_device = None
    game.test_results = game.tested_job = game.tested_snapshot = game.success_job = None
    game.delivery_open = game.help_open = game.task_help_open = False
    game.paused = True
    game.elapsed = game.rotation = 0
    game.tick_interval = min(1.0, max(.04, float(draft.get("tick_interval", .22))))
    game.selected, game.tab, game.scene = "TRACE", "BUILD", "workshop"
    workshop_floor.cancel(game)
    workshop_floor.prepare(game)
    if draft.get("runtime"):
        try:
            game.circuit.restore_runtime(draft["runtime"])
            game.elapsed = draft.get("elapsed", 0.0)
        except ValueError:
            game.circuit.reset()
    game.toast("Sandbox: all components available. Space runs; T reads the output. Your job floor is saved.")


def leave(game):
    if game.sandbox_context is None:
        return
    sync(game)
    for name, value in game.sandbox_context.items():
        setattr(game, name, value)
    game.sandbox_context = None
    game.port_editor = None
    game.task_help_open = False
    workshop_floor.cancel(game)
    game.scene = "workshop"
    game.save_game()


def toggle_inputs(game):
    names = ("A", "B") if "C" in game.circuit.switches else ("A", "B", "C")
    if game.circuit.layout_terminals(names):
        workshop_floor.cancel(game)
        game.save_game()


def probe(game):
    if game.circuit.has_sequential():
        game.toast(f"Live output: {game.circuit.output_value()} at tick {game.circuit.tick_count}. Space runs; period steps.")
        game.save_game()
        return
    values = game.circuit.switches
    output, stable = game.circuit.evaluate(values.get("A", 0), values.get("B", 0), values.get("C", 0))
    game.toast(f"Sandbox output: {output} / {'stable' if stable else 'still changing'}. No delivery or reward.")
    game.save_game()
