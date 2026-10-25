"""Startup artwork carousel; no game or save state belongs here."""
from math import cos, pi
from pathlib import Path

import pygame
import ui_theme


class OpeningScreen:
    HOLD = 6.0
    CROSSFADE = 2.0
    EXIT_FADE = 0.5

    def __init__(self, directory, reduced_motion=False):
        self.paths = sorted(Path(directory).glob("*.png"))
        self.reduced_motion = reduced_motion
        self.elapsed = 0.0
        self.departure = None
        self.finished = False
        self.cache = {}

    def begin(self):
        if self.departure is None:
            self.departure = 0.0

    def update(self, dt):
        dt = min(max(dt, 0.0), 0.1)
        if not self.reduced_motion:
            self.elapsed += dt
        if self.departure is not None:
            self.departure += dt
            self.finished = self.reduced_motion or self.departure >= self.EXIT_FADE

    def frame(self):
        cycle = self.HOLD + self.CROSSFADE
        phase = self.elapsed % cycle
        index = int(self.elapsed // cycle) % max(1, len(self.paths))
        blend = max(0.0, (phase - self.HOLD) / self.CROSSFADE)
        return index, (1 - cos(pi * blend)) / 2

    def image(self, index, size):
        key = (index, size)
        if key not in self.cache:
            try:
                source = pygame.image.load(str(self.paths[index])).convert()
                # Cover the canvas, trimming edges instead of adding borders.
                ratio = max(size[0] / source.get_width(), size[1] / source.get_height())
                fitted = pygame.transform.scale(source, (round(source.get_width() * ratio),
                                                         round(source.get_height() * ratio)))
                surface = pygame.Surface(size)
                surface.fill((12, 21, 24))
                surface.blit(fitted, fitted.get_rect(center=(size[0] // 2, size[1] // 2)))
            except (OSError, pygame.error):
                surface = pygame.Surface(size)
                surface.fill((12, 21, 24))
            self.cache[key] = surface
        return self.cache[key]

    def draw(self, screen, font, title_font=None):
        size = screen.get_size()
        index, blend = self.frame()
        screen.fill((12, 21, 24))
        if self.paths:
            following = (index + 1) % len(self.paths)
            keep = {(index, size), (following, size)}
            self.cache = {key: value for key, value in self.cache.items() if key in keep}
            screen.blit(self.image(index, size), (0, 0))
            next_image = self.image(following, size)
            if blend:
                next_image.set_alpha(round(255 * blend))
                screen.blit(next_image, (0, 0))
                next_image.set_alpha(None)
        # Keep the existing mill seal and wordmark legible on every backdrop.
        title = (title_font or font).render("NUMBERMILL", False, (249, 234, 195))
        brand = pygame.Surface((title.get_width() + 120, 96), pygame.SRCALPHA)
        pygame.draw.rect(brand, (12, 29, 31, 195), brand.get_rect(), border_radius=5)
        ui_theme.mill_seal(brand, (47, 48), 27)
        brand.blit(title, title.get_rect(midleft=(98, 48)))
        screen.blit(brand, (28, 28))
        # A subtle lower veil keeps the prompt readable over every scene.
        veil = pygame.Surface(size, pygame.SRCALPHA)
        for y in range(size[1] * 3 // 4, size[1]):
            alpha = round(140 * (y - size[1] * .75) / (size[1] * .25))
            pygame.draw.line(veil, (8, 16, 20, alpha), (0, y), (size[0], y))
        screen.blit(veil, (0, 0))
        opacity = 255 if self.reduced_motion else round(105 + 150 * (1 - cos(2 * pi * self.elapsed / 3.5)) / 2)
        prompt = font.render("Press any key to begin", False, (249, 234, 195))
        prompt.set_alpha(opacity)
        screen.blit(prompt, prompt.get_rect(center=(size[0] // 2, round(size[1] * .90))))
        if self.departure is not None:
            veil.fill((8, 16, 20, round(255 * min(1, self.departure / self.EXIT_FADE))))
            screen.blit(veil, (0, 0))
