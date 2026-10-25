"""Run regressions and capture fresh UI checks without touching player saves."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from datetime import datetime, timezone
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pygame
from circuit import CommissionCase
from game import Game
from town import LOCATIONS
import ledger


def capture_checks(output):
    artifacts = []
    with tempfile.TemporaryDirectory() as directory, patch("game.SAVES_DIR", Path(directory) / "saves"), \
            patch("game.SAVE_FILE", Path(directory) / "save.json"), \
            patch("game.DESIGNS_FILE", Path(directory) / "designs.json"):
        game = Game()
        game.start_slot(2)

        def key(code):
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=code, mod=0, unicode=""))
            for event in pygame.event.get():
                game.handle_event(event)
            game.update(0)
            game.draw()

        def capture(name):
            game.draw()
            pygame.image.save(game.screen, output / name)
            artifacts.append(name)

        capture("01-town-workshop-prompt.png")
        key(pygame.K_e)
        assert game.scene == "factory", "E did not enter the production workshop"
        capture("02-production-workshop.png")
        game.open_circuit_bench()
        assert game.scene == "workshop", "E did not enter the workshop"
        import sandbox
        sandbox.leave(game)
        capture("02-workshop-entered.png")
        game.village.active_commission = "vent"
        game.task_help_open = True
        capture("03-task-details.png")
        key(pygame.K_ESCAPE)
        game.test_results = [CommissionCase(False, False, False, False, True, (False, False, False))] * 32
        key(pygame.K_PAGEDOWN)
        game.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, y=-30, x=0))
        assert game.test_scroll == 24
        capture("04-truth-table-scrolled.png")
        key(pygame.K_ESCAPE)
        key(pygame.K_y)
        assert game.selected == "ERASE"
        game.scene = "town"
        game.town.player_x, game.town.player_y = LOCATIONS["market"]
        game.village.advance_day()
        key(pygame.K_e)
        key(pygame.K_e)
        assert game.village.player_bread == 1
        capture("05-market-purchase.png")
        key(pygame.K_ESCAPE)
        key(pygame.K_l)
        for tab in ledger.TABS:
            game.select_ledger_tab(tab)
            capture(f"ledger-{tab.lower()}.png")
        key(pygame.K_ESCAPE)
        game.village.arithmetic_unlocks = ["ADD"]
        game.open_invention("multiplier")
        game.test_invention()
        key(pygame.K_PAGEDOWN)
        key(pygame.K_PAGEDOWN)
        assert game.test_scroll == 8
        capture("06-invention-last-cases.png")
        game.task_help_open = True
        capture("07-invention-task-details.png")
        key(pygame.K_ESCAPE)
        key(pygame.K_ESCAPE)
        game.close_invention()
        game.open_compute()
        game.task_help_open = True
        capture("08-compute-task-details.png")
        key(pygame.K_ESCAPE)
        game.return_to_menu()
        game.start_slot(2)
        assert game.village.player_bread == 1
        assert not game.task_help_open
        capture("09-reloaded-town.png")
        pygame.quit()
    return artifacts


def main():
    output = ROOT / "testing-screenshots" / "debug-run"
    output.mkdir(parents=True, exist_ok=True)
    stream = io.StringIO()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    (output / "tests.txt").write_text(stream.getvalue(), encoding="utf-8")
    report = {"time_utc": datetime.now(timezone.utc).isoformat(), "python": sys.executable,
              "pygame": pygame.version.ver, "tests": result.testsRun,
              "failures": len(result.failures), "errors": len(result.errors),
              "screenshots": [], "ui_checks_passed": False}
    try:
        report["screenshots"] = capture_checks(output)
        report["ui_checks_passed"] = True
    except Exception as error:
        report["ui_error"] = repr(error)
        raise
    finally:
        (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"{result.testsRun} tests; {len(result.failures)} failures; {len(result.errors)} errors.")
    print(f"UI checks passed. Report: {output / 'report.json'}")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
