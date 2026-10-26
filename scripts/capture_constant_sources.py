"""Render and exercise constant-number editing using disposable saves."""
import argparse
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--smoke',action='store_true')
    args=parser.parse_args()
    if not args.smoke:os.environ.setdefault('SDL_VIDEODRIVER','dummy')
    import pygame
    from game import Game
    from circuit import Part
    import constant_editor
    output=ROOT/'testing-screenshots'/'constant-sources';output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as folder:
        root=Path(folder)
        with patch('game.SAVES_DIR',root/'saves'),patch('game.SAVE_FILE',root/'old.json'),patch('game.DESIGNS_FILE',root/'designs.json'):
            g=Game();g.start_slot(1);g.open_circuit_bench();g.bench_component_group='Logic'
            def key(code,text=''):
                g.handle_key(pygame.event.Event(pygame.KEYDOWN,key=code,unicode=text,mod=0))
            def point(pos):
                bx,by,cell=g.board_metrics()
                return bx+(pos[0]+.5)*cell,by+(pos[1]+.5)*cell
            def capture(name):
                g.draw();pygame.image.save(g.screen,output/name)
            g.select_part('CONSTANT');g.handle_click(point((5,3)),1)
            for char in '65535':key(ord(char),char)
            capture('edit-number.png')
            g.handle_click(constant_editor.APPLY.center,1)
            g.circuit.set_part((5,6),Part('CONSTANT',value=7))
            g.circuit.set_part((9,3),Part('DIV'))
            g.circuit.connect((5,3),(9,3),0)
            g.circuit.connect((5,6),(9,3),1,((7.5,6.5),(9.5,6.5)))
            out=next(pos for pos,p in g.circuit.terminals.items() if p['output'])
            g.circuit.connect((9,3),out,0)
            for _ in range(8):g.circuit.tick()
            assert g.circuit.output_value()==9362
            g.paused=True;capture('wired-constants.png')
            g.handle_click(point((5,3)),1)
            for char in '65536':key(ord(char),char)
            key(pygame.K_RETURN);assert g.constant_editor['error']
            capture('invalid-number.png');key(pygame.K_ESCAPE)
            g.save_game();g.start_slot(1);g.open_circuit_bench()
            assert g.circuit.parts[(5,3)].value==65535
            assert g.circuit.evaluate(0,0)==(9362,True)
            if args.smoke:
                for _ in range(90):
                    pygame.event.pump();g.draw();g.clock.tick(60)
                (output/'smoke.log').write_text('Native window: placement, typed value, mouse apply, range rejection, cancel, wiring, numeric output and save/reload passed.\n',encoding='utf-8')
            pygame.quit()
    print(output)


if __name__=='__main__':main()
