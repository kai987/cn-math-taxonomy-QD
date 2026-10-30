"""Counterfactual tests for full application-family proofs, not stored answers."""
from copy import deepcopy
from fractions import Fraction
from itertools import combinations
from pathlib import Path
import sys
import unittest
import sympy as S

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import models_applications_105 as M


def O(text,**kw):return {'key':text,'text':text,**kw}
def R(a,op,b):return {'left':a,'op':op,'right':b}


class Application105Tests(unittest.TestCase):
    def test_math_parser_has_no_execution_boolean_free_or_hidden_symbol(self):
        for source in [True,"__import__('os')",'x.__class__','x**99','1/0','sqrt(-1)']:
            with self.subTest(source=source),self.assertRaises((ValueError,SyntaxError)):M.math(source)
        with self.assertRaises(ValueError):M.math('q-q+1',{'r':'positive'})
        self.assertEqual(S.simplify(M.math('0.100000000000001-0.1')),S.Rational(1,10**15))
        with self.assertRaises(ValueError):M.zero(S.Symbol('x',real=True)-1)

    def incenter(self):
        return {'family':'nondegenerate_triangle','options':[
            O('circumcenter',intersection='perpendicular_bisectors',counterexample=[[0,0],[4,0],[0,3]]),
            O('incenter',intersection='internal_angle_bisectors'),
            O('orthocenter',intersection='altitudes',counterexample=[[0,0],[4,0],[0,3]])]}

    def test_incenter_has_general_positive_barycentrics_and_equal_distances(self):
        self.assertEqual(M.incenter_intersections(self.incenter()),'incenter')
        spec=self.incenter();spec['options'][0]['counterexample']=[[1,1],[1,7],[-7,1]]
        self.assertEqual(M.incenter_intersections(spec),'incenter')

    def test_incenter_counterexample_cannot_be_equilateral_or_degenerate(self):
        spec=self.incenter();spec['options'][0]['counterexample']=[[0,0],[2,0],[1,'sqrt(3)']]
        with self.assertRaises(ValueError):M.incenter_intersections(spec)
        spec=self.incenter();spec['options'][2]['counterexample']=[[0,0],[1,0],[2,0]]
        with self.assertRaises(ValueError):M.incenter_intersections(spec)
        spec=self.incenter();spec['family']='any_three_points'
        with self.assertRaises(ValueError):M.incenter_intersections(spec)

    def test_incenter_duplicate_or_unknown_intersection_is_not_silently_accepted(self):
        spec=self.incenter();spec['options'].append(O('duplicate',intersection='internal_angle_bisectors'))
        with self.assertRaises(ValueError):M.incenter_intersections(spec)
        spec=self.incenter();spec['options'][0]['intersection']='unknown'
        with self.assertRaises(ValueError):M.incenter_intersections(spec)

    def regular(self):
        return {'minimum_vertices':3,'counterexample_vertices':3,'counterexample_radius':1,'options':[
            O('same radii',left='apothem',op='=',right='circumradius'),
            O('same centers',left='incenter',op='=',right='circumcenter'),
            O('same angles',left='central_angle',op='=',right='interior_angle')]}

    def test_regular_polygon_proof_covers_all_vertex_counts_not_one_sample(self):
        self.assertEqual(M.regular_polygon_metrics(self.regular()),'same centers')
        spec=self.regular();spec['counterexample_vertices']=5
        self.assertEqual(M.regular_polygon_metrics(spec),'same centers')
        spec['counterexample_vertices']=4
        with self.assertRaises(ValueError):M.regular_polygon_metrics(spec) # angles coincide; this is not a refutation

    def test_regular_polygon_domain_and_radius_are_strict(self):
        for field,value in [('minimum_vertices',2),('counterexample_vertices',True),('counterexample_radius',0)]:
            spec=self.regular();spec[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):M.regular_polygon_metrics(spec)

    def circle(self):
        return {'circle_domain':'nondegenerate_inscribed_angles','counterexample_half_angle':'pi/3','counterexample_offset':'pi/6','options':[
            O('whole central',left='inscribed',op='=',right='central'),
            O('both chord sides',left='inscribed',op='=',right='opposite_arc'),
            O('same arc',left='inscribed',op='=',right='same_arc_other')]}

    def test_full_inscribed_angle_family_distinguishes_chord_side(self):
        self.assertEqual(M.inscribed_angle_relations(self.circle()),'same arc')
        spec=self.circle();spec['counterexample_half_angle']='pi/2'
        with self.assertRaises(ValueError):M.inscribed_angle_relations(spec) # diameter exception cannot refute same-chord equality
        spec=self.circle();spec['counterexample_offset']='pi'
        with self.assertRaises(ValueError):M.inscribed_angle_relations(spec)

    def test_inscribed_branch_and_metric_names_must_be_explicit(self):
        spec=self.circle();spec['circle_domain']='includes_degenerate_angles'
        with self.assertRaises(ValueError):M.inscribed_angle_relations(spec)
        spec=self.circle();spec['options'][0]['right']='unknown'
        with self.assertRaises(ValueError):M.inscribed_angle_relations(spec)

    def metric_spec(self):
        return {'counterexample_scale':2,'counterexample_triangle':[[0,0],[1,0],['1/2','sqrt(3)/2']], 'options':[
            O('equal side lengths',relations=[R('side_ratio','=','one')]),
            O('angles and proportional sides',relations=[R('image_cosine','=','original_cosine'),R('side_ratio','=','scale')]),
            O('equal perimeter',relations=[R('perimeter_ratio','=','one')]),
            O('supplementary',relations=[R('image_cosine','=','negative_original_cosine')])]}

    def test_similarity_proof_has_both_orientation_parities_and_nonunit_scales(self):
        self.assertEqual(M.similarity_metrics(self.metric_spec()),'angles and proportional sides')
        spec=self.metric_spec();spec['counterexample_scale']='3/2'
        self.assertEqual(M.similarity_metrics(spec),'angles and proportional sides')
        spec['counterexample_scale']=1
        with self.assertRaises(ValueError):M.similarity_metrics(spec)

    def test_a_right_angle_does_not_refute_universal_supplementary_claim(self):
        spec=self.metric_spec();spec['counterexample_triangle']=[[0,0],[3,0],[0,4]]
        with self.assertRaises(ValueError):M.similarity_metrics(spec)
        spec=self.metric_spec();spec['counterexample_scale']=0
        with self.assertRaises(ValueError):M.similarity_metrics(spec)

    def polygons(self):
        a=[[0,0],[2,0],[2,1],[0,1]];b=[[0,0],[3,0],[3,1],[0,1]]
        return {'options':[
            O('rectangles',family='rectangle',counterexample=[a,b]),
            O('rhombi',family='rhombus',counterexample=[[[0,0],[5,0],[8,4],[3,4]],[[0,0],[5,0],[5,5],[0,5]]]),
            O('squares',family='square'),
            O('equiangular',family='equiangular',counterexample=[a,b])]}

    def test_polygon_similarity_checks_all_vertex_bijections(self):
        self.assertEqual(M.polygon_similarity_families(self.polygons()),'squares')
        a=M.points([[0,0],[2,0],[2,1],[0,1]],convex=True)
        b=M.points([[5,7],[5,9],[6,9],[6,7]],convex=True)
        self.assertTrue(M._similarity(a,b))
        spec=self.polygons();spec['options'][0]['counterexample'][1]=[[5,7],[5,9],[6,9],[6,7]]
        with self.assertRaises(ValueError):M.polygon_similarity_families(spec)

    def test_polygon_counterexamples_must_satisfy_the_family_and_global_convexity(self):
        spec=self.polygons();spec['options'][1]['counterexample'][0]=[[0,0],[2,0],[2,1],[0,1]]
        with self.assertRaises(ValueError):M.polygon_similarity_families(spec)
        star=[[str(S.cos(4*S.pi*k/5)),str(S.sin(4*S.pi*k/5))] for k in range(5)]
        with self.assertRaises(ValueError):M.points(star,convex=True)
        with self.assertRaises(ValueError):M.points([[0,0],[2,2],[0,2],[2,0]],convex=True)

    def rays(self):
        return {'families':{'first':'fixed_direction','second':'point_source'},'options':[
            O('parallel and concurrent',properties=[{'family':'first','property':'parallel'},{'family':'second','property':'concurrent'}]),
            O('both parallel',properties=[{'family':'first','property':'parallel'},{'family':'second','property':'parallel'}]),
            O('both concurrent',properties=[{'family':'first','property':'concurrent'},{'family':'second','property':'concurrent'}])]}

    def test_spatial_light_field_uses_both_target_coordinates(self):
        self.assertEqual(M.ray_family_properties(self.rays()),'parallel and concurrent')
        h=S.Symbol('h',positive=True)
        self.assertEqual(M._ray_family('fixed_direction',h),{'parallel':True,'concurrent':False})
        self.assertEqual(M._ray_family('point_source',h),{'parallel':False,'concurrent':True})
        with self.assertRaises(ValueError):M._ray_family('unknown',h)

    def test_light_field_assumptions_must_come_from_the_problem(self):
        spec={'options':[O('lamp',ray_field='point_source'),O('sun',ray_field='fixed_direction')]}
        self.assertEqual(M.parallel_light_fields(spec),'sun')
        spec['options'][0]['ray_field']='fixed_direction'
        with self.assertRaises(ValueError):M.parallel_light_fields(spec)
        spec['options'][0]['ray_field']='unknown optics'
        with self.assertRaises(ValueError):M.parallel_light_fields(spec)
        spec=self.rays();spec['options'][1]['properties']=[]
        with self.assertRaises(ValueError):M.ray_family_properties(spec)

    def game(self):
        return {'payoffs':[['r','-l','0'],['-l','r','0']],'options':[
            O('same counts',conclusions=[R('n','=','m')],counterexample={'p':'1/2','q':'1/2','n':1,'m':2}),
            O('same probabilities',conclusions=[R('p','=','q')]),
            O('positive probabilities',conclusions=[R('p','>','0'),R('q','>','0')],counterexample={'p':0,'q':0,'n':1,'m':1}),
            O('always ties',conclusions=[R('p','=','0'),R('q','=','0')],counterexample={'p':'1/2','q':'1/2','n':1,'m':1})]}

    def test_expected_payoff_necessity_is_not_a_sufficient_special_case(self):
        self.assertEqual(M.symmetric_game_conditions(self.game()),'same probabilities')
        spec=self.game();spec['payoffs']=[['2*r','-2*l','0'],['-2*l','2*r','0']]
        self.assertEqual(M.symmetric_game_conditions(spec),'same probabilities')
        spec=self.game();spec['options'][3]['counterexample']['p']=0;spec['options'][3]['counterexample']['q']=0
        with self.assertRaises(ValueError):M.symmetric_game_conditions(spec)

    def test_game_rejects_asymmetric_or_zero_payoffs_and_invalid_probabilities(self):
        for payoffs in [[['2*r','-l','0'],['-l','r','0']],[['0','0','0'],['0','0','0']],[['z','-l','0'],['-l','r','0']]]:
            spec=self.game();spec['payoffs']=payoffs
            with self.subTest(payoffs=payoffs),self.assertRaises(ValueError):M.symmetric_game_conditions(spec)
        spec=self.game();spec['options'][0]['counterexample'].update(p=1,q=1)
        with self.assertRaises(ValueError):M.symmetric_game_conditions(spec)
        spec=self.game();spec['options'][0]['counterexample']['n']='1/2'
        with self.assertRaises(ValueError):M.symmetric_game_conditions(spec)

    def test_generic_lottery_counts_agree_with_independent_finite_enumeration(self):
        spec={'mechanism':'uniform_fixed_size_subsets','sample_range':'1<=k<=n','options':[
            O('equal',op='=',quantifier='all_labels'),O('different',op='!=',quantifier='all_labels'),O('rank dependence',op='!=',quantifier='some_ordered_labels')]}
        self.assertEqual(M.lottery_inclusion(spec),'equal')
        for n in range(1,7):
            for k in range(1,n+1):
                samples=list(combinations(range(n),k));probabilities=[Fraction(sum(i in subset for subset in samples),len(samples)) for i in range(n)]
                self.assertEqual(probabilities,[Fraction(k,n)]*n)
        spec['sample_range']='any real k'
        with self.assertRaises(ValueError):M.lottery_inclusion(spec)

    def uniform(self):
        return {'options':[O('unknown coin',outcomes=2,counterexample=['1/3','2/3']),
                           O('equal three masses',outcomes=3,equal_mass_pairs=[[0,1],[1,2]])]}

    def test_unknown_uniformity_needs_an_admissible_nonuniform_countermodel(self):
        self.assertEqual(M.uniformity_guarantees(self.uniform()),'equal three masses')
        spec=self.uniform();spec['options'][0]['counterexample']=['1/2','1/2']
        with self.assertRaises(ValueError):M.uniformity_guarantees(spec)
        spec=self.uniform();spec['options'][0]['counterexample']=['1/3','1/3']
        with self.assertRaises(ValueError):M.uniformity_guarantees(spec)
        spec=self.uniform();spec['options'][0].pop('counterexample')
        with self.assertRaises(ValueError):M.uniformity_guarantees(spec)

    def test_partial_probability_equalities_do_not_force_global_uniformity(self):
        spec={'options':[O('only first pair',outcomes=3,equal_mass_pairs=[[0,1]],counterexample=['1/4','1/4','1/2']),O('all connected',outcomes=3,equal_mass_pairs=[[0,1],[1,2]])]}
        self.assertEqual(M.uniformity_guarantees(spec),'all connected')
        spec['options'][0]['counterexample']=['1/2','1/4','1/4']
        with self.assertRaises(ValueError):M.uniformity_guarantees(spec)
        spec['options'][1]['equal_mass_pairs']=[[0,3]]
        with self.assertRaises(ValueError):M.uniformity_guarantees(spec)

    def test_classical_formula_rejects_unknown_masses_and_infinite_uniform_law(self):
        spec={'options':[O('finite uniform',sample_space='finite',outcomes=4,equal_mass_pairs=[[0,1],[1,2],[2,3]]),
                         O('unknown binary',sample_space='finite',outcomes=2,counterexample=['1/3','2/3']),O('all integers',sample_space='positive_integers')]}
        self.assertEqual(M.classical_sample_spaces(spec),'finite uniform')
        spec['options'][0]['sample_space']='not a declared space'
        with self.assertRaises(ValueError):M.classical_sample_spaces(spec)
        with self.assertRaises(ValueError):M.uniformity_guarantees({'options':[O('boolean count',outcomes=True)]})

    def urn(self):
        return {'allowed_actions':['draw','return_same_ball'],'population_lower_bound':2,'options':[
            O('simultaneous',possible_returns_between_draws=[0],simultaneous_draw_size=2),
            O('return',possible_returns_between_draws=[1]),
            O('same pre-counts',possible_returns_between_draws=[0,1],equal_pre_draw_counts=True)]}

    def test_same_urn_conservation_derives_the_hidden_return(self):
        self.assertEqual(M.replacement_protocols(self.urn()),'simultaneous')
        spec=self.urn();spec['options'][2]['possible_returns_between_draws']=[0]
        with self.assertRaises(ValueError):M.replacement_protocols(spec)
        spec=self.urn();spec['options'][1]['possible_returns_between_draws']=[0,1]
        with self.assertRaises(ValueError):M.replacement_protocols(spec) # unresolved, not default false

    def test_urn_rejects_extra_balls_or_impossible_simultaneous_expansion(self):
        spec=self.urn();spec['allowed_actions'].append('add_ball')
        with self.assertRaises(ValueError):M.replacement_protocols(spec)
        spec=self.urn();spec['options'][0]['possible_returns_between_draws']=[1]
        with self.assertRaises(ValueError):M.replacement_protocols(spec)
        spec=self.urn();spec['options'][0]['possible_returns_between_draws']=[True]
        with self.assertRaises(ValueError):M.replacement_protocols(spec)

    def rain(self):
        return {'event_probability':'7/10','options':[
            O('fixed time',claim='fixed_realized_fraction',fraction='7/10',counterexample_fractions=[1,0]),
            O('fixed area',claim='fixed_realized_fraction',fraction='7/10',counterexample_fractions=[1,0]),
            O('likely not certain',claim='probability_bounds',lower='1/2',upper=1),O('certain',claim='certain_event')]}

    def test_event_probability_is_not_a_fixed_time_or_area_fraction(self):
        self.assertEqual(M.precipitation_interpretations(self.rain()),'likely not certain')
        spec=self.rain();spec['options'][0]['counterexample_fractions']=['1/2',0]
        self.assertEqual(M.precipitation_interpretations(spec),'likely not certain')
        spec=self.rain();spec['options'][0]['counterexample_fractions']=[-1,0]
        with self.assertRaises(ValueError):M.precipitation_interpretations(spec)

    def test_probability_comparison_is_exact_and_countermodel_matches_the_event(self):
        spec=self.rain();spec['options'][2]['lower']='700000000001/1000000000000'
        with self.assertRaises(ValueError):M.precipitation_interpretations(spec) # no valid choice; not isclose
        spec=self.rain();spec['options'][0]['counterexample_fractions']=[1,'1/10']
        with self.assertRaises(ValueError):M.precipitation_interpretations(spec)
        spec=self.rain();spec['event_probability']='11/10'
        with self.assertRaises(ValueError):M.precipitation_interpretations(spec)


    def test_incenter_counterexample_has_exactly_three_physical_vertices(self):
        triangle=[[0,0],[2,0],[1,'sqrt(3)']]
        spec=self.incenter();spec['options'][0]['counterexample']=triangle+[[1,-1]]
        with self.assertRaises(ValueError):M.incenter_intersections(spec)
        ps=M.points(triangle+[[1,-1]])
        with self.assertRaises(ValueError):M._centre(ps,'perpendicular_bisectors')
        with self.assertRaises(ValueError):M._inscribed_center(ps,S.Matrix([1,0]))

    def test_equal_angle_counterexample_requires_a_corresponding_vertex_bijection(self):
        triangle=[[0,0],[2,0],[1,'sqrt(3)']];square=[[0,0],[2,0],[2,2],[0,2]]
        spec=self.polygons();spec['options'][3]['counterexample']=[triangle,square]
        with self.assertRaises(ValueError):M.polygon_similarity_families(spec)


if __name__=='__main__':unittest.main()
