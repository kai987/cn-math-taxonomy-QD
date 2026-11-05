"""Review evidence must never silently restore grading by a preference letter."""
import copy
import hashlib
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from check_remaining_review import review_errors
from math_models import signature


def fixture():
    question = {
        'id': 'cnm_105_q1', 'type': 'choice', 'prompt': 'Choose a representation.',
        'answer': 'A', 'self_assess': True,
        'choices': [{'key': 'A', 'text': 'Reference recommendation'},
                    {'key': 'B', 'text': 'Another usable representation'},
                    {'key': 'C', 'text': 'A context-dependent representation'}],
    }
    entry = {
        'id': question['id'], 'question_sha256': signature(question), 'status': 'manual',
        'derivation': 'The reference is a conditional recommendation, not a unique optimum.',
        'boundary': 'A selected letter alone does not prove or disprove understanding.',
        'grading': [{'input': key, 'result': 'manual'} for key in 'ABC'],
    }
    return question, {'entries': [entry]}


def errors(question, review):
    digest = hashlib.sha256(question['id'].encode()).hexdigest()
    return review_errors([question], review, {}, scope_count=1, scope_sha256=digest)


class SelfAssessedChoiceReviewTests(unittest.TestCase):
    def test_reference_and_other_selections_all_stay_manual(self):
        question, review = fixture()
        self.assertEqual(errors(question, review), [])

    def test_reference_letter_cannot_revert_to_correct_or_other_letter_to_wrong(self):
        for index, result in ((0, 'correct'), (1, 'wrong'), (2, 'correct')):
            question, review = fixture()
            review['entries'][0]['grading'][index]['result'] = result
            with self.subTest(index=index, result=result):
                self.assertTrue(any('self-assessed choice' in error for error in errors(question, review)))

    def test_grading_evidence_is_required_and_cannot_be_an_empty_or_invalid_container(self):
        for value in (None, [], {}, 'manual'):
            question, review = fixture()
            review['entries'][0]['grading'] = value
            with self.subTest(value=value):
                self.assertTrue(any('self-assessed choice' in error for error in errors(question, review)))
        question, review = fixture()
        review['entries'][0].pop('grading')
        self.assertTrue(any('self-assessed choice' in error for error in errors(question, review)))

    def test_every_case_needs_string_input_and_a_manual_result(self):
        malformed = [None, [], 'manual', {'input': 1, 'result': 'manual'},
                     {'input': None, 'result': 'manual'}, {'result': 'manual'},
                     {'input': 'B'}, {'input': 'B', 'result': None},
                     {'input': 'B', 'result': 'unknown'}]
        for case in malformed:
            question, review = fixture()
            # A valid earlier example cannot hide a malformed later example.
            review['entries'][0]['grading'].append(copy.deepcopy(case))
            with self.subTest(case=case):
                self.assertTrue(any('self-assessed choice' in error for error in errors(question, review)))

    def test_ordinary_unverified_choice_does_not_implicitly_become_self_assessed(self):
        question, review = fixture()
        question.pop('self_assess')
        entry = review['entries'][0]
        entry['question_sha256'] = signature(question)
        entry['grading'] = [{'input': 'A', 'result': 'correct'}, {'input': 'B', 'result': 'wrong'}]
        self.assertEqual(errors(question, review), [])

    def test_self_assessed_choice_does_not_use_the_free_response_reference_proof_contract(self):
        question, review = fixture()
        with patch('math_models.evaluate', side_effect=AssertionError('no prose proof for a choice')):
            self.assertEqual(errors(question, review), [])
        review['entries'][0]['reference_only'] = True
        self.assertTrue(any('reserved for self reference models' in error for error in errors(question, review)))

    def test_existing_free_response_grading_rule_still_requires_manual(self):
        question, review = fixture()
        question.pop('self_assess')
        question['type'] = 'self'
        entry = review['entries'][0]
        entry['question_sha256'] = signature(question)
        self.assertEqual(errors(question, review), [])
        entry['grading'][0]['result'] = 'correct'
        self.assertTrue(any('free-response grading' in error for error in errors(question, review)))


if __name__ == '__main__':
    unittest.main()
