"""Saved opening-chapter evidence and scenes; never awards gameplay rewards."""

EVIDENCE = {
    'search': ('The unnamed engineer', 'Copperside',
        'Boole and Grace build with steam logic gates whose maker never signed them. Boole wants to find the person behind that work. Shannon wants to understand where he came from.',
        'Are the old machines connected to Shannon? Start with what can be observed, and compare discoveries with the people at home.'),
    'receiver': ('A socket that fits', 'Mosswater / receiver',
        'The receiver attaches to Shannon without an adapter. He understands its technical interface, but has no personal memory of using it.',
        'A shared fitting suggests a connection. It does not identify a maker or explain the missing memories.'),
    'lens': ('The focused lens', 'Mosswater / archive',
        'The archive held a precision cutter blueprint and a lens that also fits Shannon. Recovering the blueprint made the cutter available to buy for the workshop.',
        'Two compatible parts make the connection worth investigating. What else was this equipment intended to work with?'),
    'tower_route': ('Beyond the survey network', 'Mosswater / restored archive',
        'Restoring the survey network revealed the route to Boiler Tower. The archive links two working sites, rather than a collection of unrelated relics.',
        'Follow the tower route from Mosswater when ready. Compare the purpose of its machines with the survey equipment.'),
    'accumulator': ('A reserve for more than one site', 'Boiler Tower / recovered archive',
        'The accumulator has another socket matching Shannon. Its service plate names a southern lock exchange. The tower supplied machinery beyond its own walls.',
        'The lock exchange is a lead, not an explanation. Compare the plate and the recovered equipment with Luca and Grace.'),
    'mosswater_home': ('A careful pair', 'Copperside / Mosswater homecoming',
        'Luca trusts Shannon to read dangerous machinery and trusts the friend Shannon chose. Grace distinguishes a quiet mechanism from a safe one. Mely asks how the journey felt.',
        'Keep both kinds of knowledge: what the machines do, and what the journey means to Shannon.'),
    'tower_home': ('Something brought home', 'Copperside / tower homecoming',
        'The accumulator is installed on the workshop wall. New batches take 20% less time with unchanged materials. Shannon chose to help check the installation, then asked for a quiet walk.',
        'The opening journey is complete. The southern lock exchange is the next lead; life and unfinished work in Copperside still matter.'),
    'well_evening': ('A memory of our own', 'Copperside / the well',
        'Mely, Luca, Boole and Shannon stopped by the well. There was no artifact to recover. Shannon wanted to remember the ordinary afternoon, too.',
        'Finding Shannon\'s past need not consume the life he is making now.'),
}

# Speaker, full paragraph. One page per exchange; no text is silently truncated.
SCENES = {
    'opening': ('A question worth carrying', 'Copperside / before the north road', (
        ('Boole', 'Every useful gate in my workshop begins with somebody else\'s idea. Grace and I can build with them, but neither of us knows who first made them. I want to find that person.'),
        ('Shannon', 'I would like to come. I understand the machines better than I understand my own beginning. Also, you stop when my feet get caught between the stones. That seems a sound basis for an expedition.'),
        ('Boole', 'We can follow the north road to Mosswater, and bring what we learn back here. We do not have to solve your whole history in one trip.'),
        ('Shannon', 'Good. Let us keep a journal: things we have seen on one side, questions on the other. And leave room for things that happen to us, not only things we find.'),
    )),
    'mosswater_home': ('What the lens cannot tell us', 'Copperside / back from Mosswater', (
        ('Shannon', 'The receiver fits. The lens fits. I hoped bringing them home would make something else fit as well. A place, perhaps. A face. So far, I only know more about lenses.'),
        ('Luca', 'A fitting is evidence, not a memory. You understood the traps, Shannon. And you chose a friend who listened when you said to stop. That is why I trust the two of you out there.'),
        ('Grace', 'Bring me the next pressure housing before you open it. I have been testing a vent that fails open when its control line breaks. I want my own machines to give people the warning I did not get.'),
        ('Mely', 'You can tell me about the marsh even if it does not explain anything. Was it beautiful? Was it frightening? Both are things a friend is allowed to ask.'),
        ('Shannon', 'Both. There were reeds taller than me, which is a modest achievement for a reed. I would like to go back with Boole. This time we have the tower route to follow, and somewhere to return to.'),
    )),
    'tower_home': ('A place for what we found', 'Copperside / the workshop wall', (
        ('Luca', 'The accumulator is secured to the rear wall. I checked the mountings; Boole checked the feed. The old pressure marks are still visible. Useful things can have a second life without pretending they are new.'),
        ('Grace', 'The reserve takes a fifth off new batch times. It does not make metal or fuel appear. I would rather have a modest improvement we can measure than a miracle nobody has checked.'),
        ('Shannon', 'The spare socket fits me again. And the plate names a southern lock exchange. I can help trace the connection, but first I want to watch this gauge settle. I was frightened I would miss a warning in the tower.'),
        ('Boole', 'You warned me. We came home together. You do not have to be useful every moment to belong here.'),
        ('Mely', 'Then the first thing this faster workshop can give you is a little time away from it. I would like company on a walk. No delivery baskets required.'),
        ('Shannon', 'Yes. A quiet walk, and then the next question. Put this in the journal too: today we brought something home, and it made room for an ordinary afternoon.'),
    )),
    'well_evening': ('An ordinary afternoon', 'Copperside / beside the well', (
        ('Mely', 'I used to measure a good day by how little work I left behind. Now I am trying to notice who I get to spend it with. Boole, tell me something that happened without a machine in it.'),
        ('Boole', 'Shannon tried to walk around a puddle and found a larger puddle. We agreed the second one was a deliberate inspection.'),
        ('Shannon', 'It had excellent reflections. I disagree with any suggestion that the inspection was a mistake. Though next time I would prefer dry feet.'),
        ('Luca', 'I brought a loose handle to mend, then left it on the bench. It will still be loose tomorrow. I would rather be here while everyone is here.'),
        ('Shannon', 'I want to remember this. Not because it explains who made me. Because I was here, with you.'),
    )),
}


def state(village):
    if not isinstance(getattr(village, 'manufacturing', None), dict):
        village.manufacturing = {}
    data = village.manufacturing.setdefault('opening_chapter', {})
    for key in ('evidence', 'scenes', 'topics'):
        if not isinstance(data.get(key), dict):
            data[key] = {}
    return data


def observe(village):
    """Backfill known discoveries, never completion, rewards or invented dates."""
    data = state(village)
    workshop = village.manufacturing
    field = workshop.get('adventure', {})
    tower = workshop.get('boiler_tower', {})
    eligible = {'search': True, 'receiver': field.get('receiver'),
                'lens': field.get('artifact'), 'tower_route': field.get('expansion_complete'),
                'accumulator': tower.get('complete') or 'steam_accumulator' in workshop.get('unlocks', [])}
    for key in ('mosswater_home', 'tower_home', 'well_evening'):
        eligible[key] = data['scenes'].get(key, {}).get('complete', False)
    for key, happened in eligible.items():
        if happened and key not in data['evidence']:
            data['evidence'][key] = {'read': False}
    return data


def available_scenes(village):
    data = observe(village)
    found = data['evidence']
    keys = ['opening']
    if 'lens' in found:
        keys.append('mosswater_home')
    if 'accumulator' in found:
        keys.append('tower_home')
    projects = getattr(village, 'character_projects', {})
    if (data['scenes'].get('mosswater_home', {}).get('complete') and
            any(projects.get(key, {}).get('status') == 'completed'
                for key in ('mely_bins', 'luca_sort'))):
        keys.append('well_evening')
    return keys


def pages(village, key):
    rows = list(SCENES[key][2])
    if key == 'mosswater_home' and 'tower_route' not in observe(village)['evidence']:
        rows[-1] = ('Shannon', 'Both. There were reeds taller than me, which is a modest achievement for a reed. I would like to return with Boole and finish exploring the survey network. There is more to learn there.')
    if key == 'opening' and 'receiver' in observe(village)['evidence']:
        rows[2] = ('Boole', 'We have already begun following that question. We can bring what we learn back here. We do not have to solve your whole history in one trip.')
    return rows


def pending(village):
    data = observe(village)
    # A new or older save is offered the relevant homecoming before the prologue.
    for key in ('mosswater_home', 'tower_home', 'opening', 'well_evening'):
        if key in available_scenes(village) and not data['scenes'].get(key, {}).get('complete'):
            return key
    return None


def scene_progress(village, key):
    row = state(village)['scenes'].setdefault(key, {'page': 0, 'complete': False})
    row['page'] = max(0, min(len(pages(village, key)) - 1, int(row.get('page', 0))))
    return row


def complete_scene(village, key):
    row = scene_progress(village, key)
    row.update(complete=True, page=len(pages(village, key)) - 1)
    observe(village)


def topic_stage(village):
    found = observe(village)['evidence']
    return 'tower' if 'accumulator' in found else 'mosswater' if 'lens' in found else 'search'


def topic(village, name):
    """Contextual, authored remarks kept separate from random everyday remarks."""
    stage = topic_stage(village)
    rows = {
        'search': {
            'Shannon': ('I want to know where I began. I also want to keep the life we are making here. Those seem like different questions, even when the same walk helps with both.', 'I will watch the machinery. You watch where I put my feet. It is a fair arrangement.'),
            'Luca': ('The old sites still contain live pressure and tired fittings. Shannon can help you read them. Listen to him before you trust a quiet machine.', 'He chose your company, Boole. I trust his judgment. You remind me of the engineer I hoped to be: curious enough to look, careful enough to come back.'),
            'Mely': ('I hope you find answers. But you can visit me without bringing one. I like hearing about the walk as much as the thing at the end of it.', 'I would like to see a place with flowers and no fuel baskets to count. Keep an eye out for one.'),
            'Grace': ('I wanted the anonymous inventor\'s secrets because I could build something valuable with them. I still do. Losing my leg did not take away my curiosity.', 'It changed how I prepare. I am testing a vent that opens when the control line fails. Better warnings are work we can do ourselves.'),
        },
        'mosswater': {
            'Shannon': ('I know how the lens focuses a signal. I do not remember anyone teaching me. It is strange to be confident about a thing and uncertain about yourself.', 'Please write down what we actually saw. I would rather have an honest question than a comforting answer we invented.'),
            'Luca': ('Two matching fittings are a useful lead. Measure the seats and the locking tabs before deciding they share a maker. Good engineering leaves habits in small places.', 'You and Shannon made it back by paying attention to each other. Capability is more than solving the circuit at the end.'),
            'Mely': ('Shannon looked at that lens as though it might greet him. I did not know what to say, so I asked whether he wanted company.', 'You do not have to turn every discovery into the next errand immediately. Some things need an afternoon.'),
            'Grace': ('The recovered blueprint is useful work, not a promise of effortless gears. You still need the cutter, plates, valves and fuel.', 'I can admire its design and keep working on my own. Next time we compare machines, bring your observations as well as the interesting part.'),
        },
        'tower': {
            'Shannon': ('The tower had a place for me without knowing me. Our workshop has a place for me because we made one together. I prefer the second arrangement.', 'I want to follow the lock-exchange lead. I also want the quiet walk we talked about. Please put both on the list.'),
            'Luca': ('The service plate names a southern lock exchange. An accumulator smooths the demand between machines; that tower was serving more than its own landings.', 'Before chasing another route, see what the reserve changes here. New batches run faster. The material bill stays honest.'),
            'Mely': ('I am glad the workshop runs faster. I am more glad you both came home. There should be room in a successful business for the people running it.', 'If you take that quiet walk, I would like to join you. I have opinions about paths that are completely unrelated to moving fuel.'),
            'Grace': ('An old service network, compatible sockets and no signature. That is a pattern worth following, but it is not a name.', 'My vent trial is still on the bench. I will not stop making things here while you look for the person who made those things there.'),
        },
    }
    result = list(rows[stage][name])
    projects = getattr(village, 'character_projects', {})
    if name in ('Mely', 'Luca'):
        final = 'mely_memory' if name == 'Mely' else 'luca_counter'
        first = 'mely_bins' if name == 'Mely' else 'luca_sort'
        if projects.get(final, {}).get('status') == 'completed':
            result[1] = ('The trial you helped finish gave me an evening I could put down my work. That is the sort of progress I want to keep.' if name == 'Mely' else
                         'Our finished trial taught me to stop hovering over every part. Mely and I have an evening to keep. Your next discovery can wait until morning.')
        elif projects.get(first, {}).get('status') in ('accepted', 'completed'):
            result[1] += ' And I have not forgotten the small project we started here.'
    return result


PEOPLE = ('Shannon', 'Luca', 'Mely', 'Grace')
