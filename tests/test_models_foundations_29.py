"""Parameter, original-domain and nongeometric-countermodel regressions."""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import sys
import unittest
import sympy as S
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import models_foundations_29 as M


def length(part,lane):return {'op':'length','part':part,'lane':lane}
def op(name,left,right):return {'op':name,'left':left,'right':right}
def gap():return op('subtract',length('curved_total','outer'),length('curved_total','inner'))


def track_spec(distance=400):
    return {'kind':'f29_track_explanation_guarantee','race_distance':distance,
        'target':'guarantee_equal_remaining_distance',
        'geometry':{'straight_pieces':2,'arc_pieces':2,'arc_shape':'semicircle',
            'straight_relation':'equal_across_lanes','radius_relation':'outer_strictly_larger',
            'finish_relation':'shared_finish_line','advance_measure':'along_lane_forward_distance',
            'reference_lap':'inner_full_lap'},
        'options':[
          {'key':'A','text':'fitness','explanation':{'premises':[{'op':'independent_claim','name':'fitness_advantage'}],
            'advance_policy':{'op':'unspecified'},'counterexample':{'shape_ratio':1,'extra_arc':1,'advance':'1/2'}}},
          {'key':'B','text':'shorter straight','explanation':{'premises':[op('less',length('straight_total','outer'),length('straight_total','inner'))],
            'advance_policy':{'op':'unspecified'},'counterexample':None}},
          {'key':'C','text':'appearance','explanation':{'premises':[{'op':'independent_claim','name':'aesthetic_purpose'}],
            'advance_policy':{'op':'unspecified'},'counterexample':{'shape_ratio':2,'extra_arc':1,'advance':'1/2'}}},
          {'key':'D','text':'compensate extra arc','explanation':{'premises':[op('greater',length('curved_total','outer'),length('curved_total','inner'))],
            'advance_policy':gap(),'counterexample':None}}]}


def action(source,variable,into,constant,other,coefficient):
    return {'op':'isolate_then_substitute','from':source,'variable':variable,'into':into,
            'rhs':{'constant':constant,'coefficients':{other:coefficient}}}


def substitution_spec(x='x',y='y'):
    return {'kind':'f29_integral_substitution','domain':'all_real','variables':[x,y],
        'target':'equivalent_integral_linear_isolation_then_substitute',
        'equations':[{'coefficients':{x:3,y:1},'rhs':7},{'coefficients':{x:2,y:-3},'rhs':1}],
        'options':[{'key':'A','text':'isolate y first','program':action(0,y,1,7,x,-3)},
                   {'key':'B','text':'isolate x second','program':action(1,x,0,'1/2',y,'3/2')},
                   {'key':'C','text':'isolate y second','program':action(1,y,0,'-1/3',x,'2/3')}]}


class RouteGuaranteeTests(unittest.TestCase):
    def test_compensation_and_countermodels_are_computed(self):
        spec=track_spec();proof=M.TrackGuarantee(spec['geometry'],400,spec['target'])
        results=[proof.inspect(o['explanation']) for o in spec['options']]
        self.assertEqual([r['guarantees'] for r in results],[False,False,False,True])
        self.assertEqual(results[0]['external_valuation'],{'fitness_advantage':True})
        self.assertEqual(results[2]['external_valuation'],{'aesthetic_purpose':True})
        self.assertEqual(S.cancel(results[3]['advance']-proof.g),0)
        self.assertEqual(M.track_explanation(spec),'compensate extra arc')

    def test_every_positive_track_is_covered_by_the_coordinate_chart(self):
        spec=track_spec();proof=M.TrackGuarantee(spec['geometry'],400,spec['target'])
        self.assertEqual(S.cancel(2*proof.straight+2*S.pi*proof.radius),400)
        self.assertTrue(proof.radius.is_positive);self.assertTrue(proof.straight.is_positive)
        self.assertEqual(S.cancel(2*S.pi*proof.increment),proof.g)
        for t,g in [(Fraction(1,100),Fraction(1000)),(Fraction(3,2),Fraction(1,1000)),(Fraction(100),Fraction(7))]:
            self.assertGreater(proof.radius.subs({proof.t:S.Rational(t)}),0)
            self.assertGreater(proof.straight.subs({proof.t:S.Rational(t)}),0)
            self.assertEqual(S.cancel(proof.lengths['full_lap','outer']-proof.g),400)

    def test_race_distance_and_counterexample_shape_are_parameters(self):
        for distance in ('1/7',1,200,400,1600):
            spec=track_spec(distance)
            spec['options'][0]['explanation']['counterexample']['shape_ratio']='1/100'
            self.assertEqual(M.track_explanation(spec),'compensate extra arc')

    def test_order_names_and_equivalent_program_do_not_choose_a_fixed_label(self):
        spec=track_spec();spec['options'].reverse()
        for i,o in enumerate(spec['options']):o.update(key=str(i),text='anonymous'+str(i))
        self.assertEqual(M.track_explanation(spec),'anonymous0')
        policy=op('divide',op('multiply',{'op':'scalar','value':2},gap()),{'op':'scalar','value':2})
        spec['options'][0]['explanation']['advance_policy']=policy
        self.assertEqual(M.track_explanation(spec),'anonymous0')

    def test_an_external_claim_can_accompany_a_successful_geometric_policy(self):
        spec=track_spec();spec['options'][0]['explanation']['advance_policy']=gap()
        spec['options'][0]['explanation']['counterexample']=None
        with self.assertRaises(ValueError):M.track_explanation(spec) # two genuine guarantees
        spec['options'].pop(3)
        self.assertEqual(M.track_explanation(spec),'fitness') # names never decide

    def test_half_compensation_has_a_legal_nonzero_residual_counterexample(self):
        spec=track_spec();proof=M.TrackGuarantee(spec['geometry'],400,spec['target'])
        explanation=deepcopy(spec['options'][3]['explanation'])
        explanation['advance_policy']=op('divide',gap(),{'op':'scalar','value':2})
        explanation['counterexample']={'shape_ratio':1,'extra_arc':1,'advance':'1/2'}
        self.assertFalse(proof.inspect(explanation)['guarantees'])
        explanation['counterexample']['advance']='1/3'
        with self.assertRaises(ValueError):proof.inspect(explanation)

    def test_invalid_or_equal_route_witnesses_fail_closed(self):
        for key,value in [('shape_ratio',0),('shape_ratio',-1),('extra_arc',0),
                          ('advance',0),('advance',402),('advance',1),('advance',True)]:
            spec=track_spec();spec['options'][0]['explanation']['counterexample'][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):M.track_explanation(spec)
        spec=track_spec();spec['options'][0]['explanation']['counterexample']=None
        with self.assertRaises(ValueError):M.track_explanation(spec)

    def test_missing_geometry_unknown_late_fields_and_unresolved_premises_reject(self):
        for key in track_spec()['geometry']:
            spec=track_spec();spec['geometry'].pop(key)
            with self.subTest(key=key),self.assertRaises(ValueError):M.track_explanation(spec)
        for mutation in ('policy','premise','extra','witness'):
            spec=track_spec();e=spec['options'][1]['explanation']
            if mutation=='policy':e['advance_policy']={'op':'unknown'}
            elif mutation=='premise':e['premises'].append({'op':'unknown'})
            elif mutation=='extra':e['unconsumed']=1
            else:e['counterexample']={'unknown':1}
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):M.track_explanation(spec)
        spec=track_spec();spec['options'][0]['explanation']['premises']=[op('greater',length('full_lap','inner'),gap())]
        with self.assertRaises(ValueError):M.track_explanation(spec)

    def test_original_expression_domains_and_dimensions_are_not_erased(self):
        for denominator in ({'op':'scalar','value':0},gap(),
                            op('subtract',{'op':'scalar','value':1},{'op':'scalar','value':1})):
            spec=track_spec();spec['options'][3]['explanation']['advance_policy']=op('divide',gap(),denominator)
            with self.subTest(denominator=denominator),self.assertRaises(ValueError):M.track_explanation(spec)
        spec=track_spec();spec['options'][3]['explanation']['advance_policy']=op('add',gap(),{'op':'scalar','value':1})
        with self.assertRaises(ValueError):M.track_explanation(spec)

    def test_exact_domains_numeric_spelling_and_uniqueness(self):
        for distance in (0,-1,True,400.0,'4⁰⁰','④00','400。0','4 00','1/0'):
            with self.subTest(distance=distance),self.assertRaises(ValueError):M.track_explanation(track_spec(distance))
        spec=track_spec();spec['geometry']['straight_pieces']=True
        with self.assertRaises(ValueError):M.track_explanation(spec)
        spec=track_spec();spec['options'].pop(3)
        with self.assertRaises(ValueError):M.track_explanation(spec)
        spec=track_spec();spec['options'][0]['key']='D'
        with self.assertRaises(ValueError):M.track_explanation(spec)


class IntegralSubstitutionTests(unittest.TestCase):
    def test_all_three_algebraic_actions_are_executed_but_only_one_is_integral(self):
        spec=substitution_spec();proof=M.SubstitutionActions(spec['variables'],spec['equations'],spec['target'])
        results=[proof.execute(o['program']) for o in spec['options']]
        self.assertTrue(all(r['equivalent'] for r in results))
        self.assertEqual([r['integral'] for r in results],[True,False,False])
        self.assertEqual(proof.solution,(2,1))
        self.assertEqual(M.integral_substitution(spec),'isolate y first')

    def test_variable_renaming_equation_scaling_and_option_order_are_covariant(self):
        spec=substitution_spec('a','b');spec['options'].reverse()
        for row,factor in zip(spec['equations'],(Fraction(-7,3),Fraction(2,9))):
            row['rhs']=str(M._q(row['rhs'])*factor)
            row['coefficients']={key:str(M._q(value)*factor) for key,value in row['coefficients'].items()}
        self.assertEqual(M.integral_substitution(spec),'isolate y first')

    def test_changing_the_mathematical_system_changes_the_selected_candidate(self):
        spec=substitution_spec()
        spec['equations'][1]={'coefficients':{'x':1,'y':3},'rhs':6}
        spec['options'][0]['program']=action(0,'x',1,'7/3','y','-1/3')
        spec['options'][1]['program']=action(1,'x',0,6,'y',-3)
        spec['options'][2]['program']=action(1,'y',0,2,'x','-1/3')
        self.assertEqual(M.integral_substitution(spec),'isolate x second')

    def test_scaling_equation_is_a_valid_equation_object_not_an_isolation(self):
        spec=substitution_spec();proof=M.SubstitutionActions(spec['variables'],spec['equations'],spec['target'])
        program={'op':'scale_equation','from':0,'factor':'2/3'}
        result=proof.execute(program)
        self.assertEqual(result['kind'],'equation')
        self.assertEqual(result['coefficients'],(2,Fraction(2,3)))
        spec['options'].append({'key':'D','text':'scale only','program':program})
        self.assertEqual(M.integral_substitution(spec),'isolate y first')

    def test_incorrect_rearrangement_and_missing_or_multiple_targets_do_not_pass(self):
        spec=substitution_spec();spec['options'][0]['program']['rhs']['constant']=8
        with self.assertRaises(ValueError):M.integral_substitution(spec)
        spec=substitution_spec();spec['options'].pop(0)
        with self.assertRaises(ValueError):M.integral_substitution(spec)
        spec=substitution_spec();spec['options'][1]['program']=deepcopy(spec['options'][0]['program'])
        with self.assertRaises(ValueError):M.integral_substitution(spec)

    def test_unknown_action_late_coefficients_and_missing_task_domains_fail_closed(self):
        for field in ('domain','target'):
            spec=substitution_spec();spec.pop(field)
            with self.subTest(field=field),self.assertRaises(ValueError):M.integral_substitution(spec)
        for mutation in ('op','extra','variable','into','coefficient'):
            spec=substitution_spec();p=spec['options'][2]['program']
            if mutation=='op':p['op']='unknown'
            elif mutation=='extra':p['unconsumed']=1
            elif mutation=='variable':p['variable']='z'
            elif mutation=='into':p['into']=1
            else:p['rhs']['coefficients']['z']=0
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):M.integral_substitution(spec)

    def test_undefined_singular_and_unsupported_numeric_sources_are_rejected(self):
        spec=substitution_spec();spec['equations'][1]=deepcopy(spec['equations'][0])
        with self.assertRaises(ValueError):M.integral_substitution(spec)
        for value in (True,0.5,'3²','③','3。0','1/0','3 0','sqrt(9)'):
            spec=substitution_spec();spec['equations'][0]['coefficients']['x']=value
            with self.subTest(value=value),self.assertRaises(ValueError):M.integral_substitution(spec)
        spec=substitution_spec();spec['options'][0]['program']['from']=True
        with self.assertRaises(ValueError):M.integral_substitution(spec)
        spec=substitution_spec();spec['options'].append({'key':'D','text':'zero scaling',
            'program':{'op':'scale_equation','from':0,'factor':0}})
        with self.assertRaises(ValueError):M.integral_substitution(spec)


if __name__=='__main__':unittest.main()
