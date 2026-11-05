"""Canonical description versus geometric sufficiency; exact rotation domains."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
import sympy as S
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import models_applications_29 as M


def rotation_spec(center='o',direction='d',angle='a'):
    c={'op':'parameter','name':center,'sort':'point2'}
    d={'op':'parameter','name':direction,'sort':'orientation'}
    a={'op':'parameter','name':angle,'sort':'unsigned_turn'}
    p={'op':'query_point'}
    radius={'op':'squared_distance','left':p,'right':c}
    correspondence={'op':'point_pair','first':p,'second':{'op':'apply_rotation','point':p}}
    axis={'op':'external_axis'}
    return {'kind':'app29_rotation_parameters','angle_encoding':'separate_orientation_and_unsigned_turn',
        'angle_unit':'degree','construction':{'op':'rotate_about_center','center':c,
            'signed_turn':{'op':'multiply','factors':[d,a]}},
        'options':[{'key':'a','text':'center radius time','fields':[c,radius,{'op':'external_time'}]},
                   {'key':'b','text':'center direction angle','fields':[c,d,a]},
                   {'key':'c','text':'axis direction angle','fields':[axis,d,a]},
                   {'key':'d','text':'center correspondence axis','fields':[c,correspondence,axis]}]}


class RotationDescriptionTests(unittest.TestCase):
    def test_general_geometry_and_every_endpoint_chart_are_proved(self):
        charts=M.rotation_certificate()
        self.assertEqual(len(charts),10)
        self.assertEqual({kind for kind,_,_ in charts},{'minor','reflex','identity','half_turn','full_turn'})
        for kind,_,unique in charts:self.assertEqual(unique,kind not in ('identity','full_turn'))
        self.assertEqual(M.rotation_parameters(rotation_spec()),'center direction angle')

    def test_names_candidate_order_and_field_order_are_not_answers(self):
        s=rotation_spec('C','sense','amount');s['options'].reverse()
        for i,o in enumerate(s['options']):o['key']=str(i);o['text']='candidate'+str(i);o['fields'].reverse()
        self.assertEqual(M.rotation_parameters(s),'candidate2')
        s['construction']['signed_turn']['factors'].reverse()
        self.assertEqual(M.rotation_parameters(s),'candidate2')
        s['angle_unit']='radian';self.assertEqual(M.rotation_parameters(s),'candidate2')

    def test_parameter_names_cannot_capture_query_or_internal_geometry_symbols(self):
        for names in (('query','d','query_x'),('param','external_time','angle'),('axis','m','axis_b')):
            s=rotation_spec(*names)
            description=M.Description(s['construction'],s['angle_encoding'],s['angle_unit'])
            self.assertTrue(set(description.center).isdisjoint(set(description.query)))
            self.assertTrue(set(description.center).isdisjoint({v for v in description.values.values() if isinstance(v,S.Symbol)}))
            self.assertEqual(M.rotation_parameters(s),'center direction angle')

    def test_radius_depends_on_query_point_and_time_is_external_to_the_mapping(self):
        s=rotation_spec();d=M.Description(s['construction'],s['angle_encoding'],s['angle_unit'])
        radius=d.field(s['options'][0]['fields'][1]);time=d.field(s['options'][0]['fields'][2])
        self.assertEqual(radius.sort,'scalar');self.assertEqual(radius.dependencies,frozenset({'query','o'}))
        self.assertIsNone(radius.primitive);self.assertEqual(time.dependencies,frozenset({'external_time'}))
        self.assertEqual(M.rotate_point([0,0],1,90,[1,0]),S.Matrix([0,1]))
        self.assertEqual(M.rotate_point([0,0],1,90,[2,0]),S.Matrix([0,2]))

    def test_corresponding_points_can_determine_a_turn_but_are_not_primitive_fields(self):
        s=rotation_spec();d=M.Description(s['construction'],s['angle_encoding'],s['angle_unit'])
        pair=d.field(s['options'][3]['fields'][1]);self.assertEqual(pair.sort,'point_pair');self.assertIsNone(pair.primitive)
        image=M.rotate_point([0,0],1,90,[1,0])
        # With center known and a noncentral unit point, its image gives both
        # cos andsin. Rejecting D is about the representation, not impossibility.
        self.assertEqual((image[0],image[1]),(0,1))
        self.assertEqual(M.rotation_parameters(s),'center direction angle')

    def test_signed_angle_is_a_real_two_field_alternative_convention(self):
        s=rotation_spec();c=s['construction']['center'];signed={'op':'parameter','name':'z','sort':'signed_turn'}
        s.update(angle_encoding='signed_turn_includes_orientation')
        s['construction']['signed_turn']=signed
        s['options']=[{'key':'good','text':'center and signed angle','fields':[c,signed]},
                      {'key':'other','text':'center and axis','fields':[c,{'op':'external_axis'}]}]
        self.assertEqual(M.rotation_parameters(s),'center and signed angle')
        s['options'][0]['fields'].append({'op':'external_time'})
        with self.assertRaises(ValueError):M.rotation_parameters(s)

    def test_endpoint_redundancy_does_not_remove_descriptive_fields(self):
        p=[7,-2]
        for angle in (0,360,720):
            for center in ([0,0],[5,9]):
                self.assertEqual(M.rotate_point(center,1,angle,p),S.Matrix(p))
                self.assertEqual(M.rotate_point(center,-1,angle,p),S.Matrix(p))
        c=[2,3]
        self.assertEqual(M.rotate_point(c,1,180,p),M.rotate_point(c,-1,180,p))
        self.assertEqual(M.rotate_point(c,1,180,p),2*S.Matrix(c)-S.Matrix(p))
        self.assertEqual(M.rotation_parameters(rotation_spec()),'center direction angle')

    def test_reflex_and_multiple_turns_have_full_forward_constructions(self):
        self.assertEqual(M.rotate_point([1,2],1,270,[4,2]),S.Matrix([1,-1]))
        self.assertEqual(M.rotate_point([1,2],-1,270,[4,2]),S.Matrix([1,5]))
        self.assertEqual(M.rotate_point([1,2],1,450,[4,2]),M.rotate_point([1,2],1,90,[4,2]))
        self.assertEqual(M.rotate_point([1,2],1,270,[4,2]),M.rotate_point([1,2],-1,90,[4,2]))

    def test_radian_forward_map_is_exact_and_preserves_radius(self):
        c=S.Matrix([1,2]);p=S.Matrix([3,5]);out=M.rotate_point([1,2],-1,'1/3',[3,5],'radian')
        self.assertEqual(S.trigsimp((out-c).dot(out-c)-(p-c).dot(p-c)),0)

    def test_missing_unsigned_convention_and_unknown_units_are_not_assumed(self):
        for key,value in [('angle_encoding','unspecified'),('angle_unit','turns')]:
            s=rotation_spec();s[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):M.rotation_parameters(s)
        s=rotation_spec();del s['angle_encoding']
        with self.assertRaises(ValueError):M.rotation_parameters(s)

    def test_direction_and_magnitude_types_and_distinct_names_are_checked(self):
        s=rotation_spec();s['construction']['signed_turn']['factors'][0]['sort']='signed_turn'
        with self.assertRaises(ValueError):M.rotation_parameters(s)
        s=rotation_spec();s['construction']['signed_turn']['factors'][1]['name']='o'
        with self.assertRaises(ValueError):M.rotation_parameters(s)
        s=rotation_spec();s['construction']['center']['sort']='unsigned_turn'
        with self.assertRaises(ValueError):M.rotation_parameters(s)

    def test_unknown_fields_are_rejected_even_for_already_nonmatching_candidate(self):
        for index in range(4):
            s=rotation_spec();s['options'][index]['condition']='unverified'
            with self.subTest(index=index),self.assertRaises(ValueError):M.rotation_parameters(s)
        s=rotation_spec();s['options'][0]['fields'][1]['condition']='unverified'
        with self.assertRaises(ValueError):M.rotation_parameters(s)
        s=rotation_spec();s['options'][0]['fields'].append({'op':'unknown'})
        with self.assertRaises(ValueError):M.rotation_parameters(s)

    def test_known_composite_wrong_type_does_not_substitute_for_a_point(self):
        s=rotation_spec();s['options'][0]['fields'][1]['left']={'op':'external_axis'}
        with self.assertRaises(ValueError):M.rotation_parameters(s)
        s=rotation_spec();s['options'][3]['fields'][1]['second']['point']={'op':'external_time'}
        with self.assertRaises(ValueError):M.rotation_parameters(s)

    def test_missing_duplicate_fields_or_duplicate_complete_candidates_fail_closed(self):
        s=rotation_spec();s['options'][1]['fields'].pop()
        with self.assertRaises(ValueError):M.rotation_parameters(s)
        s=rotation_spec();s['options'][1]['fields'][2]=deepcopy(s['options'][1]['fields'][0])
        with self.assertRaises(ValueError):M.rotation_parameters(s)
        s=rotation_spec();extra=deepcopy(s['options'][1]);extra['key']='extra';s['options'].append(extra)
        with self.assertRaises(ValueError):M.rotation_parameters(s)

    def test_executable_instances_keep_unsigned_and_raw_numeric_domains(self):
        self.assertEqual(M.rotate_point([0,0],1,'９０',[1,0]),S.Matrix([0,1]))
        for angle in (-90,'9⁰','⑨⓪','90。0','9 0','90/0',True,90.0):
            with self.subTest(angle=angle),self.assertRaises(ValueError):M.rotate_point([0,0],1,angle,[1,0])
        for direction in (0,2,True,'1'):
            with self.subTest(direction=direction),self.assertRaises(ValueError):M.rotate_point([0,0],direction,90,[1,0])
        with self.assertRaises(ValueError):M.rotate_point([0,0],1,90,[1])

    def test_no_illegal_parameter_tokens_or_unbounded_field_trees(self):
        for name in ('0','⓪','query x',True,'a'*40):
            s=rotation_spec();s['construction']['center']['name']=name
            with self.subTest(name=name),self.assertRaises(ValueError):M.rotation_parameters(s)
        s=rotation_spec();node={'op':'query_point'}
        for _ in range(55):node={'op':'apply_rotation','point':node}
        s['options'][0]['fields'].append(node)
        with self.assertRaises(ValueError):M.rotation_parameters(s)


if __name__=='__main__':unittest.main()
