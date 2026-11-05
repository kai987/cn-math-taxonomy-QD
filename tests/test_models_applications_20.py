"""Concrete finite supports, arbitrary counts and strict sampling-law domains."""
from copy import deepcopy
from fractions import Fraction
from itertools import combinations
from math import comb
from pathlib import Path
import sys
import time
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import models_applications_20 as M


def frame(name):return {'op':'frame','name':name}
def intervals(*rows):return {'op':'interval_union','intervals':[list(row) for row in rows]}
def restricted(name):return {'op':'restricted_to_frame','frame':frame(name)}
def uniform(ref,n):return {'op':'uniform_without_replacement','frame':ref,'size':n}

def stratified_spec():
    return {'kind':'app20_positive_inclusion_support','population':{'op':'index_range','size':1200},
        'frames':{'g7':intervals((0,400)),'g8':intervals((400,800)),'g9':intervals((800,1200)),
                  'team':intervals((0,120)),'volunteers':intervals((300,600))},
        'frame_constraints':[{'frame':name,'relation':'nonempty_proper_subset'} for name in ('team','g7','volunteers')],
        'target':'every_population_member_has_positive_inclusion_probability',
        'options':[{'key':'A','text':'all grades','sampling':{'op':'stratified_uniform_without_replacement',
                     'strata':[{'frame':frame(name),'size':40} for name in ('g7','g8','g9')]}},
                   {'key':'B','text':'team','sampling':restricted('team')},
                   {'key':'C','text':'grade7','sampling':restricted('g7')},
                   {'key':'D','text':'volunteers','sampling':restricted('volunteers')}]}


def whole_school_spec():
    return {'kind':'app20_positive_inclusion_support','population':{'op':'index_range','size':200},
        'frames':{'basketball':intervals((0,30)),'grade7':intervals((0,80)),
                  'highest':intervals((0,10),(80,90))},
        'frame_constraints':[{'frame':name,'relation':'nonempty_proper_subset'} for name in ('basketball','grade7','highest')],
        'target':'every_population_member_has_positive_inclusion_probability',
        'options':[{'key':'A','text':'basketball','sampling':restricted('basketball')},
                   {'key':'B','text':'grade7','sampling':restricted('grade7')},
                   {'key':'C','text':'highest','sampling':restricted('highest')},
                   {'key':'D','text':'whole school','sampling':uniform({'op':'population'},20)}]}


def context(spec):return M.Coverage(spec['population'],spec['frames'],spec['frame_constraints'])


class InclusionSupportTests(unittest.TestCase):
    def test_actual_stratified_and_whole_population_supports_are_computed(self):
        s=stratified_spec();c=context(s);results=[c.sampling(o['sampling']) for o in s['options']]
        self.assertEqual([r.all_positive for r in results],[True,False,False,False])
        self.assertEqual(results[0].sample_size,120)
        self.assertEqual({results[0].probability(i) for i in range(1200)},{Fraction(1,10)})
        self.assertEqual(results[1].support.size,120);self.assertEqual(results[1].probability(120),0)
        with self.assertRaises(ValueError):results[1].probability(0) # internal law remains unknown
        self.assertEqual(M.positive_inclusion_support(s),'all grades')
        s=whole_school_spec();self.assertEqual(M.positive_inclusion_support(s),'whole school')

    def test_combination_identity_matches_all_small_uniform_subset_enumerations(self):
        for n in range(1,9):
            c=M.Coverage({'op':'index_range','size':n},{},[])
            for k in range(n+1):
                p=c.sampling(uniform({'op':'population'},k));samples=list(combinations(range(n),k))
                self.assertEqual(len(samples),comb(n,k))
                self.assertEqual(p.all_positive,k>0)
                for member in range(n):
                    actual=Fraction(sum(member in sample for sample in samples),len(samples))
                    self.assertEqual(p.probability(member),actual)
                    self.assertEqual(actual,Fraction(k,n))

    def test_n_equals_population_size_endpoint_has_probability_one(self):
        for n in (1,2,100,10**30):
            c=M.Coverage({'op':'index_range','size':n},{},[]);p=c.sampling(uniform({'op':'population'},n))
            self.assertTrue(p.all_positive);self.assertEqual(p.probability(0),1);self.assertEqual(p.probability(n-1),1)
        self.assertIsNotNone(M.inclusion_certificate())

    def test_disconnected_and_overlapping_interval_fragments_are_real_sets_not_double_counts(self):
        c=M.Coverage({'op':'index_range','size':10},{'parts':intervals((0,1),(3,6),(9,10))},[])
        p=c.sampling(uniform(frame('parts'),2))
        self.assertEqual(p.support.size,5);self.assertFalse(p.all_positive)
        self.assertEqual([p.probability(i) for i in range(10)],
                         [Fraction(2,5),0,0,Fraction(2,5),Fraction(2,5),Fraction(2,5),0,0,0,Fraction(2,5)])
        merged=M.finite_set(10,[[5,7],[0,4],[2,6],[7,8]])
        self.assertEqual(merged.intervals,((0,8),));self.assertEqual(merged.size,8)
        self.assertEqual(merged.complement().intervals,((8,10),))

    def test_every_small_two_stratum_count_and_zero_quota_matches_its_marginal(self):
        for n in range(2,9):
            for cut in range(1,n):
                c=M.Coverage({'op':'index_range','size':n},{'left':intervals((0,cut)),'right':intervals((cut,n))},[])
                for a in range(cut+1):
                    for b in range(n-cut+1):
                        p=c.sampling({'op':'stratified_uniform_without_replacement',
                            'strata':[{'frame':frame('left'),'size':a},{'frame':frame('right'),'size':b}]})
                        self.assertEqual(p.all_positive,a>0 and b>0)
                        for i in range(n):self.assertEqual(p.probability(i),Fraction(a,cut) if i<cut else Fraction(b,n-cut))

    def test_unequal_positive_sampling_rates_do_not_become_a_global_srs_or_unbiased_mean(self):
        s=stratified_spec();s['frames']['g7']=intervals((0,1100));s['frames']['g8']=intervals((1100,1150));s['frames']['g9']=intervals((1150,1200))
        p=context(s).sampling(s['options'][0]['sampling'])
        self.assertTrue(p.all_positive);self.assertEqual(p.probability(0),Fraction(2,55));self.assertEqual(p.probability(1199),Fraction(4,5))
        self.assertNotEqual(p.probability(0),p.probability(1199))
        # A legal binary indicator constant within each grade. Full coverage
        # alone does not make an unweighted estimate unbiased.
        self.assertEqual(Fraction(80,120)-Fraction(100,1200),Fraction(7,12))
        self.assertEqual(M.positive_inclusion_support(s),'all grades')

    def test_stratum_marginals_do_not_require_independent_selections_between_strata(self):
        c=M.Coverage({'op':'index_range','size':4},{'l':intervals((0,2)),'r':intervals((2,4))},[])
        p=c.sampling({'op':'stratified_uniform_without_replacement',
            'strata':[{'frame':frame('l'),'size':1},{'frame':frame('r'),'size':1}]})
        correlated=[(0,2),(1,3)] # each component uniform; joint is not the product of four pairs
        for i in range(4):self.assertEqual(sum(Fraction(1,2) for sample in correlated if i in sample),p.probability(i))
        self.assertTrue(p.all_positive)

    def test_frame_names_and_option_order_do_not_determine_the_selected_rule(self):
        s=whole_school_spec();s['options'].reverse()
        for i,o in enumerate(s['options']):o.update(key=str(i),text='option'+str(i))
        self.assertEqual(M.positive_inclusion_support(s),'option0')
        # A group called highest MAY be all members if that is what the set
        # says. Remove its proper-subset premise and supply a known uniform
        # law; it becomes a real alternative, not a hard-coded false label.
        s=whole_school_spec();s['frame_constraints']=[x for x in s['frame_constraints'] if x['frame']!='highest']
        s['frames']['highest']=intervals((0,200));s['options'][2]['sampling']=uniform(frame('highest'),1)
        s['options'][3]['sampling']=restricted('basketball')
        self.assertEqual(M.positive_inclusion_support(s),'highest')

    def test_whole_frame_without_a_sampling_law_does_not_prove_positive_inclusion(self):
        s=whole_school_spec();s['frame_constraints']=[x for x in s['frame_constraints'] if x['frame']!='highest']
        s['frames']['highest']=intervals((0,200))
        p=context(s).sampling(s['options'][2]['sampling'])
        self.assertEqual(p.support.size,200)
        with self.assertRaises(ValueError):p.probability(0)
        with self.assertRaises(ValueError):p.all_positive
        with self.assertRaises(ValueError):M.positive_inclusion_support(s)

    def test_all_tied_highest_group_cannot_silently_satisfy_a_proper_group_premise(self):
        s=whole_school_spec();s['frames']['highest']=intervals((0,200))
        with self.assertRaises(ValueError):M.positive_inclusion_support(s)
        s['frame_constraints']=[x for x in s['frame_constraints'] if x['frame']!='highest']
        s['options'][2]['sampling']=uniform(frame('highest'),1)
        with self.assertRaises(ValueError):M.positive_inclusion_support(s) # two complete-support choices

    def test_zero_quotas_are_legal_but_do_not_cover_their_nonempty_stratum(self):
        s=stratified_spec();s['options'][0]['sampling']['strata'][0]['size']=0
        p=context(s).sampling(s['options'][0]['sampling'])
        self.assertFalse(p.all_positive);self.assertEqual(p.probability(0),0);self.assertGreater(p.probability(1199),0)
        with self.assertRaises(ValueError):M.positive_inclusion_support(s)
        s=whole_school_spec();s['options'][3]['sampling']['size']=0
        p=context(s).sampling(s['options'][3]['sampling']);self.assertEqual(p.support.size,0)
        self.assertEqual(p.probability(199),0);self.assertFalse(p.all_positive)

    def test_empty_overlapping_incomplete_or_duplicated_strata_and_oversized_samples_reject(self):
        mutations=[lambda s:s['options'][0]['sampling'].update(strata=[]),
            lambda s:s['frames']['g8'].update(intervals=[]),
            lambda s:s['frames']['g8'].update(intervals=[[399,800]]),
            lambda s:s['frames']['g8'].update(intervals=[[401,800]]),
            lambda s:s['options'][0]['sampling']['strata'].append(deepcopy(s['options'][0]['sampling']['strata'][0])),
            lambda s:s['options'][0]['sampling']['strata'][0].update(size=401)]
        for mutate in mutations:
            s=stratified_spec();mutate(s)
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):M.positive_inclusion_support(s)
        s=whole_school_spec();s['options'][3]['sampling']['size']=201
        with self.assertRaises(ValueError):M.positive_inclusion_support(s)

    def test_unknown_fields_even_inside_nonmatching_candidates_are_never_ignored(self):
        for i in range(4):
            s=whole_school_spec();s['options'][i]['condition']='extra'
            with self.subTest(i=i),self.assertRaises(ValueError):M.positive_inclusion_support(s)
        for target in ('population','frames','frame_constraints'):
            s=whole_school_spec()
            if target=='population':s['population']['extra']=True
            elif target=='frames':s['frames']['basketball']['extra']=True
            else:s['frame_constraints'][0]['extra']=True
            with self.subTest(target=target),self.assertRaises(ValueError):M.positive_inclusion_support(s)
        s=whole_school_spec();s['options'][0]['sampling']['frame']['unknown']='bad'
        with self.assertRaises(ValueError):M.positive_inclusion_support(s)
        s=whole_school_spec();s['options'][0]['sampling']['op']='unspecified_random'
        with self.assertRaises(ValueError):M.positive_inclusion_support(s)
        s=stratified_spec();s['options'][0]['sampling']['strata'][2]['extra']='bad'
        with self.assertRaises(ValueError):M.positive_inclusion_support(s)

    def test_missing_or_unknown_domain_constraints_do_not_get_invented(self):
        for field in ('target','population','frames','frame_constraints'):
            s=whole_school_spec();del s[field]
            with self.subTest(field=field),self.assertRaises(ValueError):M.positive_inclusion_support(s)
        s=whole_school_spec();s['target']='smallest_bias'
        with self.assertRaises(ValueError):M.positive_inclusion_support(s)
        s=whole_school_spec();s['frame_constraints'][0]['relation']='assume_biased'
        with self.assertRaises(ValueError):M.positive_inclusion_support(s)
        s=whole_school_spec();s['options'][0]['sampling']['frame']['name']='not_declared'
        with self.assertRaises(ValueError):M.positive_inclusion_support(s)

    def test_strict_integer_lexing_and_original_finite_set_domains(self):
        for bad in (True,-1,0,200.0,'200','２００','2⁰⁰','②⓪⓪','200。0'):
            s=whole_school_spec();s['population']['size']=bad
            with self.subTest(bad=bad),self.assertRaises(ValueError):M.positive_inclusion_support(s)
        for bad in (True,-1,1.0,'１','1/0'):
            s=whole_school_spec();s['options'][3]['sampling']['size']=bad
            with self.subTest(bad=bad),self.assertRaises(ValueError):M.positive_inclusion_support(s)
        for interval in ([-1,3],[2,2],[2,201],[3,2],[True,3]):
            s=whole_school_spec();s['frames']['basketball']['intervals']=[interval]
            with self.subTest(interval=interval),self.assertRaises(ValueError):M.positive_inclusion_support(s)

    def test_invalid_empty_frames_duplicate_constraints_and_member_queries_reject(self):
        s=whole_school_spec();s['frames']['basketball']['intervals']=[]
        with self.assertRaises(ValueError):M.positive_inclusion_support(s)
        s=whole_school_spec();s['frame_constraints'].append(deepcopy(s['frame_constraints'][0]))
        with self.assertRaises(ValueError):M.positive_inclusion_support(s)
        s=whole_school_spec();p=context(s).sampling(s['options'][3]['sampling'])
        for i in (-1,200,True,'0'):
            with self.subTest(i=i),self.assertRaises(ValueError):p.probability(i)

    def test_duplicate_and_absent_complete_rules_fail_unique_selection(self):
        s=whole_school_spec();extra=deepcopy(s['options'][3]);extra['key']='extra';s['options'].append(extra)
        with self.assertRaises(ValueError):M.positive_inclusion_support(s)
        s=whole_school_spec();s['options'].pop(3)
        with self.assertRaises(ValueError):M.positive_inclusion_support(s)

    def test_the_symbolic_all_count_certificate_is_fast_on_cold_start(self):
        M.inclusion_certificate.cache_clear();started=time.perf_counter()
        self.assertEqual(M.positive_inclusion_support(whole_school_spec()),'whole school')
        self.assertLess(time.perf_counter()-started,2)


if __name__=='__main__':unittest.main()
