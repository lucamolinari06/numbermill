"""Small authored projects prompted by observed village needs.

These are physical favors, separate from circuit commissions. Every payment
comes from a named local business and every material is consumed once.
"""

DEFINITIONS = {
    'pantry_shelf': {
        'key': 'pantry_shelf', 'npc': 'Dara', 'title': 'A shelf for tomorrow',
        'bill': {'timber': 2, 'fittings': 1}, 'reward': 8, 'payer': 'market',
        'intro': "I remember which families leave without bread. Could you build a dry pantry shelf so today's leftovers can help tomorrow?",
        'accepted_text': "I'll clear a space behind the counter. Bring two timber and one fitting; the market can pay you 8c.",
        'outcome': "Your shelf protects the next three uncooled spoilage events. It cannot create bread, but it gives us a little more time to sell what we have.",
        'benefit': 'Protects three future bread-spoilage events.',
    },
    'repair_kit': {
        'key': 'repair_kit', 'npc': 'Luca', 'title': 'Nothing worth wasting',
        'bill': {'metal': 2, 'fittings': 1}, 'reward': 9, 'payer': 'parts_shop',
        'intro': "Mely worries when repairs wait on an empty shelf. Help me turn spare metal into a small kit we can keep here for the next breakdown.",
        'accepted_text': "Two metal and one fitting will make three repair parts. I'll pay 9c from the shop when you bring them.",
        'outcome': "We made three repair parts together. I kept the smallest offcut; waste less today, and tomorrow's repair gets easier.",
        'benefit': "Adds three repair parts to Luca's shop.",
    },
    'recovery_salvage': {
        'key': 'recovery_salvage', 'npc': 'Jun', 'title': 'Something left to build with',
        'bill': {'metal': 1, 'fittings': 1}, 'reward': 4, 'payer': 'parts_shop',
        'intro': "Closing the oven hurt. Luca will buy a small salvage kit from us. Could you help me turn spare metal and fittings into a way back?",
        'accepted_text': "Bring one metal and one fitting. Luca pays you 4c and puts 10c into the bakery; he receives two repair parts. Reopening still needs steady orders.",
        'outcome': "Luca bought our two repair parts. Your 4c is paid, and the bakery has 10c more working cash. I still need demand and flour before reopening.",
        'benefit': "Luca receives two parts; Jun receives 10c working cash. Supply cost is 5c; your payment is 4c.",
    },
}


# Keep the original hardship favors separate from the longer authored arcs.
STORY_DEFINITIONS = {
    'mely_bins': {
        'npc': 'Mely', 'title': 'Room for tomorrow', 'chapter': 1, 'arc': 'A fire worth tending',
        'bill': {'timber': 2, 'fittings': 1}, 'reward': 8, 'payer': 'fuel_yard',
        'intro': "Luca says I count tomorrow's orders through supper. Help me sort a small fuel batch, then we can decide what kind of yard I want to run.",
        'accepted_text': "Two timber and one fitting make three fuel bundles and their sorting rack. I'll pay 8c from the yard. This is a first step, not a promise to supply every boiler.",
        'benefit': 'Makes three fuel bundles at the yard; starts Mely\'s three-chapter story.',
        'outcome': "The three bundles are ready. For once I can see tomorrow's work without counting it in my head. Let me try the new routine for a day.",
        'stock_effect': ('fuel_yard', 'fuel', 3),
    },
    'mely_plan': {
        'npc': 'Mely', 'title': 'What the fire is for', 'chapter': 2, 'arc': 'A fire worth tending',
        'previous': 'mely_bins', 'bill': {'timber': 1, 'fittings': 1}, 'reward': 6, 'payer': 'fuel_yard',
        'intro': "The rack helped. Now I have a choice: prepare another small batch for customers, or put some of the yard's earnings aside for our home. Neither choice makes me stop caring about the other.",
        'accepted_text': 'We have chosen a plan together. Bring one timber and one fitting for the order board; the yard pays 6c.',
        'benefit': 'Choose a customer reserve or a household reserve before accepting.',
        'outcome': '',
        'choices': {
            'customers': {'label': 'Customer reserve', 'benefit': 'Make two extra fuel bundles for the yard.', 'stock_effect': ('fuel_yard', 'fuel', 2),
                          'outcome': "We chose to prepare two more fuel bundles for customers. I want reliable work, not endless work. Next I need a way to remember one order while the next comes in."},
            'home': {'label': 'Household reserve', 'benefit': 'The yard transfers 6c to Mely and Luca\'s household.', 'household_payment': 6,
                     'outcome': "We chose to put 6c from the yard into our household savings. That is a real evening I don't have to spend worrying. Next I want a device that remembers an order for me."},
        },
    },
    'mely_memory': {
        'npc': 'Mely', 'title': 'An order I can put down', 'chapter': 3, 'arc': 'A fire worth tending',
        'previous': 'mely_plan', 'certificate': 'memory', 'bill': {'metal': 1, 'fittings': 1}, 'reward': 9, 'payer': 'fuel_yard',
        'intro': "Your memory prototype held a number after the input changed. That is what I needed: a record I can trust while I turn to something else. Help me finish a small batch and mark the end of our trial.",
        'accepted_text': "One metal and one fitting finish the trial's fittings; the yard pays 9c. We will prepare two fuel bundles, then I am going home to Luca.",
        'benefit': 'Completes Mely\'s story; adds two fuel bundles and records the successful memory trial.',
        'outcome': "The memory trial worked, and our last two bundles are ready. I still choose which orders to take. Now I can put one down without feeling I have abandoned it. Luca and I have an evening to ourselves.",
        'stock_effect': ('fuel_yard', 'fuel', 2),
    },
    'luca_sort': {
        'npc': 'Luca', 'title': 'The parts I keep', 'chapter': 1, 'arc': 'Something worth passing on',
        'bill': {'metal': 1, 'fittings': 1}, 'reward': 7, 'payer': 'parts_shop',
        'intro': "Mely calls this shelf a museum of almost-useful things. She is not entirely wrong. Will you help me turn some metal into two repair parts, so I can show her what I mean?",
        'accepted_text': "One metal and one fitting make two repair parts. The shop pays 7c. Then I want to see whether a clearer bench changes the next working day.",
        'benefit': 'Makes two repair parts; starts Luca\'s three-chapter story.',
        'outcome': "Two useful parts, and a clear patch on the bench. Mely noticed before I said a word. I want to try working like this tomorrow.",
        'stock_effect': ('parts_shop', 'parts', 2),
    },
    'luca_share': {
        'npc': 'Luca', 'title': 'A repair worth sharing', 'chapter': 2, 'arc': 'Something worth passing on',
        'previous': 'luca_sort', 'bill': {'timber': 1, 'metal': 1}, 'reward': 6, 'payer': 'parts_shop',
        'intro': "A clear bench made room for a new idea. I can make spare parts for the next customer, or give Dara a shelf that protects bread. Help me choose where this small day's work belongs.",
        'accepted_text': "One timber and one metal are enough for the plan we chose. The shop pays 6c; I will remember who we chose to help.",
        'benefit': 'Choose repair stock or a market pantry shelf before accepting.', 'outcome': '',
        'choices': {
            'repairs': {'label': 'Repair stock', 'benefit': 'Make two repair parts for Luca\'s shop.', 'stock_effect': ('parts_shop', 'parts', 2),
                        'outcome': "We chose two spare repair parts. I like knowing the next customer has a chance. Now I want to count a batch without having to start over whenever somebody speaks to me."},
            'pantry': {'label': 'Dara\'s pantry', 'benefit': 'Protect two future uncooled market spoilage events.', 'pantry_protection': 2,
                       'outcome': "We chose Dara's pantry. Our shelf protects two spoilage events; it cannot fill an empty counter. Next I want to count my batches without losing my place."},
        },
    },
    'luca_counter': {
        'npc': 'Luca', 'title': 'Keeping my place', 'chapter': 3, 'arc': 'Something worth passing on',
        'previous': 'luca_share', 'certificate': 'counter', 'bill': {'metal': 2, 'fittings': 1}, 'reward': 10, 'payer': 'parts_shop',
        'intro': "Your counter remembered each pulse and started fresh when asked. I can talk to a neighbor without losing my place. Let's finish one more batch, then leave the bench ready for tomorrow.",
        'accepted_text': "Two metal and one fitting make three repair parts. The shop pays 10c. Your tested counter is the idea I wanted to learn from.",
        'benefit': 'Completes Luca\'s story; makes three repair parts and records the successful counter trial.',
        'outcome': "Three parts are ready, and the counting trial is in my notebook. Mely says I came home before she had to fetch me. There is something worth passing on here: good work can leave room for people.",
        'stock_effect': ('parts_shop', 'parts', 3),
    },
}
for _key, _definition in STORY_DEFINITIONS.items():
    _definition['key'] = _key
ALL_DEFINITIONS = {**DEFINITIONS, **STORY_DEFINITIONS}


def presentation(village, key):
    definition = ALL_DEFINITIONS[key]
    state = village.character_projects[key]
    choice = definition.get('choices', {}).get(state.get('choice'), {})
    return {**definition, **choice, **state}


def choose(village, key, choice):
    definition = STORY_DEFINITIONS.get(key, {})
    project = village.character_projects.get(key, {})
    if project.get('status') != 'offered' or choice not in definition.get('choices', {}):
        return False, 'Choose a plan before accepting; accepted promises keep their original plan.'
    project['choice'] = choice
    return True, f"Chosen: {definition['choices'][choice]['label']}. Accept when you are ready."


def story_next(village, project):
    if project['status'] != 'completed' or not project.get('chapter'):
        return ''
    next_stage = next((d for d in STORY_DEFINITIONS.values() if d.get('previous') == project['key']), None)
    if next_stage is None:
        return 'Story complete. Your choices remain in the village\'s memories.'
    certificate = next_stage.get('certificate')
    if certificate and certificate not in getattr(village, 'sequential_records', {}):
        goal = 'memory' if certificate == 'memory' else 'counter'
        return f'Next: pass the {goal} timing goal in the workshop, then finish a day.'
    return 'Next: let a working day finish so your neighbor can try the new routine.'


def evaluate_stories(village):
    for key, definition in STORY_DEFINITIONS.items():
        if key in village.character_projects or village.day < 3:
            continue
        previous = village.character_projects.get(definition.get('previous'), {})
        if definition.get('previous') and (previous.get('status') != 'completed' or previous.get('completed_day', village.day) >= village.day):
            continue
        certificate = definition.get('certificate')
        if certificate and certificate not in getattr(village, 'sequential_records', {}):
            continue
        reason = (f"Day {village.day}: a day has passed since the previous promise was kept." if previous else
                  f"Day {village.day}: {definition['npc']} wants to make room for a different way of working.")
        village.character_projects[key] = {'status': 'offered', 'offered_day': village.day, 'reason': reason}
        village.journal.insert(0, f"{definition['npc']}: {definition['title']} (chapter {definition['chapter']}/3).")


def project_for(village, npc):
    """Return a presentation copy, including the authored dialogue and state."""
    projects = [presentation(village, key) for key, definition in ALL_DEFINITIONS.items()
                if definition['npc'] == npc and key in village.character_projects]
    projects.sort(key=lambda p: (p['status'] == 'accepted', p['status'] != 'completed',
                                 p.get('offered_day', 0), p.get('chapter', 0)), reverse=True)
    return projects[0] if projects else None


def evaluate(village):
    """Observe each completed day once; no guessed historical hardship."""
    report = village.last_day_report
    if report.get('day') != village.day or village.character_project_review_day >= village.day:
        return
    village.character_project_review_day = village.day
    meals = report.get('meals', {})
    hungry = any(meal.get('bought', 0) < meal.get('needed', 0) for meal in meals.values())
    produced = report.get('produced', {})
    demand = sum(home['bread_need'] for home in village.households.values())
    bread = sum(produced.get(key, 0) for key, firm in village.businesses.items() if firm['kind'] == 'bakery')
    bread_pressure = demand > 0 and bread < demand
    reasons = ' '.join(str(reason).lower() for reason in report.get('reasons', {}).values())
    parts_short = village.businesses['parts_shop']['stock'].get('parts', 0) == 0
    savings_low = village.households.get('home_3', {}).get('cash', 100) < 24
    jun = village.businesses.get('east_bakery', {})
    food_reason = ('A household missed a meal.' if hungry else
                   f'Bakeries made {bread} loaves for {demand} household meals.')
    repair_reason = ('The repair shelf is empty.' if parts_short else
                     'Mely and Luca have less than 24c in household savings.' if savings_low else
                     'A steam business lost output to a fuel shortage.')
    triggers = {
        'pantry_shelf': (hungry or bread_pressure,
                         f"Day {village.day}: {food_reason}"),
        'repair_kit': (parts_short or savings_low or 'fuel shortage' in reasons,
                       f"Day {village.day}: {repair_reason}"),
        'recovery_salvage': (jun.get('owner', 'Jun') == 'Jun' and jun.get('operating_state') == 'paused',
                             f"Day {village.day}: Jun paused the bakery and is looking for recovery funds."),
    }
    for key, (ready, reason) in triggers.items():
        if ready and key not in village.character_projects:
            village.character_projects[key] = {'status': 'offered', 'offered_day': village.day, 'reason': reason}
            definition = DEFINITIONS[key]
            village.journal.insert(0, f"{definition['npc']} has a personal project: {definition['title']}.")
    evaluate_stories(village)
    village.journal[:] = village.journal[:12]


def accept(village, key):
    definition = ALL_DEFINITIONS.get(key)
    project = village.character_projects.get(key)
    if not definition or not project:
        return 'This project is not available yet.'
    if project['status'] == 'completed':
        return 'This project is already complete.'
    if key == 'recovery_salvage' and (not village.businesses.get('east_bakery') or village.businesses['east_bakery'].get('owner', 'Jun') != 'Jun'):
        return 'Jun has left the village. This request is unavailable until Jun returns.'
    if project['status'] == 'accepted':
        return 'Already accepted. Bring the listed materials when you are ready.'
    if definition.get('choices') and project.get('choice') not in definition['choices']:
        return 'Choose a plan before accepting this promise.'
    project.update(status='accepted', accepted_day=village.day)
    return f"Accepted: {definition['title']}. No materials have been used yet."


def deliver(village, key):
    definition = ALL_DEFINITIONS.get(key)
    project = village.character_projects.get(key)
    if not definition or not project or project['status'] != 'accepted':
        return False, 'Accept this project before delivering; completed projects cannot be paid again.'
    if key == 'recovery_salvage' and (not village.businesses.get('east_bakery') or village.businesses['east_bakery'].get('owner', 'Jun') != 'Jun'):
        return False, 'Jun has left the village. Keep your materials; this promise belongs to Jun.'
    definition = presentation(village, key)
    missing = {good: count - village.material_inventory.get(good, 0)
               for good, count in definition['bill'].items()
               if village.material_inventory.get(good, 0) < count}
    if missing:
        return False, 'Still needed: ' + ', '.join(f'{count} {good}' for good, count in missing.items()) + '.'
    payer = village.businesses[definition['payer']]
    payment = definition['reward'] + (10 if key == 'recovery_salvage' else 0) + definition.get('household_payment', 0)
    if payer['cash'] < payment:
        return False, f"{payer['name']} needs {payment}c to fund this project. Your materials are untouched."
    for good, count in definition['bill'].items():
        village.material_inventory[good] -= count
        village._record_trade('Your Workshop', payer['name'], good, count, 0, purpose=definition['title'])
    payer['cash'] -= payment
    village.coins += definition['reward']
    village._record_trade(payer['name'], 'Your Workshop', 'project work', 1, definition['reward'],
                          purpose=definition['title'])
    if key == 'pantry_shelf':
        payer['pantry_protection'] = payer.get('pantry_protection', 0) + 3
    elif key == 'repair_kit':
        payer['stock']['parts'] = payer['stock'].get('parts', 0) + 3
    elif key == 'recovery_salvage':
        payer['stock']['parts'] = payer['stock'].get('parts', 0) + 2
        jun = village.businesses['east_bakery']
        jun['cash'] += 10
        village._record_trade(payer['name'], jun['name'], 'salvage proceeds', 1, 10,
                              purpose='Working capital from the recovery kit')
    if key in STORY_DEFINITIONS:
        if definition.get('stock_effect'):
            firm, good, count = definition['stock_effect']
            stock = village.businesses[firm]['stock']
            stock[good] = stock.get(good, 0) + count
        if definition.get('pantry_protection'):
            market = village.businesses['market']
            market['pantry_protection'] = market.get('pantry_protection', 0) + definition['pantry_protection']
        if definition.get('household_payment'):
            amount = definition['household_payment']
            village.households['home_3']['cash'] += amount
            village._record_trade(payer['name'], 'Mely and Luca household', 'household reserve', 1, amount,
                                  purpose=definition['title'])
        if definition.get('certificate'):
            project['certificate'] = definition['certificate']
    project.update(status='completed', completed_day=village.day, outcome=definition['outcome'], trust=8)
    person = next((person for person in village.citizens if person['name'] == definition['npc']), None)
    if person:
        person['relationships']['Boole'] = min(100, person['relationships'].get('Boole', 20) + 8)
        person['memories'] = (person.get('memories', []) + [f"Day {village.day}: Boole helped with {definition['title']}."])[-6:]
    village.journal.insert(0, f"{definition['npc']}: {definition['title']} completed. {definition['benefit']}")
    village.journal[:] = village.journal[:12]
    return True, f"{definition['title']} complete. Paid {definition['reward']}c. {definition['benefit']}"
