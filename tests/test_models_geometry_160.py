"""Adversarial and metamorphic checks for the new independent geometry proofs."""
import copy
import sys
from pathlib import Path
import unittest
import sympy as S
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from models_geometry_160 import (parse,localization_rank,inequality_objects,
 symbolic_claims,ssa_claims,hl_claims,distance_minimum,angle_bisector,
 symmetry_families,equidistant_locus,reflection_constructions,isosceles_angle_cases,
 hypotenuse_order,quadrilateral_quantifiers,weighted_influence,
 congruence_invariants,reflection_implications,regular_polygon_claims)


def options(rows):return [dict(key=str(i),text=str(i),**row) for i,row in enumerate(rows)]


class ParserTests(unittest.TestCase):
    def test_no_execution_or_undeclared_names(self):
        for source in ("__import__('os').system('true')",'x.__class__','sum([1,2])','True','x**100'):
            with self.assertRaises((ValueError,SyntaxError)):parse(source,{'x':S.Symbol('x',real=True)})
        with self.assertRaises(ValueError):parse('y+1',{'x':S.Symbol('x',real=True)})

    def test_bounded_relation_ast_and_domain(self):
        x=S.Symbol('x',real=True)
        self.assertEqual(parse('And(x>2,x<4)',{'x':x}),S.And(x>2,x<4))
        with self.assertRaises(ValueError):parse('1/x',{'x':x})
        with self.assertRaises(ValueError):parse('Eq(x,1,2)',{'x':x})


class Geometry160Tests(unittest.TestCase):
    def test_empty_solution_set_has_zero_elements(self):
        spec={'variable':'x','relation':'x**2<0',
              'options':options([{'claim':'cardinality','count':0}])}
        self.assertEqual(inequality_objects(spec),'0')

    def test_not_an_identity_does_not_mean_nonzero_at_every_angle(self):
        spec={'full_angle_domain':[0,180],'point_region':'interior','radius_domain':'positive',
              'options':options([{'claim':'angle_relation','expression':'p-1','op':'!='}])}
        with self.assertRaises(ValueError):angle_bisector(spec)  # p=t=1 radian is legal
        spec['options'][0]['expression']='p+1'
        self.assertEqual(angle_bisector(spec),'0')

    def test_self_intersecting_star_is_not_a_convex_polygon_counterexample(self):
        points=[[str(S.cos(4*S.pi*k/5)),str(S.sin(4*S.pi*k/5))] for k in range(5)]
        spec={'options':options([
            {'claim':'regular_from_properties','given':['equal_sides'],'counterexample':points},
            {'claim':'regular_from_properties','given':['equal_sides','equal_angles']}])}
        with self.assertRaisesRegex(ValueError,'global convexity'):regular_polygon_claims(spec)

    def test_solution_set_not_point_and_strict_endpoint(self):
        spec={'variable':'x','relation':'x>2','options':options([
         {'claim':'membership','point':2},{'claim':'set_equality','relation':'x>2'},
         {'claim':'set_equality','points':[3]}])}
        self.assertEqual(inequality_objects(spec),'1')
        spec['relation']='x>=2'
        self.assertEqual(inequality_objects(spec),'0')
        spec['options'].append({'key':'extra','text':'duplicate','claim':'membership','point':4})
        with self.assertRaises(ValueError):inequality_objects(spec)

    def test_localization_needs_independence_not_generic_nonzero_polynomial(self):
        spec={'dimension':2,'variables':['u'],'nonzero':['v'],'normals':[[1,0],['u','v']]}
        self.assertEqual(localization_rank(spec),2)
        spec['nonzero']=[];spec['variables']=['u','v']
        with self.assertRaises(ValueError):localization_rank(spec)
        with self.assertRaises(ValueError):localization_rank({'dimension':2,'normals':[[1,0],[2,0]]})
        self.assertEqual(localization_rank({'dimension':3,'normals':[[1,0,0],[0,1,0],[0,0,1]]}),3)

    def test_symbolic_identity_not_one_parameter_sample(self):
        spec={'positive':['v'],'options':options([
         {'clauses':[{'op':'identity','expression':'v-v'}]},
         {'clauses':[{'op':'identity','expression':'v-1'}]}])}
        self.assertEqual(symbolic_claims(spec),'0')
        spec['options'][1]['clauses'][0]['expression']='v-v'
        with self.assertRaises(ValueError):symbolic_claims(spec)

    def test_unknown_clause_cannot_pass(self):
        spec={'variables':['v'],'options':options([{'clauses':[{'op':'positive','expression':'v'}]}])}
        with self.assertRaises(ValueError):symbolic_claims(spec)
        spec={'positive':['v'],'options':options([{'clauses':[{'op':'identity','expression':'v-v'}],'opaque_conjunct':'unknown'}])}
        with self.assertRaises(ValueError):symbolic_claims(spec)

    def test_ssa_counterexample_requires_two_valid_positive_roots(self):
        spec={'counterexample':{'adjacent':4,'opposite':3,'angle_degrees':30},'congruent_example':[3,4,5],
         'options':options([{'quantifier':'all'},{'quantifier':'not_all_and_sufficient','additional':'included_angle','criterion':'SAS'},{'quantifier':'none'}])}
        self.assertEqual(ssa_claims(spec),'1')
        spec['counterexample']['opposite']=10
        with self.assertRaises(ValueError):ssa_claims(spec)

    def test_hl_false_reasons_must_have_valid_counterexamples(self):
        spec={'options':options([{'proof':'right_hypotenuse_leg'},
         {'proof':'hypotenuse_shortest','counterexample_sides':[3,4,5]}])}
        self.assertEqual(hl_claims(spec),'0')
        spec['options'][1]['counterexample_sides']=[3,4,6]
        with self.assertRaises(ValueError):hl_claims(spec)

    def test_projection_is_attained_minimum(self):
        spec={'variables':['p','q'],'positive':['h'],'options':options([
         {'squared_distance':'h**2'},{'squared_distance':'(p-q)**2+h**2'}])}
        self.assertEqual(distance_minimum(spec),'0')
        spec['options'][1]['squared_distance']='(p-p)**2+h**2'
        with self.assertRaises(ValueError):distance_minimum(spec)

    def test_internal_angle_assumptions_are_mandatory(self):
        spec={'full_angle_domain':[0,180],'point_region':'interior','radius_domain':'positive','options':options([
         {'claim':'angle_relation','expression':'p-t','op':'='},
         {'claim':'angle_relation','expression':'p-t','op':'!='}])}
        self.assertEqual(angle_bisector(spec),'0')
        spec['point_region']='exterior'
        with self.assertRaises(ValueError):angle_bisector(spec)
        spec['point_region']='interior';spec['full_angle_domain']=[0,360]
        with self.assertRaises(ValueError):angle_bisector(spec)

    def test_family_proof_and_valid_asymmetric_example(self):
        spec={'options':options([{'family':'isosceles_triangle'},
          {'family':'right_triangle','counterexample':[[0,0],[3,0],[0,2]]}])}
        self.assertEqual(symmetry_families(spec),'0')
        spec['options'][1]['counterexample']=[[0,0],[3,0],[0,3]]
        with self.assertRaises(ValueError):symmetry_families(spec)

    def test_locus_counterexample_must_be_equidistant(self):
        spec={'positive':['a'],'variables':['x','y'],'options':options([
         {'condition':'Eq(x,0)'},
         {'condition':'Eq(y,0)','counterexample':{'a':1,'x':0,'y':1}}])}
        self.assertEqual(equidistant_locus(spec),'0')
        spec['options'][1]['counterexample']['x']=1
        with self.assertRaises(ValueError):equidistant_locus(spec)

    def test_arbitrary_axis_point_does_not_construct_reflection(self):
        spec={'variables':['p','x','y'],'positive':['v','r'],'options':options([
         {'equations':['x-2*p','y+v']},{'equations':['x','y+v']}])}
        self.assertEqual(reflection_constructions(spec),'1')
        spec['options'][0]['equations']=['x','y+v']
        with self.assertRaises(ValueError):reflection_constructions(spec)

    def test_isosceles_cases_change_with_angle(self):
        spec={'angle':60,'options':options([
         {'placements':['A','B','C'],'quantifier':'all','conclusion':'equilateral'},
         {'placements':['A','B','C'],'quantifier':'all','conclusion':'not_equilateral'}])}
        self.assertEqual(isosceles_angle_cases(spec),'0')
        spec['angle']=40
        self.assertEqual(isosceles_angle_cases(spec),'1')

    def test_longest_is_derived_from_positive_squared_gaps(self):
        self.assertEqual(hypotenuse_order({'options':options([{'selection':s} for s in ('least','arbitrary','greatest')])}),'2')
        with self.assertRaises(ValueError):hypotenuse_order({'options':options([{'selection':'unknown'}])})

    def test_same_group_parallel_and_equal_required(self):
        spec={'given':['parallel_ab_cd','equal_ab_cd'],'goal':'parallelogram','options':options([
         {'quantifier':'all'},{'quantifier':'not_all'}])}
        self.assertEqual(quadrilateral_quantifiers(spec),'0')
        spec['given']=['parallel_ab_cd','equal_ad_bc']
        with self.assertRaises(ValueError):quadrilateral_quantifiers(spec)

    def test_weight_influence_is_not_claim_that_mean_always_increases(self):
        spec={'weight_domain':'positive','other_weight':'positive_fixed','options':options([
         {'claim':'data_sensitivity_increases'},
         {'claim':'mean_increases','counterexample':{'before':1,'after':2,'data':1,'other_data':2,'other_weight':1}}])}
        self.assertEqual(weighted_influence(spec),'0')
        spec['options'][1]['counterexample']['data']=3
        with self.assertRaises(ValueError):weighted_influence(spec)
        spec['other_weight']='zero'
        with self.assertRaises(ValueError):weighted_influence(spec)

    def test_perimeter_counterexample_cannot_be_congruent(self):
        tri=[[0,0],[4,0],[0,3]]
        spec={'options':options([{'premise':'rigid_overlap'},
          {'premise':'perimeter','counterexample_triangles':[tri,[[0,0],[2,0],[1,'sqrt(24)']]]}])}
        self.assertEqual(congruence_invariants(spec),'0')
        spec['options'][1]['counterexample_triangles']=[tri,tri]
        with self.assertRaises(ValueError):congruence_invariants(spec)

    def test_congruent_symmetric_triangle_is_not_valid_no_reflection_witness(self):
        spec={'options':options([{'conclusion':'isometry'},
         {'conclusion':'congruence_suffices_for_reflection','counterexample_triangles':[
           [[0,0],[3,0],[1,2]],[[5,0],[8,0],[6,2]]]}])}
        self.assertEqual(reflection_implications(spec),'0')
        spec['options'][1]['counterexample_triangles']=[[[0,0],[2,0],[1,1]],[[0,0],[2,0],[1,1]]]
        with self.assertRaises(ValueError):reflection_implications(spec)

    def test_regular_polygon_counterexample_and_definition(self):
        spec={'options':options([
         {'claim':'regular_from_properties','given':['equal_angles'],'counterexample':[[0,0],[4,0],[4,2],[0,2]]},
         {'claim':'regular_from_properties','given':['equal_sides','equal_angles']},
         {'claim':'vertex_diagonal_count','expression':'n-2'}])}
        self.assertEqual(regular_polygon_claims(spec),'1')
        spec['options'][0]['counterexample']=[[0,0],[2,0],[2,2],[0,2]]
        with self.assertRaises(ValueError):regular_polygon_claims(spec)


if __name__=='__main__':unittest.main()
