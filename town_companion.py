"""Shannon's small walking body and a trail that follows the player's footsteps."""
from collections import deque
import math
import pygame
from ui_theme import INK, COPPER, GOLD, PAPER


class Companion:
    GAP = 48.0

    def __init__(self, player, blocked, facing="south"):
        self.blocked = blocked
        self.phase = self.seconds = 0.0
        self.reset(player, facing)

    def reset(self, player, facing="south"):
        offsets = {"south": (0, -48), "north": (0, 48), "east": (-48, 0), "west": (48, 0)}
        self.position = tuple(player)
        for dx, dy in (offsets[facing], (-36, 28), (36, 28), (0, 48)):
            candidate = (player[0] + dx, player[1] + dy)
            if all(not self.blocked(player[0] + dx * i / 12, player[1] + dy * i / 12) for i in range(13)):
                self.position = candidate
                break
        self.path = deque([self.position, tuple(player)])
        self.last_player = tuple(player)
        self.facing, self.moving = facing, False

    def _append(self, point):
        point = tuple(point)
        if math.dist(self.path[-1], point) < 1e-7:
            return
        if len(self.path) >= 2:
            a, b = self.path[-2], self.path[-1]
            u, v = (b[0] - a[0], b[1] - a[1]), (point[0] - b[0], point[1] - b[1])
            if abs(u[0] * v[1] - u[1] * v[0]) < 1e-7 and u[0] * v[0] + u[1] * v[1] > 0:
                self.path[-1] = point
                return
        self.path.append(point)

    def update(self, player, dt, via=()):
        dt = max(0.0, min(float(dt), .25))
        self.seconds += dt
        self.moving = False
        if math.dist(player, self.last_player) > 160:
            self.reset(player, self.facing)
            return
        for point in (*via, player):
            self._append(point)
        self.last_player = tuple(player)
        length = sum(math.dist(a, b) for a, b in zip(self.path, list(self.path)[1:]))
        travel = min(max(0.0, length - self.GAP), 320 * dt)
        while travel > 1e-7 and len(self.path) > 1:
            a, b = self.path[0], self.path[1]
            distance = math.dist(a, b)
            if distance < 1e-7:
                self.path.popleft()
                continue
            step = min(travel, distance)
            dx, dy = b[0] - a[0], b[1] - a[1]
            self.facing = ("east" if dx > 0 else "west") if abs(dx) > abs(dy) else ("south" if dy > 0 else "north")
            self.position = (a[0] + dx * step / distance, a[1] + dy * step / distance)
            self.path[0] = self.position
            if step >= distance:
                self.path.popleft()
            self.phase += step * .16
            self.moving = True
            travel -= step

    def draw(self, surface, x, y, *, reduced_motion=False, attentive=False):
        """A tiny brass computer with piston feet, a face and a puff of steam."""
        from resident_performance import facing_toward
        seconds = 0. if reduced_motion else self.seconds
        facing = facing_toward(self.position, self.last_player, self.facing) if attentive and not self.moving else self.facing
        pygame.draw.ellipse(surface, (83, 104, 78), (x - 15, y + 16, 30, 8))
        stride = round(math.sin(self.phase) * 4) if self.moving else 0
        bob = -round(abs(math.sin(self.phase)) * 2) if self.moving else 0
        for side in (-1, 1):
            foot_x = x + side * 8 + (stride * side if facing in ("east", "west") else 0)
            foot_y = y + 18 + (stride * side // 2 if facing in ("north", "south") else 0)
            pygame.draw.line(surface, GOLD, (x + side * 8, y + 10), (foot_x, foot_y), 3)
            pygame.draw.circle(surface, (240, 200, 121), (x + side * 8, y + 11), 2)
            pygame.draw.rect(surface, INK, (foot_x - 4, foot_y, 9, 4), border_radius=2)
            pygame.draw.line(surface, (139, 156, 130), (foot_x-3, foot_y), (foot_x+3, foot_y), 1)
        y += bob
        pygame.draw.rect(surface, INK, (x - 10, y - 18, 6, 11), border_radius=1)
        pygame.draw.rect(surface, COPPER, (x - 12, y - 19, 10, 4), border_radius=1)
        puff = (seconds * .8) % 1
        pygame.draw.circle(surface, (220, 218, 190), (x - 7 + round(math.sin(puff * 6) * 2), y - 23 - round(puff * 10)), 2, 1)
        pygame.draw.rect(surface, INK, (x - 15, y - 10, 30, 26), border_radius=4)
        pygame.draw.rect(surface, COPPER, (x - 13, y - 8, 26, 22), border_radius=3)
        pygame.draw.line(surface, (231, 166, 94), (x-11,y-7), (x+10,y-7), 2)
        pygame.draw.line(surface, (118, 75, 49), (x+12,y-5), (x+12,y+11), 2)
        for bx,by in ((-12,-6),(11,-6),(-12,12),(11,12)):
            pygame.draw.rect(surface, (237, 195, 115), (x+bx,y+by,2,2))
        # Small hinged arms give the listening pose a readable body reaction.
        for arm in (-1, 1):
            hand_y = y-3 if attentive and arm == 1 else y+11
            pygame.draw.line(surface, INK, (x+arm*14,y+2),(x+arm*19,hand_y),3)
            pygame.draw.rect(surface, GOLD,(x+arm*19-2,hand_y-1,4,4))
        if facing == "north":
            pygame.draw.rect(surface, GOLD, (x - 9, y - 4, 18, 13), border_radius=2)
            for row in range(3):
                pygame.draw.line(surface, INK, (x - 6, y - 1 + row * 3), (x + 6, y - 1 + row * 3), 1)
            pygame.draw.circle(surface, (65, 95, 80), (x+8,y+9), 3)
            pygame.draw.circle(surface, (223, 180, 105), (x+8,y+9), 2, 1)
        else:
            side = 3 if facing == "east" else -3 if facing == "west" else 0
            pygame.draw.rect(surface, GOLD, (x - 11 + side, y - 6, 22 - abs(side), 15), border_radius=2)
            pygame.draw.rect(surface, (46, 78, 70), (x - 9 + side, y - 4, 18 - abs(side), 11), border_radius=1)
            pygame.draw.line(surface, (81, 115, 95), (x-8+side,y-3), (x+5+side,y-3), 1)
            for eye in (-4, 4):
                pygame.draw.rect(surface, (156, 220, 180), (x + eye + side - 1, y - 2, 2, 1 if seconds % 4.7 > 4.5 else 4 if attentive else 3))
            if attentive:
                pygame.draw.lines(surface,(156,220,180),False,[(x-3+side,y+3),(x+side,y+5),(x+3+side,y+3)])
            else:
                pygame.draw.line(surface, (156, 220, 180), (x - 2 + side, y + 4), (x + 2 + side, y + 4), 1)
            for key in range(4):
                pygame.draw.rect(surface, PAPER, (x - 8 + key * 5, y + 10, 3, 2))
            if side:
                pygame.draw.line(surface,(116,80,48),(x-side*4,y-3),(x-side*4,y+8),2)
