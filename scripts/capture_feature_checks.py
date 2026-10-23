"""Run regression checks and capture real game screens in an unsaved test village."""
from pathlib import Path
import os
import sys
import io
import json
import time
import unittest
from collections import Counter
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
from circuit import Circuit, Part
from game import Game, rounded, text, PAPER, TEAL, INK, MUTED
import inventions


class RecordedResults(unittest.TextTestResult):
    def startTestRun(self):
        self.successes = []
        super().startTestRun()

    def addSuccess(self, test):
        self.successes.append(test.id())
        super().addSuccess(test)


def calculator(kind):
    circuit = Circuit()
    for x in (2, 3, 5, 6, 7, 8):
        circuit.set_part((x, 3), Part("PIPE"))
    for y in (4, 5):
        circuit.set_part((4, y), Part("PIPE", 1))
    circuit.set_part((4, 3), Part(kind))
    return circuit


def main():
    output = ROOT / "testing-screenshots"
    output.mkdir(exist_ok=True)
    stream = io.StringIO()
    start = time.perf_counter()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=RecordedResults).run(suite)
    duration = time.perf_counter() - start
    (output / "test-results.txt").write_text(stream.getvalue(), encoding="utf-8")
    if not result.wasSuccessful():
        print(stream.getvalue())
        return 1

    game = Game()
    game.scene = "workshop"
    # Construct and verify the actual small gate prototypes to earn the blocks.
    from test_inventions import solution
    game.open_invention("adder")
    game.draw()
    pygame.image.save(game.screen, output / "00-empty-invention-challenge.png")
    game.village.invention_drafts["adder"] = solution("adder")
    game.switch_invention("adder")
    game.invention.bits = {"A": 1, "B": 1}
    game.invention.edit()
    game.invention.tick()
    game.draw()
    pygame.image.save(game.screen, output / "06-binary-half-adder.png")
    game.test_invention()
    assert "ADD" in game.village.arithmetic_unlocks
    game.draw()
    pygame.image.save(game.screen, output / "07-add-unlocked.png")
    for key in ("subtractor", "comparator", "multiplier"):
        game.village.invention_drafts[key] = solution(key)
        assert all(row["passed"] for row in inventions.test(game.village, key))
    game.switch_invention("multiplier")
    game.invention.bits = {name: 1 for name in game.invention.challenge.inputs}
    game.invention.edit()
    for _ in range(8):
        game.invention.tick()
    game.draw()
    pygame.image.save(game.screen, output / "08-binary-multiplier.png")
    game.test_invention()
    game.draw()
    pygame.image.save(game.screen, output / "09-multiplier-verified.png")
    invention_records = dict(game.village.invention_records)
    game.close_invention()
    game.open_compute()
    game.build_compute()
    game.circuit = calculator("MUL")
    game.circuit.switches = {"A": 12, "B": 3}
    game.selected = "MUL"
    for _ in range(100):
        game.circuit.tick()
    assert game.circuit.output_value() == 36
    game.draw()
    pygame.image.save(game.screen, output / "01-expanded-workbench.png")

    game.test_compute()
    assert all(row["passed"] for row in game.compute_results)
    good_cases = list(game.compute_results)
    game.draw()
    pygame.image.save(game.screen, output / "02-arithmetic-tests.png")

    game.approve_compute()
    game.run_compute()
    assert game.village.compute_orders[-1]["net"] == 5
    assert game.village.compute_orders[-1]["result"] == 6
    game.draw()
    pygame.image.save(game.screen, output / "03-paid-computation.png")
    receipt = dict(game.village.compute_orders[-1])

    game.circuit = calculator("ADD")
    game.test_compute()
    assert any(not row["passed"] for row in game.compute_results)
    game.draw()
    pygame.image.save(game.screen, output / "04-rejected-calculator.png")
    failed_cases = list(game.compute_results)

    groups = Counter(name.split(".")[0] for name in result.successes)
    game.screen.fill((61, 85, 79))
    rounded(game.screen, PAPER, (70, 55, 1140, 650), 10)
    text(game.screen, game.big, "AUTOMATED REGRESSION CHECKS", 112, 91, TEAL)
    text(game.screen, game.big, f"{result.testsRun} PASSED / 0 FAILURES / 0 ERRORS", 112, 160, TEAL)
    text(game.screen, game.font, "Actual unittest run; screenshots use a fresh village with no save slot.", 112, 213, MUTED)
    for i, (name, count) in enumerate(sorted(groups.items())):
        text(game.screen, game.heading, f"{name:<24} {count:>2} passed", 112, 282 + i * 49, INK)
    text(game.screen, game.font, f"Completed in {duration:.2f}s", 112, 604, MUTED)
    text(game.screen, game.small, "Includes nested arithmetic, customer funds, fuel, daily limits, save/load, and UI clicks.", 112, 652, TEAL)
    pygame.display.flip()
    pygame.image.save(game.screen, output / "05-test-summary.png")
    report = {"captured_at": datetime.now(timezone.utc).isoformat(), "tests_run": result.testsRun,
              "failures": len(result.failures), "errors": len(result.errors), "duration_seconds": duration,
              "passed_tests": result.successes, "groups": dict(groups), "passing_calculator": good_cases,
              "rejected_calculator": failed_cases, "paid_order": receipt,
              "invention_records": invention_records, "arithmetic_unlocks": game.village.arithmetic_unlocks,
              "screenshots": [path.name for path in sorted(output.glob("*.png"))]}
    (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    pygame.quit()
    print(f"{result.testsRun} checks passed. {len(report['screenshots'])} screenshots and report saved to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
