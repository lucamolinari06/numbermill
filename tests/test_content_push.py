"""Integrated entry, isolation and world-route regressions for the content push."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import pygame
from circuit import Part
from game import Game
from town import TRAIL_ENTRANCE
import adventure


class ContentPushTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.patches = [patch("game.SAVES_DIR", self.root / "saves"),
                        patch("game.SAVE_FILE", self.root / "save.json"),
                        patch("game.DESIGNS_FILE", self.root / "designs.json")]
        for item in self.patches:
            item.start()
        self.g = Game()
        self.g.start_slot(1)

    def tearDown(self):
        pygame.quit()
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def key(self, key):
        self.g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0))

    def test_field_math_palette_places_every_block_without_invention_unlocks(self):
        import workbench
        g = self.g
        self.assertFalse(g.village.arithmetic_unlocks)
        adventure.enter(g)
        for editor in ("decoder", "interlock"):
            adventure.enter_editor(g, editor)
            g.adventure_spec = False
            g.draw()
            g.handle_click((1090, 252), 1)  # Math tab, through the live UI.
            for i, kind in enumerate(workbench.COMPONENT_GROUPS["Math"]):
                with self.subTest(editor=editor, kind=kind):
                    g.draw()
                    g.handle_click((998 + i % 4 * 62, 304 + i // 4 * 56), 1)
                    self.assertEqual(g.selected, kind)
                    pos = (2 + i % 6, 2 + i // 6)
                    bx, by, cell = g.board_metrics()
                    g.handle_click((bx + (pos[0] + .5) * cell, by + (pos[1] + .5) * cell), 1)
                    self.assertIn(pos, g.circuit.parts)
                    self.assertEqual(g.circuit.parts[pos].kind, kind)
                    self.assertIsNone(g.invention)
            adventure.close_editor(g)
        self.assertFalse(g.village.arithmetic_unlocks)

    def test_saved_math_device_can_be_placed_in_field_editor(self):
        g = self.g
        g.open_circuit_bench()
        g.circuit.set_part((5, 4), Part("MUL"))
        g.save_copy("Reusable multiplier")
        g.open_factory()
        adventure.enter(g)
        adventure.enter_editor(g, "decoder")
        g.adventure_spec = False
        g.select_device(0)
        self.assertEqual(g.selected, "DEVICE")
        bx, by, cell = g.board_metrics()
        g.handle_click((bx + 6.5 * cell, by + 4.5 * cell), 1)
        self.assertIn((6, 4), g.circuit.parts)
        self.assertEqual(g.circuit.parts[(6, 4)].kind, "DEVICE")

    def test_factory_bench_defaults_to_saved_sandbox_and_escape_returns_floor(self):
        g = self.g
        g.circuit.set_part((4, 3), Part("AND"))
        contract = g.circuit.snapshot()
        g.open_factory()
        g.open_circuit_bench()
        self.assertIsNotNone(g.sandbox_context)
        self.assertEqual(g.tab, "BUILD")
        g.circuit.set_part((6, 4), Part("DIV"))
        draft = g.circuit.snapshot()
        g.save_game()
        self.key(pygame.K_ESCAPE)
        self.assertEqual(g.scene, "factory")
        self.assertEqual(g.circuit.snapshot(), contract)
        g.open_circuit_bench()
        self.assertEqual(g.circuit.snapshot(), draft)
        g.return_to_menu()
        g.start_slot(1)
        g.open_factory()
        g.open_circuit_bench()
        self.assertEqual(g.circuit.snapshot(), draft)
        self.assertFalse(g.submission_ready)

    def test_north_trail_enters_adventure_and_pause_freezes_world(self):
        g = self.g
        g.town.player_x, g.town.player_y = TRAIL_ENTRANCE
        self.assertEqual(g.town.nearby_place(), "adventure")
        self.key(pygame.K_e)
        self.assertEqual(g.scene, "adventure")
        g.draw()
        self.key(pygame.K_q)
        self.assertTrue(g.running)
        self.key(pygame.K_ESCAPE)
        self.assertTrue(g.pause_menu_open)
        before = deepcopy(vars(g.village))
        g.update(60)
        self.assertEqual(vars(g.village), before)
        self.key(pygame.K_RETURN)
        self.assertFalse(g.pause_menu_open)
        adventure.leave(g)
        self.assertEqual(g.scene, "town")
        self.assertEqual(g.town.nearby_place(), "adventure")

    def test_field_draft_saves_separately_and_full_recovery_unlocks_factory(self):
        from test_adventure import design
        import manufacturing
        g = self.g
        g.circuit.set_part((4, 3), Part("OR"))
        contract = g.circuit.snapshot()
        g.open_circuit_bench()
        g.circuit.set_part((6, 3), Part("ADD"))
        sandbox_draft = g.circuit.snapshot()
        g.open_factory()
        g.scene = "town"
        g.town.player_x, g.town.player_y = TRAIL_ENTRANCE
        self.key(pygame.K_e)
        current = adventure.state(g.village)
        current["position"] = list(adventure.POINTS["receiver"])
        adventure.interact(g)
        self.assertTrue(adventure.active_editor(g))
        # Specifications consume input until dismissed; no background build.
        before = g.circuit.snapshot()
        self.key(pygame.K_2)
        self.assertEqual(g.circuit.snapshot(), before)
        self.key(pygame.K_ESCAPE)
        self.assertTrue(adventure.active_editor(g))
        g.circuit = design("decoder")
        g.save_game()
        field_draft = g.circuit.snapshot()
        g.return_to_menu()
        g.start_slot(1)
        self.assertEqual(g.circuit.snapshot(), contract)
        g.open_circuit_bench()
        self.assertEqual(g.circuit.snapshot(), sandbox_draft)
        g.open_factory()
        adventure.enter(g)
        adventure.enter_editor(g, "decoder")
        self.assertEqual(g.circuit.snapshot(), field_draft)
        self.assertTrue(adventure.validate(g)[0])
        adventure.close_editor(g)
        current = adventure.state(g.village)
        current["position"] = list(adventure.POINTS["interlock"])
        adventure.interact(g)
        g.circuit = design("interlock")
        self.assertTrue(adventure.validate(g)[0])
        adventure.close_editor(g)
        from test_mosswater import complete_survey
        complete_survey(g)
        current["position"] = list(adventure.POINTS["artifact"])
        adventure.interact(g)
        self.assertTrue(manufacturing.equipment_unlocked(g.village, "precision_machine"))
        g.return_to_menu()
        g.start_slot(1)
        self.assertTrue(manufacturing.equipment_unlocked(g.village, "precision_machine"))
        self.assertTrue(adventure.state(g.village)["receiver_upgrade"])
        self.assertTrue(adventure.state(g.village)["expansion_complete"])
        self.assertTrue(adventure.state(g.village)["range_gate"])
        self.assertEqual(len(adventure.state(g.village)["survey_found"]),3)
        self.assertEqual(g.circuit.snapshot(), contract)

    def test_manual_receiver_controls_and_partial_survey_survive_save_reload(self):
        from test_adventure import design
        g=self.g;adventure.enter(g);s=adventure.state(g.village)
        s.update(receiver=True,decoder=True,interlock=True,position=list(adventure.POINTS['survey']))
        s['designs']['decoder']=design('decoder').snapshot()
        self.key(pygame.K_e)
        before=deepcopy(s)
        for key in (pygame.K_r,pygame.K_TAB,pygame.K_SPACE):self.key(key)
        self.assertEqual(s,before)
        self.key(pygame.K_RETURN)
        s.update(position=[2160,430],bearing=0)
        self.key(pygame.K_r);self.assertEqual(s['bearing'],1)
        self.key(pygame.K_SPACE)
        self.assertEqual(len(s['survey_samples']['crown']),1)
        self.key(pygame.K_TAB);self.assertEqual(s['frequency'],1)
        saved=deepcopy(s)
        g.return_to_menu();g.start_slot(1)
        self.assertEqual(adventure.state(g.village),saved)

    def test_shannon_reacts_after_inspection_is_dismissed(self):
        g=self.g;adventure.enter(g);current=adventure.state(g.village)
        current.update(decoder=True,interlock=True)
        current['position']=list(adventure.POINTS['survey'])
        adventure.interact(g)
        self.assertIsNotNone(g.adventure_modal)
        self.assertEqual(g.adventure_speech_time,0)
        g.update(10)
        self.assertEqual(g.adventure_speech_time,0)
        g.draw()
        g.handle_click((820,500),1)  # Continue in the inspection panel.
        self.assertIsNone(g.adventure_modal)
        self.assertIn('survey network',g.adventure_speech)
        self.assertEqual(g.adventure_speech_time,8)
        g.update(.1)
        self.assertLess(g.adventure_speech_time,8)

        current.update(position=list(adventure.POINTS['artifact']),range_gate=True)
        adventure.interact(g)
        self.assertEqual(g.adventure_speech_time,0)
        self.key(pygame.K_ESCAPE)  # Closing the panel must not open pause.
        self.assertFalse(g.pause_menu_open)
        self.assertIsNone(g.adventure_modal)
        self.assertIn('precision cutter blueprint',g.adventure_speech)
        self.assertEqual(g.adventure_speech_time,8)

        current['position']=list(adventure.POINTS['range_lock'])
        current['survey_found']=['crown','fern','reed']
        current['range_gate']=False
        adventure.interact(g)
        self.assertEqual(g.adventure_speech_time,0)
        self.key(pygame.K_RETURN)
        self.assertIsNone(g.adventure_modal)
        self.assertEqual(g.adventure_speech_time,0)

    def test_field_editor_respects_ledger_and_wire_escape(self):
        g = self.g
        adventure.enter(g)
        adventure.enter_editor(g, "decoder")
        g.adventure_spec = False
        g.trace_source = next(iter(g.circuit.terminals))
        self.key(pygame.K_ESCAPE)
        self.assertIsNone(g.trace_source)
        self.assertTrue(adventure.active_editor(g))
        g.open_ledger()
        self.assertEqual(g.scene, "ledger")
        self.key(pygame.K_ESCAPE)
        self.assertEqual(g.scene, "workshop")
        self.assertTrue(adventure.active_editor(g))
        g.edit_ports()
        self.key(pygame.K_ESCAPE)
        self.assertIsNone(g.port_editor)
        self.assertTrue(adventure.active_editor(g))
        self.key(pygame.K_ESCAPE)
        self.assertEqual(g.scene, "adventure")
