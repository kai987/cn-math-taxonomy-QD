import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location('question_validator', ROOT / 'scripts/validate.py')
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)
TOPICS = {topic['id']: topic for topic in json.loads((ROOT / 'data/topics.json').read_text())}
QUESTIONS = json.loads((ROOT / 'data/questions.json').read_text())


class QuestionSchemaTests(unittest.TestCase):
    def errors(self, question):
        return VALIDATOR.question_errors([question], TOPICS, require_coverage=False)[0]

    def test_confirmed_variable_contracts_are_valid(self):
        annotated = [question for question in QUESTIONS if 'variables' in question]
        self.assertGreaterEqual(len(annotated), 1)
        for question in annotated:
            with self.subTest(id=question['id']):
                self.assertEqual(self.errors(question), [])

    def test_variable_contract_rejects_duplicates_empty_wrong_length_and_type(self):
        source = next(question for question in QUESTIONS if question['id'] == 'cnm_089_q2')
        for names in ([], ['x', 'x'], ['x'], ['X', 'y'], ['x', ''], ['x', 2], 'x,y', None):
            with self.subTest(names=names):
                question = {**source, 'variables': names}
                self.assertTrue(any('variables' in error for error in self.errors(question)))

    def test_variable_contract_is_not_allowed_on_unordered_or_short_questions(self):
        source = next(question for question in QUESTIONS if question['id'] == 'cnm_089_q2')
        for patch in ({'unordered': True}, {'type': 'short'}):
            with self.subTest(patch=patch):
                self.assertTrue(any('variables' in error for error in self.errors({**source, **patch})))

    def test_expected_unit_rejects_non_numeric_and_empty_or_non_string_units(self):
        source = next(question for question in QUESTIONS if question['id'] == 'cnm_p041_q2')
        for unit in ('', [], 10, None):
            with self.subTest(unit=unit):
                self.assertTrue(any('unit' in error for error in self.errors({**source, 'unit': unit})))
        self.assertTrue(any('unit' in error for error in self.errors({**source, 'type': 'short'})))


if __name__ == '__main__':
    unittest.main()
