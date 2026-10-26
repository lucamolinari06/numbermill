"""Constant sources survive wiring, nesting, editing, rotation and saved controllers."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
import json
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pygame
from circuit import Circuit, Part, E, edge_terminals
import constant_editor
import workshop_floor


def constant_circuit(value, rotation=0):
    circuit=Circuit(terminals=edge_terminals(('A','B')))
    circuit.set_part((5,4),Part('CONSTANT',rotation,value=value))
    out=next(pos for pos,p in circuit.terminals.items() if p['output'])
    circuit.connect((5,4),out,0)
    return circuit


class ConstantCircuitTests(unittest.TestCase):
    def test_fixed_values_ignore_inputs_and_have_one_rotatable_output(self):
        for value in (0,1,42,256,65535):
            for rotation in range(4):
                circuit=constant_circuit(value,rotation)
                self.assertEqual(circuit.parts[(5,4)].ports(),((),((E+rotation)%4,)))
                for inputs in ((0,0),(65535,53)):
                    self.assertEqual(circuit.evaluate(*inputs),(value,True))

    def test_source_and_wire_use_existing_tick_delays_and_numeric_pipe_history(self):
        circuit=constant_circuit(37)
        circuit.tick()
        self.assertEqual(circuit.active[(5,4)],37)
        self.assertEqual(circuit.output_value(),0)
        circuit.tick()
        self.assertEqual(circuit.output_value(),37)
        legacy=Circuit()
        legacy.set_part((6,3),Part('CONSTANT',value=8192))
        for x in (7,8):legacy.set_part((x,3),Part('PIPE'))
        self.assertEqual(legacy.evaluate(0,0),(8192,True))
        legacy.convert_pipes()
        self.assertEqual(legacy.evaluate(0,0),(8192,True))

    def test_constants_feed_arithmetic_and_multiple_outputs(self):
        c=Circuit(terminals=edge_terminals(('A','B'),('OUT','COPY')))
        c.set_part((4,3),Part('CONSTANT',value=25))
        c.set_part((5,5),Part('CONSTANT',value=7))
        c.set_part((8,3),Part('MUL'))
        c.connect((4,3),(8,3),0);c.connect((5,5),(8,3),1)
        ports={p['name']:pos for pos,p in c.terminals.items()}
        c.connect((8,3),ports['OUT'],0);c.connect((4,3),ports['COPY'],0)
        for _ in range(8):c.tick()
        self.assertEqual(c.output_value('OUT'),175)
        self.assertEqual(c.output_value('COPY'),25)

    def test_snapshots_nested_designs_and_midflight_runtime_keep_value(self):
        c=constant_circuit(65535)
        for level in range(2):
            outer=Circuit(terminals=edge_terminals(('A','B')))
            outer.set_part((5,4),Part('DEVICE',device={'id':level+1,'version':1,'name':'Fixed output','parts':c.snapshot()}))
            out=next(pos for pos,p in outer.terminals.items() if p['output'])
            outer.connect((5,4),out,0);c=outer
        c.tick();before=deepcopy(c.runtime_snapshot())
        self.assertEqual(c.evaluate(8,99),(65535,True))
        self.assertEqual(c.runtime_snapshot(),before)
        loaded=Circuit.from_snapshot(json.loads(json.dumps(c.snapshot())))
        loaded.restore_runtime(json.loads(json.dumps(before)))
        for _ in range(10):
            c.tick();loaded.tick()
            self.assertEqual(c.runtime_snapshot(),loaded.runtime_snapshot())

    def test_malformed_values_are_rejected_and_older_parts_need_no_new_fields(self):
        for value in (-1,65536,1.5,'12',None,True):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):Part('CONSTANT',value=value)
                with self.assertRaises(ValueError):
                    Circuit.from_snapshot([{'x':5,'y':4,'kind':'CONSTANT','rotation':0,'value':value}])
        old=Circuit.from_snapshot([{'x':5,'y':4,'kind':'NOT','rotation':1}])
        self.assertNotIn('value',old.snapshot()[0])


class ConstantEditorTests(unittest.TestCase):
    def setUp(self):
        from game import Game
        self.temp=tempfile.TemporaryDirectory();root=Path(self.temp.name)
        self.patches=[patch('game.SAVES_DIR',root/'saves'),patch('game.SAVE_FILE',root/'old.json'),patch('game.DESIGNS_FILE',root/'designs.json')]
        for p in self.patches:p.start()
        self.g=Game();self.g.start_slot(1);self.g.open_circuit_bench()

    def tearDown(self):
        pygame.quit()
        for p in reversed(self.patches):p.stop()
        self.temp.cleanup()

    def key(self,key,unicode='',mod=0):
        self.g.handle_key(pygame.event.Event(pygame.KEYDOWN,key=key,unicode=unicode,mod=mod))

    def point(self,pos):
        bx,by,cell=self.g.board_metrics()
        return bx+(pos[0]+.5)*cell,by+(pos[1]+.5)*cell

    def place(self):
        g=self.g;g.select_part('CONSTANT');g.handle_click(self.point((5,4)),1)
        self.assertIsNotNone(g.constant_editor)

    def enter(self,text):
        for char in text:self.key(ord(char),char)
        self.key(pygame.K_RETURN)

    def test_place_edit_rotate_wire_and_reload_sandbox(self):
        g=self.g;self.place();self.enter('42')
        self.assertEqual(g.circuit.parts[(5,4)].value,42)
        g.handle_click(self.point((5,4)),3)
        self.assertEqual(g.circuit.parts[(5,4)].rotation,1)
        self.assertEqual(g.circuit.parts[(5,4)].value,42)
        out=next(pos for pos,p in g.circuit.terminals.items() if p['output'])
        g.handle_click(workshop_floor.socket(g,(5,4),2),1)
        self.assertIsNone(g.constant_editor)
        g.handle_click(workshop_floor.socket(g,out,3),1)
        wires=deepcopy(g.circuit.traces)
        g.tested_snapshot=g.circuit.snapshot()
        g.handle_click(self.point((5,4)),1);self.enter('65535')
        self.assertEqual(g.circuit.traces,wires)
        self.assertIsNone(g.tested_snapshot)
        self.assertEqual(g.circuit.evaluate(0,0),(65535,True))
        g.save_game();g.start_slot(1);g.open_circuit_bench()
        self.assertEqual(g.circuit.parts[(5,4)].value,65535)
        self.assertEqual(g.circuit.evaluate(0,0),(65535,True))

    def test_invalid_cancel_and_modal_input_do_not_change_circuit_or_run_time(self):
        g=self.g;self.place()
        before=deepcopy(g.circuit.runtime_snapshot());village=deepcopy(vars(g.village))
        g.update(60)
        self.assertEqual(g.circuit.runtime_snapshot(),before)
        self.assertEqual(vars(g.village),village)
        # Focus loss can raise the pause menu over the editor. Escape must
        # dismiss the visible menu first, leaving the number edit untouched.
        g.pause_menu_open=True
        self.key(pygame.K_ESCAPE)
        self.assertFalse(g.pause_menu_open)
        self.assertIsNotNone(g.constant_editor)
        self.enter('65536')
        self.assertTrue(g.constant_editor['error'])
        self.assertEqual(g.circuit.parts[(5,4)].value,1)
        self.key(pygame.K_a,'a',pygame.KMOD_CTRL);self.enter('0')
        self.assertEqual(g.circuit.parts[(5,4)].value,0)
        g.handle_click(self.point((5,4)),1)
        self.key(pygame.K_BACKSPACE);self.key(pygame.K_RETURN)
        self.assertIsNotNone(g.constant_editor)
        self.key(pygame.K_ESCAPE)
        self.assertIsNone(g.constant_editor);self.assertFalse(g.pause_menu_open)
        self.assertEqual(g.circuit.parts[(5,4)].value,0)
        g.select_part('ERASE');g.handle_click(self.point((5,4)),1)
        self.assertNotIn((5,4),g.circuit.parts)

    def test_palette_and_modal_fit_and_apply_by_mouse(self):
        g=self.g;g.bench_component_group='Logic';g.draw()
        # Third item on the second row is the source in the factory palette;
        # second item on the second row in the five-column bench palette.
        g.handle_click((1033,542),1)
        self.assertEqual(g.selected,'CONSTANT')
        g.handle_click(self.point((5,4)),1);g.draw()
        rects=[r for r,_ in g.buttons]
        self.assertTrue(all(g.screen.get_rect().contains(r) for r in rects))
        self.assertFalse(rects[0].colliderect(rects[1]))
        for char in '1234':self.key(ord(char),char)
        g.handle_click(constant_editor.APPLY.center,1)
        self.assertEqual(g.circuit.parts[(5,4)].value,1234)

    def test_factory_install_keeps_fixed_output_and_inventions_remain_gate_only(self):
        import manufacturing
        import factory_controller
        g=self.g;g.open_factory();g.village.coins=100
        manufacturing.buy_equipment(g.village,'bench',(2,2))
        manufacturing.buy_equipment(g.village,'controller',(4,2))
        machine=manufacturing.state(g.village)['equipment'][0]
        g.edit_factory_controller(machine['id']);self.place();self.enter('7')
        out=next(pos for pos,p in g.circuit.terminals.items() if p['output'])
        g.circuit.connect((5,4),out,0)
        self.assertTrue(factory_controller.install(g))
        installed=manufacturing.get_machine(g.village,machine['id'])['controller']['parts']
        self.assertEqual(Circuit.from_snapshot(installed).evaluate(0,0),(7,True))
        g.open_invention();g.select_part('CONSTANT');g.handle_click(self.point((5,4)),1)
        self.assertNotIn((5,4),g.circuit.parts)
        self.assertIsNone(g.constant_editor)


if __name__=='__main__':unittest.main()
