"""Coverage counterfamilies and complete historical-frequency definitions."""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import sys
import time
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import models_geometry_25 as M


def frame_spec(n=100,k=1000,m=99000):
    return {'kind':'g25_frame_coverage_risk',
        'premises':{'target':'all_city_residents','frame':'resident_library_visitors',
            'frame_relation':'proper_subset','time_unit':'hours_per_day',
            'reading_bounds':{'lower':0,'upper':24},
            'sampling':{'op':'select_distinct','from':'frame','size':n}},
        'example':{'frame_size':k,'omitted_size':m,'inside_hours':1,'outside_hours':0},
        'options':[
            {'key':'A','text':'too many','claim':{'op':'sample_size_exceeds_available_frame'}},
            {'key':'B','text':'coverage risk','claim':{'op':'all','claims':[
                {'op':'frame_omits_population_members'},{'op':'positive_bias_possible'},
                {'op':'negative_bias_possible'},{'op':'zero_bias_possible'}]}},
            {'key':'C','text':'randomness fixes coverage','claim':{'op':'all','claims':[
                {'op':'everyone_has_sampling_chance'},{'op':'frame_randomness_guarantees_zero_bias'}]}},
            {'key':'D','text':'elderly replacement','claim':{'op':'elderly_only_guarantees_population_coverage'}}]}


def sales_spec():
    values={'op':'values'}
    return {'kind':'g25_historical_sales_modes','goal':'all_historical_maximum_frequency_sizes',
        'example':[36,36,38,38],
        'counterexample':[36,36,36,38,40,42,44],
        'options':[
            {'key':'A','text':'mean','program':{'op':'divide','numerator':{'op':'sum','input':deepcopy(values)},
                'denominator':{'op':'length','input':deepcopy(values)}}},
            {'key':'B','text':'median','program':{'op':'middle','input':{'op':'sort','input':deepcopy(values)}}},
            {'key':'C','text':'mode','program':{'op':'argmax_keys','input':{'op':'frequencies','input':values}}}]}


class FrameRiskTests(unittest.TestCase):
    def test_actual_counts_positive_negative_zero_family_and_reading_domain(self):
        s=frame_spec();p=M.FrameCoverage(s['premises'],s['example'])
        self.assertEqual(p.example['sample_mean'],1)
        self.assertEqual(p.example['population_mean'],Fraction(1,100))
        self.assertEqual(p.example['bias'],Fraction(99,100))
        self.assertEqual([w['bias'] for w in p.worlds],[Fraction(99,100),Fraction(-99,100),0])
        self.assertEqual({w['sample_mean'] for w in p.worlds},{1})
        self.assertEqual(len({w['population_mean'] for w in p.worlds}),3)
        self.assertEqual(p.age_counterworld,{'elderly_indices':(0,1000),
            'nonelderly_indices':(1000,100000),'eligible_count':1000,'omitted_count':99000,
            'population_count':100000})
        self.assertEqual([p.claim(o['claim']) for o in s['options']],[False,True,False,False])
        self.assertEqual(M.frame_coverage_risk(s),'coverage risk')

    def test_every_legal_sample_frame_and_omission_count_is_parameterized(self):
        for n,k,m in [(1,1,1),(1,7,99),(100,100,1),(100,101,100),(300,1000,10000)]:
            s=frame_spec(n,k,m)
            with self.subTest(n=n,k=k,m=m):
                p=M.FrameCoverage(s['premises'],s['example'])
                self.assertEqual(p.example['bias'],Fraction(m,k+m))
                self.assertFalse(p.claim({'op':'sample_size_exceeds_available_frame'}))
                self.assertEqual(p.age_counterworld['eligible_count'],k)
                self.assertEqual(p.age_counterworld['omitted_count'],m)
                self.assertLess(p.age_counterworld['eligible_count'],p.age_counterworld['population_count'])
                self.assertEqual(M.frame_coverage_risk(s),'coverage risk')

    def test_observed_example_can_have_any_legal_bias_without_changing_risk(self):
        for a,b in [(0,24),(24,0),(7,7),('1/3','7/2')]:
            s=frame_spec();s['example'].update(inside_hours=a,outside_hours=b)
            p=M.FrameCoverage(s['premises'],s['example'])
            self.assertEqual(p.example['bias'],Fraction(99,100)*(Fraction(a)-Fraction(b)))
            self.assertEqual(M.frame_coverage_risk(s),'coverage risk')

    def test_risk_does_not_claim_actual_positive_or_necessarily_nonzero_bias(self):
        s=frame_spec();p=M.FrameCoverage(s['premises'],s['example'])
        self.assertFalse(p.claim({'op':'actual_bias_must_be_positive'}))
        self.assertFalse(p.claim({'op':'actual_bias_must_be_nonzero'}))
        for a,b in [(0,1),(1,0),(1,1)]:
            result=p.run(a,b)
            self.assertEqual(result['bias'],Fraction(99,100)*(a-b))

    def test_frame_sample_and_candidate_key_order_do_not_encode_the_answer(self):
        s=frame_spec();s['options'].reverse()
        for i,o in enumerate(s['options']):o.update(key=str(i),text='claim'+str(i))
        s['options'][2]['claim']['claims'].reverse()
        self.assertEqual(M.frame_coverage_risk(s),'claim2')

    def test_missing_proper_frame_target_or_unsupported_random_law_is_not_assumed(self):
        for key,value in [('target','all_library_users'),('frame_relation','equal_to_population'),
            ('time_unit','minutes_per_day')]:
            s=frame_spec();s['premises'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):M.frame_coverage_risk(s)
        s=frame_spec();s['premises']['sampling']['op']='assume_SRS'
        with self.assertRaises(ValueError):M.frame_coverage_risk(s)
        s=frame_spec();del s['premises']['frame_relation']
        with self.assertRaises(ValueError):M.frame_coverage_risk(s)

    def test_impossible_counts_zero_omission_and_invalid_time_witnesses_reject(self):
        for n,k,m in [(0,1,1),(2,1,1),(1,1,0),(1,1,-1),(True,3,1)]:
            with self.subTest(n=n,k=k,m=m),self.assertRaises(ValueError):M.frame_coverage_risk(frame_spec(n,k,m))
        for time_value in (-1,25,True,'nan','1。5','①','1/0'):
            s=frame_spec();s['example']['inside_hours']=time_value
            with self.subTest(time_value=time_value),self.assertRaises(ValueError):M.frame_coverage_risk(s)

    def test_every_unknown_field_and_late_false_conjunction_is_rejected(self):
        for path in [(),('premises',),('premises','sampling'),('premises','reading_bounds'),
            ('example',),('options',0),('options',0,'claim')]:
            s=frame_spec();node=s
            for key in path:node=node[key]
            node['unknown']='claim'
            with self.subTest(path=path),self.assertRaises(ValueError):M.frame_coverage_risk(s)
        s=frame_spec();s['options'][0]['claim']={'op':'all','claims':[s['options'][0]['claim'],{'op':'unknown'}]}
        with self.assertRaises(ValueError):M.frame_coverage_risk(s)

    def test_duplicates_no_valid_claim_and_excessive_claim_depth_fail_closed(self):
        s=frame_spec();other=deepcopy(s['options'][1]);other['key']='extra';s['options'].append(other)
        with self.assertRaises(ValueError):M.frame_coverage_risk(s)
        s=frame_spec();s['options'].pop(1)
        with self.assertRaises(ValueError):M.frame_coverage_risk(s)
        s=frame_spec();node=s['options'][1]['claim']
        for _ in range(20):node={'op':'all','claims':[node]}
        s['options'][1]['claim']=node
        with self.assertRaises(ValueError):M.frame_coverage_risk(s)


class HistoricalModesTests(unittest.TestCase):
    def test_complete_frequency_map_and_all_ties_are_actually_computed(self):
        s=sales_spec();sales=M.Sales(s['example'])
        self.assertEqual(sales.counts,{36:2,38:2})
        self.assertEqual(sales.modes,{36,38})
        result=sales.evaluate(s['options'][2]['program'])
        self.assertTrue(result.mode_certificate)
        self.assertEqual(result.value,{36,38})
        self.assertEqual(M.historical_sales_modes(s),'mode')

    def test_one_item_all_unique_all_equal_and_multiple_modes_are_parameters(self):
        for example,target in [([38],{38}),([36,38,40],{36,38,40}),
            ([42]*9,{42}),([36,36,38,38,40],{36,38})]:
            s=sales_spec();s['example']=example
            with self.subTest(example=example):
                self.assertEqual(M.Sales(example).modes,target)
                self.assertEqual(M.historical_sales_modes(s),'mode')

    def test_mean_and_median_are_executed_and_distinguished_by_a_legal_witness(self):
        s=sales_spec();witness=M.Sales(s['counterexample'])
        results=[witness.evaluate(o['program']) for o in s['options']]
        self.assertEqual([r.value for r in results],[Fraction(272,7),38,frozenset({36})])
        # In this example mean and median DO coincide numerically with the
        # single mode. The general definition, not that coincidence, decides.
        s['example']=[38,38,38]
        self.assertEqual(M.historical_sales_modes(s),'mode')

    def test_labels_are_general_categories_for_the_positive_frequency_proof(self):
        program=sales_spec()['options'][2]['program']
        sales=M.Sales(['S','M','L','S','M'])
        self.assertEqual(sales.evaluate(program).value,{'S','M'})
        self.assertEqual(sales.evaluate(program).mode_certificate,True)
        sales=M.Sales(['XL'])
        self.assertEqual(sales.evaluate(program).value,{'XL'})

    def test_order_numeric_codes_and_common_frequency_multiplier_are_not_answers(self):
        s=sales_spec();s['options'].reverse()
        for i,o in enumerate(s['options']):o.update(key=str(i),text='statistic'+str(i))
        s['example'].reverse()
        self.assertEqual(M.historical_sales_modes(s),'statistic0')
        for factor in (1,2,7):
            q=sales_spec();q['example']=q['example']*factor
            q['counterexample']=[2*v+1 for v in q['counterexample']]*factor
            self.assertEqual(M.historical_sales_modes(q),'mode')

    def test_sorted_sales_before_frequency_count_is_an_equivalent_program(self):
        s=sales_spec();s['options'][2]['program']['input']['input']={
            'op':'sort','input':{'op':'values'}}
        self.assertEqual(M.historical_sales_modes(s),'mode')

    def test_sort_certificate_covers_labels_and_mixed_codes_but_not_numeric_median(self):
        program={'op':'argmax_keys','input':{'op':'frequencies','input':{
            'op':'sort','input':{'op':'values'}}}}
        for values,expected in [(['S','M','L','S'],{'S'}),
            ([38,'M',38,'M','L'],{38,'M'})]:
            sales=M.Sales(values)
            result=sales.evaluate(program)
            self.assertEqual(result.value,expected)
            self.assertTrue(result.mode_certificate)
            ordered=sales.evaluate({'op':'sort','input':{'op':'values'}})
            self.assertEqual(M.Counter(ordered.value),sales.counts)
            for numeric in ('sum','middle'):
                with self.subTest(values=values,numeric=numeric),self.assertRaises(ValueError):
                    sales.evaluate({'op':numeric,'input':{'op':'sort','input':{'op':'values'}}})

    def test_empty_unknown_numeric_tokens_and_illegal_value_domains_reject(self):
        for example in ([],[True],[None],[0.5],['NaN'],['inf'],['3⁵'],['③'],['3。5'],['1/0']):
            s=sales_spec();s['example']=example
            with self.subTest(example=example),self.assertRaises(ValueError):M.historical_sales_modes(s)
        s=sales_spec();s['goal']='optimal_purchase_quantities'
        with self.assertRaises(ValueError):M.historical_sales_modes(s)

    def test_unknown_fields_and_operators_in_every_candidate_are_not_called_false(self):
        for index in range(3):
            for path in [(),('options',index),('options',index,'program')]:
                s=sales_spec();node=s
                for key in path:node=node[key]
                node['unknown']='claim'
                with self.subTest(path=path),self.assertRaises(ValueError):M.historical_sales_modes(s)
        s=sales_spec();s['options'][0]['program']={'op':'invent','input':{'op':'values'}}
        with self.assertRaises(ValueError):M.historical_sales_modes(s)

    def test_tampered_numeric_program_missing_divisor_and_wrong_types_reject(self):
        s=sales_spec();s['options'][0]['program']['denominator']={'op':'values'}
        with self.assertRaises(ValueError):M.historical_sales_modes(s)
        s=sales_spec();s['options'][1]['program']={'op':'middle','input':{'op':'values'}}
        s['example']=[40,36,38]
        with self.assertRaises(ValueError):M.historical_sales_modes(s)
        s=sales_spec();s['options'][2]['program']['input']={'op':'values'}
        with self.assertRaises(ValueError):M.historical_sales_modes(s)

    def test_coincident_counterexample_is_not_used_as_a_disproof(self):
        s=sales_spec();s['counterexample']=[38,38,38]
        with self.assertRaises(ValueError):M.historical_sales_modes(s)

    def test_duplicate_complete_statistic_or_no_mode_does_not_choose_first(self):
        s=sales_spec();extra=deepcopy(s['options'][2]);extra['key']='other';s['options'].append(extra)
        with self.assertRaises(ValueError):M.historical_sales_modes(s)
        s=sales_spec();s['options'].pop(2)
        with self.assertRaises(ValueError):M.historical_sales_modes(s)

    def test_excessive_statistic_program_depth_is_bounded(self):
        s=sales_spec();node={'op':'values'}
        for _ in range(20):node={'op':'sort','input':node}
        s['options'][2]['program']['input']['input']=node
        with self.assertRaises(ValueError):M.historical_sales_modes(s)


class RuntimeTests(unittest.TestCase):
    def test_actual_mathematical_examples_are_well_below_the_two_second_limit(self):
        # The runtime assertion protects the shared offline evaluator's hard
        # timeout, not an invented statistical or method-preference threshold.
        for handler,spec in [(M.frame_coverage_risk,frame_spec()),(M.historical_sales_modes,sales_spec())]:
            start=time.monotonic();handler(spec)
            self.assertLess(time.monotonic()-start,2)


if __name__=='__main__':unittest.main()
