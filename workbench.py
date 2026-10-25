"""Compact workbench palette and calculation-service screens."""
import pygame
import ui_theme
import computation
import inventions
import sandbox
import sequential
import timing_workshop
import factory_controller
import component_info
from office_ui import frame
from circuit import ARITHMETIC, SEQUENTIAL, UTILITY
from gate_symbols import GATES, LESSONS, draw_gate

SYMBOLS = {"TRACE": "~", "PIPE": "-", "BEND": "L", "SPLIT": "T", "AND": "AND", "OR": "OR", "NOT": "NOT", "XOR": "XOR",
    "ADD": "+", "SUB": "-", "MUL": "x", "GT": ">", "EQ": "=", "DEVICE": "[]", "ERASE": "X", "CLOCK": "CLK", "REGISTER": "REG", "COUNTER": "CNT"}
NAMES = {"TRACE": "Draw trace", "PIPE": "Straight pipe", "BEND": "Bend", "SPLIT": "Splitter", "AND": "AND", "OR": "OR", "NOT": "NOT",
         "XOR": "XOR / exclusive OR", "ADD": "Add", "SUB": "Subtract (floor 0)", "MUL": "Multiply", "GT": "Greater than", "EQ": "Equal", "ERASE": "Erase", "CLOCK": "Clock / 4-tick cycle", "REGISTER": "Register / rising edge", "COUNTER": "Counter / rising edge"}
SYMBOLS.update(DIV="/", MOD="%", MIN="MIN", MAX="MAX", MUX="MUX")
NAMES.update(DIV="Divide / whole numbers", MOD="Remainder", MIN="Minimum", MAX="Maximum", MUX="Selector")

COMPONENT_GROUPS = {
    "Logic": ("TRACE", "AND", "OR", "NOT", "XOR", "ERASE"),
    "Math": (*ARITHMETIC, *UTILITY),
    "Memory": SEQUENTIAL,
}
COMPONENT_HINTS = {
    "TRACE": "Join an output to an input.", "ERASE": "Remove a part and its wires.",
    "ADD": "Adds both inputs.", "SUB": "First minus second; minimum 0.",
    "MUL": "Multiplies both inputs.", "GT": "1 when first > second; else 0.", "EQ": "1 when inputs match; else 0.",
    "DIV": "Whole-number division; /0 = 0.", "MOD": "Division remainder; /0 = 0.",
    "MIN": "Chooses the smaller number.", "MAX": "Chooses the larger number.",
    "MUX": "0: first / nonzero: second", "CLOCK": "Two low ticks, two high ticks.",
    "REGISTER": "Stores data on a rising clock.", "COUNTER": "Counts pulse edges; reset clears.",
    **LESSONS,
}


def controller_labels(game):
    """Label terminals outside buildable tiles, with matching physical leads."""
    from game import text, rounded, PAPER, INK, TEAL, MUTED, GOLD
    bx, by, cell = game.board_metrics()
    item = factory_controller.machine(game)
    text(game.screen, game.heading, factory_controller.purpose(game), 58, 153, PAPER, width=650)
    subtitle = f"{manufacturing_name(item)} / controller draft" if item else "Controller draft"
    text(game.screen, game.tiny, subtitle, 58, 184, (220, 207, 177), width=650)
    game.button((724, 157, 210, 34), "WIRE INPUTS", lambda: factory_controller.edit_connections(game), small=True)
    for pos, port in game.circuit.terminals.items():
        key, output = port["name"], port["output"]
        info = factory_controller.port_info(game, key)
        cy = by + (pos[1] + .5) * cell - 1
        rect = pygame.Rect(831 if output else 48, cy - 48, 112 if output else 117, 96)
        color = GOLD if output else TEAL
        rounded(game.screen, PAPER, rect, 4)
        pygame.draw.rect(game.screen, color, rect, 2, border_radius=4)
        point = (bx + (pos[0] + (1 if output else 0)) * cell - 1, cy)
        pygame.draw.line(game.screen, color, (rect.left if output else rect.right, cy), point, 2)
        text(game.screen, game.small, key + (" >" if not output else ""), rect.x + 8, rect.y + 7, TEAL)
        ui_theme.wrapped_text(game.screen, game.tiny, info["label"], rect.x + 8, rect.y + 29,
                              rect.w - 16, INK, line_height=16, max_lines=2)
        text(game.screen, game.tiny, info["source"], rect.x + 8, rect.y + 72, MUTED, width=rect.w - 16)
    # Testing controls live with the board, away from component selection.
    text(game.screen, game.tiny, "TEST INPUTS", 58, 604, PAPER)
    game.button((196, 592, 220, 34), "COPY LIVE READINGS", lambda: factory_controller.load_live_inputs(game), small=True)
    text(game.screen, game.tiny, "Click A/B to edit", 440, 604, PAPER)
    text(game.screen, game.tiny, "OUT: 0 waits / >0 permits", 640, 604, PAPER, width=285)


def manufacturing_name(item):
    import manufacturing
    return f"{manufacturing.CATALOG[item['kind']]['name']} #{item['id']}" if item else "Factory unit"


def factory_panel(game):
    from game import rounded, text, PAPER, INK, TEAL, MUTED, COPPER
    x = 956
    rounded(game.screen, PAPER, (x, 136, 272, 588), 5)
    game.button((970, 148, 116, 34), "PARTS", lambda: setattr(game, "tab", "BUILD"), active=True, small=True)
    game.button((1098, 148, 116, 34), "LIBRARY", lambda: setattr(game, "tab", "LIBRARY"), small=True)
    for i, group in enumerate(COMPONENT_GROUPS):
        game.button((970 + i * 83, 204, 78, 30), group,
                    lambda name=group: setattr(game, "factory_component_group", name),
                    active=getattr(game, "factory_component_group", "Logic") == group, small=True)
    group = getattr(game, "factory_component_group", "Logic")
    hovered = None
    for i, kind in enumerate(COMPONENT_GROUPS.get(group, COMPONENT_GROUPS["Logic"])):
        rect = pygame.Rect(970 + i % 4 * 62, 250 + i // 4 * 56, 56, 48)
        game.button(rect, "" if kind in GATES else SYMBOLS[kind], lambda k=kind: game.select_part(k),
                    active=game.selected == kind, small=True, icon=True)
        if kind in GATES:
            draw_gate(game.screen, kind, rect.center, 36, PAPER if game.selected == kind else INK)
        if rect.collidepoint(game.mouse_pos()):
            hovered = kind
    selected = hovered or game.selected
    pygame.draw.line(game.screen, (216, 198, 160), (970, 430), (1214, 430))
    text(game.screen, game.small, NAMES.get(selected, selected), 970, 448, TEAL, width=244)
    ui_theme.wrapped_text(game.screen, game.tiny, COMPONENT_HINTS.get(selected, "Saved reusable circuit."),
                         970, 473, 244, MUTED, line_height=20, max_lines=1)
    component_info.button(game, 520)
    game.button((970, 607, 116, 34), "TEST [T]", game.test_commission, small=True)
    game.button((1098, 607, 116, 34), "HELP [H]", lambda: setattr(game, "help_open", True), small=True)
    game.button((970, 661, 244, 44), "INSTALL [ENTER]", lambda: factory_controller.install(game), active=True, small=True)


def panel(game):
    if getattr(game, "adventure_editor", None):
        import adventure
        adventure.panel(game)
        return
    if game.factory_context is not None:
        factory_panel(game)
        return
    from game import rounded, text, PAPER, INK, TEAL, MUTED, COPPER
    x = 956
    rounded(game.screen, PAPER, (x, 136, 272, 588), 5)
    for i, tab in enumerate(("BUILD", "VILLAGE", "LIBRARY")):
        game.button((x + 10 + i * 84, 148, 79, 34), {"BUILD": "Build", "VILLAGE": "Town", "LIBRARY": "Library"}[tab],
                    lambda t=tab: setattr(game, "tab", t), active=tab == game.tab, small=True)
    job = computation.JOBS.get(game.active_compute)
    bench = game.invention
    free = game.sandbox_context is not None
    timing = sequential.CHALLENGES.get(game.timing_key)
    factory = game.factory_context is not None
    hardware = free or factory
    title = factory_controller.title(game) if factory else timing.title if timing else "Sandbox" if free else bench.challenge.title if bench else job.title if job else game.commission.title
    text(game.screen, game.font, title, x + 14, 203, width=244)
    text(game.screen, game.tiny, "FACTORY / time paused" if factory else "TIMING / " + timing.customer if timing else "Free build / village paused" if free else f"INVENT / {'/'.join(bench.challenge.unlocks)}" if bench else f"{job.owner} / {job.operation}" if job else f"{game.commission.customer} / {game.commission.logic}", x + 14, 232, TEAL, width=244)
    names = tuple(factory_controller.mappings(game).values()) if factory else (timing.port_names["A"], timing.port_names["B"]) if timing else tuple(game.port_names.get(k, "Input " + k) for k in ("A", "B")) if free else job.inputs if job else (game.commission.input_a, game.commission.input_b)
    if bench:
        text(game.screen, game.tiny, bench.challenge.lesson[0], x + 14, 259, MUTED, width=244)
        text(game.screen, game.tiny, "Out: " + ", ".join(bench.challenge.outputs), x + 14, 282, MUTED, width=244)
    else:
        labels = [("A", names[0]), ("B", names[1])]
        if "C" in game.circuit.switches:
            labels.append(("C", game.port_names.get("C", "Input C") if free else game.commission.input_c or game.port_names.get("C", "Extra input")))
        for i, (name, label) in enumerate(labels):
            text(game.screen, game.tiny, f"{name}: {label}", x + 14, 251 + i * 19 if len(labels) == 3 else 259 + i * 23, MUTED, width=244)
    game.button((x + 14, 309, 244, 35), "PREVIEW SIGNAL [T]" if factory else "READ OUTPUT  [T]" if free else "TEST DESIGN  [T]", game.test_commission, active=True, small=True)
    game.button((x + 14, 351, 244, 35), "INSTALL [ENTER]" if factory else "BACK TO FLOOR [ESC]" if free else "BACK TO JOB  [ESC]" if bench or timing else "COMPUTE JOBS  [C]" if job else "DELIVERY  [ENTER]",
                (lambda: factory_controller.install(game)) if factory else (lambda: timing_workshop.leave(game)) if timing else game.open_factory if free else game.close_invention if bench else game.open_compute if job else game.open_delivery_choices,
                enabled=bool(bench or job or free or timing or factory) or game.submission_ready, small=True)
    game.button((x + 14, 397, 244, 30), "BINARY INPUTS" if bench else "NUMBER INPUTS" if game.numeric_mode else "SWITCH INPUTS",
                lambda: setattr(game, "numeric_mode", not game.numeric_mode), enabled=not bool(bench), small=True)
    group = getattr(game, "bench_component_group", "Logic")
    for i, name in enumerate(COMPONENT_GROUPS):
        game.button((x + 14 + i * 83, 436, 78, 28), name,
                    lambda name=name: setattr(game, "bench_component_group", name),
                    active=group == name, small=True)
    hovered = None
    for i, kind in enumerate(COMPONENT_GROUPS.get(group, COMPONENT_GROUPS["Logic"])):
        rect = pygame.Rect(x + 14 + i % 5 * 49, 476 + i // 5 * 46, 44, 40)
        game.button(rect, '' if kind in GATES else SYMBOLS[kind], lambda k=kind: game.select_part(k), active=game.selected == kind,
                    enabled=not (bench and kind in (*ARITHMETIC, *SEQUENTIAL, *UTILITY)), small=True, icon=True)
        if kind in GATES:
            draw_gate(game.screen, kind, rect.center, 34, PAPER if game.selected == kind else INK)
        if not hardware and kind in ARITHMETIC and kind not in game.village.arithmetic_unlocks:
            pygame.draw.rect(game.screen, MUTED, (rect.right - 11, rect.top + 7, 7, 6), border_radius=1)
            pygame.draw.arc(game.screen, MUTED, (rect.right - 10, rect.top + 2, 5, 8), 0, 3.14, 1)
        if rect.collidepoint(game.mouse_pos()):
            hovered = kind
    selected = hovered or game.selected
    held = game.held_device["name"][:25] if selected == "DEVICE" and game.held_device else NAMES.get(selected, selected)
    if not hardware and selected in ARITHMETIC and selected not in game.village.arithmetic_unlocks:
        held += " / invent first"
    text(game.screen, game.small, held, x + 14, 576, TEAL, width=244)
    hint = COMPONENT_HINTS.get(selected, "Saved reusable circuit.")
    ui_theme.wrapped_text(game.screen, game.tiny, hint, x + 14, 602, 244, MUTED,
                          line_height=18, max_lines=1)
    # Keep component text above a separate, aligned row of controls.
    component_info.button(game, 635, width=72)
    if free:
        game.button((1052, 635, 162, 30), "USE 2 INPUTS" if "C" in game.circuit.switches else "USE 3 INPUTS",
                    lambda: sandbox.toggle_inputs(game), small=True)
    else:
        game.button((1052, 635, 72, 30), "GOALS", lambda: setattr(game, "invention_picker", True), small=True)
        game.button((1134, 635, 80, 30), "SANDBOX", lambda: sandbox.enter(game), small=True)
    game.button((x + 14, 684, 116, 29), "HELP [H]", lambda: setattr(game, "help_open", True), small=True)
    game.button((x + 142, 684, 116, 29), "DETAILS", lambda: setattr(game, "task_help_open", True), small=True)


def library_panel(game):
    """Keep port names, design headings and row controls in separate bands."""
    from game import text, PANEL_X, TEAL, MUTED
    from circuit import standard_device_ports
    x, width = PANEL_X + 23, 412
    text(game.screen, game.heading, "Design library", x, 210, width=width)
    text(game.screen, game.small, "Save a version; reuse it as a device.", x, 254, MUTED, width=width)
    game.button((x, 318, 265, 44), "Save new version  [S]", game.save_copy, active=True, small=True)
    game.button((PANEL_X + 300, 318, 135, 44), "Name ports", game.edit_ports, small=True)
    summary = " / ".join(game.port_names.get(p["name"], p["name"]) for p in game.circuit.terminals.values())
    text(game.screen, game.tiny, summary, x, 370, TEAL, width=width)
    text(game.screen, game.small, f"{len(game.designs)} SAVED DESIGNS", x, 394, MUTED, width=width)
    if not game.designs:
        text(game.screen, game.small, "No saved designs", x, 440, MUTED, width=width)
        return
    ordered = list(range(len(game.designs) - 1, -1, -1))
    pages = (len(ordered) + 3) // 4
    game.library_page = max(0, min(game.library_page, pages - 1))
    for row, index in enumerate(ordered[game.library_page * 4:(game.library_page + 1) * 4]):
        item = game.designs[index]
        if not isinstance(item, dict):
            continue
        y = 421 + row * 66
        text(game.screen, game.small, f"{item.get('name', 'Design')}  v{item.get('version', 1)}",
             x, y, width=300)
        game.button((PANEL_X + 340, y - 3, 95, 25), "Delete",
                    lambda j=index: game.request_delete_design(j), small=True, danger=True)
        game.button((x, y + 24, 190, 30), "Load / edit", lambda j=index: game.load_design(j), small=True)
        prototype = bool(item.get("invention")) or not standard_device_ports(item.get("parts", []))
        game.button((PANEL_X + 225, y + 24, 210, 30), "Prototype template" if prototype else "Place device",
                    lambda j=index: game.select_device(j), enabled=not prototype and not bool(game.invention), small=True)
    if pages > 1:
        game.button((x, 686, 95, 30), "Previous", lambda: setattr(game, "library_page", max(0, game.library_page - 1)), small=True)
        text(game.screen, game.tiny, f"Page {game.library_page + 1}/{pages}", PANEL_X + 192, 694, MUTED, width=140)
        game.button((PANEL_X + 340, 686, 95, 30), "Next", lambda: setattr(game, "library_page", min(pages - 1, game.library_page + 1)), small=True)


def village_panel(game):
    from game import text, PANEL_X, TEAL, MUTED, COPPER
    x, width = PANEL_X + 23, 412
    text(game.screen, game.heading, f"Village / day {game.village.day}", x, 210, width=width)
    text(game.screen, game.font, f"Your purse   {game.village.coins} coins", x, 255, COPPER, width=width)
    text(game.screen, game.small, "GOODS & PRICES", x, 302, MUTED, width=width)
    lines = (f"Grain {game.village.grain}    Flour {game.village.flour}    Bread {game.village.bread}",
             f"Bread price {game.village.bread_price} coins / loaf", game.village.market_note)
    for i, line in enumerate(lines):
        text(game.screen, game.tiny, line, x, 332 + 26 * i, TEAL, width=width)
    text(game.screen, game.small, "BUSINESSES / CAPACITY & CASH", x, 425, MUTED, width=width)
    for row, (key, firm) in enumerate(list(game.village.businesses.items())[:4]):
        name = firm["name"].replace("Copperside ", "")[:13]
        y = 451 + row * 23
        text(game.screen, game.tiny, name, x, y, width=145)
        text(game.screen, game.tiny, f"{game.village.capacity(key)}/day", x + 155, y, width=85)
        text(game.screen, game.tiny, f"{firm['cash']} coins", x + 250, y, width=width - 250)
    game.button((x, 551, width, 39), "Advance one day", game.next_day, active=True, small=True,
                enabled=game.sandbox_context is None and game.factory_context is None
                and not getattr(game, "adventure_editor", None))
    text(game.screen, game.small, "TOWN LEDGER", x, 605, MUTED, width=width)
    for i, line in enumerate(game.village.journal[:4]):
        text(game.screen, game.tiny, line, x, 632 + 20 * i, MUTED, width=width)


def invention_picker(game):
    from game import rounded, text, PAPER, TEAL, MUTED
    shade = pygame.Surface(game.screen.get_size(), pygame.SRCALPHA)
    shade.fill((20, 29, 29, 180))
    game.screen.blit(shade, (0, 0))
    game.buttons.clear()
    rounded(game.screen, PAPER, (280, 80, 720, 620), 7)
    text(game.screen, game.heading, "WORKSHOP GOALS", 310, 104, TEAL)
    text(game.screen, game.small, "Binary inventions unlock arithmetic blocks", 310, 144, MUTED)
    for i, (key, challenge) in enumerate(inventions.CHALLENGES.items()):
        ready = not challenge.prerequisite or challenge.prerequisite in game.village.arithmetic_unlocks
        done = all(block in game.village.arithmetic_unlocks for block in challenge.unlocks)
        label = f"{challenge.title} / {'earned' if done else '/'.join(challenge.unlocks)}"
        if not ready:
            label += f" / {challenge.prerequisite} first"
        game.button((310, 178 + i * 49, 660, 40), label, lambda k=key: game.open_invention(k), enabled=ready, small=True)
    text(game.screen, game.small, "Timing goals support your neighbors' stories", 310, 392, MUTED)
    for i, (key, challenge) in enumerate(sequential.CHALLENGES.items()):
        label = challenge.title + (" / certified" if key in game.village.sequential_records else " / timing")
        game.button((310, 428 + i * 49, 660, 40), label,
                    lambda k=key: timing_workshop.enter(game, k), small=True)
    game.button((750, 638, 220, 38), "CLOSE [ESC]", lambda: setattr(game, "invention_picker", False), small=True)


def invention_results(game):
    from game import rounded, text, PAPER, TEAL, RED, MUTED
    bench = game.invention
    shade = pygame.Surface(game.screen.get_size(), pygame.SRCALPHA)
    shade.fill((20, 29, 29, 180))
    game.screen.blit(shade, (0, 0))
    game.buttons.clear()
    rounded(game.screen, PAPER, (270, 110, 740, 552), 7)
    text(game.screen, game.heading, "INVENTION TESTS", 300, 135, TEAL)
    text(game.screen, game.small, bench.message, 300, 174, TEAL if all(row["passed"] for row in bench.rows) else RED, width=680)
    text(game.screen, game.tiny, "Inputs: " + ", ".join(bench.challenge.inputs) + "   Outputs: " + ", ".join(bench.challenge.outputs), 300, 202, MUTED, width=680)
    for title, x in (("INPUTS", 330), ("EXPECTED", 470), ("ACTUAL", 610), ("RESULT", 790)):
        text(game.screen, game.tiny, title, x, 228, MUTED)
    for i, row in enumerate(bench.rows[game.test_scroll:game.test_scroll + 8]):
        bits = "".join(str(row["bits"][name]) for name in bench.challenge.inputs)
        expected = "".join(str(row["expected"][name]) for name in bench.challenge.outputs)
        actual = "".join(str(row["actual"].get(name, "?")) for name in bench.challenge.outputs)
        y = 250 + i * 35
        game.button((300, y, 680, 32), "", lambda n=game.test_scroll + i: bench.load_case(n), small=True)
        for value, x in ((bits, 330), (expected, 470), (actual, 610), ("PASS" if row["passed"] else "FAIL", 790)):
            text(game.screen, game.small, value, x, y + 8, TEAL if row["passed"] else RED)
    text(game.screen, game.tiny, f"Rows {game.test_scroll + 1}-{min(len(bench.rows), game.test_scroll + 8)} / {len(bench.rows)}   UP/DOWN or wheel to scroll", 300, 552, MUTED)
    text(game.screen, game.tiny, "Click a case to inspect its signals on the floor.", 300, 578, MUTED)
    game.button((480, 615, 240, 32), "TASK DETAILS", lambda: setattr(game, "task_help_open", True), small=True)
    game.button((740, 615, 240, 32), "BACK TO FLOOR [ESC]", lambda: setattr(bench, "show_results", False), small=True)


def compute_screen(game):
    from game import rounded, text, PAPER, INK, TEAL, MUTED, COPPER, RED
    village = game.village
    frame(game.screen, "COMPUTATION OFFICE", game.big,
          subtitle="Build a calculator, verify its cases, then sell calculation runs to the village.", small=game.small)
    rounded(game.screen, PAPER, (447, 140, 781, 555), 6)
    used = sum(entry["day"] == village.day for entry in village.compute_orders)
    text(game.screen, game.tiny, f"DAY {village.day} / {village.coins}c / SLOTS {used}/{computation.DAILY_CAPACITY} / NET EARNED {village.compute_earned}c", 715, 61, PAPER, width=496)
    for i, (key, job) in enumerate(computation.JOBS.items()):
        y = 151 + i * 125
        game.button((58, y, 370, 112), "", lambda k=key: game.select_compute(k), active=game.compute_key == key, small=True)
        color = PAPER if game.compute_key == key else INK
        text(game.screen, game.font, job.title, 73, y + 15, color, width=338)
        text(game.screen, game.small, f"{job.owner} / {job.operation} / setup {job.reward}c", 73, y + 46, color, width=338)
        registered = village.compute_designs.get(key)
        text(game.screen, game.tiny, f"Registered r{registered.get('revision', 1)} / {job.fee}c per run" if registered else
             f"Invent {job.operation} first / same workshop floor" if job.operation not in village.arithmetic_unlocks else "Design needed / floor plan stays available", 73, y + 80, color, width=338)
    job = computation.JOBS[game.compute_key]
    text(game.screen, game.heading, job.title, 463, 153, TEAL)
    text(game.screen, game.small, job.description, 463, 190, width=750)
    text(game.screen, game.tiny, f"A: {job.inputs[0]} / B: {job.inputs[1]} -> {job.output}", 463, 221, MUTED)
    a, b = computation.request_inputs(village, game.compute_key)
    text(game.screen, game.small, f"Today's request: {a} {job.operation} {b}   /   Gross {job.fee}c - costs 3c = {job.fee - 3}c net", 463, 251, COPPER)
    results = game.compute_results
    columns = (478, 570, 662, 800, 938)
    for x, label in zip(columns, ("A", "B", "EXPECTED", "ACTUAL", "RESULT")):
        text(game.screen, game.small, label, x, 298, MUTED)
    for i, row in enumerate(results[game.test_scroll:game.test_scroll + 8]):
        y = 329 + i * 23
        color = TEAL if row["passed"] else RED
        values = (row['a'], row['b'], row['expected'], row['actual'], 'PASS' if row['passed'] else 'FAIL')
        for x, value in zip(columns, values):
            text(game.screen, game.small, str(value), x, y, color, width=85)
    if not results:
        text(game.screen, game.font, "No test yet. Choose Build, then Test floor.", 478, 358, MUTED)
    else:
        text(game.screen, game.tiny, f"Rows {game.test_scroll + 1}-{min(len(results), game.test_scroll + 8)} / {len(results)}   UP/DOWN or wheel", 478, 516, MUTED)
    receipt = next((entry for entry in reversed(village.compute_orders) if entry["job"] == game.compute_key), None)
    if receipt:
        text(game.screen, game.tiny, f"RECEIPT / DAY {receipt['day']}: {receipt['a']} {job.operation} {receipt['b']} = {receipt['result']} / +{receipt['net']}c net", 478, 539, TEAL)
    for i, (label, action) in enumerate((("BUILD", game.build_compute), ("TEST FLOOR", game.test_compute),
                                        ("REGISTER", game.approve_compute), ("RUN ORDER", game.run_compute))):
        game.button((463 + i * 190, 565, 180, 40), label, action, active=i == 3, small=True)
    text(game.screen, game.tiny, "Per run: fuel 2c + maintenance 1c + one slot. 8-bit inputs / 16-bit result.", 463, 624, MUTED, width=750)
    text(game.screen, game.tiny, "Completed orders add +1 capacity to the customer's next production run.", 463, 648, MUTED, width=750)
    game.button((58, 565, 370, 40), "ADVANCE DAY / REFILL ORDERS", game.next_day, small=True)
    game.button((58, 619, 370, 38), "BACK  [ESC]", game.close_compute, small=True)
    game.button((463, 665, 180, 24), "TASK DETAILS", lambda: setattr(game, "task_help_open", True), small=True)
    text(game.screen, game.tiny, game.compute_message, 58, 705, PAPER, width=1158)
