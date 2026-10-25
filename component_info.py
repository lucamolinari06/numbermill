"""On-demand component diagrams using the circuit's real rotated pin order."""
from copy import deepcopy
import pygame
from circuit import Part, VECTORS, CONDUCTORS
from gate_symbols import GATES, draw_gate
from ui_theme import PAPER, INK, TEAL, COPPER, GOLD, MUTED, draw_panel, fit_text, wrapped_text


# Input entries are in Part.ports() order, not screen-position order.
INPUTS = {
    "SUB": (("Amount", "Number to subtract from"), ("Subtract", "Number to take away")),
    "DIV": (("Dividend", "Number being divided"), ("Divisor", "Number to divide by")),
    "MOD": (("Dividend", "Number being divided"), ("Divisor", "Size of each group")),
    "GT": (("Value", "First comparison value"), ("Threshold", "Second comparison value")),
    "MUX": (("First value", "Passed through if Select = 0"),
            ("Second value", "Passed through if Select > 0"), ("Select", "0: first / >0: second")),
    "REGISTER": (("Data", "Number to remember"), ("Clock", "Store on 0 -> nonzero")),
    "COUNTER": (("Pulse", "Count on 0 -> nonzero"), ("Reset", "Nonzero clears the count")),
    "NOT": (("Signal", "0 is off / nonzero is on"),),
}
OUTPUTS = {
    "ADD": ("Sum", "First + second"), "SUB": ("Difference", "Amount - subtract; floor 0"),
    "MUL": ("Product", "First x second"), "DIV": ("Quotient", "Whole-number division"),
    "MOD": ("Remainder", "What remains after division"),
    "GT": ("Result", "1 if Value > Threshold; else 0"),
    "EQ": ("Result", "1 if inputs are equal; else 0"),
    "MIN": ("Minimum", "The smaller input"), "MAX": ("Maximum", "The larger input"),
    "MUX": ("Selected value", "The chosen input's number"),
    "REGISTER": ("Stored value", "Last captured Data"),
    "COUNTER": ("Count", "Number of pulse edges"), "CLOCK": ("Clock signal", "Two ticks low, two ticks high"),
    "AND": ("Result", "1 when both inputs are on"), "OR": ("Result", "1 when either input is on"),
    "XOR": ("Result", "1 when exactly one is on"), "NOT": ("Result", "1 when input is 0; else 0"),
}
NOTES = {
    "ADD": "Numbers range from 0 to 65535. Overflow wraps back to 0.",
    "MUL": "Numbers range from 0 to 65535. Overflow wraps back to 0.",
    "SUB": "Input order matters. Negative results become 0.",
    "DIV": "Drops the fractional part: 37 / 16 gives 2. A zero divisor outputs 0.",
    "MOD": "Returns the remainder: 37 % 16 gives 5. A zero divisor outputs 0.",
    "GT": "Strictly greater than: equal inputs give 0. Input order matters.",
    "EQ": "Compares the actual numbers, not just whether the inputs are on.",
    "MUX": "The selector chooses a data input; the chosen number is passed through unchanged.",
    "CLOCK": "No input wires needed. Produces its own repeating signal while the circuit runs.",
    "REGISTER": "A rising edge means Clock changes from 0 to nonzero. Otherwise the stored value stays unchanged.",
    "COUNTER": "Holding Pulse high does not keep counting. Reset takes priority; the count wraps after 65535.",
    "DEVICE": "These are the saved design's named ports. Rotating the device moves the pins together.",
}
BOXES = (pygame.Rect(500,215,280,58), pygame.Rect(795,341,280,58),
         pygame.Rect(500,487,280,58), pygame.Rect(205,341,280,58))
CLOSE = pygame.Rect(885,616,180,38)
ROTATE = pygame.Rect(215,616,220,38)


def pin_labels(part):
    """Return (direction, output, name, meaning) from actual pin semantics."""
    if part.kind in CONDUCTORS:
        return [(direction, False, "Connection", "Signal passes either way") for direction in part.ports()[0]]
    labels = INPUTS.get(part.kind, (("First value", "Number from 0 to 65535"),
                                   ("Second value", "Number from 0 to 65535")))
    if part.kind in ("AND", "OR", "XOR"):
        labels = (("First signal", "0 is off / nonzero is on"), ("Second signal", "0 is off / nonzero is on"))
    result = OUTPUTS.get(part.kind, ("Output", "Resulting signal"))
    if part.kind == "DEVICE":
        names = (part.device or {}).get("ports", {})
        labels = tuple((names.get(key, key), "Saved input " + key) for key in ("A", "B"))
        result = (names.get("OUT", "OUT"), "Saved output OUT")
    rows = [(direction, False, *labels[i]) for i, direction in enumerate(part.ports()[0])]
    rows.extend((direction, True, *result) for direction in part.ports()[1])
    return rows


def open_info(g):
    if g.selected in ("TRACE", "ERASE"):
        return
    g.component_info = Part(g.selected, g.rotation, deepcopy(g.held_device) if g.selected == "DEVICE" else None)


def button(g, y, x=970, width=244):
    g.button((x,y,width,30), "INFO", lambda: open_info(g), small=True,
             enabled=g.selected not in ("TRACE", "ERASE"))


def rotate(g):
    part = g.component_info
    g.component_info = Part(part.kind, (part.rotation + 1) % 4, part.device)


def close(g):
    g.component_info = None
    g.buttons.clear()


def click(g, pos, button):
    if button != 1:
        return
    if CLOSE.collidepoint(pos):close(g)
    elif ROTATE.collidepoint(pos):rotate(g)


def key(g, event):
    if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER):close(g)
    elif event.key == pygame.K_r:rotate(g)


def draw(g):
    import workbench
    part = g.component_info
    shade = pygame.Surface(g.screen.get_size(), pygame.SRCALPHA)
    shade.fill((18,29,27,190));g.screen.blit(shade,(0,0))
    draw_panel(g.screen,(185,130,910,550))
    title = (part.device or {}).get("name", "Saved device") if part.kind == "DEVICE" else workbench.NAMES.get(part.kind,part.kind)
    fit_text(g.screen,g.heading,title,215,153,850,TEAL)
    fit_text(g.screen,g.tiny,f"Port diagram / preview rotated {part.rotation * 90} degrees clockwise",215,188,850,MUTED)
    center = (640,370)
    pygame.draw.rect(g.screen,TEAL,(585,315,110,110),border_radius=8)
    if part.kind in GATES:
        draw_gate(g.screen,part.kind,center,98,PAPER,part.rotation,floor_ports=True)
    else:
        label = g.heading.render(workbench.SYMBOLS.get(part.kind,part.kind),True,PAPER)
        g.screen.blit(label,label.get_rect(center=center))
    for direction,output,name,meaning in pin_labels(part):
        dx,dy = VECTORS[direction];rect = BOXES[direction]
        edge = (rect.centerx,rect.bottom) if direction == 0 else (rect.left,rect.centery) if direction == 1 else (rect.centerx,rect.top) if direction == 2 else (rect.right,rect.centery)
        start = (center[0]+dx*55,center[1]+dy*55)
        pygame.draw.line(g.screen,TEAL if output else COPPER,start,edge,3)
        socket = (center[0]+dx*83,center[1]+dy*83)
        pygame.draw.circle(g.screen,TEAL if output else PAPER,socket,7)
        pygame.draw.circle(g.screen,INK,socket,7,1)
        draw_panel(g.screen,rect)
        fit_text(g.screen,g.small,("OUT: " if output else "IN: ")+name,rect.x+20,rect.y+10,240,TEAL if output else COPPER)
        fit_text(g.screen,g.tiny,meaning,rect.x+20,rect.y+32,240,INK)
    note = NOTES.get(part.kind,workbench.COMPONENT_HINTS.get(part.kind,"Signals move through connected pins as the circuit ticks."))
    wrapped_text(g.screen,g.small,note,215,561,850,INK,line_height=22,max_lines=2)
    g.buttons.clear()
    g.button(ROTATE,"ROTATE VIEW [R]",lambda:rotate(g),small=True)
    fit_text(g.screen,g.tiny,"Preview only; your circuit stays unchanged.",455,628,410,MUTED)
    g.button(CLOSE,"CLOSE [ESC]",lambda:close(g),small=True)
