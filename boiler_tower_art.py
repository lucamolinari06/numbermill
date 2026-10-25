"""Pixel-drawn tower masonry, service machinery and a compact flight readout."""
import math
import pygame

import adventure
import boiler_tower as tower
import boiler_tower_layout as layout
import ui_theme
import expedition_scenery
import expedition_ui
from ui_theme import INK, PAPER, TEAL, GOLD, COPPER, MUTED


def background():
    surface = expedition_scenery.tower_backdrop(
        (tower.WIDTH, tower.HEIGHT), tower.PLATFORMS[tower.STATIONS[1]][1],
        tower.PLATFORMS[tower.STATIONS[2]][1])
    for x in (70, 1330):
        pygame.draw.rect(surface, (22, 39, 42), (x-17, 0, 56, tower.HEIGHT))
        pygame.draw.rect(surface, (116, 94, 66), (x, 0, 18, tower.HEIGHT))
        pygame.draw.rect(surface, (170, 139, 90), (x+3, 0, 4, tower.HEIGHT))
        for y in range(0, tower.HEIGHT, 90):
            pygame.draw.rect(surface, (67, 70, 57), (x-7, y, 32, 13))
            for xx in (x-3, x+20):
                pygame.draw.circle(surface, GOLD, (xx, y+6), 2)
    # A narrow rail explains how Shannon accompanies a vertical climb.
    pygame.draw.line(surface, (22, 39, 42), (1250,layout.RAIL_TOP), (1250,layout.RAIL_BOTTOM), 18)
    for y in range(int(layout.RAIL_TOP),int(layout.RAIL_BOTTOM),24):
        pygame.draw.line(surface, (115, 126, 111), (1244,y), (1257,y), 3)
    for x in (1240, 1262):
        pygame.draw.line(surface, (170, 167, 131), (x,layout.RAIL_TOP), (x,layout.RAIL_BOTTOM), 3)
    # Condensers and copper service pipes leave the platform silhouettes clear.
    for x,y in ((tower.PLATFORMS[i][0]+260,tower.PLATFORMS[i][1]) for i in tower.STATIONS[:-1]):
        pygame.draw.rect(surface, (25, 40, 42), (x-33,y-116,70,116), border_radius=20)
        pygame.draw.rect(surface, (91, 109, 94), (x-27,y-110,55,106), border_radius=18)
        pygame.draw.rect(surface, (143, 153, 116), (x-20,y-95,8,78))
        for yy in (y-83, y-30):
            pygame.draw.rect(surface, (166, 122, 72), (x-30,yy,62,9))
        pygame.draw.circle(surface, PAPER, (x+2,y-62), 16)
        pygame.draw.circle(surface, COPPER, (x+2,y-62), 16, 3)
        pygame.draw.line(surface, INK, (x+2,y-62), (x+10,y-69), 2)
    # Large machinery recedes into the shaft; the brighter ledges remain the route.
    for cx,cy,radius in ((980 if i%12==0 else 380,tower.PLATFORMS[i][1]+80,120) for i in range(0,30,6)):
        pygame.draw.circle(surface,(28,44,46),(cx,cy),radius+20)
        pygame.draw.circle(surface,(72,85,75),(cx,cy),radius,12)
        pygame.draw.circle(surface,(95,103,83),(cx,cy),radius-11,3)
        for i in range(8):
            angle=i*math.pi/4
            end=(round(cx+math.cos(angle)*(radius-12)),round(cy+math.sin(angle)*(radius-12)))
            pygame.draw.line(surface,(62,77,69),(cx,cy),end,12)
        pygame.draw.circle(surface,(112,103,72),(cx,cy),24)
        pygame.draw.circle(surface,(29,46,45),(cx,cy),10)
        pygame.draw.lines(surface,(110,83,58),False,((cx,cy+radius+18),(cx,cy+radius+48),(1328,cy+radius+48)),9)
    for i, (left, top, width) in enumerate(tower.PLATFORMS):
        color = GOLD if i in tower.STATIONS else (129, 156, 142)
        pygame.draw.rect(surface, (19, 34, 37), (left-4, top, width+8, 27))
        pygame.draw.rect(surface, color, (left, top, width, 7))
        pygame.draw.rect(surface, (70, 88, 81), (left, top+7, width, 13))
        for x in range(left+10, left+width, 24):
            pygame.draw.rect(surface, (174, 167, 118), (x, top+11, 4, 4))
        for x in (left+18, left+width-18):
            pygame.draw.line(surface, (72, 92, 85), (x,top+22), (x+32 if x<left+width/2 else x-32,top+80), 8)
        if i in tower.CHECKPOINTS and i not in tower.STATIONS:
            pygame.draw.line(surface,(164,170,135),(left+18,top),(left+18,top-50),3)
            pygame.draw.polygon(surface,(117,199,155),((left+19,top-50),(left+48,top-44),(left+19,top-30)))
        if i in tower.STATIONS:
            # Maintenance console, not a supplied circuit solution.
            cx = left+30
            pygame.draw.rect(surface, (106, 91, 66), (cx,top-58,54,58))
            pygame.draw.rect(surface, (169, 137, 86), (cx-4,top-59,62,9))
            pygame.draw.rect(surface, (31, 64, 61), (cx+7,top-45,40,24))
            for xx in (cx+12, cx+26, cx+40):
                pygame.draw.rect(surface, GOLD, (xx,top-12,6,5))
    # Summit archive and return cage.
    cx,top=tower.landing_position(tower.SUMMIT)
    pygame.draw.rect(surface,(166,134,80),(cx-60,top-70,66,70))
    pygame.draw.rect(surface,(36,67,62),(cx-51,top-60,48,39))
    for x in (cx+45,cx+125):
        pygame.draw.line(surface,(147,148,117),(x,top-210),(x,top),5)
    for y in (top-10,top-120):
        pygame.draw.rect(surface,(124,112,79),(cx+35,y,100,10))
    for x in range(int(cx+45),int(cx+135),20):
        pygame.draw.line(surface,(103,121,109),(x,top-110),(x,top-12),2)
    return surface


def steam(surface, x, y, seconds, seed, scale=1):
    for i in range(8):
        phase = (seconds*1.5+i*.19+seed*.13) % 1.5
        radius = round((3+phase*6)*scale)
        color = tuple(round(a+(b-a)*phase/1.5) for a,b in zip((220,222,188),(68,91,86)))
        pygame.draw.circle(surface, color, (round(x+math.sin(i*3+phase)*10*scale), round(y+phase*55*scale)), radius)


def draw_hazards(g,seconds,ox,oy):
    for hazard in layout.HAZARDS:
        if not oy-320 < hazard['y'] < oy+850:continue
        reading=layout.hazard_state(hazard,seconds)
        x,y=round(hazard['x']-ox),round(hazard['y']-oy)
        rect=reading['rect'].move(-ox,-oy)
        status=reading['status']
        signal=(227,104,67) if status=='active' else GOLD if status=='warning' else (114,194,155)
        if hazard['kind']=='steam':
            pygame.draw.rect(g.screen,(105,107,86),(x-29,y+273,58,16))
            for xx in range(x-20,x+25,10):pygame.draw.line(g.screen,INK,(xx,y+273),(xx,y+284),3)
            if reading['active']:
                pygame.draw.rect(g.screen,(123,142,131),rect,1)
                for i in range(22):
                    yy=rect.bottom-((seconds*170+i*29)%rect.height)
                    xx=x+math.sin(i*2.3+seconds*5)*14
                    pygame.draw.circle(g.screen,(192,211,190) if i%2 else (147,174,163),(round(xx),round(yy)),9+i%4)
            elif status=='warning':
                for yy in range(rect.top,rect.bottom,20):
                    pygame.draw.line(g.screen,GOLD,(rect.left,yy),(rect.left,yy+9),2)
                    pygame.draw.line(g.screen,GOLD,(rect.right,yy),(rect.right,yy+9),2)
            pygame.draw.circle(g.screen,signal,(x+42,y+280),6)
            ui_theme.fit_text(g.screen,g.tiny,'STEAM / '+status.upper(),x-85,y+298,205,signal)
        elif hazard['kind']=='gear':
            pygame.draw.line(g.screen,(97,105,92),(x-88,y+40),(x+88,y+40),5)
            cx,cy=reading['center'];cx-=ox;cy-=oy
            for i in range(10):
                angle=seconds*3+i*math.tau/10
                a=(round(cx+math.cos(angle)*20),round(cy+math.sin(angle)*20))
                b=(round(cx+math.cos(angle)*27),round(cy+math.sin(angle)*27))
                pygame.draw.line(g.screen,COPPER,a,b,8)
            pygame.draw.circle(g.screen,(215,112,61),(round(cx),round(cy)),21)
            pygame.draw.circle(g.screen,(247,189,91),(round(cx),round(cy)),14,3)
            pygame.draw.circle(g.screen,INK,(round(cx),round(cy)),6)
            ui_theme.fit_text(g.screen,g.tiny,'HOT GEAR',x-44,y-5,125,GOLD)
        else:
            pygame.draw.rect(g.screen,(109,117,98),(x-36,y-93,72,20))
            if reading['active']:
                pygame.draw.rect(g.screen,(148,158,140),(x-10,rect.top,20,rect.height))
                pygame.draw.rect(g.screen,COPPER,(x-28,rect.bottom-17,56,17))
                for xx in range(x-23,x+25,13):pygame.draw.line(g.screen,GOLD,(xx,rect.bottom-15),(xx+9,rect.bottom-3),3)
            elif status=='warning':
                target=reading['warning_rect'].move(-ox,-oy)
                for yy in range(target.top,target.bottom,22):pygame.draw.line(g.screen,GOLD,(x,yy),(x,yy+10),2)
            pygame.draw.circle(g.screen,signal,(x+47,y-83),6)
            ui_theme.fit_text(g.screen,g.tiny,'PISTON / '+status.upper(),x+65,y-117,220,signal)


def draw(g):
    current = tower.state(g.village)
    p = tower.profile(current)
    x, y = current['position']
    ox = round(max(0, min(tower.WIDTH-1280, x-640)))
    oy = round(max(0, min(tower.HEIGHT-760, y-460)))
    if not hasattr(g, 'tower_background'):
        g.tower_background = background()
    g.screen.blit(g.tower_background, (-ox, -oy))
    seconds = getattr(g, 'tower_time', 0.)
    # The shutters make maintenance order visible and physically enforced.
    for stage, yy in ((1,layout.ceiling(0)), (2,layout.ceiling(1))):
        if current['stage'] < stage:
            pygame.draw.rect(g.screen, (112,104,75), (90-ox,yy-oy-76,1240,22))
            for xx in range(100,1330,40):
                pygame.draw.line(g.screen, GOLD, (xx-ox,yy-oy-74), (xx+18-ox,yy-oy-56), 4)
    if not current['vent_open']:
        for xx in range(100,1340,50):
            steam(g.screen, xx-ox, layout.VENT_Y-5-oy, seconds, xx, .8)
        pygame.draw.line(g.screen, COPPER, (90-ox,layout.VENT_Y-oy), (1330-ox,layout.VENT_Y-oy), 6)
    draw_hazards(g,current['hazard_time'],ox,oy)
    for i,label in zip(tower.STATIONS,('01 / SERVICE DOCK','02 / WORN SEALS','03 / EXHAUST DECK','04 / CONDENSER ARCHIVE')):
        left, top, width = tower.PLATFORMS[i]
        if -40 < top-oy < 800:
            ui_theme.fit_text(g.screen, g.tiny, label, left+8-ox, top+30-oy, width-16, GOLD)
            if current['checkpoint'] == i:
                pygame.draw.circle(g.screen, (152,211,164), (left+57-ox,top-34-oy), 5)
    for i in tower.CHECKPOINTS:
        if i in tower.STATIONS:continue
        left,top,width=tower.PLATFORMS[i]
        if -40 < top-oy < 800:
            label='REST / SAVED' if current['checkpoint']>=i else 'REST / CHECKPOINT'
            ui_theme.fit_text(g.screen,g.tiny,label,left+8-ox,top+30-oy,width-16,(152,211,164))
    # Existing pixel characters keep Boole and Shannon visually consistent.
    moving = not g.tower_grounded or abs(getattr(g, 'tower_last_x', x)-x) > .05
    g.tower_last_x = x
    facing = getattr(g, 'tower_facing', 'east')
    g.town._villager(g.screen, round(x-ox), round(y-oy-18), TEAL, seconds*8, moving, facing, 'Boole',
                     shadow_color=(19,34,37) if g.tower_grounded else None)
    if current['checkpoint'] != tower.SUMMIT:
        pack_x = round(x-ox+(-14 if facing == 'east' else 14))
        pygame.draw.rect(g.screen, COPPER, (pack_x-7,round(y-oy-48),14,27), border_radius=3)
        pygame.draw.rect(g.screen, GOLD, (pack_x-8,round(y-oy-42),16,5))
        for crack in range(current['stage']):
            yy=round(y-oy-34+crack*7)
            pygame.draw.lines(g.screen,INK,False,((pack_x-5,yy),(pack_x,yy+3),(pack_x-2,yy+6)),2)
        if g.tower_firing:
            steam(g.screen,pack_x,y-oy-20,seconds,0,.7)
    companion = g.town.companion
    companion.facing = 'west'
    companion.seconds = seconds
    rail_y = getattr(g, 'tower_rail_y', y)
    companion.draw(g.screen, 1250-ox, round(rail_y-oy-20))
    pygame.draw.rect(g.screen, GOLD, (1233-ox,round(rail_y-oy),36,5))
    health = adventure.state(g.village)
    expedition_ui.health(g,'Boiler Tower',('Boiler Galleries','Driveworks','Condenser Crown')[current['stage']],health['health'])
    expedition_ui.panel(g.screen,(952,20,304,147))
    ui_theme.fit_text(g.screen,g.small,'Pack retired' if current['checkpoint']==tower.SUMMIT else p['name'],970,33,267,expedition_ui.TEXT)
    expedition_ui.meter(g,'Pressure',current['pressure'],12,62,expedition_ui.MINT,p['minimum'])
    expedition_ui.meter(g,'Heat',current['heat'],10,88,expedition_ui.AMBER,p['heat'])
    drive = tower.output(g,tower.editor_key(current),tower.readings(current,g.tower_firing)) if current['checkpoint'] != tower.SUMMIT else 0
    ui_theme.fit_text(g.screen,g.tiny,f"Throttle {current['throttle']} [R] / Valve {drive}",970,117,268,expedition_ui.TEXT)
    ui_theme.fit_text(g.screen,g.tiny,'Land to refill and cool',970,141,268,expedition_ui.DIM)
    station = tower.at_station(g)
    if station is not None:
        g.button((1000,180,256,32),'Saved pack circuit [G]' if current['checkpoint']==tower.SUMMIT else 'Jetpack circuit [G]',lambda:tower.edit(g),small=True)
        if station == tower.VENT_STATION:
            g.button((1000,221,256,32),'Exhaust circuit [V]',lambda:tower.edit(g,True),small=True)
        if station != tower.SUMMIT or current['complete']:
            g.button((1000,262,256,32),'Return to village',lambda:tower.leave(g),small=True)
    g.button((20,116,126,30),'Bread '+str(g.village.player_bread)+' [F]',lambda:adventure.eat(g),small=True)
    g.button((154,116,166,30),'Recall [Bksp]',lambda:tower.recover(g),small=True)
    controls = ('DEV: WASD / arrows  fly freely    G  maintenance    BACKSPACE  recall    ESC  pause'
                if tower.developer_mode.enabled(g) else
                'A/D Steer   Space Jump   W / ↑ Thrust   R Throttle   Esc Pause')
    expedition_ui.controls(g,controls,width=790 if tower.developer_mode.enabled(g) else 710)
    if station is not None:
        label = ('RETURN TO VILLAGE' if station == 0 or current['complete'] else
                 'RECOVER ACCUMULATOR' if station == tower.SUMMIT else
                 'REPAIR EXHAUST' if tower.maintenance_task(g) == 'tower_vent' else
                 'UPGRADE JETPACK' if tower.editor_key(current) not in adventure.state(g.village)['designs'] else 'EDIT JETPACK')
        g.button((456,660,368,38),label+' [E]',lambda:tower.interact(g),small=True)
    elif not tower.developer_mode.enabled(g) and tower.editor_key(current) not in adventure.state(g.village)['designs']:
        ui_theme.fit_text(g.screen,g.small,'Return to a brass landing to build this stage’s controller.',360,670,760,GOLD)
    elif g.tower_grounded and abs(y-tower.PLATFORMS[current['checkpoint']][1])<1:
        remaining=tower.STATIONS[min(3,current['stage']+1)]-current['checkpoint']
        expedition_ui.panel(g.screen,(390,660,500,38))
        ui_theme.fit_text(g.screen,g.tiny,f'Checkpoint saved / {remaining} landings to maintenance',410,672,460,expedition_ui.MINT)
    if getattr(g,'adventure_speech_time',0)>0:
        ui_theme.draw_panel(g.screen,(290,542,700,76))
        ui_theme.wrapped_text(g.screen,g.small,g.adventure_speech,310,557,660,INK,line_height=22,max_lines=2)
    if getattr(g,'adventure_modal',None):
        shade=pygame.Surface((1280,760),pygame.SRCALPHA);shade.fill((15,28,24,180));g.screen.blit(shade,(0,0));g.buttons=[]
        ui_theme.draw_panel(g.screen,(290,218,700,342))
        ui_theme.fit_text(g.screen,g.heading,g.adventure_modal_title,316,241,648,TEAL)
        ui_theme.wrapped_text(g.screen,g.font,g.adventure_modal,316,290,648,INK,line_height=25,max_lines=7)
        g.button((774,500,186,38),'CONTINUE',lambda:adventure.close_notice(g),small=True)
