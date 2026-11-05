"""Whole-reference, exact affine geometry regressions for the41 audit."""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import models_geometry_41 as M
from model_types import SelfReferenceProof, TextProof
from verify_questions import compare_self_reference


def function(a=-3, b=1, x='x', y='y'):
    return dict(independent=x, dependent=y, slope=a, intercept=b, domain='all_real')


def affine_spec(a=-3, b=1, x='x', y='y'):
    return dict(kind='g41_affine_monotonic_quadrants_reference', reference_only=True,
        function=function(a, b, x, y))


def axis_spec(a=2, b=-6, m=2, c=-6, rhs=0, x='x', y='y'):
    return dict(kind='g41_axis_equation_reference', reference_only=True,
        function=function(a, b, x, y), axis={'zero_coordinate': y, 'reported_coordinate': x},
        equation=dict(variable=x, slope=m, intercept=c, rhs=rhs, domain='all_real'))


class AffineQuadrantReferenceTests(unittest.TestCase):
    def test_actual_complete_reference_and_clause_or_set_reordering(self):
        proof = M.affine_reference(affine_spec())
        self.assertIsInstance(proof, SelfReferenceProof)
        self.assertTrue(proof.matches('y 随 x 增大而减小；经过一、二、四象限'))
        self.assertTrue(proof.matches('经过第四、第一、第二象限；单调递减。'))
        self.assertTrue(proof.matches('递减；图象经过4,1,2象限'))
        self.assertFalse(proof.matches('y随x增大而增大；经过一、二、四象限'))

    def test_all_sign_classes_including_axis_intercepts_zero(self):
        cases = [(3, 1, 1, {1, 2, 3}), (3, 0, 1, {1, 3}),
            (3, -1, 1, {1, 3, 4}), (-3, 1, -1, {1, 2, 4}),
            (-3, 0, -1, {2, 4}), (-3, -1, -1, {2, 3, 4})]
        for a, b, direction, quadrants in cases:
            with self.subTest(a=a, b=b):
                proof = M.affine_reference(affine_spec(a, b))
                self.assertEqual(proof.direction, direction)
                self.assertEqual(proof.quadrants, quadrants)

    def test_tiny_exact_parameters_have_no_epsilon_or_sampling_gap(self):
        proof = M.affine_reference(affine_spec('-1/1000000000000000000000', '1/10000000000000000000000000'))
        self.assertEqual(proof.quadrants, {1, 2, 4})
        self.assertTrue(proof.matches('递减；经过一、二、四象限'))

    def test_reflections_are_covariant_for_all_six_sign_regimes(self):
        reflect_x = {1: 2, 2: 1, 3: 4, 4: 3}
        reflect_y = {1: 4, 4: 1, 2: 3, 3: 2}
        for a in (-7, 2):
            for b in (-5, 0, 11):
                original = M.affine_reference(affine_spec(a, b))
                horizontal = M.affine_reference(affine_spec(-a, b))
                vertical = M.affine_reference(affine_spec(-a, -b))
                self.assertEqual(horizontal.quadrants, {reflect_x[q] for q in original.quadrants})
                self.assertEqual(vertical.quadrants, {reflect_y[q] for q in original.quadrants})
                self.assertEqual(horizontal.direction, -original.direction)
                self.assertEqual(vertical.direction, -original.direction)

    def test_coordinate_renaming_is_structural(self):
        proof = M.affine_reference(affine_spec(x='t', y='s'))
        self.assertTrue(proof.matches('s随t增大而减小；经过一、二、四象限'))
        self.assertFalse(proof.matches('y随x增大而减小；经过一、二、四象限'))
        self.assertFalse(proof.matches('s随s增大而减小；经过一、二、四象限'))

    def test_omission_duplicates_wrong_set_or_added_assertion_reject(self):
        proof = M.affine_reference(affine_spec())
        invalid = ['递减', '经过一、二、四象限', '递减；递减',
            '递减；经过一、二象限', '递减；经过一、二、三、四象限',
            '递减；经过一、二、四、四象限', '递减；经过一、二、四象限；且斜率为3',
            '递减；经过一、二、四象限且经过原点',
            '递减；经过一、二、四象限，不经过四象限',
            '递减；经过一、二、四象限；', '递减；经过一、二、四象限..']
        for text in invalid:
            with self.subTest(text=text):
                self.assertFalse(proof.matches(text))

    def test_strict_intersection_is_decided_over_whole_real_domain(self):
        self.assertFalse(M._strict_affine_feasible([(1, 0), (-1, 0)]))
        self.assertTrue(M._strict_affine_feasible([(1, 0), (-1, Fraction(1, 10**30))]))
        self.assertFalse(M._strict_affine_feasible([(0, 0)]))
        self.assertTrue(M._strict_affine_feasible([(0, 1), (1, 0)]))
        # A contradictory earlier constraint cannot hide an unknown later one.
        with self.assertRaises(ValueError):
            M._strict_affine_feasible([(0, 0), ('unknown', 1)])


class AxisEquationReferenceTests(unittest.TestCase):
    def test_complete_relation_and_both_values_are_required(self):
        proof = M.axis_equation_reference(axis_spec())
        self.assertIsInstance(proof, SelfReferenceProof)
        self.assertTrue(proof.matches('相等，都是 3'))
        self.assertTrue(proof.matches('相同，均为6/2。'))
        for text in ('3', '相等', '不相等', '相等，都是0', '相等，都是-3',
            '相等，都是3，交点纵坐标为1', '相等，都是3；该点位于第一象限',
            '相等，都是3和4', '不相等，分别为3、3', '相等，都是3；'):
            with self.subTest(text=text):
                self.assertFalse(proof.matches(text))

    def test_independent_equation_can_disagree_with_graph(self):
        proof = M.axis_equation_reference(axis_spec(c=-8))
        self.assertFalse(proof.same)
        self.assertFalse(proof.matches('相等，都是3'))
        self.assertTrue(proof.matches('不相等，分别为3、4'))
        self.assertFalse(proof.matches('不相等，分别为4、3'))

    def test_nonzero_equation_scaling_and_both_sides_preserve_root(self):
        for multiplier in (-7, Fraction(1, 11), 9):
            proof = M.axis_equation_reference(axis_spec(m=2*multiplier, c=-6*multiplier))
            self.assertTrue(proof.matches('相等，都是3'))
        proof = M.axis_equation_reference(axis_spec(m=2, c=4, rhs=10))
        self.assertTrue(proof.matches('相等，都是3'))

    def test_fractional_zero_and_negative_roots(self):
        for a, b in [(3, 1), (-7, 2), (1, 0), (Fraction(1, 3), Fraction(-5, 7))]:
            proof = M.axis_equation_reference(axis_spec(a, b, a, b))
            root = -Fraction(b) / Fraction(a)
            self.assertTrue(proof.matches('相等，都是' + str(root)))
            self.assertFalse(proof.matches('相等，都是' + str(root+1)))

    def test_sentence_stop_and_superscript_are_not_numeric_digits(self):
        half = M.axis_equation_reference(axis_spec(a=2, b=-7, m=2, c=-7))
        self.assertTrue(half.matches('相等，都是3.5。'))
        self.assertTrue(half.matches('相等，都是7/2。'))
        self.assertTrue(half.matches('相等，都是３．５。'))
        for text in ('相等，都是3。5', '相等，都是3。 5', '相等，都是３。５'):
            with self.subTest(text=text):
                self.assertFalse(half.matches(text))
        integer = M.axis_equation_reference(axis_spec(a=1, b=-35, m=1, c=-35))
        self.assertTrue(integer.matches('相等，都是35。'))
        self.assertFalse(integer.matches('相等，都是3⁵'))
        self.assertFalse(integer.matches('相等，都是3⁵。'))
        self.assertFalse(integer.matches('相等，都是3 5'))
        three = M.axis_equation_reference(axis_spec())
        self.assertFalse(three.matches('相等，都是③'))
        self.assertFalse(three.matches('相等，都是³'))
        fifty = M.axis_equation_reference(axis_spec(a=1, b=-50, m=1, c=-50))
        self.assertFalse(fifty.matches('相等，都是㊿'))

    def test_coordinate_renaming_not_fixed_x_or_y(self):
        proof = M.axis_equation_reference(axis_spec(x='t', y='s'))
        self.assertTrue(proof.matches('相等，都是3'))
        malformed = axis_spec(x='t', y='s')
        malformed['equation']['variable'] = 'x'
        with self.assertRaises(ValueError):
            M.axis_equation_reference(malformed)


class InputAndIntegrationGuards(unittest.TestCase):
    def test_full_domain_nonzero_slope_and_distinct_coordinates_required(self):
        for factory, handler in [(affine_spec, M.affine_reference), (axis_spec, M.axis_equation_reference)]:
            for key, value in [('domain', 'positive_real'), ('slope', 0), ('dependent', 'x')]:
                spec = factory(); spec['function'][key] = value
                with self.subTest(factory=factory.__name__, key=key), self.assertRaises(ValueError):
                    handler(spec)
            spec = factory(); del spec['function']['domain']
            with self.assertRaises(ValueError):
                handler(spec)

    def test_wrong_axis_target_or_underdetermined_equation_reject(self):
        for change in ({'zero_coordinate': 'x', 'reported_coordinate': 'y'},
            {'zero_coordinate': 'y', 'reported_coordinate': 'y'},
            {'zero_coordinate': 'y', 'reported_coordinate': 'x', 'offset': 1}):
            spec = axis_spec(); spec['axis'] = change
            with self.assertRaises(ValueError):
                M.axis_equation_reference(spec)
        for key, value in [('slope', 0), ('variable', 'y'), ('domain', 'integer')]:
            spec = axis_spec(); spec['equation'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                M.axis_equation_reference(spec)

    def test_boolean_floats_nonfinite_injection_and_unbounded_inputs_reject(self):
        for value in (True, False, 0.5, float('inf'), 'nan', 'sqrt(4)', '1/0',
            '__import__("os")', '1'*65, 10**100, '3。5', '3⁵', '３５', '3 5', '③', '㊿'):
            spec = affine_spec(); spec['function']['slope'] = value
            with self.subTest(value=value), self.assertRaises((ValueError, ZeroDivisionError)):
                M.affine_reference(spec)

    def test_no_reference_string_or_unconsumed_parameter_can_be_input(self):
        for factory, handler in [(affine_spec, M.affine_reference), (axis_spec, M.axis_equation_reference)]:
            for field in ('answer', 'expected', 'correct', 'unknown'):
                spec = factory(); spec[field] = 'reference'
                with self.subTest(field=field), self.assertRaises(ValueError):
                    handler(spec)
            for flag in (False, 1, 'true'):
                spec = factory(); spec['reference_only'] = flag
                with self.subTest(flag=flag), self.assertRaises(ValueError):
                    handler(spec)

    def test_current_source_answers_full_reference_verifier_and_accepts(self):
        data = json.loads((ROOT / 'data/questions.json').read_text())
        questions = data['questions'] if isinstance(data, dict) else data
        for qid, proof in [('cnm_203_q1', M.affine_reference(affine_spec())),
            ('cnm_206_q1', M.axis_equation_reference(axis_spec()))]:
            q = next(q for q in questions if q['id'] == qid)
            self.assertTrue(compare_self_reference(q, proof)[0])
            changed = deepcopy(q); changed['answer'] += '；且1=2'
            self.assertFalse(compare_self_reference(changed, proof)[0])
            changed = deepcopy(q); changed['accept'] = [q['answer'], q['answer'] + '；且1=2']
            self.assertFalse(compare_self_reference(changed, proof)[0])
            self.assertFalse(compare_self_reference(q, TextProof(q['answer']))[0])


if __name__ == '__main__':
    unittest.main()
