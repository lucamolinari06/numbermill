"""Shared field journal and resumable conversations over the current game scene."""
import pygame
import opening_chapter as story
from ui_theme import PAPER, CREAM, INK, MUTED, TEAL, COPPER, GOLD, draw_panel, fit_text, wrapped_text
from dialogue import portrait

JOURNAL_BUTTON = pygame.Rect(466, 18, 348, 39)
RETURN_BUTTON = pygame.Rect(435, 650, 410, 44)
BOOK = pygame.Rect(130, 82, 1020, 608)
SCENE_PANEL = pygame.Rect(220, 320, 840, 370)
PAGE_SIZE = 5


def active(g):
    return getattr(g, 'chapter_view', None) is not None


def can_open(g):
    return (g.scene in ('town', 'factory', 'adventure', 'boiler_tower') and
            not (g.scene in ('adventure', 'boiler_tower') and getattr(g, 'adventure_modal', None)) and
            not (g.scene == 'factory' and (getattr(g, 'factory_dialog', None) or
                 getattr(g, 'factory_placing', None) or getattr(g, 'factory_moving', None) is not None)))


def open_journal(g):
    if not can_open(g):
        return
    data = story.observe(g.village)
    keys = evidence_keys(g)
    first = next((i for i, key in enumerate(keys) if not data['evidence'][key]['read']), 0)
    g.chapter_view = {'mode': 'journal', 'tab': 'Evidence', 'index': first}
    g.shannon.open = False
    g.shannon.page = None
    g.town_dialogue = None
    g.buttons.clear()
    g.focus_index = -1
    read_selected(g)


def close(g):
    g.chapter_view = None
    g.buttons.clear()
    g.focus_index = -1
    g.save_game()


def evidence_keys(g):
    found = story.observe(g.village)['evidence']
    return [key for key in story.EVIDENCE if key in found]


def items(g):
    return evidence_keys(g) if g.chapter_view['tab'] == 'Evidence' else story.available_scenes(g.village)


def read_selected(g):
    if g.chapter_view['tab'] == 'Evidence':
        key = items(g)[g.chapter_view['index']]
        story.state(g.village)['evidence'][key]['read'] = True
        g.save_game()


def choose(g, index):
    g.chapter_view['index'] = max(0, min(len(items(g)) - 1, index))
    g.buttons.clear()
    read_selected(g)


def switch_tab(g, tab):
    g.chapter_view.update(tab=tab, index=0)
    g.buttons.clear()
    read_selected(g)


def can_start_scene(g, key):
    return (key in story.available_scenes(g.village) and
            (g.scene in ('town', 'factory') or
             story.state(g.village)['scenes'].get(key, {}).get('complete', False)))


def start_scene(g, key):
    if not can_start_scene(g, key):
        return False
    progress = story.scene_progress(g.village, key)
    g.chapter_view = {'mode': 'scene', 'key': key,
                      'index': 0 if progress.get('complete') else progress['page'],
                      'replay': bool(progress.get('complete'))}
    g.shannon.open = False
    g.shannon.page = None
    g.town_dialogue = None
    g.buttons.clear()
    g.focus_index = -1
    g.save_game()
    return True


def advance(g, direction=1):
    view = g.chapter_view
    key = view['key']
    count = len(story.pages(g.village, key))
    index = view['index'] + direction
    if index >= count:
        if not view['replay']:
            story.complete_scene(g.village, key)
        close(g)
        g.toast('Conversation remembered in the field journal [B].')
        return
    view['index'] = max(0, index)
    if not view['replay']:
        story.scene_progress(g.village, key)['page'] = view['index']
    g.buttons.clear()
    g.save_game()


def key(g, event):
    if not active(g):
        return False
    value = event.key
    if value in (pygame.K_ESCAPE, pygame.K_b):
        close(g)
    elif g.chapter_view['mode'] == 'scene':
        if value in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_RIGHT):
            advance(g)
        elif value == pygame.K_LEFT:
            advance(g, -1)
    else:
        if value == pygame.K_TAB:
            switch_tab(g, 'Moments' if g.chapter_view['tab'] == 'Evidence' else 'Evidence')
        elif value in (pygame.K_DOWN, pygame.K_UP):
            choose(g, g.chapter_view['index'] + (1 if value == pygame.K_DOWN else -1))
        elif value in (pygame.K_RIGHT, pygame.K_LEFT):
            choose(g, g.chapter_view['index'] + (PAGE_SIZE if value == pygame.K_RIGHT else -PAGE_SIZE))
        elif value in (pygame.K_RETURN, pygame.K_KP_ENTER) and g.chapter_view['tab'] == 'Moments':
            start_scene(g, items(g)[g.chapter_view['index']])
    return True


def click(g, point, button):
    if not active(g):
        return False
    if button == 1:
        for rect, action in reversed(g.buttons):
            if rect.collidepoint(point):
                action()
                break
    return True


def draw_prompt(g):
    if g.town_dialogue or g.shannon.open:
        return
    data = story.observe(g.village)
    unread = sum(not row['read'] for row in data['evidence'].values())
    label = 'Field journal [B]' + (f' / {unread} new' if unread else '')
    g.button(JOURNAL_BUTTON, label, lambda: open_journal(g), small=True)
    pending = story.pending(g.village)
    if pending:
        label = {'opening': 'Talk with Shannon [Enter]',
                 'mosswater_home': 'Mosswater homecoming [Enter]',
                 'tower_home': 'Tower homecoming [Enter]',
                 'well_evening': 'An afternoon by the well [Enter]'}[pending]
        g.button(RETURN_BUTTON, label, lambda: start_scene(g, pending), small=True)


def artifact(surface, key, center):
    """Small pixel silhouettes, rendered at an integer scale like the world art."""
    tile = pygame.Surface((42, 42), pygame.SRCALPHA)
    if key in ('accumulator', 'tower_home'):
        pygame.draw.rect(tile, INK, (10, 4, 24, 34))
        pygame.draw.rect(tile, COPPER, (12, 5, 20, 30))
        pygame.draw.rect(tile, CREAM, (15, 8, 14, 23))
        for y in (9, 28):
            pygame.draw.rect(tile, GOLD, (9, y, 26, 3))
        pygame.draw.circle(tile, INK, (22, 17), 6)
        pygame.draw.circle(tile, PAPER, (22, 17), 4)
        pygame.draw.line(tile, COPPER, (22, 17), (24, 14))
        pygame.draw.lines(tile, COPPER, False, ((10, 33), (5, 33), (5, 39)), 3)
    elif key in ('receiver', 'lens', 'mosswater_home'):
        pygame.draw.rect(tile, INK, (6, 13, 30, 21))
        pygame.draw.rect(tile, COPPER, (8, 14, 26, 18))
        pygame.draw.circle(tile, GOLD, (21, 23), 9)
        pygame.draw.circle(tile, TEAL, (21, 23), 6)
        pygame.draw.line(tile, CREAM, (18, 22), (22, 18), 2)
        pygame.draw.lines(tile, INK, False, ((11, 13), (11, 7), (27, 3)), 2)
    else:
        pygame.draw.rect(tile, INK, (7, 5, 28, 33))
        pygame.draw.rect(tile, COPPER, (8, 6, 26, 30))
        pygame.draw.rect(tile, PAPER, (13, 8, 18, 26))
        for y in (14, 19, 24, 29):
            pygame.draw.line(tile, TEAL, (16, y), (27, y))
        pygame.draw.rect(tile, GOLD, (11, 5, 2, 32))
    image = pygame.transform.scale(tile, (84, 84))
    surface.blit(image, image.get_rect(center=center))


def draw(g):
    if not active(g):
        return
    shade = pygame.Surface(g.screen.get_size(), pygame.SRCALPHA)
    shade.fill((20, 39, 40, 185))
    g.screen.blit(shade, (0, 0))
    g.buttons.clear()
    if g.chapter_view['mode'] == 'scene':
        draw_scene(g)
    else:
        draw_journal(g)


def draw_journal(g):
    view = g.chapter_view
    keys = items(g)
    index = max(0, min(len(keys) - 1, view['index']))
    selected = keys[index]
    start = index // PAGE_SIZE * PAGE_SIZE
    draw_panel(g.screen, BOOK)
    fit_text(g.screen, g.heading, 'Boole & Shannon / Field journal', 163, 105, 770, TEAL)
    g.button((984, 104, 133, 35), 'Close [Esc]', lambda: close(g), small=True)
    for i, tab in enumerate(('Evidence', 'Moments')):
        g.button((164 + i * 162, 155, 152, 35), tab, lambda t=tab: switch_tab(g, t),
                 active=view['tab'] == tab, small=True)
    fit_text(g.screen, g.tiny, 'Reading pauses the village and expeditions.', 568, 164, 540, MUTED)
    pygame.draw.line(g.screen, COPPER, (509, 212), (509, 618))
    data = story.observe(g.village)
    for offset, item in enumerate(keys[start:start + PAGE_SIZE]):
        y = 215 + offset * 72
        title = (story.EVIDENCE if view['tab'] == 'Evidence' else story.SCENES)[item][0]
        g.button((163, y, 323, 39), title, lambda n=start + offset: choose(g, n),
                 active=item == selected, small=True)
        if view['tab'] == 'Evidence':
            note = 'Recorded observation' if data['evidence'][item]['read'] else 'New observation'
        else:
            row = data['scenes'].get(item, {})
            note = 'Remembered / replay' if row.get('complete') else 'Continue conversation' if row.get('page') else 'Available conversation'
        fit_text(g.screen, g.tiny, note, 173, y + 44, 300, MUTED)
    if view['tab'] == 'Evidence':
        title, source, observation, question = story.EVIDENCE[selected]
        artifact(g.screen, selected, (1067, 242))
        y = wrapped_text(g.screen, g.heading, title, 540, 215, 460, TEAL, line_height=29)
        fit_text(g.screen, g.small, source, 540, y + 9, 470, COPPER)
        fit_text(g.screen, g.small, 'WHAT WE KNOW', 540, 315, 530, TEAL)
        end = wrapped_text(g.screen, g.font, observation, 540, 345, 560, INK, line_height=25)
        fit_text(g.screen, g.small, 'WHAT WE ARE ASKING', 540, max(480, end + 23), 560, TEAL)
        wrapped_text(g.screen, g.font, question, 540, max(510, end + 53), 560, INK, line_height=25)
    else:
        title, place, _ = story.SCENES[selected]
        artifact(g.screen, selected, (1065, 248))
        wrapped_text(g.screen, g.heading, title, 540, 215, 460, TEAL, line_height=29)
        fit_text(g.screen, g.small, place, 540, 287, 550, COPPER)
        progress = data['scenes'].get(selected, {})
        detail = ('A remembered conversation. Revisit it whenever you like.' if progress.get('complete') else
                  'Take a moment together. You can leave at any page and continue later.')
        wrapped_text(g.screen, g.font, detail, 540, 344, 550, INK, line_height=25)
        label = 'Replay conversation [Enter]' if progress.get('complete') else 'Continue [Enter]' if progress.get('page') else 'Begin conversation [Enter]'
        home = can_start_scene(g, selected)
        g.button((540, 480, 555, 43), label if home else 'Continue when back in Copperside',
                 lambda: start_scene(g, selected), small=True, enabled=home)
        fit_text(g.screen, g.small, 'Your place is saved. Completed moments can be replayed.', 540, 548, 550, MUTED)
    g.button((163, 628, 145, 35), 'Previous', lambda: choose(g, index - PAGE_SIZE), small=True, enabled=start > 0)
    g.button((341, 628, 145, 35), 'Next', lambda: choose(g, index + PAGE_SIZE), small=True, enabled=start + PAGE_SIZE < len(keys))
    fit_text(g.screen, g.tiny, 'Tab: section   Up/Down: entry   Left/Right: page', 540, 640, 555, MUTED)


def draw_scene(g):
    view = g.chapter_view
    scene = view['key']
    title, place, _ = story.SCENES[scene]
    rows = story.pages(g.village, scene)
    who, paragraph = rows[view['index']]
    draw_panel(g.screen, (350, 133, 580, 136))
    artifact(g.screen, scene, (410, 196))
    wrapped_text(g.screen, g.heading, title, 467, 156, 430, TEAL, line_height=29)
    fit_text(g.screen, g.small, place, 467, 226, 430, COPPER)
    draw_panel(g.screen, SCENE_PANEL)
    portrait(g.screen, who, (253, 345, 44, 44))
    fit_text(g.screen, g.heading, who, 315, 350, 600, TEAL)
    fit_text(g.screen, g.small, f"{view['index'] + 1} / {len(rows)}", 940, 356, 85, MUTED)
    pygame.draw.line(g.screen, COPPER, (253, 404), (1026, 404))
    wrapped_text(g.screen, g.font, paragraph, 253, 431, 770, INK, line_height=29)
    fit_text(g.screen, g.tiny, 'Take your time. Your place is saved.', 253, 588, 750, MUTED)
    g.button((253, 630, 132, 38), 'Back', lambda: advance(g, -1), small=True, enabled=view['index'] > 0)
    g.button((399, 630, 230, 38), 'Continue later [Esc]', lambda: close(g), small=True)
    label = 'Finish [Enter]' if view['index'] == len(rows) - 1 else 'Next [Enter]'
    g.button((758, 630, 268, 38), label, lambda: advance(g), active=True, small=True)
