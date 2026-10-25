"""Mosswater survey geography and saved, player-operated receiver challenges."""
from copy import deepcopy
import math
import water_geometry

WIDTH, HEIGHT = 4200, 1850
POINTS = {"exit":(100,690), "receiver":(370,600), "interlock":(1080,490),
          "survey":(1730,420), "range_lock":(3050,1260), "artifact":(3750,1420)}
BEACONS = (
    {"key":"crown", "name":"Crown", "position":(2380,430)},
    {"key":"fern", "name":"Fern", "position":(2760,1120)},
    {"key":"reed", "name":"Reed", "position":(2890,1570)},
)
PONDS = ((2140,620,430,240),(2470,1220,200,220),(3300,800,470,280))
# Bounds above remain useful map metadata; the shared contours below are the
# actual visible water and collision. Rounded coves leave their corners walkable.
POND_POLYGONS = tuple(water_geometry.smooth_polygon(points) for points in (
    ((2142,718),(2164,661),(2226,626),(2312,640),(2380,620),(2460,646),
     (2554,676),(2570,743),(2525,811),(2464,852),(2379,834),(2306,860),
     (2214,839),(2164,786)),
    ((2470,1317),(2493,1244),(2541,1220),(2597,1257),(2651,1251),
     (2670,1306),(2646,1361),(2654,1408),(2601,1440),(2540,1420),(2495,1388)),
    ((3300,926),(3345,855),(3412,800),(3501,834),(3580,812),(3652,840),
     (3770,912),(3740,991),(3673,1014),(3632,1078),(3541,1080),(3453,1041),
     (3381,1044),(3331,995)),
))
RIVER_POLYGONS = (
    water_geometry.stream_polygon(1230,HEIGHT,500,49,phase=.3),
    water_geometry.stream_polygon(3205,HEIGHT,1270,56,phase=1.2),
)
WATER_POLYGONS = (*POND_POLYGONS,*RIVER_POLYGONS)
WATER_BOUNDS = tuple(water_geometry.bounds(polygon) for polygon in WATER_POLYGONS)
BRIDGE_BOUNDS = ((1175,440,115,120),(3143,1200,130,140))
PATHS = (
    ((1875,600),(2020,620),(2060,940),(2400,1040),(2760,1120),(2960,1230),
     (3210,1270),(3420,1330),(3650,1500),(3750,1420)),
    ((1730,420),(2040,360),(2380,430),(2710,340),(2950,570),(2910,970),(2760,1120)),
    ((2060,940),(2210,1480),(2450,1580),(2890,1570),(2990,1440),(2960,1230)),
)


def prepare(current):
    # Existing designs, inventory and already-earned rewards remain intact.
    for key,value in {"survey_started":False,"survey_found":[],"survey_samples":{},
                      "frequency":0,"bearing":1,"range_armed":False,"range_reads":{},
                      "range_gate":False,"expansion_complete":False}.items():
        current.setdefault(key,deepcopy(value))
    current["mosswater_version"] = 2
    return current


def blocked(x,y):
    if not (50<=x<=WIDTH-60 and 180<=y<=HEIGHT-100):return True
    if x<1900 and not 230<=y<=825:return True
    if any(left<=x<=left+w and top<=y<=top+h for left,top,w,h in BRIDGE_BOUNDS):return False
    return water_blocked(x,y)


def water_blocked(x,y):
    return any(left<=x<left+w and top<=y<top+h and water_geometry.contains((x,y),polygon)
               for polygon,(left,top,w,h) in zip(WATER_POLYGONS,WATER_BOUNDS))


def safe_bank_position(position):
    """Recover a pre-shoreline-update position to nearby land on the same bank."""
    x,y=position
    if not blocked(x,y):return [float(x),float(y)]
    for radius in range(8,201,8):
        for index in range(32):
            angle=index*math.tau/32
            point=(x+math.cos(angle)*radius,y+math.sin(angle)*radius)
            # Never relocate an older save across a guarded river.
            if any((x-center)*(point[0]-center)<0 for center in (1230,3205)):continue
            if not blocked(*point):return list(point)
    return [100.,690.]


def target(current,frequency=None):
    if not current["survey_started"]:
        return {"key":"station","name":"Survey station","position":POINTS["survey"]}
    index=current["frequency"] if frequency is None else frequency
    if index==3 and current["range_gate"]:
        return {"key":"archive","name":"Archive","position":POINTS["artifact"]}
    return BEACONS[index%3]


def payload(current,position,frequency=None):
    beacon=target(current,frequency);tx,ty=beacon["position"]
    dx,dy=tx-position[0],ty-position[1];distance=math.hypot(dx,dy)
    direction=(1 if dx>0 else 3) if abs(dx)>abs(dy) else (2 if dy>0 else 0)
    resolution=25 if current.get("receiver_upgrade") and distance<400 else 100
    count=min(15,int(distance/resolution))
    return {"key":beacon["key"],"name":beacon["name"],"packet":direction*16+count,
            "direction":direction,"bearing":current["bearing"],"resolution":resolution,
            "distance":distance,"position":list(position),"overflow":distance>=resolution*16}


def record_scan(current,reading):
    """Only decoded, matching returns can contribute a survey or alignment."""
    if not reading["matched"]:return "No return on that bearing. Try turning the receiver.",False
    if reading["overflow"]:return "That return is beyond our measuring range. We need to get closer.",False
    if not current["survey_started"]:return "That signal leads to the survey station beyond the bridge.",False
    key=reading["key"]
    if key=="archive":return "The archive is ahead. Let's see what its maker left there.",False
    if len(current["survey_found"])==3 and current["range_armed"] and not current["range_gate"]:
        if key not in ("fern","reed"):return "The range lock listens to Fern and Reed.",False
        low,high=(20,30) if key=="fern" else (30,40)
        if reading["low"]<low or reading["high"]>high:
            current["range_reads"].pop(key,None)
            return f"{reading['name']} needs to read within {low}–{high} paces here.",True
        position=reading["position"]
        current["range_reads"]={k:r for k,r in current["range_reads"].items()
                                if math.dist(position,r["position"])<=20}
        current["range_reads"][key]={"position":list(position)}
        if len(current["range_reads"])==2:
            current["range_gate"]=True;current["frequency"]=3
            return "Both returns agree. The archive bridge is open!",True
        return "Hold this spot. Tune the other channel and scan its return too.",True
    if key in current["survey_found"]:
        if current['range_gate']:return "Our survey is complete. Tune the Archive channel to find the recovered machinery.",False
        if len(current['survey_found'])==3:return "All three beacons are awake. The range lock is beside the eastern bridge.",False
        return "We've uncovered this beacon. The other channels are still there to follow.",False
    samples=current["survey_samples"].setdefault(key,[])
    if not samples:
        samples.append({"position":reading["position"],"bearing":reading["bearing"]})
    elif len(samples)<2 and any(s["bearing"]!=reading["bearing"] and
                                math.dist(s["position"],reading["position"])>=180 for s in samples):
        samples.append({"position":reading["position"],"bearing":reading["bearing"]})
    if len(samples)==2 and reading["distance"]<100:
        current["survey_found"].append(key)
        if len(current["survey_found"])==3:
            return "Three beacons awake. The range-lock station is beside the eastern bridge.",True
        return f"Found {reading['name']}! A little buried aerial, still doing its job.",True
    if len(samples)<2:
        return "One bearing recorded. Move at least 18 paces and read it from another direction.",True
    return "Two bearings recorded. Bring us within 10 paces and scan to uncover it.",True
