"""Reproduce bench previews using disposable saves only."""
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
import sandbox
import workbench
import adventure


def main():
    output = ROOT / "testing-screenshots" / "bench-sweep"
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as folder, \
            patch("game.SAVES_DIR", Path(folder) / "saves"), \
            patch("game.SAVE_FILE", Path(folder) / "legacy.json"), \
            patch("game.DESIGNS_FILE", Path(folder) / "designs.json"):
        game = Game()
        game.start_slot(1)
        game.scene = "workshop"

        def capture(name):
            game.message_timer = 0
            game.draw()
            pygame.image.save(game.screen, str(output / (name + ".png")))

        capture("contract")
        sandbox.enter(game)
        for group in workbench.COMPONENT_GROUPS:
            game.bench_component_group = group
            game.selected = {"Logic": "XOR", "Math": "MUX", "Memory": "REGISTER"}[group]
            capture("sandbox-" + group)
        sandbox.toggle_inputs(game)
        capture("three-inputs")
        for i in range(6):
            game.save_copy("Long controller name for factory machinery " + str(i))
        game.tab = "LIBRARY"
        capture("library")
        game.tab = "VILLAGE"
        capture("village")
        for kind in adventure.TITLES:
            adventure.enter_editor(game, kind)
            capture("field-" + kind + "-spec")
            game.adventure_spec = False
            game.adventure_group = "Math"
            game.selected = "MUX"
            game.adventure_result = "A=65535 B=65535 C=65535: expected 65535, got 65535 (unstable)"
            capture("field-" + kind)
            adventure.close_editor(game)
        pygame.quit()
    print(output)


if __name__ == "__main__":
    main()
