from fractions import Fraction
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import models_foundations_160 as M


def O(text,**fields):return {'key':text,'text':text,**fields}
def slot(vertex,region='interior',side='right'):return {'vertex':vertex,'region':region,'side':side}
def primitive(kind,a=0,b=1):return {'kind':kind,'a':a,'b':b}


class Foundations160Tests(unittest.TestCase):
    def test_affine_boolean_equivalence_includes_zero_and_handles_negation(self):
        self.assertTrue(M._formula_equivalent('a!=0','a<0 or a>0'))
        self.assertFalse(M._formula_equivalent('a!=0','a!=0 and b!=0'))
        self.assertFalse(M._formula_equivalent('a<3','a<=3'))
        self.assertTrue(M._formula_equivalent('not (a<3)','a>=3'))
        with self.assertRaises(ValueError):M._formula_equivalent('a*b!=0','a!=0')

    def test_numeric_types_cannot_be_boolean_outcome_flags(self):
        for spec in [
            {'options':[O('bad',claim='each_sign_possible',variable='a',signs=[True])]},
            {'options':[O('bad',claim='numeric_sign',value=1,sign=True)]},
            {'options':[O('bad',claim='sign_partition',domain='real',signs=[False,1,-1])]},
        ]:
            with self.assertRaises(ValueError):M.real_claims(spec)
        with self.assertRaises(ValueError):
            M.missing_axis_parameter({'known':{'origin':0,'orientation':True},
                                      'options':[O('unit',parameter='unit_length')]})

    def test_sign_partition_proves_missing_zero_is_a_real_counterexample(self):
        options=[O('missing zero',claim='sign_partition',domain='rational',signs=[-1,1]),
                 O('all signs',claim='sign_partition',domain='integer',signs=[1,0,-1])]
        self.assertEqual(M.real_claims({'options':options}),'all signs')
        with self.assertRaises(ValueError):M.real_claims({'options':[O('unknown',claim='table_truth')]})

    def test_reciprocal_root_set_is_complete_and_zero_is_undefined(self):
        options=[O('zero',claim='reciprocal_value',value=0,reciprocal=0),
                 O('complete',claim='fixed_points',values=[-1,1]),
                 O('incomplete',claim='fixed_points',values=[1]),
                 O('always smaller',claim='forall_comparison',operator='<')]
        self.assertEqual(M.reciprocal_claims({'options':options}),'complete')
        options.append(O('duplicate complete',claim='fixed_points',values=[1,-1]))
        with self.assertRaises(ValueError):M.reciprocal_claims({'options':options})

    def test_square_quantities_are_symbolic_not_one_numeric_example(self):
        spec={'vertices':[['0','0'],['a','0'],['a','a'],['0','a']],
              'assumptions':{'a':'positive'},'source':'4*a',
              'options':[O('area',quantity='area'),O('perimeter',quantity='perimeter'),
                         O('diagonal',quantity='segment',vertices=[0,2]),
                         O('half',quantity='segment',vertices=[0,1],divisor=2)]}
        self.assertEqual(M.polygon_quantity(spec),'perimeter')
        # a=4 would make area and perimeter coincide; no such single sample is used.
        for source in ['a/a','sqrt(a-2)','1/b']:
            with self.subTest(source=source),self.assertRaises(ValueError):
                M.polygon_quantity({**spec,'source':source})
        with self.assertRaises(ValueError):M.polygon_quantity({**spec,'assumptions':{'a':'real'}})

    def test_parameter_degree_condition_is_necessary_and_sufficient(self):
        spec={'expression':'a*x+b','unknown':'x','parameters':['a','b'],'degree':1,
              'options':[O('a zero',condition='a==0'),O('b nonzero',condition='b!=0'),
                         O('a nonzero',condition='a!=0'),O('both nonzero',condition='a!=0 and b!=0')]}
        self.assertEqual(M.degree_parameter_condition(spec),'a nonzero')
        for expression in ['(a/a)*x+b','sqrt(a)*x+b','c*x+b']:
            with self.subTest(expression=expression),self.assertRaises(ValueError):
                M.degree_parameter_condition({**spec,'expression':expression})

    def test_affine_primitive_reversal_distinguishes_line_ray_and_segment(self):
        options=[O('segments different',claim='different_set',first=primitive('segment'),second=primitive('segment',1,0)),
                 O('rays same',claim='same_set',first=primitive('ray'),second=primitive('ray',1,0)),
                 O('line finite',claim='finite_length',primitive=primitive('line')),
                 O('lines same',claim='same_set',first=primitive('line'),second=primitive('line',1,0))]
        self.assertEqual(M.primitive_claims({'options':options}),'lines same')
        for claim in ['endpoint_count','unbounded_directions']:
            with self.subTest(claim=claim),self.assertRaises(ValueError):
                M.primitive_claims({'primitive':primitive('ray'),'options':[O('boolean count',claim=claim,count=True)]})
        # An affine parameter change preserves these set equalities.
        for option in options:
            for field in ['first','second','primitive']:
                if field in option:
                    option[field]={**option[field],'a':2*option[field]['a']+7,'b':2*option[field]['b']+7}
        self.assertEqual(M.primitive_claims({'options':options}),'lines same')

    def test_undetermined_order_is_computed_from_all_feasible_signs(self):
        options=[O('less',operator='<'),O('greater',operator='>'),O('equal',operator='='),O('unknown',operator='undetermined')]
        self.assertEqual(M.affine_order({'premises':[M.R('b','>',0),M.R('b','<','d')],
                                        'left':'b','right':'d','options':options}),'less')
        self.assertEqual(M.affine_order({'premises':[],'left':'b','right':'d','options':options}),'unknown')

    def test_correct_conclusion_with_wrong_complement_reason_is_rejected(self):
        ambient=[M.R(v,'>',0) for v in 'abc']+[M.R(v,'<',180) for v in 'abc']
        options=[O('wrong reason',claim='explained_conclusion',reasons=[M.R('a+b','=',180),M.R('a+c','=',180)],
                   conclusions=[M.R('b','=','c')]),
                 O('right reason',claim='explained_conclusion',reasons=[M.R('a+b','=',90),M.R('a+c','=',90)],
                   conclusions=[M.R('b','=','c')]),O('unknown',claim='undetermined')]
        self.assertEqual(M.affine_reasoning({'ambient':ambient,'given':[M.R('a+b','=',90),M.R('a+c','=',90)],
                                             'compare':['b','c'],'options':options}),'right reason')

    def test_direction_parity_requires_plane_and_distinct_parallel_lines(self):
        spec={'plane_dimension':2,'relations':[['a','perpendicular','b'],['b','perpendicular','c']],
              'query':['a','c'],'distinct_pairs':[['a','c']],
              'options':[O('parallel',relation='parallel'),O('perpendicular',relation='perpendicular')]}
        self.assertEqual(M.line_relation_family(spec),'parallel')
        with self.assertRaises(ValueError):M.line_relation_family({**spec,'plane_dimension':3})
        with self.assertRaises(ValueError):M.line_relation_family({**spec,'distinct_pairs':[]})

    def test_angle_slots_need_both_crossings_and_are_mirror_invariant(self):
        options=[O('alternate',angle_class='alternate_interior'),O('same side',angle_class='same_side_interior'),
                 O('vertical',angle_class='vertical')]
        angles=[slot('upper',side='left'),slot('lower',side='right')]
        self.assertEqual(M.angle_slot_classification({'angles':angles,'options':options}),'alternate')
        mirrored=[{**a,'side':'right' if a['side']=='left' else 'left'} for a in angles]
        self.assertEqual(M.angle_slot_classification({'angles':mirrored,'options':options}),'alternate')
        with self.assertRaises(ValueError):M.parallel_angle_claims({'mode':'criterion','options':[
            O('bad vertices',angles=[slot('upper'),slot('upper',side='left')],relation='equal')]})

    def test_parallel_criterion_and_property_have_opposite_logical_directions(self):
        options=[O('same-side equal',angles=[slot('upper'),slot('lower')],relation='equal'),
                 O('corresponding supplementary',angles=[slot('upper'),slot('lower','exterior')],relation='supplementary'),
                 O('alternate equal',angles=[slot('upper'),slot('lower',side='left')],relation='equal')]
        self.assertEqual(M.parallel_angle_claims({'mode':'criterion','options':options}),'alternate equal')
        self.assertEqual(M.parallel_angle_claims({'mode':'property','options':options}),'alternate equal')
        measured={'angles':[slot('upper'),slot('lower','exterior')],'measures':[65,65],
                  'options':[O('parallel',relation='parallel'),O('intersect',relation='intersect')]}
        self.assertEqual(M.numeric_angle_lines(measured),'parallel')
        with self.assertRaises(ValueError):M.numeric_angle_lines({**measured,'angles':measured['angles']+[slot('upper')]})

    def test_convex_quad_family_covers_arbitrary_shear_not_only_right_trapezoids(self):
        options=[O('base pair',claim='parallel_edges',edges=[['A','B'],['C','D']]),
                 O('other pair',claim='parallel_edges',edges=[['A','D'],['B','C']]),
                 O('diagonals',claim='parallel_edges',edges=[['A','C'],['B','D']]),
                 O('parallelogram',claim='parallelogram')]
        self.assertEqual(M.supplementary_quad({'vertices':list('ABCD'),'supplementary':['A','D'],'options':options}),'base pair')
        self.assertEqual(M.supplementary_quad({'vertices':list('BCDA'),'supplementary':['A','D'],'options':options}),'base pair')
        with self.assertRaises(ValueError):M.supplementary_quad({'vertices':list('ABCD'),'supplementary':['A','C'],'options':options})

    def test_cubic_bijection_proof_covers_zero_and_both_signs(self):
        options=[O('all real unique',domain='real',count=1),O('negative none',domain='negative',count=0),
                 O('positive two',domain='positive',count=2),O('zero none',domain='zero',count=0)]
        self.assertEqual(M.cubic_root_counts({'degree':3,'options':options}),'all real unique')
        with self.assertRaises(ValueError):M.cubic_root_counts({'degree':2,'options':options})

    def test_pi_uses_nested_rational_bounds_and_proves_rounding(self):
        lower4,upper4=M.pi_interval(4);lower6,upper6=M.pi_interval(6)
        self.assertIsInstance(lower6,Fraction)
        self.assertLess(lower4,lower6);self.assertLess(upper6,upper4)
        self.assertLess(Fraction(314159,100000),lower6)
        self.assertLess(upper6,Fraction(314160,100000))
        options=[O('wrong interval',interval=[2,3]),O('correct rounded',interval=[3,4],approximation='3.14',decimal_places=2)]
        self.assertEqual(M.pi_location({'options':options}),'correct rounded')
        with self.assertRaises(ValueError):M.pi_location({'terms':1,'options':options})
        with self.assertRaises(ValueError):M.pi_location({'options':[
            O('off-grid',interval=[3,4],approximation='3.141',decimal_places=2)]})
        with self.assertRaises(ValueError):M.atan_interval(Fraction(1,5),True)

    def test_parallel_axiom_checks_actual_counterexamples_not_claim_labels(self):
        options=[O('unique',claim='parallel_count',point_domain='off_line',count=1),
                 O('segments',claim='disjoint_segments_imply_parallel_lines',
                   counterexample=[[[1,0],[2,0]],[[0,1],[0,2]]]),
                 O('all points',claim='parallel_count',point_domain='all',count=1,
                   counterexample={'point':[0,0],'line':[[0,0],[1,0]]}),
                 O('perpendicular',claim='common_parallel_implies_perpendicular',
                   counterexample=[[[0,0],[1,0]],[[0,1],[1,1]],[[0,2],[1,2]]])]
        self.assertEqual(M.parallel_axiom_claims({'plane_dimension':2,'options':options}),'unique')
        bad={**options[1],'counterexample':[[[-1,0],[1,0]],[[0,-1],[0,1]]]}
        with self.assertRaises(ValueError):M.parallel_axiom_claims({'plane_dimension':2,'options':[options[0],bad]})

    def test_translation_requires_nonzero_domain_and_checks_false_claim_witness(self):
        options=[O('unique intersection',relation='always_one_intersection',
                   counterexample={'points':[[0,0],[0,1]],'vector':[1,0]}),
                 O('perpendicular',relation='always_perpendicular'),
                 O('same directed displacement',relation='parallel_or_collinear_and_equal'),
                 O('unequal',relation='parallel_and_unequal')]
        self.assertEqual(M.translation_relations({'translation_domain':'nonzero','options':options}),'same directed displacement')
        with self.assertRaises(ValueError):M.translation_relations({'translation_domain':'including_zero','options':options})
        bad={**options[0],'counterexample':{'points':[[0,0],[1,0]],'vector':[1,0]}}
        with self.assertRaises(ValueError):M.translation_relations({'translation_domain':'nonzero','options':[bad,options[2]]})


if __name__=='__main__':unittest.main()
