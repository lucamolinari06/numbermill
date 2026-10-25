"""Authored platforming route and deterministic, telegraphed machinery hazards."""
import math
import pygame

VERSION = 2
WIDTH, HEIGHT = 1460, 5500
PLATFORM_THICKNESS = 22
BODY_HALF, BODY_HEIGHT = 13., 56.
# Ten traversals between each circuit stop; the route doubles back across the shaft.
CENTRES = (270,570,870,1150,850,550,250,550,850,1150,850,
           550,250,550,850,1150,850,550,250,550,850,
           1150,850,550,250,550,850,1150,850,550,850)
STATIONS = (0,10,20,30)
CHECKPOINTS = (0,4,7,10,14,17,20,24,27,30)
SUMMIT = STATIONS[-1]
VENT_STATION = STATIONS[2]
PLATFORMS = tuple((cx-(300 if i in STATIONS else 200 if i in CHECKPOINTS else 160)//2,
                   5300-i*155, 300 if i in STATIONS else 200 if i in CHECKPOINTS else 160)
                  for i,cx in enumerate(CENTRES))
VENT_Y = PLATFORMS[VENT_STATION][1]-135
RAIL_TOP, RAIL_BOTTOM = 180., 5360.


def landing_position(index):
    left, top, width = PLATFORMS[index]
    return [left+width/2, float(top)]


def ceiling(stage):
    return PLATFORMS[STATIONS[stage+1]][1]-70 if stage < 2 else 160.


def body(x, y):
    return pygame.Rect(round(x-BODY_HALF),round(y-BODY_HEIGHT),BODY_HALF*2,BODY_HEIGHT)


# Targets identify a crossing, not a safe landing. Every hazard leaves both
# platform centres clear so players can wait, read its cycle and refill there.
HAZARDS = tuple(dict(kind=('steam','gear','piston')[n%3], target=i,
                    x=(CENTRES[i-1]+CENTRES[i])/2, y=PLATFORMS[i][1]-110,
                    offset=(n*.71)%6)
                for n,i in enumerate((2,4,6,8,9,12,14,16,18,19,22,24,26,28,29)))


def hazard_state(hazard, seconds):
    """One shared reading drives both the drawing and damaging volume."""
    kind=hazard['kind'];x,y=hazard['x'],hazard['y']
    phase=(seconds+hazard['offset'])%6
    status='warning' if 2.8 <= phase < 3.8 else 'active' if 3.8 <= phase < 5.1 else 'safe'
    if kind=='steam':
        rect=pygame.Rect(x-22,y,44,275)
        return dict(status=status,rect=rect,active=status=='active',phase=phase)
    if kind=='gear':
        # A continuously moving hot wheel: fly past when it clears your line.
        cx=x+math.sin((seconds+hazard['offset'])*math.tau/4.6)*78
        cy=y+40+math.sin((seconds+hazard['offset'])*math.tau/4.6)*22
        return dict(status='active',rect=pygame.Rect(cx-27,cy-27,54,54),
                    active=True,center=(cx,cy),radius=27,phase=phase)
    extension=0.
    if status=='active':
        t=phase-3.8
        extension=240*min(1., t/.3, (1.3-t)/.35)
    rect=pygame.Rect(x-28,y-75,56,max(0.,extension))
    return dict(status=status,rect=rect,active=extension>0,phase=phase,
                warning_rect=pygame.Rect(x-28,y-75,56,240))


def touching(hazard, reading, actor):
    if not reading['active'] or not reading['rect'].colliderect(actor):
        return False
    if hazard['kind']=='gear':
        cx,cy=reading['center']
        nearest=(max(actor.left,min(cx,actor.right)),max(actor.top,min(cy,actor.bottom)))
        return math.dist(nearest,(cx,cy)) < reading['radius']
    return True
