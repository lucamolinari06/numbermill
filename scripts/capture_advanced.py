"""Render timing goals/results and story choices using disposable saves."""
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
import timing_workshop
import character_projects


def main():
    output = ROOT / "testing-screenshots" / "advanced-circuits-stories"
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as directory, \
            patch("game.SAVES_DIR", Path(directory) / "saves"), \
            patch("game.SAVE_FILE", Path(directory) / "old.json"), \
            patch("game.DESIGNS_FILE", Path(directory) / "designs.json"):
        game = Game()
        game.start_slot(1)
        game.scene = "workshop"

        def capture(name):
            game.draw()
            pygame.image.save(game.screen, str(output / f"{name}.png"))

        game.invention_picker = True
        capture("goals")
        for key, kind in (("memory", "REGISTER"), ("clock", "CLOCK")):
            timing_workshop.enter(game, key)
            game.circuit.set_part((6, 3), Part(kind))
            ports = {p["name"]: pos for pos, p in game.circuit.terminals.items()}
            if kind != "CLOCK":
                game.circuit.connect(ports["A"], (6, 3), 0)
                game.circuit.connect(ports["B"], (6, 3), 1)
            game.circuit.connect((6, 3), ports["OUT"], 0)
            game.selected = kind
            capture(f"{key}-floor")
            timing_workshop.test(game)
            capture(f"{key}-results")
            game.task_help_open = True
            capture(f"{key}-details")
            game.task_help_open = False
        timing_workshop.leave(game)
        village = game.village
        village.day = 3
        village.last_day_report = {"day": 3, "produced": {"bakery": 4}}
        character_projects.evaluate(village)
        village.material_inventory = {"timber": 2, "fittings": 1}
        village.businesses["fuel_yard"]["cash"] = 100
        character_projects.accept(village, "mely_bins")
        character_projects.deliver(village, "mely_bins")
        village.day = 4
        village.last_day_report = {"day": 4, "produced": {"bakery": 4}}
        character_projects.evaluate(village)
        game.open_requests("Mely")
        capture("mely-choice")
        character_projects.choose(village, "mely_plan", "home")
        capture("mely-selected")
        pygame.quit()
    print(output)


if __name__ == "__main__":
    main()
