"""Real circuit certification, complete flight route, recovery and saved rewards."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
import json
import tempfile
import unittest
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import boiler_tower_layout as layout

import pygame
import adventure
import boiler_tower as tower
import manufacturing
from circuit import Circuit, Part, edge_terminals
from economy import Village
from game import Game


def design(kind):
    """Test fixtures are never imported by production or supplied to the player."""
    c = Circuit(terminals=edge_terminals(('A', 'B', 'C')))
    ports = {p['name']: pos for pos, p in c.terminals.items()}
    count = 0
    def gate(name, part, *sources):
        nonlocal count
        pos = (2+count//4*2, 1+count%4*2)
        count += 1
        ports[name] = pos
        c.parts[pos] = Part(part)
        for i, source in enumerate(sources):
            c.connect(ports[source], pos, i)
        return name
    def number(n):
        name = str(n)
        if name not in ports:
            if n == 1:
                gate(name, 'EQ', 'A', 'A')
            else:
                a = number(n//2)
                b = number(n-n//2)
                gate(name, 'ADD', a, b)
        return name
    if kind == 'tower_vent':
        gate('excess', 'SUB', 'A', 'B')
        gate('result', 'MUL', 'excess', 'C')
    else:
        p = tower.PROFILES[int(kind[-1])]
        low, limit, gain = number(p['minimum']), number(p['heat']), number(p['gain'])
        gate('low', 'GT', low, 'A')
        gate('pressure', 'NOT', 'low')
        gate('cool', 'GT', limit, 'B')
        gate('safe', 'AND', 'pressure', 'cool')
        gate('demand', 'MUL', 'C', gain)
        gate('result', 'MUL', 'demand', 'safe')
    c.connect(ports['result'], ports['OUT'], 0)
    return c


def fake_game():
    g = SimpleNamespace(village=Village(), save_game=Mock(), toast=Mock(),
                        adventure_modal=None, tower_facing='east',scene='boiler_tower')
    tower.reset_motion(g)
    tower.state(g.village)
    return g


def fly_to(g, index, dt=1/120, on_frame=None):
    """Traverse using only movement, jump and thrust; never teleport a landing."""
    s = tower.state(g.village)
    g.adventure_modal = None
    # Wait on the actual platform for pressure and heat to recover.
    for _ in range(round(4/dt)):
        tower.step(g, dt)
    left, top, width = tower.PLATFORMS[index]
    target = left+width/2
    def attempt(actor,clearance,callback=None):
        active=tower.state(actor.village);released=False
        injuries=adventure.state(actor.village)['injuries']
        for frame in range(round(4/dt)):
            x,y=active['position']
            dx=1 if target-x>2 else -1 if target-x < -2 else 0
            released=released or y<top-clearance
            tower.step(actor,dt,dx,not released,frame==0)
            if callback:callback(frame)
            if adventure.state(actor.village)['injuries']!=injuries:return False
            if actor.tower_grounded and abs(active['position'][1]-top)<1 and abs(active['position'][0]-target)<4:return True
        return False
    # Look for a launch window by waiting on safe ground. Probe the real physics
    # and hazard clock on disposable state; the actual traversal only uses input.
    for _ in range(48):
        for clearance in ((50,) if index in tower.STATIONS else (90,125,60)):
            probe=fake_game();probe.village.manufacturing=deepcopy(g.village.manufacturing)
            probe.tower_vx=g.tower_vx;probe.tower_vy=g.tower_vy;probe.tower_grounded=g.tower_grounded
            if attempt(probe,clearance):
                if attempt(g,clearance,on_frame):return
                raise AssertionError(f'Probe and traversal disagree at {index}')
        for _ in range(round(.25/dt)):tower.step(g,dt)
    raise AssertionError(f"No safe flight to landing {index} from {s['position']}")


class TowerTests(unittest.TestCase):
    def test_platforms_block_tops_undersides_and_both_sides(self):
        g=fake_game()
        left,top,width=tower.PLATFORMS[2]
        cx=left+width/2;bottom=top+layout.PLATFORM_THICKNESS
        head_stop=bottom+layout.BODY_HEIGHT
        g.tower_vy=-320
        _,y,landed=tower.collide_platforms(g,cx,head_stop+5,cx,head_stop-40)
        self.assertEqual(y,head_stop);self.assertEqual(g.tower_vy,0);self.assertIsNone(landed)
        g.tower_vy=600
        _,y,landed=tower.collide_platforms(g,cx,top-10,cx,top+50)
        self.assertEqual(y,top);self.assertEqual(landed,2)
        for old,new,edge in ((left-30,left+30,left-layout.BODY_HALF),
                             (left+width+30,left+width-30,left+width+layout.BODY_HALF)):
            g.tower_vx=220
            x,_,_=tower.collide_platforms(g,old,top+12,new,top+12)
            self.assertEqual(x,edge);self.assertEqual(g.tower_vx,0)
        # Sustained real thrust cannot push the head through the underside.
        s=tower.state(g.village);s['position']=[cx,head_stop+4]
        g.tower_grounded=False;g.tower_vy=-300
        adventure.state(g.village)['designs']['jetpack_0']=design('jetpack_0').snapshot()
        for _ in range(60):tower.step(g,1/120,thrust=True)
        self.assertGreaterEqual(s['position'][1],head_stop)
        self.assertFalse(g.tower_grounded)

    def test_hazards_warn_before_damage_and_all_three_hit_in_real_physics(self):
        for hazard in layout.HAZARDS[:3]:
            with self.subTest(kind=hazard['kind']):
                seconds=4.-hazard['offset']
                reading=layout.hazard_state(hazard,seconds)
                self.assertTrue(reading['active'])
                g=fake_game();s=tower.state(g.village)
                s['position']=[float(reading['rect'].centerx),float(reading['rect'].centery+20)]
                s['hazard_time']=seconds-1/120
                g.tower_grounded=False
                tower.step(g,1/120)
                self.assertEqual(adventure.state(g.village)['health'],75)
                self.assertEqual(s['position'],tower.landing_position(0))
                if hazard['kind']!='gear':
                    warning=layout.hazard_state(hazard,3.-hazard['offset'])
                    quiet=layout.hazard_state(hazard,1.-hazard['offset'])
                    self.assertEqual(warning['status'],'warning')
                    self.assertFalse(warning['active']);self.assertFalse(quiet['active'])

    def test_rest_centres_stay_safe_through_full_hazard_cycles(self):
        for index in range(len(tower.PLATFORMS)):
            actor=layout.body(*tower.landing_position(index))
            for tick in range(120):
                for hazard in layout.HAZARDS:
                    self.assertFalse(layout.touching(hazard,layout.hazard_state(hazard,tick*.1),actor),
                                     f'Unsafe waiting spot at {index}: {hazard}')

    def test_long_sections_have_saved_rest_stops_without_extra_puzzles(self):
        self.assertEqual(len(tower.PLATFORMS),31)
        self.assertEqual(len(tower.STATIONS),4)
        self.assertTrue(all(b-a>=10 for a,b in zip(tower.STATIONS,tower.STATIONS[1:])))
        self.assertGreaterEqual(len(layout.HAZARDS),15)
        g=fake_game();s=tower.state(g.village)
        rest=tower.CHECKPOINTS[1]
        s['position']=tower.landing_position(rest)
        tower.arrive(g,rest)
        self.assertEqual(s['checkpoint'],rest);self.assertEqual(s['stage'],0)
        self.assertIsNone(g.adventure_modal);self.assertIsNone(tower.at_station(g))
        tower.recover(g);self.assertEqual(s['position'],tower.landing_position(rest))
        loaded=Village(**json.loads(json.dumps(asdict(g.village))))
        self.assertEqual(tower.state(loaded),s)

    def test_old_tower_saves_map_to_equivalent_stages_without_losing_designs(self):
        for old_index,stage in ((0,0),(3,1),(6,2),(9,2)):
            g=fake_game();current=manufacturing.state(g.village)
            current['boiler_tower']={'stage':stage,'checkpoint':old_index,'position':[1100.,1360.],
                                    'complete':old_index==9,'visited':True,'falls':2}
            board=design('jetpack_'+str(stage)).snapshot()
            adventure.state(g.village)['designs']['jetpack_'+str(stage)]=board
            adventure.state(g.village)['health']=63
            if old_index==9:current['unlocks'].append('steam_accumulator')
            s=tower.state(g.village)
            expected=tower.SUMMIT if old_index==9 else tower.STATIONS[stage]
            self.assertEqual(s['checkpoint'],expected)
            self.assertEqual(s['position'],tower.landing_position(expected))
            self.assertEqual(s['falls'],2)
            self.assertEqual(adventure.state(g.village)['health'],63)
            self.assertEqual(adventure.state(g.village)['designs']['jetpack_'+str(stage)],board)
            if old_index==9:self.assertIn('steam_accumulator',current['unlocks'])

    def test_rail_follows_with_delay_acceleration_and_a_resting_gap(self):
        for dt in (1/60, 1/120):
            with self.subTest(dt=dt):
                g = fake_game()
                tower.reset_rail(g)
                s = tower.state(g.village)
                start = g.tower_rail_y
                s['position'][1] -= 240
                for _ in range(round(.2/dt)):
                    tower.update_rail(g, dt)
                self.assertEqual(g.tower_rail_y, start)
                for _ in range(round(.3/dt)):
                    tower.update_rail(g, dt)
                self.assertLess(g.tower_rail_y, start)
                self.assertGreater(g.tower_rail_y, s['position'][1]+180)
                self.assertLess(g.tower_rail_velocity, 0)
                self.assertLess(abs(g.tower_rail_velocity), tower.RAIL_SPEED)
                for _ in range(round(4/dt)):
                    tower.update_rail(g, dt)
                self.assertLess(abs(g.tower_rail_y-s['position'][1]), 32)
                self.assertLess(abs(g.tower_rail_velocity), 1)
                # Small player motion inside the resting band does not tug the rail.
                s['position'][1] = g.tower_rail_y+10
                before = g.tower_rail_y
                for _ in range(round(1/dt)):
                    tower.update_rail(g, dt)
                self.assertAlmostEqual(g.tower_rail_y, before, delta=.3)

    def test_rail_does_not_snap_at_stations_and_recovery_resets_it(self):
        g = fake_game()
        s = tower.state(g.village)
        tower.reset_rail(g)
        g.tower_rail_y = 1510.
        g.tower_rail_velocity = -160.
        s['position'] = tower.landing_position(tower.STATIONS[1])
        tower.arrive(g,tower.STATIONS[1])
        self.assertEqual(g.tower_rail_y,1510.)
        self.assertEqual(g.tower_rail_velocity,-160.)
        tower.restore_checkpoint(g)
        self.assertEqual(g.tower_rail_y,tower.PLATFORMS[tower.STATIONS[1]][1])
        self.assertEqual(g.tower_rail_velocity,0.)

    def test_airborne_speed_builds_coasts_and_reverses_without_snapping(self):
        g = fake_game()
        s = tower.state(g.village)
        s.update(stage=2,position=[600.,400.])
        g.tower_grounded = False
        g.tower_vy = -200.
        tower.step(g, 1/120, horizontal=1)
        self.assertGreater(g.tower_vx, 0)
        self.assertLess(g.tower_vx, tower.WALK_SPEED/10)
        for _ in range(30):
            tower.step(g, 1/120, horizontal=1)
        speed = g.tower_vx
        x = s['position'][0]
        for _ in range(12):
            tower.step(g, 1/120)
        self.assertGreater(s['position'][0], x+10)
        self.assertGreater(g.tower_vx, speed*.8)
        self.assertLess(g.tower_vx, speed)
        tower.step(g, 1/120, horizontal=-1)
        self.assertGreater(g.tower_vx, 0)  # Counter-steering brakes before reversing.
        for _ in range(35):
            tower.step(g, 1/120, horizontal=-1)
        self.assertLess(g.tower_vx, 0)
        self.assertGreaterEqual(g.tower_vx, -tower.WALK_SPEED)

    def test_takeoff_carries_walk_speed_and_landing_recall_and_walls_stop_drift(self):
        g = fake_game()
        s = tower.state(g.village)
        tower.step(g, 1/120, horizontal=1)
        self.assertEqual(g.tower_vx, tower.WALK_SPEED)
        tower.step(g, 1/120, jump=True)
        self.assertGreater(g.tower_vx, tower.WALK_SPEED*.9)
        for _ in range(110):
            tower.step(g, 1/120)
        self.assertTrue(g.tower_grounded)
        self.assertEqual(g.tower_vx, 0)
        x = s['position'][0]
        tower.step(g, .02)
        self.assertEqual(s['position'][0], x)
        s['position'] = [tower.WIDTH-35., 1500.]
        g.tower_grounded = False
        g.tower_vx = tower.WALK_SPEED
        tower.step(g, 1/120, horizontal=1)
        self.assertEqual(s['position'][0], tower.WIDTH-35.)
        self.assertEqual(g.tower_vx, 0)
        g.tower_vx = 180.
        tower.recover(g)
        self.assertEqual(g.tower_vx, 0)

    def test_air_momentum_is_consistent_across_simulation_rates(self):
        positions = []
        for dt in (1/60, 1/120):
            g = fake_game()
            s = tower.state(g.village)
            s.update(stage=2,position=[600.,400.])
            g.tower_grounded = False
            g.tower_vy = -200.
            for direction, duration in ((1,.3),(0,.2),(-1,.2)):
                for _ in range(round(duration/dt)):
                    tower.step(g, dt, horizontal=direction)
            positions.append((s['position'][0], g.tower_vx))
        self.assertAlmostEqual(positions[0][0], positions[1][0], delta=.5)
        self.assertAlmostEqual(positions[0][1], positions[1][1], delta=.5)

    def test_each_profile_certifies_full_range_and_rejects_previous_gain(self):
        for kind in tower.EDITOR_KEYS:
            c = design(kind)
            before = deepcopy(c.runtime_snapshot())
            self.assertTrue(adventure.certify(c, kind)[0], kind)
            self.assertEqual(before, c.runtime_snapshot())
            blank = Circuit(terminals=edge_terminals(('A', 'B', 'C')))
            self.assertFalse(adventure.certify(blank, kind)[0])
            ports = {p['name']: pos for pos,p in blank.terminals.items()}
            blank.connect(ports['C'], ports['OUT'], 0)
            self.assertFalse(adventure.certify(blank, kind)[0])
        self.assertFalse(adventure.certify(design('jetpack_0'), 'jetpack_1')[0])
        self.assertFalse(adventure.certify(design('jetpack_1'), 'jetpack_2')[0])

    def test_complete_climb_uses_real_designs_at_every_wear_stage(self):
        for dt in (1/120, 1/60):
            with self.subTest(dt=dt):
                g = fake_game()
                s = tower.state(g.village)
                designs = adventure.state(g.village)['designs']
                for i in range(1,len(tower.PLATFORMS)):
                    designs[tower.editor_key(s)] = design(tower.editor_key(s)).snapshot()
                    if s['stage'] == 2:
                        designs['tower_vent'] = design('tower_vent').snapshot()
                    fly_to(g, i, dt)
                self.assertEqual(s['checkpoint'], tower.SUMMIT)
                self.assertEqual(s['falls'], 0)
                self.assertFalse(s['complete'])
                self.assertFalse(g.tower_firing)
                g.adventure_modal = None
                tower.interact(g)
                self.assertTrue(s['complete'])
                self.assertEqual(manufacturing.state(g.village)['unlocks'], ['steam_accumulator'])

    def test_certificate_without_board_does_not_fly_and_thrust_uses_output(self):
        g = fake_game()
        s = tower.state(g.village)
        adventure.state(g.village)['jetpack_0'] = True
        minimum = s['position'][1]
        for frame in range(240):
            tower.step(g, 1/120, thrust=True, jump=frame == 0)
            minimum = min(minimum, s['position'][1])
        self.assertGreater(minimum,tower.PLATFORMS[0][1]-80)  # Jump alone cannot reach the next deck.
        adventure.state(g.village)['designs']['jetpack_0'] = design('jetpack_0').snapshot()
        self.assertEqual(tower.output(g, 'jetpack_0', (12,0,3)), 3)
        self.assertEqual(tower.output(g, 'jetpack_0', (2,0,3)), 0)
        self.assertEqual(tower.output(g, 'jetpack_0', (12,8,3)), 0)

    def test_closed_shutters_and_steam_cannot_be_bypassed(self):
        g = fake_game()
        s = tower.state(g.village)
        for stage,barrier in ((0,layout.ceiling(0)),(1,layout.ceiling(1)),(2,layout.VENT_Y+45)):
            s.update(stage=stage,position=[600.,float(barrier+1)],checkpoint=tower.STATIONS[stage])
            g.tower_vy = -300
            g.tower_grounded = False
            tower.step(g, .02)
            self.assertGreaterEqual(s['position'][1], barrier)
        adventure.state(g.village)['designs']['tower_vent'] = design('tower_vent').snapshot()
        s['position'] = [600.,layout.VENT_Y+46.]
        g.tower_vy = -260
        tower.step(g,.02)
        self.assertLess(s['position'][1],layout.VENT_Y+45)

    def test_falls_recall_and_reload_preserve_stage_designs_and_rewards(self):
        g = fake_game()
        s = tower.state(g.village)
        s.update(stage=2,checkpoint=tower.VENT_STATION,position=[1400.,tower.PLATFORMS[tower.VENT_STATION][1]+500.],pressure=0,heat=9)
        adventure.state(g.village)['designs']['jetpack_2'] = design('jetpack_2').snapshot()
        tower.step(g,.01)
        self.assertEqual(s['position'],tower.landing_position(tower.VENT_STATION))
        self.assertEqual((s['falls'],s['pressure'],s['heat']),(1,5.,0.))
        self.assertEqual(adventure.state(g.village)['health'],75)
        before=deepcopy(g.village.manufacturing)
        loaded=Village(**json.loads(json.dumps(asdict(g.village))))
        self.assertEqual(tower.state(loaded),s)
        self.assertEqual(loaded.manufacturing,before)
        tower.recover(g)
        self.assertEqual(s['falls'],1)

    def test_reward_applies_once_to_new_batches_with_real_material_costs(self):
        g=fake_game();v=g.village;s=tower.state(v)
        v.coins=100;v.material_inventory={'metal':10,'fuel':10,'fittings':10}
        self.assertTrue(manufacturing.buy_equipment(v,'bench',(0,0))[0])
        machine=manufacturing.state(v)['equipment'][0]
        manufacturing.start_batch(v,machine['id'])
        self.assertEqual(machine['busy'],12)
        s.update(stage=2,checkpoint=tower.SUMMIT,position=tower.landing_position(tower.SUMMIT))
        tower.interact(g)
        self.assertEqual(machine['busy'],12)  # No retroactive rewrite of running work.
        manufacturing.update(v,12)
        materials=deepcopy(v.material_inventory)
        manufacturing.start_batch(v,machine['id'])
        self.assertAlmostEqual(machine['busy'],9.6)
        for key,amount in manufacturing.RECIPE.items():
            self.assertEqual(v.material_inventory[key],materials[key]-amount)
        s['complete']=False  # Even a migrated completion flag cannot stack the upgrade.
        tower.interact(g)
        self.assertEqual(manufacturing.state(v)['unlocks'].count('steam_accumulator'),1)


class TowerUITests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        root=Path(self.temp.name)
        self.patches=[patch('game.SAVES_DIR',root/'saves'),patch('game.SAVE_FILE',root/'old.json'),patch('game.DESIGNS_FILE',root/'designs.json')]
        for item in self.patches:item.start()
        self.g=Game();self.g.start_slot(1)

    def tearDown(self):
        pygame.quit()
        for item in reversed(self.patches):item.stop()
        self.temp.cleanup()

    def key(self,key):
        self.g.handle_event(pygame.event.Event(pygame.KEYDOWN,key=key,mod=0,unicode=''))

    def enter(self):
        adventure.state(self.g.village)['expansion_complete']=True
        tower.enter(self.g)
        adventure.close_notice(self.g)

    def test_actual_maintenance_route_updates_specification_and_then_selects_exhaust(self):
        g=self.g;self.enter()
        for stage in range(3):
            if stage:
                for landing in range(tower.STATIONS[stage-1]+1,tower.STATIONS[stage]+1):
                    fly_to(g,landing)
                adventure.close_notice(g)
                self.key(pygame.K_e)
            else:
                self.key(pygame.K_g)
            self.assertEqual(g.adventure_editor,f'jetpack_{stage}')
            title,lines=g.task_description()
            self.assertIn(f'Stage {stage+1} of 3',title)
            minimum,heat,gain=((3,8,1),(2,7,2),(1,6,3))[stage]
            self.assertIn(f'OUT = C × {gain} only when A ≥ {minimum} and B < {heat}.',lines)
            if stage:self.assertIn('Upgrade:',lines[-1])
            g.draw()  # Automatic specification and the header use the same task.
            self.key(pygame.K_ESCAPE)
            self.key(pygame.K_h)
            self.assertEqual(adventure.specification(g),(title,lines))
            self.key(pygame.K_ESCAPE)
            if stage:self.assertFalse(adventure.validate(g)[0])  # Copied old board must fail.
            g.circuit=design(g.adventure_editor)
            self.assertTrue(adventure.validate(g)[0])
            adventure.close_editor(g)
        self.key(pygame.K_e)
        self.assertEqual(g.adventure_editor,'tower_vent')
        self.assertIn('exhaust',g.task_description()[0])
        g.circuit=design('tower_vent');self.assertTrue(adventure.validate(g)[0])
        adventure.close_editor(g)
        self.key(pygame.K_g)
        self.assertEqual(g.adventure_editor,'jetpack_2')
        self.assertIn('Stage 3 of 3',g.task_description()[0])

    def test_tower_shadow_is_only_drawn_on_ground_in_the_tower_palette(self):
        g=self.g;self.enter()
        for grounded,expected in ((True,(19,34,37)),(False,None)):
            g.tower_grounded=grounded
            with patch.object(g.town,'_villager',wraps=g.town._villager) as draw_actor:
                g.draw()
                self.assertEqual(draw_actor.call_args.kwargs['shadow_color'],expected)
        # Exercise the shared sprite renderer as well as its scene arguments.
        for color in ((19,34,37),None):
            surface=pygame.Surface((100,110));surface.fill((1,2,3))
            g.town._villager(surface,50,65,(61,121,115),name='Boole',shadow_color=color)
            pixels=[tuple(surface.get_at((x,y)))[:3] for x in range(100) for y in range(110)]
            self.assertNotIn((83,104,78),pixels)
            self.assertEqual((19,34,37) in pixels,color is not None)

    def test_expeditions_have_no_passive_health_loss_or_player_hunger(self):
        from collections import defaultdict
        g=self.g;self.enter()
        s=adventure.state(g.village);s.update(health=55,hunger=0)
        with patch('pygame.key.get_pressed',return_value=defaultdict(bool)):
            for _ in range(600):tower.update(g,.1)
            self.assertEqual(s['health'],55);self.assertNotIn('hunger',s)
            adventure.enter(g)
            for _ in range(600):adventure.update(g,.1)
            self.assertEqual(s['health'],55);self.assertNotIn('hunger',s)

    def test_tower_hazards_cost_health_and_incapacitation_preserves_checkpoint(self):
        g=self.g;self.enter()
        s=tower.state(g.village);health=adventure.state(g.village)
        s.update(stage=2,checkpoint=tower.VENT_STATION,position=[600.,layout.VENT_Y+46.])
        g.tower_grounded=False;g.tower_vy=-260
        tower.step(g,.02)
        self.assertEqual(health['health'],75)
        self.assertEqual(s['position'],tower.landing_position(tower.VENT_STATION))
        self.assertEqual(s['falls'],0)
        g.village.player_bread=1;adventure.eat(g)
        self.assertEqual(health['health'],100)
        for _ in range(4):tower.fall(g)
        self.assertEqual(g.scene,'town')
        self.assertEqual(health['health'],40)
        self.assertEqual((s['stage'],s['checkpoint']),(2,tower.VENT_STATION))
        tower.enter(g)
        self.assertEqual(s['position'],tower.landing_position(tower.VENT_STATION))
        self.assertEqual(health['health'],40)

    def test_unlock_editor_isolation_pause_and_real_slot_roundtrip(self):
        g=self.g
        self.assertFalse(tower.enter(g))
        self.enter()
        original=g.circuit.snapshot()
        self.key(pygame.K_g)
        self.assertEqual(g.scene,'workshop')
        self.assertEqual(g.adventure_editor,'jetpack_0')
        g.draw()
        village=deepcopy(vars(g.village));g.update(2)
        self.assertEqual(vars(g.village),village)
        self.key(pygame.K_ESCAPE)  # Specification.
        g.circuit=design('jetpack_0')
        self.assertTrue(adventure.validate(g)[0])
        self.key(pygame.K_ESCAPE)
        self.assertEqual(g.scene,'boiler_tower')
        self.assertEqual(g.circuit.snapshot(),original)
        self.key(pygame.K_ESCAPE)
        rail_before=(g.tower_rail_y,g.tower_rail_velocity,g.tower_rail_wait)
        before=deepcopy(vars(g.village));g.update(10)
        self.assertEqual(vars(g.village),before)
        self.assertEqual((g.tower_rail_y,g.tower_rail_velocity,g.tower_rail_wait),rail_before)
        self.key(pygame.K_ESCAPE)
        self.assertFalse(g.pause_menu_open)
        tower.state(g.village).update(stage=1,checkpoint=tower.STATIONS[1])
        tower.restore_checkpoint(g)
        tower.edit(g)
        self.assertEqual(g.circuit.snapshot(),design('jetpack_0').snapshot())
        g.circuit=design('jetpack_1');adventure.validate(g)
        adventure.close_editor(g)
        g.save_game();saved=deepcopy(g.village.manufacturing)
        g.return_to_menu();g.start_slot(1)
        self.assertEqual(g.village.manufacturing,saved)
        tower.enter(g)
        self.assertEqual(tower.state(g.village)['position'],tower.landing_position(tower.STATIONS[1]))
        g.draw()
        self.assertNotIn('jetpack_0',g.sandbox_draft)

    def test_modal_blocks_movement_and_reactions_start_on_close(self):
        g=self.g
        adventure.state(g.village)['expansion_complete']=True
        tower.enter(g)
        before=deepcopy(tower.state(g.village))
        tower.update(g,.1)
        self.assertEqual(tower.state(g.village),before)
        self.key(pygame.K_SPACE)
        self.assertFalse(g.tower_jump)
        self.key(pygame.K_e)
        self.assertIsNone(g.adventure_modal)
        self.assertGreater(g.adventure_speech_time,0)
        g.draw()

    def test_mosswater_travel_button_and_pause_return_clear_field_context(self):
        g=self.g
        adventure.state(g.village)['expansion_complete']=True
        adventure.enter(g);g.draw()
        g.handle_click((150,228),1)
        self.assertEqual(g.scene,'boiler_tower')
        adventure.close_notice(g)
        tower.edit(g)
        g.circuit=design('jetpack_0')
        g.pause_menu_open=True
        g.resume_in_town()
        self.assertEqual(g.scene,'town')
        self.assertFalse(adventure.active_editor(g))
        self.assertFalse(g.pause_menu_open)
        self.assertEqual(adventure.state(g.village)['drafts']['jetpack_0']['parts'],design('jetpack_0').snapshot())

    def test_retired_pack_design_can_be_reviewed_but_never_flies_again(self):
        g=self.g;self.enter()
        s=tower.state(g.village)
        s.update(stage=2,checkpoint=tower.SUMMIT,complete=True)
        tower.restore_checkpoint(g)
        self.key(pygame.K_g)
        g.circuit=design('jetpack_2')
        self.assertTrue(adventure.validate(g)[0])
        adventure.close_editor(g)
        tower.step(g,1/120,thrust=True)
        self.assertFalse(g.tower_firing)
        self.assertEqual(s['position'][1],tower.PLATFORMS[tower.SUMMIT][1])
        tower.interact(g)
        self.assertEqual(g.scene,'town')


if __name__=='__main__':unittest.main()
