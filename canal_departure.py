"""Copperside's southern launch: repair, test and depart through real controls."""
import math
import pygame

import canal_progress
from ui_theme import INK, MUTED, PAPER, TEAL, COPPER, GOLD, draw_panel, fit_text, wrapped_text

LANDING = (1120, 1465)
RETURN_POSITION = (1120, 1430)
PANEL = pygame.Rect(255, 174, 770, 440)


def nearby(g):
    return math.dist((g.town.player_x, g.town.player_y), LANDING) < 100


def open_panel(g):
    if g.scene != 'town' or not nearby(g):
        return
    g.canal_departure_open = True
    g.canal_departure_message = ''
    g.town_dialogue = None
    g.shannon.open = False
    g.buttons.clear()


def close(g):
    g.canal_departure_open = False
    g.buttons.clear()


def repair(g):
    ok, message = canal_progress.repair(g.village)
    g.canal_departure_message = message
    g.toast(message)
    if ok:
        g.save_game()


def build(g):
    if not canal_progress.unlocked(g.village) or not canal_progress.state(g.village)['boat_repaired']:
        return
    import adventure
    close(g)
    adventure.enter_editor(g, canal_progress.KIND)


def travel(g):
    if not canal_progress.can_travel(g.village):
        g.canal_departure_message = canal_progress.status(g.village)
        return
    import canal_settlement
    close(g)
    canal_settlement.enter(g)


def handle_key(g, event):
    if not getattr(g, 'canal_departure_open', False):
        return False
    if event.key == pygame.K_ESCAPE:
        close(g)
    elif event.key == pygame.K_r:
        repair(g)
    elif event.key == pygame.K_g:
        build(g)
    elif event.key in (pygame.K_e, pygame.K_RETURN, pygame.K_KP_ENTER):
        travel(g)
    return True


def click(g, pos, button):
    if getattr(g, 'canal_departure_open', False):
        if button == 1:
            for rect, action in reversed(g.buttons):
                if rect.collidepoint(pos):
                    action()
                    break
        return True
    if nearby(g) and not g.town_dialogue and not g.shannon.open and pygame.Rect(460, 659, 360, 42).collidepoint(pos):
        if button == 1:
            open_panel(g)
        return True
    return False


def draw_world(surface, camera, village, seconds=0.):
    """The launch is moored in existing water beside the existing southern pier."""
    from canal_art import boat
    ox, oy = camera
    current = getattr(village, 'manufacturing', {}).get('canal', {})
    repaired = current.get('boat_repaired', False)
    pygame.draw.line(surface, (109, 87, 57), (1183-ox, 1492-oy), (1210-ox, 1500-oy), 2)
    boat(surface, 1268-ox, 1502-oy, repaired=repaired, seconds=0.)
    # Two mooring posts and a modest waymarker, clear of the walking lane.
    for x in (1181, 1190):
        pygame.draw.rect(surface, (87, 70, 51), (x-ox, 1440-oy, 7, 31))
        pygame.draw.rect(surface, (186, 153, 96), (x-ox-1, 1439-oy, 9, 4))
    pygame.draw.rect(surface, (76, 68, 51), (1193-ox, 1404-oy, 6, 41))
    pygame.draw.rect(surface, (220, 200, 153), (1174-ox, 1401-oy, 65, 24))
    pygame.draw.rect(surface, (112, 94, 63), (1174-ox, 1401-oy, 65, 24), 2)
    pygame.draw.line(surface, TEAL, (1185-ox, 1413-oy), (1226-ox, 1413-oy), 3)
    pygame.draw.polygon(surface, TEAL, [(1228-ox,1413-oy),(1217-ox,1407-oy),(1217-ox,1419-oy)])


def draw(g):
    if not getattr(g, 'canal_departure_open', False):
        if nearby(g) and not g.town_dialogue and not g.shannon.open:
            g.button((460, 659, 360, 42), 'Southern landing  [E]', lambda: open_panel(g), small=True)
        return
    shade = pygame.Surface(g.screen.get_size(), pygame.SRCALPHA)
    shade.fill((17, 32, 32, 175))
    g.screen.blit(shade, (0, 0))
    draw_panel(g.screen, PANEL)
    g.buttons.clear()
    fit_text(g.screen, g.heading, 'The southern launch', 287, 197, 700, TEAL)
    fit_text(g.screen, g.small, 'A passage to Reedhaven', 287, 232, 700, COPPER)
    unlocked = canal_progress.unlocked(g.village)
    repaired = canal_progress.state(g.village)['boat_repaired']
    ready = canal_progress.can_travel(g.village)
    copy = ('The canal beyond Copperside leads to the lock exchange named on the old service plate. '
            'This small steam launch can make the journey again.' if unlocked else
            'An idle launch waits beside the southern pier. Complete the Mosswater archive and '
            'Boiler Tower expeditions to recover the tools and southern route lead needed to restore it.')
    wrapped_text(g.screen, g.font, copy, 287, 271, 700, INK, line_height=25, max_lines=3)
    rows = (
        ('Recovered machinery', 'Cutter blueprint and steam accumulator' if unlocked else 'Complete both expeditions'),
        ('Drive assembly', 'Replacement gear fitted' if repaired else 'Requires 1 manufactured precision gear'),
        ('Departure controller', 'All operating conditions verified' if ready else 'Build and test the steam-feed circuit'),
    )
    for i, (label, value) in enumerate(rows):
        y = 357+i*36
        fit_text(g.screen, g.small, label, 287, y, 205, TEAL)
        fit_text(g.screen, g.small, value, 505, y, 480, INK)
    note = getattr(g, 'canal_departure_message', '') or canal_progress.status(g.village)
    wrapped_text(g.screen, g.small, note, 287, 470, 700, MUTED, line_height=21, max_lines=2)
    if not repaired:
        g.button((287, 546, 222, 40), 'Fit precision gear  [R]', lambda: repair(g), small=True, enabled=unlocked)
    else:
        g.button((287, 546, 222, 40), 'Edit controller  [G]', lambda: build(g), small=True, enabled=unlocked)
    g.button((521, 546, 252, 40), 'Travel to Reedhaven  [E]', lambda: travel(g), small=True, active=ready, enabled=ready)
    g.button((785, 546, 208, 40), 'Back  [Esc]', lambda: close(g), small=True)
