"""Compact workbench palette and calculation-service screens."""
import pygame
import computation
import inventions
from circuit import PLACEABLE, ARITHMETIC

SYMBOLS = {"PIPE": "-", "BEND": "L", "SPLIT": "T", "AND": "&", "OR": "OR", "NOT": "!", "XOR": "^",
    "ADD": "+", "SUB": "-", "MUL": "x", "GT": ">", "EQ": "=", "DEVICE": "[]", "ERASE": "X"}
NAMES = {"PIPE": "Straight pipe", "BEND": "Bend", "SPLIT": "Splitter", "AND": "AND", "OR": "OR", "NOT": "NOT",
         "XOR": "Exclusive OR", "ADD": "Add", "SUB": "Subtract (floor 0)", "MUL": "Multiply", "GT": "Greater than", "EQ": "Equal", "ERASE": "Erase"}


def panel(game):
    from game import rounded, text, PAPER, INK, TEAL, MUTED, COPPER
    x = 956
    rounded(game.screen, PAPER, (x, 136, 272, 588), 5)
    for i, tab in enumerate(("BUILD", "VILLAGE", "LIBRARY")):
        game.button((x + 10 + i * 84, 148, 79, 34), {"BUILD": "Build", "VILLAGE": "Town", "LIBRARY": "Library"}[tab],
                    lambda t=tab: setattr(game, "tab", t), active=tab == game.tab, small=True)
    job = computation.JOBS.get(game.active_compute)
    title = job.title if job else game.commission.title
    text(game.screen, game.font, title, x + 14, 203)
    text(game.screen, game.tiny, f"{job.owner} / {job.operation}" if job else f"{game.commission.customer} / {game.commission.logic}", x + 14, 232, TEAL)
    names = job.inputs if job else (game.commission.input_a, game.commission.input_b)
    text(game.screen, game.tiny, f"A: {names[0]}", x + 14, 259, MUTED)
    text(game.screen, game.tiny, f"B: {names[1]}", x + 14, 282, MUTED)
    game.button((x + 14, 309, 244, 35), "TEST DESIGN  [T]", game.test_commission, active=True, small=True)
    game.button((x + 14, 351, 244, 35), "COMPUTE JOBS  [C]" if job else "DELIVERY  [ENTER]",
                game.open_compute if job else game.open_delivery_choices, enabled=bool(job) or game.submission_ready, small=True)
    game.button((x + 14, 397, 244, 30), "NUMBER INPUTS" if game.numeric_mode else "SWITCH INPUTS",
                lambda: setattr(game, "numeric_mode", not game.numeric_mode), small=True)
    palette = (*PLACEABLE, *ARITHMETIC, "ERASE")
    hovered = None
    for i, kind in enumerate(palette):
        rect = pygame.Rect(x + 14 + i % 5 * 49, 444 + i // 5 * 46, 44, 40)
        game.button(rect, SYMBOLS[kind], lambda k=kind: game.select_part(k), active=game.selected == kind, small=True, icon=True)
        if kind in ARITHMETIC and kind not in game.village.arithmetic_unlocks:
            pygame.draw.rect(game.screen, MUTED, (rect.right - 11, rect.top + 7, 7, 6), border_radius=1)
            pygame.draw.arc(game.screen, MUTED, (rect.right - 10, rect.top + 2, 5, 8), 0, 3.14, 1)
        if rect.collidepoint(pygame.mouse.get_pos()):
            hovered = kind
    selected = hovered or game.selected
    held = game.held_device["name"][:25] if selected == "DEVICE" and game.held_device else NAMES.get(selected, selected)
    if selected in ARITHMETIC and selected not in game.village.arithmetic_unlocks:
        held += " / invent first"
    text(game.screen, game.small, held, x + 14, 590, TEAL)
    game.button((x + 14, 614, 244, 30), "INVENTIONS [I]", game.open_invention, small=True)
    text(game.screen, game.tiny, "R rotate / A,B: click +1 / -1", x + 14, 648, MUTED)
    text(game.screen, game.tiny, "16-bit bus / requests 0..255", x + 14, 659, COPPER)
    game.button((x + 14, 684, 244, 29), "HELP  [H]", lambda: setattr(game, "help_open", True), small=True)


def compute_screen(game):
    from game import rounded, text, PAPER, INK, TEAL, MUTED, COPPER, RED
    village = game.village
    game.screen.fill((61, 85, 79))
    rounded(game.screen, PAPER, (32, 25, 1216, 704), 9)
    text(game.screen, game.big, "COMPUTATION OFFICE", 58, 49, TEAL)
    used = sum(entry["day"] == village.day for entry in village.compute_orders)
    text(game.screen, game.small, f"DAY {village.day} / {village.coins}c / SLOTS {used}/{computation.DAILY_CAPACITY} / NET EARNED {village.compute_earned}c", 660, 61)
    text(game.screen, game.small, "Build a calculator, verify its cases, then sell calculation runs to the village.", 58, 99, MUTED)
    for i, (key, job) in enumerate(computation.JOBS.items()):
        y = 151 + i * 125
        game.button((58, y, 370, 112), "", lambda k=key: game.select_compute(k), active=game.compute_key == key, small=True)
        color = PAPER if game.compute_key == key else INK
        text(game.screen, game.font, job.title, 73, y + 15, color)
        text(game.screen, game.small, f"{job.owner} / {job.operation} / setup {job.reward}c", 73, y + 46, color)
        registered = village.compute_designs.get(key)
        text(game.screen, game.tiny, f"Registered r{registered.get('revision', 1)} / {job.fee}c per run" if registered else
             f"Invent {job.operation} first / Build opens its lesson" if job.operation not in village.arithmetic_unlocks else "Design needed / floor plan stays available", 73, y + 80, color)
    job = computation.JOBS[game.compute_key]
    text(game.screen, game.heading, job.title, 463, 153, TEAL)
    text(game.screen, game.small, job.description, 463, 190)
    text(game.screen, game.tiny, f"A: {job.inputs[0]} / B: {job.inputs[1]} -> {job.output}", 463, 221, MUTED)
    a, b = computation.request_inputs(village, game.compute_key)
    text(game.screen, game.small, f"Today's request: {a} {job.operation} {b}   /   Gross {job.fee}c - costs 3c = {job.fee - 3}c net", 463, 251, COPPER)
    results = game.compute_results
    text(game.screen, game.small, "A       B       EXPECTED     ACTUAL       RESULT", 478, 298, MUTED)
    for i, row in enumerate(results):
        y = 329 + i * 26
        color = TEAL if row["passed"] else RED
        text(game.screen, game.small, f"{row['a']:<7} {row['b']:<7} {row['expected']:<12} {row['actual']:<12} {'PASS' if row['passed'] else 'FAIL'}", 478, y, color)
    if not results:
        text(game.screen, game.font, "No test yet. Choose Build, then Test floor.", 478, 358, MUTED)
    receipt = next((entry for entry in reversed(village.compute_orders) if entry["job"] == game.compute_key), None)
    if receipt:
        text(game.screen, game.tiny, f"RECEIPT / DAY {receipt['day']}: {receipt['a']} {job.operation} {receipt['b']} = {receipt['result']} / +{receipt['net']}c net", 478, 539, TEAL)
    for i, (label, action) in enumerate((("BUILD", game.build_compute), ("TEST FLOOR", game.test_compute),
                                        ("REGISTER", game.approve_compute), ("RUN ORDER", game.run_compute))):
        game.button((463 + i * 190, 565, 180, 40), label, action, active=i == 3, small=True)
    text(game.screen, game.tiny, "Each run uses 1 fuel (2c), maintenance (1c), and one daily slot. Inputs: 8 bits; result: 16 bits.", 463, 624, MUTED)
    text(game.screen, game.tiny, "A completed calculation improves that customer's next production run by +1 capacity.", 463, 648, MUTED)
    game.button((58, 565, 370, 40), "ADVANCE DAY / REFILL ORDERS", game.next_day, small=True)
    game.button((58, 619, 370, 38), "BACK  [ESC]", game.close_compute, small=True)
    text(game.screen, game.tiny, game.compute_message[:150], 58, 693, TEAL)
