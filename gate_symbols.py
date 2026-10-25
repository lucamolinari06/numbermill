"""Distinctive-shape logic symbols, rotated with the game's actual sockets.

The schematic conventions match TI logic diagrams (SN74HC08/32/04/86):
AND's flat input edge, OR's curved input edge, XOR's second input curve,
and the inverter's output bubble. Pin numbers and package outlines are omitted.
"""
from functools import lru_cache
import math
import pygame

GATES = frozenset(('AND', 'OR', 'NOT', 'XOR'))
LESSONS = {'AND': 'Both inputs on', 'OR': 'At least one input on',
           'NOT': 'Inverts the input', 'XOR': 'Exactly one input on'}


def _curve(a, b, c, d, steps=20):
    return [tuple((1-t)**3*a[j] + 3*(1-t)**2*t*b[j] + 3*(1-t)*t*t*c[j] + t**3*d[j]
                  for j in (0, 1)) for t in (i/steps for i in range(steps+1))]


@lru_cache(maxsize=128)
def symbol_image(kind, size, color, rotation=0, floor_ports=False):
    """Return an antialiased icon; floor leads preserve west/south input sockets."""
    scale = max(1, size) * 4 / 100
    image = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
    stroke = max(4, round(size * .16))

    def line(points, closed=False):
        pygame.draw.lines(image, color, closed,
                          [(round(x*scale), round(y*scale)) for x, y in points], stroke)

    if kind == 'NOT':
        line([(25, 22), (25, 78), (70, 50)], True)
        pygame.draw.circle(image, color, (round(77*scale), round(50*scale)), round(7*scale), stroke)
        line([(2, 50), (25, 50)])
        line([(84, 50), (98, 50)])
    else:
        if kind == 'AND':
            arc = [(53 + 29*math.cos(a), 50 + 28*math.sin(a))
                   for a in (-math.pi/2 + i*math.pi/24 for i in range(25))]
            line([(28, 22), *arc, (28, 78)], True)
            input_x = 28
            output_x = 82
        else:
            # The two convex sides meet at the output; the concave input edge
            # is closed independently so XOR can add its characteristic curve.
            top = _curve((26, 22), (53, 21), (73, 28), (85, 50))
            bottom = _curve((85, 50), (73, 72), (53, 79), (26, 78))
            back = _curve((26, 78), (43, 57), (43, 43), (26, 22))
            line(top + bottom + back, True)
            if kind == 'XOR':
                line(_curve((16, 78), (33, 57), (33, 43), (16, 22)))
            input_x = 35
            output_x = 85
        if floor_ports:
            # Leads turn from the unchanged west/south sockets into the
            # standard two input terminals on the left of the gate body.
            line([(2, 50), (9, 50), (9, 35), (input_x, 35)])
            line([(50, 98), (50, 88), (9, 88), (9, 65), (input_x, 65)])
        else:
            line([(2, 35), (input_x, 35)])
            line([(2, 65), (input_x, 65)])
        line([(output_x, 50), (98, 50)])
    image = pygame.transform.rotate(image, -90 * (rotation % 4))
    return pygame.transform.smoothscale(image, (size, size))


def draw_gate(surface, kind, center, size, color, rotation=0, *, floor_ports=False):
    if kind not in GATES:
        return
    image = symbol_image(kind, max(8, int(size)), tuple(color), rotation % 4, floor_ports)
    surface.blit(image, image.get_rect(center=center))
