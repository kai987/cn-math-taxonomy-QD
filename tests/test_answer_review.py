import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from check_answer_review import REVIEW_PATH, review_errors
from verify_questions import verify_all


class AnswerReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.questions = json.loads((ROOT / 'data/questions.json').read_text())
        cls.review = json.loads(REVIEW_PATH.read_text())
        cls.topics = json.loads((ROOT / 'data/topics.json').read_text())

    def test_all_532_independently_reviewed_records_match_current_questions(self):
        self.assertEqual(review_errors(self.questions, self.review, self.topics), [])

    def test_repaired_catalogue_reference_cannot_revert_independently(self):
        topics = copy.deepcopy(self.topics)
        topic = next(t for t in topics if t['id'] == 'cnm_315')
        topic['diagnostic_question']['answer'] = '有限次试验接近1/2就证明公平'
        self.assertTrue(any('catalogue preview' in error for error in review_errors(self.questions, self.review, topics)))

    def test_cannot_drop_duplicate_or_replace_a_reviewed_question(self):
        for mutation in ('drop', 'duplicate', 'replace'):
            with self.subTest(mutation=mutation):
                review = copy.deepcopy(self.review)
                if mutation == 'drop':
                    review['entries'].pop()
                elif mutation == 'duplicate':
                    review['entries'][0] = review['entries'][1]
                else:
                    review['entries'][0]['id'] = 'cnm_p001_q1'
                self.assertTrue(review_errors(self.questions, review))

    def test_prompt_option_reference_and_grading_changes_require_review(self):
        original = next(q for q in self.questions if q['id'] == 'cnm_001_q2')
        for mutation in ('prompt', 'option', 'answer', 'accept'):
            with self.subTest(mutation=mutation):
                questions = copy.deepcopy(self.questions)
                question = next(q for q in questions if q['id'] == original['id'])
                if mutation == 'option':
                    question['choices'][0]['text'] += '修改'
                elif mutation == 'accept':
                    question['accept'] = ['错误答案']
                else:
                    question[mutation] += '修改'
                self.assertTrue(any(original['id'] in error for error in review_errors(questions, self.review)))

    def test_every_current_computational_reference_passes_independent_expression(self):
        result = verify_all(self.questions)
        self.assertEqual(result['expression_errors'], [])
        self.assertEqual(result['mismatch'], [])


if __name__ == '__main__':
    unittest.main()
