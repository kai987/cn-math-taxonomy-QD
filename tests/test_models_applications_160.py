"""Independent proof/false-positive regressions; no question ids or answer table."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
import sympy as S

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import models_applications_160 as M


def R(a,op,b='0'):return {'left':a,'op':op,'right':b}
def O(text,**values):return {'key':text,'text':text,**values}
def C(variables,conclusions,witness,premises=None,counterexample=None,**extras):
    result={'variables':variables,'conclusions':conclusions,'witness':witness,'premises':premises or [],**extras}
    if counterexample is not None:result['counterexample']=counterexample
    return result


class Applications160ProofTests(unittest.TestCase):
    def test_nonzero_saturation_never_divides_by_a_possible_zero(self):
        case=C({'k':'real','x':'real'},[R('x','=')],{'k':2,'x':0},[R('k*x','='),R('k','!=')])
        self.assertTrue(M.prove_case(case))
        case['premises']=case['premises'][:1];case['counterexample']={'k':0,'x':1}
        self.assertFalse(M.prove_case(case))
        case['counterexample']={'k':2,'x':1}
        with self.assertRaises(ValueError):M.prove_case(case)

    def test_inconsistent_or_nonreal_premises_do_not_make_vacuous_proofs(self):
        case=C({'x':'real'},[R('0','=')],{'x':0},[R('x*x+1','=')])
        with self.assertRaises(ValueError):M.prove_case(case)
        case=C({'x':'positive'},[R('x','>')],{'x':-1})
        with self.assertRaises(ValueError):M.prove_case(case)

    def test_unresolved_relation_requires_a_real_counterexample(self):
        case=C({'x':'real'},[R('x','>')],{'x':1})
        with self.assertRaises(ValueError):M.prove_case(case)
        case['counterexample']={'x':0};self.assertFalse(M.prove_case(case))
        case['counterexample']={'x':1}
        with self.assertRaises(ValueError):M.prove_case(case)

    def test_counterexample_checks_every_premise_and_symbol_assumption(self):
        case=C({'x':'positive'},[R('x','=','1')],{'x':2},[R('x','<','3')],{'x':0})
        with self.assertRaises(ValueError):M.prove_case(case)
        case['counterexample']={'x':4}
        with self.assertRaises(ValueError):M.prove_case(case)
        case['counterexample']={'x':2};self.assertFalse(M.prove_case(case))

    def test_existential_witness_and_not_forall_have_distinct_obligations(self):
        case=C({'x':'real'},[R('x*x','=','4')],{'x':2},mode='exists')
        self.assertTrue(M.prove_case(case))
        case['witness']={'x':1}
        with self.assertRaises(ValueError):M.prove_case(case)
        case=C({'x':'real'},[R('x*x','=','4')],{'x':2},counterexample={'x':0},mode='not_forall')
        self.assertTrue(M.prove_case(case))
        case['mode']='usually'
        with self.assertRaises(ValueError):M.prove_case(case)

    def test_sum_of_squares_certificate_proves_a_global_attained_chord_bound(self):
        case=C({'a':'real','b':'real','c':'real','d':'real'},[R('4-(a-c)**2-(b-d)**2','>=')],
               {'a':1,'b':0,'c':-1,'d':0},[R('a*a+b*b','=','1'),R('c*c+d*d','=','1')],
               certificates={'0':{'squares':['a+c','b+d']}})
        self.assertTrue(M.prove_case(case))
        attained=C({'r':'positive'},[R('(r-(-r))**2','=','4*r*r')],{'r':2},mode='exists')
        self.assertTrue(M.prove_case(attained))
        case['conclusions'][0]['left']='3-(a-c)**2-(b-d)**2'
        with self.assertRaises(ValueError):M.prove_case(case)

    def test_square_certificate_cannot_justify_strict_positivity_at_zero(self):
        case=C({'x':'real','y':'real'},[R('x*x+y*y','>')],{'x':1,'y':0},certificates={'0':{'squares':['x','y']}})
        with self.assertRaises(ValueError):M.prove_case(case)
        case['conclusions'][0]['op']='>=';self.assertTrue(M.prove_case(case))

    def test_all_candidate_obligations_are_evaluated_and_unknown_is_not_false(self):
        true=C({'x':'real'},[R('x-x','=')],{'x':0})
        false=C({'x':'real'},[R('x','=','1')],{'x':1},counterexample={'x':0})
        unknown=C({'x':'real'},[R('x','>')],{'x':1})
        self.assertEqual(M.relation_proofs({'options':[O('yes',cases=[true]),O('no',cases=[false])]}),'yes')
        with self.assertRaises(ValueError):M.relation_proofs({'options':[O('yes',cases=[true]),O('unknown',cases=[false,unknown])]})
        with self.assertRaises(ValueError):M.relation_proofs({'options':[O('empty',cases=[])]})
        with self.assertRaises(ValueError):M.relation_proofs({'options':[O('yes',cases=[true]),O('duplicate',cases=[true])]})

    def test_undeclared_symbols_boolean_and_free_witnesses_are_rejected(self):
        for value in [True,'x']:
            with self.subTest(value=value),self.assertRaises(ValueError):M.prove_case(C({'x':'real'},[R('x-x','=')],{'x':value}))
        with self.assertRaises(ValueError):M.prove_case(C({'x':'real'},[R('y-y','=')],{'x':0}))
        with self.assertRaises(ValueError):M.prove_case(C({'x':'real'},[R('x-x','=')],{}))

    def test_pure_translation_has_no_finite_homothety_center(self):
        first=[M.S.Matrix(point) for point in [[0,0],[3,0],[0,4]]]
        second=[point+M.S.Matrix([5,-2]) for point in first]
        self.assertFalse(M.homothety_exists(first,second))
        self.assertTrue(M.homothety_exists(first,list(reversed(first))))

    def test_set_homothety_enumerates_every_vertex_bijection(self):
        first=[S.Matrix(p) for p in [(0,0),(3,0),(0,4)]]
        rotated=[S.Matrix(p) for p in [(0,0),(0,3),(-4,0)]]
        self.assertFalse(M.homothety_exists(first,rotated))
        translated_scaled=[2*p+S.Matrix([5,-2]) for p in first]
        translated_scaled=translated_scaled[1:]+translated_scaled[:1]
        self.assertTrue(M.homothety_exists(first,translated_scaled))
        reversed_scale=[-p+S.Matrix([1,1]) for p in first]
        self.assertTrue(M.homothety_exists(first,reversed_scale))

    def test_similarity_counterexample_must_be_a_genuine_set_counterexample(self):
        case={'construction':'similarity_pair','points':[[0,0],[3,0],[0,4]],'matrix':[[0,-1],[1,0]]}
        self.assertFalse(M.prove_case(case))
        case['matrix']=[[2,0],[0,2]]
        with self.assertRaises(ValueError):M.prove_case(case)  # a positive example cannot prove universality
        case['matrix']=[[1,0],[0,2]]
        with self.assertRaises(ValueError):M.prove_case(case)  # not similar
        case['matrix']=[[0,0],[0,0]]
        with self.assertRaises(ValueError):M.prove_case(case)

    def circle_case(self,mode='equal',same_radius=True):
        return {'variables':{'r':'positive','s':'positive','t':'positive'},
                'circles':[{'radius':'r','angle':'t'},{'radius':'r' if same_radius else 's','angle':'t'}],
                'quantity':'arc','mode':mode,'witness':{'r':1,'s':2,'t':1}}

    def test_circle_equalities_use_actual_arc_and_chord_formulas(self):
        arc=self.circle_case();chord=deepcopy(arc);chord['quantity']='chord_squared'
        neq=self.circle_case('not_always_equal')
        spec={'options':[O('equal quantities',cases=[arc,chord]),O('not always',cases=[neq])]}
        self.assertEqual(M.circle_pairs(spec),'equal quantities')
        with self.assertRaises(ValueError):M.circle_pairs({'options':[O('empty',cases=[])]})
        chord['quantity']='unknown'
        with self.assertRaises(ValueError):M.circle_pairs(spec)

    def test_different_radii_require_a_valid_exact_unequal_witness(self):
        equal=self.circle_case('equal',same_radius=False);unequal=self.circle_case('not_always_equal',same_radius=False)
        self.assertEqual(M.circle_pairs({'options':[O('universal equality',cases=[equal]),O('counterexample exists',cases=[unequal])]}),'counterexample exists')
        unequal['witness']['s']=1
        with self.assertRaises(ValueError):M.circle_pairs({'options':[O('bad witness',cases=[unequal])]})

    def test_circle_witness_checks_variable_assumptions_even_when_radius_stays_positive(self):
        case={'variables':{'a':'positive'},'circles':[{'radius':'a*a+1','angle':'1'},{'radius':'2','angle':'1'}],
              'quantity':'arc','mode':'not_always_equal','witness':{'a':-2}}
        with self.assertRaises(ValueError):M.circle_pairs({'options':[O('illegal negative parameter',cases=[case])]})
        case['witness']['a']='b'
        with self.assertRaises(ValueError):M.circle_pairs({'options':[O('unbound parameter',cases=[case])]})
        case['witness']['a']=2
        self.assertEqual(M.circle_pairs({'options':[O('legal unequal case',cases=[case])]}),'legal unequal case')

    def test_circle_witness_must_describe_real_nonempty_arcs(self):
        case=self.circle_case()
        for value in [0,7,'2*pi']:
            case['witness']['t']=value
            with self.subTest(value=value),self.assertRaises(ValueError):M.circle_pairs({'options':[O('bad',cases=[case])]})
        case['witness']['t']='pi/2'
        self.assertEqual(M.circle_pairs({'options':[O('quarter circle',cases=[case])]}),'quarter circle')

    def cone_spec(self):
        return {'variables':{'r':'positive','h':'positive'},'radius':'r','height':'h','witness':{'r':3,'h':4},'options':[
            O('generator and rim',radius='sqrt(r*r+h*h)',arc='2*pi*r'),O('radius and height',radius='r',arc='h')]}

    def test_cone_result_is_derived_from_both_surface_boundary_integrals(self):
        self.assertEqual(M.cone_development(self.cone_spec()),'generator and rim')
        spec=self.cone_spec();spec['witness']['h']=0
        with self.assertRaises(ValueError):M.cone_development(spec)
        spec=self.cone_spec();spec['variables']['h']='real'
        with self.assertRaises(ValueError):M.cone_development(spec)

    def test_cone_nonidentity_cannot_be_decided_from_an_accidental_equal_witness(self):
        spec=self.cone_spec();spec['options'][1]['radius']='sqrt(r*r+h*h)+(r-3)*(h-4)';spec['options'][1]['arc']='2*pi*r'
        with self.assertRaises(ValueError):M.cone_development(spec)
        spec['witness']={'r':2,'h':3}
        self.assertEqual(M.cone_development(spec),'generator and rim')

    def circumcircle_spec(self):
        return {'variables':{'a':'positive','b':'positive'},'vertices':[['a','0'],['0','b'],['0','0']],
                'chord':[0,1],'witness':{'a':1,'b':2},'options':[
                    O('diameter',op='=',radius_squared_factor=4),
                    O('shorter than radius',op='<',radius_squared_factor=1),
                    O('undetermined',op='=',radius_squared_factor=4,quantifier='not_forall')]}

    def test_circumcircle_is_solved_from_equal_distances_and_ordered_chord(self):
        self.assertEqual(M.circumcircle_chord(self.circumcircle_spec()),'diameter')
        spec=self.circumcircle_spec();spec['chord']=[0,2]
        with self.assertRaises(ValueError):M.circumcircle_chord(spec)
        spec=self.circumcircle_spec();spec['vertices'][2]=['2*a','-b']
        with self.assertRaises(ValueError):M.circumcircle_chord(spec)  # all vertices collinear

    def test_circumcircle_rejects_undefined_quantifier_and_nearby_diameter(self):
        spec=self.circumcircle_spec();spec['options'][2]['quantifier']='maybe'
        with self.assertRaises(ValueError):M.circumcircle_chord(spec)
        spec=self.circumcircle_spec();spec['options']=spec['options'][:1];spec['options'][0]['radius_squared_factor']='4000000000001/1000000000000'
        with self.assertRaises(ValueError):M.circumcircle_chord(spec)

    def tangent_spec(self):
        return {'center':['0','0'],'radius':'1','options':[
            O('perpendicular',point=['1','0'],direction=['d','e'],case=C({'d':'real','e':'nonzero'},[],{'d':0,'e':1},[R('d','=')])),
            O('radial',point=['1','0'],direction=['d','e'],case=C({'d':'nonzero','e':'real'},[],{'d':1,'e':0},[R('e','=')],{'d':1,'e':0}))]}

    def test_tangent_condition_derives_the_quadratic_and_discriminant(self):
        self.assertEqual(M.tangent_conditions(self.tangent_spec()),'perpendicular')
        spec=self.tangent_spec();spec['options'][0]['case']['witness']['d']=1
        with self.assertRaises(ValueError):M.tangent_conditions(spec)
        spec=self.tangent_spec();spec['options'][0]['point']=['0','0'];spec['options'][0]['case']['counterexample']={'d':0,'e':1}
        with self.assertRaises(ValueError):M.tangent_conditions(spec)  # perpendicular through centre is a secant

    def test_zero_direction_is_an_invalid_line_not_a_false_tangency_claim(self):
        spec=self.tangent_spec();spec['options'][1]['direction']=['0','0']
        with self.assertRaises(ValueError):M.tangent_conditions(spec)
        spec=self.tangent_spec();spec['radius']='0'
        with self.assertRaises(ValueError):M.tangent_conditions(spec)

    def test_unknown_perpendicular_distance_is_not_assumed_a_radius(self):
        case=C({'r':'positive','d':'nonnegative'},[],{'r':1,'d':2},counterexample={'r':1,'d':2})
        good=C({'r':'positive','d':'nonnegative'},[],{'r':1,'d':1},[R('d','=','r')])
        spec={'center':['0','0'],'radius':'r','options':[O('foot only',point=['0','d'],direction=['1','0'],case=case),O('foot equals radius',point=['0','d'],direction=['1','0'],case=good)]}
        self.assertEqual(M.tangent_conditions(spec),'foot equals radius')
        case['counterexample']={'r':1,'d':1}
        with self.assertRaises(ValueError):M.tangent_conditions(spec)

    def obtuse_spec(self):
        return {'normalization':{'base':[[0,0],[1,0]],'third':['u','v'],'obtuse_at':'third'},
                'witness':{'u':'1/2','v':'1/4','g':'3/16'},'options':[
                    O('inside',region='inside'),O('midpoint',region='longest_side_midpoint'),O('outside',region='outside')]}

    def test_obtuse_circumcenter_uses_general_gap_not_one_triangle_sample(self):
        self.assertEqual(M.obtuse_circumcenter(self.obtuse_spec()),'outside')
        spec=self.obtuse_spec();spec['witness']={'u':'1/3','v':'1/3','g':'1/9'}
        self.assertEqual(M.obtuse_circumcenter(spec),'outside')
        spec['witness']['g']=0
        with self.assertRaises(ValueError):M.obtuse_circumcenter(spec)
        spec=self.obtuse_spec();spec['witness']['v']=2
        with self.assertRaises(ValueError):M.obtuse_circumcenter(spec)

    def test_obtuse_source_normalization_and_region_must_be_explicit(self):
        spec=self.obtuse_spec();spec['normalization']['obtuse_at']='unknown'
        with self.assertRaises(ValueError):M.obtuse_circumcenter(spec)
        spec=self.obtuse_spec();spec['options'][0]['region']='nearby'
        with self.assertRaises(ValueError):M.obtuse_circumcenter(spec)


if __name__=='__main__':unittest.main()
