"""Shared shoreline geometry for water artwork and walkable-bank collision."""
import math


def bounds(polygon):
    xs, ys = zip(*polygon)
    left, top = math.floor(min(xs)), math.floor(min(ys))
    return left, top, math.ceil(max(xs)) - left + 1, math.ceil(max(ys)) - top + 1


def contains(point, polygon):
    """Ray crossing with inclusive edges; polygons may be smoothly concave."""
    x, y = point
    inside = False
    ax, ay = polygon[-1]
    for bx, by in polygon:
        # Exact edge positions are water too, avoiding tiny gaps at vertices.
        cross = (x - ax) * (by - ay) - (y - ay) * (bx - ax)
        if abs(cross) < 1e-7 and min(ax, bx) <= x <= max(ax, bx) and min(ay, by) <= y <= max(ay, by):
            return True
        if (ay > y) != (by > y) and x < ax + (y - ay) * (bx - ax) / (by - ay):
            inside = not inside
        ax, ay = bx, by
    return inside


def smooth_polygon(points, passes=2):
    """Round authored banks without introducing random changes between saves."""
    points = tuple((float(x), float(y)) for x, y in points)
    for _ in range(passes):
        rounded = []
        for a, b in zip(points, (*points[1:], points[0])):
            rounded.append((a[0] * .75 + b[0] * .25, a[1] * .75 + b[1] * .25))
            rounded.append((a[0] * .25 + b[0] * .75, a[1] * .25 + b[1] * .75))
        points = tuple(rounded)
    # The same integer contour is rasterized and used for gameplay collision.
    return tuple((round(x), round(y)) for x, y in points)


def stream_polygon(center_x, height, crossing_y, half_width, phase=0):
    """A continuous meandering channel, pinned under its existing bridge."""
    left, right = [], []
    for y in range(-40, height + 81, 24):
        free = max(0., min(1., (abs(y - crossing_y) - 85) / 125))
        bend = (math.sin(y / 143 + phase) * 19 + math.sin(y / 63 + phase) * 6) * free
        width = half_width + (math.sin(y / 107 + phase) * 8 + math.cos(y / 53) * 3) * free
        left.append((round(center_x + bend - width), y))
        right.append((round(center_x + bend + width), y))
    return tuple(left + list(reversed(right)))
