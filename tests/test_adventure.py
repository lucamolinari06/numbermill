"""Field puzzle certification, persistence, injury and reward regression checks."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock
from circuit import Circuit,Part,edge_terminals
from economy import Village
import adventure
import manufacturing


def design(kind):
    c=Circuit(terminals=edge_terminals(('A','B','C')))
    ports={p['name']:pos for pos,p in c.terminals.items()}
    def gate(name,kind,pos,*sources):
        ports[name]=pos;c.parts[pos]=Part(kind)
        for i,source in enumerate(sources):c.connect(ports[source],pos,i)
    if kind=='decoder':
        gate('bearing','DIV',(3,2),'A','C')
        gate('range','MOD',(3,6),'A','C')
        gate('matches','EQ',(7,2),'bearing','B')
        gate('result','MUL',(11,4),'range','matches')
    else:
        gate('one','EQ',(2,1),'A','A')
        gate('zero','SUB',(2,7),'A','A')
        gate('locked','EQ',(5,1),'C','one')
        gate('positive','GT',(5,7),'A','zero')
        gate('over','GT',(5,4),'A','B')
        gate('below','NOT',(8,4),'over')
        gate('pressure','AND',(10,6),'below','positive')
        gate('result','AND',(12,4),'locked','pressure')
    c.connect(ports['result'],ports['OUT'],0)
    return c


class AdventureTests(unittest.TestCase):
    def test_real_multi_gate_solutions_pass_without_mutating_editor(self):
        for kind in ('decoder','interlock'):
            c=design(kind);c.tick();before=deepcopy(c.runtime_snapshot())
            ok,message=adventure.certify(c,kind)
            self.assertTrue(ok,message)
            self.assertEqual(before,c.runtime_snapshot())

    def test_blank_direct_and_constant_designs_cannot_disable_hazard(self):
        for kind in ('decoder','interlock'):
            c=Circuit(terminals=edge_terminals(('A','B','C')))
            self.assertFalse(adventure.certify(c,kind)[0])
            p={v['name']:k for k,v in c.terminals.items()}
            c.connect(p['A'],p['OUT'],0)
            self.assertFalse(adventure.certify(c,kind)[0])
            c.parts[(5,4)]=Part('EQ');c.connect(p['A'],(5,4),0);c.connect(p['A'],(5,4),1);c.connect((5,4),p['OUT'],0)
            self.assertFalse(adventure.certify(c,kind)[0])

    def test_interlock_rejects_fault_and_zero_pressure_shortcuts(self):
        c=design('interlock')
        self.assertEqual(c.evaluate(0,6,1)[0],0)
        self.assertEqual(c.evaluate(6,6,1)[0],1)
        self.assertEqual(c.evaluate(7,6,1)[0],0)
        self.assertEqual(c.evaluate(6,6,3)[0],0)
        self.assertEqual(c.evaluate(6,6,0)[0],0)

    def test_artifact_reward_requires_both_designs_and_is_one_time(self):
        v=Village();s=adventure.state(v);s['position']=list(adventure.POINTS['artifact'])
        g=SimpleNamespace(village=v,save_game=Mock())
        adventure.interact(g);self.assertFalse(s['artifact'])
        s.update(decoder=True,interlock=True,range_gate=True)
        adventure.interact(g);self.assertTrue(s['artifact']);self.assertTrue(s['receiver_upgrade'])
        unlocked=deepcopy(manufacturing.state(v).get('unlocks'))
        adventure.interact(g);self.assertEqual(manufacturing.state(v).get('unlocks'),unlocked)
        self.assertEqual(g.save_game.call_count,1)

    def test_food_and_hazards_have_real_saved_costs(self):
        v=Village();v.player_bread=1;s=adventure.state(v);s.update(health=30,hunger=20)
        g=SimpleNamespace(village=v,save_game=Mock(),toast=Mock(),adventure_companion=SimpleNamespace(reset=Mock()))
        adventure.eat(g);self.assertEqual((v.player_bread,s['health']),(0,55))
        self.assertNotIn('hunger',s)
        adventure.eat(g);self.assertEqual(s['health'],55)
        adventure.hurt(g,25);self.assertEqual(s['health'],30);self.assertEqual(s['position'],[1090.,540.])

    def test_old_hunger_is_removed_without_changing_progress_and_bread_cannot_be_wasted(self):
        v=Village();v.player_bread=3;s=adventure.state(v)
        s.update(hunger=0,health=90,decoder=True)
        g=SimpleNamespace(village=v,save_game=Mock(),toast=Mock())
        self.assertNotIn('hunger',adventure.state(v))
        self.assertTrue(s['decoder']);self.assertEqual(s['health'],90)
        adventure.eat(g)
        self.assertEqual((s['health'],v.player_bread),(100,2))
        adventure.eat(g)
        self.assertEqual((s['health'],v.player_bread),(100,2))
        self.assertEqual(g.save_game.call_count,1)

    def test_ravine_cannot_be_walked_around_and_old_save_defaults_are_safe(self):
        self.assertFalse(adventure.blocked(1230,500))
        for y in range(0,1040,20):
            if not 440<=y+adventure.FOOT_OFFSET<=560:self.assertTrue(adventure.blocked(1230,y))
        v=Village();s=adventure.state(v);s['health']=44
        self.assertEqual(adventure.state(v)['health'],44)
        self.assertNotIn('adventure',Village().manufacturing)


if __name__=='__main__':unittest.main()
