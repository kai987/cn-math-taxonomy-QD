import copy
from fractions import Fraction
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from math_models import MODEL_PATH, binding_errors, evaluate
from check_remaining_review import PATH, review_errors
from verify_questions import compare_choice, compare_numeric, compare_short, safe_eval, num_equal

ROOT = Path(__file__).resolve().parents[1]


class MathematicalModelsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.questions = json.loads((ROOT / 'data/questions.json').read_text())
        cls.by_id = {q['id']: q for q in cls.questions}
        cls.records = json.loads(MODEL_PATH.read_text())['models']
        cls.review = json.loads(PATH.read_text())

    def test_every_model_is_current_and_every_followup_has_a_concrete_outcome(self):
        self.assertEqual(review_errors(self.questions, self.review, self.records), [])

    def test_independent_models_reject_every_alternative_answer_key(self):
        for qid, record in self.records.items():
            question = self.by_id[qid]
            result = evaluate(record['spec'])
            with self.subTest(id=qid):
                comparator = {'choice': compare_choice, 'numeric': compare_numeric, 'short': compare_short}[question['type']]
                self.assertTrue(comparator(question, result)[0])
                if question['type'] == 'choice':
                    for option in question['choices']:
                        if option['key'] != question['answer']:
                            self.assertFalse(compare_choice({**question, 'answer': option['key']}, result)[0])
                elif question['type'] == 'short':
                    self.assertFalse(compare_short({**question, 'answer': '错误的参考值'}, result)[0])
                    self.assertFalse(compare_short({**question, 'accept': question.get('accept', []) + ['错误的参考值']}, result)[0])
                else:
                    parts = question['answer'].replace('，', ',').split(',')
                    parts[0] = str(Fraction(parts[0]) + 1)
                    self.assertFalse(compare_numeric({**question, 'answer': ','.join(parts)}, result)[0])

    def test_missing_cross_question_stale_or_answer_filled_inputs_fail(self):
        qid = next(iter(self.records))
        for mutation in ('stale', 'answer', 'missing', 'cross'):
            with self.subTest(mutation=mutation):
                records = copy.deepcopy(self.records)
                questions = copy.deepcopy(self.questions)
                if mutation == 'stale':
                    records[qid]['question_sha256'] = '0'*64
                elif mutation == 'answer':
                    records[qid]['spec']['answer'] = self.by_id[qid]['answer']
                elif mutation == 'missing':
                    del records[qid]
                else:
                    next(q for q in questions if q['id'] == qid)['verify'] = "model('cnm_999_q1')"
                self.assertTrue(binding_errors(questions, records))

    def test_model_input_mutations_require_re_review(self):
        records = copy.deepcopy(self.records)
        qid = next(iter(records))
        records[qid]['spec']['reviewed_assumption_changed'] = True
        self.assertTrue(any('model semantics changed' in e for e in review_errors(self.questions, self.review, records)))

    def test_manual_outcome_cannot_be_removed_or_mislabeled_automatic(self):
        review = copy.deepcopy(self.review)
        entry = next(e for e in review['entries'] if e['status'] == 'manual')
        entry['status'] = 'model'
        self.assertTrue(review_errors(self.questions, review, self.records))
        review['entries'].pop()
        self.assertTrue(review_errors(self.questions, review, self.records))

    def test_open_response_components_are_checked_without_grading_the_whole_response(self):
        checked = 0
        for entry in self.review['entries']:
            for proof in entry.get('supporting_proofs', []):
                checked += 1
                with self.subTest(id=entry['id'], expression=proof['expression']):
                    self.assertEqual(entry['status'], 'manual')
                    actual = safe_eval(proof['expression'])
                    expected = proof['value']
                    if proof.get('comparison') == 'lt':
                        self.assertLess(actual, Fraction(expected))
                    else:
                        actuals = list(actual) if isinstance(actual, (list, tuple)) else [actual]
                        expecteds = expected if isinstance(expected, list) else [expected]
                        self.assertEqual(len(actuals), len(expecteds))
                        self.assertTrue(all(num_equal(Fraction(str(e)), a) for a, e in zip(actuals, expecteds)))
        self.assertGreaterEqual(checked, 6)


if __name__ == '__main__':
    unittest.main()
