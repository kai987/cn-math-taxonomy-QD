"""Counterfactual and boundary tests for independent application proof models."""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import models_applications as M


def O(text, **data):return dict(key=text,text=text,**data)
def V(text,value):return O(text,value=value)
def S(kind,query,inputs,options=None):
    value={'kind':'app_'+kind,'query':query,'inputs':inputs}
    if options is not None:value['options']=options
    return value


class ApplicationsModelTests(unittest.TestCase):
    def test_semantic_comparison_keeps_boolean_and_number_types_distinct(self):
        self.assertFalse(M.eq(True,1));self.assertFalse(M.eq(False,0))
        self.assertFalse(M.eq({'similar':True},{'similar':1}))
        self.assertFalse(M.eq([False],[0]));self.assertTrue(M.eq(True,True))
        self.assertTrue(M.eq('1/2',Fraction(1,2)))
        with self.assertRaises(ValueError):M.F(True)

    def test_unique_selection_rejects_duplicate_semantic_answers_and_no_answer(self):
        spec=S('affine','monotonic',{'slope':-2},[V('a','decreasing'),V('b','increasing')])
        self.assertEqual(M.affine(spec),'a')
        spec['inputs']['slope']=3;self.assertEqual(M.affine(spec),'b')
        spec['options'].append(V('also b','increasing'))
        with self.assertRaises(ValueError):M.affine(spec)
        spec['options']=[V('none','constant')]
        with self.assertRaises(ValueError):M.affine(spec)

    def test_two_distinct_correct_points_required(self):
        spec=S('affine','points',{'slope':3,'intercept':2},[
            O('same twice',points=[[0,2],[0,2]]),O('two valid',points=[[0,2],[2,8]]),O('one wrong',points=[[0,2],[1,6]])])
        self.assertEqual(M.affine(spec),'two valid')
        spec['inputs']['intercept']=1
        with self.assertRaises(ValueError):M.affine(spec)

    def test_ordered_axes_and_line_intersection_proofs(self):
        proof=M.affine(S('affine','axes',{'slope':-2,'intercept':6}))
        self.assertTrue(proof.matches('(0,6),(3,0)'))
        self.assertFalse(proof.matches('(3,0),(0,6)'))
        self.assertFalse(proof.matches('6,3'))
        proof=M.affine(S('affine','intersection',{'slope':2,'intercept':1,'second_slope':-1,'second_intercept':7}))
        self.assertTrue(proof.matches('(2,5)'));self.assertFalse(proof.matches('(5,2)'))
        with self.assertRaises(ValueError):M.affine(S('affine','intersection',{'slope':2,'intercept':1,'second_slope':2,'second_intercept':7}))

    def test_affine_signs_and_nonzero_parameter_are_complete_ranges(self):
        options=[V('strict',['>',3]),V('wrong',['<',3]),V('closed',['≥',3])]
        self.assertEqual(M.affine(S('affine','positive_set',{'slope':2,'intercept':-6},options)),'strict')
        self.assertEqual(M.affine(S('affine','positive_set',{'slope':-2,'intercept':6},options)),'wrong')
        proof=M.affine(S('affine','nonzero_parameter',{'slope':2,'intercept':-6,'variable':'m'}))
        self.assertTrue(proof.matches('m≠3'));self.assertFalse(proof.matches('m>3'))
        self.assertEqual(M.affine(S('affine','nonzero_parameter_choice',{'slope':2,'intercept':-6,'variable':'m'},[V('all but 3',['≠',3]),V('only positive',['>',3])])),'all but 3')

    def test_quadrants_depend_on_coefficient_signs_not_magnitudes(self):
        self.assertEqual(M.linear_quadrants(-7,2),[1,2,4])
        self.assertEqual(M.linear_quadrants('-1/1000',500),[1,2,4])
        self.assertEqual(M.linear_quadrants(3,0),[1,3])
        self.assertEqual(M.linear_quadrants(0,-2),[3,4])
        spec=S('affine','quadrants_to_parameters',{'quadrants':[1,2,4]},[V('neg pos',[-1,1]),V('neg neg',[-1,-1])])
        self.assertEqual(M.affine(spec),'neg pos')

    def test_polynomial_classification_simplifies_cancellation_and_rejects_other_variables(self):
        options=[O('cancels',expression='x**2+2*x-x**2'),O('quadratic',expression='2*(x-1)**2'),O('rational',expression='1/x+x**2'),O('two vars',expression='x**2+y')]
        self.assertEqual(M.polynomial_class(S('polynomial_class','classify',{'degree':2},options)),'quadratic')
        self.assertEqual(M.polynomial_class(S('polynomial_class','classify',{'degree':1,'zero_constant':True},options)),'cancels')
        with self.assertRaises(ValueError):M.polynomial_class(S('polynomial_class','classify',{'degree':0},options))

    def test_quadratic_root_candidates_validate_denominator_before_dividing(self):
        options=[O('undefined',center=1,radicand=1,scale=0),O('complex',center=1,radicand=-1,scale=1),O('roots',center=1,radicand=4,scale=1),O('wrong sum',center=-1,radicand=4,scale=1)]
        spec=S('quadratic','roots',{'coefficients':[1,-2,-3]},options)
        self.assertEqual(M.quadratic(spec),'roots')
        spec['inputs']['coefficients']=[1,2,-3];self.assertEqual(M.quadratic(spec),'wrong sum')
        options.append(O('equivalent roots',center=1,radicand=16,scale=2))
        spec['inputs']['coefficients']=[1,-2,-3]
        with self.assertRaises(ValueError):M.quadratic(spec)

    def test_quadratic_geometry_width_and_strict_rank(self):
        self.assertEqual(M.quadratic(S('quadratic','increasing',{'coefficients':[-2,8,0]},[V('left',['<',2]),V('right',['>',2])])),'left')
        self.assertEqual(M.quadratic(S('quadratic','widest',{},[O('wide',coefficient='1/4'),O('narrow',coefficient=-2)])),'wide')
        with self.assertRaises(ValueError):M.quadratic(S('quadratic','rank',{'coefficients':[1,0,0],'xs':[-1,1]},[V('tie ignored',[0,1])]))
        with self.assertRaises(ValueError):M.quadratic(S('quadratic','graph',{'coefficients':[0,1,2]},[]))

    def test_inverse_monotonicity_is_explicitly_per_branch(self):
        spec=S('inverse','graph',{'k':-8},[
            V('each branch',{'quadrants':[2,4],'branch_monotonic':'increasing'}),
            V('global claim',{'quadrants':[2,4],'monotonic':'increasing'}),
            V('wrong slope',{'quadrants':[2,4],'branch_monotonic':'decreasing'})])
        self.assertEqual(M.inverse(spec),'each branch')
        with self.assertRaises(ValueError):M.inverse(S('inverse','graph',{'k':0},spec['options']))
        self.assertEqual(M.inverse(S('inverse','point',{'point':[-2,4]},[O('right',point=[4,-2]),O('wrong',point=[4,2])])),'right')

    def test_inverse_classifier_and_physical_domain(self):
        self.assertEqual(M.inverse(S('inverse','classify',{},[O('linear',numerator='x',denominator='5'),O('inverse',numerator='5',denominator='x'),O('zero',numerator='0',denominator='x')])),'inverse')
        spec=S('inverse','physical_formula',{'k':8},[V('right',{'power':-1,'coefficient':8,'positive_domain':True}),V('no positive width',{'power':-1,'coefficient':8,'positive_domain':False})])
        self.assertEqual(M.inverse(spec),'right')

    def test_rational_sign_table_splits_at_poles_and_respects_multiplicity(self):
        spec=S('rational_sign','positive_intervals',{'zeros':[-3,2],'poles':[0],'leading':1,'sign':1},[
            V('right intervals',[[-3,0],[2,None]]),V('forgot pole',[[-3,2]]),V('negative intervals',[[None,-3],[0,2]])])
        self.assertEqual(M.rational_sign(spec),'right intervals')
        spec['inputs']['sign']=-1;self.assertEqual(M.rational_sign(spec),'negative intervals')
        self.assertEqual(M.rational_sign(S('rational_sign','positive_intervals',{'zeros':[1,1],'poles':[],'leading':1,'sign':1},[V('both sides',[[None,1],[1,None]]),V('all',[[None,None]])])),'both sides')

    def test_variance_units_and_iqr_comparisons(self):
        spec=S('statistics','stable',{'samples':[{'kind':'sd','spread':'1.5'},{'kind':'variance','spread':2}]},[V('first',[0]),V('second',[1])])
        self.assertEqual(M.statistics_model(spec),'second')
        spec['inputs']['samples'][1]['spread']=3;self.assertEqual(M.statistics_model(spec),'first')
        self.assertEqual(M.statistics_model(S('statistics','iqr',{'quartiles':[[2,8],[4,6]]},[V('first',[0]),V('second',[1])])),'second')
        with self.assertRaises(ValueError):M.statistics_model(S('statistics','iqr',{'quartiles':[[8,2]]},[V('bad',[0])]))

    def test_translation_variance_is_symbolic_and_chart_scale_requires_coverage(self):
        self.assertEqual(M.statistics_model(S('statistics','translate_variance',{'shift':1000000},[V('same','same'),V('larger','second')])),'same')
        axes=[O('clips',start=0,stop=100,step=10),O('good',start=0,stop=500,step=100),O('coarse',start=0,stop=5000,step=1000)]
        spec=S('statistics','axis_scale',{'data':[120,350,410]},axes)
        self.assertEqual(M.statistics_model(spec),'good')
        spec['inputs']['data']=[1000,3000];self.assertEqual(M.statistics_model(spec),'coarse')

    def test_finite_events_distinguish_impossible_random_and_certain(self):
        for value,expected in [(7,'不可能事件'),(3,'随机事件')]:
            proof=M.probability(S('probability','classification',{'experiments':[[1,2,3,4,5,6]],'event':{'op':'eq','value':value}}))
            self.assertTrue(proof.matches(expected))
        proof=M.probability(S('probability','classification',{'experiments':[['red']],'event':{'op':'eq','value':'red'}}))
        self.assertTrue(proof.matches('必然事件'))
        with self.assertRaises(ValueError):M.probability(S('probability','classification',{'experiments':[[]],'event':{'op':'eq','value':1}}))

    def test_without_replacement_urn_uses_labelled_combinations(self):
        spec=S('probability','certain_option',{'urn':{'counts':{'W':3,'Y':2},'draws':3,'replace':False}},[
            O('one white',event={'op':'count_ge','value':'W','count':1}),O('one yellow',event={'op':'count_ge','value':'Y','count':1}),O('all white',event={'op':'all_equal','value':'W'})])
        self.assertEqual(M.probability(spec),'one white')
        spec['inputs']['urn']['replace']=True
        with self.assertRaises(ValueError):M.probability(spec)
        self.assertEqual(len(M.outcomes({'urn':{'counts':{'W':3,'Y':2},'draws':3,'replace':False}})),60)
        with self.assertRaises(ValueError):M.outcomes({'urn':{'counts':{'W':1},'draws':2,'replace':False}})

    def test_each_candidate_can_have_a_distinct_experiment(self):
        spec=S('probability','certain_option',{},[
            O('coin',experiment={'experiments':[['H','T']]},event={'op':'eq','value':'H'}),
            O('red bag',experiment={'experiments':[['R']]},event={'op':'eq','value':'R'})])
        self.assertEqual(M.probability(spec),'red bag')
        spec['options'][0]['event']={'op':'in','values':['H','T']}
        with self.assertRaises(ValueError):M.probability(spec)

    def test_probability_rank_and_equal_reward_winner_are_enumerated(self):
        events=[{'op':'sum_in','values':[7]},{'op':'sum_in','values':[6,8]}]
        spec=S('probability','winner',{'experiments':[list(range(1,7))]*2,'events':events,'rewards':[1,1]},[V('first',[0]),V('second',[1])])
        self.assertEqual(M.probability(spec),'second')
        spec['inputs']['rewards']=[2,1];self.assertEqual(M.probability(spec),'first')
        spec['inputs']['rewards']=[1]
        with self.assertRaises(ValueError):M.probability(spec)
        proof=M.probability(S('probability','color_order',{'urn':{'counts':{'红':5,'白':3,'黄':2},'draws':1,'replace':False}}))
        self.assertTrue(proof.matches('红球＞白球＞黄球'));self.assertFalse(proof.matches('黄球＞白球＞红球'))

    def test_probability_range_keeps_nontrivial_endpoints_open(self):
        options=[V('zero',0),V('one',1),V('middle','3/4'),V('too large','6/5')]
        self.assertEqual(M.probability_number(S('probability_number','range',{'lower':0,'upper':1,'strict':True},options)),'middle')
        with self.assertRaises(ValueError):M.probability_number(S('probability_number','range',{'lower':0,'upper':1,'strict':False},options))

    def test_sampling_frame_excludes_hidden_coverage_bias(self):
        spec=S('sampling','equal_inclusion',{'population':[1,2,3,4],'sample_size':2},[
            O('fixed',method='fixed',frame=[1,2,3,4]),O('incomplete',method='simple_random',frame=[1,2]),
            O('teacher selection has a valid biased witness',method='unspecified',frame=[1,2,3,4],counterexample={'method':'fixed','frame':[1,2,3,4]}),O('uniform',method='simple_random',frame=[1,2,3,4])])
        self.assertEqual(M.sampling(spec),'uniform')
        saved=deepcopy(spec['options'][2]['counterexample'])
        del spec['options'][2]['counterexample']
        with self.assertRaises(ValueError):M.sampling(spec)
        spec['options'][2]['counterexample']={'method':'simple_random','frame':[1,2,3,4]}
        with self.assertRaises(ValueError):M.sampling(spec)
        spec['options'][2]['counterexample']=saved
        spec['options'][-1]['frame']=[1,2,3,5]
        with self.assertRaises(ValueError):M.sampling(spec)

    def test_circle_positions_have_three_distinct_distance_cases(self):
        options=[V('inside','inside'),V('on','on'),V('outside','outside')]
        for offset,expected in [([3,0],'inside'),([3,4],'on'),([6,0],'outside')]:
            self.assertEqual(M.circle_position(S('circle_position','point',{'radius':5,'offset':offset},options)),expected)
        self.assertEqual(M.circle_position(S('circle_position','axes',{'radius':4,'center':[3,4]},[V('order matters',['tangent','secant']),V('swapped',['secant','tangent'])])),'order matters')
        with self.assertRaises(ValueError):M.circle_position(S('circle_position','point',{'radius':0,'offset':[0,0]},options))

    def test_pythagorean_tangency_requires_oa_to_be_the_radius(self):
        spec=S('circle_position','pythagorean_tangent',{'radius':5,'lengths':[5,12,13]},[V('tangent','tangent'),V('secant','secant')])
        self.assertEqual(M.circle_position(spec),'tangent')
        spec['inputs']['radius']=4
        with self.assertRaises(ValueError):M.circle_position(spec)
        spec['inputs']={'radius':5,'lengths':[5,2,8]}
        with self.assertRaises(ValueError):M.circle_position(spec)

    def test_proportion_checks_all_permutations_without_reusing_a_length(self):
        options=[O('yes',lengths=[6,2,4,3]),O('no',lengths=[1,2,3,4])]
        self.assertEqual(M.proportions(S('proportions','permutable',{},options)),'yes')
        options.append(O('second valid',lengths=[2,5,4,10]))
        with self.assertRaises(ValueError):M.proportions(S('proportions','permutable',{},options))

    def test_rational_identity_is_universal_not_an_accidental_sample_value(self):
        options=[O('identity',left=['t','1-t'],right=['2*t','2-2*t']),O('coincidence only',left=['t','1'],right=['t','1-t'])]
        self.assertEqual(M.rational_identity(S('rational_identity','test',{'select_true':False},options)),'coincidence only')
        options[0]['left'][1]='0'
        with self.assertRaises(ValueError):M.rational_identity(S('rational_identity','test',{'select_true':False},options))

    def test_triangle_similarity_uses_angle_sum_and_the_included_angle(self):
        aa=S('triangle_similarity','angle_equalities',{'equal_angle_pairs':[['A','D'],['B','E']]},[
            V('AA',{'similar':True,'criterion':'AA'}),V('not SSS input',{'similar':True,'criterion':'SSS'})])
        self.assertEqual(M.triangle_similarity(aa),'AA')
        aa['inputs']['equal_angle_pairs'][1]=['A','E']
        with self.assertRaises(ValueError):M.triangle_similarity(aa)
        sas=S('triangle_similarity','sas',{'sides':[[4,6],[6,9]],'angles':[50,50]},[V('similar',{'similar':True,'criterion':'SAS'}),V('not similar',{'similar':False,'criterion':'SAS'})])
        self.assertEqual(M.triangle_similarity(sas),'similar')
        sas['inputs']['angles'][1]=60;self.assertEqual(M.triangle_similarity(sas),'not similar')

    def test_parallel_triangles_preserve_order_for_arbitrary_symbolic_vertices(self):
        spec=S('triangle_similarity','parallel_correspondence',{'names':['A','D','E','B','C']},[
            V('correct',[['A','D','E'],['A','B','C']]),V('reversed',[['A','D','E'],['A','C','B']]),V('different',[['A','D','E'],['D','B','C']])])
        self.assertEqual(M.triangle_similarity(spec),'correct')
        spec['options'][0]['value'][1]=['B','A','C']
        with self.assertRaises(ValueError):M.triangle_similarity(spec)

    def test_quarter_turn_rotations_preserve_length_but_change_quadrants(self):
        options=[V('Q1',1),V('Q2',2),V('Q3',3),V('Q4',4)]
        spec=S('rotation','point',{'angle':180,'point_signs':[-1,1]},options)
        self.assertEqual(M.rotation(spec),'Q4')
        spec['inputs']['angle']=90;self.assertEqual(M.rotation(spec),'Q3')
        spec['inputs']['angle']=45
        with self.assertRaises(ValueError):M.rotation(spec)
        self.assertEqual(M.rotation(S('rotation','length_angle',{'angle':270,'length':8,'vertex_angle':35})),[8,35])

    def test_trigonometry_evaluates_radicals_and_rejects_invalid_geometry(self):
        options=[V('right',[[3,2]]),V('wrong',['1/2'])]
        self.assertEqual(M.trig_model(S('trig','special',{'functions':[['sin',60]]},options)),'right')
        parking=S('trig','parking',{'length':5,'depth':4},[O('fits',angle=45),O('too deep',angle=60)])
        self.assertEqual(M.trig_model(parking),'fits')
        parking['inputs']['depth']=5
        with self.assertRaises(ValueError):M.trig_model(parking)
        parking['options'][0]['angle']=-45
        with self.assertRaises(ValueError):M.trig_model(parking)
        with self.assertRaises(ValueError):M.trig_model(S('trig','triangle',{'angle':0,'opposite':4},[]))
        self.assertEqual(M.trig_model(S('trig','scale_ratio',{'scale':7},[V('unchanged',1),V('scaled',7)])),'unchanged')

    def test_orthographic_projection_uses_rank_and_axis_order(self):
        options=[V('segment','segment'),V('point','point'),V('area','area')]
        self.assertEqual(M.orthographic(S('orthographic','circle_edge_on',{'plane_basis':[[1,0,0],[0,0,1]]},options)),'segment')
        self.assertEqual(M.orthographic(S('orthographic','circle_edge_on',{'plane_basis':[[1,0,0],[0,1,0]]},options)),'area')
        self.assertEqual(M.orthographic(S('orthographic','views',{'shape':'cylinder','height':7,'radius':2},[V('axis vertical',['rectangle','rectangle','circle']),V('swapped',['rectangle','circle','rectangle'])])),'axis vertical')
        with self.assertRaises(ValueError):M.orthographic(S('orthographic','views',{'shape':'cylinder','height':0},[]))

    def test_radical_domain_has_open_endpoint_only_when_denominator(self):
        options=[V('open',['>',3]),V('closed',['≥',3]),V('wrong',['<',3])]
        self.assertEqual(M.radical_domain(S('radical_domain','domain',{'slope':2,'intercept':-6,'in_denominator':True},options)),'open')
        self.assertEqual(M.radical_domain(S('radical_domain','domain',{'slope':2,'intercept':-6,'in_denominator':False},options)),'closed')
        self.assertEqual(M.radical_domain(S('radical_domain','domain',{'slope':-2,'intercept':6,'in_denominator':True},options)),'wrong')

    def test_growth_model_expands_compounding_and_rejects_simple_interest(self):
        options=[O('compound',left='10*(1+x)**3',right='20'),O('simple',left='10*(1+3*x)',right='20')]
        self.assertEqual(M.growth_equation(S('growth_equation','growth',{'initial':10,'final':20,'periods':3},options)),'compound')
        with self.assertRaises(ValueError):M.growth_equation(S('growth_equation','growth',{'initial':0,'final':20,'periods':3},options))

    def test_product_power_and_symbolic_normalization_do_not_encode_answer_keys(self):
        options=[V('inverse',-1),V('inverse square',-2)]
        self.assertEqual(M.monomial_product(S('monomial_product','power',{'x_power':1},options)),'inverse')
        self.assertEqual(M.monomial_product(S('monomial_product','power',{'x_power':2},options)),'inverse square')
        options=[V('one',1),V('two',2)]
        self.assertEqual(M.symbolic_ratio(S('symbolic_ratio','constant',{'numerator':'a+b','denominator':'a+b'},options)),'one')
        self.assertEqual(M.symbolic_ratio(S('symbolic_ratio','constant',{'numerator':'2*a+2*b','denominator':'a+b'},options)),'two')
        with self.assertRaises(ValueError):M.symbolic_ratio(S('symbolic_ratio','constant',{'numerator':'a+2*b','denominator':'a+b'},options))

    def test_grouped_weighted_mean_compares_formulas_exactly(self):
        options=[O('weighted',numerator='a*u+b*v',denominator='u+v'),O('unweighted',numerator='a+b',denominator='2')]
        self.assertEqual(M.weighted_mean_formula(S('weighted_mean_formula','formula',{'midpoints':['a','b'],'frequencies':['u','v']},options)),'weighted')
        options.append(O('equivalent scaled',numerator='2*a*u+2*b*v',denominator='2*u+2*v'))
        with self.assertRaises(ValueError):M.weighted_mean_formula(S('weighted_mean_formula','formula',{'midpoints':['a','b'],'frequencies':['u','v']},options))

    def test_grouping_witnesses_refute_universals_but_do_not_prove_them(self):
        options=[O('possible error',claim='possible_error'),O('always exact',claim='always_equal'),O('always positive',claim='always_overestimate')]
        spec=S('grouping_error','bias',{'witnesses':[[{'lower':0,'upper':2,'data':['1/2']}],[{'lower':0,'upper':2,'data':['3/2']}]]},options)
        self.assertEqual(M.grouping_error(spec),'possible error')
        spec['inputs']['witnesses']=spec['inputs']['witnesses'][:1]
        with self.assertRaises(ValueError):M.grouping_error(spec)
        spec['inputs']['witnesses']=[[{'lower':0,'upper':2,'data':[2]}]]
        with self.assertRaises(ValueError):M.grouping_error(spec)

    def test_rotation_metric_proof_rejects_stretch_and_supplementary_angles(self):
        options=[O('isometry',length_ratio=1,cosine_sign=1),O('stretch',length_ratio=2,cosine_sign=1),O('supplement',length_ratio=1,cosine_sign=-1)]
        self.assertEqual(M.rotation_invariants(S('rotation_invariants','metric',{},options)),'isometry')
        options.append(O('negative distance',length_ratio=-1,cosine_sign=1))
        self.assertEqual(M.rotation_invariants(S('rotation_invariants','metric',{},options)),'isometry')
        options.append(O('duplicate',length_ratio=1,cosine_sign=1))
        with self.assertRaises(ValueError):M.rotation_invariants(S('rotation_invariants','metric',{},options))

    def test_symbolic_circumcenter_is_general_not_an_isosceles_coincidence(self):
        spec=S('equidistant_point','circumcenter',{'vertices':[['0','0'],['a','0'],['0','b']]},[
            O('vertex',numerators=['0','0'],denominator='1'),
            O('altitude foot',numerators=['a*b**2','a**2*b'],denominator='a**2+b**2'),
            O('hypotenuse midpoint',numerators=['a','b'],denominator='2')])
        self.assertEqual(M.equidistant_point(spec),'hypotenuse midpoint')
        spec['options'][-1]['numerators']=['b','a']
        with self.assertRaises(ValueError):M.equidistant_point(spec)

    def test_half_turn_shape_families_include_odd_polygon_counterexamples(self):
        options=[O('all central',shapes=[{'shape':'parallelogram'},{'shape':'circle'}]),O('odd',shapes=[{'shape':'regular_polygon','vertices':5}]),O('triangle',shapes=[{'shape':'triangle'}])]
        self.assertEqual(M.central_symmetry(S('central_symmetry','families',{},options)),'all central')
        options[1]['shapes'][0]['vertices']=6
        with self.assertRaises(ValueError):M.central_symmetry(S('central_symmetry','families',{},options))

    def test_binomial_support_refutes_exact_frequency_and_gamblers_fallacy(self):
        options=[O('fixed five',claim='fixed_count',count=5),O('not guaranteed',claim='not_fixed_count_with_concentration',count=5),O('wrong marginal',claim='single_probability',probability='1/10')]
        self.assertEqual(M.bernoulli_claims(S('bernoulli_claims','count',{'p':'1/2','trials':10},options)),'not guaranteed')
        options=[O('concentrates',claim='concentration'),O('gambler',claim='next_probability_greater',history_heads=0,history_trials=3,probability='1/2'),O('rare guaranteed',claim='fixed_count',count=1,experiment={'p':'1/100','trials':100})]
        self.assertEqual(M.bernoulli_claims(S('bernoulli_claims','claims',{'p':'1/2','trials':100},options)),'concentrates')
        with self.assertRaises(ValueError):M.bernoulli_claims(S('bernoulli_claims','claims',{'p':0,'trials':100},options))

    def test_nonuniform_die_cannot_identify_a_single_face_probability(self):
        spec=S('identifiability','probability',{'outcome_count':3,'target_index':2,'distributions':[['1/2','1/6','1/3'],['1/4','1/4','1/2']]},[
            O('forced',claim='forced_probability',probability='1/3'),O('not identified',claim='not_identified'),O('infinite',claim='infinite_outcomes')])
        self.assertEqual(M.identifiability(spec),'not identified')
        spec['inputs']['distributions'][1]=['1/3']*3
        with self.assertRaises(ValueError):M.identifiability(spec)
        spec['inputs']['distributions'][1]=['1/2','1/6','1/3']
        with self.assertRaises(ValueError):M.identifiability(spec)

    def test_shadow_derivative_sign_requires_all_factors_strictly_positive(self):
        spec=S('positive_rational_sign','shadow',{'positive_variables':['h','g'],'coefficient':1,'numerator_powers':{'h':1},'denominator_powers':{'g':1}},[V('grows','increasing'),V('shrinks','decreasing')])
        self.assertEqual(M.positive_rational_sign(spec),'grows')
        spec['inputs']['coefficient']=-1;self.assertEqual(M.positive_rational_sign(spec),'shrinks')
        spec['inputs']['positive_variables']=['h']
        with self.assertRaises(ValueError):M.positive_rational_sign(spec)


    def test_without_replacement_preserves_first_draw_events(self):
        spec=S('probability','classification',{'urn':{'counts':{'R':1,'B':1},'draws':2,'replace':False},'event':{'op':'eq','index':0,'value':'R'}})
        proof=M.probability(spec)
        self.assertTrue(proof.matches('随机事件'));self.assertFalse(proof.matches('必然事件'))
        self.assertEqual(sorted(M.outcomes(spec['inputs'])),[('B','R'),('R','B')])

    def test_trigonometric_identities_do_not_accept_nearby_rationals(self):
        almost='500000000001/1000000000000'
        spec=S('trig','special',{'functions':[['sin',30]]},[V('exact',['1/2']),V('too close for float',[almost])])
        self.assertEqual(M.trig_model(spec),'exact')
        spec['options']=spec['options'][1:]
        with self.assertRaises(ValueError):M.trig_model(spec)
        # A tiny depth shortfall must not be hidden by a numerical tolerance.
        spec=S('trig','parking',{'length':1,'depth':'499999999999/1000000000000'},[O('30 degrees does not fit',angle=30)])
        with self.assertRaises(ValueError):M.trig_model(spec)


    def test_event_comparisons_do_not_alias_booleans_to_measurements(self):
        self.assertFalse(M.event({'op':'eq','value':True},(1,)))
        self.assertFalse(M.event({'op':'in','values':[True]},(1,)))
        self.assertFalse(M.event({'op':'all_equal','value':True},(1,)))
        self.assertFalse(M.event({'op':'count_ge','value':True,'count':1},(1,)))
        self.assertFalse(M.event({'op':'sum_in','values':[True]},(1,)))
        self.assertFalse(M.event({'op':'mod','divisor':2,'remainder':True},(1,)))
        with self.assertRaises(ValueError):M.event({'op':'lt','value':2},(True,))
        proof=M.probability(S('probability','classification',{'experiments':[[1]],'event':{'op':'eq','value':True}}))
        self.assertTrue(proof.matches('不可能事件'))


if __name__=='__main__':unittest.main()
