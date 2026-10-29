from fractions import Fraction
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from models_symbolic import (parse_math, identity, factorization, equation, domain,
                             rational_form, rational_reduced, factorization_form)
from models_symbolic import number_rationality, affine_incidence


def options(*expressions):
    return [{'key': chr(65+i), 'text': text, 'expression': text} for i, text in enumerate(expressions)]


class SymbolicModelsTests(unittest.TestCase):
    def test_rejects_code_and_retains_exact_decimal_tokens(self):
        for source in ('__import__("os")', 'x.__class__', '[x]', 'x**100', '0/0', 'sqrt(-1)'):
            if source == 'sqrt(-1)':
                _, conditions = parse_math(source)
                self.assertIn(False, conditions)
            else:
                with self.assertRaises((ValueError, SyntaxError)):
                    parse_math(source)
        with self.assertRaises(ValueError):
            parse_math('0.100000000000000001')

    def test_exact_identity_checks_all_choices_and_domain_holes(self):
        self.assertEqual(identity({'source':'(x+1)**2','options':options('x**2+2*x+1','x**2+1')}), 'x**2+2*x+1')
        with self.assertRaises(ValueError):
            identity({'source':'(x+1)**2','options':options('x**2+2*x+1','(x+1)**2')})
        self.assertEqual(identity({'source':'x+1','options':options('x+1','(x**2-1)/(x-1)')}), 'x+1')
        self.assertEqual(identity({'source':'(x**2-1)/(x-1)','options':options('x+1','x-1')}), 'x+1')

    def test_complete_factorization_uses_irreducible_factors_over_rationals(self):
        self.assertEqual(factorization({'source':'2*x**3-8*x','options':options(
            '2*x*(x**2-4)','2*x*(x+2)*(x-2)','2*x*(x+2)**2')}), '2*x*(x+2)*(x-2)')
        self.assertEqual(factorization({'source':'6*a**2*b-9*a*b**2','options':options(
            '3*a*b*(2*a-3*b)','3*a*b*(2*a+3*b)')}), '3*a*b*(2*a-3*b)')

    def test_equation_filters_extraneous_roots_and_counts_empty_set(self):
        spec={'lhs':'(x**2-1)/(x-1)','rhs':'2','variable':'x','query':'count'}
        self.assertEqual(equation(spec), 0)
        self.assertEqual(equation({'lhs':'2*x+1','rhs':'4','query':'roots'}), Fraction(3,2))
        self.assertEqual(equation({'lhs':'x**2-1','query':'roots'}), [-1,1])

    def test_domain_uses_original_denominators_and_square_roots(self):
        spec={'expression':'sqrt(x-1)/(x-2)','options':[
            {'key':'A','text':'x>=1 and x!=2','condition':'x>=1 and x!=2'},
            {'key':'B','text':'x>=1','condition':'x>=1'},
            {'key':'C','text':'x>1 and x!=2','condition':'x>1 and x!=2'}]}
        self.assertEqual(domain(spec), 'x>=1 and x!=2')
        self.assertEqual(domain({'expression':'(x**2-1)/(x-1)','query':'excluded_values'}), 1)

    def test_candidate_conditions_keep_their_own_denominator_and_radical_domains(self):
        self.assertEqual(domain({'expression':'sqrt(x)','options':[
            {'key':'A','text':'root identity','condition':'sqrt(x)==sqrt(x)'},
            {'key':'B','text':'all real','condition':'True'}]}), 'root identity')
        with self.assertRaises(ValueError):
            domain({'expression':'sqrt(x**2)','options':[
                {'key':'A','text':'x/x==1','condition':'x/x==1'},
                {'key':'B','text':'x>0','condition':'x>0'}]})

    def test_common_domain_policy_never_proves_an_identity_on_an_empty_domain(self):
        for source, candidate in [
            ('sqrt(x-1)-sqrt(x-1)', 'sqrt(-x)-sqrt(-x)'),
            ('sqrt(x*y)-sqrt(x*y)', 'sqrt(-x*y-1)-sqrt(-x*y-1)'),
        ]:
            with self.subTest(source=source):
                with self.assertRaises(ValueError):
                    identity({'source': source, 'domain_policy':'common_defined',
                              'options': options(candidate, '1')})
        self.assertEqual(factorization({'source':'x**2/4-1', 'options':options(
            '(x/2-1)*(x/2+1)', '(x/2-1)**2')}), '(x/2-1)*(x/2+1)')

    def test_rational_syntax_rejects_zero_denominator_and_reduces_expanded_polynomials(self):
        for source in ('x/(x-x)', 'x/(0*x)'):
            with self.assertRaises(ValueError):
                rational_form({'options':options(source, 'x+1')})
        self.assertEqual(rational_reduced({'options':options('(x-x+1)/(x+1)', 'x/(2*x)')}), '(x-x+1)/(x+1)')

    def test_factorization_direction_accepts_extracted_constants_and_powers(self):
        for lhs, rhs in [('2*x+2','2*(x+1)'), ('x**2+2*x+1','(x+1)**2')]:
            self.assertEqual(factorization_form({'options':[
                {'key':'A','text':'factored','lhs':lhs,'rhs':rhs},
                {'key':'B','text':'multiplied','lhs':rhs,'rhs':lhs}]}), 'factored')

    def test_number_classes_use_exact_theorems_and_growing_gap_certificate(self):
        self.assertEqual(number_rationality({'target':'rational','values':['-2','0','sqrt(3)','1/2','pi','-sqrt(9)']}), 4)
        self.assertEqual(number_rationality({'target':'irrational','values':[
            '3.14','sqrt(5)','-pi',{'kind':'growing_decimal_gaps','start':1,'step':1,'digit':1},'sqrt(16)','22/7','cbrt(8)']}), 3)
        with self.assertRaises(ValueError):
            number_rationality({'target':'irrational','values':[{'kind':'growing_decimal_gaps','start':1,'step':0,'digit':1}]})

    def test_symbolic_incidence_handles_all_admitted_directions_not_one_example(self):
        for query in ('perpendicular_through_point','parallel_through_point'):
            self.assertEqual(affine_incidence({'query':query,'plane_dimension':2,'given_direction_nonzero':True,'point_off_line':True}), 1)
            with self.assertRaises(ValueError):
                affine_incidence({'query':query,'plane_dimension':3,'given_direction_nonzero':True})
        self.assertEqual(affine_incidence({'query':'two_parallels_and_transversal','parallel_lines_distinct':True,'transversal_meets_first':True}), 2)


if __name__ == '__main__':
    unittest.main()
