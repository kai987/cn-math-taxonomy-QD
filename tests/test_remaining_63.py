import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from check_remaining_63 import PATH, review_errors
from math_models import MODEL_PATH


class Remaining63Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.questions = json.loads((ROOT / 'data/questions.json').read_text())
        cls.topics = json.loads((ROOT / 'data/topics.json').read_text())
        cls.review = json.loads(PATH.read_text())
        cls.records = json.loads(MODEL_PATH.read_text())['models']

    def test_original_63_references_and_boundaries_are_current(self):
        self.assertEqual(review_errors(self.questions, self.review, self.records, self.topics), [])

    def test_scope_baseline_and_counts_cannot_silently_change(self):
        for mutation in ('drop', 'duplicate', 'replace', 'baseline', 'counts'):
            review = copy.deepcopy(self.review)
            if mutation == 'drop': review['entries'].pop()
            elif mutation == 'duplicate': review['entries'][0] = copy.deepcopy(review['entries'][1])
            elif mutation == 'replace': review['entries'][0]['id'] = 'cnm_p001_q1'
            elif mutation == 'baseline': review['baseline_commit'] = '0'*40
            else: review['summary']['reviewed'] = 62
            with self.subTest(mutation=mutation):
                self.assertTrue(review_errors(self.questions, review, self.records))

    def test_source_reference_and_model_semantics_require_a_new_review(self):
        entry = self.review['entries'][0]
        for field in ('prompt', 'answer'):
            questions = copy.deepcopy(self.questions)
            next(q for q in questions if q['id'] == entry['id'])[field] += 'changed'
            with self.subTest(field=field):
                self.assertTrue(review_errors(questions, self.review, self.records))
        for entry in self.review['entries']:
            if entry['status'] == 'model':
                records = copy.deepcopy(self.records)
                records[entry['id']]['spec']['unreviewed_condition'] = 1
                self.assertTrue(review_errors(self.questions, self.review, records))
                break

    def test_open_response_or_note_cannot_be_promoted_to_mathematical_proof(self):
        for mutation in ('status', 'note'):
            review = copy.deepcopy(self.review)
            entry = next(e for e in review['entries'] if e['id'] == 'cnm_315_q1')
            if mutation == 'status': entry['status'] = 'model'
            else: entry.setdefault('supporting_proofs', []).append({'meaning': 'not executable'})
            with self.subTest(mutation=mutation):
                self.assertTrue(review_errors(self.questions, review, self.records))


if __name__ == '__main__': unittest.main()
