"""Actual info-button entry, pin orientation, and modal input isolation."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import pygame
import adventure
import component_info
import manufacturing
import ui_theme
import workbench
from circuit import Part
from game import Game


class ComponentInfoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.patches = [patch("game.SAVES_DIR", root / "saves"),
                        patch("game.SAVE_FILE", root / "save.json"),
                        patch("game.DESIGNS_FILE", root / "designs.json")]
        for item in self.patches:item.start()
        self.g = Game();self.g.start_slot(1)

    def tearDown(self):
        for item in reversed(self.patches):item.stop()
        pygame.quit();self.temp.cleanup()

    def key(self,key):
        self.g.handle_key(pygame.event.Event(pygame.KEYDOWN,key=key,mod=0))

    def test_info_button_opens_in_every_editor(self):
        g = self.g
        g.open_circuit_bench();g.select_part("DIV");g.draw()
        g.handle_click((1006,650),1)
        self.assertEqual(g.component_info.kind,"DIV")
        self.key(pygame.K_ESCAPE)
        g.open_factory();g.village.coins=100
        self.assertTrue(manufacturing.buy_equipment(g.village,"bench",(1,1))[0])
        g.edit_factory_controller(manufacturing.state(g.village)["equipment"][0]["id"])
        g.select_part("REGISTER");g.draw();g.handle_click((1092,535),1)
        self.assertEqual(g.component_info.kind,"REGISTER")
        self.key(pygame.K_ESCAPE)
        for editor in ("decoder","interlock"):
            adventure.enter(g);adventure.enter_editor(g,editor);g.adventure_spec=False
            g.select_part("MUX");g.draw();g.handle_click((1092,525),1)
            self.assertEqual(g.component_info.kind,"MUX")
            self.key(pygame.K_ESCAPE)
            self.assertTrue(adventure.active_editor(g))
            self.assertFalse(g.pause_menu_open)
            adventure.close_editor(g)

    def test_modal_blocks_board_shortcuts_and_time_without_changing_design(self):
        g=self.g;adventure.enter(g);adventure.enter_editor(g,"decoder");g.adventure_spec=False
        g.select_part("MUL");g.draw();g.handle_click((1092,525),1)
        before=g.circuit.snapshot();runtime=deepcopy(g.circuit.runtime_snapshot())
        village=deepcopy(vars(g.village));g.draw()
        for key in (pygame.K_SPACE,pygame.K_t,pygame.K_n,pygame.K_2):self.key(key)
        g.handle_click((360,360),1);g.handle_click((360,360),3);g.update(60)
        self.assertEqual(g.circuit.snapshot(),before)
        self.assertEqual(g.circuit.runtime_snapshot(),runtime)
        self.assertEqual(vars(g.village),village)
        self.key(pygame.K_r)
        self.assertEqual(g.component_info.rotation,1)
        self.assertEqual(g.rotation,0)
        g.handle_click(component_info.CLOSE.center,1)
        self.assertIsNone(g.component_info)
        self.assertEqual(g.buttons,[])
        self.assertTrue(adventure.active_editor(g))

    def test_pin_roles_follow_rotations_and_custom_device_names(self):
        unrotated={d:name for d,_,name,_ in component_info.pin_labels(Part("MUX"))}
        self.assertEqual(unrotated,{3:"First value",2:"Second value",0:"Select",1:"Selected value"})
        clockwise={d:name for d,_,name,_ in component_info.pin_labels(Part("MUX",1))}
        self.assertEqual(clockwise,{0:"First value",3:"Second value",1:"Select",2:"Selected value"})
        self.assertEqual([row[2] for row in component_info.pin_labels(Part("REGISTER"))],
                         ["Data","Clock","Stored value"])
        self.assertEqual([row[2] for row in component_info.pin_labels(Part("COUNTER"))],
                         ["Pulse","Reset","Count"])
        device=Part("DEVICE",0,{"ports":{"A":"Metal","B":"Target","OUT":"Produce"}})
        self.assertEqual([row[2] for row in component_info.pin_labels(device)],["Metal","Target","Produce"])

    def test_shared_panels_keep_screws_clear_of_text_across_screens(self):
        import dialogue, factory_ui, factory_shannon, ledger, project_ui, shannon
        from contextlib import ExitStack
        g=self.g
        def check():
            boxes=[];screws=[]
            original=ui_theme.fit_text;original_circle=pygame.draw.circle
            def capture(*args,**kwargs):
                rect=original(*args,**kwargs);boxes.append(rect);return rect
            def circle(*args,**kwargs):
                rect=original_circle(*args,**kwargs)
                if args[1]==ui_theme.COPPER and args[3]==2:screws.append(rect.inflate(6,6))
                return rect
            with ExitStack() as stack:
                for module in (ui_theme,dialogue,factory_ui,factory_shannon,ledger,project_ui,shannon):
                    if hasattr(module,"fit_text"):stack.enter_context(patch.object(module,"fit_text",side_effect=capture))
                stack.enter_context(patch("pygame.draw.circle",side_effect=circle))
                g.draw()
            for text in boxes:
                for screw in screws:self.assertFalse(text.colliderect(screw),(g.scene,text,screw))
        check()
        adventure.enter(g);check()
        adventure.leave(g);g.open_factory()
        for page in ("floor","equipment","supplies","orders"):
            g.factory_page=page;check()
        g.open_ledger()
        for tab in ledger.TABS:
            g.select_ledger_tab(tab);check()
        g.open_requests();check()
        g.scene="town";g.town_dialogue="person:Luca";check()

    def test_all_component_diagrams_fit_without_text_or_button_overlap(self):
        g=self.g;g.open_circuit_bench()
        kinds=[k for group in workbench.COMPONENT_GROUPS.values() for k in group if k not in ("TRACE","ERASE")]
        original=ui_theme.fit_text
        original_circle=pygame.draw.circle
        for kind in kinds:
            for rotation in range(4):
                with self.subTest(kind=kind,rotation=rotation):
                    g.component_info=Part(kind,rotation);boxes=[];screws=[]
                    def capture(*args,**kwargs):
                        rect=original(*args,**kwargs);boxes.append(rect);return rect
                    def capture_circle(*args,**kwargs):
                        rect=original_circle(*args,**kwargs)
                        if args[1]==ui_theme.COPPER and args[3]==2:screws.append(rect.inflate(6,6))
                        return rect
                    with patch("component_info.fit_text",side_effect=capture),patch("ui_theme.fit_text",side_effect=capture),patch("pygame.draw.circle",side_effect=capture_circle):
                        component_info.draw(g)
                    for i,rect in enumerate(boxes):
                        self.assertTrue(pygame.Rect(185,130,910,550).contains(rect))
                        for other in boxes[i+1:]:self.assertFalse(rect.colliderect(other))
                        for button,_ in g.buttons:self.assertFalse(rect.colliderect(button))
                        for screw in screws:self.assertFalse(rect.colliderect(screw))
