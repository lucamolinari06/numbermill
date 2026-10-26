"""Authored voices grounded in the same village state the player can inspect."""
import random
import pygame
from ui_theme import draw_panel, wrapped_text, fit_text, INK, MUTED, TEAL, COPPER

SHOP_GREETINGS = {
    'sawmill': "Iris: I cut timber for sturdy frames. Otto also buys it to fire the foundry.",
    'foundry': "Otto: Good metal starts with a hot furnace. Iris supplies the wood; Tess shapes what I smelt.",
    'toolmaker': "Tess: A frame holds your machine together. My fittings make its moving parts work.",
}

VOICES = {
    'Ada': ("Good soil asks for patience. I try to give people the same.", "I'd like a reliable pump, then enough grain to welcome more neighbors."),
    'Bram': ("A mill should hum, not cough. I listen to mine all morning.", "One day I'd like an apprentice who hears a fault before I do."),
    'Agnes': ("The first warm loaf is my favorite part of the day.", "I'd love a bigger bread counter, once flour deliveries can keep up."),
    'Dara': ("You learn a town by what people put in their shopping baskets.", "New neighbors are welcome, but our shelves must grow with them."),
    'Mely': ("Steam is useful only when somebody keeps the fire supplied.", "I'd like our new trades to grow without leaving the old ones short of fuel."),
    'Luca': ("I keep worn parts. There's usually one more useful thing inside.", "A local toolmaker means fewer repairs waiting on the road from outside."),
    'Rowan': ("I'm still learning everyone's footsteps on this street.", "I came for steady work. Now I'd like to make this cottage feel like home."),
}

HARDSHIP_VOICES = {
    'Ada': "An empty shelf starts a long way from the market. I worry about the field, then the mill, then everyone's supper.",
    'Bram': "When bread runs short, I count the flour sacks twice. I want to know whether the delay began at my door.",
    'Agnes': "I can share market orders with Jun. Watching another baker close still hurts; an oven is someone's living.",
    'Dara': "A closed shop means fewer choices for my customers. I need steady deliveries, but I can't promise orders nobody can pay for.",
    'Mely': "I know the sound of a cold boiler. Jun needs a working trade again, not fuel bills he can't cover.",
    'Luca': "A closed door makes me wonder what could be repaired. Some troubles need a fitting; others need customers.",
    'Rowan': "I came here for steady work. When a shop closes, I wonder how firmly I've put down roots.",
}

WORK_JOBS = {'Ada': ('pump',), 'Bram': ('mill',), 'Agnes': ('bakery', 'vent'), 'Dara': ('market', 'sorter')}


def request_reflection(village, name):
    from character_projects import project_for
    project = project_for(village, name)
    if not project:
        return None
    state = project['status']
    if state == 'completed':
        if project.get('key') == 'pantry_shelf':
            remaining = village.businesses['market'].get('pantry_protection', 0)
            return (f"Your shelves still protect {remaining} spoilage events. It gives us time to sell the bread we already have."
                    if remaining else "Your shelves saved three loaves. They've worn out now, but I remember the families who got that bread.")
        return project['outcome']
    if state == 'accepted':
        return project['accepted_text']
    return project['intro']


def recent_work(village, name):
    """Acknowledge an actual delivery and its author, never an assumed promise."""
    for key in reversed(WORK_JOBS.get(name, ())):
        offer = village.offers.get(key, {})
        if offer.get('status') not in ('player', 'rival'):
            continue
        author = 'You' if offer['status'] == 'player' else offer.get('design_owner', 'Grace')
        reflections = {
            'pump': "made the pump controls safer. Now I can think about the crop instead of watching every valve.",
            'mill': "got the mill controller working. I still listen for trouble, but I don't have to do every check by hand.",
            'bakery': "gave the ovens a backup. It helps me plan a batch, though I still need flour to fill it.",
            'vent': "installed the safety vent. Knowing the boiler can release pressure lets me concentrate on the bread.",
            'market': "fixed the storeroom cooling. Keeping a loaf fresh matters as much as making another one.",
            'sorter': "improved the market signals. The counter feels calmer when deliveries arrive in a sensible order.",
        }
        return f"{author} {reflections[key]}"
    return None


def _conversation(village, name, topic):
    """Return full paragraphs; presentation wraps them instead of cutting dialogue."""
    if name == 'Shannon':
        return {
            'work': ["I watch your circuits, but I like watching you work things out even more.",
                     "A little light comes on, and suddenly an idea can do something. I don't think I'll get tired of that."],
            'family': ["I like our walks, Boole. You always wait when my feet get caught on a stone.",
                       "I think that's a good thing to have in a friend. Someone who notices when you need a moment."],
            'town': ["Everyone has somewhere to be. I like learning which footsteps belong to which person.",
                     "Do you think a place becomes home all at once, or a little more each time somebody says hello?"],
            'hopes': ["I'd like to find out where I came from. Some days I am curious. Some days I am a little frightened.",
                      "When we find something, will you stay with me while I work out what it means?"],
        }.get(topic, ["I'm glad we're taking this walk together.", "Shall we stop here a moment?"])
    tenant = village.businesses.get('east_bakery', {})
    if topic == 'town' and tenant and tenant.get('owner', 'Jun') != 'Jun':
        return [f"{tenant['owner']} has brought a different trade to the northeast street. A shop needs real customers to keep its doors open.", village.competition_status]
    if name == 'Grace':
        bid = next((key for key, offer in village.offers.items() if offer['status'] == 'bid'), None)
        if topic == 'hopes':
            return ["I'd like Copperside to know me for useful machines, not just quick bids.",
                    "I still want to understand those old machines. Next time, I want to come home with the knowledge and everyone I went with."]
        if topic == 'family':
            return ["I lost my leg trying to reach one of the old inventor's artifacts. Its defenses were still working. I found that out too late.",
                    "I thought those secrets would make my fortune. I came back with fewer plans, and people who helped me learn to walk again."]
        if topic == 'town':
            if village.businesses.get('east_bakery', {}).get('operating_state') == 'paused':
                return ["Jun's closed oven is a reminder: a clever controller cannot create paying customers. I want my work to solve the right problem.",
                        village.businesses['east_bakery'].get('owner_decision', village.competition_status)]
            return ["A larger village needs more than roofs. People need meals and work that pays.", village.migration_status]
        return [f"I'm building the {bid.replace('_', ' ')} job. A promise matters once a customer is waiting." if bid else
                "I'm looking for a job where a machine will actually earn its keep.",
                "After the expedition that cost me my leg, I stopped trusting a machine just because it looked quiet. Test the failure cases, Boole."]
    person = next((p for p in village.citizens if p['name'] == name), None)
    if person is None:
        return ["I'm away from the village just now.", "The People ledger keeps the latest household news."]
    newcomer_voices = {
        'Saffron': 'I learn names faster than street corners. Have you met our newest neighbor?',
        'Felix': 'A good fitting saves twice as much time as a hurried repair.',
        'Wren': "Nothing useful should go to waste, whether it is a seed or a day's work.",
        'Hugo': 'My old teacher said steady hands come from patient mornings.',
        'Alma': 'There is always room for another chair around my table.',
        'Perry': 'A bent cog is a puzzle. I like puzzles that leave something useful behind.',
        'Cleo': 'I keep a little notebook of what worked today. Tomorrow starts there.',
    }
    voice, hope = VOICES.get(name, (newcomer_voices.get(name, "It's good to see a familiar face."), person['aspiration']))
    home = village.households[person['home']]
    firm = village.businesses.get(person['workplace'], {})
    trust = person['relationships'].get('Boole', 20)
    if topic == 'hopes':
        request = request_reflection(village, name)
        if request:
            return [hope, request]
        return [hope, "I've come to trust your work. Seeing you keep a promise makes a difference." if trust >= 30 else
                "Come by again. It's easier to share plans once we know each other."]
    if topic == 'family':
        family = [p['name'] for p in village.citizens if p['home'] == person['home'] and p['name'] != name]
        family_voices = {
            'Ada': "Bram brings the mill home in his head. I try to ask about his day before I ask about the flour.",
            'Bram': "Ada notices when I am worrying before I say anything. We talk things through over supper.",
            'Agnes': "Dara hears everyone's news at the counter. At home I ask for one story that isn't about deliveries.",
            'Dara': "Agnes rises thinking about the next batch. I try to make sure our own meal doesn't become another chore.",
            'Mely': "Luca keeps every worn part. I complain about the clutter, then ask him to fix something with it.",
            'Luca': "Mely knows when I've forgotten to stop working. An evening together is worth more than one extra repair.",
            'Rowan': "I'm still deciding where everything belongs in the cottage. Having a key of my own makes this feel real.",
        }
        first = family_voices.get(name, f"I share my home with {' and '.join(family)}." if family else "The cottage is mine to look after.")
        if name in ('Mely', 'Luca'):
            from character_projects import STORY_DEFINITIONS, presentation
            chapters = [presentation(village, key) for key, definition in STORY_DEFINITIONS.items()
                        if definition['npc'] == name and key in village.character_projects]
            story = max(chapters, key=lambda chapter: chapter['chapter'], default=None)
            if story and story.get('chapter'):
                if story['status'] == 'completed' and story['chapter'] == 3:
                    first = ("Luca and I had our evening together. The yard still needs me, but it does not need every thought I have." if name == 'Mely' else
                             "I left the bench ready and came home to Mely. I want that to be a habit, not a celebration I have only once.")
                elif story.get('chapter', 0) >= 2:
                    first += " We have been talking about the plan you helped us choose. It matters that the choice was ours."

        if home['bought'] < home['bread_need']:
            second = f"We still need today's bread. We have {home['cash']}c saved; the market asks {village.bread_price}c a loaf."
        else:
            second = f"We've eaten today, and have {home['cash']}c put aside. That makes it easier to think about tomorrow."
        return [first, second]
    if topic == 'town':
        if 'east_bakery' in village.businesses:
            if village.businesses['east_bakery'].get('operating_state') == 'paused':
                return [HARDSHIP_VOICES.get(name, "Jun has paused the bakery. I hope local trade can support him again."),
                        village.businesses['east_bakery'].get('owner_decision', village.competition_status)]
            perspectives = {
                'Agnes': "Jun and I now share the market's orders. More ovens help only if the mill can keep both of us supplied.",
                'Bram': "Two bakers now buy our flour. I can see both orders in the trade ledger; keeping the mill running matters.",
                'Dara': "I buy from both bakeries in turn when they have bread. Jun's counter gives us another local supplier.",
            }
            return [perspectives.get(name, "Jun has opened a bakery on the northeast street. Another working shop makes the village feel more settled."),
                    village.competition_status]
        event = village.migration_events[-1]['message'] if village.migration_events else village.migration_status
        return ["The eastern road now reaches the timber yard, foundry, and toolmaker. Buying locally keeps their work moving.", event]
    reason = village.daily_life.get('reasons', {}).get(person['workplace'])
    reflection = recent_work(village, name)
    request = request_reflection(village, name)
    if request:
        detail = request
    elif reason and any(word in reason.lower() for word in ('cannot', 'shortage', 'shutdown', 'closed')):
        detail = f"At {firm.get('name', person['workplace'])}: {reason}"
    elif reflection:
        detail = reflection
    elif firm.get('machines'):
        detail = "The installed machine helps, but we still need workers, supplies, and customers. None of those run on promises."
    else:
        detail = f"Today I'm {person['activity']}. {person['last_reason'].rstrip('.')}."
    return [voice, detail]


# Personal lines vary independently of the economic and story reports.
PERSONAL_LINES = {
    'Luca': {
        'work': (
            "A repair tells you how somebody used a thing. The polished handle, the worn hinge. I like that part of the job.",
            "Sometimes I leave a difficult fitting overnight. In the morning I can usually see what I was forcing.",
            "I keep a chair beside the bench. Visitors shouldn't have to invent a broken tool just to sit with me.",
        ),
        'hopes': (
            "I'd like to make things people can mend themselves. A useful tool shouldn't become a mystery when it breaks.",
            "I'm trying to finish work before the lamps need lighting. Mely deserves more than whatever is left of my evening.",
            "Perhaps I'll teach someone to file a fitting properly. Patience is harder to pass on than measurements.",
        ),
    },
    'Mely': {
        'work': (
            "I can tell which customer has arrived by how they stack the empty fuel baskets. Luca's always has a loose screw in it.",
            "Dry fuel, a clear path, a swept hearth. Most good mornings begin with something nobody notices.",
            "I keep the small pieces for lighting stubborn fires. Being too small for one job doesn't make a thing useless.",
        ),
        'hopes': (
            "I'd like an afternoon with Luca when neither of us says 'just one more thing.' I might have to hide the tools.",
            "When the yard can spare me, I'd like to walk somewhere without calculating how much fuel the journey would take.",
            "I'd like people to stop by even when their baskets are full. News travels better with a cup of tea.",
        ),
    },
}



PERSONAL_LINES.setdefault('Ada', {})
PERSONAL_LINES['Ada']['work'] = (*PERSONAL_LINES['Ada'].get('work', ()), *('The rows look straight from the road. Up close, every plant has its own opinion.', 'I check the soil before I check the sky. One tells me what happened; the other makes promises.', 'Bram asks how the crop is coming. I bring him a handful of grain when words will not do.'))
PERSONAL_LINES['Ada']['hopes'] = (*PERSONAL_LINES['Ada'].get('hopes', ()), *('I would like a season with enough grain left to put some aside.', 'A new neighbor should find a meal waiting, not another empty field.', 'Someday I want to spend a morning growing flowers just because I like them.'))
PERSONAL_LINES.setdefault('Bram', {})
PERSONAL_LINES['Bram']['work'] = (*PERSONAL_LINES['Bram'].get('work', ()), *('Flour finds its way into every pocket. I have stopped taking it personally.', 'I know the sound of a loose bearing better than the sound of my own snoring. Ada disagrees.', 'A quiet mill can mean a good repair or no grain. I always look before I celebrate.'))
PERSONAL_LINES['Bram']['hopes'] = (*PERSONAL_LINES['Bram'].get('hopes', ()), *('I want someone else to know this mill as well as I do.', 'A little spare flour would let us weather a delayed delivery.', "I would like to go home with enough energy to hear about Ada's day properly."))
PERSONAL_LINES.setdefault('Agnes', {})
PERSONAL_LINES['Agnes']['work'] = (*PERSONAL_LINES['Agnes'].get('work', ()), *('I judge a morning by the crust on the first loaf.', 'Dara says I bring flour home on my sleeves. I call it proof I was working.', 'People wait more patiently when they can smell bread. I try not to make them wait too long.'))
PERSONAL_LINES['Agnes']['hopes'] = (*PERSONAL_LINES['Agnes'].get('hopes', ()), *('I would like enough room to try a new recipe without holding up supper.', 'One day I want to bake a loaf just for a long picnic with Dara.', 'A steady flour delivery leaves room for a little imagination.'))
PERSONAL_LINES.setdefault('Dara', {})
PERSONAL_LINES['Dara']['work'] = (*PERSONAL_LINES['Dara'].get('work', ()), *('A tidy counter makes room for a conversation. That is part of the trade too.', 'I remember who likes the darker crust. It saves them asking every time.', 'A delivery is only useful if someone can afford what arrives.'))
PERSONAL_LINES['Dara']['hopes'] = (*PERSONAL_LINES['Dara'].get('hopes', ()), *('I want new neighbors to learn our names before they learn our prices.', 'A well-stocked shelf should mean less worry at supper.', 'I would like an evening with Agnes where neither of us counts anything.'))
PERSONAL_LINES.setdefault('Rowan', {})
PERSONAL_LINES['Rowan']['work'] = (*PERSONAL_LINES['Rowan'].get('work', ()), *('Every familiar face makes the street feel a little less new.', 'I am learning which doors stick and which neighbors wave first.', 'I still take the long way home sometimes, just to learn the village.'))
PERSONAL_LINES['Rowan']['hopes'] = (*PERSONAL_LINES['Rowan'].get('hopes', ()), *('I want to hang something on the cottage wall that I made myself.', 'I would like to invite someone over without worrying whether there is enough bread.', 'One day I hope I can show a newcomer around instead of asking directions.'))
PERSONAL_LINES.setdefault('Saffron', {})
PERSONAL_LINES['Saffron']['work'] = (*PERSONAL_LINES['Saffron'].get('work', ()), *('I remember a face more easily once we have shared a laugh.', 'There is always another name to learn at the market.', 'I like a street where people pause to greet one another.'))
PERSONAL_LINES['Saffron']['hopes'] = (*PERSONAL_LINES['Saffron'].get('hopes', ()), *('I want to host a meal where nobody feels like a stranger.', 'I would like to know who to ask when a neighbor needs help.', 'I hope my cottage becomes a place people visit without an excuse.'))
PERSONAL_LINES.setdefault('Felix', {})
PERSONAL_LINES['Felix']['work'] = (*PERSONAL_LINES['Felix'].get('work', ()), *('Measure twice, then check which end you started from.', 'A fitting that almost fits is a fitting that needs more work.', 'I like a repair that leaves no wobble behind.'))
PERSONAL_LINES['Felix']['hopes'] = (*PERSONAL_LINES['Felix'].get('hopes', ()), *('I want a shelf of tools I know I can trust.', 'I would like to teach someone how to spot a worn joint.', 'A day without a hurried repair would be a fine thing.'))
PERSONAL_LINES.setdefault('Wren', {})
PERSONAL_LINES['Wren']['work'] = (*PERSONAL_LINES['Wren'].get('work', ()), *('Even a small patch can grow something useful.', 'I save string. People laugh until they need a piece.', 'I like work that leaves less waste on the ground.'))
PERSONAL_LINES['Wren']['hopes'] = (*PERSONAL_LINES['Wren'].get('hopes', ()), *('I would like a little garden by the door.', 'I hope we keep room for growing things as the village grows.', 'Someday I want to share seeds with every household.'))
PERSONAL_LINES.setdefault('Hugo', {})
PERSONAL_LINES['Hugo']['work'] = (*PERSONAL_LINES['Hugo'].get('work', ()), *('I set things out before I start. It helps my hands catch up with my head.', 'My teacher would have spotted that crooked edge from the doorway.', 'A slow first attempt saves a second attempt surprisingly often.'))
PERSONAL_LINES['Hugo']['hopes'] = (*PERSONAL_LINES['Hugo'].get('hopes', ()), *('I want to make something my old teacher would use.', 'I would like to stop rushing when somebody is watching.', 'A sturdy table and a good lamp would suit me well.'))
PERSONAL_LINES.setdefault('Alma', {})
PERSONAL_LINES['Alma']['work'] = (*PERSONAL_LINES['Alma'].get('work', ()), *('People tell you more over a meal than across a counter.', 'I keep an extra cup handy. Someone usually needs it.', 'I like knowing which neighbor has had a difficult morning.'))
PERSONAL_LINES['Alma']['hopes'] = (*PERSONAL_LINES['Alma'].get('hopes', ()), *('I want a table long enough for all my guests.', 'I would like everyone here to have someone to call on.', 'A warm kitchen on a cold evening is a good ambition.'))
PERSONAL_LINES.setdefault('Perry', {})
PERSONAL_LINES['Perry']['work'] = (*PERSONAL_LINES['Perry'].get('work', ()), *('A bent cog tells you where the force went.', 'I turn broken parts over in my hands while I think.', 'Finding a use for a discarded part feels like getting a present.'))
PERSONAL_LINES['Perry']['hopes'] = (*PERSONAL_LINES['Perry'].get('hopes', ()), *('I would like a little bench of my own.', 'I want to build something from parts everyone else gave up on.', 'Someday I hope people bring me their difficult repairs.'))
PERSONAL_LINES.setdefault('Cleo', {})
PERSONAL_LINES['Cleo']['work'] = (*PERSONAL_LINES['Cleo'].get('work', ()), *('I write down the mistake before I forget why it happened.', 'A clean page makes a difficult morning feel possible.', 'I keep the useful scraps beside my notebook.'))
PERSONAL_LINES['Cleo']['hopes'] = (*PERSONAL_LINES['Cleo'].get('hopes', ()), *('I want to fill a notebook with things that worked.', 'I would like to show someone a trick I discovered myself.', 'Someday I hope to read these notes and see how far I have come.'))
PERSONAL_LINES.setdefault('Luca', {})
PERSONAL_LINES['Luca']['work'] = (*PERSONAL_LINES['Luca'].get('work', ()), *('Can we try it before we call it finished?', 'It works when I am watching. I would like it to work when I go home too.', 'Wait, when does that valve actually open?'))
PERSONAL_LINES['Luca']['hopes'] = (*PERSONAL_LINES['Luca'].get('hopes', ()), *('I want a bench with room to use it. I keep forgetting that when I add things.', 'I would like to mend something and have it stay mended for years.', 'I had another idea on the walk home. I should probably write it down before supper.'))
PERSONAL_LINES.setdefault('Mely', {})
PERSONAL_LINES['Mely']['work'] = (*PERSONAL_LINES['Mely'].get('work', ()), *('A fuel basket is heavier at the end of the day. I am sure of it.', 'I sweep before I lock up. Tomorrow morning deserves a fair start.', 'Luca calls it a useful spare. I call it something he left on the kitchen table.'))
PERSONAL_LINES['Mely']['hopes'] = (*PERSONAL_LINES['Mely'].get('hopes', ()), *('I would like a good pair of boots and a day with nowhere urgent to be.', 'A yard that runs smoothly should leave me time for my friends.', 'I want a quiet supper while it is still hot. A modest dream, surely.'))

PERSONAL_LINES['Shannon'] = {
    'work': ("I like the moment you stop frowning at a circuit and reach for a part.", "May I watch this time? I will save my questions until you put the tools down.", "Your bench has many interesting corners. I am investigating them carefully."),
    'family': ("I like walking at your pace. It gives us time to notice small things.", "You make room for me when we stop. I notice that, Boole.", "It is nice to have a friend who does not mind a little steam on the walk."),
    'town': ("I am learning the village one doorway at a time.", "The market is a good place to practice saying hello.", "There is a different sound outside every shop. I wonder if people notice."),
    'hopes': ("I have questions about myself that I cannot answer yet.", "Sometimes I wonder what we will find beyond the next bend.", "There are still things I would like to understand about how I work."),
}
PERSONAL_LINES['Grace'] = {
    'family': ("People helped me learn to walk with this leg. I remember who showed up, even when I was poor company.", "After the artifact expedition, I had to learn when to ask for a hand. That was harder than I expected.", "I keep a stool near the bench now. Taking the weight off for a while helps me think."),
    'hopes': ("I would like a customer to come looking for my work before I have to chase their bid.", "I want to understand those artifacts well enough to approach them safely.", "A successful expedition should bring everyone home. I take that rather seriously now."),
}

def session_choice(village, key, choices):
    """Fresh choices for each loaded village; stable during rendering and the day.

    This extra attribute is excluded by village_from_data's dataclass allowlist.
    """
    if not hasattr(village, '_voice_choices'):
        village._voice_choices = {}
    cache = village._voice_choices
    if cache.get('day') != village.day:
        cache.clear()
        cache['day'] = village.day
    token = repr(key)
    if token not in cache or cache[token] not in choices:
        cache[token] = random.choice(choices)
    return cache[token]


def conversation(village, name, topic):
    """Keep live reports intact while personal remarks vary on each load."""
    if topic == 'journey':
        import opening_chapter
        if name in opening_chapter.PEOPLE:
            return opening_chapter.topic(village, name)
    lines = _conversation(village, name, topic)
    choices = PERSONAL_LINES.get(name, {}).get(topic, ())
    if choices:
        lines[0] = session_choice(village, (name, topic, lines[0]), (lines[0], *choices))
    if name == 'Grace' and topic == 'work':
        lines[1] = session_choice(village, (name, 'caution'), (
            lines[1],
            "The artifact defenses were still active when I went in. I mistook silence for safety. That mistake cost me my leg.",
            "The wooden leg needs care, like any tool I rely on. I'd rather you asked about it than pretended it wasn't there.",
            "I wanted the old inventor's secrets because I could sell what I learned. I hadn't thought nearly enough about getting back.",
            "I check every pressure gauge twice now. A few extra minutes at the bench are cheap compared with another bad expedition.",
            "I still enjoy beating you to a bid. I'd enjoy seeing both of us finish with all our fingers even more.",
        ))
    return lines


def portrait(surface, name, rect):
    """Use the same character artwork as the village, with a closer framing."""
    from town import Town
    rect = pygame.Rect(rect)
    pygame.draw.rect(surface, (46, 80, 73), rect, border_radius=4)
    pygame.draw.line(surface, (173, 143, 88), rect.bottomleft, rect.bottomright, 2)
    if name == 'Shannon':
        from shannon import sprite
        image = pygame.Surface((110, 150), pygame.SRCALPHA)
        sprite(image, (55, 90), 0)
        surface.blit(pygame.transform.scale(image, (37, 50)), (rect.x + 4, rect.y - 4))
        return
    from resident_performance import coat_for
    image = pygame.Surface((72, 80), pygame.SRCALPHA)
    Town._villager(None, image, 36, 45, coat_for(name), name=name, shadow_color=None)
    surface.blit(image, rect.topleft, (14, 2, rect.w, rect.h))


def draw_dialogue(surface, fonts, village, location, message, topic='work'):
    from town import location_label
    from materials import SHOPS
    small, regular, heading, _ = fonts
    draw_panel(surface, (235, 414, 810, 306))
    who = location_label(village, location) or 'Available site'
    prompt = 'E / Esc close'
    if location.startswith('person:'):
        who = location[7:]
        lines = conversation(village, who, topic)
        prompt = ('1 Work  2 Family  3 Village  4 Hopes  Esc' if who == 'Shannon' else
                  '1 Work  2 Family  3 Village  4 Hopes  5 Requests  Esc')
        from opening_chapter import PEOPLE
        if who in PEOPLE:
            prompt = ('1 Work  2 Family  3 Village  4 Hopes  6 Journey  Esc' if who == 'Shannon' else
                      '1 Work  2 Family  3 Village  4 Hopes  5 Requests  6 Journey  Esc')
        fit_text(surface, small, topic.upper(), 830, 440, 180, TEAL)
    elif location in SHOPS:
        shop = SHOPS[location]
        firm = village.businesses[location]
        # Shop metadata is exposed by materials; the inventory is shared with delivery.
        good, price = shop['good'], shop['price']
        lines = [SHOP_GREETINGS[location],
                 f"{good.title()}: {price}c each. Counter stock {firm['stock'].get(good, 0)}. You carry {village.material_inventory.get(good, 0)}; purse {village.coins}c."]
        prompt = 'E Buy one   Esc Close'
    elif location == 'market':
        lines = [f"Dara: Bread is {village.bread_price}c a loaf. There are {village.businesses['market']['stock'].get('bread', 0)} on the counter.",
                 f"Your purse: {village.coins}c. Your pantry: {village.player_bread} bread. We keep a loaf for walk-in shoppers when we can."]
        prompt = 'E Buy bread   N Next day   Esc Close'
    elif location == 'east_bakery':
        firm = village.businesses.get(location)
        if firm:
            from economy import BUSINESS_TYPES
            owner = firm.get('owner', 'Owner')
            good = BUSINESS_TYPES[firm['kind']]['output']
            lines = [f"{owner}: I trade {good} here. My capacity is {firm.get('capacity_override', 2)} per day; I pay for supplies and a daily site lease.",
                     f"Stock: {firm['stock'].get(good, 0)}. {firm.get('operating_status', 'Opening tomorrow')}."]
            if firm.get('operating_state') == 'paused':
                lines = [f"{owner}: I've paused work while I look for paying orders. If trade does not recover, I will release the site.",
                         firm.get('owner_decision', village.competition_status)]
            if owner == 'Jun':
                request = request_reflection(village, owner)
                if request:
                    lines[1] = request
                prompt = '5 Requests   Esc Close'
        else:
            lines = ["An available trading site. Its next occupant will depend on local demand.", village.competition_status]
    elif location in village.households:
        home = village.households[location]
        names = ', '.join(p['name'] for p in village.citizens if p['home'] == location)
        lines = [f"{names} live here. Household savings: {home['cash']}c.",
                 f"Bread today: {home['bought']}/{home['bread_need']}. Click a resident to hear their own news."]
    elif location.startswith('home_'):
        lines = ["A place for the village to grow.", village.migration_status]
    elif location == 'grace_shop':
        lines = conversation(village, 'Grace', 'work')
    else:
        firm = village.businesses.get(location, {})
        lines = [f"{who}: {', '.join(f'{n} {g}' for g, n in firm.get('stock', {}).items()) or 'workshop and plans'}.",
                 "The Businesses ledger shows today's output and supplies."]
        if location in ('mill', 'bakery'):
            prompt = 'E Build commission   Esc Close'
    speaker = who if location.startswith('person:') else {
        'sawmill': 'Iris', 'foundry': 'Otto', 'toolmaker': 'Tess', 'market': 'Dara', 'grace_shop': 'Grace',
        'mill': 'Bram', 'bakery': 'Agnes', 'fuel_yard': 'Mely', 'parts_shop': 'Luca'}.get(location)
    if speaker:
        portrait(surface, speaker, (263, 429, 44, 44))
    else:
        pygame.draw.circle(surface, (214, 192, 147), (285, 451), 18, 2)
        pygame.draw.line(surface, TEAL, (276, 451), (294, 451), 3)
        pygame.draw.line(surface, TEAL, (285, 442), (285, 460), 3)
    fit_text(surface, heading, who, 322, 438, 487, TEAL)
    pygame.draw.line(surface, (218, 201, 166), (263, 477), (1013, 477))
    y = 483
    for paragraph in lines:
        y = wrapped_text(surface, regular, paragraph, 263, y, 750, INK, line_height=23, max_lines=3) + 12
    if location in SHOPS or location == 'market':
        fit_text(surface, small, message, 263, 650, 750, COPPER)
    pygame.draw.line(surface, (218, 201, 166), (263, 674), (1013, 674))
    fit_text(surface, small, prompt, 263, 686, 750, TEAL)
