import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from check_manual_review import PATH, review_errors, check_supporting_proof
from math_models import MODEL_PATH


class ManualReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.questions = json.loads((ROOT / 'data/questions.json').read_text())
        cls.topics = json.loads((ROOT / 'data/topics.json').read_text())
        cls.review = json.loads(PATH.read_text())
        cls.records = json.loads(MODEL_PATH.read_text())['models']

    def test_all_original_160_references_have_current_evidence(self):
        self.assertEqual(review_errors(self.questions, self.review, self.records, self.topics), [])

    def test_scope_cannot_shrink_duplicate_or_replace_an_item(self):
        for mutation in ('drop', 'duplicate', 'replace'):
            review = copy.deepcopy(self.review)
            if mutation == 'drop':
                review['entries'].pop()
            elif mutation == 'duplicate':
                review['entries'][0] = copy.deepcopy(review['entries'][1])
            else:
                review['entries'][0]['id'] = 'cnm_p001_q1'
            with self.subTest(mutation=mutation):
                self.assertTrue(review_errors(self.questions, review, self.records))

    def test_new_wording_reference_or_model_requires_re_review(self):
        model_entry = next(e for e in self.review['entries'] if e['status'] == 'model')
        for mutation in ('prompt', 'answer', 'spec'):
            questions, records = copy.deepcopy(self.questions), copy.deepcopy(self.records)
            if mutation == 'spec':
                records[model_entry['id']]['spec']['changed_assumption'] = 1
            else:
                question = next(q for q in questions if q['id'] == model_entry['id'])
                question[mutation] += 'changed'
            with self.subTest(mutation=mutation):
                self.assertTrue(review_errors(questions, self.review, records))

    def test_self_components_cannot_promote_whole_question_to_automatic(self):
        review = copy.deepcopy(self.review)
        entry = next(e for e in review['entries'] if e['id'] == 'cnm_315_q1')
        entry['status'] = 'model'
        self.assertTrue(review_errors(self.questions, review, self.records))

    def test_counts_are_derived_from_entries_including_partial_proofs(self):
        for field in ('reviewed', 'outcomes', 'remaining_by_type', 'models_by_kind',
                      'repaired_questions', 'component_checks'):
            review = copy.deepcopy(self.review)
            review['summary'][field] = None
            with self.subTest(field=field):
                self.assertTrue(any(field in e for e in review_errors(self.questions, review, self.records)))

    def test_every_open_response_component_runs_independently(self):
        checked = 0
        for entry in self.review['entries']:
            for proof in entry.get('supporting_proofs', []):
                checked += 1
                self.assertEqual(entry['status'], 'manual')
                with self.subTest(id=entry['id'], expression=proof['expression']):
                    check_supporting_proof(proof)
        self.assertGreaterEqual(checked, 13)

    def test_partial_component_cannot_be_an_unexecuted_note_or_wrong_result(self):
        for proof in ({'verify': '3+4', 'meaning': '7'},
                      {'expression': '3+4', 'value': 8},
                      {'expression': "poly('x+x')", 'value': 'x', 'comparison': 'polynomial'}):
            with self.subTest(proof=proof), self.assertRaises((ValueError, KeyError)):
                check_supporting_proof(proof)


if __name__ == '__main__':
    unittest.main()
