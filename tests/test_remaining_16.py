"""Fixed16 scope, source bindings, complete proofs and manual boundaries."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from check_remaining_16 import PATH, review_errors
from math_models import MODEL_PATH


class Remaining16Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.questions = json.loads((ROOT / 'data/questions.json').read_text())
        cls.by_id = {q['id']: q for q in cls.questions}
        cls.topics = json.loads((ROOT / 'data/topics.json').read_text())
        cls.review = json.loads(PATH.read_text())
        cls.records = json.loads(MODEL_PATH.read_text())['models']

    def test_every_original_question_has_current_evidence(self):
        self.assertEqual(review_errors(self.questions, self.review, self.records, self.topics), [])

    def test_scope_baseline_and_summary_cannot_drift(self):
        for mutation in ('drop', 'duplicate', 'replace', 'baseline', 'counts', 'self_count'):
            review = copy.deepcopy(self.review)
            if mutation == 'drop': review['entries'].pop()
            elif mutation == 'duplicate': review['entries'][0] = copy.deepcopy(review['entries'][1])
            elif mutation == 'replace': review['entries'][0]['id'] = 'cnm_p001_q1'
            elif mutation == 'baseline': review['baseline_commit'] = '0' * 40
            elif mutation == 'self_count': review['summary']['self_reference_models'] = -1
            else: review['summary']['reviewed'] = 15
            with self.subTest(mutation=mutation):
                self.assertTrue(review_errors(self.questions, review, self.records))

    def test_reference_source_and_formal_semantics_require_re_review(self):
        qid = self.review['entries'][0]['id']
        for field in ('prompt', 'answer'):
            questions = copy.deepcopy(self.questions)
            next(q for q in questions if q['id'] == qid)[field] += 'changed'
            with self.subTest(field=field):
                self.assertTrue(review_errors(questions, self.review, self.records))
        for entry in self.review['entries']:
            if entry['status'] == 'model':
                records = copy.deepcopy(self.records)
                records[entry['id']]['spec']['unreviewed_condition'] = 1
                self.assertTrue(review_errors(self.questions, self.review, records))

    def test_partial_components_are_not_complete_proofs_or_unexecuted_notes(self):
        for mutation in ('status', 'note'):
            review = copy.deepcopy(self.review)
            entry = next(e for e in review['entries'] if e['status'] == 'manual')
            if mutation == 'status': entry['status'] = 'model'
            else: entry.setdefault('supporting_proofs', []).append({'meaning': 'not an executable proof'})
            with self.subTest(mutation=mutation):
                self.assertTrue(review_errors(self.questions, review, self.records))

    def test_each_manual_reference_identifies_its_gap_and_revisit_condition(self):
        for field in ('category', 'missing_basis', 'revisit_if'):
            review = copy.deepcopy(self.review)
            entry = next(e for e in review['entries'] if e['status'] == 'manual')
            entry['automation_gap'].pop(field)
            with self.subTest(field=field):
                self.assertTrue(review_errors(self.questions, review, self.records))

    def test_all_self_grading_stays_manual_with_or_without_a_reference_model(self):
        for original in self.review['entries']:
            if self.by_id[original['id']]['type'] != 'self':
                continue
            review = copy.deepcopy(self.review)
            entry = next(e for e in review['entries'] if e['id'] == original['id'])
            entry['grading'][0]['result'] = 'correct'
            with self.subTest(id=original['id']):
                self.assertTrue(review_errors(self.questions, review, self.records))
            if original['status'] == 'model':
                review = copy.deepcopy(self.review)
                next(e for e in review['entries'] if e['id'] == original['id']).pop('reference_only')
                self.assertTrue(review_errors(self.questions, review, self.records))


if __name__ == '__main__': unittest.main()
