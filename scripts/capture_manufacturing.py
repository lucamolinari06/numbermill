"""Disposable previews of the production floor and its circuit editor."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pygame
from game import Game
import manufacturing
import factory_controller
import factory_ui


def main():
    output = ROOT / "testing-screenshots" / "manufacturing"
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as folder, \
            patch("game.SAVES_DIR", Path(folder) / "saves"), \
            patch("game.SAVE_FILE", Path(folder) / "legacy.json"), \
            patch("game.DESIGNS_FILE", Path(folder) / "designs.json"):
        game = Game()
        game.start_slot(1)
        game.open_factory()

        def capture(name):
            game.draw()
            pygame.image.save(game.screen, str(output / (name + ".png")))

        capture("new-workshop")
        manufacturing.buy_equipment(game.village, "bench", (2, 2))
        machine_id = manufacturing.state(game.village)["equipment"][0]["id"]
        game.factory_selected = machine_id
        for good in manufacturing.RECIPE:
            manufacturing.buy_supply(game.village, good)
        manufacturing.start_batch(game.village, machine_id)
        for _ in range(6):
            game.update(.5)
        capture("first-batch")
        # The remaining captures illustrate equipment in a disposable test save.
        game.village.coins = 100
        for kind, pos in (("controller", (4, 2)), ("display", (5, 2)), ("storage", (6, 2))):
            manufacturing.buy_equipment(game.village, kind, pos)
        game.edit_factory_controller(machine_id)
        positions = {p["name"]: pos for pos, p in game.circuit.terminals.items()}
        game.circuit.connect(positions["A"], positions["OUT"], 0)
        capture("controller-editor")
        game.task_help_open = True
        assert 270 + (len(game.task_detail_lines()) - 1) * 23 < 584
        capture("controller-details")
        game.task_help_open = False
        factory_controller.install(game)
        factory_controller.leave(game)
        manufacturing.set_mode(game.village, machine_id, True)
        for _ in range(20):
            game.update(.5)
        for page in ("floor", "equipment", "supplies", "orders"):
            game.factory_page = page
            capture(page)
        factory_ui.open_route(game, unit_id=machine_id)
        capture("input-connections")
        factory_ui.close_dialog(game)
        factory_ui.open_dialog(game, "equipment", equipment="buyer")
        capture("procurement-details")
        factory_ui.close_dialog(game)
        display = next(item for item in manufacturing.state(game.village)["equipment"] if item["kind"] == "display")
        manufacturing.configure_display(game.village, display["id"], "signal", machine_id)
        factory_ui.open_dialog(game, "settings", item_id=display["id"])
        capture("display-settings")
        factory_ui.close_dialog(game)
        factory_ui.open_dialog(game, "sell", item_id=display["id"])
        capture("sell-equipment")
        factory_ui.close_dialog(game)
        game.factory_order_page = 1
        capture("road-customer")
        game.pause_menu_open = True
        capture("paused")
        pygame.quit()
    print(output)


if __name__ == "__main__":
    main()
