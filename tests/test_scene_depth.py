"""Rendered overlap checks: actors behind props hide; actors in front remain."""
import os
os.environ.setdefault("SDL_VIDEODRIVER","dummy")
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pygame
import adventure
import scene_depth
import ui_theme
from game import Game
from town import decoration_layout,WORLD_W,WORLD_H

MARKER=(255,0,255)


class SceneDepthTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();root=Path(self.temp.name)
        self.patches=[patch("game.SAVES_DIR",root/"saves"),patch("game.SAVE_FILE",root/"save.json"),patch("game.DESIGNS_FILE",root/"designs.json")]
        for item in self.patches:item.start()
        self.g=Game();self.g.start_slot(1)

    def tearDown(self):
        for item in reversed(self.patches):item.stop()
        pygame.quit();self.temp.cleanup()

    def test_town_foliage_hides_player_npc_and_shannon_only_from_behind(self):
        g=self.g;t=g.town
        _,tx,ty,_=next(p for p in decoration_layout() if p[0]=="tree" and p[1]==530)
        def marker(surface,x,y,*args,**kwargs):pygame.draw.rect(surface,MARKER,(x-10,y-40,20,56))
        for who in ("Boole","Ada","Shannon"):
            for front in (False,True):
                with self.subTest(who=who,front=front):
                    ay=ty+25 if front else ty-20
                    t.player_x,t.player_y=(tx,ay) if who=="Boole" else (tx+100,ty)
                    t.display_people["Ada"]=[tx,ay] if who=="Ada" else [0,0]
                    t.companion.position=(tx,ay) if who=="Shannon" else (0,0)
                    def person(surface,x,y,*args):
                        if args[-1]==who:marker(surface,x,y)
                    with patch.object(t,"_villager",side_effect=person),patch.object(t.companion,"draw",side_effect=marker if who=="Shannon" else lambda *a:None):
                        t.draw(g.screen,(g.small,g.font,g.heading,g.big),g.village,None,"")
                    camera=(max(0,min(WORLD_W-1280,int(t.player_x-640))),max(0,min(WORLD_H-760,int(t.player_y-380))))
                    pixel=g.screen.get_at((tx-camera[0],ty+(3 if front else -50)-camera[1]))[:3]
                    self.assertEqual(pixel==MARKER,front)

    def test_field_machinery_hides_both_companions_only_from_behind(self):
        g=self.g;adventure.enter(g);g.adventure_speech_time=0
        def marker(surface,x,y,*args,**kwargs):pygame.draw.rect(surface,MARKER,(x-10,y-40,20,56))
        for who in ("Boole","Shannon"):
            for front in (False,True):
                with self.subTest(who=who,front=front):
                    ay=525 if front else 460
                    pos=(1080,ay) if who=="Boole" else (1000,525)
                    adventure.state(g.village)["position"]=list(pos)
                    g.adventure_companion.position=(1080,ay) if who=="Shannon" else (0,0)
                    with patch.object(g.town,"_villager",side_effect=marker if who=="Boole" else lambda *a:None),patch.object(g.adventure_companion,"draw",side_effect=marker if who=="Shannon" else lambda *a:None):
                        adventure.draw(g)
                    ox=max(0,min(780,pos[0]-640));oy=max(0,min(280,pos[1]-420))
                    pixel=g.screen.get_at((1080-ox,(495 if front else 465)-oy))[:3]
                    self.assertEqual(pixel==MARKER,front)

    def test_cached_props_are_reused_and_distance_labels_are_scaled_clean_ranges(self):
        from test_adventure import design
        g=self.g;adventure.enter(g);props=g.adventure_props
        current=adventure.state(g.village)
        current.update(decoder=True,receiver=True,position=[780.,420.])
        current['designs']['decoder']=design('decoder').snapshot()
        labels=[];original=ui_theme.fit_text
        def capture(*args,**kwargs):labels.append(str(args[2]));return original(*args,**kwargs)
        with patch('ui_theme.fit_text',side_effect=capture):adventure.draw(g)
        self.assertIn('90–100 paces',labels)
        current.update(receiver_upgrade=True,position=[1630.,420.]);labels.clear()
        with patch('ui_theme.fit_text',side_effect=capture):adventure.draw(g)
        self.assertIn('10–12.5 paces',labels)
        adventure.enter(g)
        self.assertIs(g.adventure_props,props)

    def test_transparent_sprite_corners_do_not_erase_actors(self):
        cache=scene_depth.Cache((100,100))
        cache.capture((20,20,60,60),80,lambda s:pygame.draw.circle(s,(0,100,0),(50,40),10))
        props=cache.finish();surface=pygame.Surface((100,100));surface.fill((1,2,3))
        scene_depth.draw(surface,(0,0),props,[(30,lambda:pygame.draw.rect(surface,MARKER,(25,25,50,50)))])
        self.assertEqual(surface.get_at((30,30))[:3],MARKER)
        self.assertEqual(surface.get_at((50,40))[:3],(0,100,0))
