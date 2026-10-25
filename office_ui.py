"""Timber and copper framing shared by the village's office screens."""
import pygame
from ui_theme import PAPER, GOLD, backdrop, fit_text


def frame(surface, title, font, *, subtitle="", small=None):
    backdrop(surface)
    pygame.draw.rect(surface, (17, 32, 33), (28, 28, 1224, 716), border_radius=7)
    pygame.draw.rect(surface, (38, 61, 57), (28, 22, 1224, 716), border_radius=6)
    pygame.draw.rect(surface, (153, 112, 71), (28, 22, 1224, 716), 1, border_radius=6)
    pygame.draw.rect(surface, (43, 71, 67), (41, 37, 1198, 96), border_radius=3)
    pygame.draw.line(surface, (181, 137, 78), (43, 37), (1237, 37), 2)
    pygame.draw.line(surface, (96, 120, 102), (43, 135), (1237, 135))
    pygame.draw.rect(surface, (43, 62, 57), (41, 137, 1198, 586), border_radius=3)
    fit_text(surface, font, title, 60, 48, 630, PAPER)
    if subtitle and small:
        fit_text(surface, small, subtitle, 61, 91, 1120, (213, 220, 190))
    for x in (49, 1230):
        for y in (30, 730):
            pygame.draw.line(surface, GOLD, (x - 4, y), (x + 4, y))


def navigation_rail(surface, rect):
    pygame.draw.rect(surface, (27, 47, 44), rect, border_radius=4)
    pygame.draw.rect(surface, (132, 111, 73), rect, 1, border_radius=4)
