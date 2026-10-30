import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import models_foundations_105 as M


def O(text,**fields):return {'key':text,'text':text,**fields}
def rectangle():return {'kind':'polygon','vertices':[['0','0'],['w','0'],['w','h'],['0','h']]}
def disk():return {'kind':'disk','center':['0','0'],'radius':'r'}
def unroll():
    return {'symbols':{'r':'positive','h':'positive','w':'positive','s':'real','z':'real'},
            'parameters':['s','z'],'bounds':{'s':['0','2*pi*r'],'z':['0','h']},
            'surface':['r*cos(s/r)','r*sin(s/r)','z'],'radius':'r','seam':'separated_boundary_copies',
            'options':[O('disk',region=disk()),O('rectangle',region=rectangle())]}
def projection():
    return {'symbols':{'r':'positive','h':'positive','w':'positive','x':'real','y':'real','z':'real'},
            'radius':'r','height':'h','coordinates':['x','y','z'],'axis':'z','radial':['x','y'],
            'views':[['x','z'],['x','y']],
            'options':[O('front/top',regions=[rectangle(),disk()]),O('reversed',regions=[disk(),rectangle()])]}
def revolution():
    return {'symbols':{'r':'positive','h':'positive','z':'real'},'axis':'z',
            'radial_profile':'r*(1-z/h)','axial_interval':['0','h'],'turn_angle':'2*pi',
            'options':[O('cylinder',solid={'kind':'disk_sections','radius_squared':'r**2','axial_interval':['0','h']}),
                       O('cone',solid={'kind':'disk_sections','radius_squared':'(r*(1-z/h))**2','axial_interval':['0','h']}),
                       O('ball',solid={'kind':'disk_sections','radius_squared':'r**2-(z-r)**2','axial_interval':['0','2*r']}),
                       O('pyramid',solid={'kind':'polyhedral_sections'})]}
def right_angles():
    return [{'vertex':['0','0'],'rays':[['1','0'],['0','1']]},
            {'vertex':['2','0'],'rays':[['1','0'],['0','1']]}]
def slot(v,region='interior',side='right'):return {'vertex':v,'region':region,'side':side}


class Foundations105Tests(unittest.TestCase):
    def test_bounded_ast_rejects_execution_and_unproved_domains(self):
        symbols=M._symbols({'x':'real'})
        for source in ['__import__("os")','x.__class__','[x]','f(x)','x/x','sqrt(x)','0**0','x**100','1/0']:
            with self.subTest(source=source),self.assertRaises((ValueError,SyntaxError)):
                M._parse(source,symbols)
        self.assertEqual(M._parse('0.125',{}),M.S.Rational(1,8))

    def test_parameter_boxes_are_independent_nonempty_continuous_domains(self):
        symbols=M._symbols({'s':'real','z':'real','h':'positive'})
        for bounds in [{'s':['s','s+1'],'z':['0','h']},
                       {'s':['z','z+1'],'z':['0','h']},
                       {'s':['0','0'],'z':['0','h']}]:
            with self.assertRaises(ValueError):M._box_domain(['s','z'],bounds,symbols)
        with self.assertRaises(ValueError):
            M._box_domain(['s'],{'s':['-2','-1']},M._symbols({'s':'positive'}))
        M._box_domain(['s'],{'s':['0','inf']},M._symbols({'s':'positive'}))

    def test_unroll_proves_metric_and_one_separated_winding(self):
        spec=unroll();self.assertEqual(M.cylinder_unroll(spec),'rectangle')
        reflected={**spec,'surface':['r*cos(-s/r)','r*sin(-s/r)','z']}
        self.assertEqual(M.cylinder_unroll(reflected),'rectangle')
        for altered in [
            {**spec,'seam':'joined'},
            {**spec,'bounds':{'s':['0','4*pi*r'],'z':['0','h']}},
            {**spec,'surface':['r*cos(2*s/r)','r*sin(2*s/r)','z']},
            {**spec,'surface':['s','0','z']},
        ]:
            with self.assertRaises(ValueError):M.cylinder_unroll(altered)

    def test_affine_hull_dimension_uses_full_set_upper_bound_and_rank_lower_bound(self):
        options=[O('ball',set={'kind':'linear_ball','radius':'r','basis':[['1','0','0'],['0','1','0'],['0','0','1']]}),
                 O('disk',set={'kind':'linear_ball','radius':'r','basis':[['1','0'],['0','1'],['0','0']]}),
                 O('triangle',set={'kind':'convex_hull','vertices':[['0','0','0'],['1','0','0'],['0','1','0']]})]
        self.assertEqual(M.affine_dimensions({'symbols':{'r':'positive'},'dimension':3,'options':options}),'ball')
        with self.assertRaises(ValueError):M.affine_dimensions({'symbols':{'r':'nonnegative'},'dimension':3,'options':options})
        with self.assertRaises(ValueError):M.affine_dimensions({'symbols':{'r':'positive'},'dimension':True,'options':options})
        with self.assertRaises(ValueError):M._rank(M.S.Matrix([[M.S.Symbol('x',real=True)]]))

    def test_projection_has_bidirectional_elimination_and_view_order(self):
        spec=projection();self.assertEqual(M.cylinder_projection(spec),'front/top')
        exchanged=copy.deepcopy(spec);exchanged['views']=[['x','y'],['x','z']]
        self.assertEqual(M.cylinder_projection(exchanged),'reversed')
        duplicated=copy.deepcopy(spec);duplicated['coordinates']=['x','y','z','z']
        with self.assertRaises(ValueError):M.cylinder_projection(duplicated)

    def test_projection_rejects_dimensions_varying_over_ambient_points(self):
        spec=projection()
        for radius,height in [('sqrt(z*z+1)','1'),('1','sqrt(x*x+1)')]:
            with self.subTest(radius=radius,height=height),self.assertRaises(ValueError):
                M.cylinder_projection({**spec,'radius':radius,'height':height})
        quadrant=copy.deepcopy(spec);quadrant['symbols']['x']='positive'
        quadrant['views']=[['x','y']];quadrant['options']=[O('circle',regions=[disk()])]
        with self.assertRaises(ValueError):M.cylinder_projection(quadrant)

    def test_revolution_compares_complete_sections_and_requires_one_full_turn(self):
        spec=revolution();self.assertEqual(M.revolution(spec),'cone')
        for altered in [{**spec,'turn_angle':'pi'},
                        {**spec,'axial_interval':['z','z+h']},
                        {**spec,'radial_profile':'r'}]:
            with self.assertRaises(ValueError):M.revolution(altered)
        missing=copy.deepcopy(spec);missing['options'][1]['solid']['axial_interval']=[]
        with self.assertRaises(ValueError):M.revolution(missing)

    def test_sweep_dimensions_are_jacobian_proofs_not_label_truth_arrays(self):
        point={'kind':'explicit','coordinates':['0','0','0'],'parameters':[],'bounds':{}}
        regular={'kind':'regular_curve','parameters':['t'],'bounds':{'t':['0','1']}}
        spec={'symbols':{'t':'real'},'query':'classify','motion':{'initial':point,'sweep':regular},
              'options':[O('point to line',dimensions=[0,1]),O('line to plane',dimensions=[1,2])]}
        self.assertEqual(M.sweep_dimensions(spec),'point to line')
        invalid=copy.deepcopy(spec);invalid['options'][0]['dimensions']=[False,1]
        with self.assertRaises(ValueError):M.sweep_dimensions(invalid)

    def test_first_positive_collinearity_solves_the_continuous_open_interval(self):
        spec={'options':[O('right',degrees=90),O('straight',degrees=180),O('full',degrees=360),O('obtuse',interval=[90,180])]}
        self.assertEqual(M.first_collinearity(spec),'straight')
        duplicate=copy.deepcopy(spec);duplicate['options'].append(O('also straight',degrees='360/2'))
        with self.assertRaises(ValueError):M.first_collinearity(duplicate)

    def test_equal_angles_at_different_vertices_are_legal_counterexamples(self):
        witness=right_angles()
        spec={'counterexample':witness,'options':[O('wrong reason',claim='deny_using_vertical_inequality'),
              O('checked witness',claim='deny_with_right_angle_counterexample',counterexample=witness),
              O('converse',claim='equal_implies_vertical')]}
        self.assertEqual(M.equal_angle_converse(spec),'checked witness')
        bad=copy.deepcopy(witness);bad[1]={'vertex':['0','0'],'rays':[['-1','0'],['0','-1']]}
        with self.assertRaises(ValueError):M._equal_not_vertical(bad)

    def test_angle_statement_count_computes_theorems_and_checks_false_witnesses(self):
        statements=[{'claim':'vertical_equal'},
                    {'claim':'equal_implies_vertical','counterexample':right_angles()},
                    {'claim':'parallel_transversal','angles':[slot('upper'),slot('lower')],'relation':'supplementary'},
                    {'claim':'transversal','angles':[slot('upper'),slot('lower','exterior')],'relation':'equal','counterexample':[-20,10]}]
        self.assertEqual(M.angle_propositions({'statements':statements}),2)
        bad=copy.deepcopy(statements);bad[-1]['counterexample']=[10,10]
        with self.assertRaises(ValueError):M.angle_propositions({'statements':bad})

    def test_nonadjacent_supplementary_angles_need_geometry_not_only_angle_sum(self):
        first={'vertex':['0','0'],'rays':[['1','0'],['1/2','sqrt(3)/2']]}
        second={'vertex':['2','0'],'rays':[['1','0'],['-1/2','sqrt(3)/2']]}
        options=[O('equal',claim='neighbor_relation',relation='equal',counterexample_degrees=30),
                 O('supplementary',claim='neighbor_relation',relation='supplementary'),
                 O('inverse',claim='supplementary_implies_adjacent',counterexample=[first,second])]
        self.assertEqual(M.adjacent_angle_claims({'options':options}),'supplementary')

    def test_ruler_construction_guarantees_incidence_and_perpendicularity(self):
        spec={'symbols':{'p':'real','h':'positive','a':'positive','b':'positive'},'point':['p','h'],
              'options':[O('slide leg',plan='aligned_leg_slide',triangle=[['0','0'],['a','0'],['0','b']]),
                         O('parallel',plan='draw_in_aligned_hypotenuse_direction'),
                         O('approximate',plan='approximate_right_angle',tolerance_interval=['0','pi/180']),
                         O('acute vertex',plan='acute_vertex_draw_hypotenuse',counterexample=[['p','h'],['p+1','h'],['p+1/2','h+1/2']])]}
        self.assertEqual(M.ruler_construction(spec),'slide leg')
        invalid=copy.deepcopy(spec);invalid['options'][0]['triangle'][2]=['a','b']
        with self.assertRaises(ValueError):M.ruler_construction(invalid)

    def test_canal_minimum_is_global_and_excludes_on_bank_degeneracy(self):
        options=[O(name,plan=plan) for name,plan in [('any length','all_endpoints_equal_length'),('parallel','parallel_to_bank'),
                 ('foot','orthogonal_projection'),('arbitrary','arbitrary_endpoint_is_minimum')]]
        self.assertEqual(M.shortest_canal({'symbols':{'p':'real','h':'positive'},'point':['p','h'],'options':options}),'foot')
        with self.assertRaises(ValueError):M.shortest_canal({'symbols':{'p':'real'},'point':['p','0'],'options':options})

    def test_general_periodic_decimal_formula_and_concrete_counterexamples(self):
        spec={'base':10,'options':[
            O('infinite all irrational',claim='all_infinite_decimals_irrational',counterexample={'integer':'0','prefix':'0','prefix_length':0,'period':'3','period_length':1}),
            O('radical all irrational',claim='all_radical_expressions_irrational',counterexample='sqrt(4)'),
            O('irrational nonperiodic',claim='irrationals_are_nonterminating_nonperiodic'),
            O('addition closed',claim='irrational_addition_closed',counterexample=['sqrt(2)','-sqrt(2)'])]}
        self.assertEqual(M.decimal_claims(spec),'irrational nonperiodic')
        bad=copy.deepcopy(spec);bad['options'][0]['counterexample']['period']='5'
        # 0.555...=5/9 is also nonterminating, so the conclusion is invariant.
        self.assertEqual(M.decimal_claims(bad),'irrational nonperiodic')
        bad['options'][0]['counterexample']['period']='9'
        with self.assertRaises(ValueError):M.decimal_claims(bad)
        with self.assertRaises(ValueError):M.decimal_claims({**spec,'base':True})

    def test_axis_inverse_is_symbolic_over_full_real_parameter_line(self):
        options=[O('bijection',claim='coordinate_bijection'),O('all rational',claim='all_coordinates_rational',counterexample='sqrt(2)'),
                 O('omit zero',claim='real_sign_partition',signs=[1,-1]),O('zero neither',claim='number_class',value='0',number_class='neither')]
        self.assertEqual(M.real_axis_claims({'options':options}),'bijection')

    def test_notation_printer_does_not_replace_style_by_algebraic_equality(self):
        self.assertEqual(M.notation_format({'options':[O(t,expression=t) for t in ['4a','a×4','1a','a÷b']]}),'4a')
        self.assertEqual(M.canonical_product('2ba'),'2ba') # do not invent an alphabetical-order rule
        self.assertEqual(M.canonical_product('-1a'),'-a')
        for source in ['a+a','a*a','0.5a','1 2a','__import__("os")']:
            with self.subTest(source=source),self.assertRaises((ValueError,SyntaxError)):M.canonical_product(source)


if __name__=='__main__':unittest.main()
