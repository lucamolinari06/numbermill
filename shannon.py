"""Shannon's small steam console and radial village navigation."""
import math
import pygame
from ui_theme import PAPER, INK, TEAL, COPPER, GOLD, MUTED, draw_panel, fit_text, wrapped_text

CENTER = (55, 690)
OPEN_CENTER = (145, 610)
BODY = pygame.Rect(18, 636, 74, 100)
PANEL = pygame.Rect(310, 390, 485, 346)
ACTIONS = ('news', 'ledger', 'contracts', 'map', 'next_day', 'help')
LABELS = ('News', 'Ledger', 'Jobs', 'Map', 'Next day', 'Help')
NODES = tuple((round(OPEN_CENTER[0] + 90 * math.cos(math.radians(a))),
               round(OPEN_CENTER[1] + 90 * math.sin(math.radians(a))))
              for a in (210, 270, 330, 30, 90, 150))


class Shannon:
    def __init__(self):
        self.open = False
        self.page = None
        self.news_page = 0
        self.motion = 0.0

    def update(self, dt):
        direction = 1 if self.open else -1
        self.motion = max(0.0, min(1.0, self.motion + direction * max(0, dt) / .3))

    @property
    def center(self):
        ease = self.motion * self.motion * (3 - 2 * self.motion)
        return tuple(round(a + (b - a) * ease) for a, b in zip(CENTER, OPEN_CENTER))

    @property
    def body(self):
        return BODY.move(self.center[0] - CENTER[0], self.center[1] - CENTER[1])

    def toggle(self, game):
        self.open = not self.open
        self.page = None
        if self.open:
            game.town_dialogue = None

    def click(self, game, point, button):
        if self.body.collidepoint(point):
            if button == 1:
                self.toggle(game)
            return True
        if not self.open:
            return False
        if self.motion < 1:
            return True
        if button == 1:
            for action, center in zip(ACTIONS, NODES):
                if math.dist(point, center) <= 29:
                    self.activate(game, action)
                    return True
            if self.page == 'news' and 641 <= point[1] <= 671 and 330 <= point[0] <= 775:
                count = max(1, math.ceil(len(self.news_lines(game)) / 8))
                self.news_page = max(0, min(count - 1, self.news_page + (-1 if point[0] < 550 else 1)))
                return True
            if self.page and PANEL.collidepoint(point):
                if self.page == 'news' and pygame.Rect(330, 678, 445, 38).collidepoint(point):
                    nearby = game.town.nearby()
                    if nearby is None:
                        self.page = 'help'
                        return True
                    self.open = False
                    self.page = None
                    if nearby.startswith('person:'):
                        game.town_dialogue = nearby
                        game.town_topic = 'work'
                    else:
                        game.interact_town()
                return True
        # Dismiss without accidentally speaking to somebody behind the menu.
        self.open = False
        self.page = None
        return True

    def activate(self, game, action):
        if action in ('news', 'help'):
            self.page = action
            self.news_page = 0
            return
        self.open = False
        self.page = None
        if action == 'ledger':
            game.open_ledger()
        elif action == 'contracts':
            game.open_contract_board()
        elif action == 'map':
            game.open_ledger()
            game.select_ledger_tab('Map')
        elif action == 'next_day':
            game.next_day()

    def news_lines(self, game):
        paragraphs = [(game.village.market_note, INK), (game.message, COPPER)]
        latest = next(iter(game.village.journal), '')
        if latest != game.message:
            paragraphs.append((latest, INK))
        paragraphs.append((game.village.competition_status, MUTED))
        decision = game.village.businesses.get('east_bakery', {}).get('owner_decision')
        if decision:
            paragraphs.append((decision, INK))
        lines = []
        for paragraph, color in paragraphs:
            if not paragraph:
                continue
            line = ''
            for word in str(paragraph).split():
                candidate = (line + ' ' + word).strip()
                if game.small.render(candidate, True, color).get_width() > 440:
                    if line:
                        lines.append((line, color))
                    line = ''
                    for char in word:
                        if game.small.render(line + char, True, color).get_width() > 440:
                            lines.append((line, color))
                            line = ''
                        line += char
                else:
                    line = candidate
            if line:
                lines.append((line, color))
            lines.append(('', color))
        return lines

    def draw(self, game):
        screen = game.screen
        if self.motion > .65:
            menu = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            pygame.draw.circle(menu, COPPER, self.center, 90, 3)
            for action, label, point in zip(ACTIONS, LABELS, NODES):
                point = (point[0] + self.center[0] - OPEN_CENTER[0], point[1] + self.center[1] - OPEN_CENTER[1])
                hover = math.dist(game.mouse_pos(), point) <= 29
                pygame.draw.circle(menu, INK, (point[0] + 2, point[1] + 3), 29)
                pygame.draw.circle(menu, GOLD if hover else PAPER, point, 28)
                pygame.draw.circle(menu, COPPER, point, 28, 3)
                icon(menu, action, point)
                text = game.tiny.render(label, True, PAPER)
                badge = text.get_rect(midtop=(point[0], point[1] + 30)).inflate(10, 4)
                pygame.draw.rect(menu, (49, 69, 61), badge, border_radius=4)
                menu.blit(text, text.get_rect(center=badge.center))
            menu.set_alpha(round(255 * (self.motion - .65) / .35))
            screen.blit(menu, (0, 0))
        avatar = pygame.Surface((110, 150), pygame.SRCALPHA)
        sprite(avatar, (55, 85), 0 if getattr(game, 'reduced_motion', False) else game.town.visual_time)
        screen.blit(pygame.transform.scale(avatar, (88, 120)), (self.center[0] - 44, self.center[1] - 68))
        if self.motion == 0:
            text = game.tiny.render('SHANNON [H]', True, PAPER)
            rect = text.get_rect(center=(55, 741)).inflate(14, 9)
            pygame.draw.rect(screen, (49, 69, 61), rect, border_radius=5)
            screen.blit(text, text.get_rect(center=rect.center))
            if game.message_timer > 0:
                pygame.draw.circle(screen, GOLD, (85, 657), 9)
                fit_text(screen, game.tiny, '!', 82, 649, 10, INK)
        if self.open and self.page:
            draw_panel(screen, PANEL)
            title = 'SHANNON / VILLAGE NOTES' if self.page == 'news' else 'SHANNON / FIELD GUIDE'
            fit_text(screen, game.font, title, 330, 410, 440, TEAL)
            if self.page == 'news':
                lines = self.news_lines(game)
                pages = max(1, math.ceil(len(lines) / 8))
                self.news_page = min(self.news_page, pages - 1)
                for i, (line, color) in enumerate(lines[self.news_page * 8:(self.news_page + 1) * 8]):
                    screen.blit(game.small.render(line, True, color), (330, 451 + i * 23))
                if pages > 1:
                    fit_text(screen, game.small, '< Previous', 330, 648, 145, TEAL)
                    fit_text(screen, game.small, f'{self.news_page + 1} / {pages}', 520, 648, 100, MUTED)
                    fit_text(screen, game.small, 'Next >', 695, 648, 80, TEAL)
                pygame.draw.rect(screen, TEAL, (330, 678, 445, 38), border_radius=5)
                fit_text(screen, game.small, game.town.interaction_prompt(), 342, 688, 421, PAPER)
            else:
                lines = ('WASD / arrows  Walk around', 'Click a resident  Talk', 'E  Visit a nearby building',
                         'L Ledger  J Jobs  M Map  B Journal', 'C Compute  I Invent  /  6 Journey topic',
                         '20:00  Next morning starts automatically',
                         'N  Skip ahead / Q  Menu pauses time', 'H / Esc  Close Shannon')
                for i, line in enumerate(lines):
                    fit_text(screen, game.small, line, 330, 452 + i * 33, 440, INK)


def icon(surface, action, center):
    x, y = center
    if action in ('news', 'ledger', 'contracts'):
        pygame.draw.rect(surface, TEAL, (x - 13, y - 15, 26, 30), 2, border_radius=3)
        if action == 'ledger':
            pygame.draw.line(surface, COPPER, (x - 6, y - 14), (x - 6, y + 14), 3)
        for dy in (-7, 0, 7):
            pygame.draw.line(surface, TEAL, (x - 2, y + dy), (x + 8, y + dy), 2)
        if action == 'contracts':
            pygame.draw.circle(surface, COPPER, (x + 10, y + 10), 6)
    elif action == 'map':
        pygame.draw.lines(surface, TEAL, True, [(x-16,y-10),(x-5,y-15),(x+5,y-10),(x+16,y-15),(x+16,y+10),(x+5,y+15),(x-5,y+10),(x-16,y+15)], 2)
        pygame.draw.line(surface, COPPER, (x-5,y-12), (x-5,y+9), 2)
        pygame.draw.line(surface, COPPER, (x+5,y-8), (x+5,y+12), 2)
    elif action == 'next_day':
        pygame.draw.circle(surface, TEAL, center, 15, 2)
        pygame.draw.lines(surface, COPPER, False, [(x,y-10),(x,y),(x+8,y+4)], 3)
    else:
        pygame.draw.circle(surface, TEAL, center, 14, 2)
        pygame.draw.line(surface, COPPER, (x,y-3), (x,y+8), 4)
        pygame.draw.circle(surface, COPPER, (x,y-8), 2)


def sprite(surface, center, seconds):
    """Procedural brass computer: teal screen, keys, piston feet and steam."""
    x, y = center
    bob = round(math.sin(seconds * 2.5) * 2)
    pygame.draw.ellipse(surface, (64, 81, 62), (x-38,y+41,76,13))
    for dx in (-19, 19):
        pygame.draw.rect(surface, COPPER, (x+dx-5,y+30,10,15), border_radius=2)
        pygame.draw.rect(surface, INK, (x+dx-11,y+42,22,6), border_radius=2)
    y += bob
    pygame.draw.rect(surface, INK, (x-24,y-48,12,21), border_radius=2)
    pygame.draw.rect(surface, COPPER, (x-27,y-51,18,7), border_radius=2)
    for i in range(3):
        phase = (seconds * .6 + i / 3) % 1
        pygame.draw.circle(surface, (221, 217, 186), (x-18+round(math.sin(phase*7)*5), y-54-round(phase*23)), 2+round(phase*3), 1)
    pygame.draw.rect(surface, INK, (x-37,y-34,74,73), border_radius=9)
    pygame.draw.rect(surface, COPPER, (x-34,y-32,68,68), border_radius=7)
    pygame.draw.rect(surface, GOLD, (x-30,y-28,60,42), border_radius=4)
    pygame.draw.rect(surface, (46, 78, 70), (x-25,y-24,50,33), border_radius=3)
    blink = seconds % 4.7 > 4.5
    for dx in (-11, 11):
        pygame.draw.rect(surface, (156, 220, 180), (x+dx-3,y-15,6,2 if blink else 8), border_radius=1)
    pygame.draw.lines(surface, (156,220,180), False, [(x-5,y),(x,y+3),(x+5,y)], 2)
    for row in range(2):
        for col in range(5):
            pygame.draw.rect(surface, PAPER, (x-23+col*10,y+19+row*7,7,4), border_radius=1)
    for dx in (-30,30):
        pygame.draw.circle(surface, GOLD, (x+dx,y+30), 2)
    pygame.draw.line(surface, INK, (x-37,y+4),(x-43,y+20), 5)
    pygame.draw.line(surface, INK, (x+37,y+4),(x+43,y+17+round(math.sin(seconds*2)*3)), 5)
