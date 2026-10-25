"""Reproduce the workshop presentation pass using disposable saves only."""
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
from circuit import Part
import manufacturing as factory
import factory_ui
import dialogue
import ledger


def main():
    output = ROOT / 'testing-screenshots' / 'workshop-overhaul'
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as folder:
        root = Path(folder)
        with patch('game.SAVES_DIR', root / 'saves'), patch('game.SAVE_FILE', root / 'legacy.json'), \
                patch('game.DESIGNS_FILE', root / 'designs.json'):
            g = Game()
            g.start_slot(1)
            g.open_factory()

            def capture(name):
                g.message_timer = 0
                g.draw()
                pygame.image.save(g.screen, str(output / (name + '.png')))
                rects = [rect for rect, _ in g.buttons]
                for i, rect in enumerate(rects):
                    assert g.screen.get_rect().contains(rect), (name, rect)
                    assert not any(rect.colliderect(other) for other in rects[i + 1:]), (name, rect)

            capture('empty-workshop')
            g.factory_page = 'equipment'
            capture('equipment-starting')
            g.village.coins = 600
            g.village.businesses['toolmaker']['stock']['fittings'] = 100
            g.village.material_inventory = {'metal': 30, 'fuel': 30, 'fittings': 30}
            factory.unlock_equipment(g.village, 'precision_machine')
            equipment = (('bench', (2, 2)), ('storage', (1, 4)), ('controller', (3, 4)),
                         ('display', (5, 4)), ('buyer', (1, 1)), ('seller', (7, 4)),
                         ('press', (4, 2)), ('lathe', (6, 2)), ('precision_machine', (7, 1)))
            for kind, pos in equipment:
                assert factory.buy_equipment(g.village, kind, pos)[0]
            current = factory.state(g.village)
            current['unlocks'].append('steam_accumulator')
            current['goods'].update(metal_plates=2, steam_valves=2, repair_kits=2)
            g.village.daily_life['elapsed'] = 3.15
            bench = current['equipment'][0]
            assert factory.start_batch(g.village, bench['id'])[0]
            g.factory_selected = bench['id']
            g.factory_page = 'floor'
            capture('working-floor')
            g.factory_selected = None
            capture('workshop-overview')
            for page in ('equipment', 'supplies', 'orders'):
                g.factory_page = page
                capture(page)
            factory_ui.open_dialog(g, 'equipment', equipment='precision_machine')
            capture('machine-details')
            factory_ui.close_dialog(g)
            g.open_circuit_bench()
            for pos, kind in (((4, 3), 'XOR'), ((7, 5), 'NOT'), ((10, 3), 'OR')):
                g.circuit.set_part(pos, Part(kind))
            inputs = [p for p, term in g.circuit.terminals.items() if not term['output']]
            outputs = [p for p, term in g.circuit.terminals.items() if term['output']]
            g.circuit.connect(inputs[0], (4, 3), 0, [[2.5, 3.5]])
            g.circuit.connect(inputs[1], (4, 3), 1, [[3.5, 7], [4.5, 7]])
            g.circuit.connect((4, 3), (10, 3), 0, [[8.5, 3.5]])
            g.circuit.connect(inputs[1], (7, 5), 0, [[3.5, 7], [6.5, 7]])
            g.circuit.connect((7, 5), (10, 3), 1, [[10.5, 5.5]])
            g.circuit.connect((10, 3), outputs[0], 0, [[13.5, 3.5]])
            capture('free-build')
            for name in ('Sorting relay', 'Pressure monitor', 'Production counter'):
                g.save_copy(name)
            g.tab = 'LIBRARY'
            capture('library')
            g.scene = 'contracts'
            capture('contracts')
            g.scene = 'ledger'
            for tab in ledger.TABS:
                g.select_ledger_tab(tab)
                capture('ledger-' + tab.lower())
            for _ in range(6):
                g.village.advance_day(g.town)
            g.select_ledger_tab('Overview')
            capture('ledger-history')
            g.scene = 'town'
            for name in ('Mely', 'Luca', 'Grace', 'Shannon'):
                g.town_dialogue = 'person:' + name
                g.town_topic = 'hopes'
                capture('dialogue-' + name.lower())
            pygame.quit()
    print(output)


if __name__ == '__main__':
    main()
