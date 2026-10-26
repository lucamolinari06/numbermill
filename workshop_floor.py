"""Shared trace tools for contracts, calculators and binary inventions."""
import math
import pygame
from circuit import Part, VECTORS, ARITHMETIC


def draw_board_base(game):
    """A quiet drafting surface with the exact existing cell geometry."""
    bx, by, cell = game.board_metrics()
    rect = pygame.Rect(bx - 13, by - 13, 16 * cell + 24, 9 * cell + 24)
    surface = game.screen
    pygame.draw.rect(surface, (26, 43, 41), rect.move(0, 5), border_radius=6)
    pygame.draw.rect(surface, (96, 65, 44), rect, border_radius=5)
    pygame.draw.rect(surface, (182, 131, 76), rect.inflate(-4, -4), 2, border_radius=4)
    pygame.draw.rect(surface, (66, 83, 75), (bx - 5, by - 5, 16 * cell + 8, 9 * cell + 8), border_radius=2)
    for y in range(9):
        for x in range(16):
            tile = pygame.Rect(bx + x * cell, by + y * cell, cell - 1, cell - 1)
            color = (213, 216, 193) if (x + y) % 2 else (221, 222, 201)
            pygame.draw.rect(surface, color, tile)
            pygame.draw.line(surface, (192, 201, 175), (tile.x, tile.bottom - 1), (tile.right - 1, tile.bottom - 1))
            pygame.draw.circle(surface, (186, 196, 171), tile.center, 1)
    for x in (rect.left + 6, rect.right - 7):
        for y in (rect.top + 6, rect.bottom - 7):
            pygame.draw.circle(surface, (231, 194, 117), (x, y), 2)
            pygame.draw.line(surface, (104, 81, 51), (x - 1, y), (x + 1, y))


def prepare(game):
    if not game.circuit.trace_mode or any(p.kind in ("PIPE", "BEND", "SPLIT") for p in game.circuit.parts.values()):
        game.circuit.convert_pipes()
    inputs = [port["name"] for port in game.circuit.terminals.values() if not port["output"]]
    outputs = [port["name"] for port in game.circuit.terminals.values() if port["output"]]
    if game.sandbox_context is None and not game.invention and game.timing_key is None and game.factory_context is None and not getattr(game, "adventure_editor", None) and not game.device_stack and not game.active_compute and game.commission.input_c:
        if "C" not in inputs:
            inputs.append("C")
        game.port_names.setdefault("C", game.commission.input_c)
    if not game.circuit.layout_terminals(inputs, outputs):
        game.toast("Free a floor tile so the edge terminals can be placed.")


def socket(game, pos, direction):
    bx, by, cell = game.board_metrics()
    dx, dy = VECTORS[direction]
    return (bx + (pos[0] + .5 + dx * .43) * cell - 1,
            by + (pos[1] + .5 + dy * .43) * cell - 1)


def hit_socket(game, mouse):
    for pos, part in game.circuit.parts.items():
        inputs, outputs = part.ports()
        for is_output, directions in ((True, outputs), (False, inputs)):
            for pin, direction in enumerate(directions):
                x, y = socket(game, pos, direction)
                if math.hypot(mouse[0] - x, mouse[1] - y) <= 9:
                    return pos, is_output, pin
    return None


def socket_label(part, output, pin):
    if output:
        return "OUT"
    names = {"REGISTER": ("Data", "Clock"), "COUNTER": ("Pulse", "Reset"),
             "MUX": ("First", "Second", "Select"), "NOT": ("IN",), "OUTPUT": ("IN",), "LAMP": ("IN",)}
    return names.get(part.kind, ("First", "Second", "Third"))[pin]


def direction_arrow(surface, start, end, color, size=5):
    distance = math.dist(start, end)
    if distance < 8:
        return
    dx, dy = (end[0] - start[0]) / distance, (end[1] - start[1]) / distance
    tip = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
    pygame.draw.polygon(surface, color, [tip, (tip[0] - dx * size - dy * size, tip[1] - dy * size + dx * size),
                                       (tip[0] - dx * size + dy * size, tip[1] - dy * size - dx * size)])


def cancel(game):
    game.trace_source = None
    game.trace_points = []


def changed(game):
    game.tested_snapshot = None
    if game.invention:
        game.invention.edit()


def click(game, mouse, button):
    prepare(game)
    pos = game.board_pos(mouse)
    if pos is None:
        return
    circuit = game.circuit
    part = circuit.parts.get(pos)
    hit = hit_socket(game, mouse)
    if hit and (game.selected != "ERASE" or button == 3):
        target, output, pin = hit
        if button == 3 and not output:
            circuit.disconnect(target, pin)
            changed(game)
            return
        if button == 1 and output:
            game.selected = "TRACE"
            game.trace_source, game.trace_points = target, []
            game.toast("Trace: click corners, then an input socket. Esc cancels.")
            return
        if button == 1 and not output and game.trace_source is not None:
            if circuit.connect(game.trace_source, target, pin, game.trace_points):
                cancel(game)
                changed(game)
                game.toast("Trace connected. Crossings stay electrically separate.")
            return
    terminal = circuit.terminals.get(pos)
    if terminal:
        if not terminal["output"] and button in (1, 3):
            name = terminal["name"]
            if game.numeric_mode:
                mods = pygame.key.get_mods()
                step = 256 if mods & pygame.KMOD_CTRL else 16 if mods & pygame.KMOD_SHIFT else 1
                circuit.switches[name] = (int(circuit.switches[name]) + (step if button == 1 else -step)) % 65536
            elif button == 1:
                circuit.switches[name] = not circuit.switches[name]
            if game.invention:
                game.invention.edit()
        return
    if button == 3:
        if game.trace_source is not None:
            if game.trace_points:
                game.trace_points.pop()
            else:
                cancel(game)
        elif part and part.kind == "DEVICE":
            game.inspect_device(pos)
        elif part:
            circuit.set_part(pos, Part(part.kind, (part.rotation + 1) % 4, part.device, part.value))
            changed(game)
        return
    if button != 1:
        return
    if part and part.kind == "CONSTANT" and game.selected != "ERASE" and game.trace_source is None:
        import constant_editor
        constant_editor.open_editor(game, pos)
        return
    if game.selected == "TRACE":
        if game.trace_source is not None:
            bx, by, cell = game.board_metrics()
            # Half-cell routing lanes make deliberate right-angle paths easy.
            point = [round((mouse[0] - bx) / cell * 2) / 2,
                     round((mouse[1] - by) / cell * 2) / 2]
            if not game.trace_points or game.trace_points[-1] != point:
                game.trace_points.append(point)
        else:
            game.toast("Start a trace at a component's output socket.")
        return
    if game.selected == "ERASE":
        if part:
            circuit.set_part(pos, None)
        else:
            for trace in reversed(circuit.traces):
                points = trace_path(game, trace)
                if any(segment_distance(mouse, a, b) < 7 for a, b in zip(points, points[1:])):
                    circuit.traces.remove(trace)
                    circuit.reset()
                    break
        cancel(game)
        changed(game)
        return
    if game.invention and game.selected not in ("AND", "OR", "XOR", "NOT"):
        game.toast("This invention uses binary logic gates.")
        return
    requires_unlocks = (game.sandbox_context is None and game.factory_context is None
                        and not getattr(game, "adventure_editor", None))
    if requires_unlocks and game.selected in ARITHMETIC and game.selected not in game.village.arithmetic_unlocks:
        game.select_part(game.selected)
        return
    if game.selected == "DEVICE":
        from inventions import locked_blocks
        if not game.held_device or (requires_unlocks and locked_blocks(game.village, game.held_device["parts"])):
            game.toast("Invent the arithmetic inside this device before placing it.")
            return
    placed = circuit.set_part(pos, Part(game.selected, game.rotation, game.held_device if game.selected == "DEVICE" else None))
    changed(game)
    if placed and game.selected == "CONSTANT":
        import constant_editor
        constant_editor.open_editor(game, pos)


def segment_distance(point, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = dx * dx + dy * dy
    t = max(0, min(1, ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / length)) if length else 0
    return math.hypot(point[0] - a[0] - t * dx, point[1] - a[1] - t * dy)


def orthogonal(points):
    result = [points[0]]
    for point in points[1:]:
        last = result[-1]
        if point[0] != last[0] and point[1] != last[1]:
            result.append((point[0], last[1]))
        result.append(point)
    return result


def trace_path(game, trace):
    circuit = game.circuit
    source, target = tuple(trace["source"]), tuple(trace["target"])
    if source not in circuit.parts or target not in circuit.parts:
        return []
    bx, by, cell = game.board_metrics()
    start = socket(game, source, circuit.parts[source].ports()[1][0])
    end = socket(game, target, circuit.parts[target].ports()[0][trace["pin"]])
    # Short outward stubs keep the first corner clear of the component body.
    sd = VECTORS[circuit.parts[source].ports()[1][0]]
    td = VECTORS[circuit.parts[target].ports()[0][trace["pin"]]]
    points = [start, (start[0] + sd[0] * cell * .2, start[1] + sd[1] * cell * .2)]
    points += [(bx + x * cell, by + y * cell) for x, y in trace.get("points", [])]
    points += [(end[0] + td[0] * cell * .2, end[1] + td[1] * cell * .2), end]
    return orthogonal(points)


def bridge_path(points, underneath, radius=6):
    """Lift the later-drawn wire over perpendicular crossings, not junctions."""
    result = [points[0]]
    for a, b in zip(points, points[1:]):
        horizontal = abs(a[1] - b[1]) < .01
        length = math.dist(a, b)
        if length < radius * 2:
            result.append(b)
            continue
        dx, dy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
        crossings = set()
        for c, d in underneath:
            other_horizontal = abs(c[1] - d[1]) < .01
            if horizontal == other_horizontal:
                continue
            x, y = (c[0], a[1]) if horizontal else (a[0], c[1])
            distance = (x - a[0]) * dx + (y - a[1]) * dy
            inside_other = (min(c[1], d[1]) < y < max(c[1], d[1]) if horizontal else
                            min(c[0], d[0]) < x < max(c[0], d[0]))
            if inside_other and radius + 1 < distance < length - radius - 1:
                crossings.add(round(distance, 4))
        previous = -radius * 2
        for distance in sorted(crossings):
            if distance - previous < radius * 2 + 2:
                continue
            # A semicircle consistently arches upward (horizontal wires) or
            # rightward (vertical wires), independent of routing direction.
            nx, ny = (0, -1) if horizontal else (1, 0)
            for step in range(13):
                angle = math.pi * step / 12
                along = distance - radius * math.cos(angle)
                lift = radius * math.sin(angle)
                result.append((a[0] + dx * along + nx * lift,
                               a[1] + dy * along + ny * lift))
            previous = distance
        result.append(b)
    return result


def draw_traces(game):
    from game import TEAL_LIGHT, GOLD
    bx, by, cell = game.board_metrics()
    old_clip = game.screen.get_clip()
    game.screen.set_clip(pygame.Rect(bx, by, cell * 16, cell * 9))
    underneath = []
    mouse = game.mouse_pos() if hasattr(game, 'mouse_pos') else pygame.mouse.get_pos()
    hovered = game.board_pos(mouse)
    for trace in game.circuit.traces:
        points = trace_path(game, trace)
        if len(points) >= 2:
            selected = hovered in (tuple(trace["source"]), tuple(trace["target"]))
            color = GOLD if selected else TEAL_LIGHT if game.circuit.active.get(tuple(trace["source"]), 0) else (65, 91, 85)
            bridged = bridge_path(points, underneath, max(4, cell * .12))
            pygame.draw.lines(game.screen, (221, 202, 163), False, bridged, 5)
            pygame.draw.lines(game.screen, color, False, bridged, 3)
            for start, end in zip(points, points[1:]):
                if math.dist(start, end) > cell * .6:
                    direction_arrow(game.screen, start, end, color)
            underneath.extend(zip(points, points[1:]))
    if game.trace_source in game.circuit.parts:
        source = game.trace_source
        bx, by, cell = game.board_metrics()
        points = [socket(game, source, game.circuit.parts[source].ports()[1][0])]
        points += [(bx + x * cell, by + y * cell) for x, y in game.trace_points]
        mouse = game.mouse_pos() if hasattr(game, 'mouse_pos') else pygame.mouse.get_pos()
        if game.board_pos(mouse) is not None:
            points.append(mouse)
        if len(points) > 1:
            pygame.draw.lines(game.screen, GOLD, False,
                              bridge_path(orthogonal(points), underneath, max(4, cell * .12)), 3)
    game.screen.set_clip(old_clip)
