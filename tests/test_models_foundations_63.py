import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import models_foundations_63 as M


def O(text,**fields):return {'key':text,'text':text,**fields}
def pred(op,*args):return {'op':op,'args':list(args)}
def slot(v,region='interior',side='right'):return {'vertex':v,'region':region,'side':side}
def crossing():return {'kind':'transversal','lines':['a','b'],'angles':{'i':slot('upper'),'j':slot('lower','exterior')}}
def vertical():
    return {'kind':'rays','rays':{'u':['1','0'],'v':['cos(t*pi/180)','sin(t*pi/180)'],
            'w':['-1','0'],'x':['-cos(t*pi/180)','-sin(t*pi/180)']},
            'angles':{'i':['u','v'],'j':['w','x']},'angle_forms':{'i':'t','j':'t'}}
def theorem_step():return {'given':[pred('parallel','a','b')],'goal':pred('angle_equal','i','j')}
def source_schema():
    return {'angles':['a','b','c'],'given':[pred('angle_supplementary','a','c'),pred('angle_supplementary','b','c')],
            'goal':[pred('angle_equal','a','b')]}
def polar():
    return O('polar',symbols={'a':'real','d':'nonnegative'},known_parameters=['a','d'],
             linear_part=[['1','0'],['0','1']],offset=['d*cos(a)','d*sin(a)'],polar_parameters=['a','d'])
def rotation():
    return O('rotation',symbols={'a':'real','c':'real','d':'real'},known_parameters=['a','c','d'],
             linear_part=[['cos(a)','-sin(a)'],['sin(a)','cos(a)']],
             offset=['(1-cos(a))*c+sin(a)*d','(1-cos(a))*d-sin(a)*c'],
             counterexample={'a':'pi/2','c':'0','d':'0'})
def shape_only():
    return O('shape only',symbols={'a':'positive','b':'real','c':'positive','u':'real','v':'real'},
             known_parameters=['a','b','c'],linear_part=[['1','0'],['0','1']],offset=['u','v'],
             shape=[['0','0'],['a','0'],['b','c']],
             indistinguishable_parameters=[{'a':'1','b':'0','c':'1','u':'0','v':'0'},
                                             {'a':'1','b':'0','c':'1','u':'1','v':'0'}])


class Foundations63Tests(unittest.TestCase):
    def test_all_basis_certificates_have_actual_general_proofs(self):
        kinds=['line_through_two_points','point_line_distance','point_point_path','parallel_through_point','same_angle_supplements']
        for kind in kinds:
            with self.subTest(kind=kind):self.assertEqual(M.prove_basis(kind),M.canonical_problem(M.basis_problem(kind)))
        with self.assertRaises(ValueError):M.prove_basis('unproved_teacher_label')

    def test_basis_goal_matching_is_alpha_invariant_and_not_certificate_label_only(self):
        problem=M.basis_problem('line_through_two_points')
        renamed={'objects':{'X':'Point','Y':'Point'},'assumptions':[['distinct','Y','X']],
                 'goal':{'quantifier':'unique','variable':['result','Line'],'relation':['line_through','result','Y','X']}}
        self.assertEqual(M.canonical_problem(problem),M.canonical_problem(renamed))
        options=[O('minimum',certificate='point_line_distance',problem=M.basis_problem('point_line_distance')),
                 O('unique line',certificate='line_through_two_points',problem=renamed)]
        self.assertEqual(M.basis_application({'problem':problem,'options':options}),'unique line')
        options[0]['problem']=problem
        with self.assertRaises(ValueError):M.basis_application({'problem':problem,'options':options})

    def test_ill_typed_problem_does_not_become_a_wrong_option(self):
        wrong=M.basis_problem('line_through_two_points');wrong['objects']['B']='Line'
        with self.assertRaises(ValueError):M.canonical_problem(wrong)

    def test_typed_line_notation_is_evaluated_on_the_whole_vector_family(self):
        lines={'a':{'point':['0','0'],'direction':['cos(t)','sin(t)']},
               'b':{'point':['p','q'],'direction':['-sin(t)','cos(t)']}}
        options=[O(s,notation=s) for s in ['a∥b','a⊥b','a=b','a∠b']]
        self.assertEqual(M.line_notation({'symbols':{'t':'real','p':'real','q':'real'},'lines':lines,'options':options}),'a⊥b')
        invalid=copy.deepcopy(options);invalid[0]['notation']='a+b'
        with self.assertRaises(ValueError):M.line_notation({'symbols':{'t':'real','p':'real','q':'real'},'lines':lines,'options':invalid})
        lines['b']['direction']=['0','0']
        with self.assertRaises(ValueError):M.line_notation({'symbols':{'t':'real','p':'real','q':'real'},'lines':lines,'options':options})

    def test_parallel_direction_without_proved_separation_is_unresolved(self):
        lines={'a':{'point':['0','0'],'direction':['1','0']},'b':{'point':['0','h'],'direction':['1','0']}}
        with self.assertRaises(ValueError):M.line_notation({'symbols':{'h':'real'},'lines':lines,'options':[O('parallel',notation='a∥b')]})
        self.assertEqual(M.line_notation({'symbols':{'h':'positive'},'lines':lines,'options':[O('parallel',notation='a∥b')]}),'parallel')

    def test_inverse_valid_theorem_is_not_the_current_ordered_step(self):
        context=crossing();source=theorem_step()
        options=[O('criterion',context=context,sequent={'given':[pred('angle_equal','i','j')],'goal':pred('parallel','a','b')}),
                 O('property',context=context,sequent=source)]
        self.assertEqual(M.angle_rule_application({'query':'apply','context':context,'sequent':source,'options':options}),'property')
        # An invalid geometric theorem must raise even if it would not match.
        options[0]['sequent']['goal']=pred('angle_supplementary','i','j')
        with self.assertRaises(ValueError):M.angle_rule_application({'query':'apply','context':context,'sequent':source,'options':options})

    def test_same_angle_names_do_not_alias_different_crossing_objects(self):
        context=crossing();step=theorem_step();other=copy.deepcopy(context)
        # This is a valid vertical-angle equality, but not the source's two
        # distinct-vertex corresponding-angle objects, despite equal i/j names.
        other['angles']['j']=slot('upper','exterior','left')
        wrong=O('other objects',context=other,sequent=step)
        with self.assertRaises(ValueError):
            M.angle_rule_application({'query':'apply','context':context,'sequent':step,'options':[wrong]})
        correct=O('bound objects',context=context,sequent=step)
        self.assertEqual(M.angle_rule_application({'query':'apply','context':context,'sequent':step,'options':[wrong,correct]}),'bound objects')
        mirrored=copy.deepcopy(context)
        for angle in mirrored['angles'].values():angle['side']='left' if angle['side']=='right' else 'right'
        self.assertEqual(M.angle_rule_application({'query':'apply','context':mirrored,'sequent':step,
                         'options':[O('mirrored source',context=mirrored,sequent=step)]}),'mirrored source')

    def test_ray_topology_and_angle_forms_are_independently_checked(self):
        context=vertical();step={'given':[pred('vertical','i','j')],'goal':pred('angle_equal','i','j')}
        M.prove_sequent(context,step)
        bad=copy.deepcopy(context);bad['angle_forms']['j']='180-t'
        with self.assertRaises(ValueError):M.prove_sequent(bad,step)
        bad=copy.deepcopy(context);bad['rays']['x']=['cos(t*pi/180)','sin(t*pi/180)']
        with self.assertRaises(ValueError):M.prove_sequent(bad,step)

    def test_condition_is_applied_boolean_premise_not_true_conclusion_or_noun(self):
        context=vertical();step={'given':[pred('vertical','i','j')],'goal':pred('angle_equal','i','j')}
        options=[O('premise',expression=pred('vertical','i','j')),O('conclusion',expression=pred('angle_equal','i','j')),
                 O('relation name',expression={'op':'predicate_symbol','name':'vertical'}),
                 O('angle set',expression={'op':'set_comprehension','predicate':pred('angle_equal','i','j'),'bound':['i','j']})]
        self.assertEqual(M.condition_of_sequent({'context':context,'sequent':step,'options':options}),'premise')

    def test_true_existential_converse_is_not_same_ordered_implication(self):
        source=source_schema()
        converse={'angles':['a','b','c'],'given':[pred('angle_equal','a','b')],
                  'goal':[pred('angle_supplementary','a','c'),pred('angle_supplementary','b','c')],
                  'exists':['c'],'witnesses':{'c':'180-a'}}
        self.assertTrue(M.prove_linear_schema(converse))
        self.assertTrue(M.prove_linear_schema(source))
        self.assertNotEqual(M._schema_key(source),M._schema_key(converse))
        options=[O('converse',schema=converse),O('same schema',schema=source)]
        self.assertEqual(M.implication_rewrite({'source':source,'options':options}),'same schema')

    def test_linear_supplement_proofs_include_zero_and_180_degree_endpoints(self):
        bad={'angles':['a','b'],'given':[pred('angle_supplementary','a','b')],
             'goal':[pred('angle_equal','a','b')],'counterexample':{'a':0,'b':180}}
        self.assertFalse(M.prove_linear_schema(bad))
        zero_equal={'angles':['a','b','c'],'given':[{'op':'linear_equal','left':'a','right':'0'},pred('angle_equal','a','b')],
                    'goal':[pred('angle_supplementary','a','c'),pred('angle_supplementary','b','c')],
                    'exists':['c'],'witnesses':{'c':'180-a'}}
        self.assertTrue(M.prove_linear_schema(zero_equal))

    def test_counterexamples_and_existential_witnesses_must_be_legal(self):
        base={'angles':['a','b'],'given':[pred('angle_supplementary','a','b')],'goal':[pred('angle_equal','a','b')]}
        for witness in [{'a':-1,'b':181},{'a':30,'b':60},{'a':90,'b':90}]:
            with self.subTest(witness=witness),self.assertRaises(ValueError):M.prove_linear_schema({**base,'counterexample':witness})
        bad={'angles':['a','b','c'],'given':[pred('angle_equal','a','b')],
             'goal':[pred('angle_supplementary','a','c')],'exists':['c'],'witnesses':{'c':'-a'}}
        with self.assertRaises(ValueError):M.prove_linear_schema(bad)
        with self.assertRaises(ValueError):M._schema_key({'angles':['a'],'given':[],'goal':[{'op':'linear_equal','left':'z','right':'a'}]})
        for left,right in [('c','a'),('2*c','2*a')]:
            illegal={'angles':['a','c'],'given':[{'op':'linear_equal','left':left,'right':right}],
                     'goal':[pred('angle_equal','a','c')],'exists':['c'],'witnesses':{'c':'a'}}
            with self.subTest(left=left),self.assertRaises(ValueError):M.prove_linear_schema(illegal)

    def test_affine_family_identification_checks_math_not_transformation_names(self):
        options=[polar(),rotation(),shape_only()]
        self.assertEqual(M.translation_identifiability({'options':options}),'polar')
        cart=O('Cartesian',symbols={'x':'real','y':'real'},known_parameters=['x','y'],
               linear_part=[['1','0'],['0','1']],offset=['x','y'],cartesian_parameters=['x','y'])
        self.assertEqual(M.translation_identifiability({'options':[cart,rotation(),shape_only()]}),'Cartesian')
        with self.assertRaises(ValueError):M.translation_identifiability({'options':[polar(),cart]})

    def test_bad_nontranslation_or_nonidentifiability_witnesses_are_not_false(self):
        invalid=rotation();invalid['counterexample']['a']='0'
        with self.assertRaises(ValueError):M.translation_identifiability({'options':[polar(),invalid]})
        invalid=shape_only();invalid['indistinguishable_parameters'][1]['a']='2'
        with self.assertRaises(ValueError):M.translation_identifiability({'options':[polar(),invalid]})
        invalid=shape_only();invalid['indistinguishable_parameters'][1]['u']='0'
        with self.assertRaises(ValueError):M.translation_identifiability({'options':[polar(),invalid]})

    def test_coverage_domain_and_parameter_types_fail_closed(self):
        invalid=polar();invalid['symbols']['d']='positive'
        with self.assertRaises(ValueError):M.translation_identifiability({'options':[invalid]})
        diagonal=O('diagonal only',symbols={'x':'real'},known_parameters=['x'],
                   linear_part=[['1','0'],['0','1']],offset=['x','x'],cartesian_parameters=['x','x'])
        with self.assertRaises(ValueError):M.translation_identifiability({'options':[diagonal]})
        invalid=rotation();invalid['symbols']['a']='integer'
        with self.assertRaises(ValueError):M.translation_identifiability({'options':[polar(),invalid]})
        constant=O('only identity',symbols={},known_parameters=[],linear_part=[['1','0'],['0','1']],offset=['0','0'])
        with self.assertRaises(ValueError):M.translation_identifiability({'options':[constant]})


if __name__=='__main__':unittest.main()
