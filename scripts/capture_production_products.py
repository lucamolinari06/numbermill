"""Render expanded manufacturing using disposable save paths."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pygame
from game import Game
import factory_ui
import manufacturing as factory


def main():
    output = ROOT / 'testing-screenshots' / 'production-products'
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as folder, \
            patch('game.SAVES_DIR', Path(folder) / 'saves'), \
            patch('game.SAVE_FILE', Path(folder) / 'old.json'), \
            patch('game.DESIGNS_FILE', Path(folder) / 'designs.json'):
        game = Game()
        game.start_slot(1)
        game.open_factory()

        def capture(name):
            game.draw()
            rects = [rect for rect, _ in game.buttons]
            for index, rect in enumerate(rects):
                assert game.screen.get_rect().contains(rect), (name, rect)
                assert not any(rect.colliderect(other) for other in rects[index + 1:]), (name, rect)
            pygame.image.save(game.screen, str(output / (name + '.png')))

        game.factory_page = 'equipment'
        capture('equipment-locked')
        factory_ui.open_dialog(game, 'equipment', equipment='precision_machine')
        capture('blueprint-details')
        factory_ui.close_dialog(game)
        game.village.coins = 500
        game.village.businesses['toolmaker']['stock']['fittings'] = 50
        game.village.material_inventory = {'metal': 30, 'fuel': 30, 'fittings': 30}
        factory.unlock_equipment(game.village, 'precision_machine')
        for i, kind in enumerate(factory.CATALOG):
            assert factory.buy_equipment(game.village, kind, (i, 2))[0]
        for machine in factory.state(game.village)['equipment']:
            if machine['kind'] in factory.PRODUCTION:
                game.factory_selected = machine['id']
                game.factory_page = 'floor'
                factory.start_batch(game.village, machine['id'])
                capture(machine['kind'] + '-floor')
                factory.update(game.village, 15)
            factory_ui.open_dialog(game, 'settings' if machine['kind'] in factory.CONTROLLABLE else 'inspect', item_id=machine['id'])
            capture(machine['kind'] + '-details')
            factory_ui.close_dialog(game)
        for good in factory.PRODUCTS:
            factory_ui.open_dialog(game, 'product', good=good)
            capture(good + '-recipe')
            factory_ui.close_dialog(game)
        for page in ('equipment', 'supplies', 'orders'):
            game.factory_page = page
            capture(page)
        game.factory_order_page = 1
        capture('export-orders')
        pygame.quit()
    print(output)


if __name__ == '__main__':
    main()
