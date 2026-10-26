"""Matching clock/light fixtures and native motion checks; no player files used."""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VIEWS = (('center', (1000, 865)), ('mill', (350, 690)),
         ('artisan-street', (2110, 690)), ('river-cottages', (700, 1360)),
         ('developed-east', (2130, 1360)), ('developed-commercial', (2130, 350)))
HOURS = (('morning', 8.5), ('noon', 12), ('afternoon', 17), ('evening', 19.5))


def stage(game):
    """A populated, developed review fixture, separate from ordinary progression."""
    from citizens import prepare
    from daily_life import state
    from migration import HOMES, NEWCOMERS, housing_state
    village, town = game.village, game.town
    for home, candidate, job in zip(HOMES, NEWCOMERS, ('sawmill', 'foundry', 'toolmaker')):
        housing_state(village, home, True).update(cottage_built=True, housing_stage='occupied')
        village.households[home] = dict(cash=48, bread_need=1, missed_meals=0, bought=0)
        person = deepcopy(candidate)
        person.update(home=home, workplace=job, wage=8)
        prepare(person)
        village.citizens.append(person)
        village.businesses[job]['workers'] = 1
    village.businesses['east_bakery'] = dict(kind='bakery', name="Jun's Bakery", owner='Jun',
        workers=0, owner_operated=True, cash=120, stock={'bread': 0}, machines=[], operating_state='open')
    state(village)['started'] = True
    for person in village.citizens:
        person.update(activity='working', destination=person['workplace'])
    town.update_people(village, 0)
    for person in village.citizens:
        name = person['name']
        point = list(town.route_targets[name])
        town.people[name] = point.copy()
        town.display_people[name] = point.copy()
        person['position'] = point.copy()
    town.display_moving.clear()
    town.visual_time = 2.5


def set_hour(game, hour):
    from daily_life import DAY_SECONDS, state
    state(game.village).update(elapsed=(hour-8)/12*DAY_SECONDS, accumulator=0.)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', default='after', choices=('before', 'after'))
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--hold', type=float, default=0., help='Keep the final native view open for inspection')
    args = parser.parse_args()
    if not args.smoke:
        os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
    import pygame
    from game import Game
    output = ROOT/'testing-screenshots'/'copperside-daylight'
    frames = output/args.label
    frames.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as folder:
        root = Path(folder)
        with patch('game.SAVES_DIR', root/'saves'), patch('game.SAVE_FILE', root/'old.json'), \
                patch('game.DESIGNS_FILE', root/'designs.json'):
            g = Game(); g.start_slot(1)
            pygame.display.set_caption('Numbermill - Copperside daylight review (disposable)')
            g.opening_screen = None
            g.reduced_motion = False
            stage(g)

            def draw():
                g.town.draw(g.screen, (g.small, g.font, g.heading, g.big), g.village, None, '')

            for name, point in VIEWS:
                g.town.player_x, g.town.player_y = point
                g.town.companion.reset(point)
                for period, hour in HOURS:
                    set_hour(g, hour)
                    draw()
                    pygame.image.save(g.screen, frames/f'{name}-{period}.png')
            if args.label == 'after':
                # Also inspect ordinary decisions and production, not only the
                # deliberately populated matching before/after work fixture.
                from daily_life import state, update_continuous
                state(g.village).update(elapsed=0., accumulator=0., started=False)
                for period,hour in HOURS:
                    target=(hour-8)/12*180.
                    update_continuous(g.village,g.town,target-state(g.village)['elapsed'])
                    g.town.update_visuals(1.)
                    for name,point in VIEWS:
                        g.town.player_x,g.town.player_y=point
                        g.town.companion.reset(point)
                        draw();pygame.image.save(g.screen,frames/f'routine-{name}-{period}.png')
            if args.smoke:
                native_check(g, draw, output)
                import time
                end=time.monotonic()+max(0.,args.hold)
                while time.monotonic()<end:
                    pygame.event.pump();g.viewport.present();g.clock.tick(60)
            pygame.quit()
    options = ''.join(f'<option value="{name}">{name.replace("-", " ")}</option>' for name, _ in VIEWS)
    periods = ''.join(f'<option value="{name}">{name} {int(hour):02d}:{round(hour%1*60):02d}</option>' for name, hour in HOURS)
    (output/'review.html').write_text('''<!doctype html><meta charset="utf-8"><title>Copperside daylight review</title>
<style>body{background:#233b35;color:#f1e4c2;font:18px system-ui;margin:24px}img{display:block;image-rendering:pixelated;max-width:none;margin:16px 0}button,select{font:inherit;padding:6px 12px}button:focus{outline:3px solid #dcab51}</style>
<h1>Copperside daylight</h1><p>Matching 1280 × 760 gameplay frames. Populated streets and developed eastern sites are staged disposable fixtures. Choose a place and clock time, then switch Before/After. Images keep native pixels.</p>
<select id="place" onchange="show()">'''+options+'''</select><select id="period" onchange="show()">'''+periods+'''</select>
<button onclick="version='before';show()">Before</button><button onclick="version='after';show()">After</button>
<span id="caption"></span><img id="view" width="1280" height="760">
<h2>Ordinary village routines</h2><p>These additional views advance the same disposable developed town through its real simulation, including purchases, attendance, production limits and evening destinations.</p>
<button onclick="routine.src='after/routine-'+place.value+'-'+period.value+'.png'">Show chosen place/time with ordinary routines</button>
<img id="routine" src="after/routine-center-evening.png" width="1280" height="760">
<script>let version='after';function show(){view.src=version+'/'+place.value+'-'+period.value+'.png';caption.textContent=version;}show();</script>''', encoding='utf-8')
    print(frames)


def native_check(g, draw, output):
    """Advance the real update path, freeze via Escape, resume, then calm motion."""
    import pygame
    from daily_life import state
    from PIL import Image
    # Opening chapter modals are disabled only in this disposable fixture.
    with patch('chapter_ui.active', return_value=False):
        # Start a fresh fixture for the native checks after routine captures.
        g.start_slot(2);g.opening_screen=None;stage(g)
        g.scene = 'town'; g.town_dialogue = None
        g.town.player_x, g.town.player_y = (350, 690)
        g.town.companion.reset((350, 690))
        set_hour(g, 10)
        g.village.manufacturing['equipment'] = []
        animation = []
        timings = []
        import time
        for frame in range(150):
            pygame.event.pump()
            g.update(1/60)
            start = time.perf_counter(); draw(); timings.append(time.perf_counter()-start)
            g.viewport.present(); g.clock.tick(60)
            if frame % 6 == 0:
                animation.append(Image.frombytes('RGB', g.screen.get_size(), pygame.image.tobytes(g.screen, 'RGB')))
        animation[0].save(output/'native-motion.gif', save_all=True, append_images=animation[1:], duration=100, loop=0)
        before = g.town.visual_time
        g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode=''))
        assert g.pause_menu_open
        draw(); frozen = pygame.image.tobytes(g.screen, 'RGB')
        saved = deepcopy(vars(g.village))
        for _ in range(60):
            pygame.event.pump(); g.update(1/60); draw(); g.viewport.present(); g.clock.tick(60)
            assert pygame.image.tobytes(g.screen, 'RGB') == frozen
        assert g.town.visual_time == before and vars(g.village) == saved
        g.draw(); pygame.image.save(g.screen, output/'native-paused.png')
        g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode=''))
        g.update(1/60)
        assert not g.pause_menu_open and g.town.visual_time > before
        g.reduced_motion = True; g.update(0)
        for name, point in g.town.people.items():
            g.town.display_people[name] = point.copy()
        g.town.display_moving.clear(); g.town._player_is_moving = False
        g.town.companion.moving = False
        draw(); calm = pygame.image.tobytes(g.screen, 'RGB')
        for _ in range(60):
            pygame.event.pump()
            # Fixed actors and actual clock isolate decorative motion.
            g.town.update_visuals(1/60); g.town.companion.seconds += 1/60
            draw(); g.viewport.present(); g.clock.tick(60)
            assert pygame.image.tobytes(g.screen, 'RGB') == calm
        set_hour(g, 19.5); draw(); g.viewport.present()
        pygame.image.save(g.screen, output/'native-evening.png')
        report = dict(driver=pygame.display.get_driver(), motion_frames=150, pause_frames=60,
            reduced_motion_frames=60, exact_pause=True, resume=True, calm_decoration=True,
            mean_draw_ms=round(sum(timings)/len(timings)*1000, 2), max_draw_ms=round(max(timings)*1000, 2),
            first_draw_ms=round(timings[0]*1000,2), warm_p95_draw_ms=round(sorted(timings[1:])[int(len(timings[1:])*.95)]*1000,2),
            elapsed=state(g.village)['elapsed'])
        (output/'native-check.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(report)


if __name__ == '__main__':
    main()
