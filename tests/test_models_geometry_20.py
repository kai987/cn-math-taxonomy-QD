"""Universal central-rank preservation and actual statistic-program changes."""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import sys
import time
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import models_geometry_20 as M


def invariance_spec():
    values={'op':'values'}
    return {'kind':'g20_maximum_raise_invariance',
        'premises':{'minimum_size':3,'order':'nondecreasing',
            'change':'raise_only_last_by_positive_amount','criterion':'unchanged_for_all_admissible_tables',
            'mode_ties':'all_maximum_frequency_values'},
        'example':{'values':[8,8,9,10,65],'increase':100},
        'counterexample':{'values':[1,1,2,9,9],'increase':1},
        'options':[
            {'key':'A','text':'mean','program':{'op':'divide','numerator':{'op':'sum','input':deepcopy(values)},
                'denominator':{'op':'length','input':deepcopy(values)}}},
            {'key':'B','text':'median','program':{'op':'middle','input':{'op':'sort','input':deepcopy(values)}}},
            {'key':'C','text':'modes','program':{'op':'argmax_keys','input':{'op':'frequencies','input':values}}}]}


class CentralRankTests(unittest.TestCase):
    def test_actual_mean_median_and_complete_mode_set_changes(self):
        s=invariance_spec();p=M.MaximumRaise(s['counterexample'])
        results=[p.execute(o['program']) for o in s['options']]
        self.assertEqual(results[0][1].value-results[0][0].value,Fraction(1,5))
        self.assertEqual((results[1][0].value,results[1][1].value),(2,2))
        self.assertEqual((results[2][0].value,results[2][1].value),({1,9},{1}))
        self.assertEqual(M.maximum_raise_invariance(s),'median')

    def test_parity_certificate_exhausts_all_n_ge_three(self):
        charts=M.central_rank_certificate()
        self.assertEqual(len(charts),2)
        for n in range(3,40):
            indices=(n//2,) if n%2 else (n//2-1,n//2)
            self.assertTrue(all(index<=n-2 for index in indices))
        for n in range(3,14):
            s=invariance_spec();s['example']={'values':[i//2 for i in range(n)],'increase':'1/7'}
            p=M.MaximumRaise(s['example'])
            before,after=p.execute(s['options'][1]['program'])
            self.assertEqual(before.value,after.value)
            self.assertEqual(M.maximum_raise_invariance(s),'median')

    def test_repeated_maximum_all_equal_and_zero_data_do_not_drop_observations(self):
        for data in ([0,0,0],[7,7,7,7],[1,9,9],[-8,-8,-2,-2],['1/5','1/3','1/3','1/3']):
            s=invariance_spec();s['example']={'values':data,'increase':'1/100000000000000000000'}
            with self.subTest(data=data):
                p=M.MaximumRaise(s['example'])
                self.assertEqual(len(p.before),len(p.after))
                self.assertEqual(p.before[:-1],p.after[:-1])
                self.assertGreater(p.after[-1],p.before[-1])
                self.assertEqual(M.maximum_raise_invariance(s),'median')

    def test_n_one_and_two_boundary_is_not_credited_as_median_invariance(self):
        for data in ([7],[1,100]):
            with self.subTest(data=data),self.assertRaises(ValueError):M.MaximumRaise({'values':data,'increase':900})
        program=invariance_spec()['options'][1]['program']
        for before,after,change in [([7],[907],900),([1,100],[1,1000],450)]:
            old=M.Sales(before).evaluate(program).value
            new=M.Sales(after).evaluate(program).value
            self.assertEqual(new-old,change)

    def test_zero_or_inward_change_unsorted_and_wrong_change_rule_are_rejected(self):
        for delta in (0,-1,True,'0/1'):
            s=invariance_spec();s['example']['increase']=delta
            with self.subTest(delta=delta),self.assertRaises(ValueError):M.maximum_raise_invariance(s)
        s=invariance_spec();s['example']['values']=[8,10,9]
        with self.assertRaises(ValueError):M.maximum_raise_invariance(s)
        s=invariance_spec();s['premises']['change']='increase_an_arbitrary_observation'
        with self.assertRaises(ValueError):M.maximum_raise_invariance(s)

    def test_mean_change_uses_actual_n_and_positive_increase_not_a_snapshot(self):
        for n in (3,4,10,31):
            s=invariance_spec();s['example']={'values':list(range(n)),'increase':'17/9'}
            p=M.MaximumRaise(s['example']);old,new=p.execute(s['options'][0]['program'])
            self.assertEqual(new.value-old.value,Fraction(17,9*n))

    def test_mode_can_stay_in_some_tables_but_not_be_guaranteed(self):
        s=invariance_spec();s['example']={'values':[8,8,8],'increase':1}
        old,new=M.MaximumRaise(s['example']).execute(s['options'][2]['program'])
        self.assertEqual(old.value,new.value)
        self.assertEqual(M.maximum_raise_invariance(s),'median')

    def test_different_legal_mode_witness_with_ties_also_refutes_the_guarantee(self):
        s=invariance_spec();s['counterexample']={'values':[1,1,2,2],'increase':1}
        old,new=M.MaximumRaise(s['counterexample']).execute(s['options'][2]['program'])
        self.assertEqual((old.value,new.value),({1,2},{1}))
        self.assertEqual(M.maximum_raise_invariance(s),'median')

    def test_mode_counterexample_does_not_depend_on_all_distinct_data_conventions(self):
        s=invariance_spec();s['counterexample']={'values':[1,9,9],'increase':1}
        with self.assertRaises(ValueError):M.maximum_raise_invariance(s)


class ProgramAndDomainGuards(unittest.TestCase):
    def test_keys_text_candidate_order_and_equivalent_sorted_program_do_not_pick_names(self):
        s=invariance_spec();s['options'].reverse()
        for i,o in enumerate(s['options']):o.update(key=str(i),text='statistic'+str(i))
        s['options'][1]['program']={'op':'middle','input':{'op':'values'}}
        self.assertEqual(M.maximum_raise_invariance(s),'statistic1')

    def test_every_unknown_field_and_late_nonmatching_program_fail_closed(self):
        for path in [(),('premises',),('example',),('counterexample',),('options',0),('options',2,'program')]:
            s=invariance_spec();node=s
            for key in path:node=node[key]
            node['unknown']='claim'
            with self.subTest(path=path),self.assertRaises(ValueError):M.maximum_raise_invariance(s)
        s=invariance_spec();s['options'][2]['program']={'op':'unknown'}
        with self.assertRaises(ValueError):M.maximum_raise_invariance(s)

    def test_missing_n_bound_positive_change_or_complete_tie_definition_reject(self):
        for key in ('minimum_size','change','mode_ties','criterion'):
            s=invariance_spec();del s['premises'][key]
            with self.subTest(key=key),self.assertRaises(ValueError):M.maximum_raise_invariance(s)
        for n in (1,2,True):
            s=invariance_spec();s['premises']['minimum_size']=n
            with self.subTest(n=n),self.assertRaises(ValueError):M.maximum_raise_invariance(s)

    def test_raw_numeric_tokens_empty_data_and_complexity_limits_are_not_normalized(self):
        for value in (True,0.5,'NaN','3。5','3⁵','③','３','1/0'):
            s=invariance_spec();s['example']['values'][0]=value
            with self.subTest(value=value),self.assertRaises(ValueError):M.maximum_raise_invariance(s)
        for values in ([],[1]*129):
            s=invariance_spec();s['example']['values']=values
            with self.subTest(values=values),self.assertRaises(ValueError):M.maximum_raise_invariance(s)
        s=invariance_spec();node={'op':'values'}
        for _ in range(25):node={'op':'sort','input':node}
        s['options'][1]['program']['input']=node
        with self.assertRaises(ValueError):M.maximum_raise_invariance(s)

    def test_nonzero_sample_denominator_does_not_prove_universal_definedness(self):
        s=invariance_spec();s['options'][0]['program']['denominator']={'op':'sum','input':{'op':'values'}}
        with self.assertRaises(ValueError):M.maximum_raise_invariance(s)

    def test_missing_duplicate_or_coincident_counterexample_is_not_forced_to_one_choice(self):
        s=invariance_spec();s['options'].pop(1)
        with self.assertRaises(ValueError):M.maximum_raise_invariance(s)
        s=invariance_spec();extra=deepcopy(s['options'][1]);extra['key']='extra';s['options'].append(extra)
        with self.assertRaises(ValueError):M.maximum_raise_invariance(s)
        s=invariance_spec();s['counterexample']={'values':[8,8,8],'increase':1}
        with self.assertRaises(ValueError):M.maximum_raise_invariance(s)

    def test_count_is_a_different_invariant_statistic_and_causes_ambiguity_if_added(self):
        s=invariance_spec();s['options'].append({'key':'N','text':'sample count','program':{'op':'length','input':{'op':'values'}}})
        with self.assertRaises(ValueError):M.maximum_raise_invariance(s)

    def test_actual_mathematical_spec_is_under_the_offline_timeout(self):
        start=time.monotonic();self.assertEqual(M.maximum_raise_invariance(invariance_spec()),'median')
        self.assertLess(time.monotonic()-start,2)


if __name__=='__main__':unittest.main()
