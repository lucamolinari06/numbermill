"""A small modal for a placed constant source; edits preserve its wiring."""
from dataclasses import replace
import pygame
from ui_theme import INK, PAPER, TEAL, COPPER, MUTED, draw_panel, fit_text

FIELD = pygame.Rect(430, 324, 420, 58)
APPLY = pygame.Rect(655, 440, 195, 40)
CANCEL = pygame.Rect(430, 440, 195, 40)


def open_editor(game, pos):
    part = game.circuit.parts.get(pos)
    if part is None or part.kind != 'CONSTANT' or game.device_stack:
        return
    game.constant_editor = {'pos': pos, 'circuit': game.circuit,
                            'text': str(part.value), 'replace': True, 'error': ''}
    game.buttons.clear()


def close(game):
    game.constant_editor = None
    game.buttons.clear()


def apply(game):
    edit = game.constant_editor
    text = edit['text']
    if not text or not text.isascii() or not text.isdecimal() or not 0 <= int(text) <= 65535:
        edit['error'] = 'Enter a whole number from 0 to 65535.'
        return
    part = game.circuit.parts.get(edit['pos'])
    if game.circuit is edit['circuit'] and part and part.kind == 'CONSTANT':
        import workshop_floor
        game.circuit.set_part(edit['pos'], replace(part, value=int(text)))
        workshop_floor.changed(game)
    close(game)


def key(game, event):
    edit = game.constant_editor
    if event.key == pygame.K_ESCAPE:
        close(game)
    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
        apply(game)
    elif event.key == pygame.K_a and getattr(event, 'mod', 0) & pygame.KMOD_CTRL:
        edit['replace'] = True
    elif event.key in (pygame.K_BACKSPACE, pygame.K_DELETE):
        edit['text'] = '' if edit['replace'] or event.key == pygame.K_DELETE else edit['text'][:-1]
        edit['replace'] = False
        edit['error'] = ''
    else:
        char = getattr(event, 'unicode', '')
        if char and char.isascii() and char.isdecimal():
            edit['text'] = ('' if edit['replace'] else edit['text']) + char
            edit['text'] = edit['text'][:6]
            edit['replace'] = False
            edit['error'] = ''


def click(game, point, button):
    if button != 1:
        return
    if APPLY.collidepoint(point):
        apply(game)
    elif CANCEL.collidepoint(point):
        close(game)
    elif FIELD.collidepoint(point):
        game.constant_editor['replace'] = True


def draw(game):
    edit = game.constant_editor
    shade = pygame.Surface(game.screen.get_size(), pygame.SRCALPHA)
    shade.fill((18,29,27,190)); game.screen.blit(shade,(0,0))
    draw_panel(game.screen,(390,230,500,285))
    fit_text(game.screen,game.heading,'Constant number',430,250,420,TEAL)
    fit_text(game.screen,game.small,'Always outputs this number. No inputs needed.',430,290,420,INK)
    pygame.draw.rect(game.screen,TEAL if edit['replace'] else PAPER,FIELD,border_radius=4)
    pygame.draw.rect(game.screen,TEAL,FIELD,2,border_radius=4)
    fit_text(game.screen,game.heading,edit['text'] or '|',446,337,388,PAPER if edit['replace'] else INK)
    fit_text(game.screen,game.small,edit['error'] or 'Whole number: 0 to 65535',430,400,420,COPPER if edit['error'] else MUTED)
    game.buttons.clear()
    game.button(CANCEL,'CANCEL [ESC]',lambda:close(game),small=True)
    game.button(APPLY,'APPLY [ENTER]',lambda:apply(game),small=True)
