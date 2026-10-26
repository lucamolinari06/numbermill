"""The first visitable canal settlement, reached by the restored steam launch."""
import math
import pygame
import canal_art
import canal_layout as layout
import canal_progress
import scene_depth
import town_atmosphere
import ui_theme
from town_companion import Companion
from ui_theme import INK, MUTED, PAPER, TEAL, COPPER, GOLD


def state(village):
    return canal_progress.state(village)


def _runtime(g):
    if not getattr(g,'canal_runtime',None):
        current=state(g.village)
        current['position']=layout.safe_position(current['position'])
        g.canal_runtime=dict(companion=Companion(current['position'],layout.blocked),
                             facing='south',phase=0.,moving=False,modal=None,
                             message='',message_time=0.)
    return g.canal_runtime


def _prepare_art(g):
    if not hasattr(g,'canal_art_cache'):
        g.canal_art_cache=canal_art.build_scene()


def enter(g,resume=False):
    if not canal_progress.can_travel(g.village):
        if not resume:g.toast(canal_progress.status(g.village))
        return False
    current=state(g.village)
    first=not current['visited']
    if not resume:
        current['position']=list(layout.ARRIVAL)
        current['trips']+=1
    current['position']=layout.safe_position(current['position'])
    current['visited']=True
    g.scene='canal';g.town_dialogue=None
    g.buttons.clear()
    if not resume:g.opening_reveal=0. if g.reduced_motion else .35
    g.canal_runtime=None
    rt=_runtime(g)
    _prepare_art(g)
    if first and not resume:rt['modal']='arrival'
    if not resume:g.save_game()
    return True


def leave(g):
    from canal_departure import RETURN_POSITION
    g.scene='town';g.town_dialogue=None
    g.buttons.clear()
    g.opening_reveal=0. if g.reduced_motion else .35
    g.town.player_x,g.town.player_y=RETURN_POSITION
    g.town.companion.reset(RETURN_POSITION)
    if getattr(g,'canal_runtime',None):g.canal_runtime['modal']=None
    g.save_game()


def modal_active(g):
    return bool(getattr(g,'canal_runtime',None) and g.canal_runtime.get('modal'))


def near(g):
    position=state(g.village)['position']
    nearby=[(math.dist(position,point),key) for key,point in layout.POINTS.items()]
    distance,key=min(nearby)
    return key if distance<86 else None


def _notice(g,message):
    rt=_runtime(g);rt['message']=message;rt['message_time']=7.


def _close(g):
    _runtime(g)['modal']=None
    g.buttons.clear()


def interact(g,key=None):
    if modal_active(g):
        _close(g);return
    key=key or near(g)
    if key not in layout.POINTS:return
    # Mouse targets and keyboard prompts have the same physical reach.
    if math.dist(state(g.village)['position'],layout.POINTS[key])>=86:return
    rt=_runtime(g);rt['modal']=key;rt['message']=''
    g.buttons.clear()
    current=state(g.village)
    if key in layout.RESIDENTS and key not in current['met']:
        current['met'].append(key);g.save_game()
    if key=='waterworks':
        if canal_progress.discover_clue(g.village):g.save_game()


def _deliver(g):
    ok,message=canal_progress.deliver_request(g.village)
    _notice(g,message)
    if ok:g.save_game()


def _buy(g):
    ok,message=canal_progress.buy_bread(g.village)
    _notice(g,message)
    if ok:g.save_game()


def handle_key(g,event):
    rt=_runtime(g)
    if rt['modal']:
        if event.key in (pygame.K_ESCAPE,pygame.K_e,pygame.K_RETURN,pygame.K_KP_ENTER):_close(g)
        elif event.key==pygame.K_1:
            if rt['modal']=='boat':leave(g)
            elif rt['modal']=='Sela':_buy(g)
            elif rt['modal'] in ('Ivo','cistern'):_deliver(g)
        return True
    if event.key==pygame.K_e:interact(g);return True
    return event.key!=pygame.K_ESCAPE


def handle_click(g,pos,button=1):
    if button!=1:return
    for rect,action in reversed(g.buttons):
        if rect.collidepoint(pos):action();return
    if modal_active(g):return
    camera=layout.camera(state(g.village)['position'],g.screen.get_size())
    world=(pos[0]+camera[0],pos[1]+camera[1])
    for name in layout.RESIDENTS:
        x,y=layout.POINTS[name]
        if pygame.Rect(x-24,y-47,48,73).collidepoint(world):
            interact(g,name);return


def update(g,dt):
    rt=_runtime(g)
    if rt['modal']:return
    dt=max(0.,min(.1,float(dt)))
    current=state(g.village)
    current['visual_time']+=dt
    rt['message_time']=max(0.,rt['message_time']-dt)
    keys=pygame.key.get_pressed()
    dx=int(keys[pygame.K_d] or keys[pygame.K_RIGHT])-int(keys[pygame.K_a] or keys[pygame.K_LEFT])
    dy=int(keys[pygame.K_s] or keys[pygame.K_DOWN])-int(keys[pygame.K_w] or keys[pygame.K_UP])
    length=math.hypot(dx,dy);rt['moving']=bool(length)
    old=tuple(current['position']);via=[]
    if length:
        dx*=225*dt/length;dy*=225*dt/length
        # Small substeps prevent tunnelling across shore edges during slow frames.
        count=max(1,math.ceil(max(abs(dx),abs(dy))/4))
        for _ in range(count):
            x,y=current['position']
            if not layout.blocked(x+dx/count,y):current['position'][0]+=dx/count
            via.append(tuple(current['position']))
            if not layout.blocked(current['position'][0],y+dy/count):current['position'][1]+=dy/count
            via.append(tuple(current['position']))
        rt['facing']=('east' if dx>0 else 'west') if abs(dx)>abs(dy) else ('south' if dy>0 else 'north')
        distance=math.dist(old,current['position']);rt['phase']+=distance*.12
        rt['moving']=distance>1e-5
    rt['companion'].update(current['position'],dt,via=via)


def _resident(g,surface,name,x,y,*,seconds=0.,facing='south',portrait=False):
    details=layout.RESIDENTS[name]
    g.town._villager(surface,x,y,details['coat'],name=name,facing=facing,
                     seconds=seconds,action='idle' if portrait else details['action'],
                     shadow_color=None if portrait else (112,130,99))
    # Working dress is shared by the small portrait and world sprite.
    if name=='Mara':
        pygame.draw.rect(surface,(48,87,86),(x-11,y-43,22,7))
        pygame.draw.rect(surface,(88,128,119),(x-14,y-38,29,4))
        pygame.draw.rect(surface,GOLD,(x-3,y-41,6,3))
    elif name=='Ivo':
        pygame.draw.line(surface,(221,189,119),(x+8,y-12),(x+8,y+1),2)
        for dx in (5,10):
            pygame.draw.circle(surface,GOLD,(x+dx,y+2),2,1)
            pygame.draw.line(surface,GOLD,(x+dx,y+4),(x+dx,y+10),2)
    elif name=='Sela':
        pygame.draw.rect(surface,(196,155,82),(x-11,y-40,22,5))
        pygame.draw.polygon(surface,(224,187,111),[(x+9,y-39),(x+15,y-35),(x+12,y-25)])
    elif name=='Orrin':
        pygame.draw.line(surface,(208,195,144),(x-10,y-14),(x+12,y+8),3)
        pygame.draw.rect(surface,(167,133,82),(x+8,y+4,11,12))


def _portrait(g,name,rect):
    pygame.draw.rect(g.screen,(63,98,89),rect,border_radius=4)
    sprite=pygame.Surface((72,84),pygame.SRCALPHA)
    _resident(g,sprite,name,36,47,portrait=True)
    g.screen.blit(sprite,(rect.x+4,rect.y+2))
    pygame.draw.line(g.screen,GOLD,rect.bottomleft,rect.bottomright,2)


def _dialogue(g):
    rt=_runtime(g);key=rt['modal'];current=state(g.village)
    if not key:return
    # One bounded panel leaves the player and most of the settlement in view.
    rect=pygame.Rect(225,420,830,300)
    ui_theme.draw_panel(g.screen,rect)
    if key in layout.RESIDENTS:
        _portrait(g,key,pygame.Rect(249,441,80,88))
        title=key+' / '+layout.RESIDENTS[key]['role'];tx=349;width=678
    else:title={'arrival':'Reedhaven','boat':'The canal launch','cistern':'The public cistern','waterworks':'Upstream records'}[key];tx=249;width=778
    ui_theme.fit_text(g.screen,g.heading,title,tx,443,width,TEAL)
    if key=='arrival':
        copy=('The canal widens into a quiet lake. Pale stone houses gather around the lock, '
              'and your launch settles against a timber landing.\n'
              'Shannon: "A town with its feet in the water. I shall be watching mine."\n'
              'Follow the towpath west and cross the footbridge to the market square.')
    elif key=='boat':
        copy=('Your repaired launch is moored here. The departure controller and replacement gear '
              'are still fitted.\nSail back to Copperside whenever you need your workshop.')
    elif key=='Mara':
        copy=('That little launch has found its rhythm again. Good work. I build hulls; '
              'I leave temperamental steam valves to people with steadier patience.\n'
              'The footbridge takes you to Sela\'s market. Ask Ivo about the cistern if you are looking for work.')
    elif key=='Ivo':
        copy=(('There is water in the square again. Thank you. I have put your supplies to work.\n'
               'The old pressure records point upstream, beyond this lock. Several places share '
               'that waterworks. We need to understand the whole network before opening its gates.')
              if current['request_complete'] else
              ('The public cistern has a cracked steam valve. We can fit the repair, but our last '
               'shipment never arrived.\nBring two repair kits and one steam valve from your workshop. '
               'The settlement will pay 32c. You can use your boat for the return trip.'))
    elif key=='Sela':
        copy=(f'Bread, river baskets and enough rope to tie the whole market together. '
              f'I have {current["market_bread"]} loaves left from this shipment, at 8c each.\n'
              'We trade in small loads here. A steady boat is more useful than a grand promise.')
    elif key=='Orrin':
        copy=(('The cistern is fixed, but its gauge still follows the upstream machinery. These '
               'channels are one system, even where the banks make them look separate.\n'
               'Ivo\'s records name an old waterworks beyond the lock. Its pressure districts '
               'continue farther than any of our present trade routes.')
              if current['clue_found'] else
              ('I measure the lake each morning. It rises and falls when none of our gates have moved.\n'
               'There is an old survey plate beside the western lock. Its pressure markings '
               'may tell us which upstream machinery is still connected.'))
    elif key=='cistern':
        copy=(('Clear water spills from the repaired spout. The new valve holds a steady feed, '
               'and the square has its drinking water again.') if current['request_complete'] else
              ('The basin is low. A split valve has been strapped shut until replacement supplies arrive.\n'
               'Ivo needs two repair kits and one steam valve. The repair pays 32c.'))
    else:
        copy=('A weathered brass plate maps pressure districts along the canal. The same small '
              'junction marks recur on the machinery you have recovered. There is no maker\'s name.\n'
              'The lines converge at an old waterworks farther upstream. Its service route is '
              'shut; Ivo and Orrin are checking the surviving gate records.')
    ui_theme.wrapped_text(g.screen,g.font,copy,tx,481,width,INK,line_height=24,max_lines=6)
    # Transaction feedback occupies its own row, never the conversation copy.
    if rt['message']:
        ui_theme.fit_text(g.screen,g.small,rt['message'],249,634,778,TEAL)
    if key=='boat':g.button((249,670,294,32),'Sail to Copperside [1]',lambda:leave(g),active=True,small=True)
    if key=='Sela':
        g.button((249,670,294,32),'Buy bread / 8c [1]',lambda:_buy(g),small=True,
                 enabled=current['market_bread']>0 and g.village.coins>=canal_progress.BREAD_PRICE)
    if key in ('Ivo','cistern') and not current['request_complete']:
        g.button((249,670,294,32),'Deliver repair supplies [1]',lambda:_deliver(g),active=True,small=True)
    g.button((811,670,216,32),'Continue [E / Esc]',lambda:_close(g),small=True)


def _minimap(g,position):
    rect=pygame.Rect(1050,20,206,142)
    ui_theme.draw_panel(g.screen,rect)
    bounds=pygame.Rect(1059,29,188,108)
    old_clip=g.screen.get_clip();g.screen.set_clip(bounds)
    pygame.draw.rect(g.screen,(144,159,117),bounds)
    def point(x,y):return (round(bounds.x+x/layout.WIDTH*bounds.w),round(bounds.y+y/layout.HEIGHT*bounds.h))
    pygame.draw.polygon(g.screen,canal_art.WATER,[point(x,y) for x,y in layout.WATER])
    for path in layout.PATHS:pygame.draw.lines(g.screen,(214,201,158),False,[point(*p) for p in path],2)
    for (x,y),_,_,_ in layout.BUILDINGS.values():pygame.draw.rect(g.screen,(65,110,99),(*point(x-55,y-60),9,6))
    for key,color in (('boat',PAPER),('waterworks',COPPER)):
        p=point(*layout.POINTS[key]);pygame.draw.rect(g.screen,color,(p[0]-2,p[1]-2,5,5))
    pygame.draw.circle(g.screen,INK,point(*position),4)
    pygame.draw.circle(g.screen,GOLD,point(*position),2)
    g.screen.set_clip(old_clip)
    ui_theme.fit_text(g.screen,g.tiny,'N  /  CANAL & LAKE',1062,141,180,MUTED)


def draw(g):
    current=state(g.village);rt=_runtime(g);_prepare_art(g)
    ground,props,lights=g.canal_art_cache
    position=current['position'];camera=layout.camera(position,g.screen.get_size());ox,oy=camera
    seconds=0. if g.reduced_motion else current['visual_time']
    g.screen.blit(ground,(-ox,-oy))
    canal_art.water_motion(g.screen,camera,seconds,g.reduced_motion)
    jobs=[(655,lambda:canal_art.boat(g.screen,2285-ox,625-oy,True,seconds)),
          (1038,lambda:canal_art.cistern(g.screen,980-ox,1038-oy,current['request_complete'],seconds)),
          (680,lambda:canal_art.survey_plate(g.screen,230-ox,680-oy))]
    for name in layout.RESIDENTS:
        x,y=layout.POINTS[name]
        facing='south'
        if math.dist(position,(x,y))<150:
            from resident_performance import facing_toward
            facing=facing_toward((x,y),position)
        jobs.append((y+18,lambda name=name,x=x,y=y,facing=facing:_resident(g,g.screen,name,x-ox,y-oy,seconds=seconds,facing=facing)))
    x,y=position
    jobs.append((y+18,lambda:g.town._villager(g.screen,round(x-ox),round(y-oy),TEAL,rt['phase'],rt['moving'],rt['facing'],'Boole')))
    companion=rt['companion'];cx,cy=companion.position
    jobs.append((cy+18,lambda:companion.draw(g.screen,round(cx-ox),round(cy-oy),reduced_motion=g.reduced_motion,attentive=bool(rt['modal']))))
    progress=town_atmosphere.clock_progress(g.village)
    light=town_atmosphere.evening_light(progress)
    for prop in lights:
        if light>0:
            prop.image.set_alpha(round(light*255))
            jobs.append((prop.depth+.1,lambda prop=prop:prop.draw(g.screen,camera)))
    scene_depth.draw(g.screen,camera,props,jobs)
    town_atmosphere.apply_daylight(g.screen,progress)
    # UI and resident labels keep the shared colors after the world tint.
    ui_theme.draw_panel(g.screen,(20,16,180,108))
    ui_theme.fit_text(g.screen,g.heading,'Reedhaven',34,27,152,TEAL)
    ui_theme.fit_text(g.screen,g.font,f'Day {g.village.day}',34,60,152,INK)
    ui_theme.fit_text(g.screen,g.font,f'Coins  {g.village.coins}c',34,87,152,COPPER)
    import day_clock
    day_clock.draw(g.screen,g.village,g.tiny)
    _minimap(g,position)
    target=near(g)
    if not rt['modal']:
        for name in layout.RESIDENTS:
            x,y=layout.POINTS[name]
            if math.dist(position,(x,y))<140:
                text=g.small.render(name,True,INK)
                bounds=text.get_rect(midbottom=(x-ox,y-oy-51))
                pygame.draw.rect(g.screen,PAPER,bounds.inflate(12,5),border_radius=3)
                g.screen.blit(text,bounds)
        if target:
            label=('Talk to '+target if target in layout.RESIDENTS else
                   {'boat':'Board the canal launch','cistern':'Inspect the cistern','waterworks':'Read the survey plate'}[target])
            g.button((400,652,480,38),label+' [E]',lambda:interact(g),active=True,small=True)
        ui_theme.draw_panel(g.screen,(20,714,625,29))
        ui_theme.fit_text(g.screen,g.tiny,'WASD / arrows  Move    E  Interact    B  Journal    Esc  Pause',32,720,601,MUTED)
        if rt['message_time'] and rt['message']:
            ui_theme.draw_panel(g.screen,(310,590,660,42))
            ui_theme.fit_text(g.screen,g.small,rt['message'],325,602,630,TEAL)
    else:_dialogue(g)
