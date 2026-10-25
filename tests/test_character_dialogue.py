"""Character voices react to evidence and to the player's actual promises."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
import unittest
from unittest.mock import patch
import pygame
from dialogue import conversation, HARDSHIP_VOICES
from economy import Village


class CharacterDialogueTests(unittest.TestCase):
    def test_random_choice_is_stable_until_reload_and_preserves_live_details(self):
        from game import village_from_data
        village = Village()
        with patch('dialogue.random.choice', side_effect=lambda choices: choices[-1]) as choose:
            before = conversation(village, 'Ada', 'work')
            self.assertEqual(conversation(village, 'Ada', 'work'), before)
            self.assertEqual(choose.call_count, 1)
        loaded = village_from_data(vars(village))
        with patch('dialogue.random.choice', side_effect=lambda choices: choices[0]) as choose:
            after = conversation(loaded, 'Ada', 'work')
            self.assertEqual(choose.call_count, 1)
        self.assertNotEqual(before[0], after[0])
        self.assertEqual(before[1], after[1])

    def test_each_resident_has_a_distinct_reaction_to_a_closed_shop(self):
        village = Village()
        village.businesses['east_bakery'] = {'operating_state': 'paused', 'owner_decision': 'Waiting for supplies.'}
        lines = [conversation(village, person['name'], 'town')[0] for person in village.citizens]
        self.assertEqual(len(lines), len(set(lines)))
        self.assertIn('paying customers', conversation(village, 'Grace', 'town')[0])

    def test_delivery_acknowledgement_names_the_actual_builder(self):
        village = Village()
        village.offers['mill']['status'] = 'player'
        self.assertIn('You got the mill', conversation(village, 'Bram', 'work')[1])
        village.offers['mill'].update(status='rival', design_owner='Grace')
        self.assertIn('Grace got the mill', conversation(village, 'Bram', 'work')[1])

    def test_request_dialogue_distinguishes_offer_promise_and_completion(self):
        village = Village()
        project = {'status': 'offered', 'intro': 'I need a shelf.',
                   'accepted_text': 'You promised a shelf.', 'outcome': 'The shelf is finished.'}
        with patch('character_projects.project_for', return_value=project):
            for state, expected in [('offered', 'I need a shelf.'), ('accepted', 'You promised a shelf.'),
                                    ('completed', 'The shelf is finished.')]:
                project['status'] = state
                self.assertEqual(conversation(village, 'Dara', 'work')[1], expected)
                self.assertEqual(conversation(village, 'Dara', 'hopes')[1], expected)

    def test_authored_conversation_paragraphs_fit_the_dialogue_panel(self):
        from game import PixelFont
        from character_projects import DEFINITIONS
        pygame.init()
        font = PixelFont(18)
        village = Village()
        paragraphs = []
        for person in village.citizens:
            for topic in ('work', 'family', 'town', 'hopes'):
                paragraphs.extend(conversation(village, person['name'], topic))
        for day in range(1, 5):
            village.day = day
            for name in ('Luca', 'Mely', 'Grace'):
                for topic in ('work', 'family', 'town', 'hopes'):
                    paragraphs.extend(conversation(village, name, topic))
        from dialogue import PERSONAL_LINES, SHOP_GREETINGS
        for topics in PERSONAL_LINES.values():
            for choices in topics.values():
                paragraphs.extend(choices)
        paragraphs.extend(SHOP_GREETINGS.values())
        paragraphs.extend(HARDSHIP_VOICES.values())
        for definition in DEFINITIONS.values():
            paragraphs.extend(definition[field] for field in ('intro', 'accepted_text', 'outcome'))
        for paragraph in paragraphs:
            lines, current = 1, ''
            for word in paragraph.split():
                candidate = (current + ' ' + word).strip()
                if font.render(candidate, True, (0, 0, 0)).get_width() > 750:
                    lines += 1
                    current = word
                else:
                    current = candidate
            self.assertLessEqual(lines, 3, paragraph)
        pygame.quit()
