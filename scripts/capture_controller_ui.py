"""Disposable controller and signal-routing previews; never opens player saves."""
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
from circuit import Part
import manufacturing
import factory_controller
import factory_ui
import workshop_floor


def main():
    output = ROOT / "testing-screenshots" / "controller-ui"
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as folder, \
            patch("game.SAVES_DIR", Path(folder) / "saves"), \
            patch("game.SAVE_FILE", Path(folder) / "legacy.json"), \
            patch("game.DESIGNS_FILE", Path(folder) / "designs.json"):
        game = Game()
        game.start_slot(1)
        game.open_factory()
        game.village.coins = 100
        game.village.businesses["toolmaker"]["stock"]["fittings"] = 30
        for kind, pos in (("buyer", (6, 2)), ("storage", (1, 3)), ("controller", (4, 2)), ("display", (6, 4))):
            assert manufacturing.buy_equipment(game.village, kind, pos)[0]
        unit, rack, cabinet, display = manufacturing.state(game.village)["equipment"]
        assert factory_controller.configure_input(game.village, unit["id"], "A", rack["id"], "metal")[0]
        game.village.material_inventory["metal"] = 1
        game.edit_factory_controller(unit["id"])
        circuit = game.circuit
        ports = {port["name"]: pos for pos, port in circuit.terminals.items()}
        circuit.set_part((7, 4), Part("GT"))
        circuit.connect(ports["B"], (7, 4), 0)
        circuit.connect(ports["A"], (7, 4), 1)
        circuit.connect((7, 4), ports["OUT"], 0)
        factory_controller.load_live_inputs(game)
        for _ in range(12):
            circuit.tick()

        def capture(name):
            game.message_timer = 0
            game.draw()
            pygame.image.save(game.screen, str(output / (name + ".png")))

        game.selected = "GT"
        game.factory_component_group = "Math"
        capture("controller-math")
        game.selected = "MUX"
        capture("component-pins")
        game.selected = "REGISTER"
        game.factory_component_group = "Memory"
        capture("controller-memory")
        with patch("pygame.mouse.get_pos", return_value=workshop_floor.socket(game, (7, 4), 3)):
            capture("wire-highlight")
        assert factory_controller.install(game)
        factory_controller.leave(game)
        manufacturing.configure_display(game.village, display["id"], "signal", unit["id"])
        capture("floor-paths")
        factory_ui.open_route(game, unit_id=unit["id"])
        capture("wire-sensor")
        pygame.quit()
    print(output)


if __name__ == "__main__":
    main()
