"""SRS indicator moments, lawful countermodels and design qualification."""
from copy import deepcopy
from fractions import Fraction
from itertools import combinations
from math import comb
from pathlib import Path
import sys
import time
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import models_applications_16 as M


def variance_spec(size=400,positives=200):
    return {'kind':'app16_minimum_binary_srs_variance','data_model':M.DATA_MODEL,
        'population':{'size':size,'positives':positives},'minimum_population_size':200,
        'population_condition':'both_statuses_present',
        'goal':{'design':'full_population_uniform_without_replacement','statistic':'sample_proportion','comparison':'minimum_design_variance'},
        'options':[{'key':'A','text':'optician','plan':{'op':'restricted_frame_plan',
                    'frame':{'op':'interval_union','intervals':[[0,size//2]]},'frame_relation':'nonempty_proper_subset',
                    'requested_count':{'op':'constant','value':200}}},
                   {'key':'B','text':'sample20','plan':{'op':'uniform_without_replacement','frame':{'op':'population'},'size':20,'statistic':'sample_proportion'}},
                   {'key':'C','text':'sample200','plan':{'op':'uniform_without_replacement','frame':{'op':'population'},'size':200,'statistic':'sample_proportion'}},
                   {'key':'D','text':'restricted vision frame','plan':{'op':'restricted_frame_plan',
                    'frame':{'op':'interval_union','intervals':[[0,size//2]]},'frame_relation':'nonempty_proper_subset',
                    'requested_count':{'op':'unspecified'}}}]}


def mean_spec():
    return {'kind':'app16_mean_design_claims','data_model':M.DATA_MODEL,
        'target':'finite_population_mean_design_expectation_and_realized_error',
        'counterexamples':{
            'single_srs_error':{'population':[0,1,2],'sampling':{'op':'uniform_subsets','frame':[0,1,2],'size':1}},
            'larger_sample':{'population':[0,1,2],'smaller':{'op':'fixed_sample','members':[1]},
                             'larger':{'op':'fixed_sample','members':[1,0]}},
            'frame_only':{'population':[0,1,2],'frame':[0,1],
                          'sampling':{'op':'uniform_subsets','frame':[0,1],'size':1}}},
        'options':[{'key':'A','text':'unbiased but not always exact','claim':{'op':'all','claims':[
                    {'op':'full_srs_sample_mean_is_design_unbiased'},
                    {'op':'not_all_single_srs_samples_equal_population_mean'}]}},
                   {'key':'B','text':'larger always no worse','claim':{'op':'larger_sample_cannot_have_larger_error_regardless_of_selection'}},
                   {'key':'C','text':'familiar means unbiased','claim':{'op':'frame_only_selection_guarantees_design_unbiased'}}]}


class MomentIdentityTests(unittest.TestCase):
    def test_binary_moments_match_exhaustive_uniform_subsets_for_every_small_count(self):
        for N in range(1,9):
            for count in range(N+1):
                values=[1]*count+[0]*(N-count);proof=M.BinarySRS(N,count)
                for n in range(1,N+1):
                    means=[Fraction(sum(values[i] for i in ids),n) for ids in combinations(range(N),n)]
                    mean=sum(means)/len(means);variance=sum((x-mean)**2 for x in means)/len(means)
                    self.assertEqual(proof.moments(n),(mean,variance))
                    if N>1:self.assertEqual(variance,Fraction(count,N)*(1-Fraction(count,N))*Fraction(N-n,n*(N-1)))

    def test_first_and_pair_member_inclusion_counts_include_n_one_and_n_N(self):
        for N in range(2,9):
            for n in range(1,N+1):
                samples=list(combinations(range(N),n))
                first=Fraction(sum(0 in s for s in samples),len(samples))
                pair=Fraction(sum(0 in s and 1 in s for s in samples),len(samples))
                self.assertEqual(first,Fraction(n,N));self.assertEqual(pair,Fraction(n*(n-1),N*(N-1)))
        self.assertIsNotNone(M.srs_moment_certificate())

    def test_singleton_population_and_full_census_are_deterministic_not_division_by_zero(self):
        for positive in (0,1):self.assertEqual(M.BinarySRS(1,positive).moments(1),(Fraction(positive),0))
        for N,Mn in ((2,1),(200,1),(200,199),(400,200)):
            self.assertEqual(M.BinarySRS(N,Mn).moments(N),(Fraction(Mn,N),0))
        result=M.execute_law(['7/3'],{'op':'uniform_subsets','frame':[0],'size':1})
        self.assertEqual(result.expectation,Fraction(7,3));self.assertEqual(result.variance,0)

    def test_empty_oversized_impossible_and_unicode_counts_do_not_enter_formulas(self):
        for N,Mn in ((0,0),(2,3),(2,-1),(True,0),('２００',10),(200,'2⁰')):
            with self.subTest(N=N,M=Mn),self.assertRaises(ValueError):M.BinarySRS(N,Mn)
        p=M.BinarySRS(200,100)
        for n in (0,-1,201,True,20.0,'20','②⓪'):
            with self.subTest(n=n),self.assertRaises(ValueError):p.moments(n)

    def test_nonconstant_values_mean_variance_matches_general_finite_population_identity(self):
        for values in ([1,2,7],[-2,'1/2',4,10],[3,3,3]):
            ys=[Fraction(x) for x in values];N=len(ys);mu=sum(ys)/N;v=sum((x-mu)**2 for x in ys)/N
            for n in range(1,N+1):
                r=M.execute_law(values,{'op':'uniform_subsets','frame':list(range(N)),'size':n})
                self.assertEqual(r.expectation,mu);self.assertEqual(r.variance,v*Fraction(N-n,n*(N-1)))


class VarianceComparisonTests(unittest.TestCase):
    def test_actual_counts_are_ranked_by_derived_design_variance(self):
        s=variance_spec();self.assertEqual(M.minimum_binary_variance(s),'sample200')
        p=M.VarianceComparison(s['population'],200,s['population_condition'],s['goal'])
        results=[p.plan(o['plan']) for o in s['options']]
        self.assertEqual([r.qualified for r in results],[False,True,True,False])
        self.assertTrue(all(r.variance is None for r in (results[0],results[3])))
        self.assertEqual(results[1].variance,Fraction(19,1596));self.assertEqual(results[2].variance,Fraction(1,1596))

    def test_N_200_endpoint_does_not_execute_the_impossible_200_person_local_plan(self):
        s=variance_spec(200,37);proof=M.VarianceComparison(s['population'],200,s['population_condition'],s['goal'])
        self.assertEqual(proof.plan(s['options'][2]['plan']).variance,0)
        # The local frame has100, requested count200. This is an unqualified
        # candidate offer, never simulated as a legal statistical sample.
        self.assertFalse(proof.plan(s['options'][0]['plan']).qualified)
        self.assertIsNone(proof.plan(s['options'][0]['plan']).variance)
        self.assertEqual(M.minimum_binary_variance(s),'sample200')

    def test_every_nondegenerate_count_strictly_improves_and_extremes_really_tie(self):
        for N in (200,201,400,10000):
            for count in (1,N//2,N-1):
                s=variance_spec(N,count);self.assertEqual(M.minimum_binary_variance(s),'sample200')
                self.assertGreater(M.BinarySRS(N,count).moments(20)[1],M.BinarySRS(N,count).moments(200)[1])
        for count in (0,400):
            s=variance_spec(400,count)
            with self.assertRaises(ValueError):M.minimum_binary_variance(s) # violates stated both-statuses premise
            s['population_condition']='no_additional_status_condition'
            self.assertEqual(M.BinarySRS(400,count).moments(20)[1],0)
            self.assertEqual(M.BinarySRS(400,count).moments(200)[1],0)
            with self.assertRaises(ValueError):M.minimum_binary_variance(s) # genuine two-qualified-design tie

    def test_candidate_order_keys_and_sample_sizes_not_letters_determine_winner(self):
        s=variance_spec();s['options'].reverse()
        for i,o in enumerate(s['options']):o.update(key=str(i),text='candidate'+str(i))
        self.assertEqual(M.minimum_binary_variance(s),'candidate1')
        s=variance_spec();s['options'][1]['plan']['size']=300
        self.assertEqual(M.minimum_binary_variance(s),'sample20') # its text is arbitrary; actual plan now300
        s=variance_spec();s['options'][0]['plan']=deepcopy(s['options'][2]['plan']);s['options'][0]['plan']['size']=400
        self.assertEqual(M.minimum_binary_variance(s),'optician')

    def test_a_frame_equal_to_population_is_not_rejected_by_its_role_name(self):
        s=variance_spec();s['options'][0]['plan']['frame']['intervals']=[[0,400]]
        with self.assertRaises(ValueError):M.minimum_binary_variance(s) # contradicts explicit proper-frame premise
        s['options'][0]['plan']=deepcopy(s['options'][2]['plan'])
        with self.assertRaises(ValueError):M.minimum_binary_variance(s) # now two equally good known full-SRS plans

    def test_nonfull_frame_uniform_design_is_not_ranked_as_if_it_estimates_full_school(self):
        s=variance_spec();s['options'][1]['plan']['frame']={'op':'interval_union','intervals':[[0,200]]}
        p=M.VarianceComparison(s['population'],200,s['population_condition'],s['goal'])
        self.assertFalse(p.plan(s['options'][1]['plan']).qualified)
        self.assertIsNone(p.plan(s['options'][1]['plan']).variance)
        self.assertEqual(M.minimum_binary_variance(s),'sample200')

    def test_missing_measurement_response_and_estimator_conditions_are_not_assumed(self):
        for field in ('data_model','goal','population_condition','minimum_population_size'):
            s=variance_spec();del s[field]
            with self.subTest(field=field),self.assertRaises(ValueError):M.minimum_binary_variance(s)
        s=variance_spec();s['data_model']='unknown_measurement_error_or_nonresponse'
        with self.assertRaises(ValueError):M.minimum_binary_variance(s)
        s=variance_spec();s['goal']['comparison']='minimum_total_cost'
        with self.assertRaises(ValueError):M.minimum_binary_variance(s)
        s=variance_spec();s['options'][1]['plan']['statistic']='unknown_estimator'
        with self.assertRaises(ValueError):M.minimum_binary_variance(s)

    def test_unknown_late_fields_counts_and_duplicate_or_no_qualified_candidates_fail_closed(self):
        for i in range(4):
            s=variance_spec();s['options'][i]['condition']='extra'
            with self.subTest(i=i),self.assertRaises(ValueError):M.minimum_binary_variance(s)
        s=variance_spec();s['options'][0]['plan']['requested_count']['extra']='bad'
        with self.assertRaises(ValueError):M.minimum_binary_variance(s)
        for count in (0,401,True,'２0'):
            s=variance_spec();s['options'][1]['plan']['size']=count
            with self.subTest(count=count),self.assertRaises(ValueError):M.minimum_binary_variance(s)
        s=variance_spec();s['options'][1]['plan']['size']=200
        with self.assertRaises(ValueError):M.minimum_binary_variance(s)
        s=variance_spec();s['options']=[s['options'][0],s['options'][3]]
        with self.assertRaises(ValueError):M.minimum_binary_variance(s)


class MeanClaimTests(unittest.TestCase):
    def test_actual_mean_claims_use_global_identity_and_executed_countermodels(self):
        s=mean_spec();self.assertEqual(M.mean_design_claims(s),'unbiased but not always exact')
        p=M.MeanClaims(s['counterexamples'])
        self.assertEqual([p.claim(o['claim']) for o in s['options']],[True,False,False])
        self.assertEqual(p.one.expectation,1);self.assertTrue(any(m!=1 for _,_,m in p.one.samples))
        self.assertEqual(p.small.samples[0][2],1);self.assertEqual(p.large.samples[0][2],Fraction(1,2))
        self.assertEqual(p.frame_law.expectation,Fraction(1,2));self.assertEqual(p.frame_law.population_mean,1)

    def test_counterpopulation_values_can_shift_scale_and_reorder_without_a_person_label_rule(self):
        for factor,shift in ((2,7),(-3,2),(Fraction(1,3),Fraction(-2,5))):
            s=mean_spec()
            for witness in s['counterexamples'].values():witness['population']=[str(factor*x+shift) for x in witness['population']]
            s['options'].reverse();self.assertEqual(M.mean_design_claims(s),'unbiased but not always exact')
        s=mean_spec();s['options'][0]['claim']=deepcopy(s['options'][1]['claim']);s['options'][2]['claim']={
            'op':'full_srs_sample_mean_is_design_unbiased'}
        self.assertEqual(M.mean_design_claims(s),'familiar means unbiased')

    def test_single_error_witness_cannot_be_a_census_or_constant_population(self):
        for mutate in (lambda x:x['sampling'].update(size=3),lambda x:x.update(population=[1,1,1])):
            s=mean_spec();mutate(s['counterexamples']['single_srs_error'])
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):M.mean_design_claims(s)
        s=mean_spec();s['counterexamples']['single_srs_error']['sampling']['frame']=[0,1]
        with self.assertRaises(ValueError):M.mean_design_claims(s)

    def test_bigger_sample_counterexample_must_be_larger_and_really_worse(self):
        s=mean_spec();s['counterexamples']['larger_sample']['larger']['members']=[2]
        with self.assertRaises(ValueError):M.mean_design_claims(s)
        s=mean_spec();s['counterexamples']['larger_sample']['larger']['members']=[0,2]
        with self.assertRaises(ValueError):M.mean_design_claims(s) # mean1, not a distinguishing counterexample

    def test_frame_counterexample_must_respect_its_set_and_have_nonzero_design_bias(self):
        s=mean_spec();s['counterexamples']['frame_only']['frame']=[1,2]
        with self.assertRaises(ValueError):M.mean_design_claims(s)
        s=mean_spec();s['counterexamples']['frame_only']['sampling']['frame']=[0,1,2];s['counterexamples']['frame_only']['frame']=[0,1,2]
        with self.assertRaises(ValueError):M.mean_design_claims(s) # full SRS is unbiased, not a disproof

    def test_empty_repeated_out_of_domain_indices_and_numeric_words_are_not_simplified_away(self):
        for sampling in ({'op':'uniform_subsets','frame':[0,1,2],'size':0},
                         {'op':'uniform_subsets','frame':[0,1,2],'size':4},
                         {'op':'fixed_sample','members':[0,0]}, {'op':'fixed_sample','members':[3]}):
            with self.subTest(sampling=sampling),self.assertRaises(ValueError):M.execute_law([0,1,2],sampling)
        for values in ([],[True],[1.0],['1。5'],['①'],['1/(x-x)'],['1/0']):
            with self.subTest(values=values),self.assertRaises(ValueError):M.execute_law(values,{'op':'fixed_sample','members':[0]})
        r=M.execute_law(['１','２','３'],{'op':'uniform_subsets','frame':[0,1,2],'size':1})
        self.assertEqual(r.expectation,2)

    def test_all_unknown_claims_and_late_assertions_reject_even_if_already_false(self):
        for i in range(3):
            s=mean_spec();s['options'][i]['condition']='extra'
            with self.subTest(i=i),self.assertRaises(ValueError):M.mean_design_claims(s)
        s=mean_spec();s['options'][1]['claim']={'op':'all','claims':[s['options'][1]['claim'],{'op':'unknown'}]}
        with self.assertRaises(ValueError):M.mean_design_claims(s)
        s=mean_spec();s['counterexamples']['larger_sample']['smaller']['extra']='bad'
        with self.assertRaises(ValueError):M.mean_design_claims(s)
        s=mean_spec();s['data_model']='unmeasured_real_values'
        with self.assertRaises(ValueError):M.mean_design_claims(s)

    def test_duplicate_or_missing_true_claim_and_excessive_depth_reject(self):
        s=mean_spec();other=deepcopy(s['options'][0]);other['key']='other';s['options'].append(other)
        with self.assertRaises(ValueError):M.mean_design_claims(s)
        s=mean_spec();s['options'].pop(0)
        with self.assertRaises(ValueError):M.mean_design_claims(s)
        s=mean_spec();node=s['options'][0]['claim']
        for _ in range(70):node={'op':'all','claims':[node]}
        s['options'][0]['claim']=node
        with self.assertRaises(ValueError):M.mean_design_claims(s)

    def test_both_actual_handlers_fit_the_cold_two_second_budget(self):
        for handler,spec in ((M.minimum_binary_variance,variance_spec()),(M.mean_design_claims,mean_spec())):
            M.srs_moment_certificate.cache_clear();start=time.perf_counter();handler(spec)
            self.assertLess(time.perf_counter()-start,2)


if __name__=='__main__':unittest.main()
