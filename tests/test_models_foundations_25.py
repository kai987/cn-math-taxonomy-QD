"""All-method equivalence and the separate explicit first-step criterion."""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import models_foundations_25 as M


def spec(a=3,b=6,variable='x'):
    return {'kind':'f25_quadratic_variable_factor_first_step','domain':'all_real',
        'equation':{'variable':variable,'quadratic_coefficient':a,'linear_rhs_coefficient':b},
        'target':'first_variable_factor_zero_product','options':[
          {'key':'A','text':'factor method','program':{'op':'extract_variable_factor'}},
          {'key':'B','text':'square root with preparation','program':{'op':'prepare_then_open_square_root'}},
          {'key':'C','text':'complete square','program':{'op':'complete_square'}},
          {'key':'D','text':'formula','program':{'op':'quadratic_formula'}}]}


class FirstStepTests(unittest.TestCase):
    def test_all_four_algorithms_preserve_actual_roots_and_only_one_first_product(self):
        s=spec();p=M.QuadraticFirstStep(s['equation'],s['domain'],s['target'])
        results=[p.execute(o['program']) for o in s['options']]
        self.assertTrue(all(r.identity_verified for r in results))
        self.assertTrue(all(r.roots==(0,2) for r in results))
        self.assertEqual(results[0].first_product,((0,3),(-2,1)))
        self.assertEqual([p.meets_first_step(r) for r in results],[True,False,False,False])
        self.assertTrue(results[1].preparation_required)
        self.assertEqual(results[1].first_right,(1,))
        self.assertEqual(results[2].first_right,(1,))
        self.assertEqual(results[2].square_shift,1)
        self.assertEqual(results[3].discriminant,36)
        self.assertEqual(M.quadratic_first_step(s),'factor method')

    def test_positive_negative_fractional_parameters_are_exact(self):
        for a in ('1/7',-3,8):
            for b in ('-11/3',0,'2/5',17):
                s=spec(a,b);p=M.QuadraticFirstStep(s['equation'],s['domain'],s['target'])
                expected=tuple(sorted({Fraction(0),M._q(b)/M._q(a)}))
                with self.subTest(a=a,b=b):
                    for option in s['options']:
                        result=p.execute(option['program']);self.assertTrue(result.identity_verified)
                        self.assertEqual(result.roots,expected)
                    self.assertEqual(M.quadratic_first_step(s),'factor method')

    def test_double_root_does_not_make_other_valid_methods_meet_the_first_step_goal(self):
        s=spec(-7,0);p=M.QuadraticFirstStep(s['equation'],s['domain'],s['target'])
        results=[p.execute(o['program']) for o in s['options']]
        self.assertTrue(all(r.roots==(0,) for r in results))
        self.assertFalse(results[1].preparation_required)
        self.assertEqual(results[3].discriminant,0)
        self.assertEqual([p.meets_first_step(r) for r in results],[True,False,False,False])

    def test_variable_renaming_global_scaling_and_candidate_order_do_not_pick_names(self):
        for factor in ('-2/3',7):
            s=spec(str(3*M._q(factor)),str(6*M._q(factor)),variable='t')
            s['options'].reverse()
            for i,o in enumerate(s['options']):o.update(key=str(i),text='anonymous'+str(i))
            self.assertEqual(M.quadratic_first_step(s),'anonymous3')

    def test_arbitrary_supplied_linear_product_is_verified_not_name_matched(self):
        s=spec();s['options'][0]['program']={'op':'complete_square'}
        s['options'][3]['program']={'op':'display_linear_product','factors':[[-2,1],[0,3]]}
        self.assertEqual(M.quadratic_first_step(s),'formula')
        s['options'][3]['program']['factors'][0][0]=-3
        p=M.QuadraticFirstStep(s['equation'],s['domain'],s['target'])
        result=p.execute(s['options'][3]['program'])
        self.assertFalse(result.identity_verified);self.assertFalse(p.meets_first_step(result))
        with self.assertRaises(ValueError):M.quadratic_first_step(s)

    def test_factor_that_coincides_at_one_source_root_is_not_an_identity(self):
        s=spec();p=M.QuadraticFirstStep(s['equation'],s['domain'],s['target'])
        result=p.execute({'op':'display_linear_product','factors':[[0,1],[-2,2]]})
        self.assertFalse(result.identity_verified)
        self.assertFalse(p.meets_first_step(result))

    def test_unequal_and_missing_successful_options_fail_closed(self):
        s=spec();s['options'].pop(0)
        with self.assertRaises(ValueError):M.quadratic_first_step(s)
        s=spec();s['options'][3]['program']=deepcopy(s['options'][0]['program'])
        with self.assertRaises(ValueError):M.quadratic_first_step(s)
        s=spec();s['options'][0]['key']='D'
        with self.assertRaises(ValueError):M.quadratic_first_step(s)

    def test_unknown_late_method_and_every_unconsumed_field_are_rejected(self):
        for path in [(),('equation',),('options',0),('options',3,'program')]:
            s=spec();node=s
            for key in path:node=node[key]
            node['unconsumed']=1
            with self.subTest(path=path),self.assertRaises(ValueError):M.quadratic_first_step(s)
        s=spec();s['options'][3]['program']={'op':'unknown'}
        with self.assertRaises(ValueError):M.quadratic_first_step(s)

    def test_real_domain_nonzero_quadratic_and_explicit_task_are_not_defaults(self):
        for key in ('domain','target'):
            s=spec();s.pop(key)
            with self.subTest(key=key),self.assertRaises(ValueError):M.quadratic_first_step(s)
        for domain in ('integer','positive_real','complex','not_given'):
            s=spec();s['domain']=domain
            with self.subTest(domain=domain),self.assertRaises(ValueError):M.quadratic_first_step(s)
        with self.assertRaises(ValueError):M.quadratic_first_step(spec(0,6))

    def test_dividing_by_x_cannot_discard_zero_and_complexity_is_bounded(self):
        s=spec();s['options'][3]['program']={'op':'divide_by_x_and_discard_zero'}
        with self.assertRaises(ValueError):M.quadratic_first_step(s)
        for options in ([],None,[deepcopy(spec()['options'][0]) for _ in range(17)]):
            s=spec();s['options']=options
            with self.subTest(options=options),self.assertRaises(ValueError):M.quadratic_first_step(s)
        with self.assertRaises(ValueError):M.quadratic_first_step(spec(10**1000,6))

    def test_numeric_unicode_original_domain_and_nonliteral_coefficients_reject(self):
        self.assertEqual(M.quadratic_first_step(spec('３','６')),'factor method')
        for value in (True,3.0,'3²','③','3。0','3 0','1/0','x/x','0*x**0','1/(x-1)','sqrt(9)'):
            with self.subTest(value=value),self.assertRaises(ValueError):M.quadratic_first_step(spec(value,6))
        for pair in ([0],[0,1,2],[0,0],[True,1],['x/x',1]):
            s=spec();s['options'][0]['program']={'op':'display_linear_product','factors':[pair,[-2,3]]}
            with self.subTest(pair=pair),self.assertRaises(ValueError):M.quadratic_first_step(s)


if __name__=='__main__':unittest.main()
