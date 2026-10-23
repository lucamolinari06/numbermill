"""Shared full-screen village ledger; each section has room to grow."""

import pygame
from town import LOCATIONS, WORLD_W, WORLD_H, LABELS


TABS = ("Overview", "Map", "People", "Businesses", "Trade", "Inventors", "Workshop")
INK = (42, 47, 45)
MUTED = (102, 104, 95)
PAPER = (250, 239, 211)
TEAL = (55, 116, 108)
COPPER = (171, 94, 62)
RED = (171, 75, 67)


def card(screen, rect):
    pygame.draw.rect(screen, (66, 79, 71), pygame.Rect(rect).move(3, 4), border_radius=7)
    pygame.draw.rect(screen, PAPER, rect, border_radius=7)
    pygame.draw.rect(screen, (187, 170, 135), rect, 2, border_radius=7)


def label(game, value, x, y, color=INK, font=None):
    game.screen.blit((font or game.small).render(str(value), True, color), (x, y))


def plot(game, rect, values, title, color=TEAL):
    card(game.screen, rect)
    x, y, w, h = rect
    label(game, title, x + 18, y + 14, font=game.font)
    if not values:
        label(game, "No daily history yet", x + 18, y + 78, MUTED)
        return
    low, high = min(values), max(values)
    span = max(1, high - low)
    points = []
    for i, value in enumerate(values):
        px = x + 24 + int(i * (w - 48) / max(1, len(values) - 1))
        py = y + h - 34 - int((value - low) * (h - 88) / span)
        points.append((px, py))
    pygame.draw.line(game.screen, (187, 170, 135), (x + 24, y + h - 33), (x + w - 24, y + h - 33), 2)
    if len(points) > 1:
        pygame.draw.lines(game.screen, color, False, points, 3)
    for point in points[-1:]:
        pygame.draw.circle(game.screen, color, point, 5)
    label(game, f"{values[-1]} now", x + w - 123, y + 17, color)
    label(game, f"low {low}  high {high}  /  last {len(values)} days", x + 18, y + h - 25, MUTED, game.tiny)


def draw(game):
    screen, village = game.screen, game.village
    screen.fill((61, 82, 76))
    card(screen, (28, 22, 1224, 716))
    label(game, "TOWN LEDGER", 55, 44, TEAL, game.big)
    label(game, f"DAY {village.day}  /  {village.coins}c  /  {len(village.citizens)} residents", 895, 53, MUTED)
    game.button((1094, 91, 132, 35), "BACK [ESC]", game.close_ledger, small=True)
    for index, tab in enumerate(TABS):
        game.button((55 + index * 145, 94, 136, 37), tab.upper(),
                    lambda chosen=tab: game.select_ledger_tab(chosen),
                    active=game.ledger_tab == tab, small=True)
    label(game, game.ledger_tab, 62, 159, TEAL, game.heading)
    if game.ledger_tab == "Overview":
        plot(game, (58, 200, 365, 198), [h["population"] for h in village.history], "Population")
        plot(game, (456, 200, 365, 198), [h["bread_price"] for h in village.history], "Bread price", COPPER)
        plot(game, (854, 200, 365, 198), [h["missed_meals"] for h in village.history], "Missed meals", RED)
        card(screen, (58, 423, 562, 270))
        label(game, "WHY THINGS CHANGED", 77, 444, TEAL, game.font)
        label(game, village.market_note[:61], 77, 485)
        for i, event in enumerate(village.journal[:5]):
            label(game, event[:67], 77, 518 + i * 31, MUTED, game.tiny)
        card(screen, (645, 423, 574, 270))
        label(game, "NEXT DECISIONS", 663, 444, TEAL, game.font)
        open_jobs = [key for key, offer in village.offers.items() if offer["status"] in ("open", "bid")]
        lines = [
            f"Open jobs: {', '.join(open_jobs) if open_jobs else 'none'}",
            f"Workshop service: {'open' if village.service_active else 'paused'}",
            f"Fuel: {village.businesses['fuel_yard']['stock'].get('fuel', 0)}   Parts: {village.businesses['parts_shop']['stock'].get('parts', 0)}",
            "J: contract board     Workshop tab: recurring service",
        ]
        for i, line in enumerate(lines):
            label(game, line, 663, 490 + i * 43)
    elif game.ledger_tab == "Map":
        card(screen, (58, 200, 810, 493))
        card(screen, (891, 200, 328, 493))
        label(game, "COPPERSIDE  /  YOU ARE THE GOLD DOT", 77, 216, TEAL, game.font)
        left, top, width, height = 92, 253, 740, 411
        pygame.draw.rect(screen, (137, 168, 119), (left, top, width, height), border_radius=4)
        sx, sy = width / WORLD_W, height / WORLD_H
        def point(x, y):
            return int(left + x * sx), int(top + y * sy)
        for a, b in (((80, 625), (1740, 625)), ((1120, 120), (1120, 1260)),
                     ((100, 970), (1620, 970)), ((90, 1150), (1200, 1150)),
                     ((280, 290), (1600, 290))):
            pygame.draw.line(screen, (205, 194, 156), point(*a), point(*b), 14)
        for key, (x, y) in LOCATIONS.items():
            px, py = point(x, y)
            color = COPPER if key in ("fuel_yard", "parts_shop", "nell_shop") else TEAL
            pygame.draw.circle(screen, color, (px, py), 7)
            short = {"fuel_yard": "Mely", "parts_shop": "Luca", "nell_shop": "Nell",
                     "workshop": "Workshop", "home_1": "Home", "home_2": "Home", "home_3": "Home"}.get(key, LABELS[key])
            label(game, short, px + 9, py - 8, INK, game.tiny)
        pygame.draw.circle(screen, (230, 183, 71), point(game.town.player_x, game.town.player_y), 9)
        label(game, "NEIGHBORHOODS", 910, 218, TEAL, game.font)
        for i, line in enumerate((
            "North: fuel, repairs, Nell",
            "Center: mill, workshop, bakery",
            "South: farm, market, homes",
            "",
            "Walk with WASD or arrows.",
            "Press E near a door or person.",
            "M opens this map in town.",
        )):
            label(game, line, 910, 268 + i * 46, INK if i < 3 else MUTED, game.tiny)
    elif game.ledger_tab == "People":
        plot(game, (58, 200, 475, 213), [h["population"] for h in village.history], "Population")
        plot(game, (552, 200, 667, 213), [h["missed_meals"] for h in village.history], "Cumulative missed meals", RED)
        card(screen, (58, 434, 525, 260))
        label(game, "RESIDENTS  /  CURRENT CHOICES", 78, 452, TEAL, game.font)
        people = sorted(village.citizens, key=lambda person:
                        (person["name"] not in ("Mely", "Luca"), person["name"]))
        for i, person in enumerate(people[:7]):
            color = COPPER if i == game.ledger_index else INK
            label(game, f"{person['name']:<8} {person['activity'][:22]}", 80, 490 + i * 27, color, game.tiny)
        selected = people[game.ledger_index % len(people)]
        home = village.households[selected["home"]]
        card(screen, (603, 434, 616, 260))
        label(game, selected["name"].upper(), 624, 452, TEAL, game.font)
        label(game, f"Mood {selected['mood']}   Energy {selected['energy']}   Hunger {selected['hunger']}", 624, 489)
        label(game, f"Home savings {home['cash']}c   Work: {selected['workplace']}", 624, 521)
        label(game, selected["last_reason"][:68], 624, 553, COPPER)
        label(game, selected["aspiration"][:67], 624, 582, INK, game.tiny)
        relation = selected["relationships"].get("Luca" if selected["name"] == "Mely" else "Mely", None)
        trust = selected["relationships"].get("You", 20)
        if relation is not None:
            label(game, f"Spouse bond: {relation}/100   Trust in you: {trust}/100", 624, 610, MUTED, game.tiny)
        else:
            label(game, f"Trust in you: {trust}/100", 624, 610, MUTED, game.tiny)
        label(game, (selected["memories"][-1] if selected["memories"] else "No recent memory")[:75],
              624, 648, MUTED, game.tiny)
    elif game.ledger_tab == "Businesses":
        keys = list(village.businesses)
        selected = keys[game.ledger_index % len(keys)]
        firm = village.businesses[selected]
        card(screen, (58, 199, 440, 495))
        label(game, "FIRMS  /  UP DOWN TO SELECT", 77, 216, TEAL, game.font)
        for i, key in enumerate(keys[:12]):
            current = village.businesses[key]
            color = COPPER if key == selected else INK
            label(game, f"{current['name'][:25]:<25} {current['cash']:>4}c", 77, 259 + i * 34, color, game.tiny)
        card(screen, (520, 199, 699, 495))
        label(game, firm["name"], 542, 220, TEAL, game.heading)
        lines = [
            f"Owner: {firm['owner']}   Workers: {firm['workers']}   Capacity: {village.capacity(selected)}/day",
            f"Stock: {', '.join(f'{good} {count}' for good, count in firm['stock'].items()) or 'none'}",
            f"Machines: {', '.join(firm['machines']) or 'none'}",
            f"Parent firm: {firm.get('parent_id') or 'independent'}",
        ]
        for i, line in enumerate(lines):
            label(game, line[:65], 542, 276 + i * 33)
        plot(game, (542, 430, 652, 235), [h.get("business_cash", {}).get(selected, firm["cash"]) for h in village.history],
             "Cash history")
    elif game.ledger_tab == "Trade":
        plot(game, (58, 200, 550, 239), [h["bread"] for h in village.history], "Bread in village")
        plot(game, (628, 200, 591, 239), [h["bread_price"] for h in village.history], "Bread price", COPPER)
        card(screen, (58, 462, 570, 232))
        label(game, "LOCAL SUPPLY CHAINS", 78, 479, TEAL, game.font)
        for i, line in enumerate((
            "Farm > Mill > Bakery > Market > Homes",
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
            buyer = entry["to"].replace("Copperside ", "")[:16]
            line = f"{seller} > {buyer}: {entry['units']} {entry['good']} / {entry['coins']}c"
            label(game, line[:69], 667, 518 + i * 31, INK, game.tiny)
        if not entries:
            label(game, "Advance a day to see purchases and deliveries.", 667, 526, MUTED)
    elif game.ledger_tab == "Inventors":
        card(screen, (58, 198, 555, 497))
        label(game, "NELL  /  RIVAL INVENTOR", 80, 223, TEAL, game.heading)
        active = [(key, offer) for key, offer in village.offers.items() if offer["status"] == "bid"]
        label(game, f"Earned: {village.rival_cash}c", 80, 278)
        label(game, f"Current work: {active[0][0] if active else 'looking for work'}", 80, 315)
        if active:
            label(game, f"Expected delivery: day {active[0][1]['finish_day']}", 80, 350)
        label(game, "Nell visits a customer while building their job.", 80, 399, MUTED)
        label(game, "Public bids and deliveries also appear on the board.", 80, 430, MUTED)
        card(screen, (637, 198, 582, 497))
        label(game, "CONTRACT RECORD", 659, 223, TEAL, game.heading)
        for i, (key, offer) in enumerate(village.offers.items()):
            label(game, f"{key.title():<11} {offer['status']:<8}  owner {offer.get('design_owner', 'undecided')}",
                  659, 281 + i * 47)
            if offer["status"] == "bid":
                label(game, f"Customer deadline {offer['due_day']}  /  Nell finishes {offer['finish_day']}",
                      659, 303 + i * 47, COPPER, game.tiny)
    else:
        card(screen, (58, 199, 560, 495))
        label(game, "YOUR WORKSHOP", 80, 222, TEAL, game.heading)
        owned = sum(offer["status"] == "player" for offer in village.offers.values())
        for i, line in enumerate((
            f"Delivered designs: {owned}",
            f"Active licenses: {len(village.licenses)}",
            f"Service days completed: {village.service_days}",
            f"Net service earnings: {village.service_earned}c",
            "Service costs 3c fuel + 2c parts per order.",
            "Customer pays 7c and gains +1 capacity that day.",
        )):
            label(game, line, 80, 286 + i * 39)
        game.button((80, 601, 400, 48),
                    "PAUSE SERVICE" if village.service_active else "OPEN SERVICE",
                    game.toggle_service, active=village.service_active, small=True)
        card(screen, (641, 199, 578, 495))
        label(game, "SERVICE INPUTS", 662, 222, TEAL, game.heading)
        for i, (key, good) in enumerate((("fuel_yard", "fuel"), ("parts_shop", "parts"))):
            firm = village.businesses[key]
            label(game, f"{firm['name']}: {firm['stock'].get(good, 0)} {good}", 662, 290 + i * 52)
        label(game, "Complete any contract to offer this recurring service.", 662, 431, MUTED)
        label(game, "Shortages or insolvent customers pause orders for the day.", 662, 465, MUTED)
        label(game, f"Computation: {len(village.compute_designs)} calculators / {village.compute_earned}c net", 662, 530, TEAL)
        game.button((662, 601, 400, 48), "COMPUTATION OFFICE  [C]", game.open_compute, small=True)
    label(game, "LEFT / RIGHT change section    UP / DOWN select firm    ESC return", 63, 706, MUTED, game.tiny)
