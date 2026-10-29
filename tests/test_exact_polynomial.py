from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from exact_polynomial import poly
from verify_questions import compare_choice, compare_short, safe_eval


class ExactPolynomialTests(unittest.TestCase):
    def test_expand_factor_and_reorder_exactly(self):
        for source, equivalent in [
            ('(x+1)**2', 'x²+2x+1'), ('(a-b)*(a+b)', 'a²-b²'),
            ('2*(a+2)+2*a', '4+4a'), ('3*a*b', '3ba'),
            ('a*b*(c+d)', 'ab(c+d)'), ('2*a*b*(a-b)', '2ab(a-b)'),
            ('x/3+x/6', '0.5x'), ('0*(x+y)', '0'),
        ]:
            with self.subTest(source=source):
                self.assertTrue(poly(source).matches(equivalent))
                self.assertFalse(poly(source).matches(equivalent + '+1'))

    def test_decimal_tokens_never_round_to_an_equal_coefficient(self):
        self.assertFalse(poly('0.1').matches('0.100000000000000001'))
        self.assertFalse(poly('1').matches('0.99999999999999999'))
        self.assertFalse(poly('0.1*x').matches('0.100000000000001*x'))

    def test_function_dependent_variable_and_sign_are_preserved(self):
        reference = poly('10+2*(x-3)', 'y')
        self.assertTrue(reference.matches('y=2x+4'))
        self.assertTrue(reference.matches('2x+4'))
        self.assertTrue(reference.matches('y=10+2(x-3)=2x+4'))
        for wrong in ('x=2x+4', 'y=2x-4', 'y=2x+4=99', 'y=2y+4'):
            self.assertFalse(reference.matches(wrong))

    def test_choice_requires_a_unique_mathematically_equal_option(self):
        question = {'answer': 'B', 'choices': [
            {'key': 'A', 'text': 'x²+1'}, {'key': 'B', 'text': 'x²+2x+1'},
            {'key': 'C', 'text': 'x²-2x+1'},
        ]}
        result = safe_eval("poly('(x+1)**2')")
        self.assertTrue(compare_choice(question, result)[0])
        question['answer'] = 'A'
        self.assertFalse(compare_choice(question, result)[0])
        question['answer'] = 'B'
        question['choices'][0]['text'] = '(x+1)²'
        self.assertFalse(compare_choice(question, result)[0])

    def test_short_checks_every_accepted_expression(self):
        question = {'answer': '4a+4', 'accept': ['2(a+2)+2a', '4+4a']}
        reference = poly('2*(a+2)+2*a')
        self.assertTrue(compare_short(question, reference)[0])
        question['accept'].append('4a-4')
        self.assertFalse(compare_short(question, reference)[0])
        self.assertFalse(compare_short(question, '4a+4')[0])

    def test_reject_unsupported_or_unbounded_code(self):
        for source in ('x/x', '1/0', 'x**-1', 'x**9', 'x**x', '__import__("os")',
                       'sqrt(x)', 'x[0]', 'x.__class__', 'x;y', 'x!', 'x' * 257,
                       '0**0', '(x-x)**0'):
            with self.subTest(source=source):
                with self.assertRaises((ValueError, SyntaxError, ZeroDivisionError)):
                    poly(source)
        with self.assertRaises(ValueError):
            poly('y+1', 'y')


if __name__ == '__main__':
    unittest.main()
