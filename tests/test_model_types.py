from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from model_types import TextProof, plain, select_unique


class ModelTypesTests(unittest.TestCase):
    def test_relations_preserve_variable_sign_strictness_and_direction(self):
        result = TextProof(('x', '≤', '3'), 'relation')
        for value in ('x<=3', '3≥x', 'x≤3.0'):
            self.assertTrue(result.matches(value))
        for value in ('x<3', 'x≥3', 'y≤3', '3≤x', 'x≤3!', 'x≤3..'):
            self.assertFalse(result.matches(value))
        self.assertTrue(TextProof(('m', '≠', 1), 'relation').matches('m不等于1'))
        self.assertFalse(TextProof(('m', '≠', 1), 'relation').matches('m等于1'))

    def test_coordinates_preserve_order_and_exact_rational_values(self):
        result = TextProof([(0, 4), (2, 0)], 'coordinates')
        for text in ('(0,4)，(2,0)', '（0,4）和（2,0）', '(0,8/2),(2,0)'):
            self.assertTrue(result.matches(text))
        for text in ('(2,0),(0,4)', '(0,4),,(2,0)', '[0,4],[2,0]', '(0,4.00000000000000001),(2,0)'):
            self.assertFalse(result.matches(text))

    def test_word_and_colour_aliases_do_not_swallow_negation_or_reorder(self):
        self.assertTrue(TextProof('是', 'like_terms').matches('是同类项'))
        self.assertFalse(TextProof('是', 'like_terms').matches('是方程的解'))
        self.assertTrue(TextProof('是', 'equation_solution').matches('是方程的解'))
        self.assertFalse(TextProof('是', 'equation_solution').matches('是同类项'))
        self.assertFalse(TextProof('是', 'word').matches('不是'))
        self.assertTrue(TextProof('EDF', 'word').matches('△EDF'))
        result = TextProof(['红', '白', '黄'], 'ordered_words')
        self.assertTrue(result.matches('红球＞白球＞黄球'))
        self.assertFalse(result.matches('黄>白>红'))
        self.assertFalse(result.matches('红>,黄'))
        self.assertEqual(plain('x¹²'), 'x^12')

    def test_candidate_selection_rejects_unknown_and_duplicate_solutions(self):
        options = [{'key': 'A', 'text': '1', 'n': 1}, {'key': 'B', 'text': '2', 'n': 2}]
        self.assertEqual(select_unique(options, lambda o: o['n'] % 2 == 0), '2')
        for predicate in (lambda o: None, lambda o: True, lambda o: False, lambda o: 1):
            with self.assertRaises(ValueError):
                select_unique(options, predicate)

    def test_proved_equation_degree_and_reversed_identity(self):
        result = TextProof({'answer': False, 'degree': 2}, 'equation_classification')
        self.assertTrue(result.matches('不是'))
        self.assertTrue(result.matches('不是，未知数次数为 2'))
        for text in ('是', '不是，未知数次数为3', '不是，因为分母为零'):
            self.assertFalse(result.matches(text))
        identity = TextProof('a+b=b+a', 'identity_equation')
        self.assertTrue(identity.matches('b+a=a+b'))
        self.assertFalse(identity.matches('a-b=b-a'))

    def test_tuple_comparators_are_canonical_and_empty_operators_rejected(self):
        self.assertTrue(TextProof(('x', '>=', 3), 'relation').matches('x≥3'))
        for comparator in ('', '><', '==', '<>'):
            with self.assertRaises(ValueError):
                TextProof(('x', comparator, 3), 'relation')
        self.assertFalse(TextProof(('x', '≤', 12), 'relation').matches('x≤1 2'))


if __name__ == '__main__':
    unittest.main()
