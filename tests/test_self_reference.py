"""Offline reference verification never becomes an automatic prose grader."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from model_types import SelfReferenceProof, TextProof
from math_models import evaluate
from verify_questions import compare_self_reference, verify_all


class SelfReferenceContractTests(unittest.TestCase):
    def test_proof_contract_is_abstract_and_plain_text_is_not_mathematics(self):
        with self.assertRaises(TypeError):
            SelfReferenceProof()
        for result in ('参考答案', TextProof('参考答案'), 3, True):
            self.assertFalse(compare_self_reference({'answer': '参考答案'}, result)[0])

    def test_plain_expression_and_cross_question_calls_cannot_verify_self(self):
        for expression in ("'参考答案'", '1+2', "model('cnm_999_q1')"):
            with self.subTest(expression=expression), patch('verify_questions.safe_eval') as evaluator:
                result = verify_all([{'id': 'cnm_003_q1', 'type': 'self', 'answer': '参考答案', 'verify': expression}])
                self.assertEqual(result['auto_verified'], [])
                self.assertEqual(len(result['mismatch']), 1)
                evaluator.assert_not_called()

    def test_unmodelled_self_remains_explicitly_unverified(self):
        result = verify_all([{'id': 'cnm_315_q1', 'type': 'self', 'answer': '自由设计'}])
        self.assertEqual(result['unverifiable'], ['cnm_315_q1'])
        self.assertEqual(result['auto_verified'], [])

    def test_every_complete_self_model_checks_all_reference_claims(self):
        questions = {q['id']: q for q in json.loads((ROOT / 'data/questions.json').read_text())}
        models = json.loads((ROOT / 'data/verification_models.json').read_text())['models']
        checked = 0
        for qid, record in models.items():
            question = questions[qid]
            if question['type'] != 'self':
                continue
            checked += 1
            proof = evaluate(record['spec'])
            with self.subTest(id=qid):
                self.assertIsInstance(proof, SelfReferenceProof)
                self.assertTrue(compare_self_reference(question, proof)[0])
                for text in ('', '错误的参考答案', question['answer'] + '；另有未经核验的结论'):
                    self.assertFalse(compare_self_reference({**question, 'answer': text}, proof)[0])
                self.assertFalse(compare_self_reference({**question, 'accept': ['错误的参考答案']}, proof)[0])
        self.assertGreaterEqual(checked, 1)


if __name__ == '__main__':
    unittest.main()
