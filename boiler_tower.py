"""The second expedition: a saved, side-view climb with a temporary steam pack.

Positions use the centre of Boole's feet. Physics runs in bounded substeps and
only maintenance landings change the pack's wear; nothing breaks in midair.
"""
from copy import deepcopy
import math
import pygame

import adventure
import developer_mode
import manufacturing
from circuit import Circuit
import boiler_tower_layout as layout
from boiler_tower_layout import (WIDTH, HEIGHT, PLATFORMS, STATIONS, CHECKPOINTS,
                                SUMMIT, VENT_STATION, landing_position)

GRAVITY, WALK_SPEED, JUMP_SPEED = 850., 220., 330.
AIR_ACCELERATION, AIR_DRAG = 700., .65
RAIL_DELAY, RAIL_GAP, RAIL_SPEED, RAIL_ACCELERATION = .35, 28., 360., 900.
PROFILES = (
    dict(name='Sound seals', pressure=12, minimum=3, heat=8, gain=1, force=600, speed=320),
    dict(name='Worn seals', pressure=8, minimum=2, heat=7, gain=2, force=250, speed=290),
    dict(name='Cracked seals', pressure=5, minimum=1, heat=6, gain=3, force=140, speed=260),
)
EDITOR_KEYS = ('jetpack_0', 'jetpack_1', 'jetpack_2', 'tower_vent')


def state(village):
    current = manufacturing.state(village).setdefault('boiler_tower', {})
    if current and current.get('layout_version',1) < layout.VERSION:
        # Old saves resume at the equivalent puzzle stop, never inside new steel.
        old_checkpoint=current.get('checkpoint',0)
        checkpoint=SUMMIT if current.get('complete') or old_checkpoint==9 else STATIONS[min(2,max(0,current.get('stage',0)))]
        current.update(layout_version=layout.VERSION,checkpoint=checkpoint,
                       position=landing_position(checkpoint))
    for key, value in dict(layout_version=layout.VERSION,visited=False, stage=0, checkpoint=0, position=landing_position(0),
                           pressure=12., heat=0., throttle=3, complete=False,
                           falls=0, vent_open=False, hazard_time=0.).items():
        current.setdefault(key, deepcopy(value))
    return current


def unlocked(village):
    return adventure.state(village)['expansion_complete']


def profile(current):
    return PROFILES[current['stage']]


def editor_key(current):
    return 'jetpack_' + str(current['stage'])


def specification(kind):
    if kind == 'tower_vent':
        return ('Tower / exhaust regulator', (
            'A: pipe pressure (0–12). B: safe pressure (0–9).',
            'C: exhaust request (0 or 1). OUT: pressure to release.',
            'When C is 1, release A minus B, with a minimum of zero.',
            'When C is 0, OUT must be 0. Use a combinational circuit.'))
    stage = int(kind[-1])
    p = PROFILES[stage]
    change = 'First installation: build a controller for the sound pack.'
    if stage:
        old = PROFILES[stage-1]
        change = (f"Upgrade: gain {old['gain']} → {p['gain']}; minimum pressure {old['minimum']} → {p['minimum']}; "
                  f"heat cutoff {old['heat']} → {p['heat']}.")
    return (f"Jetpack / Stage {stage+1} of 3 / {p['name']}", (
        f"A: pressure (0–12; pack holds {p['pressure']}). B: heat (0–10).",
        'C: thrust request (0–3). OUT: valve drive.',
        f"OUT = C × {p['gain']} only when A ≥ {p['minimum']} and B < {p['heat']}.",
        'Otherwise OUT = 0. Test every condition before flight.', change))


def cases(kind):
    if kind == 'tower_vent':
        return [(a, b, c, max(0, a-b)*c) for a in range(13) for b in range(10) for c in range(2)]
    p = PROFILES[int(kind[-1])]
    return [(a, b, c, c*p['gain'] if a >= p['minimum'] and b < p['heat'] else 0)
            for a in range(13) for b in range(11) for c in range(4)]


def readings(current, firing=False):
    return (int(current['pressure']), int(current['heat']), current['throttle'] if firing else 0)


def output(g, kind, inputs):
    """Evaluate the installed player board; a certificate alone supplies no thrust."""
    designs = adventure.state(g.village)['designs']
    snapshot = designs.get(kind)
    if snapshot is None:
        return 0
    cache = getattr(g, 'tower_circuits', None)
    if cache is None:
        cache = g.tower_circuits = {}
    entry = cache.get(kind)
    if entry is None or entry[0] != snapshot:
        entry = [deepcopy(snapshot), Circuit.from_snapshot(snapshot), {}]
        cache[kind] = entry
    if inputs not in entry[2]:
        value, stable = entry[1].evaluate(*inputs)
        entry[2][inputs] = value if stable else 0
    return entry[2][inputs]


def reset_motion(g):
    g.tower_vx = 0.
    g.tower_vy = 0.
    g.tower_grounded = True
    g.tower_firing = False
    g.tower_jump = False


def restore_checkpoint(g):
    current = state(g.village)
    x, y, width = PLATFORMS[current['checkpoint']]
    current['position'] = [x+width/2, float(y)]
    current['pressure'], current['heat'] = float(profile(current)['pressure']), 0.
    reset_motion(g)
    reset_rail(g)


def reset_rail(g):
    """Recovery moves both companions safely; normal landings do not snap the rail."""
    g.tower_rail_y = max(layout.RAIL_TOP, min(layout.RAIL_BOTTOM, state(g.village)['position'][1]))
    g.tower_rail_target = g.tower_rail_y
    g.tower_rail_velocity = 0.
    g.tower_rail_wait = RAIL_DELAY


def update_rail(g, dt):
    """Shannon checks the climb periodically and drives his own service carriage."""
    if not hasattr(g, 'tower_rail_y'):
        reset_rail(g)
    g.tower_rail_wait -= dt
    if g.tower_rail_wait <= 0:
        g.tower_rail_target = max(layout.RAIL_TOP, min(layout.RAIL_BOTTOM, state(g.village)['position'][1]))
        g.tower_rail_wait += RAIL_DELAY
    error = g.tower_rail_target-g.tower_rail_y
    # A resting band avoids mimicking small hops and shuffling at a landing.
    desired = math.copysign(min(RAIL_SPEED, max(0., abs(error)-RAIL_GAP)*3.2), error)
    previous = g.tower_rail_velocity
    change = RAIL_ACCELERATION*dt
    g.tower_rail_velocity += max(-change, min(change, desired-previous))
    position = g.tower_rail_y+(previous+g.tower_rail_velocity)*.5*dt
    g.tower_rail_y = max(layout.RAIL_TOP, min(layout.RAIL_BOTTOM, position))
    if g.tower_rail_y != position:
        g.tower_rail_velocity = 0.


def enter(g):
    if not unlocked(g.village):
        g.toast('Restore the Mosswater archive before following its tower route.')
        return False
    if adventure.active_editor(g):
        adventure.close_editor(g)
    current = state(g.village)
    restore_checkpoint(g)  # Reloads and return visits always start on safe ground.
    g.scene = 'boiler_tower'
    g.tower_time = 0.
    g.tower_circuits = {}
    g.tower_facing = 'east'
    g.adventure_modal = None
    g.adventure_notice_reply = None
    g.adventure_speech_time = 0.
    if not current['visited']:
        current['visited'] = True
        adventure.notice(g, 'Boiler Tower / expedition 02',
            'The archive marks an abandoned condenser tower. A service jetpack waits at the landing. '
            'Build its controller [G], then move with A/D, jump with Space and hold W to thrust. '
            'Coast and counter-steer to brake. Platforms are solid: fly around their edges. '
            'Land to refill; green flags save progress. Watch warning lamps before crossing machinery.',
            'A steam pack with three expired inspection stamps. Let us take the landings seriously.')
    g.save_game()
    return True


def leave(g):
    g.scene = 'town'
    g.town.companion.reset((g.town.player_x, g.town.player_y))
    g.save_game()


def at_station(g):
    if not getattr(g, 'tower_grounded', False):
        return None
    x, y = state(g.village)['position']
    return next((i for i in STATIONS if PLATFORMS[i][0]-10 <= x <= PLATFORMS[i][0]+PLATFORMS[i][2]+10
                 and abs(y-PLATFORMS[i][1]) < 2), None)


def edit(g, vent=False):
    current = state(g.village)
    station = at_station(g)
    if station is None:
        g.toast('Land at a brass maintenance station to revise a controller.')
        return
    if vent and station != VENT_STATION:
        return
    kind = 'tower_vent' if vent else editor_key(current)
    # Carry the player's own previous work forward for revision, never a solution.
    drafts = adventure.state(g.village)['drafts']
    if not vent and current['stage'] and kind not in drafts:
        prior = 'jetpack_' + str(current['stage']-1)
        if prior in drafts:
            drafts[kind] = deepcopy(drafts[prior])
    adventure.enter_editor(g, kind)


def maintenance_task(g):
    current = state(g.village)
    if (at_station(g) == VENT_STATION and editor_key(current) in adventure.state(g.village)['designs']
            and output(g, 'tower_vent', (9, 4, 1)) != 5):
        return 'tower_vent'
    return editor_key(current)


def arrive(g, platform):
    current = state(g.village)
    if platform not in CHECKPOINTS or platform <= current['checkpoint']:
        return
    current['checkpoint'] = platform
    if platform not in STATIONS:
        g.toast('Rest checkpoint saved. Refill here and watch the next hazard cycle.')
        g.save_game()
        return
    reset_motion(g)
    if platform == SUMMIT:
        adventure.notice(g, 'The last landing',
            'The final pressure seal splits after you land. The pack is finished, but the condenser archive '
            'and a gravity return cage are within reach. Press E to recover the archive.',
            'Both feet on the floor. Good. I was counting.')
    else:
        current['stage'] = STATIONS.index(platform)
        current['pressure'], current['heat'] = float(profile(current)['pressure']), 0.
        p = profile(current)
        adventure.notice(g, p['name'] + ' / maintenance landing',
            f"The pack now holds {p['pressure']} pressure. Valve gain must rise to {p['gain']}; "
            f"cut thrust below {p['minimum']} pressure or at {p['heat']} heat. Open G to revise your previous design. "
            + ('The upper steam curtain also needs an exhaust regulator [V].' if platform == VENT_STATION else
               'The next climb has lower thrust. Every platform still refills and cools the pack.'),
            'The seals are wearing out. A new circuit cannot mend them, but it can keep us moving safely.')
    g.save_game()


def interact(g):
    current = state(g.village)
    station = at_station(g)
    if station == SUMMIT:
        if not current['complete']:
            current['complete'] = True
            reset_motion(g)
            unlocks = manufacturing.state(g.village)['unlocks']
            if 'steam_accumulator' not in unlocks:
                unlocks.append('steam_accumulator')
                manufacturing._event(g.village, 'Tower steam accumulator recovered: new production batches take 20% less time.')
            adventure.notice(g, 'Steam accumulator recovered',
                'A lasting workshop upgrade: all new production batches take 20% less time, with the same material costs. '
                'Your jetpack designs are preserved. The pack stays here, permanently broken. '
                'A service plate names a southern lock exchange. '
                'Press E again after closing this panel to take the return cage home.',
                'No signature again. Just a little spare socket, exactly my size.')
            g.save_game()
        else:
            leave(g)
    elif station == 0:
        leave(g)
    elif station is not None:
        edit(g, vent=maintenance_task(g) == 'tower_vent')


def fall(g):
    if developer_mode.enabled(g): return
    current = state(g.village)
    current['falls'] += 1
    hurt(g, 'The safety line caught you. Back at the last landing; 25 health lost.')


def hurt(g, message):
    if developer_mode.enabled(g): return
    health = adventure.state(g.village)
    health['health'] = max(0., health['health']-adventure.HAZARD_DAMAGE)
    health['injuries'] += 1
    restore_checkpoint(g)
    if health['health'] == 0:
        health['health'] = adventure.RESCUE_HEALTH
        leave(g)
        g.toast('Shannon brought you home. Tower checkpoint saved; bread restores health.')
        return
    adventure.speak(g, message)
    g.save_game()


def collide_platforms(g, x, y, nx, ny):
    """Resolve swept body edges against steel tops, undersides and sides."""
    half,height=layout.BODY_HALF,layout.BODY_HEIGHT
    for left,top,width in PLATFORMS:
        right,bottom=left+width,top+layout.PLATFORM_THICKNESS
        if y > top and y-height < bottom:
            if nx > x and x+half <= left and nx+half > left:
                nx=left-half;g.tower_vx=0.
            elif nx < x and x-half >= right and nx-half < right:
                nx=right+half;g.tower_vx=0.
    landed=None
    for i,(left,top,width) in enumerate(PLATFORMS):
        if nx+half <= left or nx-half >= left+width:
            continue
        bottom=top+layout.PLATFORM_THICKNESS
        if ny >= y and y <= top <= ny:
            ny=float(top);g.tower_vy=0.;landed=i
        elif ny < y and y-height >= bottom and ny-height < bottom:
            ny=bottom+height;g.tower_vy=0.
    return nx,ny,landed


def step(g, dt, horizontal=0, thrust=False, jump=False, vertical=None):
    """One physics substep, also exercised by complete traversal tests."""
    current = state(g.village)
    current['hazard_time'] = current.get('hazard_time',0.)+dt
    if developer_mode.enabled(g):
        developer_mode.fly(g, dt, horizontal, -int(thrust) if vertical is None else vertical)
        return
    p = profile(current)
    x, y = current['position']
    if jump and g.tower_grounded:
        g.tower_vy = -JUMP_SPEED
        g.tower_grounded = False
    drive = 0
    if not current['complete'] and current['checkpoint'] != SUMMIT:
        drive = output(g, editor_key(current), readings(current, thrust))
    # Valve range is a physical limit; installed certification enforces safety.
    drive = max(0, min(p['gain']*3, drive))
    g.tower_firing = drive > 0
    if drive:
        current['pressure'] = max(0., current['pressure']-dt*.9)
        current['heat'] = min(10., current['heat']+dt*1.6)
    else:
        current['heat'] = max(0., current['heat']-dt*(4 if g.tower_grounded else .65))
    if g.tower_grounded and not drive:
        current['pressure'] = min(float(p['pressure']), current['pressure']+dt*8)
    # Walking stays immediate, but takeoff carries speed into flight. Air steering
    # changes velocity rather than position; releasing a direction leaves a glide.
    airborne = not g.tower_grounded or drive*p['force'] > GRAVITY
    if airborne:
        previous_vx = g.tower_vx
        if horizontal:
            g.tower_vx = max(-WALK_SPEED, min(WALK_SPEED, previous_vx+horizontal*AIR_ACCELERATION*dt))
            dx = (previous_vx+g.tower_vx)*.5*dt
        else:
            g.tower_vx *= math.exp(-AIR_DRAG*dt)
            dx = (previous_vx-g.tower_vx)/AIR_DRAG
    else:
        g.tower_vx = horizontal*WALK_SPEED
        dx = g.tower_vx*dt
    nx = max(35., min(WIDTH-35., x+dx))
    if nx != x+dx:
        g.tower_vx = 0.
    g.tower_vy = max(-float(p['speed']), min(700., g.tower_vy+(GRAVITY-drive*p['force'])*dt))
    ny = y+g.tower_vy*dt
    g.tower_grounded = False
    # Section shutters open only when the preceding maintenance landing is reached.
    ceiling = layout.ceiling(current['stage'])
    if ny < ceiling:
        ny, g.tower_vy = ceiling, max(0., g.tower_vy)
    # A closed steam curtain occupies the full shaft, including during recovery.
    current['vent_open'] = output(g, 'tower_vent', (9, 4, 1)) == 5
    if not current['vent_open'] and y >= layout.VENT_Y+45 and ny < layout.VENT_Y+45:
        hurt(g, 'That steam curtain is live! 25 health lost. Repair its exhaust controller.')
        return
    nx,ny,landed=collide_platforms(g,x,y,nx,ny)
    g.tower_grounded=landed is not None
    current['position'] = [nx, ny]
    swept=layout.body(x,y).union(layout.body(nx,ny))
    for hazard in layout.HAZARDS:
        if abs(hazard['y']-ny)>400:continue
        reading=layout.hazard_state(hazard,current['hazard_time'])
        if layout.touching(hazard,reading,swept):
            names={'steam':'Steam burst','gear':'Hot gear','piston':'Piston strike'}
            hurt(g,names[hazard['kind']]+': 25 health lost. Watch its timing from the rest platform.')
            return
    if horizontal:
        g.tower_facing = 'east' if horizontal > 0 else 'west'
    if landed is not None:
        g.tower_vx = horizontal*WALK_SPEED
        arrive(g, landed)
    checkpoint_y = PLATFORMS[current['checkpoint']][1]
    if ny > min(HEIGHT+70, checkpoint_y+330):
        fall(g)
    update_rail(g, dt)


def update(g, dt):
    if getattr(g, 'adventure_modal', None):
        return
    dt = max(0., min(.1, dt))
    g.tower_time += dt
    g.adventure_speech_time = max(0., getattr(g, 'adventure_speech_time', 0)-dt)
    keys = pygame.key.get_pressed()
    horizontal = int(keys[pygame.K_d] or keys[pygame.K_RIGHT])-int(keys[pygame.K_a] or keys[pygame.K_LEFT])
    thrust = bool(keys[pygame.K_w] or keys[pygame.K_UP])
    jump, g.tower_jump = g.tower_jump, False
    vertical = int(keys[pygame.K_s] or keys[pygame.K_DOWN])-int(thrust)
    steps = max(1, math.ceil(dt*120))
    for i in range(steps):
        step(g, dt/steps, horizontal, thrust, jump and i == 0, vertical=vertical)
        if getattr(g, 'adventure_modal', None) or g.scene != 'boiler_tower':
            break


def handle_key(g, event):
    if getattr(g, 'adventure_modal', None):
        if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_e):
            adventure.close_notice(g)
        return True
    actions = {pygame.K_e: lambda: interact(g), pygame.K_g: lambda: edit(g),
               pygame.K_v: lambda: edit(g, vent=True), pygame.K_f: lambda: adventure.eat(g),
               pygame.K_BACKSPACE: lambda: recover(g)}
    if event.key in actions:
        actions[event.key]()
    elif event.key == pygame.K_SPACE:
        g.tower_jump = True
    elif event.key == pygame.K_r:
        current = state(g.village)
        current['throttle'] = current['throttle'] % 3+1
    return event.key != pygame.K_ESCAPE


def recover(g):
    # Always available: a bad design or an empty pack cannot strand the player.
    restore_checkpoint(g)
    adventure.speak(g, 'Service line recalled. Pressure refilled at the maintenance landing.')
    g.save_game()


def draw(g):
    import boiler_tower_art
    boiler_tower_art.draw(g)
