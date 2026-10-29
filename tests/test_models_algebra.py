from fractions import Fraction
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import models_algebra as M


def R(left,op,right):return {'left':left,'op':op,'right':right}
def O(text,**kwargs):return {'key':text,'text':text,**kwargs}


class AlgebraModelTests(unittest.TestCase):
    def test_rational_arithmetic_never_rounds_decimal_tokens(self):
        self.assertEqual(M.number('0.100000000000000001-0.1'),Fraction(1,10**18))
        self.assertEqual(M.number('6/(-1/3)'),-18)
        self.assertEqual(M.number('sqrt(9/16)'),Fraction(3,4))
        for source in ['True','x','1/0','0**0','sqrt(2)','sqrt(-1)','f(1)']:
            with self.subTest(source=source),self.assertRaises((ValueError,ZeroDivisionError)):
                M.number(source)

    def test_scientific_value_and_normalized_coefficient_both_required(self):
        options=[O('unnormalized',coefficient='34.5',exponent=5),
                 O('normalized',coefficient='3.45',exponent=6),
                 O('small coefficient',coefficient='0.345',exponent=7)]
        self.assertEqual(M.scientific_notation({'number':'3450000','options':options}),'normalized')
        options.append(O('duplicate normalized',coefficient='3.450',exponent=6))
        with self.assertRaises(ValueError):M.scientific_notation({'number':'3450000','options':options})

    def test_strict_and_closed_feasibility_at_the_same_endpoint(self):
        self.assertFalse(M.feasible([R('x','>','2'),R('x','<=','2')]))
        self.assertTrue(M.feasible([R('x','>=','2'),R('x','<=','2')]))
        self.assertFalse(M.feasible([R('0','>','0')]))
        self.assertTrue(M.feasible([R('0','>=','0')]))

    def test_coupled_elimination_and_variable_renaming(self):
        for x,y in [('x','y'),('z','a')]:
            premises=[R(x+'+'+y,'=','1'),R(x,'>','0'),R(y,'>','0')]
            self.assertTrue(M.implies(premises,R(x,'<','1')))
            self.assertFalse(M.implies(premises,R(x,'<','1/2')))
            self.assertFalse(M.feasible(premises+[R(x,'>=','1')]))

    def test_linear_entailment_rejects_inconsistent_premises(self):
        with self.assertRaises(ValueError):
            M.implies([R('x','>','0'),R('x','<','0')],R('x','=','99'))

    def test_negative_coefficient_and_short_endpoint_normalization(self):
        proof=M.linear_interval({'constraints':[R('-2x','>','6')]})
        self.assertTrue(proof.matches('x<-3'))
        self.assertTrue(proof.matches('-3>x'))
        for wrong in ['x>-3','x≤-3','y<-3','x<3']:
            self.assertFalse(proof.matches(wrong))

    def test_interval_equivalence_requires_both_containments(self):
        spec={'constraints':[R('x','>','1'),R('x','<=','4')],
              'options':[O('half',constraints=[R('x','>','1')]),
                         O('exact',constraints=[R('x','>','1'),R('x','<=','4')]),
                         O('open',constraints=[R('x','>','1'),R('x','<','4')])]}
        self.assertEqual(M.linear_interval(spec),'exact')

    def test_empty_parameter_window_includes_equal_open_endpoints(self):
        options=[O('strict',constraints=[R('a','>','3')]),
                 O('closed',constraints=[R('a','>=','3')])]
        self.assertEqual(M.window_empty_parameter({'lower_variable':'a','upper':3,'options':options}),'closed')
        self.assertEqual(M.window_empty_parameter({'lower_variable':'a','upper':3,'options':options,
                                                   'left_open':False,'right_open':False}),'strict')

    def test_like_terms_keep_all_exponents_and_ignore_coefficient(self):
        self.assertTrue(M.like_terms('3ab','-ba'))
        self.assertTrue(M.like_terms('-3','5'))
        self.assertFalse(M.like_terms('a²b','ab²'))
        with self.assertRaises(ValueError):M.like_terms('a+b','a')
        proof=M.monomial_pairs({'left':'3ab','right':'-ba'})
        self.assertTrue(proof.matches('是同类项'))
        self.assertFalse(proof.matches('是方程的解'))

    def test_ast_definitions_distinguish_expression_relation_and_equation(self):
        for source in ['2a+1','5','m/n','π']:
            self.assertTrue(M.expression_has_kind(source,'algebraic'))
        for source in ['x=3','a-b>0','3>2']:
            self.assertFalse(M.expression_has_kind(source,'algebraic'))
        self.assertTrue(M.expression_has_kind('2x+1=7','linear1'))
        for source in ['x²=4','1/x=2','x+y=3','4+5=9']:
            self.assertFalse(M.expression_has_kind(source,'linear1'))
        self.assertFalse(M.expression_has_kind('x+x','monomial'))
        self.assertFalse(M.expression_has_kind('π=3','equation'))
        self.assertTrue(M.expression_has_kind('-5xy','monomial'))

    def test_definition_capacity_limits_never_become_proved_false(self):
        for kind in ['polynomial','monomial']:
            with self.subTest(kind=kind),self.assertRaises(ValueError):
                M.expression_kind({'target':kind,'want':'false','options':[
                    O('outside capacity',expression='x^9'),O('polynomial',expression='x^2')]})
        for kind in ['linear1','linear2']:
            with self.subTest(kind=kind),self.assertRaises(ValueError):
                M.expression_has_kind('x^9=0',kind)
        with self.assertRaises(ValueError):
            M.system_kind({'unknown_count':2,'equation_count':2,'options':[
                O('unresolved',equations=['x^9+y=0','x-y=1'])]})
        with self.assertRaises(ValueError):M.expression_has_kind('10000000000000000x','polynomial')
        self.assertFalse(M.expression_has_kind('1/x','polynomial'))
        self.assertFalse(M.expression_has_kind('x^-1','polynomial'))

    def test_no_sampling_can_prove_a_polynomial_implication(self):
        options=[O('multiply',premises=['a=b'],conclusion='ac=bc'),
                 O('unsafe cancel',premises=['ac=bc'],conclusion='a=b')]
        self.assertEqual(M.polynomial_implications({'options':options}),'multiply')
        # All trial integer points miss x²=2. The model must say unresolved, not true.
        with self.assertRaises(ValueError):
            M.polynomial_implications({'options':[O('unresolved',premises=['x²=2'],conclusion='x=0')]})

    def test_absolute_domain_partition_keeps_zero(self):
        options=[O('negative',constraints=[R('a','<','0')]),
                 O('nonpositive',constraints=[R('a','<=','0')])]
        self.assertEqual(M.absolute_domain({'variable':'a','right':'-a','options':options}),'nonpositive')

    def test_root_sets_preserve_principal_branch_and_completeness(self):
        options=[O('incomplete',radicand=4,principal=False,claimed_roots=[2]),
                 O('complete',radicand=4,principal=False,claimed_roots=[-2,2])]
        self.assertEqual(M.real_root_sets({'options':options}),'complete')
        options=[O('wrong branch',radicand=4,principal=True,claimed_roots=[-2]),
                 O('positive',radicand=4,principal=True,claimed_roots=[2])]
        self.assertEqual(M.real_root_sets({'options':options}),'positive')

    def test_system_solution_checks_every_equation_and_variable(self):
        options=[O('only first',values={'x':1,'y':4}),O('both',values={'x':2,'y':3})]
        self.assertEqual(M.equation_solution({'equations':['x+y=5','2x-y=1'],'options':options}),'both')
        with self.assertRaises(ValueError):
            M.equation_solution({'equations':['x+y=5'],'values':{'x':2}})
        proof=M.equation_solution({'equations':['3x-1=5'],'values':{'x':2}})
        self.assertTrue(proof.matches('是方程的解'))
        self.assertFalse(proof.matches('是同类项'))

    def test_elimination_must_remove_target_and_retain_other_unknown(self):
        options=[O('subtract',weights=[1,-1]),O('add',weights=[1,1])]
        self.assertEqual(M.linear_elimination({'equations':['x+y=7','x-y=3'],'eliminate':'y','options':options}),'add')
        with self.assertRaises(ValueError):
            M.linear_elimination({'equations':['x+y=7','2x+2y=14'],'eliminate':'y',
                                  'options':[O('zero identity',weights=[2,-1])]})
        with self.assertRaises(ValueError):
            M.linear_elimination({'equations':['x*x+y=0'],'eliminate':'x',
                                  'options':[O('nonlinear',weights=[1])]})

    def test_undefined_option_is_false_but_unknown_syntax_is_not_silenced(self):
        spec={'options':[O('undefined',**R('1/0','=','0'),allow_undefined=True),
                         O('valid',**R('0/3','=','0'))]}
        self.assertEqual(M.numeric_relations(spec),'valid')
        with self.assertRaises(ValueError):
            M.numeric_relations({'options':[O('bad syntax',**R('f(1)','=','1'))]})
        with self.assertRaises(ValueError):
            M.numeric_relations({'options':[O('still unresolved',**R('f(1)','=','1'),allow_undefined=True)]})

    def test_positive_domain_model_refuses_unsupported_polynomial(self):
        with self.assertRaises(ValueError):
            M.positive_polynomial_sign({'variable':'m','sign':-1,
                                       'options':[O('quadratic',expression='-m²+m-1')]})

    def test_geometric_minimum_and_ordered_coordinate_boundaries(self):
        self.assertEqual(M.two_focus_minimum({'a':[2,3],'b':[5,7]}),5)
        self.assertEqual(M.two_focus_minimum({'a':[2,3],'b':[2,3]}),0)
        self.assertEqual(M.coordinate_choices({'point':[4,-5],
                         'options':[O('reverse',point=[-5,4]),O('ordered',point=[4,-5])]}),'ordered')
        with self.assertRaises(ValueError):M.translation_equal_length({'displacement_length':-1})
        with self.assertRaises(ValueError):
            M.point_line_distance({'perpendicular_distance':3,'candidate_length':2,
                                   'options':[O('unknown',claim='unknown')]})


if __name__=='__main__':unittest.main()
