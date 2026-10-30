"""Definition, adversarial and metamorphic regressions for the105 audit."""
import copy
from pathlib import Path
import sys
import unittest
import sympy as S
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import models_geometry_105 as M


def design(pop=500,n=50,quantity='height'):
    return {'entity':'student','population_count':pop,'selection':{'method':'without_replacement','count':n},
     'measurement':{'kind':'scalar','quantity':quantity,'records_per_subject':1,'missing_subjects':0}}
def subject(scope):return {'op':'subjects','scope':scope}
def obs(scope,quantity='height'):return {'op':'observe','subjects':subject(scope),'quantity':quantity}
def role(name):return {'op':'role','name':name}
def options(rows):return [dict(key=str(i),text=str(i),**r) for i,r in enumerate(rows)]


class ObservationTests(unittest.TestCase):
    def test_capacity_comes_from_typed_observation_index_not_distinct_values(self):
        d=design(4,3);d['records']=[{'subject':1,'value':150},{'subject':2,'value':150},{'subject':4,'value':150}]
        self.assertEqual(M.observation_objects({'design':d,'query':'capacity'}),3)
        d['selection']['count']=2;d['records']=d['records'][:2]
        self.assertEqual(M.observation_objects({'design':d,'query':'capacity'}),2)
        d['population_count']=100
        self.assertEqual(M.observation_objects({'design':d,'query':'capacity'}),2)

    def test_repeated_missing_or_multivariate_measurements_fail_closed(self):
        for changes in ({'records_per_subject':2},{'missing_subjects':1},{'kind':'vector'},{'quantity':''}):
            d=design(4,3);d['measurement'].update(changes)
            with self.subTest(changes=changes),self.assertRaises(ValueError):M.Survey({'design':d})
        d=design(4,3);d['records']=[{'subject':1,'value':150},{'subject':2,'value':150}]
        with self.assertRaises(ValueError):M.Survey({'design':d})

    def test_injectivity_and_population_membership_are_checked(self):
        for ids in ([1,1],[1,5]):
            d=design(4,2);d['records']=[{'subject':i,'value':150} for i in ids]
            with self.subTest(ids=ids),self.assertRaises(ValueError):M.Survey({'design':d})
        for changes in ({'count':0},{'count':5},{'count':True},{'method':'with_replacement'}):
            d=design(4,2);d['selection'].update(changes)
            with self.subTest(changes=changes),self.assertRaises(ValueError):M.Survey({'design':d})

    def test_subject_family_datum_measurement_and_capacity_are_distinct_types(self):
        s=M.Survey({'design':design(800,80,'weight')})
        sample=s.evaluate(role('sample'))
        self.assertEqual(sample,s.evaluate(obs('selected','weight')))
        for node in (subject('selected'),subject('population'),{'op':'datum','quantity':'weight'},
                     {'op':'number','value':80},obs('selected','height'),obs('population','weight')):
            with self.subTest(node=node):self.assertNotEqual(sample,s.evaluate(node))
        with self.assertRaises(ValueError):s.evaluate({'op':'cardinality','object':subject('selected')})
        for quantity in ('',True,None,[] ):
            with self.subTest(quantity=quantity),self.assertRaises(ValueError):s.evaluate({'op':'datum','quantity':quantity})

    def test_census_changes_sample_identity_and_reveals_duplicate_candidates(self):
        spec={'design':design(4,2),'query':'identity','target':role('sample'),'options':options([
            {'object':obs('selected')},{'object':obs('population')}])}
        self.assertEqual(M.observation_objects(spec),'0')
        spec['design']['selection']['count']=4
        with self.assertRaises(ValueError):M.observation_objects(spec)

    def test_wrong_population_range_is_not_sample_scope(self):
        spec={'design':design(30000,1000,'fitness'),'query':'claims','options':options([
          {'left':role('population'),'right':obs('selected','fitness')},
          {'left':role('individual'),'right':{'op':'datum','quantity':'fitness'}}])}
        self.assertEqual(M.observation_objects(spec),'1')
        spec['options'][0]['right']=obs('population','fitness')
        with self.assertRaises(ValueError):M.observation_objects(spec)

    def test_closed_measurements_reject_boolean_or_symbolic_rows(self):
        for value in (True,'x',"__import__('os')",[150,60]):
            d=design(2,1);d['records']=[{'subject':1,'value':value}]
            with self.subTest(value=value),self.assertRaises((ValueError,SyntaxError)):M.Survey({'design':d})


class StatisticalDefinitionTests(unittest.TestCase):
    def test_subgroup_counterexample_remains_biased_for_arbitrary_sample_size(self):
        spec={'included_value':200,'excluded_value':150,'options':options([
          {'claim':'not_guaranteed'},{'claim':'guaranteed_by_inclusion'},{'claim':'guaranteed_by_large_size'}])}
        self.assertEqual(M.sampling_guarantee(spec),'0')
        spec['included_value'],spec['excluded_value']=150,200
        self.assertEqual(M.sampling_guarantee(spec),'0')
        spec['excluded_value']=150
        with self.assertRaises(ValueError):M.sampling_guarantee(spec)

    def frequency_spec(self):
        return {'observation_count':20,'bin_width':5,'counterexample':{'data':[2]*8+[7]*12,'bins':[[0,5],[5,10]]},
         'options':options([{'algorithm':a} for a in ('sum_bin_widths','data_range','count_members_per_bin','sum_values_per_bin')])}

    def test_frequency_counts_occurrences_not_value_sum_or_distinct_set(self):
        spec=self.frequency_spec();self.assertEqual(M.frequency_algorithm(spec),'2')
        xs,bins,counts=M.frequencies([2,2,7],[[0,5],[5,10]])
        self.assertEqual(counts,[2,1])
        spec['counterexample']['data']=[3]*8+[8]*12
        self.assertEqual(M.frequency_algorithm(spec),'2')

    def test_frequency_alternative_needs_real_refutation_not_convenient_example(self):
        spec=self.frequency_spec();spec['counterexample']['data']=[1]*8+[6]*12
        # The first sum-of-values frequency happens to agree, but the second
        # still differs, so the full frequency-vector algorithm is refuted.
        self.assertEqual(M.frequency_algorithm(spec),'2')
        with self.assertRaises(ValueError):M.frequencies([2],[[0,5],[4,10]])
        with self.assertRaises(ValueError):M.frequencies([10],[[0,5],[5,10]])
        spec=self.frequency_spec();spec['bin_width']=4
        with self.assertRaises(ValueError):M.frequency_algorithm(spec)
        spec=self.frequency_spec();spec['observation_count']=19
        with self.assertRaises(ValueError):M.frequency_algorithm(spec)

    def test_all_ones_cannot_refute_sum_values_algorithm(self):
        spec={'observation_count':20,'bin_width':5,'counterexample':{'data':[1]*20,'bins':[[0,5]]},
              'options':options([{'algorithm':'count_members_per_bin'},{'algorithm':'sum_values_per_bin'}])}
        with self.assertRaises(ValueError):M.frequency_algorithm(spec)

    def test_iqr_counterexample_must_have_both_larger_width_and_lower_mean(self):
        spec={'options':options([{'claim':'central_width_increases'},
          {'claim':'central_width_decreases'},
          {'claim':'mean_increases','counterexample':[[10,11,11,12],[0,0,2,2]]}])}
        self.assertEqual(M.quartile_width(spec),'0')
        spec['options'][2]['counterexample']=[[0,0,2,2],[10,11,11,12]]
        with self.assertRaises(ValueError):M.quartile_width(spec)

    def test_same_extremes_and_count_do_not_determine_mean_or_variance(self):
        pair=[[1,2,3],[1,1,3]]
        spec={'options':options([{'algorithms':['max'],'counterexample':pair},
          {'algorithms':['mean','variance']},{'algorithms':['count'],'counterexample':pair}])}
        self.assertEqual(M.summary_sufficiency(spec),'1')
        spec['options'][0]['counterexample']=[[1,2,3],[1,2,3]]
        with self.assertRaises(ValueError):M.summary_sufficiency(spec)
        spec['options'][0]['counterexample']=pair;spec['options'][1]['algorithms'].append('max')
        self.assertEqual(M.summary_sufficiency(spec),'1')


class GeometryProofTests(unittest.TestCase):
    def test_graph_slope_sign_changes_with_coordinate_step(self):
        spec={'positive':['t','v'],'coordinate_step':['t','v'],'axis_units':[1,1],
              'options':options([{'comparison':s} for s in ('decreasing','increasing','constant')])}
        self.assertEqual(M.graph_order(spec),'1')
        spec['coordinate_step'][1]='-v';self.assertEqual(M.graph_order(spec),'0')
        spec['coordinate_step'][1]='0';self.assertEqual(M.graph_order(spec),'2')
        spec['coordinate_step'][0]='-t'
        with self.assertRaises(ValueError):M.graph_order(spec)

    def test_graph_order_unknown_sign_is_not_false(self):
        spec={'positive':['t'],'variables':['v'],'coordinate_step':['t','v'],'axis_units':[1,1],
              'options':options([{'comparison':'increasing'},{'comparison':'decreasing'}])}
        with self.assertRaises(ValueError):M.graph_order(spec)

    def test_maximum_does_not_require_unique_maximizer(self):
        spec={'vertical_scale':1,'vertical_offset':0,'options':options([
          {'interpretation':'upper_ordinate'},{'interpretation':'lower_ordinate'},{'interpretation':'zero_ordinate'}])}
        self.assertEqual(M.graph_extremum(spec),'0')
        spec['vertical_scale']=-1
        with self.assertRaises(ValueError):M.graph_extremum(spec)
        spec['vertical_scale']=1;spec['vertical_offset']=-10
        with self.assertRaises(ValueError):M.graph_extremum(spec)

    def angle_spec(self):
        return {'given':'parallel','goal':'angle_equal','angles':[
          {'vertex':'upper','region':'interior','side':'left'},
          {'vertex':'lower','region':'interior','side':'right'}],
          'options':options([
           {'theorem':'parallel_angles','angle_class':'alternate_interior','direction':'property','conclusion':'angle_equal'},
           {'theorem':'parallel_angles','angle_class':'alternate_interior','direction':'criterion','conclusion':'angle_equal'},
           {'theorem':'vertical_angles'}])}

    def test_rule_direction_and_geometric_positions_are_independently_checked(self):
        spec=self.angle_spec();self.assertEqual(M.direct_angle_rule(spec),'0')
        spec['angles'][1]={'vertex':'upper','region':'exterior','side':'right'}
        self.assertEqual(M.direct_angle_rule(spec),'2')
        spec['angles'][1]=spec['angles'][0]
        with self.assertRaises(ValueError):M.direct_angle_rule(spec)
        spec=self.angle_spec();spec['options'][1]['theorem']='unproved'
        with self.assertRaises(ValueError):M.direct_angle_rule(spec)

    def test_unsupported_goal_is_not_called_false(self):
        spec=self.angle_spec();spec['goal']='triangle_sum'
        with self.assertRaises(ValueError):M.direct_angle_rule(spec)

    def test_doubled_median_requires_half_turn_and_proves_strict_metric_goal(self):
        kinds=['perpendicular_through_midpoint','parallel_ab_through_midpoint','midpoint_ab','extend_median_equal_length']
        spec={'options':options([{'construction':k} for k in kinds])}
        self.assertEqual(M.doubled_median(spec),'3')
        spec['options'].reverse();self.assertEqual(M.doubled_median(spec),'3')
        spec['options'][0]['construction']='unproved_rotation'
        with self.assertRaises(ValueError):M.doubled_median(spec)
        spec={'options':options([{'construction':'extend_median_equal_length'}]*2)}
        with self.assertRaises(ValueError):M.doubled_median(spec)


if __name__=='__main__':unittest.main()
