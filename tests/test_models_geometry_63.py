"""Adversarial and metamorphic checks for the structural63 proof kernels."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import models_geometry_63 as M


def options(rows):return [dict(key=str(i),text=str(i),**r) for i,r in enumerate(rows)]
def D(a,b):return {'op':'distance','points':[a,b]}
def Ang(a,b,c):return {'op':'angle','points':[a,b,c]}
def Add(*xs):return {'op':'add','items':list(xs)}
def Eq(a,b):return {'op':'eq','left':a,'right':b}
def Le(a,b):return {'op':'le','left':a,'right':b}
def hyp(a,b):return {'rule':'hypothesis','statement':[a,b]}


def metric_spec():
    path=Le(D('a','b'),Add(D('a','p'),D('p','b')))
    return {'goal':path,'available_hypotheses':[],'options':options([
      {'hypotheses':[{'op':'on_line','point':'q','line':'l'}],
       'conclusion':Le({'op':'point_line_distance','point':'p','line':'l'},D('p','q'))},
      {'hypotheses':[{'op':'nondegenerate_triangle','points':['a','b','c']}],
       'conclusion':Eq(Add(Ang('a','b','c'),Ang('b','c','a'),Ang('c','a','b')),{'op':'number','value':180})},
      {'hypotheses':[{'op':'nondegenerate_triangle','points':['a','b','c']},Eq(Ang('a','b','c'),Ang('b','c','a'))],
       'conclusion':Eq(D('a','b'),D('a','c'))},
      {'hypotheses':[],'conclusion':path}])}


def rename_points(value,mapping):
    if isinstance(value,list):return [rename_points(x,mapping) for x in value]
    if not isinstance(value,dict):return value
    result={k:rename_points(v,mapping) for k,v in value.items()}
    if 'points' in value:result['points']=[mapping.get(x,x) for x in value['points']]
    for field in ('point','line'):
        if field in value:result[field]=mapping.get(value[field],value[field])
    return result


def process_spec():
    const=lambda n,d:{'op':'constant','value':n,'dimension':d}
    var=lambda x:{'op':'variable','symbol':x}
    return {'family':'constant_outflow_reservoir','variables':{'v':[1,0],'t':[0,1]},'defined_symbol':'v',
      'expression':{'op':'subtract','left':const(100,[1,0]),'right':{'op':'multiply','left':const(4,[1,-1]),'right':var('t')}},
      'options':options([{'quantity':var('v')},{'quantity':const(100,[1,0])},
                        {'quantity':const(4,[1,-1])},{'quantity':var('t')}])}


class HistogramTests(unittest.TestCase):
    def specification(self):
        return {'construction':'frequency_rectangles','counterexample':{'data':[1,1,1,6,6],'bins':[[0,5],[5,10]]},
          'options':options([{'quantity':s} for s in ('bin_width','total_count','bin_midpoint','bin_frequency')])}

    def test_height_is_coordinate_difference_not_width_or_total(self):
        self.assertEqual(M.histogram_height(self.specification()),'3')
        s=self.specification();s['counterexample']={'data':[2,2,8],'bins':[[0,7],[7,14]]}
        self.assertEqual(M.histogram_height(s),'3')
        s['options'].reverse();self.assertEqual(M.histogram_height(s),'3')

    def test_invalid_histogram_or_nonrefuting_example_is_unresolved(self):
        for data,bins in [([1],[[0,5],[5,11]]),([1],[[0,5],[4,9]]),([10],[[0,5],[5,10]])]:
            s=self.specification();s['counterexample']={'data':data,'bins':bins}
            with self.subTest(data=data,bins=bins),self.assertRaises(ValueError):M.histogram_height(s)
        s=self.specification();s['counterexample']={'data':[1]*5+[6],'bins':[[0,5],[5,10]]}
        with self.assertRaises(ValueError):M.histogram_height(s) # height=width, so it does not refute that candidate
        s=self.specification();s['construction']='density_rectangles'
        with self.assertRaises(ValueError):M.histogram_height(s)


class AntecedentAndProofTests(unittest.TestCase):
    def test_geometric_premise_and_equal_conclusion_have_distinct_types(self):
        vertical={'op':'opposite_ray_angles','arguments':['a','b']};equal={'op':'equal_angles','arguments':['a','b']}
        s={'domain':'two_distinct_intersecting_lines','theorem':{'premise':vertical,'conclusion':equal},
           'options':options([{'predicate':equal},{'predicate':vertical}])}
        self.assertEqual(M.theorem_antecedent(s),'1')
        s['options'][1]['predicate']={'op':'opposite_ray_angles','arguments':['b','a']}
        self.assertEqual(M.theorem_antecedent(s),'1')
        s['theorem']={'premise':equal,'conclusion':vertical}
        with self.assertRaises(ValueError):M.theorem_antecedent(s)

    def test_degenerate_or_unknown_angle_predicates_fail_closed(self):
        with self.assertRaises(ValueError):M.predicate({'op':'equal_angles','arguments':['a','a']})
        with self.assertRaises(ValueError):M.predicate({'op':'truth','arguments':['a','b']})
        with self.assertRaises(ValueError):M.predicate({'op':'equal_angles','arguments':[True,False]})

    def test_assumptions_symmetry_transitivity_and_lemma_reuse_are_checked(self):
        s={'options':options([
          {'evidence':'equality_certificate','hypotheses':[['a','b']],'goal':['a','b'],'proof':hyp('a','b')},
          {'evidence':'equality_certificate','hypotheses':[['a','b']],'goal':['b','a'],'proof':{'rule':'symmetric','from':hyp('a','b')}},
          {'evidence':'quantized_observation','lengths':[1,'1001/1000'],'resolution':'1/100'},
          {'evidence':'equality_certificate','hypotheses':[['a','b'],['b','c']],'goal':['a','c'],
           'lemmas':{'l':{'rule':'transitive','first':hyp('a','b'),'second':hyp('b','c')}},'proof':{'rule':'lemma','id':'l'}}])}
        self.assertEqual(M.proof_evidence(s),'2')
        s['options'][0]['hypotheses']=[]
        with self.assertRaises(ValueError):M.proof_evidence(s)

    def test_cyclic_unproved_or_wrong_middle_lemma_is_not_trusted(self):
        for proof,lemmas in [({'rule':'lemma','id':'x'},{}),
          ({'rule':'lemma','id':'x'},{'x':{'rule':'lemma','id':'x'}}),
          ({'rule':'transitive','first':hyp('a','b'),'second':hyp('a','c')},{})]:
            with self.subTest(proof=proof),self.assertRaises(ValueError):
                M.checked_equality(proof,[('a','b'),('a','c')],lemmas)

    def test_visual_refutation_needs_actual_unequal_but_indistinguishable_lengths(self):
        s={'options':options([{'evidence':'quantized_observation','lengths':[1,'1001/1000'],'resolution':'1/100'}])}
        self.assertEqual(M.proof_evidence(s),'0')
        for lengths,step in [([1,1],'1/100'),([1,2],'1/100'),([1,'1001/1000'],0)]:
            s['options'][0].update(lengths=lengths,resolution=step)
            with self.subTest(lengths=lengths),self.assertRaises(ValueError):M.proof_evidence(s)


class MetricRuleTests(unittest.TestCase):
    def test_actual_path_rule_and_candidate_reordering(self):
        s=metric_spec();self.assertEqual(M.metric_final_step(s),'3')
        s['options'].reverse();self.assertEqual(M.metric_final_step(s),'3')

    def test_goal_and_theorem_schema_can_be_independently_alpha_renamed(self):
        s=metric_spec();s['goal']=rename_points(s['goal'],{'a':'x','b':'y','p':'z'})
        self.assertEqual(M.metric_final_step(s),'3')
        for o in s['options']:
            o['conclusion']=rename_points(o['conclusion'],{'a':'f','b':'g','c':'h','p':'j','q':'k','l':'m'})
            o['hypotheses']=rename_points(o['hypotheses'],{'a':'f','b':'g','c':'h','p':'j','q':'k','l':'m'})
        self.assertEqual(M.metric_final_step(s),'3')

    def test_commutative_distance_and_sum_order_do_not_change_the_goal(self):
        s=metric_spec();s['goal']['left']['points'].reverse();s['goal']['right']['items'].reverse()
        for t in s['goal']['right']['items']:t['points'].reverse()
        self.assertEqual(M.metric_final_step(s),'3')

    def test_reversing_only_one_angles_endpoints_preserves_its_vertex(self):
        s=metric_spec()
        right=s['options'][2]['hypotheses'][1]['right']
        right['points']=['a','c','b'] # BCA and ACB are the same angle at C.
        self.assertEqual(M.metric_final_step(s),'3')
        right['points']=['c','a','b'] # Changing the middle point changes the angle.
        with self.assertRaises(ValueError):M.metric_final_step(s)

    def test_zero_leg_at_endpoint_is_covered_by_unconditional_triangle_bound(self):
        s=metric_spec();s['goal']=rename_points(s['goal'],{'p':'a'})
        self.assertEqual(M.metric_final_step(s),'3')

    def test_wrong_path_endpoint_or_comparison_target_is_rejected(self):
        for goal in (Le(D('a','b'),Add(D('a','p'),D('p','c'))),Eq(D('a','b'),D('a','c'))):
            s=metric_spec();s['goal']=goal
            with self.subTest(goal=goal),self.assertRaises(ValueError):M.metric_final_step(s)

    def test_conditional_rules_cannot_lose_geometric_hypotheses(self):
        for index in (0,1,2):
            s=metric_spec();s['options'][index]['hypotheses']=[]
            with self.subTest(index=index),self.assertRaises(ValueError):M.metric_final_step(s)
        s=metric_spec();s['options'][2]['hypotheses']=s['options'][2]['hypotheses'][1:]
        with self.assertRaises(ValueError):M.metric_final_step(s) # equal zero angles in a collinear triple are not sufficient
        s=metric_spec();s['options'][2]['hypotheses']=s['options'][2]['hypotheses'][:1]
        with self.assertRaises(ValueError):M.metric_final_step(s) # triangle alone gives no side equality

    def test_unverified_arithmetic_or_angle_theorem_is_not_a_false_distractor(self):
        s=metric_spec();s['options'][1]['conclusion']['right']['value']=179
        with self.assertRaises(ValueError):M.metric_final_step(s)
        s=metric_spec();s['options'][3]['conclusion']=Le(Add(D('a','p'),D('p','b')),D('a','b'))
        with self.assertRaises(ValueError):M.metric_final_step(s)


class ProcessTests(unittest.TestCase):
    def test_free_argument_is_derived_from_dimension_checked_definition(self):
        s=process_spec();self.assertEqual(M.process_argument(s),'3')
        s['variables']={'w':[1,0],'s':[0,1]};s['defined_symbol']='w'
        s['expression']['right']['right']['symbol']='s'
        s['options'][0]['quantity']['symbol']='w';s['options'][3]['quantity']['symbol']='s'
        self.assertEqual(M.process_argument(s),'3')

    def test_reservoir_requires_positive_initial_amount_and_rate(self):
        for field,value in [('initial',0),('initial',-1),('rate',0),('rate',-1)]:
            s=process_spec()
            if field=='initial':s['expression']['left']['value']=value
            else:s['expression']['right']['left']['value']=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):M.process_argument(s)

    def test_wrong_units_output_feedback_or_undefined_scalar_fail_closed(self):
        s=process_spec();s['expression']['right']['left']['dimension']=[1,0]
        with self.assertRaises(ValueError):M.process_argument(s)
        s=process_spec();s['expression']['right']['right']['symbol']='v'
        with self.assertRaises(ValueError):M.process_argument(s)
        s=process_spec();s['expression']['left']['value']="__import__('os')"
        with self.assertRaises((ValueError,SyntaxError)):M.process_argument(s)


class TrimmedMeanTests(unittest.TestCase):
    def specification(self):
        return {'operation':'remove_one_min_and_one_max','domain':'at_least_three_real_scores',
          'options':options([{'claim':'reduced_outward_extreme_influence'},
           {'claim':'always_increases_total','counterexample':[0,1,10]},
           {'claim':'fewer_judges'},
           {'claim':'unique_mode','counterexample':[0,1,1,2,2,3]}])}

    def test_global_outward_cancellation_and_all_candidates(self):
        self.assertEqual(M.trimmed_mean_robustness(self.specification()),'0')
        # Ties do not invalidate the outward-max proof: one10 becomes20;
        # exactly one maximum is removed in either score vector.
        def trim(xs):return sum(sorted(xs)[1:-1])/(len(xs)-2)
        self.assertEqual(trim([0,10,10,10]),trim([0,10,10,20]))
        self.assertEqual(trim([0,0,0,10]),trim([-10,0,0,10]))
        self.assertEqual(trim([5,5,5]),trim([5,5,10]))

    def test_invalid_nonrefuting_counterexamples_are_rejected(self):
        s=self.specification();s['options'][1]['counterexample']=[0,9,10]
        with self.assertRaises(ValueError):M.trimmed_mean_robustness(s) # trimmed mean9 is above raw19/3
        s=self.specification();s['options'][3]['counterexample']=[0,1,1,1,2]
        with self.assertRaises(ValueError):M.trimmed_mean_robustness(s)
        s=self.specification();s['options'][1]['counterexample']=[0,10]
        with self.assertRaises(ValueError):M.trimmed_mean_robustness(s)

    def test_protocol_and_unknown_claims_fail_closed(self):
        s=self.specification();s['operation']='remove_all_extreme_ties'
        with self.assertRaises(ValueError):M.trimmed_mean_robustness(s)
        s=self.specification();s['options'][2]['claim']='unproved_effect'
        with self.assertRaises(ValueError):M.trimmed_mean_robustness(s)


if __name__=='__main__':unittest.main()
