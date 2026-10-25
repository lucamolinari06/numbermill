"""Saved timing-goal workbenches and their test overlay."""
import pygame
import sequential
import sandbox
import workshop_floor
from circuit import Circuit, edge_terminals


def sync(game):
    if game.timing_key is None:
        return
    circuit, names = game.device_stack[0][:2] if game.device_stack else (game.circuit, game.port_names)
    game.village.sequential_drafts[game.timing_key] = {
        "parts": circuit.snapshot(), "ports": names.copy(),
        "runtime": circuit.runtime_snapshot(), "numeric": game.numeric_mode,
        "elapsed": game.elapsed, "paused": game.paused, "tick_interval": game.tick_interval,
    }


def enter(game, key):
    if game.factory_context is not None:
        import factory_controller
        factory_controller.leave(game)
    if key not in sequential.CHALLENGES:
        return
    if game.timing_key is not None:
        leave(game)
    if game.sandbox_context is not None:
        sandbox.leave(game)
    if game.invention:
        game.close_invention()
    game.timing_context = {name: getattr(game, name) for name in sandbox.CONTEXT}
    game.timing_key = key
    draft = game.village.sequential_drafts.get(key, {})
    game.circuit = Circuit.from_snapshot(draft["parts"]) if draft else Circuit(terminals=edge_terminals(("A", "B")))
    game.port_names = dict(draft.get("ports", sequential.CHALLENGES[key].port_names))
    game.device_stack = []
    game.active_compute = None
    game.numeric_mode = bool(draft.get("numeric", key != "clock"))
    game.paused = bool(draft.get("paused", True))
    game.elapsed = draft.get("elapsed", 0.0)
    game.tick_interval = min(1.0, max(.04, float(draft.get("tick_interval", .22))))
    game.rotation = 0
    game.selected, game.tab, game.scene = "TRACE", "BUILD", "workshop"
    game.design_source = game.held_device = None
    game.test_results = game.tested_job = game.tested_snapshot = game.success_job = None
    game.delivery_open = game.help_open = game.task_help_open = game.invention_picker = False
    game.timing_results = None
    workshop_floor.cancel(game)
    workshop_floor.prepare(game)
    if draft.get("runtime"):
        try:
            game.circuit.restore_runtime(draft["runtime"])
        except ValueError:
            game.toast("The timing draft was restored with its simulation reset.")
    game.save_game()


def leave(game):
    if game.timing_key is None:
        return
    sync(game)
    for name, value in game.timing_context.items():
        setattr(game, name, value)
    game.timing_key = game.timing_context = game.timing_results = None
    game.task_help_open = False
    game.port_editor = None
    workshop_floor.cancel(game)
    game.scene = "workshop"
    game.save_game()


def test(game):
    workshop_floor.prepare(game)
    game.test_scroll = 0
    game.task_help_open = False
    game.timing_results = sequential.run_tests(game.circuit, game.timing_key)
    passed = bool(game.timing_results) and all(row.passed for row in game.timing_results)
    if passed:
        game.village.sequential_records[game.timing_key] = {
            "day": game.village.day, "parts": game.circuit.snapshot(),
            "ports": game.port_names.copy(),
        }
    game.toast("Timing design certified. Your neighbors can use this work." if passed else
               "Timing checks need work. Review the expected and actual values.")
    game.save_game()


def draw_results(game):
    from game import rounded, text, PAPER, TEAL, MUTED, RED
    shade = pygame.Surface(game.screen.get_size(), pygame.SRCALPHA)
    shade.fill((20, 29, 29, 180))
    game.screen.blit(shade, (0, 0))
    game.buttons.clear()
    rounded(game.screen, PAPER, (250, 95, 780, 575), 8)
    rows = game.timing_results
    count = sum(row.passed for row in rows)
    text(game.screen, game.heading, f"TIMING CHECKS: {count}/{len(rows)}", 280, 120, TEAL)
    text(game.screen, game.small, "Certified for story projects" if count == len(rows) else "Each test follows a sequence over time.", 280, 160)
    for label, x in (("SEQUENCE", 280), ("EXPECTED", 670), ("ACTUAL", 815), ("PASS", 965)):
        text(game.screen, game.tiny, label, x, 204, MUTED)
    for i, row in enumerate(rows[game.test_scroll:game.test_scroll + 8]):
        y = 239 + i * 39
        text(game.screen, game.tiny, row.label, 280, y, width=375)
        text(game.screen, game.tiny, str(row.expected), 670, y, width=135)
        text(game.screen, game.tiny, str(row.actual), 815, y, width=135)
        text(game.screen, game.tiny, "YES" if row.passed else "NO", 965, y, TEAL if row.passed else RED)
    text(game.screen, game.tiny, "Up/Down or wheel: scroll. Tests leave your live circuit unchanged.", 280, 570, MUTED)
    game.button((280, 612, 210, 36), "CLOSE [ESC]", lambda: setattr(game, "timing_results", None), small=True)
    game.button((515, 612, 210, 36), "TEST AGAIN [T]", lambda: test(game), small=True)
    game.button((750, 612, 250, 36), "TASK DETAILS", lambda: setattr(game, "task_help_open", True), small=True)
