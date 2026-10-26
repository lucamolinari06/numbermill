"""Shared full-screen village ledger; each section has room to grow."""

import pygame
from town import LOCATIONS, WORLD_W, WORLD_H, LABELS, HOME_STREET_Y
import town_ground
from ui_theme import INK, MUTED, PAPER, TEAL, COPPER, GOLD, draw_panel, backdrop, fit_text, wrapped_text
from office_ui import frame, navigation_rail


TABS = ("Overview", "Map", "People", "Businesses", "Trade", "Inventors", "Workshop")
RED = (171, 75, 67)


def card(screen, rect):
    draw_panel(screen, rect)
    # Text defaults to the innermost card containing its anchor.
    _cards.append(pygame.Rect(rect))


_cards = []


def map_label_layout(font, bounds, entries):
    """Place complete map captions above/below markers without collisions."""
    markers = [pygame.Rect(x - 9, y - 9, 18, 18) for _, (x, y), _ in entries]
    placed = []
    for key, (x, y), lines in entries:
        width = max(font.render(line, True, INK).get_width() for line in lines)
        height = len(lines) * 17
        for offset in (-height - 13, 13, -height - 36, 36, -height - 59, 59):
            rect = pygame.Rect(x - width // 2, y + offset, width, height)
            rect.clamp_ip(bounds.inflate(-12, -12))
            if not any(rect.inflate(10, 6).colliderect(other) for other in markers + [p[1] for p in placed]):
                break
        placed.append((key, rect, lines))
    return placed


def label(game, value, x, y, color=INK, font=None, width=None):
    if width is None:
        parent = next((rect for rect in reversed(_cards) if rect.collidepoint(x, y)), game.screen.get_rect())
        width = parent.right - x - 18
    return fit_text(game.screen, font or game.small, value, x, y, width, color)


def plot(game, rect, values, title, color=TEAL):
    card(game.screen, rect)
    x, y, w, h = rect
    label(game, title, x + 18, y + 14, font=game.font, width=w - 155)
    if not values:
        label(game, "No daily history yet", x + 18, y + 78, MUTED)
        return
    low, high = min(values), max(values)
    span = max(1, high - low)
    for fraction in (0, 0.5, 1):
        gy = y + h - 34 - int(fraction * (h - 104))
        pygame.draw.line(game.screen, (231, 216, 180), (x + 24, gy), (x + w - 24, gy))
    points = []
    for i, value in enumerate(values):
        px = x + 24 + int(i * (w - 48) / max(1, len(values) - 1))
        py = y + h - 34 - int((value - low) * (h - 104) / span)
        points.append((px, py))
    pygame.draw.line(game.screen, (187, 170, 135), (x + 24, y + h - 33), (x + w - 24, y + h - 33), 2)
    if len(points) > 1:
        wash = pygame.Surface((w, h), pygame.SRCALPHA)
        polygon = [(px - x, py - y) for px, py in points]
        polygon += [(points[-1][0] - x, h - 34), (points[0][0] - x, h - 34)]
        pygame.draw.polygon(wash, (*color, 24), polygon)
        game.screen.blit(wash, (x, y))
        pygame.draw.lines(game.screen, color, False, points, 3)
    for point in points[-1:]:
        pygame.draw.circle(game.screen, color, point, 5)
    label(game, str(values[-1]), x + w - 123, y + 12, color, game.heading, width=104)
    label(game, "LATEST", x + w - 123, y + 44, MUTED, game.tiny, width=104)
    days = "day" if len(values) == 1 else "days"
    label(game, f"low {low}  high {high}  /  last {len(values)} {days}", x + 18, y + h - 25, MUTED, game.tiny)


def draw(game):
    from daily_life import state, progress, SHIFT_SECONDS
    screen, village = game.screen, game.village
    life = state(village)
    _cards.clear()
    frame(screen, "TOWN LEDGER", game.big)
    label(game, f"DAY {village.day}  /  {village.coins}c  /  {len(village.citizens)} residents", 855, 53, PAPER, width=356)
    game.button((1094, 91, 132, 35), "BACK [ESC]", game.close_ledger, small=True)
    for index, tab in enumerate(TABS):
        game.button((55 + index * 145, 94, 136, 37), tab.upper(),
                    lambda chosen=tab: game.select_ledger_tab(chosen),
                    active=game.ledger_tab == tab, small=True)
    label(game, game.ledger_tab, 62, 159, PAPER, game.heading)
    label(game, f"Day {village.day}: {round(progress(village) * 100)}% complete", 690, 160, PAPER, game.tiny)
    game.button((995, 151, 224, 33), "NEXT DAY [N]", game.next_day, small=True)
    if game.ledger_tab == "Overview":
        plot(game, (58, 200, 365, 198), [h["population"] for h in village.history], "Population")
        plot(game, (456, 200, 365, 198), [h["bread_price"] for h in village.history], "Bread price", COPPER)
        plot(game, (854, 200, 365, 198), [h["missed_meals"] for h in village.history], "Missed meals", RED)
        card(screen, (58, 423, 562, 270))
        label(game, "WHY THINGS CHANGED", 77, 444, TEAL, game.font)
        label(game, village.market_note, 77, 485)
        events = village.last_day_report.get("causes", []) or village.journal
        for i, event in enumerate(events[:3]):
            label(game, event, 77, 518 + i * 27, MUTED, game.tiny)
        label(game, "VILLAGE GROWTH", 77, 607, TEAL, game.tiny)
        wrapped_text(screen, game.tiny, getattr(village, "migration_status", "Households watch food, savings and local jobs."),
                     77, 631, 522, MUTED, line_height=19, max_lines=2)
        card(screen, (645, 423, 574, 270))
        label(game, "NEXT DECISIONS", 663, 444, TEAL, game.font)
        open_jobs = [key for key, offer in village.offers.items() if offer["status"] in ("open", "bid")]
        lines = [
            f"Open commissions: {len(open_jobs)}",
            f"Workshop service: {'open' if village.service_active else 'paused'}",
            f"Fuel: {village.businesses['fuel_yard']['stock'].get('fuel', 0)}   Parts: {village.businesses['parts_shop']['stock'].get('parts', 0)}",
        ]
        for i, line in enumerate(lines):
            wrapped_text(screen, game.small, line, 663, 484 + i * 34, 536, INK, line_height=20, max_lines=1)
        label(game, "NEW BUSINESSES", 663, 601, TEAL, game.tiny)
        wrapped_text(screen, game.tiny, village.competition_status, 663, 627, 536, MUTED,
                     line_height=19, max_lines=3)
    elif game.ledger_tab == "Map":
        card(screen, (58, 200, 810, 493))
        card(screen, (891, 200, 328, 493))
        label(game, "COPPERSIDE  /  BOOLE IS THE GOLD DOT", 77, 216, TEAL, game.font)
        left, top, width, height = 92, 253, 740, 411
        pygame.draw.rect(screen, (178, 193, 150), (left, top, width, height), border_radius=4)
        sx, sy = width / WORLD_W, height / WORLD_H
        def point(x, y):
            return int(left + x * sx), int(top + y * sy)
        # Cartographic landmarks follow the same world coordinates as the town.
        import town_water
        old_clip = screen.get_clip()
        screen.set_clip(old_clip.clip(pygame.Rect(left, top, width, height)))
        river = [point(x, y) for x, y in town_water.polygon(WORLD_W, WORLD_H)]
        pygame.draw.polygon(screen, (104, 150, 146), river)
        pygame.draw.lines(screen, (218, 220, 173), True, river, 2)
        bridge_left, bridge_top = point(1060, WORLD_H - 102)
        bridge_right, bridge_bottom = point(1187, WORLD_H - 9)
        pygame.draw.rect(screen, (158, 116, 70), (bridge_left, bridge_top, bridge_right - bridge_left, bridge_bottom - bridge_top))
        for xx in (bridge_left, bridge_right):
            pygame.draw.line(screen, (101, 79, 52), (xx, bridge_top), (xx, bridge_bottom), 2)
        screen.set_clip(old_clip)
        town_ground.draw_map(screen, point, (205, 194, 156))
        captions = []
        short = {'fuel_yard': ("Mely's", 'Fuel Yard'), 'parts_shop': ("Luca's", 'Repair Shop'),
                 'grace_shop': ("Grace's", 'Workshop'), 'east_bakery': ("Jun's", 'Bakery'),
                 'home_1': ('Ada & Bram', 'Home'), 'home_2': ('Agnes & Dara', 'Home'),
                 'home_3': ('Mely & Luca', 'Home'), 'home_4': ("Rowan's", 'Cottage')}
        for key, (x, y) in LOCATIONS.items():
            if key == 'east_bakery' and key not in village.businesses:
                px, py = point(x, y)
                pygame.draw.rect(screen, COPPER, (px - 6, py - 6, 12, 12), 1)
                continue
            if key.startswith("home_") and key not in village.households:
                px, py = point(x, y)
                pygame.draw.rect(screen, COPPER, (px - 6, py - 6, 12, 12), 1)
                continue
            px, py = point(x, y)
            color = COPPER if key in ("fuel_yard", "parts_shop", "grace_shop") else TEAL
            pygame.draw.circle(screen, color, (px, py), 7)
            if key == 'east_bakery' or key.startswith('home_') and key not in ('home_1', 'home_2', 'home_3'):
                from town import location_label
                caption = location_label(village, key)
                if caption:
                    captions.append((key, (px, py), tuple(caption.split(' ', 1))))
            else:
                captions.append((key, (px, py), short.get(key, (LABELS[key],))))
        for _, rect, lines in map_label_layout(game.tiny, pygame.Rect(left, top, width, height), captions):
            pygame.draw.rect(screen, (226, 229, 195), rect.inflate(6, 4), border_radius=2)
            for i, line in enumerate(lines):
                text = game.tiny.render(line, True, INK)
                screen.blit(text, text.get_rect(midtop=(rect.centerx, rect.y + i * 17)))
        pygame.draw.circle(screen, (230, 183, 71), point(game.town.player_x, game.town.player_y), 9)
        label(game, "NEIGHBORHOODS", 910, 218, TEAL, game.font)
        for i, line in enumerate((
            "North: fuel, repairs, Grace",
            "Center: mill, workshop, bakery",
            "South: farm, market, homes",
            "East: timber, metal, fittings",
        )):
            label(game, line, 910, 268 + i * 46, INK if i < 3 else MUTED, game.tiny)
        pygame.draw.line(screen, (218, 201, 166), (910, 463), (1197, 463))
        label(game, "MAP KEY", 910, 488, TEAL, game.font)
        for i, (color, caption) in enumerate(((GOLD, 'Boole'), (TEAL, 'Local businesses & homes'),
                                             (COPPER, 'Northern workshops'))):
            pygame.draw.circle(screen, color, (918, 534 + i * 32), 5)
            label(game, caption, 934, 526 + i * 32, MUTED, game.tiny)
    elif game.ledger_tab == "People":
        plot(game, (58, 200, 475, 213), [h["population"] for h in village.history], "Population")
        card(screen, (552, 200, 667, 213))
        label(game, "A PLACE TO CALL HOME", 574, 219, TEAL, game.font)
        wrapped_text(screen, game.small, getattr(village, "migration_status", "Households watch food, savings and local jobs."),
                     574, 258, 622, INK, line_height=23, max_lines=3)
        events = getattr(village, "migration_events", [])
        note = (f"Day {events[-1]['day']}: {events[-1]['message']}" if events else
                "Three stable days start a cottage; construction takes two further days. One new household can settle.")
        wrapped_text(screen, game.tiny, note, 574, 339, 622, MUTED, line_height=21, max_lines=3)
        card(screen, (58, 434, 525, 260))
        label(game, "RESIDENTS  /  CURRENT CHOICES", 78, 452, TEAL, game.font)
        people = sorted(village.citizens, key=lambda person:
                        (person["name"] not in ("Mely", "Luca"), person["name"]))
        index = game.ledger_index % len(people)
        start = (index // 7) * 7
        for i, person in enumerate(people[start:start + 7]):
            color = COPPER if start + i == index else INK
            if start + i == index:
                pygame.draw.rect(screen, (234, 222, 185), (72, 485 + i * 27, 499, 26), border_radius=4)
            label(game, person['name'], 80, 490 + i * 27, color, game.tiny, width=100)
            label(game, person['activity'], 184, 490 + i * 27, color, game.tiny, width=380)
        selected = people[game.ledger_index % len(people)]
        home = village.households[selected["home"]]
        card(screen, (603, 434, 616, 260))
        from dialogue import portrait
        portrait(screen, selected['name'], (624, 438, 44, 44))
        label(game, selected["name"], 682, 452, TEAL, game.heading)
        label(game, f"Mood {selected['mood']}   Energy {selected['energy']}   Hunger {selected['hunger']}", 624, 489)
        workplace = village.businesses.get(selected['workplace'], {}).get('name', selected['workplace'].replace('_', ' ').title())
        label(game, f"Home savings {home['cash']}c   Work: {workplace}", 624, 521)
        label(game, selected["last_reason"][:68], 624, 553, COPPER)
        worked = life["worked"].get(selected["name"], 0.0)
        paid = life["paid"].get(selected["name"], 0)
        label(game, f"Shift {round(worked / SHIFT_SECONDS * 100)}% / paid {paid}c / household bread {home['bought']}/{home['bread_need']}", 624, 579, TEAL, game.tiny)
        label(game, selected["aspiration"][:67], 624, 602, INK, game.tiny)
        relation = selected["relationships"].get("Luca" if selected["name"] == "Mely" else "Mely", None)
        trust = selected["relationships"].get("Boole", 20)
        if relation is not None:
            label(game, f"Spouse bond: {relation}/100   Trust in you: {trust}/100", 624, 626, MUTED, game.tiny)
        else:
            label(game, f"Trust in you: {trust}/100", 624, 626, MUTED, game.tiny)
        label(game, (selected["memories"][-1] if selected["memories"] else "No recent memory")[:75],
              624, 651, MUTED, game.tiny)
    elif game.ledger_tab == "Businesses":
        keys = list(village.businesses)
        selected = keys[game.ledger_index % len(keys)]
        firm = village.businesses[selected]
        card(screen, (58, 199, 440, 495))
        label(game, "FIRMS  /  UP DOWN TO SELECT", 77, 216, TEAL, game.font)
        start = (keys.index(selected) // 10) * 10
        for i, key in enumerate(keys[start:start + 10]):
            current = village.businesses[key]
            color = COPPER if key == selected else INK
            if key == selected:
                pygame.draw.rect(screen, (234, 222, 185), (71, 254 + i * 32, 413, 29), border_radius=4)
            label(game, current['name'], 77, 259 + i * 32, color, game.tiny, width=310)
            label(game, f"{current['cash']}c", 404, 259 + i * 32, color, game.tiny, width=73)
        label(game, f"Firms {start + 1}-{min(start + 10, len(keys))} of {len(keys)}", 77, 583, MUTED, game.tiny)
        wrapped_text(screen, game.tiny, village.competition_status, 77, 612, 399, MUTED,
                     line_height=19, max_lines=3)
        card(screen, (520, 199, 699, 495))
        label(game, firm["name"], 542, 220, TEAL, game.heading)
        staff = "Owner-operated" if firm.get('owner_operated') else f"{firm['workers']} worker slots"
        lines = [
            f"Owner: {firm['owner']} / {staff} / Capacity {village.capacity(selected)}/day",
            f"Stock: {', '.join(f'{good} {count}' for good, count in firm['stock'].items()) or 'none'}",
            f"Machines: {', '.join(firm['machines']) or 'none'}",
            (f"Wholesale bread: {firm.get('wholesale_price', 7)}c / Independent owner"
             if firm['kind'] == 'bakery' else f"Parent firm: {firm.get('parent_id') or 'independent'}"),
        ]
        for i, line in enumerate(lines):
            label(game, line, 542, 276 + i * 33)
        made = life["produced"].get(selected, 0)
        label(game, f"Today: {made} produced / {life['reasons'].get(selected, 'Waiting for the shift to begin')}"[:85], 542, 403, TEAL, game.tiny)
        chart_y = 430
        credit = firm.get('working_credit', {})
        if credit.get('owed', 0):
            lender = village.businesses.get(credit['lender'], {}).get('name', credit['lender'])
            wrapped_text(screen, game.tiny, f"Working credit: {credit['owed']}c owed to {lender}. Repays above 64c cash.",
                         542, 432, 650, MUTED, line_height=19, max_lines=2)
            chart_y = 480
        if selected == 'east_bakery':
            label(game, f"{firm.get('operating_state', 'open').upper()} / Owner reserve {firm.get('owner_reserve', 20)}c", 542, 432, COPPER, game.tiny)
            wrapped_text(screen, game.tiny, firm.get('owner_decision', 'The owner reviews demand, supplies and cash each evening.'),
                         542, 455, 650, MUTED, line_height=19, max_lines=2)
            chart_y = 505
        plot(game, (542, chart_y, 652, 665 - chart_y), [h["business_cash"][selected] for h in village.history if selected in h.get("business_cash", {})],
             "Cash history")
    elif game.ledger_tab == "Trade":
        plot(game, (58, 200, 550, 239), [h["bread"] for h in village.history], "Bread in village")
        plot(game, (628, 200, 591, 239), [h["bread_price"] for h in village.history], "Bread price", COPPER)
        card(screen, (58, 462, 570, 232))
        label(game, "LOCAL SUPPLY CHAINS", 78, 479, TEAL, game.font)
        for i, line in enumerate((
            "Farm > Mill > Bakeries > Market > Homes",
            "Mely > steam firms / Luca > Workshop > Customers",
            village.market_note,
        )):
            label(game, line[:57], 78, 524 + i * 47)
        card(screen, (648, 462, 571, 232))
        latest = village.trade_history[-1 - game.trade_day_offset]
        label(game, f"DAY {latest['day']} EXCHANGES", 667, 479, TEAL, game.font)
        game.button((987, 474, 100, 35), "OLDER", lambda: game.shift_trade_day(1), small=True,
                    enabled=game.trade_day_offset < len(village.trade_history) - 1)
        game.button((1093, 474, 105, 35), "NEWER", lambda: game.shift_trade_day(-1), small=True,
                    enabled=game.trade_day_offset > 0)
        entries = latest["entries"][-5:]
        for i, entry in enumerate(entries):
            seller = entry["from"].replace("Copperside ", "")[:16]
            buyer = entry.get("person", entry["to"]).replace("Copperside ", "")[:16]
            line = f"{seller} > {buyer}: {entry['units']} {entry['good']} / {entry['coins']}c"
            label(game, line[:69], 667, 518 + i * 31, INK, game.tiny)
        if not entries:
            label(game, "Residents trade during the day. N finishes the day.", 667, 526, MUTED)
    elif game.ledger_tab == "Inventors":
        from inventor_roster import roster, contracts
        inventors = roster(village)
        selected_index = game.ledger_index % len(inventors)
        identity, profile = inventors[selected_index]
        start = selected_index // 6 * 6
        card(screen, (58, 198, 365, 497))
        label(game, 'INVENTOR DIRECTORY', 78, 222, TEAL, game.font)
        label(game, 'Click a name / Up Down to browse', 78, 256, MUTED, game.tiny)
        for row, (key, item) in enumerate(inventors[start:start + 6]):
            game.button((78, 296 + row * 52, 325, 42), item['name'],
                        lambda index=start + row: setattr(game, 'ledger_index', index),
                        active=key == identity, small=True)
        label(game, f'{selected_index + 1} of {len(inventors)} inventors', 78, 646, MUTED, game.tiny)
        if len(inventors) > 6:
            game.button((78, 610, 155, 28), 'PREVIOUS',
                        lambda: setattr(game, 'ledger_index', max(0, start - 6)), small=True, enabled=start > 0)
            game.button((248, 610, 155, 28), 'NEXT',
                        lambda: setattr(game, 'ledger_index', min(len(inventors) - 1, start + 6)),
                        small=True, enabled=start + 6 < len(inventors))
        card(screen, (444, 198, 775, 497))
        label(game, profile['name'], 466, 222, TEAL, game.heading)
        label(game, profile.get('specialty', 'Independent inventor'), 466, 260, COPPER)
        wrapped_text(screen, game.small, profile.get('bio', 'A member of the local inventor community.'),
                     466, 292, 725, INK, line_height=22, max_lines=2)
        records = contracts(village, identity)
        active = [(key, offer) for key, offer in records if offer['status'] == 'bid']
        completed = sum(offer['status'] == 'rival' for _, offer in records)
        earned = village.rival_cash if identity == 'grace' else profile.get('earned', 0)
        label(game, f'Earned {earned}c / Delivered {completed} / Active bids {len(active)}', 466, 351, TEAL)
        label(game, profile.get('workshop', 'Workshop not yet listed'), 466, 382, MUTED)
        label(game, 'CONTRACT RECORD', 466, 425, TEAL, game.font)
        for row, (key, offer) in enumerate(records[:6]):
            status = (f"Building / due {offer['due_day']} / finishes {offer['finish_day']}"
                      if offer['status'] == 'bid' else 'Delivered / customer owns the installed copy')
            label(game, key.title(), 466, 462 + row * 32, INK, game.tiny, width=120)
            label(game, status, 596, 462 + row * 32, MUTED, game.tiny, width=595)
        if not records:
            label(game, 'No bids or deliveries yet. Available work is on the job board.', 466, 466, MUTED, game.tiny)
    else:
        card(screen, (58, 199, 560, 495))
        label(game, "YOUR WORKSHOP", 80, 222, TEAL, game.heading)
        import manufacturing
        factory = manufacturing.state(village)
        for i, line in enumerate((
            f"Equipment placed: {len(factory['equipment'])}",
            f"Goods made: {factory['produced']} / sold: {factory['sold']}",
            f"Manufacturing sales: {factory['earned']}c",
            f"Equipment and supplies: {factory['spent']}c",
            f"Side-service earnings: {village.service_earned}c net",
            "Optional service: 6c costs / 8c payment.",
        )):
            label(game, line, 80, 286 + i * 39)
        game.button((80, 544, 400, 40), "OPEN FACTORY FLOOR", game.open_factory, active=True, small=True)
        game.button((80, 601, 400, 48),
                    "PAUSE SERVICE" if village.service_active else "OPEN SERVICE",
                    game.toggle_service, active=village.service_active, small=True)
        card(screen, (641, 199, 578, 495))
        label(game, "SERVICE INPUTS", 662, 222, TEAL, game.heading)
        for i, (key, good) in enumerate((("fuel_yard", "fuel"), ("parts_shop", "parts"))):
            firm = village.businesses[key]
            label(game, f"{firm['name']}: {firm['stock'].get(good, 0)} {good}", 662, 290 + i * 52)
        from materials import material_status
        inventory = getattr(village, "material_inventory", {})
        label(game, "PROJECT MATERIALS", 662, 390, TEAL, game.font)
        label(game, "On hand: " + " / ".join(f"{good} {inventory.get(good, 0)}" for good in ("timber", "metal", "fittings")), 662, 424, INK, game.tiny)
        wrapped_text(screen, game.tiny, material_status(village, village.active_commission),
                     662, 450, 536, COPPER, line_height=20, max_lines=2)
        label(game, "Buy locally in the east district. Prototyping stays free.", 662, 499, MUTED, game.tiny)
        label(game, f"Computation: {len(village.compute_designs)} calculators / {village.compute_earned}c net", 662, 530, TEAL)
        game.button((662, 557, 400, 33), "FIND MATERIAL SUPPLIERS  [MAP]", lambda: game.select_ledger_tab("Map"), small=True)
        game.button((662, 601, 400, 48), "COMPUTATION OFFICE  [C]", game.open_compute, small=True)
    controls = {
        "Overview": "LEFT / RIGHT change section    J contracts    ESC return",
        "Map": "LEFT / RIGHT change section    ESC return",
        "People": "UP / DOWN select resident    LEFT / RIGHT change section    ESC return",
        "Businesses": "UP / DOWN select firm    LEFT / RIGHT change section    ESC return",
        "Trade": "UP / DOWN older / newer day    LEFT / RIGHT change section    ESC return",
        "Inventors": "UP / DOWN select inventor    LEFT / RIGHT section    J contracts    ESC return",
        "Workshop": "Factory floor / optional service / computation    LEFT / RIGHT change section    ESC return",
    }
    label(game, controls[game.ledger_tab] + "    N next day", 63, 706, PAPER, game.tiny)
