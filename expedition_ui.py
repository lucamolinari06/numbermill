"""Compact field instruments using the same theme as the village HUD."""
import math
import pygame
import ui_theme

PANEL = ui_theme.PAPER
TEXT = ui_theme.INK
DIM = ui_theme.MUTED
MINT = ui_theme.TEAL
AMBER = ui_theme.COPPER


def panel(surface, rect):
    ui_theme.draw_panel(surface, rect)


def health(g, title, subtitle, value):
    panel(g.screen, (20, 20, 300, 84))
    ui_theme.fit_text(g.screen, g.heading, title, 36, 28, 268, ui_theme.TEAL)
    ui_theme.fit_text(g.screen, g.tiny, subtitle, 36, 58, 268, DIM)
    pygame.draw.rect(g.screen, ui_theme.CREAM, (36, 83, 210, 7), border_radius=3)
    pygame.draw.rect(g.screen, (192, 105, 81), (36, 83, round(210 * max(0, min(100, value)) / 100), 7), border_radius=3)
    ui_theme.fit_text(g.screen, g.tiny, str(round(value)) + ' HP', 258, 78, 50, TEXT)


def compass(surface, center, bearing):
    x, y = center
    pygame.draw.circle(surface, ui_theme.CREAM, center, 28)
    pygame.draw.circle(surface, ui_theme.COPPER, center, 27, 2)
    for index in range(16):
        angle = index * math.tau / 16 - math.pi / 2
        length = 5 if index % 4 == 0 else 2
        a = (round(x + math.cos(angle) * (24 - length)), round(y + math.sin(angle) * (24 - length)))
        b = (round(x + math.cos(angle) * 24), round(y + math.sin(angle) * 24))
        pygame.draw.line(surface, DIM, a, b, 1)
    angle = bearing * math.pi / 2 - math.pi / 2
    tip = (round(x + math.cos(angle) * 19), round(y + math.sin(angle) * 19))
    left = (round(x + math.cos(angle + 2.3) * 9), round(y + math.sin(angle + 2.3) * 9))
    right = (round(x + math.cos(angle - 2.3) * 9), round(y + math.sin(angle - 2.3) * 9))
    pygame.draw.polygon(surface, AMBER, (tip, left, center, right))
    pygame.draw.circle(surface, TEXT, center, 3)


def meter(g, label, value, maximum, y, color, threshold=None):
    ui_theme.fit_text(g.screen, g.tiny, label, 970, y, 72, DIM)
    rect = pygame.Rect(1047, y + 5, 137, 7)
    pygame.draw.rect(g.screen, ui_theme.CREAM, rect, border_radius=2)
    fill = rect.copy()
    fill.width = round(rect.width * max(0, min(maximum, value)) / maximum)
    pygame.draw.rect(g.screen, color, fill, border_radius=2)
    if threshold is not None:
        x = rect.left + round(rect.width * threshold / maximum)
        pygame.draw.line(g.screen, TEXT, (x, rect.top - 3), (x, rect.bottom + 3), 1)
    ui_theme.fit_text(g.screen, g.tiny, f'{value:.1f}', 1195, y, 43, TEXT)


def controls(g, text, width=710):
    panel(g.screen, (20, 712, width, 30))
    ui_theme.fit_text(g.screen, g.tiny, text, 32, 720, width - 24, DIM)
