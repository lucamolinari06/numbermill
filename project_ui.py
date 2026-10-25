"""Character requests, with enough room for the reason and actual outcome."""
import pygame
from office_ui import frame
from ui_theme import draw_panel, fit_text, wrapped_text, TEAL, INK, MUTED, COPPER, PAPER


def visible(village):
    from character_projects import ALL_DEFINITIONS, project_for
    names = dict.fromkeys(d['npc'] for d in ALL_DEFINITIONS.values())
    return [project for name in names if (project := project_for(village, name))]


def draw(game):
    screen = game.screen
    frame(screen, 'VILLAGE REQUESTS', game.big)
    game.button((1050, 91, 175, 35), 'BACK [ESC]', game.close_requests, small=True)
    projects = visible(game.village)
    draw_panel(screen, (58, 160, 330, 530))
    draw_panel(screen, (410, 160, 809, 530))
    fit_text(screen, game.font, 'NEIGHBORS', 78, 184, 290, TEAL)
    if not projects:
        wrapped_text(screen, game.font, 'No requests yet. Residents will ask for help as village needs emerge.',
                     436, 215, 750, INK, line_height=28)
        return
    index = game.request_index % len(projects)
    for row, project in enumerate(projects):
        game.button((78, 238 + row * 86, 290, 44), project['npc'],
                    lambda selected=row: setattr(game, 'request_index', selected), active=row == index, small=True)
        fit_text(screen, game.tiny, project['status'].title(), 88, 289 + row * 86, 270, MUTED)
    project = projects[index]
    fit_text(screen, game.heading, project['title'], 436, 184, 750, TEAL)
    if project.get('chapter'):
        fit_text(screen, game.tiny, f"{project['arc']} / Chapter {project['chapter']} of 3", 436, 212, 750, COPPER)
    wrapped_text(screen, game.small, project['intro'], 436, 240, 750, INK, line_height=22, max_lines=3)
    wrapped_text(screen, game.tiny, project['reason'], 436, 310, 750, MUTED, line_height=19)
    bill = project['bill']
    inventory = game.village.material_inventory
    completed = project['status'] == 'completed'
    materials = ('Supplies delivered' if completed else
                 ' / '.join(f"{good.title()} {inventory.get(good, 0)}/{needed}" for good, needed in bill.items()))
    fit_text(screen, game.small, materials, 436, 385, 750, COPPER)
    fit_text(screen, game.small, f"{'Paid' if completed else 'Payment'}: {project['reward']}c", 436, 419, 750, INK)
    effect = project['outcome'] if project['status'] == 'completed' else project['benefit']
    wrapped_text(screen, game.small, effect, 436, 453, 750, TEAL, line_height=22, max_lines=3)
    if project.get('choices') and project['status'] == 'offered':
        for column, (choice, details) in enumerate(project['choices'].items()):
            game.button((436 + column * 365, 520, 350, 34), details['label'],
                        lambda selected=choice: choose_plan(game, project['key'], selected),
                        active=project.get('choice') == choice, small=True)
    elif project['status'] == 'completed':
        from character_projects import story_next
        wrapped_text(screen, game.tiny, story_next(game.village, project), 436, 527, 750, MUTED, line_height=18, max_lines=2)
    if project['status'] != 'completed':
        game.button((436, 566, 250, 44), 'ACCEPT' if project['status'] == 'offered' else 'DELIVER SUPPLIES',
                    lambda: act_on_project(game, project), active=True, small=True)
        game.button((710, 566, 250, 44), 'FIND SUPPLIERS', game.request_suppliers, small=True)
    else:
        fit_text(screen, game.font, f"Completed on day {project.get('completed_day', '?')}", 436, 568, 750, TEAL)
        from character_projects import STORY_DEFINITIONS
        next_stage = next((d for d in STORY_DEFINITIONS.values() if d.get('previous') == project['key']), {})
        goal = next_stage.get('certificate')
        if goal and goal not in game.village.sequential_records:
            import timing_workshop
            game.button((805, 566, 370, 40), 'OPEN TIMING GOAL',
                        lambda: timing_workshop.enter(game, goal), active=True, small=True)
    if game.request_notice and game.request_notice_key == project['key']:
        wrapped_text(screen, game.tiny, game.request_notice, 436, 627, 750, COPPER, line_height=19, max_lines=2)


def choose_plan(game, key, choice):
    from character_projects import choose
    okay, message = choose(game.village, key, choice)
    game.request_notice, game.request_notice_key = message, key
    game.toast(message)
    if okay:
        game.save_game()


def act_on_project(game, project):
    from character_projects import presentation
    project = presentation(game.village, project['key'])
    if project.get('choices') and project['status'] == 'offered' and not project.get('choice'):
        game.request_notice = 'Choose one of the two plans above before accepting.'
        game.request_notice_key = project['key']
        return
    game.act_on_request(project['key'])
