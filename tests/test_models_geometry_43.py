"""Typed-signature and full-domain projection regressions for43 audit."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
import sympy as S
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import models_geometry_43 as M


def options(rows):return [dict(key=str(i),text=str(i),**r) for i,r in enumerate(rows)]


def angle_spec(a='a',o='o',b='b',p='p'):
    member={'op':'member','point':p,'set':{'op':'internal_angle_bisector','angle':[a,o,b]}}
    angles={'op':'equal','left':{'op':'angle','points':[a,o,p]},'right':{'op':'angle','points':[p,o,b]}}
    distances={'op':'equal','left':{'op':'distance_to_line','point':p,'line':[o,a]},'right':{'op':'distance_to_line','point':p,'line':[o,b]}}
    imp=lambda x,y:{'op':'implies','left':x,'right':y}
    return {'context':{'angle':[a,o,b],'point':p,'full_angle_domain':{'kind':'open_interval','lower':0,'upper':180},
      'point_region':'strict_interior','distance':'perpendicular_to_supporting_lines'},
      'theorem':imp(distances,member),'options':options([
       {'signature':imp(member,distances)},{'signature':imp(distances,member)},
       {'signature':{'op':'iff','left':member,'right':angles}}])}


def projection_spec():
    p={'op':'linear_part'}
    base=[{'op':'matrix_equal','left':{'op':'multiply','left':p,'right':p},'right':p},
          {'op':'rank','value':2},{'op':'parallel_fibres'}]
    symmetric={'op':'matrix_equal','left':{'op':'transpose','argument':p},'right':p}
    nonsymmetric={'op':'matrix_not_equal','left':{'op':'transpose','argument':p},'right':p}
    return {'normal_domain':'all_nonzero_real_normals','direction':'nonzero_normal_multiple',
      'plane_offset_domain':'all_real_offsets','options':options([
       {'requirements':base},{'requirements':[{'op':'finite_fibre_concurrency'}]},
       {'requirements':base+[symmetric]},{'requirements':base+[nonsymmetric]}])}


class CriterionSignatureTests(unittest.TestCase):
    def test_criterion_signature_not_the_truth_of_all_three_theorems(self):
        s=angle_spec();self.assertEqual(M.angle_criterion_signature(s),'1')
        s['theorem']=deepcopy(s['options'][0]['signature'])
        self.assertEqual(M.angle_criterion_signature(s),'0')
        s['theorem']=deepcopy(s['options'][2]['signature'])
        self.assertEqual(M.angle_criterion_signature(s),'2')

    def test_all_geometric_identifiers_can_be_renamed(self):
        self.assertEqual(M.angle_criterion_signature(angle_spec('x','z','y','q')),'1')
        s=angle_spec();s['options'].reverse()
        self.assertEqual(M.angle_criterion_signature(s),'1')

    def test_supporting_lines_and_ordinary_angles_are_unoriented(self):
        s=angle_spec();q=s['options'][1]['signature']['left']
        q['left']['line'].reverse();q['right']['line'].reverse()
        q['left'],q['right']=q['right'],q['left']
        self.assertEqual(M.angle_criterion_signature(s),'1')
        s=angle_spec();s['options'][2]['signature']['right']['left']['points'].reverse()
        self.assertEqual(M.angle_criterion_signature(s),'1')

    def test_open_angle_interior_and_distance_domain_are_required(self):
        for field,value in [('full_angle_domain',[0,180]),
          ('full_angle_domain',{'kind':'closed_interval','lower':0,'upper':180}),
          ('full_angle_domain',{'kind':'open_interval','lower':False,'upper':180}),
          ('full_angle_domain',{'kind':'open_interval','lower':0,'upper':360}),
          ('point_region','boundary'),('point_region','exterior'),('distance','distance_to_rays')]:
            s=angle_spec();s['context'][field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):M.angle_criterion_signature(s)

    def test_duplicate_or_unproved_predicate_is_not_forced_to_one_answer(self):
        s=angle_spec();s['options'][0]['signature']=deepcopy(s['options'][1]['signature'])
        with self.assertRaises(ValueError):M.angle_criterion_signature(s)
        s=angle_spec();s['options'][0]['signature']['op']='unproved'
        with self.assertRaises(ValueError):M.angle_criterion_signature(s)
        s=angle_spec();s['theorem']={'op':'iff','left':s['theorem']['left'],'right':s['theorem']['right']}
        with self.assertRaises(ValueError):M.angle_criterion_signature(s) # equivalent theorem is not the canonical constructor definition

    def test_malformed_or_degenerate_geometric_objects_are_rejected(self):
        for bad in ('__import__',True,'aa'):
            with self.subTest(bad=bad),self.assertRaises(ValueError):M.identifier(bad)
        s=angle_spec();s['context']['point']='o'
        with self.assertRaises(ValueError):M.angle_criterion_signature(s)


class ProjectionTypeTests(unittest.TestCase):
    def test_actual_general_source_selects_strict_subtype(self):
        s=projection_spec();self.assertEqual(M.most_specific_projection(s),'2')
        s['options'].reverse();self.assertEqual(M.most_specific_projection(s),'2')

    def test_self_adjoint_wedge_characterization_on_all_three_normal_charts(self):
        r=S.Symbol('r',real=True,nonzero=True);u,v=S.symbols('u v',real=True)
        for normal in (S.Matrix([r,u,v]),S.Matrix([0,r,u]),S.Matrix([0,0,r])):
            self.assertTrue(M._self_adjoint_characterization(normal))
        with self.assertRaises(ValueError):M._self_adjoint_characterization(S.Matrix([0,0,0]))

    def test_arbitrary_plane_offset_is_not_silently_zero(self):
        n=S.Matrix([1,2,3]);d=-2*n;t=S.Matrix([2,-1,0]);h=S.Integer(7)
        case=M._case(n,d,h,t);p=case['matrix'];shift=d*h/(n.dot(d))
        self.assertEqual(p*p,p);self.assertEqual(p.T,p)
        self.assertEqual(n.dot(shift),h);self.assertEqual(p*shift,S.zeros(3,1))
        self.assertTrue(M._requirement({'op':'parallel_fibres'},case))
        self.assertFalse(M._requirement({'op':'finite_fibre_concurrency'},case))

    def test_legal_oblique_world_separates_parallel_and_orthogonal_classes(self):
        case=M._case(S.Matrix([0,0,1]),S.Matrix([1,0,1]),S.Integer(0),S.Matrix([1,0,0]))
        self.assertEqual(case['matrix'],S.Matrix([[1,0,-1],[0,1,0],[0,0,0]]))
        p={'op':'linear_part'};relation={'op':'matrix_equal','left':{'op':'transpose','argument':p},'right':p}
        self.assertFalse(M._requirement(relation,case))
        relation['op']='matrix_not_equal';self.assertTrue(M._requirement(relation,case))
        self.assertTrue(M._requirement({'op':'parallel_fibres'},case))

    def test_missing_specialized_type_does_not_fall_back_to_broad_true_type(self):
        s=projection_spec();s['options'].pop(2)
        with self.assertRaises(ValueError):M.most_specific_projection(s)
        s=projection_spec();s['options']=[s['options'][0]]
        with self.assertRaises(ValueError):M.most_specific_projection(s)

    def test_duplicate_or_logically_equivalent_specialized_names_are_ambiguous(self):
        s=projection_spec();extra=deepcopy(s['options'][2]);extra.update(key='extra',text='duplicate');s['options'].append(extra)
        with self.assertRaises(ValueError):M.most_specific_projection(s)
        s=projection_spec();extra=deepcopy(s['options'][2]);extra.update(key='extra',text='same type plus tautology')
        extra['requirements'].append({'op':'matrix_equal','left':{'op':'linear_part'},'right':{'op':'linear_part'}})
        s['options'].append(extra)
        with self.assertRaises(ValueError):M.most_specific_projection(s)

    def test_unknown_predicates_are_checked_even_for_an_already_false_type(self):
        s=projection_spec();s['options'][1]['requirements'].append({'op':'unproved'})
        with self.assertRaises(ValueError):M.most_specific_projection(s)
        s=projection_spec();s['options'][2]['requirements'][1]['value']=True
        with self.assertRaises(ValueError):M.most_specific_projection(s)

    def test_matrix_nonidentity_does_not_mean_everywhere_nonzero(self):
        x=S.Symbol('x',real=True)
        with self.assertRaises(ValueError):M._matrix_equal(S.Matrix([[1,x],[0,1]]),S.eye(2))
        y=S.Symbol('y',real=True,nonzero=True)
        self.assertFalse(M._matrix_equal(S.Matrix([[1,y],[0,1]]),S.eye(2)))

    def test_undefined_normal_direction_or_plane_scope_fails_closed(self):
        for key,value in [('normal_domain','possibly_zero'),('direction','oblique'),('plane_offset_domain','unspecified')]:
            s=projection_spec();s[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):M.most_specific_projection(s)
        n=S.Matrix([0,0,1]);t=S.Matrix([1,0,0])
        with self.assertRaises(ValueError):M._case(n,S.Matrix([0,0,0]),0,t)
        with self.assertRaises(ValueError):M._case(n,S.Matrix([1,0,0]),0,t)
        with self.assertRaises(ValueError):M._case(S.zeros(3,1),S.Matrix([1,0,0]),0,t)


if __name__=='__main__':unittest.main()
