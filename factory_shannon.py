"""Shannon's saved workshop memories and unhurried, contextual remarks.

Milestones are observed even while the player is elsewhere. Their queue only
advances while the workshop floor is visible, so a fast-forward or a save/load
cannot silently spend the first-batch conversation off screen.
"""
import random
import pygame

from shannon import sprite
from ui_theme import INK, TEAL, draw_panel, fit_text, wrapped_text


LINES = {
    "first_machine": "Our first machine! It looks very serious. Shall we give it something useful to do?",
    "first_batch": "We made those. All of them. Even the slightly wonky one. I am counting that one too.",
    "first_auto": "You didn't touch it! I was watching. Your circuit really is running the workshop.",
    "first_sale": "Someone wanted something we made. I think that makes this a proper workshop.",
}
GREETINGS = (
    "There you are! What shall we make together today?",
    "Welcome back, Boole. I have kept an eye on things. Both eyes, when possible.",
    "Our workshop sounds better with your footsteps in it.",
    "Shall we try one of your ideas? I have brought all of my curiosity.",
    "Back at the bench! I like the part where a drawing becomes something real.",
    "Hello again. Do we have a plan, or shall we discover one as we go?",
    "I was just admiring our little corner of the world. Come in!",
    "Another visit, another possibility. I am ready when you are.",
    "Welcome in! Shall I watch the gauges while you get settled?",
    "I hope you brought an idea. I brought several questions.",
    "Hello, Boole. There is a whole bench here waiting for your next thought.",
    "Back together at the workshop. That is a promising start.",
)


def enter_workshop(village):
    """Shuffle greetings without repetition; retain pending milestone remarks."""
    data = _state(village)
    visits = data.get("visits", 0)
    bag = data.get("greeting_bag", [])
    if not bag:
        bag = list(GREETINGS)
        random.shuffle(bag)
        if bag[-1] == data.get("greeting"):
            bag[0], bag[-1] = bag[-1], bag[0]
    data["greeting"] = bag.pop()
    data["greeting_bag"] = bag
    data["greeting_remaining"] = READ_SECONDS
    data["visits"] = visits + 1


READ_SECONDS = 10.0
DIAGNOSTIC_COOLDOWN = 35.0


def _state(village):
    if not isinstance(getattr(village, "manufacturing", None), dict):
        village.manufacturing = {}
    data = village.manufacturing.setdefault("shannon", {})
    for key, value in (("seen", []), ("queue", []), ("line", ""),
                       ("remaining", 0.0), ("cooldown", 0.0), ("shortage", "")):
        data.setdefault(key, value)
    return data


def event(village, key):
    """Queue a named milestone once; idempotent across saves and frames."""
    if key not in LINES:
        return False
    data = _state(village)
    if key in data["seen"]:
        return False
    data["seen"].append(key)
    data["queue"].append(LINES[key])
    return True


def observe(village):
    """Observe persistent totals, including production completed off screen."""
    _state(village)
    workshop = village.manufacturing
    from manufacturing import PRODUCTION
    milestones = (
        ("first_machine", any(item.get("kind") in PRODUCTION for item in workshop.get("equipment", []))),
        ("first_batch", workshop.get("produced", 0) > 0),
        ("first_auto", workshop.get("auto_produced", 0) > 0),
        ("first_sale", workshop.get("sold", 0) > 0),
    )
    for key, happened in milestones:
        if happened:
            event(village, key)


def _shortage(village):
    from manufacturing import PRODUCTION
    for item in village.manufacturing.get("equipment", []):
        status = str(item.get("status", ""))
        if item.get("kind") in PRODUCTION and status.lower().startswith("need "):
            return status[5:].rstrip(".")
    return ""


def update(game, dt):
    """Call after simulation; only visible, unpaused floor time spends speech."""
    observe(game.village)
    if game.scene != "factory" or getattr(game, "pause_menu_open", False):
        return
    data = _state(game.village)
    dt = max(0.0, min(float(dt), 1.0))
    if data.get("greeting_remaining", 0) > 0:
        data["greeting_remaining"] = max(0.0, data["greeting_remaining"] - dt)
        return
    data["remaining"] = max(0.0, data["remaining"] - dt)
    data["cooldown"] = max(0.0, data["cooldown"] - dt)
    if data["remaining"] > 0:
        return
    data["line"] = ""
    if data["queue"]:
        data["line"] = data["queue"].pop(0)
        data["remaining"] = READ_SECONDS
        return
    shortage = _shortage(game.village)
    if not shortage:
        data["shortage"] = ""
    elif shortage != data["shortage"] and data["cooldown"] == 0:
        data["line"] = f"The bench is waiting for {shortage}. Very patiently. Shall we check the suppliers?"
        data["shortage"] = shortage
        data["remaining"] = READ_SECONDS
        data["cooldown"] = DIAGNOSTIC_COOLDOWN


def current_line(village):
    data = _state(village)
    if data.get("greeting_remaining", 0) > 0:
        return data["greeting"]
    if data["line"]:
        return data["line"]
    if data["queue"]:
        return data["queue"][0]
    workshop = village.manufacturing
    from dialogue import session_choice
    index = session_choice(village, 'workshop_ambient', tuple(range(4)))
    if not any(item.get("kind") == "bench" for item in workshop.get("equipment", [])):
        return (
            "A machine, some supplies, and a little patience. I can help with the patience.",
            "An empty workshop has excellent echoes. I would prefer it with you and a machine in it, though.",
            "Shall we start small? I should like to remember our first little corner when the room is full.",
            "I have inspected the space. There is room for a machine and a rather proud companion.",
        )[index]
    if any(item.get("status") == "Working" for item in workshop.get("equipment", [])):
        return (
            "I like that sound. Something useful is happening.",
            "The machines have a rhythm. I tried joining in, but apparently my timing needs work.",
            "You build the circuits and I watch the little lights. We both take our duties very seriously.",
            "Do you think the people who use these parts will wonder who made them? I hope they like our work.",
        )[index]
    return (
        "I'm here if you need a second pair of eyes. Mine are particularly good at blinking.",
        "It is rather nice, having somewhere to come back to. Especially when you are here too.",
        "I don't remember learning to count. I do remember our first sale. I prefer that memory.",
        "If you need a rest, I can sit quietly with you. Quietly is a skill I am practicing.",
    )[index]


def draw(game, rect):
    """Compact companion panel; no buttons or gameplay mutations."""
    area = pygame.Rect(rect)
    draw_panel(game.screen, area)
    old_clip = game.screen.get_clip()
    game.screen.set_clip(area.inflate(-8, -8))
    avatar = pygame.Surface((110, 150), pygame.SRCALPHA)
    daily = getattr(game.village, 'daily_life', {}) or {}
    phase = daily.get('elapsed', 0) + daily.get('accumulator', 0)
    sprite(avatar, (55, 90), 0 if getattr(game, 'reduced_motion', False) else phase)
    height = min(120, area.height - 8)
    width = round(height * 110 / 150)
    game.screen.blit(pygame.transform.scale(avatar, (width, height)),
                     (area.x + 8, area.bottom - height - 4))
    left = area.x + width + 20
    available = area.right - left - 18
    fit_text(game.screen, game.small, "SHANNON", left, area.y + 13, available, TEAL)
    wrapped_text(game.screen, game.small, current_line(game.village), left, area.y + 38,
                 available, INK, line_height=21, max_lines=max(1, (area.height - 46) // 21))
    game.screen.set_clip(old_clip)
