"""Explicit, session-only expedition tools for development playthroughs."""
import math


def enabled(g):
    return bool(getattr(g, 'developer_mode', False))


def toggle(g):
    import adventure
    import boiler_tower as tower
    g.developer_mode = not enabled(g)
    # Turning collision back on must not leave Boole embedded in steel or water.
    scene = getattr(g, 'adventure_return_scene', '') if adventure.active_editor(g) else g.scene
    if not enabled(g):
        if scene == 'boiler_tower':
            tower.restore_checkpoint(g)
        elif scene == 'adventure':
            s = adventure.state(g.village)
            keys = ['exit', 'receiver', 'interlock']
            if s['interlock']: keys += ['survey', 'range_lock']
            if s['range_gate']: keys += ['artifact']
            point = min((adventure.POINTS[k] for k in keys), key=lambda p: math.dist(p, s['position']))
            s['position'] = list(point)
            g.adventure_companion.reset(point)
        g.save_game()
    g.toast('Developer mode ON: invincible / noclip.' if enabled(g) else
            'Developer mode OFF. Returned to safe ground.')


def solution(kind):
    """Build real circuits so installed output and ordinary certification agree."""
    from circuit import Circuit, Part, edge_terminals
    import boiler_tower as tower
    if kind not in ('decoder', 'interlock', *tower.EDITOR_KEYS):
        raise ValueError('Unknown field puzzle: ' + kind)
    c = Circuit(terminals=edge_terminals(('A', 'B', 'C')))
    ports = {p['name']: pos for pos, p in c.terminals.items()}
    count = 0

    def gate(name, part, *sources):
        nonlocal count
        pos = (2 + count // 4 * 2, 1 + count % 4 * 2)
        count += 1
        ports[name] = pos
        c.parts[pos] = Part(part)
        for i, source in enumerate(sources): c.connect(ports[source], pos, i)
        return name

    def number(n):
        name = str(n)
        if name not in ports:
            if n == 1: gate(name, 'EQ', 'A', 'A')
            else: gate(name, 'ADD', number(n // 2), number(n - n // 2))
        return name

    if kind == 'decoder':
        gate('bearing', 'DIV', 'A', 'C')
        gate('distance', 'MOD', 'A', 'C')
        gate('matches', 'EQ', 'bearing', 'B')
        gate('result', 'MUL', 'distance', 'matches')
    elif kind == 'interlock':
        one = number(1)
        gate('zero', 'SUB', 'A', 'A')
        gate('locked', 'EQ', 'C', one)
        gate('positive', 'GT', 'A', 'zero')
        gate('over', 'GT', 'A', 'B')
        gate('below', 'NOT', 'over')
        gate('pressure', 'AND', 'below', 'positive')
        gate('result', 'AND', 'locked', 'pressure')
    elif kind == 'tower_vent':
        gate('excess', 'SUB', 'A', 'B')
        gate('result', 'MUL', 'excess', 'C')
    else:
        p = tower.PROFILES[int(kind[-1])]
        low, limit, gain = number(p['minimum']), number(p['heat']), number(p['gain'])
        gate('low', 'GT', low, 'A')
        gate('pressure', 'NOT', 'low')
        gate('cool', 'GT', limit, 'B')
        gate('safe', 'AND', 'pressure', 'cool')
        gate('demand', 'MUL', 'C', gain)
        gate('result', 'MUL', 'demand', 'safe')
    c.connect(ports['result'], ports['OUT'], 0)
    return c


def solve(g, kind=None):
    import adventure
    import workshop_floor
    if not enabled(g): return False
    editing = adventure.active_editor(g)
    if editing:
        if g.device_stack: return False
        kind = g.adventure_editor
    if kind is None: return False
    if kind == 'canal_boat':
        g.toast('Build and test the boat controller at the landing.')
        return False
    circuit = solution(kind)
    ok, message = adventure.certify(circuit, kind)
    if not ok:
        g.toast(message)
        return False
    if editing:
        workshop_floor.cancel(g)
        g.circuit = circuit
        g.test_results = g.tested_job = g.tested_snapshot = g.success_job = None
        adventure.validate(g)
    else:
        s = adventure.state(g.village)
        s[kind] = True
        s['drafts'][kind] = {'parts': circuit.snapshot()}
        s['designs'][kind] = circuit.snapshot()
    if kind == 'decoder': adventure.state(g.village)['receiver'] = True
    g.adventure_decoder_cache = None
    g.tower_circuits = {}
    g.save_game()
    g.toast('Developer: puzzle solved and installed.')
    return True


def tower_task(g):
    import adventure
    import boiler_tower as tower
    s = tower.state(g.village)
    kind = tower.editor_key(s)
    if s['stage'] == 2 and kind in adventure.state(g.village)['designs']:
        return 'tower_vent'
    return kind


def next_maintenance(g):
    import boiler_tower as tower
    if not enabled(g) or g.scene != 'boiler_tower': return
    s = tower.state(g.village)
    target = next((i for i in tower.STATIONS if i > s['checkpoint']), None)
    if target is None: return
    s['position'] = tower.landing_position(target)
    tower.reset_motion(g)
    tower.arrive(g, target)
    tower.reset_rail(g)


def mosswater_task(g):
    import adventure
    s = adventure.state(g.village)
    if not s['decoder']: return 'decoder'
    if not s['interlock']: return 'interlock'
    if len(s['survey_found']) < 3: return 'survey'
    if not s['range_gate']: return 'range lock'
    return None


def skip_mosswater(g):
    import adventure
    import mosswater
    if not enabled(g) or g.scene != 'adventure': return
    kind = mosswater_task(g)
    if kind in ('decoder', 'interlock'):
        solve(g, kind)
        return
    s = adventure.state(g.village)
    if kind == 'survey':
        s['survey_started'] = True
        s['survey_found'] = [b['key'] for b in mosswater.BEACONS]
    elif kind == 'range lock':
        s.update(range_armed=True, range_gate=True, frequency=3)
    else: return
    g.save_game()
    g.toast('Developer: ' + kind + ' skipped.')


def fly(g, dt, horizontal, vertical):
    import boiler_tower as tower
    s = tower.state(g.village)
    x, y = s['position']
    length = max(1., math.hypot(horizontal, vertical))
    nx = max(35., min(tower.WIDTH-35., x + horizontal*560*dt/length))
    ny = max(80., min(tower.HEIGHT-40., y + vertical*560*dt/length))
    tower.reset_motion(g)
    g.tower_grounded = False
    # Checkpoint triggers remain usable, but none of the decks block flight.
    for i in tower.CHECKPOINTS:
        left, top, width = tower.PLATFORMS[i]
        if left <= nx <= left+width and min(y, ny) <= top <= max(y, ny):
            if i > s['checkpoint']:
                ny = float(top)
                s['position'] = [nx, ny]
                s['stage'] = max(s['stage'], min(2, sum(i >= station for station in tower.STATIONS)-1))
                tower.arrive(g, i)
                break
    s['position'] = [nx, ny]
    g.tower_grounded = any(left <= nx <= left+width and abs(ny-top) < 1
                           for left, top, width in tower.PLATFORMS)
    if horizontal: g.tower_facing = 'east' if horizontal > 0 else 'west'
    tower.update_rail(g, dt)


def draw(g):
    import adventure
    import boiler_tower as tower
    import ui_theme
    if not enabled(g) or getattr(g, 'adventure_modal', None): return
    if g.scene not in ('adventure', 'boiler_tower'): return
    ui_theme.draw_panel(g.screen, (24, 262, 300, 132))
    ui_theme.fit_text(g.screen, g.small, 'DEV / INVINCIBLE + NOCLIP', 36, 273, 276, ui_theme.TEAL)
    ui_theme.fit_text(g.screen, g.tiny, 'WASD / arrows: free movement', 36, 298, 276, ui_theme.MUTED)
    if g.scene == 'boiler_tower':
        s = tower.state(g.village)
        kind = tower_task(g)
        label = 'SOLVE EXHAUST' if kind == 'tower_vent' else f"SOLVE JETPACK {s['stage']+1}"
        g.button((34, 323, 280, 28), label, lambda: solve(g, tower_task(g)), small=True,
                 enabled=s['checkpoint'] != tower.SUMMIT)
        g.button((34, 357, 280, 28), 'NEXT MAINTENANCE', lambda: next_maintenance(g), small=True,
                 enabled=s['checkpoint'] != tower.SUMMIT)
    else:
        task = mosswater_task(g)
        g.button((34, 331, 280, 34), 'SKIP ' + task.upper() if task else 'PUZZLES COMPLETE',
                 lambda: skip_mosswater(g), small=True, enabled=task is not None)
