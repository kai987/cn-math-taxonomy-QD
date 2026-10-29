"""Regression tests use altered mathematical inputs, not answer snapshots."""
import copy
from fractions import Fraction
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from models_geometry import (criteria, congruence, correspondence, triangle_closure,
    altitude_positions, coordinate_facts, quadrilateral, symbolic_isometry_count,
    reflection, affine_model, triangle_ratio, circle_intersections, polygon_model,
    triangle_square_model, reflected_path, formula_quantities,
    function_relation, relation_is_function, angle_implication, diagonal_transport)


def options(field,values):
    return [{'key':str(i),'text':str(v),field:v} for i,v in enumerate(values)]


class CongruenceTests(unittest.TestCase):
    def test_ssa_is_not_sas_and_aaa_has_no_scale(self):
        base={'triangles':['ABC','DEF'],'equal_sides':[['AB','DE'],['BC','EF']],
              'equal_angles':[['BAC','EDF']]}
        self.assertEqual(criteria(base),set())
        base['equal_angles']=[['ABC','DEF']]
        self.assertEqual(criteria(base),{'SAS'})
        base['equal_sides']=[]
        base['equal_angles']=[['BAC','EDF'],['ABC','DEF'],['ACB','DFE']]
        self.assertEqual(criteria(base),set())

    def test_direct_asa_aas_distinguishes_included_side(self):
        base={'triangles':['ABC','DEF'],'equal_angles':[['BAC','EDF'],['ABC','DEF']],
              'equal_sides':[['AB','DE']]}
        self.assertEqual(criteria(base),{'ASA'})
        base['equal_sides']=[['BC','EF']]
        self.assertEqual(criteria(base),{'AAS'})

    def test_hl_requires_both_right_angles_and_actual_hypotenuse(self):
        base={'triangles':['ABC','DEF'],'equal_sides':[['AB','DE'],['BC','EF']],
              'right_angles':['ACB','DFE']}
        self.assertEqual(criteria(base),{'HL'})
        base['right_angles']=['ACB']
        self.assertEqual(criteria(base),set())
        base['right_angles']=['BAC','EDF']
        # AB and BC become a leg/hypotenuse pair at A/D, still HL.
        self.assertEqual(criteria(base),{'HL'})
        base['equal_sides']=[['AB','DE'],['AC','DF']]
        self.assertEqual(criteria(base),{'SAS'})

    def test_shared_edges_and_midpoint_generate_sss(self):
        self.assertEqual(criteria({'triangles':['ABD','ACD'],
             'equal_sides':[['AB','AC']],'midpoints':[['D','B','C']]}),{'SSS'})

    def test_numeric_transfer_changes_with_source_and_rejects_missing_proof(self):
        spec={'triangles':['ACD','BDC'],'equal_sides':[['AC','BD']],
              'right_angles':['ADC','BCD'],'query':'length',
              'measurements':{'BC':'13/2'},'target':'AD'}
        self.assertEqual(congruence(spec),Fraction(13,2))
        spec['right_angles']=[]
        with self.assertRaises(ValueError):congruence(spec)

    def test_conflicting_corresponding_measurements_rejected(self):
        spec={'triangles':['ABC','DEF'],'equal_sides':[['AB','DE'],['AC','DF'],['BC','EF']],
              'query':'length','measurements':{'AB':3,'DE':4},'target':'DE'}
        with self.assertRaises(ValueError):congruence(spec)

    def test_condition_query_requires_unique_candidate(self):
        spec={'triangles':['ABC','DEF'],'equal_sides':[['AB','DE'],['AC','DF']],
              'query':'condition','required':'SAS','options':[
              {'key':'1','text':'atA','equal_angles':[['BAC','EDF']]},
              {'key':'2','text':'atB','equal_angles':[['ABC','DEF']]}]}
        self.assertEqual(congruence(spec),'atA')
        spec['options'][1]['equal_angles']=[['BAC','EDF']]
        with self.assertRaises(ValueError):congruence(spec)

    def test_correspondence_is_ordered_bijection(self):
        spec={'triangles':['ABC','DEF'],'pairs':[['A','E'],['B','D'],['C','F']],'entity':'ABC'}
        result=correspondence(spec)
        self.assertTrue(result.matches('△EDF'))
        self.assertFalse(result.matches('DEF'))
        spec['pairs']=[['A','D'],['B','D'],['C','F']]
        with self.assertRaises(ValueError):correspondence(spec)


class EuclideanModelTests(unittest.TestCase):
    def test_derived_angle_equality_transfers_opposite_side(self):
        spec={'triangles':['ABC'],'angle_values':{'BAC':40,'ABC':70},
              'length_values':{'AB':11},'query':'length','target':'AC'}
        self.assertEqual(triangle_closure(spec),11)
        spec['angle_values']['BAC']=50
        with self.assertRaises(ValueError):triangle_closure(spec)

    def test_invalid_angle_sum_rejected(self):
        with self.assertRaises(ValueError):triangle_closure({'triangles':['ABC'],
          'angle_values':{'BAC':30,'ABC':60,'ACB':80},'query':'classification'})

    def test_altitudes_and_orthocenter_depend_on_angle_signs(self):
        self.assertEqual(altitude_positions({'cosine_signs':[1,0,1],'query':'boundary_count'}),2)
        self.assertEqual(altitude_positions({'cosine_signs':[1,1,1],'query':'boundary_count'}),0)
        spec={'cosine_signs':[-1,1,1],'query':'orthocenter','options':options('location',['inside','outside','vertex'])}
        self.assertEqual(altitude_positions(spec),'outside')
        spec['cosine_signs']=[1,1,1]
        self.assertEqual(altitude_positions(spec),'inside')
        spec['cosine_signs']=[0,-1,1]
        with self.assertRaises(ValueError):altitude_positions(spec)

    def test_median_equal_area_is_symbolic_not_one_sample(self):
        spec={'query':'area_relation','points':{'A':['u','v'],'B':[0,0],'C':['b',0]},
          'positive':['b','v'],'constructions':[{'name':'D','points':['B','C'],'weights':[1,1]}],
          'triangles':['ABD','ACD'],'options':options('comparison',['equal','greater'])}
        self.assertEqual(affine_model(spec),'equal')
        spec['constructions'][0]['weights']=[1,2]
        with self.assertRaises(ValueError):affine_model(spec)

    def test_symmetry_rectangle_specializes_to_square(self):
        ds={'0,1':'w**2','0,2':'w**2+h**2','0,3':'h**2','1,2':'h**2','1,3':'w**2+h**2','2,3':'w**2'}
        self.assertEqual(symbolic_isometry_count({'vertices':4,'squared_distances':ds}),2)
        square={k:v.replace('h','w') for k,v in ds.items()}
        self.assertEqual(symbolic_isometry_count({'vertices':4,'squared_distances':square}),4)

    def test_reflection_keeps_other_coordinate_and_is_involution(self):
        opts=[{'key':'a','text':'reflected','point':[-7,4]},{'key':'b','text':'wrong','point':[7,-4]}]
        self.assertEqual(reflection({'axis':'y','point':[7,4],'options':opts}),'reflected')
        opts[0]['point']=[7,4]
        self.assertEqual(reflection({'axis':'y','point':[-7,4],'options':opts}),'reflected')

    def test_circle_radius_condition_excludes_tangency_and_arbitrary_radius(self):
        spec={'options':[{'key':'1','text':'two','condition':'t>1/2'},
                         {'key':'2','text':'tangent','condition':'Eq(t,1/2)'},
                         {'key':'3','text':'allpositive','condition':'t>0'}]}
        self.assertEqual(circle_intersections(spec),'two')
        spec['options'][1]['condition']='t>=1/2'
        self.assertEqual(circle_intersections(spec),'two')

    def test_angle_implication_requires_valid_counterexample(self):
        spec={'query':'not_equilateral','options':[
          {'key':'1','text':'one60','angle_values':{'A':60},'counterexample':[60,40,80]},
          {'key':'2','text':'two60','angle_values':{'A':60,'B':60}}]}
        self.assertEqual(angle_implication(spec),'one60')
        spec['options'][0]['counterexample']=[60,60,60]
        with self.assertRaises(ValueError):angle_implication(spec)

    def test_pythagoras_does_not_accept_triangle_inequality_as_reason(self):
        spec={'squared_sides':['9','16','25'],'query':'explanation','options':[
          {'key':'1','text':'pythagoras','conclusion':'right','argument':'pythagoras','hypotenuse':2},
          {'key':'2','text':'triangleineq','conclusion':'right','argument':'triangle_inequality','hypotenuse':2}]}
        self.assertEqual(triangle_square_model(spec),'pythagoras')
        spec['squared_sides']=['9','16','36']
        with self.assertRaises(ValueError):triangle_square_model(spec)

    def test_original_polynomial_constraint_is_eliminated_exactly(self):
        spec={'positive':['a','b','c'],'squared_sides':['a**2','b**2','c**2'],
          'constraint':'(a+b)**2-c**2-2*a*b','variable_order':['c','a','b'],
          'options':options('classification',['acute','right','obtuse'])}
        self.assertEqual(triangle_square_model(spec),'right')

    def test_degenerate_and_impossible_side_sets_rejected(self):
        for values in (['1','4','9'],['1','4','16']):
            with self.assertRaises(ValueError):triangle_square_model({'squared_sides':values,
              'options':options('classification',['acute','right','obtuse'])})

    def test_positive_leg_parameters_give_exact_right_angle(self):
        spec={'positive':['a','b'],'squared_sides':['a','b','a+b'],
              'options':options('classification',['acute','right','obtuse'])}
        self.assertEqual(triangle_square_model(spec),'right')

    def test_polygon_recurrence_not_selected_letter(self):
        spec={'convex':True,'query':'fan_triangles','options':options('expression',['n-3','n-2','n-1'])}
        self.assertEqual(polygon_model(spec),'n-2')
        spec['query']='exterior_sum';spec['options']=options('expression',['180','360','180*n'])
        self.assertEqual(polygon_model(spec),'360')
        spec['convex']=False
        with self.assertRaises(ValueError):polygon_model(spec)

    def test_reflected_path_proves_attainment_before_returning_distance(self):
        self.assertEqual(reflected_path({'query':'minimum','reflected_distance':'19/2'}),Fraction(19,2))
        spec={'query':'point','options':options('point_x',['(u+v)/2','(b*u+a*v)/(a+b)'])}
        self.assertEqual(reflected_path(spec),'(b*u+a*v)/(a+b)')


class QuadrilateralTests(unittest.TestCase):
    para=[[0,0],[3,0],[4,2],[1,2]]
    rect=[[0,0],[4,0],[4,2],[0,2]]
    trap=[[0,0],[6,0],[5,2],[1,2]]

    def test_counterexample_is_measured_not_stored_truth(self):
        facts=coordinate_facts(self.trap)
        self.assertIn('diagonals_equal',facts)
        self.assertNotIn('parallelogram',facts)
        self.assertIn('exclusive_isosceles_trapezoid',facts)
        self.assertNotIn('exclusive_isosceles_trapezoid',coordinate_facts(self.rect))

    def test_missing_or_invalid_counterexample_rejected(self):
        spec={'given':['parallelogram'],'query':'not_implies','options':[
          {'key':'a','text':'equaldiags','target':'diagonals_equal','counterexample':self.para},
          {'key':'b','text':'bisected','target':'diagonals_bisect'}]}
        self.assertEqual(quadrilateral(spec),'equaldiags')
        spec['options'][0]['counterexample']=self.rect
        with self.assertRaises(ValueError):quadrilateral(spec)
        del spec['options'][0]['counterexample']
        with self.assertRaises(ValueError):quadrilateral(spec)

    def test_new_assumption_changes_rectangle_to_square(self):
        spec={'given':['parallelogram','diagonals_equal'],'options':[
          {'key':'a','text':'rectangle','target':'rectangle'},
          {'key':'b','text':'square','target':'square','counterexample':self.rect}]}
        self.assertEqual(quadrilateral(spec),'rectangle')
        spec['given'].append('equal_ab_bc')
        # Both candidates now true: no artificial priority suppresses duplicate.
        with self.assertRaises(ValueError):quadrilateral(spec)

    def test_nonconvex_counterexample_rejected(self):
        with self.assertRaises(ValueError):coordinate_facts([[0,0],[2,2],[0,2],[2,0]])

    def test_diagonal_transport_requires_proof(self):
        self.assertEqual(diagonal_transport({'given':['rectangle'],'known_diagonal':8}),8)
        with self.assertRaises(ValueError):diagonal_transport({'given':['parallelogram'],'known_diagonal':8})
        with self.assertRaises(ValueError):diagonal_transport({'given':['rectangle'],'known_diagonal':-1})


class FunctionModelTests(unittest.TestCase):
    def test_count_is_derived_from_unfixed_free_symbols(self):
        spec={'symbols':['s','v','t'],'relation':'s-v*t','query':'count','fixed':{'v':5}}
        self.assertEqual(formula_quantities(spec),2)
        spec['fixed']={}
        self.assertEqual(formula_quantities(spec),3)
        spec['fixed']={'v':5,'t':3}
        self.assertEqual(formula_quantities(spec),1)

    def test_constant_must_actually_occur_in_source_formula(self):
        spec={'symbols':['s','t'],'relation':'s-60*t','query':'constants',
          'options':[{'key':'a','text':'source','quantities':['60']},
                     {'key':'b','text':'unrelated','quantities':['61']}]}
        self.assertEqual(formula_quantities(spec),'source')

    def test_nonfunction_requires_exact_multiple_real_roots(self):
        self.assertFalse(relation_is_function('y**2-x','x','y',4))
        self.assertFalse(relation_is_function('Abs(y)-x','x','y',1))
        # At x=0 the two branches coincide: this is not a counterexample.
        with self.assertRaises(ValueError):relation_is_function('y**2-x','x','y',0)

    def test_natural_domain_excludes_pole_without_disqualifying_function(self):
        self.assertTrue(relation_is_function('y-1/x','x','y'))
        self.assertTrue(relation_is_function('y-Abs(x)','x','y'))
        self.assertFalse(relation_is_function('x**2+y**2-4','x','y',0))

    def test_table_duplicate_pairs_are_not_conflicting_values(self):
        spec={'query':'table','pairs':[[1,2],[1,2]],'options':[
          {'key':'a','text':'nonunique','argument':'collision','input':1},
          {'key':'b','text':'unique','argument':'unique_output'}]}
        self.assertEqual(function_relation(spec),'unique')
        spec['pairs'][1]=[1,3]
        self.assertEqual(function_relation(spec),'nonunique')


if __name__=='__main__':unittest.main()
