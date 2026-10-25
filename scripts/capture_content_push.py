"""Render the content push with disposable saves; never touches player progress."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import tempfile
from unittest.mock import patch
import pygame
from game import Game
import adventure
import scene_depth
from town import TRAIL_ENTRANCE


def main():
    output = ROOT / "testing-screenshots" / "content-push"
    output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as directory:
        root = Path(directory)
        with patch("game.SAVES_DIR", root / "saves"), patch("game.SAVE_FILE", root / "save.json"), patch("game.DESIGNS_FILE", root / "designs.json"):
            g = Game()
            g.start_slot(1)
            def capture(name):
                g.draw()
                pygame.image.save(g.screen, str(output / (name + ".png")))
            g.open_factory()
            g.open_circuit_bench()
            capture("sandbox-default")
            g.open_factory()
            g.scene = "town"
            g.town.player_x, g.town.player_y = TRAIL_ENTRANCE
            g.town.companion.reset(TRAIL_ENTRANCE)
            capture("town-trail")
            adventure.enter(g)
            capture("trail-entry")
            for name, position in (("ravine", (1080,560)), ("artifact", (1620,490))):
                adventure.state(g.village)["position"] = list(position)
                g.adventure_companion.reset(position)
                capture(name)
            overview = g.adventure_background.copy()
            scene_depth.draw(overview,(0,0),g.adventure_props)
            pygame.image.save(overview,str(output / "mosswater-overview.png"))
            adventure.enter_editor(g, "interlock")
            capture("interlock-specification")
            g.adventure_spec = False
            g.adventure_group = "Math"
            capture("field-circuit")
            pygame.quit()
    print(output)


if __name__ == "__main__":
    main()
