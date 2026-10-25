"""Render a disposable town preview and sprite comparison without player saves."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pygame
from game import Game
from ui_theme import PAPER, TEAL, INK


def main():
    output = ROOT / "testing-screenshots" / "walking-shannon"
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as folder, \
            patch("game.SAVES_DIR", Path(folder) / "saves"), \
            patch("game.SAVE_FILE", Path(folder) / "legacy.json"), \
            patch("game.DESIGNS_FILE", Path(folder) / "designs.json"):
        game = Game()
        game.start_slot(1)
        for _ in range(38):
            game.town.move(defaultdict(bool, {pygame.K_d: True}), 1 / 60)
        game.draw()
        pygame.image.save(game.screen, str(output / "town.png"))
        sheet = pygame.Surface((920, 580))
        sheet.fill(PAPER)
        for column, facing in enumerate(("south", "east", "north", "west")):
            title = game.small.render(facing.title(), True, TEAL)
            sheet.blit(title, title.get_rect(center=(column * 230 + 115, 22)))
            for row, name in enumerate(("Boole", "Luca", "Shannon")):
                sprite = pygame.Surface((90, 85), pygame.SRCALPHA)
                if name == "Shannon":
                    game.town.companion.facing = facing
                    game.town.companion.draw(sprite, 45, 49)
                else:
                    game.town._villager(sprite, 45, 49, TEAL if name == "Boole" else (65, 115, 130),
                                        facing=facing, name=name)
                sheet.blit(pygame.transform.scale(sprite, (180, 170)), (column * 230 + 25, 42 + row * 178))
                label = game.tiny.render(name, True, INK)
                sheet.blit(label, label.get_rect(center=(column * 230 + 115, 205 + row * 178)))
        pygame.image.save(sheet, str(output / "sprite-comparison.png"))
        pygame.quit()
    print(output)


if __name__ == "__main__":
    main()
