"""Disposable previews of the town scenery, without touching player saves."""
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


def main():
    output = ROOT / "testing-screenshots" / "town-detail"
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as folder, \
            patch("game.SAVES_DIR", Path(folder) / "saves"), \
            patch("game.SAVE_FILE", Path(folder) / "legacy.json"), \
            patch("game.DESIGNS_FILE", Path(folder) / "designs.json"):
        game = Game()
        game.start_slot(1)
        for name, position in (("workshop", (755, 690)), ("garden", (1010, 900)),
                               ("artisans", (2110, 690)), ("cottages-river", (700, 1360)),
                               ("north-shops", (975, 350))):
            game.town.player_x, game.town.player_y = position
            game.town.companion.reset(position)
            game.draw()
            pygame.image.save(game.screen, str(output / (name + ".png")))
        pygame.image.save(pygame.transform.scale(game.town.background, (1350, 780)), str(output / "town-overview.png"))
        pygame.quit()
    print(output)


if __name__ == "__main__":
    main()
