"""A tangible production floor around the existing circuit workbench."""
import math
import pygame

import manufacturing
import factory_art
from office_ui import frame
from ui_theme import PAPER, CREAM, INK, MUTED, TEAL, COPPER, GOLD, draw_panel, fit_text, wrapped_text


FLOOR = pygame.Rect(74, 210, 684, 384)
CELL_W, CELL_H = 76, 64
PAGES = ("floor", "equipment", "supplies", "orders")
PAGE_NAMES = ("Machine", "Equipment", "Supplies", "Customers")


def prepare(game):
    defaults = {"factory_page": "floor", "factory_selected": None,
                "factory_placing": None, "factory_moving": None, "factory_message": "", "factory_order_page": 0,
                "factory_dialog": None, "factory_dialog_buttons": [], "factory_input_ready": True}
    for name, value in defaults.items():
        if not hasattr(game, name):
            setattr(game, name, value)


def tile_at(point):
    if not FLOOR.collidepoint(point):
        return None
    return ((point[0] - FLOOR.x) // CELL_W, (point[1] - FLOOR.y) // CELL_H)


def tile_rect(pos):
    return pygame.Rect(FLOOR.x + pos[0] * CELL_W, FLOOR.y + pos[1] * CELL_H, CELL_W, CELL_H)


def selected(game):
    return next((item for item in manufacturing.state(game.village)["equipment"]
                 if item["id"] == game.factory_selected), None)


def notify(game, result):
    okay, message = result
    game.factory_message = message
    game.toast(message)
    if okay:
        game.save_game()
    return okay


def switch_page(game, page):
    game.factory_page = page
    game.factory_placing = game.factory_moving = None


def place(game, kind):
    game.factory_placing = kind
    game.factory_moving = None
    game.factory_message = "Choose an empty floor tile. Payment happens only when placed."


def move(game, item):
    game.factory_moving = item["id"]
    game.factory_placing = None
    game.factory_message = "Choose an empty tile for this equipment. Esc cancels."


def click(game, point, button):
    """One action per click; equipment placement cannot trigger another control."""
    prepare(game)
    if not game.factory_input_ready:
        return True
    if game.factory_dialog is not None:
        if button == 1:
            for rect, action in reversed(game.factory_dialog_buttons):
                if rect.collidepoint(point):
                    action()
                    break
        return True
    if button == 3 and (game.factory_placing or game.factory_moving is not None):
        game.factory_placing = game.factory_moving = None
        game.factory_message = "Placement cancelled."
        return True
    if button != 1:
        return False
    for rect, action in reversed(game.buttons):
        if rect.collidepoint(point):
            action()
            return True
    pos = tile_at(point)
    if pos is None:
        return False
    state = manufacturing.state(game.village)
    if game.factory_placing:
        kind = game.factory_placing
        if notify(game, manufacturing.buy_equipment(game.village, kind, pos)):
            game.factory_selected = state["equipment"][-1]["id"]
            game.factory_placing = None
            game.factory_page = "floor"
        return True
    if game.factory_moving is not None:
        if notify(game, manufacturing.move_equipment(game.village, game.factory_moving, pos)):
            game.factory_moving = None
        return True
    item = next((item for item in state["equipment"] if tuple(item["pos"]) == pos), None)
    game.factory_selected = item["id"] if item else None
    game.factory_page = "floor"
    return True


def handle_key(game, event):
    prepare(game)
    if game.factory_dialog is not None:
        if event.key == pygame.K_ESCAPE:
            close_dialog(game)
        return True
    if event.key == pygame.K_ESCAPE:
        if game.factory_placing or game.factory_moving is not None:
            game.factory_placing = game.factory_moving = None
            game.factory_message = "Placement cancelled."
            return True
        if game.factory_page != "floor":
            game.factory_page = "floor"
            return True
        return False
    return False


def equipment_sprite(surface, kind, rect, *, working=False, value=0, phase=0):
    """Detailed workshop furniture, sharing the original placement footprint."""
    factory_art.equipment(surface, kind, rect, working=working, value=value, phase=phase)


def item_sprite(surface, kind, rect):
    cx, cy = rect.center
    if kind == "metal":
        for dx, dy in ((-18, 5), (4, 5), (-7, -9)):
            pygame.draw.polygon(surface, (121, 145, 143), [(cx + dx - 9, cy + dy + 8), (cx + dx - 4, cy + dy - 7),
                                (cx + dx + 12, cy + dy - 7), (cx + dx + 17, cy + dy + 8)])
            pygame.draw.line(surface, PAPER, (cx + dx - 3, cy + dy - 5), (cx + dx + 10, cy + dy - 5), 2)
    elif kind == "fittings":
        for dx, dy in ((-13, 7), (12, -7)):
            pygame.draw.circle(surface, COPPER, (cx + dx, cy + dy), 15)
            pygame.draw.circle(surface, GOLD, (cx + dx, cy + dy), 11, 3)
            pygame.draw.circle(surface, (60, 78, 65), (cx + dx, cy + dy), 6)
    elif kind == "metal_plates":
        for dy in (12, 4, -4):
            pygame.draw.polygon(surface, (104, 142, 142), [(cx - 26, cy + dy), (cx + 9, cy + dy - 13), (cx + 27, cy + dy - 4), (cx - 9, cy + dy + 10)])
            pygame.draw.lines(surface, PAPER, False, [(cx - 25, cy + dy), (cx - 9, cy + dy + 9), (cx + 26, cy + dy - 4)], 2)
    elif kind in ("steam_valves", "precision_gears"):
        if kind == "steam_valves":
            pygame.draw.line(surface, COPPER, (cx - 23, cy + 12), (cx + 23, cy + 12), 13)
            pygame.draw.line(surface, GOLD, (cx, cy + 12), (cx, cy - 16), 7)
            pygame.draw.ellipse(surface, TEAL, (cx - 19, cy - 26, 38, 16), 5)
        else:
            for i in range(10):
                angle = i * math.tau / 10
                x, y = cx + round(math.cos(angle)*19), cy + round(math.sin(angle)*19)
                pygame.draw.circle(surface, COPPER, (x, y), 6)
            pygame.draw.circle(surface, GOLD, (cx, cy), 21)
            pygame.draw.circle(surface, COPPER, (cx, cy), 15, 3)
            pygame.draw.circle(surface, TEAL, (cx, cy), 7)
    elif kind == "fuel":
        for dx, dy in ((-15, 7), (6, 10), (-4, -8)):
            pygame.draw.polygon(surface, (59, 61, 54), [(cx + dx - 10, cy + dy + 9), (cx + dx - 13, cy + dy - 5),
                                (cx + dx, cy + dy - 13), (cx + dx + 12, cy + dy - 5), (cx + dx + 10, cy + dy + 9)])
            pygame.draw.line(surface, (100, 107, 91), (cx + dx - 8, cy + dy - 3), (cx + dx, cy + dy - 8), 2)
    else:
        pygame.draw.rect(surface, TEAL, (cx - 25, cy - 13, 50, 31), border_radius=5)
        pygame.draw.rect(surface, COPPER, (cx - 12, cy - 22, 24, 13), 4, border_radius=3)
        pygame.draw.rect(surface, GOLD, (cx - 4, cy - 4, 8, 13), border_radius=1)


def _cable(surface, start, end, color, offset=0):
    # Wires run along tile seams, leaving the furniture silhouettes clear.
    sy, ey = start[1] - CELL_H / 2 + offset, end[1] - CELL_H / 2 + offset
    lane = end[0] - CELL_W / 2 + offset
    source_x = start[0] + (24 if offset == 0 else 0)
    target_x = end[0] + (-24 if offset < 0 else 0)
    points = [(source_x, start[1] - 22), (source_x, sy),
              (lane, sy), (lane, ey), (target_x, ey), (target_x, end[1] - 22)]
    pygame.draw.lines(surface, (64, 63, 47), False, points, 5)
    pygame.draw.lines(surface, color, False, points, 2)
    from workshop_floor import direction_arrow
    for a, b in zip(points, points[1:]):
        if math.dist(a, b) > 22:
            direction_arrow(surface, a, b, color, 4)
    pygame.draw.circle(surface, color, points[0], 4)
    pygame.draw.circle(surface, color, points[-1], 4, 1)


def input_summary(game, item, port):
    import factory_controller
    controller = factory_controller.wiring(game.village, item["id"])
    sensor = controller.get("inputs", {}).get(port)
    if sensor is None:
        return f"{port} / no board installed"
    rack = controller.get("sources", {}).get(port)
    source = f"Rack #{rack}" if rack is not None else "Unit"
    label = manufacturing.SENSOR_NAMES.get(sensor, sensor)
    return f"{port} <- {source}: {label}"


def draw_floor(game, state):
    screen = game.screen
    factory_art.room(screen, accumulator='steam_accumulator' in state['unlocks'])
    daily = getattr(game.village, 'daily_life', {}) or {}
    phase = daily.get('elapsed', 0) + daily.get('accumulator', 0)
    if getattr(game, 'reduced_motion', False):
        phase = 0
    by_id = {item["id"]: item for item in state["equipment"]}
    focused = game.factory_selected
    highlighted = set()
    for cabinet in state["equipment"]:
        if cabinet["kind"] != "controller":
            continue
        unit = by_id.get(cabinet.get("machine_id"))
        if not unit:
            continue
        sources = (unit.get("controller") or {}).get("sources", {})
        displays = [e for e in state["equipment"] if e["kind"] == "display" and
                    e.get("display", {}).get("source") == "signal" and e["display"].get("machine_id") == unit["id"]]
        active = focused is not None and focused in (cabinet["id"], unit["id"], *sources.values(), *(e["id"] for e in displays))
        if active:
            highlighted.update((cabinet["id"], unit["id"], *sources.values(), *(e["id"] for e in displays)))
        destination = tile_rect(cabinet["pos"]).center
        _cable(screen, destination, tile_rect(unit["pos"]).center, GOLD if active or focused is None else (130, 113, 78))
        for port, source in sources.items():
            rack = by_id.get(source)
            if rack and rack["kind"] == "storage":
                _cable(screen, tile_rect(rack["pos"]).center, destination,
                       ((137, 220, 216) if port == "A" else (171, 190, 236)) if active or focused is None else (115, 132, 119), -5 if port == "A" else 5)
        for display in displays:
            _cable(screen, destination, tile_rect(display["pos"]).center,
                   (177, 219, 148) if active or focused is None else (115, 132, 119))
    for item in state["equipment"]:
        rect = tile_rect(item["pos"])
        if item["id"] == game.factory_selected:
            factory_art.selection(screen, rect, PAPER)
        elif item["id"] in highlighted:
            factory_art.selection(screen, rect, GOLD)
        reading = manufacturing.display_reading(game.village, item["id"]) if item["kind"] == "display" else {}
        equipment_sprite(screen, item["kind"], rect, working=item.get("busy", 0) > 0,
                         value=reading.get("value", 0), phase=phase)
        if item.get('busy', 0) > 0 and item['kind'] in manufacturing.PRODUCTION:
            # A live activity strip; remaining time in the inspector is exact.
            # Avoid inventing a batch percentage for saves with no start duration.
            for step in range(3):
                color = (168, 214, 157) if int(phase * 3) % 3 == step else (68, 89, 66)
                pygame.draw.rect(screen, color, (rect.x + 23 + step * 11, rect.bottom - 5, 8, 3))
        if item.get("mode") == "auto":
            pygame.draw.circle(screen, (149, 217, 148), (rect.right - 8, rect.top + 8), 4)
        if item["id"] in highlighted or item["id"] == focused:
            fit_text(screen, game.tiny, f"#{item['id']}", rect.x + 5, rect.bottom - 15, rect.w - 10, INK)
    for cabinet in state["equipment"]:
        if cabinet["kind"] != "controller" or cabinet["id"] not in highlighted:
            continue
        unit = by_id.get(cabinet.get("machine_id"))
        if not unit:
            continue
        rect = tile_rect(cabinet["pos"])
        for i, port in enumerate(("A", "B", "OUT")):
            badge = pygame.Rect(rect.left + 2 + i * 24, rect.top - 16, 26 if port == "OUT" else 23, 16)
            pygame.draw.rect(screen, (45, 65, 61), badge, border_radius=2)
            fit_text(screen, game.tiny, port, badge.x + 1, badge.y + 1, badge.w - 2, GOLD if port == "OUT" else PAPER)
    pos = tile_at(game.mouse_pos() if hasattr(game, 'mouse_pos') else pygame.mouse.get_pos())
    if pos and (game.factory_placing or game.factory_moving is not None):
        occupied = any(tuple(e["pos"]) == pos and e["id"] != game.factory_moving for e in state["equipment"])
        factory_art.selection(screen, tile_rect(pos), (211, 96, 74) if occupied else PAPER)
    elif pos:
        factory_art.selection(screen, tile_rect(pos), (209, 181, 125))


def has_dialog(game):
    return getattr(game, "factory_dialog", None) is not None


def open_dialog(game, kind, **values):
    prepare(game)
    game.factory_dialog = {"kind": kind, **values}
    game.factory_message = ""
    game.factory_dialog_buttons = []
    game.buttons.clear()
    game.factory_input_ready = False


def close_dialog(game):
    game.factory_dialog = None
    game.factory_dialog_buttons = []
    game.buttons.clear()
    game.factory_input_ready = False


def place_from_dialog(game, kind):
    close_dialog(game)
    place(game, kind)


def draw(game):
    prepare(game)
    state = manufacturing.state(game.village)
    frame(game.screen, "BOOLE'S WORKSHOP", game.big,
          subtitle=f"Day {game.village.day}  /  {game.village.coins}c  /  {sum(state['goods'].values())} goods", small=game.small)
    game.button((785, 48, 193, 36), "CIRCUIT BENCH", game.open_circuit_bench, small=True)
    game.button((990, 48, 125, 36), "TOWN", lambda: setattr(game, "scene", "town"), small=True)
    game.button((1125, 48, 105, 36), "PAUSE", lambda: setattr(game, "pause_menu_open", True), small=True)
    status = ("PLACE " + manufacturing.CATALOG[game.factory_placing]["name"] if game.factory_placing else
              "MOVE EQUIPMENT" if game.factory_moving is not None else "WORKSHOP FLOOR")
    draw_floor(game, state)
    fit_text(game.screen, game.small, status, 81, 156, 300, PAPER)
    if 'steam_accumulator' in state['unlocks']:
        fit_text(game.screen, game.tiny, "Steam reserve / -20% batch time", 81, 182, 300, (205, 220, 180))
    else:
        fit_text(game.screen, game.tiny, "Select a machine to inspect its work", 81, 182, 300, (205, 220, 180))
    draw_panel(game.screen, (794, 144, 436, 572))
    tab_x = 808
    for page, label, tab_width in zip(PAGES, PAGE_NAMES, (86, 108, 102, 108)):
        game.button((tab_x, 160, tab_width, 31), label, lambda p=page: switch_page(game, p),
                    active=game.factory_page == page, small=True)
        tab_x += tab_width + 4
    if game.factory_page == "equipment":
        draw_equipment(game, state)
    elif game.factory_page == "supplies":
        draw_supplies(game, state)
    elif game.factory_page == "orders":
        draw_orders(game, state)
    else:
        draw_machine(game, state)
    if game.factory_message:
        wrapped_text(game.screen, game.tiny, game.factory_message, 812, 661, 397, COPPER, line_height=18, max_lines=2)
    import factory_shannon
    factory_shannon.draw(game, pygame.Rect(62, 612, 710, 103))
    if has_dialog(game):
        draw_dialog(game)
    game.factory_input_ready = True


def icon_rect(index):
    return pygame.Rect(823 + (index % 3) * 128, 224 + (index // 3) * 112, 112, 96)


EQUIPMENT_LABELS = {"bench": "Assembly", "storage": "Storage rack", "controller": "Controller",
                    "display": "Display", "buyer": "Procurement", "seller": "Dispatch",
                    "press": "Metal press", "lathe": "Valve lathe", "precision_machine": "Gear cutter"}


def catalogue_label(game, rect, title, detail, *, locked=False):
    fit_text(game.screen, game.tiny, title, rect.x + 7, rect.y + 64, rect.w - 14, INK)
    fit_text(game.screen, game.tiny, detail, rect.x + 7, rect.y + 80, rect.w - 14, COPPER if locked else TEAL)


def draw_equipment(game, state):
    fit_text(game.screen, game.tiny, "Tess's equipment / choose to inspect", 817, 201, 391, MUTED)
    for i, kind in enumerate(manufacturing.CATALOG):
        rect = icon_rect(i)
        game.button(rect, "", lambda k=kind: open_dialog(game, "equipment", equipment=k), small=True)
        equipment_sprite(game.screen, kind, pygame.Rect(rect.x, rect.y + 1, rect.w, 59))
        locked = not manufacturing.equipment_unlocked(game.village, kind)
        catalogue_label(game, rect, EQUIPMENT_LABELS[kind], "Blueprint" if locked else f"{manufacturing.equipment_price(game.village, kind)}c", locked=locked)
        if locked:
            pygame.draw.rect(game.screen, COPPER, (rect.right - 22, rect.y + 10, 13, 12), border_radius=2)
            pygame.draw.arc(game.screen, COPPER, (rect.right - 20, rect.y + 3, 9, 13), 0, math.pi, 2)


def draw_supplies(game, state):
    fit_text(game.screen, game.tiny, "Materials & finished goods", 817, 201, 391, MUTED)
    for i, good in enumerate(manufacturing.SUPPLIES):
        rect = icon_rect(i)
        game.button(rect, "", lambda g=good: open_dialog(game, "supply", good=g), small=True)
        item_sprite(game.screen, good, pygame.Rect(rect.x, rect.y, rect.w, 60))
        listing = manufacturing.SUPPLIES[good]
        catalogue_label(game, rect, listing['name'], f"{game.village.material_inventory.get(good, 0)} held / {listing['price']}c")
    for i, product in enumerate(manufacturing.PRODUCTS, len(manufacturing.SUPPLIES)):
        rect = icon_rect(i)
        game.button(rect, "", lambda g=product: open_dialog(game, "product", good=g), small=True)
        item_sprite(game.screen, product, pygame.Rect(rect.x, rect.y, rect.w, 60))
        title = {'precision_gears': 'Fine gears'}.get(product, manufacturing.PRODUCTS[product]['name'])
        catalogue_label(game, rect, title, f"{state['goods'].get(product, 0)} ready")


def draw_orders(game, state):
    fit_text(game.screen, game.heading, "CUSTOMERS", 812, 211, 396, TEAL)
    fit_text(game.screen, game.small, f"Finished goods: {sum(state['goods'].values())}", 812, 249, 390)
    offers = manufacturing.offers(game.village)
    pages = max(1, (len(offers) + 2) // 3)
    game.factory_order_page = max(0, min(game.factory_order_page, pages - 1))
    first = game.factory_order_page * 3
    for i, offer in enumerate(offers[first:first + 3]):
        y = 288 + i * 108
        pygame.draw.line(game.screen, (217, 201, 167), (812, y - 9), (1205, y - 9))
        fit_text(game.screen, game.small, offer["name"], 812, y, 390)
        wrapped_text(game.screen, game.tiny, offer["reason"], 812, y + 25, 390, MUTED, line_height=18, max_lines=2)
        game.button((812, y + 66, 393, 32), f"SELL ONE / {offer['price']}c / needs {offer['demand']}",
                    lambda key=offer["id"]: notify(game, manufacturing.sell_goods(game.village, key)),
                    enabled=offer["demand"] > 0 and state["goods"].get(offer.get("product", "repair_kits"), 0) > 0, small=True)
    if pages > 1:
        game.button((812, 616, 103, 31), "PREVIOUS",
                    lambda: setattr(game, "factory_order_page", max(0, game.factory_order_page - 1)),
                    enabled=game.factory_order_page > 0, small=True)
        fit_text(game.screen, game.tiny, f"Page {game.factory_order_page + 1} / {pages}", 937, 625, 142, MUTED)
        game.button((1102, 616, 103, 31), "NEXT",
                    lambda: setattr(game, "factory_order_page", min(pages - 1, game.factory_order_page + 1)),
                    enabled=game.factory_order_page < pages - 1, small=True)


def _name(item):
    return f"{manufacturing.CATALOG[item['kind']]['name']} #{item['id']}"


def draw_machine(game, state):
    item = selected(game)
    if item is None:
        fit_text(game.screen, game.heading, "WORKSHOP", 812, 211, 396, TEAL)
        for i, (label, value) in enumerate((("Machines", len(state['equipment'])),
                                           ("Goods ready", sum(state['goods'].values())),
                                           ("Made", state.get('produced', 0)), ("Sold", state.get('sold', 0)))):
            x, y = 812 + (i % 2) * 204, 256 + (i // 2) * 86
            pygame.draw.rect(game.screen, (233, 223, 196), (x, y, 189, 72), border_radius=4)
            fit_text(game.screen, game.tiny, label, x + 12, y + 10, 165, MUTED)
            fit_text(game.screen, game.heading, str(value), x + 12, y + 32, 165, TEAL)
        if not state['equipment']:
            wrapped_text(game.screen, game.small, "A place for your first machine. Choose equipment, then place it on the floor.",
                         812, 449, 386, INK, line_height=24, max_lines=3)
            game.button((812, 543, 393, 38), "BROWSE EQUIPMENT", lambda: switch_page(game, 'equipment'), active=True, small=True)
        else:
            wrapped_text(game.screen, game.small, "Select equipment on the floor to inspect its work or adjust its controller.",
                         812, 449, 386, MUTED, line_height=24, max_lines=3)
        if 'steam_accumulator' in state['unlocks']:
            fit_text(game.screen, game.tiny, "Tower accumulator installed", 812, 609, 390, TEAL)
            fit_text(game.screen, game.tiny, "New batches take 20% less time", 812, 632, 390, MUTED)
        return
    fit_text(game.screen, game.heading, manufacturing.CATALOG[item["kind"]]["name"].upper(), 812, 211, 396, TEAL)
    fit_text(game.screen, game.tiny, f"#{item['id']} / floor {item['pos'][0] + 1}, {item['pos'][1] + 1}", 812, 251, 390, MUTED)
    game.button((812, 292, 122, 33), "DETAILS", lambda: open_dialog(game, "inspect", item_id=item["id"]), small=True)
    game.button((947, 292, 122, 33), "MOVE", lambda: move(game, item), small=True)
    game.button((1082, 292, 122, 33), "SELL", lambda: open_dialog(game, "sell", item_id=item["id"]), small=True)
    if item["kind"] in manufacturing.CONTROLLABLE:
        pygame.draw.rect(game.screen, (231, 224, 196), (806, 383, 405, 44), border_radius=3)
        for i, port in enumerate(("A", "B")):
            fit_text(game.screen, game.tiny, input_summary(game, item, port), 812, 344 + i * 23, 392, MUTED)
        fit_text(game.screen, game.tiny, item.get("status", "Ready"), 812, 391, 392, TEAL)
        if item.get("busy", 0) > 0:
            fit_text(game.screen, game.tiny, f"{item['busy']:.1f}s remaining", 812, 413, 390, TEAL)
        else:
            fit_text(game.screen, game.tiny, f"{item.get('mode', 'manual').title()} / OUT {item.get('signal', 0)}", 812, 413, 390, TEAL)
        action = (lambda: manufacturing.start_batch(game.village, item["id"])) if item["kind"] in manufacturing.PRODUCTION else (lambda: manufacturing.trade_once(game.village, item["id"]))
        game.button((812, 434, 189, 36), "START BATCH" if item["kind"] in manufacturing.PRODUCTION else "TRADE ONCE", lambda: notify(game, action()), small=True)
        game.button((1016, 434, 189, 36), "MANUAL" if item.get("mode") == "auto" else "ENABLE AUTO",
                    lambda: notify(game, manufacturing.set_mode(game.village, item["id"], item.get("mode") != "auto")), small=True)
        game.button((812, 482, 393, 36), "EDIT CONTROLLER", lambda: game.edit_factory_controller(item["id"]), active=True, small=True)
        game.button((812, 530, 393, 36), "WIRE INPUTS", lambda: open_route(game, unit_id=item["id"]), small=True)
        game.button((812, 578, 393, 36), "SETTINGS", lambda: open_dialog(game, "settings", item_id=item["id"]), small=True)
    elif item["kind"] == "storage":
        values = manufacturing.storage_values(game.village, item["id"])
        for i, key in enumerate(("metal", "fittings", "fuel", "stock", "free_space")):
            fit_text(game.screen, game.small, f"{key.replace('_', ' ').title()}: {values.get(key, 0)}", 812, 354 + i * 33, 390)
        game.button((812, 553, 393, 38), "CONNECT OUTPUT", lambda: open_route(game, storage_id=item["id"]), small=True)
    elif item["kind"] == "display":
        reading = manufacturing.display_reading(game.village, item["id"])
        fit_text(game.screen, game.small, reading.get("label", "Readout"), 812, 360, 390, MUTED)
        fit_text(game.screen, game.big, str(reading["value"]), 812, 405, 390, TEAL)
        game.button((812, 498, 393, 38), "CONFIGURE DISPLAY", lambda: open_dialog(game, "settings", item_id=item["id"]), small=True)
    elif item["kind"] == "controller":
        linked = manufacturing.get_machine(game.village, item.get("machine_id"))
        fit_text(game.screen, game.small, _name(linked) if linked else "Unassigned", 812, 360, 390, MUTED)
        if linked:
            game.button((812, 425, 393, 38), "EDIT DESIGN", lambda: game.edit_factory_controller(linked["id"]), small=True)
            game.button((812, 473, 393, 38), "WIRE INPUTS", lambda: open_route(game, unit_id=linked["id"]), small=True)


DESCRIPTIONS = {
    "bench": "Assembles one repair kit from one metal, one fitting and one fuel.",
    "press": "Shapes metal into plates for bridge work and precision components.",
    "lathe": "Turns fittings and metal into steam valves for pumps and advanced machinery.",
    "precision_machine": "An old precision cutter. Combines your plates and valves into fine instrument gears. Blueprint recovered outside the village.",
    "storage": "Stores workshop materials and finished goods; exposes their quantities to connected controllers.",
    "controller": "Runs your circuit design and connects its output to one workshop unit.",
    "display": "Displays a selected stock, cash, production or controller reading.",
    "buyer": "Purchases a selected material when your controller requests it, subject to spending limits.",
    "seller": "Delivers your selected product when your controller requests a sale, subject to customer demand and your limits.",
}


def _dialog_button(game, rect, label, action, **kwargs):
    start = len(game.buttons)
    game.button(rect, label, action, small=True, **kwargs)
    game.factory_dialog_buttons.extend(game.buttons[start:])


def recipe_text(recipe):
    names = {"metal_plates": "plate", "steam_valves": "valve", "precision_gears": "gear", "repair_kits": "kit", "fittings": "fitting"}
    return " + ".join(f"{count} {names.get(good, good)}" for good, count in recipe.items())


def _row(game, label, value, y):
    fit_text(game.screen, game.small, label, 350, y, 235, MUTED)
    fit_text(game.screen, game.small, value, 603, y, 325, INK)


def draw_dialog(game):
    shade = pygame.Surface(game.screen.get_size(), pygame.SRCALPHA)
    shade.fill((20, 29, 29, 185))
    game.screen.blit(shade, (0, 0))
    draw_panel(game.screen, (310, 125, 660, 550))
    game.buttons.clear()
    game.factory_dialog_buttons = []
    dialog = game.factory_dialog
    item = manufacturing.get_machine(game.village, dialog.get("item_id"))
    kind = dialog["kind"]
    if kind in ("equipment", "inspect"):
        equipment = dialog["equipment"] if kind == "equipment" else item["kind"] if item else None
        if equipment is None:
            close_dialog(game)
            return
        title = manufacturing.CATALOG[equipment]["name"]
        fit_text(game.screen, game.heading, title, 350, 158, 575, TEAL)
        equipment_sprite(game.screen, equipment, pygame.Rect(350, 200, 90, 82))
        wrapped_text(game.screen, game.small, DESCRIPTIONS[equipment], 466, 209, 455, INK, line_height=24, max_lines=3)
        if kind == "equipment":
            _row(game, "Purchase", f"{manufacturing.equipment_price(game.village, equipment)}c", 320)
            seller = game.village.businesses[manufacturing.CATALOG[equipment]["seller"]]
            _row(game, "Seller", seller["name"], 360)
        else:
            _row(game, "Equipment", f"#{item['id']}", 320)
            _row(game, "State", item.get("status", "Installed"), 360)
        rate = {"bench": f"1 kit / {manufacturing.BATCH_SECONDS:g} seconds", "storage": "+6 finished-goods capacity",
                "controller": "1 circuit tick / 0.5 seconds", "display": "Live selected signal",
                "buyer": f"1 purchase / {manufacturing.TRADE_SECONDS:g} seconds", "seller": f"1 sale / {manufacturing.TRADE_SECONDS:g} seconds"}.get(equipment, "")
        if equipment in manufacturing.PRODUCTION:
            product = next(key for key, data in manufacturing.PRODUCTS.items() if data["machine"] == equipment)
            rate = f"1 batch / {manufacturing.production_seconds(game.village, product):g} seconds"
        _row(game, "Rate / capacity", rate, 400)
        if equipment in manufacturing.PRODUCTION:
            data = manufacturing.PRODUCTS[product]
            _row(game, "Inputs", recipe_text(data["recipe"]), 440)
            _row(game, "Sale value", f"{data['price']}c per funded order", 480)
        if not manufacturing.equipment_unlocked(game.village, equipment):
            _row(game, "Blueprint", "Recover beyond the village", 520)
        if kind == "equipment":
            _dialog_button(game, (670, 608, 255, 38), "PLACE", lambda: place_from_dialog(game, equipment), active=True, enabled=manufacturing.equipment_unlocked(game.village, equipment))
    elif kind in ("supply", "product"):
        good = dialog.get("good", "repair_kits")
        title = manufacturing.SUPPLIES[good]["name"] if good in manufacturing.SUPPLIES else manufacturing.PRODUCTS[good]["name"]
        fit_text(game.screen, game.heading, title, 350, 158, 575, TEAL)
        item_sprite(game.screen, good, pygame.Rect(350, 210, 110, 90))
        if kind == "supply":
            listing = manufacturing.SUPPLIES[good]
            seller = game.village.businesses[listing["seller"]]
            _row(game, "Unit price", f"{listing['price']}c", 330)
            _row(game, "Seller", seller["name"], 370)
            _row(game, "Available", str(seller["stock"].get(good, 0)), 410)
            _row(game, "In workshop", str(game.village.material_inventory.get(good, 0)), 450)
            _dialog_button(game, (670, 608, 255, 38), "BUY ONE", lambda: notify(game, manufacturing.buy_supply(game.village, good)), active=True)
        else:
            data = manufacturing.PRODUCTS[good]
            _row(game, "In workshop", str(manufacturing.state(game.village)["goods"].get(good, 0)), 330)
            _row(game, "Recipe", recipe_text(data["recipe"]), 370)
            _row(game, "Production time", f"{manufacturing.production_seconds(game.village, good):g} seconds", 410)
            _row(game, "Sale price", f"{data['price']}c per funded order", 450)
            _row(game, "Machine", manufacturing.CATALOG[data["machine"]]["name"], 490)
    elif kind == "sell":
        draw_sale(game, item)
    elif kind == "settings":
        draw_settings(game, item)
    elif kind == "route":
        draw_route(game)
    _dialog_button(game, (350, 608, 190, 38), "CLOSE [ESC]", lambda: close_dialog(game))
    if game.factory_message:
        fit_text(game.screen, game.tiny, game.factory_message, 350, 570, 575, COPPER)


def draw_sale(game, item):
    if item is None:
        close_dialog(game)
        return
    quote = manufacturing.equipment_sell_quote(game.village, item["id"])
    game.factory_dialog["quote"] = quote["price"]
    fit_text(game.screen, game.heading, "Sell equipment?", 350, 158, 575, TEAL)
    equipment_sprite(game.screen, item["kind"], pygame.Rect(350, 210, 110, 90))
    _row(game, "Item", _name(item), 330)
    _row(game, "Proceeds", f"{quote['price']}c", 375)
    wrapped_text(game.screen, game.small, quote.get("reason", ""), 350, 427, 575, INK, line_height=24, max_lines=4)
    _dialog_button(game, (670, 608, 255, 38), "CONFIRM SALE", lambda: confirm_sale(game, item["id"]), enabled=quote["allowed"], danger=True)


def confirm_sale(game, item_id):
    quote = manufacturing.equipment_sell_quote(game.village, item_id)
    if quote["price"] != game.factory_dialog.get("quote"):
        game.factory_message = "The quote changed. Review the new proceeds before confirming."
        return
    if notify(game, manufacturing.sell_equipment(game.village, item_id)):
        game.factory_selected = None
        close_dialog(game)


def _choices(values, current, delta):
    values = list(values)
    if not values:
        return None
    index = values.index(current) if current in values else 0
    return values[(index + delta) % len(values)]


def _adjuster(game, label, value, y, previous, next_value):
    fit_text(game.screen, game.small, label, 350, y + 8, 240, MUTED)
    _dialog_button(game, (594, y, 37, 32), "<", previous)
    fit_text(game.screen, game.small, str(value), 650, y + 8, 227, INK)
    _dialog_button(game, (888, y, 37, 32), ">", next_value)


def configure(game, item, key, value):
    notify(game, manufacturing.configure_trader(game.village, item["id"], **{key: value}))


def draw_settings(game, item):
    if item is None:
        close_dialog(game)
        return
    fit_text(game.screen, game.heading, "Settings / " + manufacturing.CATALOG[item["kind"]]["name"], 350, 158, 575, TEAL)
    config = item.get("config", {})
    if item["kind"] in ("buyer", "seller"):
        fields = (("good", "Material", "metal", list(manufacturing.SUPPLIES)), ("target", "Target signal", 2, None),
                  ("reserve", "Cash reserve", 8, None), ("daily_budget", "Daily budget", 24, None), ("max_price", "Maximum unit price", 3, None)) if item["kind"] == "buyer" else (
                  ("buyer", "Customer", "any", ["any"] + [offer["id"] for offer in manufacturing.offers(game.village)]),
                  ("product", "Product", "repair_kits", list(manufacturing.PRODUCTS)),
                  ("keep_stock", "Keep goods", 0, None), ("min_price", "Minimum price", 10, None))
        for i, (key, label, default, choices) in enumerate(fields):
            value = config.get(key, default)
            change = lambda delta, k=key, v=value, options=choices: configure(game, item, k, _choices(options, v, delta) if options else max(0, int(v) + delta))
            _adjuster(game, label, value, 235 + i * 58, lambda fn=change: fn(-1), lambda fn=change: fn(1))
    elif item["kind"] == "display":
        reading = manufacturing.display_reading(game.village, item["id"])
        sources = list(manufacturing.DISPLAY_SOURCES)
        source, unit = reading["source"], reading.get("machine_id")
        units = [e["id"] for e in manufacturing.state(game.village)["equipment"] if e["kind"] in manufacturing.CONTROLLABLE]
        def change_source(delta):
            new = _choices(sources, source, delta)
            linked = unit or (units[0] if units else None)
            notify(game, manufacturing.configure_display(game.village, item["id"], new, linked if new == "signal" else None))
        _adjuster(game, "Reading", source, 260, lambda: change_source(-1), lambda: change_source(1))
        if source == "signal":
            def change_unit(delta):
                notify(game, manufacturing.configure_display(game.village, item["id"], source, _choices(units, unit, delta)))
            _adjuster(game, "Linked unit", f"#{unit}" if unit else "None", 330, lambda: change_unit(-1), lambda: change_unit(1))
        _row(game, "Value", str(reading["value"]), 425)
    else:
        target = manufacturing.state(game.village)["target"]
        _adjuster(game, "Stock target", target, 260,
                  lambda: notify(game, manufacturing.set_target(game.village, max(0, target - 1))),
                  lambda: notify(game, manufacturing.set_target(game.village, target + 1)))
    if item["kind"] in manufacturing.CONTROLLABLE:
        _dialog_button(game, (570, 532, 355, 32), "RESET CONTROLLER MEMORY", lambda: notify(game, manufacturing.reset_controller(game.village, item["id"])))


def open_route(game, unit_id=None, storage_id=None):
    import factory_controller
    units = [e for e in manufacturing.state(game.village)["equipment"] if e["kind"] in manufacturing.CONTROLLABLE]
    unit = manufacturing.get_machine(game.village, unit_id) if unit_id else next(iter(units), None)
    controller = factory_controller.wiring(game.village, unit["id"]) if unit else {}
    source = storage_id if storage_id is not None else controller.get("sources", {}).get("A")
    sensor = "metal" if storage_id is not None else controller.get("inputs", {}).get("A", "ready")
    open_dialog(game, "route", unit_id=unit["id"] if unit else None, storage_id=source, fixed_storage=storage_id, port="A", sensor=sensor)


def route_change(game, field, values, delta):
    dialog = game.factory_dialog
    dialog[field] = _choices(values, dialog.get(field), delta)
    if field == "storage_id":
        dialog["sensor"] = "metal" if dialog[field] is not None else "ready"


def draw_route(game):
    dialog = game.factory_dialog
    state = manufacturing.state(game.village)
    units = [e["id"] for e in state["equipment"] if e["kind"] in manufacturing.CONTROLLABLE]
    racks = [None] + [e["id"] for e in state["equipment"] if e["kind"] == "storage"]
    unit = manufacturing.get_machine(game.village, dialog.get("unit_id"))
    fit_text(game.screen, game.heading, "Wire a sensor to your board", 350, 158, 575, TEAL)
    sources = manufacturing.STORAGE_SENSORS if dialog.get("storage_id") is not None else list(manufacturing.SENSOR_NAMES)
    fields = (("storage_id", "From", "Machine sensors" if dialog.get("storage_id") is None else f"Storage rack #{dialog['storage_id']}", racks),
              ("sensor", "Reading", manufacturing.SENSOR_NAMES.get(dialog["sensor"], dialog["sensor"]), sources),
              ("unit_id", "To machine", _name(unit) if unit else "None", units),
              ("port", "Board input", dialog["port"], ("A", "B")))
    for i, (key, label, value, choices) in enumerate(fields):
        _adjuster(game, label, value, 235 + i * 65,
                  lambda k=key, c=choices: route_change(game, k, c, -1),
                  lambda k=key, c=choices: route_change(game, k, c, 1))
    ready = unit is not None
    if unit and ready:
        values = (manufacturing.storage_values(game.village, dialog["storage_id"]) if dialog.get("storage_id") is not None
                  else manufacturing.sensor_values(game.village, unit["id"]))
        pygame.draw.rect(game.screen, CREAM, (350, 506, 575, 42), border_radius=4)
        reading = manufacturing.SENSOR_NAMES.get(dialog["sensor"], dialog["sensor"])
        fit_text(game.screen, game.small, f"{reading}: {values.get(dialog['sensor'], 0)}  ->  {dialog['port']}", 366, 518, 543, TEAL)
    else:
        fit_text(game.screen, game.small, "Place a production or trading unit first.", 350, 518, 575, MUTED)
    def connect():
        import factory_controller
        notify(game, factory_controller.configure_input(game.village, dialog.get("unit_id"), dialog["port"],
                                                    dialog.get("storage_id"), dialog["sensor"]))
    _dialog_button(game, (670, 608, 255, 38), "CONNECT", connect, active=True, enabled=ready)


