"""Adversarial checks for structural equations, typed sets and proof outlines."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
import sympy as S

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import models_applications_63 as M


def O(text,**values):return dict(key=text,text=text,**values)
def shape(name):return {'tag':'shape','name':name}
def point(name):return {'tag':'point','name':name}
def definition(target='T',center='c'):
    return {'tag':'exists','variables':[{'name':center,'sort':'point'}],
            'body':{'tag':'equal','left':{'tag':'half_turn','center':point(center),'shape':shape('S')},'right':shape(target)}}


class Applications63Tests(unittest.TestCase):
    def test_explicit_square_applicability_includes_verified_complete_root_sets(self):
        spec={'variable':'x','options':[
            O('needs completion',equation=['x**2-4*x','5']),
            O('direct',equation=['(2*x-1)**2','9']),
            O('other method',equation=['x*(x-2)','3*x'])]}
        self.assertEqual(M.direct_square_equations(spec),'direct')
        spec['options'][0]['equation']=['(x-2)**2','9']
        with self.assertRaises(ValueError):M.direct_square_equations(spec) # two directly applicable equations

    def test_same_terms_on_both_sides_can_cancel_before_direct_square(self):
        for equation in [['x**2+x','x+9'],['(x-1)**2+3*x','3*x+9'],
                         ['x**4+(x+2)**2','x**4+4'],['2*(x**2+x)','2*x+8']]:
            with self.subTest(equation=equation):self.assertTrue(M._direct_square_equation(equation,'x'))

    def test_direct_form_does_not_invent_a_completed_square_or_drop_a_root(self):
        for equation in [['x**2+2*x','3'],['x*(x-2)','3*x'],['x**2+(x-1)**2','9']]:
            self.assertFalse(M._direct_square_equation(equation,'x'))
        for equation in [['-2*(3*x+1)**2','-8'],['(x-1)**2','0'],['x**2','-1'],['(x+2)*(2*x+4)','8']]:
            self.assertTrue(M._direct_square_equation(equation,'x'))
        self.assertFalse(M._direct_square_equation(['x**2','x**2'],'x'))

    def test_equation_parser_rejects_execution_undeclared_variables_and_domain_loss(self):
        for equation in [["__import__('os')",'0'],['x.__class__','0'],['x**99','0'],['(x+y)**2','9'],['x/x','1'],['x**2/0','1']]:
            with self.subTest(equation=equation),self.assertRaises((ValueError,SyntaxError)):M._direct_square_equation(equation,'x')
        with self.assertRaises(ValueError):M.direct_square_equations({'variable':'xx','options':[]})

    def symmetry(self):
        return {'relation_expression':definition('T'),'property_expression':definition('S'),'options':[
            O('two versus one',claim='free_shape_arities',arities=[2,1]),
            O('same meaning',claim='identical_predicates',counterexample_shape=[[0,0],[3,0],[0,4]],half_turn_center=[0,0]),
            O('quarter turn definition',claim='equivalent_rotation_invariance',angles=[180,90],counterexample_shape=[[0,0],[2,0],[2,1],[0,1]])]}

    def test_free_shape_arity_is_computed_from_bound_formal_expressions(self):
        self.assertEqual(M.central_symmetry_types(self.symmetry()),'two versus one')
        spec=self.symmetry();spec['relation_expression']=definition('T','z');spec['property_expression']=definition('S','z')
        self.assertEqual(M.central_symmetry_types(spec),'two versus one')
        _,free=M._free_variables({'tag':'exists','variables':[{'name':'T','sort':'shape'}],'body':definition('T')})
        self.assertEqual(free,{'shape':{'S'},'point':set()})

    def test_free_center_or_wrong_variable_sort_is_not_an_intrinsic_property(self):
        spec=self.symmetry();spec['property_expression']['variables'][0]['name']='z'
        with self.assertRaises(ValueError):M.central_symmetry_types(spec)
        spec=self.symmetry();spec['property_expression']=definition('T')
        with self.assertRaises(ValueError):M.central_symmetry_types(spec)
        expr=definition('T');expr['variables'][0]['sort']='shape'
        with self.assertRaises(ValueError):M._free_variables(expr)
        spec=self.symmetry();spec['options'][0]['arities']=[True,1]
        with self.assertRaises(ValueError):M.central_symmetry_types(spec)

    def test_relation_property_counterexample_must_not_itself_be_centrally_symmetric(self):
        spec=self.symmetry();spec['options'][1]['counterexample_shape']=[[0,0],[2,0],[2,1],[0,1]]
        with self.assertRaises(ValueError):M.central_symmetry_types(spec)
        spec=self.symmetry();spec['options'][1]['half_turn_center']=[4,-3]
        self.assertEqual(M.central_symmetry_types(spec),'two versus one')

    def test_quarter_turn_counterexample_excludes_every_possible_center(self):
        rectangle=M.points([[0,0],[2,0],[2,1],[0,1]],convex=True)
        self.assertTrue(M._rotation_invariant(rectangle,180));self.assertFalse(M._rotation_invariant(rectangle,90))
        spec=self.symmetry();spec['options'][2]['counterexample_shape']=[[0,0],[2,0],[2,2],[0,2]]
        with self.assertRaises(ValueError):M.central_symmetry_types(spec) # square does not separate the two classes
        spec=self.symmetry();spec['options'][2]['angles']=[180,180]
        with self.assertRaises(ValueError):M.central_symmetry_types(spec)
        with self.assertRaises(ValueError):M._rotation_invariant(rectangle,0)

    def certificate(self):
        return {'figure':'square_closed_edge_points_with_45_degree_angle','rules':'isometry_congruence_segment_addition',
            'goal':{'segment':['E','F'],'sum':[['B','E'],['D','F']]},'options':[
             O('invalid congruence',steps=[{'op':'perpendicular_foot','point':'A','line':['E','F'],'name':'H'},
                 {'op':'congruent','triangles':[['A','B','E'],['A','D','F']]}],failure_witness={'a':1,'e':'1/2','f':'1/3'}),
             O('rotation then congruence',steps=[{'op':'quarter_turn','center':'A','maps_from':'D','maps_to':'B','degrees':90,'point':'F','image':'Q'},
                 {'op':'congruent','triangles':[['A','E','F'],['A','E','Q']]}]),
             O('true unrelated fact',steps=[{'op':'perpendicular','segments':[['A','C'],['B','D']]}])]}

    def test_square_proof_accepts_complete_length_chain_and_not_unrelated_truth(self):
        self.assertEqual(M.square_rotation_certificates(self.certificate()),'rotation then congruence')
        spec=self.certificate();spec['options'].reverse()
        self.assertEqual(M.square_rotation_certificates(spec),'rotation then congruence')
        spec=self.certificate();spec['options']=[spec['options'][2]]
        with self.assertRaises(ValueError):M.square_rotation_certificates(spec)

    def test_removing_the_congruence_step_does_not_presupply_the_goal(self):
        spec=self.certificate();spec['options'][1]['steps'].pop()
        with self.assertRaises(ValueError):M.square_rotation_certificates(spec)
        # Appending a correct completion to the other outline is allowed: no key lookup.
        spec=self.certificate();completion=deepcopy(spec['options'][1]['steps']);spec['options'][2]['steps']+=completion;spec['options'].pop(1)
        self.assertEqual(M.square_rotation_certificates(spec),'true unrelated fact')

    def test_two_complete_proofs_are_not_forced_into_one_preselected_answer(self):
        spec=self.certificate();spec['options'][0]['steps']=deepcopy(spec['options'][1]['steps'])
        with self.assertRaises(ValueError):M.square_rotation_certificates(spec)

    def test_false_congruence_requires_a_legal_noncongruent_square_configuration(self):
        for witness in [{'a':1,'e':2,'f':'-1/3'},{'a':1,'e':'1/2','f':'1/2'},{'a':-1,'e':0,'f':-1},
                        {'a':1,'e':'sqrt(2)-1','f':'sqrt(2)-1'}]:
            spec=self.certificate();spec['options'][0]['failure_witness']=witness
            with self.subTest(witness=witness),self.assertRaises(ValueError):M.square_rotation_certificates(spec)
        spec=self.certificate();spec['options'][0].pop('failure_witness')
        with self.assertRaises(ValueError):M.square_rotation_certificates(spec)

    def test_quarter_turn_constructor_needs_the_stated_map_and_a_fresh_image(self):
        for key,value in [('degrees',180),('maps_to','C'),('image','B')]:
            spec=self.certificate();spec['options'][1]['steps'][0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):M.square_rotation_certificates(spec)
        spec=self.certificate();spec['rules']='any_unwritten_argument'
        with self.assertRaises(ValueError):M.square_rotation_certificates(spec)
        spec=self.certificate();spec['options'][1]['steps'][1]['op']='guess'
        with self.assertRaises(ValueError):M.square_rotation_certificates(spec)

    def test_closed_edge_endpoints_have_proper_target_triangles(self):
        # These are independent endpoint checks, not the universal proof.
        for e,f in [(S.Integer(0),S.Integer(1)),(S.Integer(1),S.Integer(0)),(S.Rational(1,2),S.Rational(1,3))]:
            a=S.Matrix([0,0]);p=S.Matrix([1,e]);q=S.Matrix([f,1]);image=S.Matrix([1,-f])
            self.assertNotEqual(S.det(S.Matrix.hstack(p,q)),0)
            self.assertNotEqual(S.det(S.Matrix.hstack(p,image)),0)
            self.assertEqual(S.simplify((p-q).dot(p-q)-(e+f)**2),0)
            self.assertEqual(S.simplify((p-image).dot(p-image)-(e+f)**2),0)

    def test_proof_goal_must_match_the_length_chain_actually_completed(self):
        spec=self.certificate();spec['goal']['segment']=['A','C']
        with self.assertRaises(ValueError):M.square_rotation_certificates(spec)
        spec=self.certificate();spec['goal']['sum'].append(['A','B'])
        with self.assertRaises(ValueError):M.square_rotation_certificates(spec)

    def table(self):
        return {'classification':'one_category_per_person_exhaustive','population':40,'counts':[15,12,10],'header':40,'options':[
            O('valid original',claim='valid_table'),O('change header only',claim='valid_after_header_edit',new_header=37),
            O('contradiction',claim='inconsistency_certificate',row_sum=37,known_population=40)]}

    def test_partition_guard_checks_population_in_addition_to_header_sum(self):
        self.assertEqual(M.partition_table_audit(self.table()),'contradiction')
        spec=self.table();spec['population']=37;spec['options'][2]['known_population']=37
        self.assertEqual(M.partition_table_audit(spec),'change header only')
        spec['header']=37
        self.assertEqual(M.partition_table_audit(spec),'valid original')

    def test_partition_claimed_arithmetic_is_not_accepted_as_input_truth(self):
        for field,value in [('row_sum',38),('known_population',39)]:
            spec=self.table();spec['options'][2][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):M.partition_table_audit(spec)
        spec=self.table();spec['options'][1]['new_header']=40
        self.assertEqual(M.partition_table_audit(spec),'contradiction')

    def test_partition_requires_single_exhaustive_categories_and_integer_counts(self):
        for field,value in [('classification','multi_select'),('population',0),('counts',[15,-1,10]),('counts',[True,12,10]),('counts',[15,'1/2',10]),('counts',[])]:
            spec=self.table();spec[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):M.partition_table_audit(spec)
        spec=self.table();spec['options'][1]['new_header']='__import__("os")'
        with self.assertRaises((ValueError,SyntaxError)):M.partition_table_audit(spec)


    def test_zeroth_powers_cannot_erase_the_original_nonzero_domain(self):
        for equation in [['x**2','1-x**0'],['(x-1)**2','1-(x-1)**0'],['x**2+x**0','x**0']]:
            with self.subTest(equation=equation),self.assertRaises(ValueError):M._direct_square_equation(equation,'x')
        self.assertTrue(M._direct_square_equation(['x**2','1-2**0'],'x'))
        self.assertTrue(M._direct_square_equation(['x**2','1-(x-x+1)**0'],'x'))


if __name__=='__main__':unittest.main()
