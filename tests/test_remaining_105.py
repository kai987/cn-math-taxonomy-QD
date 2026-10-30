import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from check_remaining_105 import PATH, review_errors
from math_models import MODEL_PATH


class Remaining105Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.questions = json.loads((ROOT / 'data/questions.json').read_text())
        cls.topics = json.loads((ROOT / 'data/topics.json').read_text())
        cls.review = json.loads(PATH.read_text())
        cls.records = json.loads(MODEL_PATH.read_text())['models']

    def test_all_original_105_have_current_reference_and_proof_boundaries(self):
        self.assertEqual(review_errors(self.questions, self.review, self.records, self.topics), [])

    def test_scope_baseline_and_summary_cannot_drift(self):
        for mutation in ('drop', 'duplicate', 'replace', 'baseline', 'summary'):
            review = copy.deepcopy(self.review)
            if mutation == 'drop': review['entries'].pop()
            elif mutation == 'duplicate': review['entries'][0] = copy.deepcopy(review['entries'][1])
            elif mutation == 'replace': review['entries'][0]['id'] = 'cnm_p001_q1'
            elif mutation == 'baseline': review['baseline_commit'] = '0'*40
            else: review['summary']['outcomes'] = {'model': 105}
            with self.subTest(mutation=mutation):
                self.assertTrue(review_errors(self.questions, review, self.records))

    def test_reference_source_and_mathematical_assumptions_require_re_review(self):
        entry = next(e for e in self.review['entries'] if e['status'] == 'model')
        for mutation in ('prompt', 'answer', 'spec'):
            questions, records = copy.deepcopy(self.questions), copy.deepcopy(self.records)
            if mutation == 'spec': records[entry['id']]['spec']['changed_premise'] = 'not reviewed'
            else: next(q for q in questions if q['id'] == entry['id'])[mutation] += 'changed'
            with self.subTest(mutation=mutation):
                self.assertTrue(review_errors(questions, self.review, records))

    def test_unchecked_partial_notes_or_open_prose_cannot_be_full_proofs(self):
        for mutation in ('whole', 'partial'):
            review = copy.deepcopy(self.review)
            entry = next(e for e in review['entries'] if e['id'] == 'cnm_315_q1')
            if mutation == 'whole': entry['status'] = 'model'
            else: entry.setdefault('supporting_proofs', []).append({'verify': '3+4', 'meaning': '7'})
            with self.subTest(mutation=mutation):
                self.assertTrue(review_errors(self.questions, review, self.records))


if __name__ == '__main__': unittest.main()
