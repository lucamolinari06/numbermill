"""Render the connected opening chapter using disposable saves and preferences."""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if '--smoke' not in sys.argv:
    os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
import pygame
import adventure
import boiler_tower
import chapter_ui
import opening_chapter as story
from game import Game


def main():
    output = ROOT / 'testing-screenshots' / 'opening-chapter'
    output.mkdir(parents=True, exist_ok=True)
    scratch = ROOT / '.test-tmp'
    scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch) as folder:
        root = Path(folder)
        with patch('game.SAVES_DIR', root / 'saves'), patch('game.SAVE_FILE', root / 'old.json'), patch('game.DESIGNS_FILE', root / 'designs.json'):
            g = Game()
            g.start_slot(1)

            def capture(name):
                g.draw()
                pygame.image.save(g.screen, str(output / (name + '.png')))

            capture('opening-prompt')
            chapter_ui.start_scene(g, 'opening')
            capture('opening-conversation')
            chapter_ui.close(g)
            chapter_ui.open_journal(g)
            capture('journal-first-question')
            chapter_ui.close(g)
            field = adventure.state(g.village)
            field.update(receiver=True, artifact=True, expansion_complete=True)
            boiler_tower.state(g.village)['complete'] = True
            g.village.manufacturing['unlocks'] += ['precision_machine', 'steam_accumulator']
            g.village.character_projects['mely_bins'] = {'status': 'completed'}
            for key in ('mosswater_home', 'tower_home', 'well_evening'):
                chapter_ui.start_scene(g, key)
                while chapter_ui.active(g):
                    capture(f"{key}-{g.chapter_view['index'] + 1}")
                    chapter_ui.advance(g)
            chapter_ui.open_journal(g)
            for index, key in enumerate(chapter_ui.evidence_keys(g)):
                chapter_ui.choose(g, index)
                capture('evidence-' + key)
            chapter_ui.switch_tab(g, 'Moments')
            capture('remembered-moments')
            chapter_ui.close(g)
            for name in story.PEOPLE:
                g.town_dialogue = 'person:' + name
                g.town_topic = 'journey'
                capture('journey-' + name.lower())
            g.town_dialogue = None
            g.open_factory()
            capture('accumulator-workshop')
            chapter_ui.start_scene(g, 'tower_home')
            capture('workshop-homecoming')
            if '--smoke' in sys.argv:
                # Exercise native input through the normal event dispatcher.
                for value in (pygame.K_RETURN, pygame.K_ESCAPE, pygame.K_b, pygame.K_TAB):
                    g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=value, mod=0))
                    g.update(1 / 60)
                    g.draw()
                assert g.chapter_view['tab'] == 'Moments'
                finish = pygame.time.get_ticks() + 2200
                while pygame.time.get_ticks() < finish:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            finish = 0
                    g.draw()
                    g.clock.tick(60)
            pygame.quit()
    print(output)


if __name__ == '__main__':
    main()
