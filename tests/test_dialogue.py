import unittest
from economy import Village
from dialogue import conversation


class DialogueTests(unittest.TestCase):
    def test_household_dialogue_reflects_food_and_savings(self):
        village = Village()
        home = village.households['home_1']
        home.update(cash=7, bought=0)
        self.assertIn('7c', ' '.join(conversation(village, 'Ada', 'family')))
        home['bought'] = home['bread_need']
        self.assertIn("We've eaten", ' '.join(conversation(village, 'Ada', 'family')))

    def test_distinct_voices_and_trust_dependent_hopes(self):
        village = Village()
        names = [p['name'] for p in village.citizens] + ['Grace']
        self.assertEqual(len({conversation(village, name, 'work')[0] for name in names}), len(names))
        person = village.citizens[0]
        before = conversation(village, person['name'], 'hopes')
        person['relationships']['Boole'] = 40
        after = conversation(village, person['name'], 'hopes')
        self.assertNotEqual(before, after)
        self.assertEqual(before[0], after[0])

    def test_grace_speaks_job_keys_as_words(self):
        village = Village()
        for offer in village.offers.values():
            offer['status'] = 'available'
        village.offers['parts_selector'] = {'status': 'bid'}
        line = conversation(village, 'Grace', 'work')[0]
        self.assertIn('parts selector job', line)
        self.assertNotIn('_', line)

    def test_recent_growth_and_grace_bid_are_visible(self):
        village = Village()
        village.migration_events.append({'message': 'A cottage is under construction.'})
        self.assertIn('under construction', ' '.join(conversation(village, 'Agnes', 'town')))
        village.offers['mill']['status'] = 'bid'
        self.assertIn('building the mill', ' '.join(conversation(village, 'Grace', 'work')))
