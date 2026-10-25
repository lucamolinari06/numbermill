"""Window presentation and player preferences, independent of game saves."""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import pygame
import window_display

LOGICAL_SIZE = (1280, 760)
DEFAULTS = {"fullscreen": False, "smooth_scaling": False, "reduced_motion": False,
            "window_size": [1280, 760], "last_slot": None}


def window_icon():
    icon = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.circle(icon, (28, 64, 65), (16, 16), 16)
    pygame.draw.circle(icon, (237, 220, 167), (16, 16), 13)
    pygame.draw.circle(icon, (164, 101, 55), (16, 16), 12, 2)
    for spoke in range(8):
        angle = spoke * math.tau / 8
        tip = (round(16 + 11 * math.cos(angle)), round(16 + 11 * math.sin(angle)))
        pygame.draw.line(icon, (164, 101, 55), (16, 16), tip, 2)
    pygame.draw.circle(icon, (211, 166, 72), (16, 16), 4)
    return icon


def load_preferences(path: Path):
    result = {**DEFAULTS, "window_size": list(LOGICAL_SIZE)}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return result
    if not isinstance(data, dict):
        return result
    for key in ("fullscreen", "smooth_scaling", "reduced_motion"):
        if isinstance(data.get(key), bool):
            result[key] = data[key]
    size = data.get("window_size")
    if isinstance(size, list) and len(size) == 2 and all(type(n) is int for n in size):
        result["window_size"] = [max(640, min(3840, size[0])), max(380, min(2160, size[1]))]
    if type(data.get("last_slot")) is int and 1 <= data["last_slot"] <= 5:
        result["last_slot"] = data["last_slot"]
    return result


def prepare_display():
    # Must precede pygame.init(): let the game scale once at real monitor pixels,
    # instead of having Windows stretch an already scaled low-resolution bitmap.
    os.environ.setdefault("SDL_WINDOWS_DPI_AWARENESS", "permonitorv2")


def viewport_rect(window_size, logical_size=LOGICAL_SIZE, integer=False):
    width, height = window_size
    scale = min(max(1, width) / logical_size[0], max(1, height) / logical_size[1])
    if integer and scale >= 1:
        scale = max(1, math.floor(scale))
    fitted = (max(1, round(logical_size[0] * scale)), max(1, round(logical_size[1] * scale)))
    return pygame.Rect((width - fitted[0]) // 2, (height - fitted[1]) // 2, *fitted)


def logical_position(position, window_size, logical_size=LOGICAL_SIZE, integer=False):
    rect = viewport_rect(window_size, logical_size, integer)
    if not rect.collidepoint(position):
        return (-1000, -1000)
    return (int((position[0] - rect.x) * logical_size[0] / rect.width),
            int((position[1] - rect.y) * logical_size[1] / rect.height))


class Viewport:
    """Render at a stable logical size and map all pointer input through the same fit."""

    def __init__(self, preferences):
        self.preferences = preferences
        self.window = None
        self.full_active = False
        self.windowed_position = None
        self.canvas = pygame.Surface(LOGICAL_SIZE)
        self.configure()

    def configure(self):
        headless = pygame.display.get_driver() == "dummy"
        full = self.preferences["fullscreen"] and not headless
        size = tuple(self.preferences["window_size"])
        native = window_display.geometry() if not headless else None
        if full and not self.full_active and native and native["window"]:
            self.windowed_position = native["window"].topleft
        if not headless:
            desktop = native["monitor"].size if native else pygame.display.get_desktop_sizes()[0]
            size = desktop if full else (min(size[0], max(640, desktop[0] - 64)),
                                         min(size[1], max(380, desktop[1] - 100)))
        flags = (pygame.NOFRAME if native else pygame.FULLSCREEN) if full else pygame.RESIZABLE
        self.window = pygame.display.set_mode(size, flags)
        if native:
            if full:
                window_display.position(native["monitor"], resize=True)
            elif self.full_active:
                actual = window_display.geometry()["window"]
                actual.topleft = self.windowed_position or native["work"].topleft
                window_display.position(actual.clamp(native["work"]))
        self.full_active = full
        # A borderless desktop-sized window avoids changing monitor modes
        # and preserves Pygame's software-surface ownership on Windows.
        pygame.event.clear(pygame.VIDEORESIZE)

    def resize(self, size):
        if self.preferences["fullscreen"]:
            return
        size = (max(640, int(size[0])), max(380, int(size[1])))
        if self.window.get_size() != size:
            self.window = pygame.display.set_mode(size, pygame.RESIZABLE)
        self.preferences["window_size"] = list(size)

    def pointer(self, position):
        if self.preferences["fullscreen"]:
            width, height = self.window.get_size()
            return (int(position[0] * LOGICAL_SIZE[0] / width),
                    int(position[1] * LOGICAL_SIZE[1] / height))
        return logical_position(position, self.window.get_size(), integer=self.sharp_fullscreen())

    def sharp_fullscreen(self):
        return self.preferences["fullscreen"] and not self.preferences["smooth_scaling"]

    def present(self):
        self.window = pygame.display.get_surface()
        if self.window is None:
            return
        rect = (self.window.get_rect() if self.preferences["fullscreen"] else
                viewport_rect(self.window.get_size()))
        self.window.fill((16, 28, 30))
        if rect.size == LOGICAL_SIZE:
            self.window.blit(self.canvas, rect)
        else:
            scale = pygame.transform.smoothscale if self.preferences["smooth_scaling"] else pygame.transform.scale
            self.window.blit(scale(self.canvas, rect.size), rect)
        pygame.display.flip()


CONTROL_GROUPS = (
    ("Around Copperside", (("WASD / Arrows", "Walk"), ("E", "Use a doorway or counter"),
                           ("Click a resident", "Talk"), ("H", "Shannon's menu"),
                           ("M / L / J", "Map / Ledger / Jobs"), ("B / 6 in conversation", "Journal / Journey topic"))),
    ("Circuit bench", (("Left click", "Place parts and route wires"), ("Right click", "Cancel or disconnect"),
                       ("R / Y", "Rotate / Erase"), ("T", "Test the current design"),
                       ("Space / .", "Run or pause / Single step"))),
    ("Mosswater", (("R / Tab", "Receiver bearing / Channel"), ("Space", "Scan"),
                   ("G", "Receiver circuit"), ("E", "Inspect or operate"), ("F", "Eat bread to heal"))),
    ("Boiler Tower", (("A / D", "Steer; reverse to brake"), ("Space / W", "Jump / Thrust"),
                      ("R", "Change throttle"), ("E / G / V", "Station / Jetpack / Exhaust"),
                      ("Backspace / F", "Recall / Heal"))),
)


def draw_settings(game):
    import ui_theme as ui
    shade = pygame.Surface(LOGICAL_SIZE, pygame.SRCALPHA)
    shade.fill((12, 29, 31, 210))
    game.screen.blit(shade, (0, 0))
    ui.draw_panel(game.screen, (280, 130, 720, 510))
    ui.fit_text(game.screen, game.heading, "Settings", 320, 159, 580, ui.TEAL)
    ui.fit_text(game.screen, game.small, "Display & comfort", 320, 196, 580, ui.MUTED)
    rows = (("Fullscreen", "fullscreen", "F11 also switches display mode."),
            ("Smooth scaling", "smooth_scaling", "Off: sharp pixels. On: softened scaling."),
            ("Reduced motion", "reduced_motion", "Calms decoration; gameplay warnings stay active."))
    for i, (label, key, detail) in enumerate(rows):
        y = 249 + i * 83
        ui.fit_text(game.screen, game.font, label, 320, y, 420)
        ui.fit_text(game.screen, game.small, detail, 320, y + 28, 450, ui.MUTED)
        game.button((805, y - 1, 150, 42), "On" if game.settings[key] else "Off",
                    lambda k=key: game.toggle_preference(k), active=game.settings[key], small=True)
    game.button((320, 529, 230, 44), "Controls", lambda: setattr(game, "controls_open", True), small=True)
    game.button((725, 563, 230, 44), "Done  [Esc]", game.close_settings, active=True, small=True)
    ui.fit_text(game.screen, game.tiny, "Settings save automatically.", 320, 578, 360, ui.MUTED)


def draw_controls(game):
    import ui_theme as ui
    shade = pygame.Surface(LOGICAL_SIZE, pygame.SRCALPHA)
    shade.fill((12, 29, 31, 215))
    game.screen.blit(shade, (0, 0))
    ui.draw_panel(game.screen, (100, 76, 1080, 622))
    ui.fit_text(game.screen, game.heading, "Controls", 140, 104, 500, ui.TEAL)
    for i, (title, entries) in enumerate(CONTROL_GROUPS):
        x, y = 140 + (i % 2) * 530, 163 + (i // 2) * 221
        ui.fit_text(game.screen, game.heading, title, x, y, 440, ui.TEAL)
        pygame.draw.line(game.screen, (210, 189, 149), (x, y + 38), (x + 445, y + 38))
        for j, (key, action) in enumerate(entries):
            yy = y + 52 + j * 27
            ui.fit_text(game.screen, game.small, key, x, yy, 166, ui.COPPER)
            ui.fit_text(game.screen, game.small, action, x + 174, yy, 278, ui.INK)
    ui.fit_text(game.screen, game.small, "Esc closes the current panel or pauses.  F11 toggles fullscreen.", 140, 638, 760, ui.MUTED)
    game.button((959, 630, 180, 42), "Back  [Esc]", lambda: setattr(game, "controls_open", False), small=True)
