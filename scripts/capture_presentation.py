"""Inspect the presentation overhaul using a disposable game and preferences."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--play", action="store_true", help="Open an interactive disposable title screen.")
    parser.add_argument("--smoke", action="store_true", help="Exercise real resize/fullscreen presentation.")
    args = parser.parse_args()
    if not (args.play or args.smoke):
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame
    from game import Game
    output = ROOT/"testing-screenshots"/"presentation-overhaul"
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as folder:
        root = Path(folder)
        with patch("game.SAVES_DIR", root/"saves"), patch("game.SAVE_FILE", root/"old.json"), \
                patch("game.DESIGNS_FILE", root/"designs.json"):
            g = Game()
            if args.play:
                pygame.display.set_caption("Numbermill — disposable visual preview")
                g.run()
                return

            def capture(name):
                g.draw()
                pygame.image.save(g.screen, str(output/(name+".png")))

            capture("title")
            g.open_settings()
            capture("settings")
            g.controls_open = True
            capture("controls")
            g.close_settings()
            g.start_slot(1)
            capture("town")
            g.pause_menu_open = True
            capture("pause")
            g.pause_menu_open = False
            g.return_to_menu()
            g.menu_page = "slots"
            capture("save-slots")
            if args.smoke:
                import window_display
                import presentation
                g.menu_page = "title"
                stages = [(1280, 760), (1600, 950), (1000, 760)]
                for i, size in enumerate(stages):
                    g.viewport.resize(size)
                    for _ in range(24):
                        for event in pygame.event.get():
                            g.handle_event(event)
                        g.update(g.clock.tick(60)/1000)
                        g.draw()
                    pygame.image.save(g.viewport.window, str(output/f"window-{i}.png"))
                native = window_display.geometry()
                if native:
                    # Reproduce the reported bug: start at the monitor's center.
                    displaced = pygame.Rect(*native["monitor"].center, *g.viewport.window.get_size())
                    window_display.position(displaced)
                before_full = window_display.geometry()
                g.toggle_preference("fullscreen")
                for _ in range(24):
                    for event in pygame.event.get():
                        g.handle_event(event)
                    g.update(g.clock.tick(60)/1000)
                    g.draw()
                pygame.image.save(g.viewport.window, str(output/"fullscreen.png"))
                full = window_display.geometry()
                if full:
                    assert full["window"] == full["monitor"], (full["window"], full["monitor"])
                    assert g.viewport.window.get_size() == full["monitor"].size
                fit = presentation.viewport_rect(g.viewport.window.get_size(), integer=True)
                assert g.viewport.pointer(fit.center) == (640, 380)
                g.open_settings()
                g.draw()
                pygame.image.save(g.viewport.window, str(output/"fullscreen-settings.png"))
                smooth_button = g.buttons[1][0].center
                physical = (fit.x + smooth_button[0] * fit.w // 1280,
                            fit.y + smooth_button[1] * fit.h // 760)
                g.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=physical, button=1))
                assert g.settings["smooth_scaling"]  # actual scaled Settings button
                g.draw()
                pygame.image.save(g.viewport.window, str(output/"fullscreen-smooth.png"))
                g.toggle_preference("smooth_scaling")
                g.close_settings()
                g.toggle_preference("fullscreen")
                g.draw()
                pygame.image.save(g.viewport.window, str(output/"restored-window.png"))
                restored = window_display.geometry()
                if restored:
                    assert restored["work"].contains(restored["window"])
                g.toggle_preference("fullscreen")
                pygame.quit()
                g = Game()  # preferences reopen fullscreen with no existing window
                g.draw()
                reopened = window_display.geometry()
                assert g.settings["fullscreen"]
                if reopened:
                    assert reopened["window"] == reopened["monitor"]
                g.toggle_preference("fullscreen")
                def serialize(value):
                    return {key: list(rect) if rect is not None else None for key, rect in value.items()} if value else None
                (output/"display-check.json").write_text(json.dumps({
                    "before_fullscreen": serialize(before_full), "fullscreen": serialize(full),
                    "restored": serialize(restored), "game_viewport": list(fit),
                    "reopened_fullscreen": serialize(reopened),
                    "checks_passed": True}, indent=2), encoding="utf-8")
            pygame.quit()
    print(output)


if __name__ == "__main__":
    main()
