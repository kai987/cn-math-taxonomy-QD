import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from check_remaining_43 import PATH, review_errors
from math_models import MODEL_PATH


class Remaining43Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.questions = json.loads((ROOT / 'data/questions.json').read_text())
        cls.topics = json.loads((ROOT / 'data/topics.json').read_text())
        cls.review = json.loads(PATH.read_text())
        cls.records = json.loads(MODEL_PATH.read_text())['models']

    def test_all_original43_have_current_evidence(self):
        self.assertEqual(review_errors(self.questions, self.review, self.records, self.topics), [])

    def test_scope_baseline_and_summary_cannot_drift(self):
        for mutation in ('drop', 'duplicate', 'replace', 'baseline', 'counts'):
            review = copy.deepcopy(self.review)
            if mutation == 'drop': review['entries'].pop()
            elif mutation == 'duplicate': review['entries'][0] = copy.deepcopy(review['entries'][1])
            elif mutation == 'replace': review['entries'][0]['id'] = 'cnm_p001_q1'
            elif mutation == 'baseline': review['baseline_commit'] = '0'*40
            else: review['summary']['reviewed'] = 42
            with self.subTest(mutation=mutation):
                self.assertTrue(review_errors(self.questions, review, self.records))

    def test_reference_wording_and_formal_models_require_re_review(self):
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

    def test_free_design_or_nonexecuted_notes_are_not_full_proofs(self):
        for mutation in ('status', 'note'):
            review = copy.deepcopy(self.review)
            entry = next(e for e in review['entries'] if e['id'] == 'cnm_315_q1')
            if mutation == 'status': entry['status'] = 'model'
            else: entry.setdefault('supporting_proofs', []).append({'meaning': 'not an executable proof'})
            with self.subTest(mutation=mutation):
                self.assertTrue(review_errors(self.questions, review, self.records))

    def test_manual_limits_must_say_what_is_missing_and_when_to_revisit(self):
        for field in ('category', 'missing_basis', 'revisit_if'):
            review = copy.deepcopy(self.review)
            entry = next(e for e in review['entries'] if e['status'] == 'manual')
            entry['automation_gap'].pop(field)
            with self.subTest(field=field):
                self.assertTrue(review_errors(self.questions, review, self.records))


if __name__ == '__main__': unittest.main()
