"""A saved first expedition: player-built receiver decoder and safety interlock."""
from copy import deepcopy
import math
import pygame
from circuit import Circuit, edge_terminals, CONDUCTORS
import manufacturing
import developer_mode
import sandbox
import workshop_floor
import ui_theme
import adventure_art
import expedition_ui
import mosswater
import scene_depth
from town_companion import Companion
from ui_theme import PAPER, INK, TEAL, GOLD, MUTED, COPPER

TITLES={'decoder':'Shannon / echo receiver','interlock':'Ravine / safety interlock'}
POINTS=mosswater.POINTS
MAX_HEALTH, BREAD_HEAL, HAZARD_DAMAGE, RESCUE_HEALTH = 100., 25., 25., 40.
FOOT_OFFSET = 18  # Town sprites and Shannon are anchored above their ground contact.
SPECIFICATIONS={
 'decoder':("A: packet = bearing × 16 + distance (0–63).", "B: selected bearing (0–3). C: packet base (16).", "OUT: distance when packet bearing matches B; otherwise 0.", "Distance is 0–15. Install a combinational decoder."),
 'interlock':("A: boiler pressure (0–12). B: pressure limit (3–9).", "C: latch status: 0 open / 1 locked / 2 fault / 3 locked + fault.", "OUT must be exactly 1 only with positive pressure at or below", "the limit AND a locked, fault-free latch. All other cases: 0.")}


def state(village):
    result=manufacturing.state(village).setdefault('adventure',{})
    result.pop('hunger', None)  # Old expedition saves migrate without changing health or progress.
    for key,value in {'position':[100.,690.], 'health':MAX_HEALTH,'receiver':False,'decoder':False,
                      'interlock':False,'artifact':False,'drafts':{},'designs':{},'visited':False,'injuries':0}.items():
        result.setdefault(key,deepcopy(value))
    return mosswater.prepare(result)


def active_editor(g): return bool(getattr(g,'adventure_editor',None))


def cases(kind):
    if kind.startswith('jetpack_') or kind == 'tower_vent':
        import boiler_tower
        return boiler_tower.cases(kind)
    if kind=='decoder':
        return [(a,b,16,a%16 if a//16==b else 0) for a in range(64) for b in range(4)]
    return [(a,b,c,int(0<a<=b and c==1)) for a in range(13) for b in range(3,10) for c in range(4)]


def certify(circuit,kind):
    if circuit.has_sequential(): return False,'This interface requires a combinational circuit.'
    if set(circuit.switches)!={'A','B','C'}: return False,'Keep the three field input terminals.'
    trial=Circuit.from_snapshot(circuit.snapshot())
    rows=cases(kind)
    # Explicit combinational traces have no hidden transport history. When every
    # gate is unchanged, this is a true fixed point, not merely a quiet output.
    # Older pipe layouts and nested devices retain the engine's full evaluator.
    fixed_point_safe=trial.trace_mode and not any(p.kind in (*CONDUCTORS,'DEVICE') for p in trial.parts.values())
    for a,b,c,expected in rows:
        if fixed_point_safe:
            trial.switches.update(A=a,B=b,C=c);trial.reset();stable=False
            for _ in range(trial.settle_budget()):
                before=trial.active;trial.tick()
                if trial.active==before:stable=True;break
            actual=trial.output_value()
        else:actual,stable=trial.evaluate(a,b,c)
        if actual!=expected or not stable:
            return False,f'A={a} B={b} C={c}: expected {expected}, got {actual}'+(' (unstable)' if not stable else '')
    return True,f'{len(rows)} operating conditions verified.'


def sync(g):
    if not active_editor(g): return
    circuit=(g.device_stack[0][0] if g.device_stack else g.circuit)
    state(g.village)['drafts'][g.adventure_editor]={'parts':circuit.snapshot()}


def enter_editor(g,kind):
    if active_editor(g): close_editor(g)
    g.adventure_return_scene = 'boiler_tower' if kind.startswith('jetpack_') or kind == 'tower_vent' else 'adventure'
    if g.factory_context is not None:
        import factory_controller
        factory_controller.leave(g)
    if g.sandbox_context is not None:sandbox.leave(g)
    if g.timing_key is not None:
        import timing_workshop
        timing_workshop.leave(g)
    if g.invention:g.close_invention()
    g.adventure_context={name:getattr(g,name) for name in sandbox.CONTEXT}
    g.adventure_editor=kind
    draft=state(g.village)['drafts'].get(kind,{})
    g.circuit=Circuit.from_snapshot(draft['parts']) if draft else Circuit(terminals=edge_terminals(('A','B','C')))
    g.circuit.switches.update({'A':37 if kind=='decoder' else 4,'B':2 if kind=='decoder' else 6,'C':16 if kind=='decoder' else 1})
    g.port_names=({'A':'Packed echo','B':'Bearing','C':'Base 16','OUT':'Distance'} if kind=='decoder' else
                  {'A':'Pressure','B':'Limit','C':'Latch flags','OUT':'Safe passage'})
    if kind.startswith('jetpack_') or kind == 'tower_vent':
        import boiler_tower
        g.circuit.switches.update(dict(zip(('A','B','C'), (9,4,1) if kind == 'tower_vent' else
                                          boiler_tower.readings(boiler_tower.state(g.village), True))))
        g.port_names = ({'A':'Pipe pressure','B':'Safe pressure','C':'Exhaust request','OUT':'Release'}
                        if kind == 'tower_vent' else
                        {'A':'Pressure','B':'Heat','C':'Thrust request','OUT':'Valve drive'})
    g.active_compute=None;g.numeric_mode=True;g.paused=True;g.elapsed=0;g.tick_interval=.22
    g.device_stack=[];g.design_source=g.held_device=None
    g.test_results=g.tested_job=g.tested_snapshot=g.success_job=None
    g.delivery_open=g.help_open=g.task_help_open=False
    g.selected,g.tab,g.scene='TRACE','BUILD','workshop';g.rotation=0;g.port_editor=None
    g.adventure_group='Logic';g.adventure_spec=True;g.adventure_result=''
    workshop_floor.cancel(g);workshop_floor.prepare(g)


def close_editor(g):
    if not active_editor(g): return
    sync(g)
    for name,value in g.adventure_context.items(): setattr(g,name,value)
    g.adventure_context=None;g.adventure_editor=None;g.adventure_spec=False
    g.port_editor=None;workshop_floor.cancel(g)
    g.scene=getattr(g,'adventure_return_scene','adventure');g.save_game()


def validate(g):
    sync(g);ok,message=certify(g.circuit,g.adventure_editor)
    g.adventure_result=message
    if ok:
        current=state(g.village);current[g.adventure_editor]=True
        current['designs'][g.adventure_editor]=g.circuit.snapshot()
        g.adventure_decoder_cache=None
        g.toast('Tower controller installed.' if g.adventure_editor.startswith('jetpack_') or g.adventure_editor == 'tower_vent' else
                'Receiver decoder installed.' if g.adventure_editor=='decoder' else 'Interlock installed. The bridge is safe.')
        g.save_game()
    return ok,message


def editor_key(g,event):
    if not active_editor(g): return False
    if g.scene!='workshop' or any(getattr(g,key,None) for key in ('port_editor','help_open','task_help_open','pending_design_delete','device_stack','invention_picker')):
        return False
    if getattr(g,'adventure_spec',False):
        if event.key in (pygame.K_ESCAPE,pygame.K_RETURN,pygame.K_h): g.adventure_spec=False
        return True
    if event.key==pygame.K_ESCAPE:
        if getattr(g,'trace_source',None) is not None:workshop_floor.cancel(g)
        else:close_editor(g)
        return True
    if event.key==pygame.K_t: validate(g);return True
    if event.key==pygame.K_h: g.adventure_spec=True;return True
    return False


def editor_click(g,pos,button=1):
    if not active_editor(g):return False
    if getattr(g,'adventure_spec',False):
        if pygame.Rect(830,535,170,40).collidepoint(pos):g.adventure_spec=False
        return True
    return False


def specification(g):
    if g.adventure_editor.startswith('jetpack_') or g.adventure_editor == 'tower_vent':
        import boiler_tower
        title, lines = boiler_tower.specification(g.adventure_editor)
        return title, list(lines)
    return TITLES[g.adventure_editor],list(SPECIFICATIONS[g.adventure_editor])


def draw_specification(g):
    if not getattr(g,'adventure_spec',False):return
    shade=pygame.Surface((1280,760),pygame.SRCALPHA);shade.fill((15,28,24,170));g.screen.blit(shade,(0,0))
    ui_theme.draw_panel(g.screen,(240,218,800,380))
    title, lines = specification(g)
    ui_theme.fit_text(g.screen,g.heading,title,270,246,740,TEAL)
    for i,line in enumerate(lines):
        ui_theme.fit_text(g.screen,g.font,line,270,300+i*32,740,INK)
    ui_theme.fit_text(g.screen,g.small,'T tests every condition and installs a passing design.',270,478,740,MUTED)
    g.button((830,535,170,40),'CLOSE',lambda:setattr(g,'adventure_spec',False),small=True)


def panel(g):
    import workbench
    from gate_symbols import GATES,draw_gate
    ui_theme.draw_panel(g.screen,(956,136,272,588))
    ui_theme.fit_text(g.screen,g.small,'FIELD CIRCUIT',972,151,240,TEAL)
    g.button((970,186,244,34),'SPECIFICATION',lambda:setattr(g,'adventure_spec',True),small=True)
    for i,group in enumerate(workbench.COMPONENT_GROUPS):
        g.button((970+i*83,237,78,30),group,lambda k=group:setattr(g,'adventure_group',k),small=True,active=getattr(g,'adventure_group','Logic')==group)
    for i,kind in enumerate(workbench.COMPONENT_GROUPS.get(getattr(g,'adventure_group','Logic'),())):
        rect=pygame.Rect(970+i%4*62,280+i//4*56,56,48)
        g.button(rect,'' if kind in GATES else workbench.SYMBOLS[kind],lambda k=kind:g.select_part(k),small=True,active=g.selected==kind)
        if kind in GATES:draw_gate(g.screen,kind,rect.center,36,PAPER if g.selected==kind else INK)
    ui_theme.fit_text(g.screen,g.small,workbench.NAMES.get(g.selected,g.selected),970,452,244,TEAL)
    workbench.component_info.button(g,510)
    ui_theme.wrapped_text(g.screen,g.tiny,workbench.COMPONENT_HINTS.get(g.selected,''),970,479,244,MUTED,line_height=19,max_lines=1)
    ui_theme.wrapped_text(g.screen,g.tiny,getattr(g,'adventure_result',''),970,555,244,INK,line_height=20,max_lines=2 if developer_mode.enabled(g) else 3)
    if developer_mode.enabled(g):
        g.button((970,597,244,27),'DEV: AUTO SOLVE',lambda:developer_mode.solve(g),small=True)
    g.button((970,630,244,34),'TEST + INSTALL [T]',lambda:validate(g),small=True)
    g.button((970,678,244,32),'BACK TO EXPEDITION',lambda:close_editor(g),small=True)


def blocked(x,y):
    return mosswater.blocked(x,y+FOOT_OFFSET)


def safe_position(position):
    """Convert a saved actor anchor to ground space for shoreline recovery."""
    x,y=position
    foot=mosswater.safe_bank_position((x,y+FOOT_OFFSET))
    return [foot[0],foot[1]-FOOT_OFFSET]


def enter(g):
    if active_editor(g):close_editor(g)
    if g.factory_context is not None:
        import factory_controller
        factory_controller.leave(g)
    if g.sandbox_context is not None:sandbox.leave(g)
    if g.timing_key is not None:
        import timing_workshop
        timing_workshop.leave(g)
    if g.invention:g.close_invention()
    current=state(g.village);g.scene='adventure';g.adventure_time=0.;g.adventure_cooldown=0.;g.adventure_modal=None
    g.adventure_notice_reply=None
    if not hasattr(g,'adventure_props'):
        g.adventure_background,g.adventure_props=adventure_art.build_scene()
    if blocked(*current['position']):current['position']=safe_position(current['position'])
    g.adventure_companion=Companion(current['position'],blocked)
    g.adventure_facing='east';g.adventure_phase=0.;g.adventure_moving=False
    if not current['visited']:
        current['visited']=True;g.adventure_speech='Shannon: That aerial is humming. I would like to know why.';g.adventure_speech_time=8.
    else:g.adventure_speech_time=0.
    g.save_game()


def leave(g):
    if active_editor(g):close_editor(g)
    g.scene='town';g.town.companion.reset((g.town.player_x,g.town.player_y));g.save_game()


def near(g):
    p=state(g.village)['position']
    return next((key for key,xy in POINTS.items() if math.dist(p,xy)<92),None)


def speak(g,line):g.adventure_speech='Shannon: '+line;g.adventure_speech_time=8.


def notice(g,title,message,reply=None):
    g.adventure_modal_title=title;g.adventure_modal=message
    g.adventure_notice_reply=reply
    g.adventure_speech_time=0.


def close_notice(g):
    g.adventure_modal=None
    reply=getattr(g,'adventure_notice_reply',None)
    g.adventure_notice_reply=None
    if reply:speak(g,reply)


def receiver_reading(g):
    current=state(g.village)
    if not current['decoder'] or 'decoder' not in current['designs']:return None
    reading=mosswater.payload(current,current['position'])
    key=(reading['packet'],reading['bearing'])
    cache=getattr(g,'adventure_decoder_cache',None)
    if not cache or cache[0]!=key:
        circuit=Circuit.from_snapshot(current['designs']['decoder'])
        value,stable=circuit.evaluate(*key,16)
        g.adventure_decoder_cache=(key,value,stable)
    else:_,value,stable=cache
    reading.update(matched=stable and reading['direction']==reading['bearing'],
                   low=value*reading['resolution']/10,high=(value+1)*reading['resolution']/10)
    return reading


def tune(g):
    current=state(g.village)
    if not current['decoder'] or not current['survey_started']:return
    current['frequency']=(current['frequency']+1)%(4 if current['range_gate'] else 3)
    g.save_game()


def rotate_receiver(g):
    current=state(g.village)
    if not current['decoder']:return
    current['bearing']=(current['bearing']+1)%4;g.save_game()


def scan(g):
    reading=receiver_reading(g)
    if reading is None:return
    message,changed=mosswater.record_scan(state(g.village),reading)
    speak(g,message)
    if changed:g.save_game()


def interact(g):
    key=near(g);current=state(g.village)
    if key=='exit':leave(g)
    elif key=='receiver':
        current['receiver']=True
        speak(g,'It fits my socket. That is either convenient or slightly worrying.')
        enter_editor(g,'decoder')
    elif key=='interlock':
        if not current['decoder']:speak(g,'The maintenance port needs the receiver to read its instructions.')
        else:enter_editor(g,'interlock')
    elif key=='survey':
        if not current['decoder'] or not current['interlock']:speak(g,'The survey station is waiting for its safety circuit.')
        else:
            current['survey_started']=True
            notice(g,'Survey station','Three buried beacons: Crown, Fern, Reed. Record each from two different bearings, at least 18 paces apart. Then scan within 10 paces to uncover it. Turn [R], tune [Tab], scan [Space].',
                   'A whole survey network! Naturally, its maker filed the instructions in a tree.')
            g.save_game()
    elif key=='range_lock':
        if len(current['survey_found'])<3:
            notice(g,'Archive range lock','Three survey beacons must be uncovered before the lock will accept readings. Follow their receiver channels from the survey station.')
        elif current['range_gate']:speak(g,'The bridge is open. The archive has its own channel now.')
        else:
            current['range_armed']=True
            notice(g,'Archive range lock','Find one spot where Fern reads 20–30 paces and Reed reads 30–40 paces. Scan both channels there, turning the receiver as needed. Move no more than 2 paces between readings.')
            g.save_game()
    elif key=='artifact':
        if current['expansion_complete']:speak(g,'Empty cradle. I hope its inventor would approve.')
        elif not current['decoder'] or not current['interlock'] or not current['range_gate']:speak(g,'The cradle is still locked.')
        else:
            already=current['artifact'];current['expansion_complete']=True
            current['artifact']=True
            manufacturing.unlock_equipment(g.village,'precision_machine')
            current['receiver_upgrade']=True
            notice(g,'Archive recovered',('The archive matches your recovered precision cutter blueprint and focused lens. Its survey network is now fully restored.' if already else 'Recovered: precision cutter blueprint and focused receiver lens. The cutter is now available in workshop equipment.') + ' A route to Boiler Tower is marked inside. Use the Boiler Tower travel button to begin expedition two.',
                   'A precision cutter blueprint! And this lens fits me too. Peculiar.')
            g.save_game()


def eat(g):
    current=state(g.village)
    if current['health']>=MAX_HEALTH:g.toast('Health is full. Bread saved for later.');return
    if g.village.player_bread<=0:g.toast('No bread packed. Town shops sell food.');return
    g.village.player_bread-=1
    current['health']=min(MAX_HEALTH,current['health']+BREAD_HEAL)
    g.save_game()


def handle_key(g,event):
    if getattr(g,'adventure_modal',None):
        if event.key in (pygame.K_ESCAPE,pygame.K_RETURN,pygame.K_e):close_notice(g)
        return True
    if event.key==pygame.K_e:interact(g);return True
    if event.key==pygame.K_f:eat(g);return True
    if event.key==pygame.K_g and state(g.village)['receiver']:enter_editor(g,'decoder');return True
    if event.key==pygame.K_r:rotate_receiver(g);return True
    if event.key==pygame.K_TAB:tune(g);return True
    if event.key==pygame.K_SPACE:scan(g);return True
    return event.key!=pygame.K_ESCAPE


def click(g,pos,button=1):
    if button!=1:return
    for rect,action in reversed(g.buttons):
        if rect.collidepoint(pos):action();return


def hurt(g,amount,checkpoint=(1090.,540.)):
    if developer_mode.enabled(g):return
    current=state(g.village);current['health']=max(0.,current['health']-amount);current['injuries']+=1
    g.adventure_cooldown=1.5
    current['position']=safe_position(checkpoint)
    g.adventure_companion.reset(current['position'])
    speak(g,'Back! That pressure seal is still live.')
    if current['health']<=0:
        current['health']=RESCUE_HEALTH;current['position']=[100.,690.]
        leave(g);g.toast('Shannon brought you home. Eat before trying the ravine again.')
    g.save_game()


def update(g,dt):
    dt=max(0.,min(.1,dt));current=state(g.village)
    g.adventure_time+=dt;g.adventure_cooldown=max(0.,g.adventure_cooldown-dt)
    g.adventure_speech_time=max(0.,getattr(g,'adventure_speech_time',0)-dt)
    if getattr(g,'adventure_modal',None):return
    keys=pygame.key.get_pressed();dx=int(keys[pygame.K_d] or keys[pygame.K_RIGHT])-int(keys[pygame.K_a] or keys[pygame.K_LEFT]);dy=int(keys[pygame.K_s] or keys[pygame.K_DOWN])-int(keys[pygame.K_w] or keys[pygame.K_UP])
    length=math.hypot(dx,dy);g.adventure_moving=bool(length)
    old=tuple(current['position'])
    if length:
        speed=450 if developer_mode.enabled(g) else 230
        dx*=speed*dt/length;dy*=speed*dt/length
        if developer_mode.enabled(g):
            current['position'][0]=max(50.,min(mosswater.WIDTH-60.,current['position'][0]+dx))
            current['position'][1]=max(180.,min(mosswater.HEIGHT-100.,current['position'][1]+dy))
        else:
            if not blocked(current['position'][0]+dx,current['position'][1]):current['position'][0]+=dx
            if not blocked(current['position'][0],current['position'][1]+dy):current['position'][1]+=dy
        g.adventure_facing=('east' if dx>0 else 'west') if abs(dx)>abs(dy) else ('south' if dy>0 else 'north')
        g.adventure_phase+=math.dist(old,current['position'])*.1
    for unlocked,left,right,top,bottom,checkpoint in (
            (current['interlock'],1180,1285,435,565,(1090.,540.)),
            (current['range_gate'],3150,3265,1195,1345,(3050.,1300.))):
        if not developer_mode.enabled(g) and not unlocked and left<current['position'][0]<right and top<current['position'][1]+FOOT_OFFSET<bottom:
            if not g.adventure_cooldown:hurt(g,HAZARD_DAMAGE,checkpoint)
            else:
                current['position']=safe_position(checkpoint);g.adventure_companion.reset(current['position'])
    g.adventure_companion.update(current['position'],dt,via=((current['position'][0],old[1]),))


def draw(g):
    current=state(g.village);x,y=current['position'];ox=max(0,min(adventure_art.WIDTH-1280,x-640));oy=max(0,min(adventure_art.HEIGHT-760,y-420))
    g.screen.blit(g.adventure_background,(-int(ox),-int(oy)))
    # Raised scenery, Boole, Shannon and the bridge fittings share ground depth.
    jobs=[]
    for unlocked,left,right,rails,vents,emitter,span in (
            (current['interlock'],1185,1283,(434,562),range(454,553,22),1216,29),
            (current['range_gate'],3150,3265,(1198,1340),range(1210,1331,24),3190,40)):
        color=TEAL if unlocked else COPPER
        for yy in rails:
            jobs.append((yy,lambda yy=yy,left=left,right=right,color=color:
                         pygame.draw.line(g.screen,color,(left-ox,yy-oy),(right-ox,yy-oy),7)))
        if not unlocked:
            for i,yy in enumerate(vents):
                jobs.append((yy,lambda i=i,yy=yy,emitter=emitter,span=span:
                             adventure_art.steam_jet(g.screen,emitter-ox,yy-oy,g.adventure_time,i,span)))
    for beacon in mosswater.BEACONS:
        if beacon['key'] in current['survey_found']:
            bx,by=beacon['position']
            jobs.append((by+12,lambda bx=bx,by=by:adventure_art.beacon(g.screen,int(bx-ox),int(by-oy))))
    if not current['expansion_complete']:
        ax,ay=POINTS['artifact']
        jobs.append((ay+33,lambda:pygame.draw.circle(g.screen,GOLD,(int(ax-ox),int(ay-oy-10)),13,2)))
    jobs.append((y+18,lambda:g.town._villager(g.screen,int(x-ox),int(y-oy),TEAL,g.adventure_phase,g.adventure_moving,g.adventure_facing,'Boole')))
    cx,cy=g.adventure_companion.position
    jobs.append((cy+18,lambda:g.adventure_companion.draw(g.screen,int(cx-ox),int(cy-oy))))
    scene_depth.draw(g.screen,(int(ox),int(oy)),g.adventure_props,jobs)
    for label,point in (('ECHO RECEIVER',POINTS['receiver']),('INTERLOCK',POINTS['interlock'])):
        if math.dist((x,y),point)<160:ui_theme.fit_text(g.screen,g.tiny,label,int(point[0]-ox-70),int(point[1]-oy-70),180,INK)
    region='Archive hills' if x>3260 else 'Reed marsh' if x>1900 and y>1120 else 'Survey woods' if x>1900 else 'Western trail'
    expedition_ui.health(g,'Mosswater',region,current['health'])
    g.button((20,116,220,30),'Bread '+str(g.village.player_bread)+' / +25 HP [F]',lambda:eat(g),small=True)
    reading=receiver_reading(g)
    if reading:
        expedition_ui.panel(g.screen,(976,20,280,226))
        ui_theme.fit_text(g.screen,g.tiny,'ECHO RECEIVER',994,35,240,expedition_ui.DIM)
        expedition_ui.compass(g.screen,(1018,95),current['bearing'])
        ui_theme.fit_text(g.screen,g.small,reading['name'],1058,68,178,expedition_ui.TEXT)
        label=('No return' if not reading['matched'] else '150+ paces' if reading['overflow'] else
               f"{reading['low']:g}–{reading['high']:g} paces")
        ui_theme.fit_text(g.screen,g.small,label,1058,96,178,expedition_ui.MINT)
        g.button((988,163,124,32),'Turn '+('N','E','S','W')[current['bearing']]+' [R]',lambda:rotate_receiver(g),small=True)
        if current['survey_started']:
            g.button((1120,163,124,32),'Tune [Tab]',lambda:tune(g),small=True)
        g.button((988,204,256,32),'Scan [Space]',lambda:scan(g),small=True)
        samples=current['survey_samples'].get(reading['key'],[])
        bearings=' / '.join(('N','E','S','W')[sample['bearing']] for sample in samples) or '0/2'
        status=('Archive bridge open' if current['range_gate'] else
                f"Range lock: {len(current['range_reads'])}/2" if current['range_armed'] else
                'Beacon uncovered' if reading['key'] in current['survey_found'] else
                f"Bearings: {bearings}" if current['survey_started'] else 'Survey station signal')
        ui_theme.fit_text(g.screen,g.tiny,status,994,135,240,expedition_ui.DIM)
    if current['receiver']:g.button((1000,256,256,30),'Receiver circuit [G]',lambda:enter_editor(g,'decoder'),small=True)
    if current['survey_started']:
        expedition_ui.panel(g.screen,(20,158,272,36))
        ui_theme.fit_text(g.screen,g.tiny,f"Beacons uncovered: {len(current['survey_found'])}/3",36,168,240,expedition_ui.MINT)
    if current['expansion_complete']:
        import boiler_tower
        g.button((24,210,300,38),'TRAVEL TO BOILER TOWER',lambda:boiler_tower.enter(g),small=True)
    key=near(g)
    labels={'exit':'RETURN TO VILLAGE','receiver':'INSPECT RECEIVER','interlock':'EDIT SAFETY CIRCUIT','artifact':'INSPECT ARTIFACT','survey':'SURVEY STATION','range_lock':'ARCHIVE RANGE LOCK'}
    if key:g.button((450,684,380,44),labels[key]+' [E]',lambda:interact(g),small=True)
    if getattr(g,'adventure_speech_time',0)>0:
        ui_theme.draw_panel(g.screen,(220,591,840,70));ui_theme.wrapped_text(g.screen,g.small,g.adventure_speech,240,607,800,INK,line_height=21,max_lines=2)
    if getattr(g,'adventure_modal',None):
        shade=pygame.Surface((1280,760),pygame.SRCALPHA);shade.fill((15,28,24,160));g.screen.blit(shade,(0,0));g.buttons=[]
        ui_theme.draw_panel(g.screen,(330,230,620,310));ui_theme.fit_text(g.screen,g.heading,getattr(g,'adventure_modal_title','Recovered technology'),355,252,570,TEAL)
        ui_theme.wrapped_text(g.screen,g.font,g.adventure_modal,355,301,570,INK,line_height=24,max_lines=6)
        g.button((740,480,180,40),'CONTINUE',lambda:close_notice(g),small=True)
