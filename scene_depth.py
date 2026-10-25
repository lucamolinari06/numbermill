"""Cached transparent scenery, sorted with characters by ground contact."""
from dataclasses import dataclass
import pygame


@dataclass
class Prop:
    depth: float
    rect: pygame.Rect
    image: pygame.Surface

    def draw(self, surface, camera):
        surface.blit(self.image, (self.rect.x-camera[0], self.rect.y-camera[1]))


class Cache:
    def __init__(self, size):
        self.scratch = pygame.Surface(size, pygame.SRCALPHA)
        self.props = []

    def capture(self, bounds, depth, painter):
        """Paint at original world coordinates, preserving seeded artwork."""
        rect = pygame.Rect(bounds).clip(self.scratch.get_rect())
        if not rect.width or not rect.height:
            return
        self.scratch.set_clip(rect)
        self.scratch.fill((0,0,0,0),rect)
        painter(self.scratch)
        self.props.append(Prop(depth,rect,self.scratch.subsurface(rect).copy()))

    def finish(self):
        self.scratch = None
        return tuple(self.props)


def draw(surface, camera, props, actors=()):
    """Actors are (depth, draw_callback); all scenery and actors share one sort."""
    viewport = pygame.Rect(camera, surface.get_size())
    jobs = [(prop.depth, lambda p=prop:p.draw(surface,camera))
            for prop in props if prop.rect.colliderect(viewport)]
    jobs.extend(actors)
    for _,painter in sorted(jobs,key=lambda job:job[0]):
        painter()
