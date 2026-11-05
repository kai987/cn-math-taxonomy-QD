"""Universal and executable histogram-coordinate proof regressions."""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import models_geometry_33 as M
from verify_questions import compare_choice


def cardinality(collection):
    return {'op':'cardinality','of':{'op':collection}}


def axis_spec():
    intervals={'op':'bin_intervals'}
    counts=cardinality('bin_members')
    total=cardinality('all_members')
    return {'kind':'g33_histogram_axis_encoding',
        'construction':{'shape':'axis_aligned_rectangles','bin_axis':'x',
            'frequency_origin':0,'frequency_scale':1,'bin_spacing':'equal_width'},
        'example':{'endpoints':[-3,-1,1,3],'frequencies':[1,0,3]},
        'counterexample':{'endpoints':[-4,1,6,11],'frequencies':[2,4,1]},
        'options':[
            {'key':'A','text':'counts;intervals','axes':{'x':deepcopy(counts),'y':deepcopy(intervals)}},
            {'key':'B','text':'intervals;counts','axes':{'x':deepcopy(intervals),'y':deepcopy(counts)}},
            {'key':'C','text':'total;width','axes':{'x':total,'y':{'op':'length','of':deepcopy(intervals)}}},
            {'key':'D','text':'ratios;number','axes':{'x':{'op':'divide','numerator':deepcopy(counts),
                'denominator':deepcopy(total)},'y':cardinality('bins')}}]}


class HistogramConstructionTests(unittest.TestCase):
    def test_every_rectangle_and_both_coordinate_projections_are_constructed(self):
        s=axis_spec();h=M.Histogram(s['example'],'x')
        self.assertEqual(h.bars[0],((-3,0),(-1,0),(-1,1),(-3,1)))
        self.assertEqual(h.bars[1],((-1,0),(1,0),(1,0),(-1,0)))
        self.assertEqual(h.projections['x'],((-3,-1),(-1,1),(1,3)))
        self.assertEqual(h.projections['y'],((0,1),(0,0),(0,3)))
        self.assertEqual(M.histogram_axes(s),'intervals;counts')

    def test_origins_widths_frequencies_and_bin_numbers_are_parameters(self):
        tables=[{'endpoints':[0,1],'frequencies':[1]},
            {'endpoints':['-7/3','-2','-5/3','-4/3'],'frequencies':[0,9,0]},
            {'endpoints':[100,110,120,130,140],'frequencies':[1,1,1,1]},
            {'endpoints':[0,1,2],'frequencies':[10**40,0]}]
        for table in tables:
            s=axis_spec();s['example']=table
            with self.subTest(table=table):
                self.assertEqual(M.histogram_axes(s),'intervals;counts')

    def test_generic_identity_not_a_coincident_numeric_snapshot_decides_axes(self):
        s=axis_spec();s['example']={'endpoints':[0,1],'frequencies':[1]}
        h=M.Histogram(s['example'],'x')
        self.assertEqual(h.projections['x'],h.projections['y'])
        self.assertEqual(M.histogram_axes(s),'intervals;counts')

    def test_transposing_the_constructed_rectangles_reverses_the_correct_axes(self):
        s=axis_spec();s['construction']['bin_axis']='y'
        h=M.Histogram(s['example'],'y')
        self.assertEqual(h.bars[0],((0,-3),(0,-1),(1,-1),(1,-3)))
        self.assertEqual(M.histogram_axes(s),'counts;intervals')

    def test_zero_frequency_bins_preserve_their_footprints_and_identity(self):
        s=axis_spec();s['example']['frequencies']=[0,4,0]
        h=M.Histogram(s['example'],'x')
        self.assertEqual(h.projections['x'],h.intervals)
        self.assertEqual(tuple(hi-lo for lo,hi in h.projections['y']),(0,4,0))
        self.assertEqual(M.histogram_axes(s),'intervals;counts')

    def test_candidate_order_keys_text_are_not_part_of_mathematical_decision(self):
        s=axis_spec();s['options'].reverse()
        for i,o in enumerate(s['options']):o.update(key=str(i),text='anonymous'+str(i))
        self.assertEqual(M.histogram_axes(s),'anonymous2')

    def test_equivalent_quantity_program_is_derived_rather_than_name_matched(self):
        s=axis_spec();n=cardinality('all_members')
        one={'op':'divide','numerator':deepcopy(n),'denominator':deepcopy(n)}
        s['options'][1]['axes']['y']={'op':'divide','numerator':cardinality('bin_members'),'denominator':one}
        self.assertEqual(M.histogram_axes(s),'intervals;counts')

    def test_all_quantity_functions_execute_and_conserve_actual_counts(self):
        h=M.Histogram(axis_spec()['example'],'x')
        values=[M.quantity(node,h).values for node in (
            {'op':'bin_intervals'},cardinality('bin_members'),cardinality('all_members'),
            {'op':'length','of':{'op':'bin_intervals'}},
            {'op':'divide','numerator':cardinality('bin_members'),'denominator':cardinality('all_members')},
            cardinality('bins'))]
        self.assertEqual(values,[((-3,-1),(-1,1),(1,3)),(1,0,3),4,(2,2,2),
            (Fraction(1,4),0,Fraction(3,4)),3])


class StrictDomainAndUniquenessTests(unittest.TestCase):
    def test_unequal_decreasing_repeated_or_incomplete_boundaries_reject(self):
        for table in ({'endpoints':[0,1,3],'frequencies':[2,1]},
            {'endpoints':[0,0,1],'frequencies':[2,1]},
            {'endpoints':[2,1,0],'frequencies':[2,1]},
            {'endpoints':[0,1,2],'frequencies':[2]},
            {'endpoints':[],'frequencies':[]},
            {'endpoints':[0,1],'frequencies':[0]}):
            s=axis_spec();s['example']=table
            with self.subTest(table=table),self.assertRaises(ValueError):M.histogram_axes(s)

    def test_fractional_negative_boolean_unknown_or_missing_counts_reject(self):
        for value in (-1,True,False,'2',Fraction(1,2),0.5,None,10**100):
            s=axis_spec();s['example']['frequencies'][0]=value
            with self.subTest(value=value),self.assertRaises(ValueError):M.histogram_axes(s)
        s=axis_spec();del s['example']['frequencies']
        with self.assertRaises(ValueError):M.histogram_axes(s)

    def test_raw_numeric_spelling_cannot_change_values_or_run_code(self):
        for value in (True,0.5,float('inf'),'nan','3。5','3⁵','③','３','1 2','1/0','__import__("os")'):
            s=axis_spec();s['example']['endpoints'][0]=value
            with self.subTest(value=value),self.assertRaises((ValueError,ZeroDivisionError)):M.histogram_axes(s)

    def test_density_relative_frequency_nonzero_baseline_and_reverse_scale_reject(self):
        for field,value in [('shape','density_rectangles'),('frequency_scale','1/w'),
            ('frequency_scale',0),('frequency_scale',-1),('frequency_scale',True),
            ('frequency_origin',1),('frequency_origin',False),('bin_spacing','arbitrary'),('bin_axis','z')]:
            s=axis_spec();s['construction'][field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):M.histogram_axes(s)

    def test_missing_premises_and_unknown_fields_at_every_level_reject(self):
        paths=[(),('construction',),('example',),('counterexample',),('options',0),
            ('options',0,'axes'),('options',0,'axes','x'),('options',0,'axes','x','of')]
        for path in paths:
            s=axis_spec();node=s
            for key in path:node=node[key]
            node['unknown']='claim'
            with self.subTest(path=path),self.assertRaises(ValueError):M.histogram_axes(s)
        for field in ('bin_spacing','frequency_scale','frequency_origin'):
            s=axis_spec();del s['construction'][field]
            with self.subTest(field=field),self.assertRaises(ValueError):M.histogram_axes(s)

    def test_unknown_in_a_false_candidate_or_second_axis_cannot_be_short_circuited(self):
        for i,axis in [(0,'y'),(2,'x'),(3,'y')]:
            s=axis_spec();s['options'][i]['axes'][axis]={'op':'unknown'}
            with self.subTest(i=i,axis=axis),self.assertRaises(ValueError):M.histogram_axes(s)

    def test_bad_quotient_types_or_unproved_divisors_reject(self):
        for numerator,denominator in [({'op':'bin_intervals'},cardinality('all_members')),
            (cardinality('bin_members'),cardinality('bin_members'))]:
            s=axis_spec();s['options'][0]['axes']['x']={'op':'divide','numerator':numerator,'denominator':denominator}
            with self.assertRaises(ValueError):M.histogram_axes(s)
        s=axis_spec();s['options'][0]['axes']['x']={'op':'length','of':cardinality('bin_members')}
        with self.assertRaises(ValueError):M.histogram_axes(s)

    def test_nonidentity_with_a_coincident_witness_fails_conservatively(self):
        s=axis_spec();s['counterexample']={'endpoints':[0,1],'frequencies':[1]}
        with self.assertRaises(ValueError):M.histogram_axes(s)

    def test_invalid_counterexample_is_not_used_as_a_disproof(self):
        s=axis_spec();s['counterexample']['endpoints']=[0,1,3,4]
        with self.assertRaises(ValueError):M.histogram_axes(s)

    def test_duplicate_equivalent_or_missing_candidate_never_chooses_first(self):
        s=axis_spec();o=deepcopy(s['options'][1]);o['key']='extra';s['options'].append(o)
        with self.assertRaises(ValueError):M.histogram_axes(s)
        s=axis_spec();s['options'].pop(1)
        with self.assertRaises(ValueError):M.histogram_axes(s)
        s=axis_spec();s['options'][0]['key']='B'
        with self.assertRaises(ValueError):M.histogram_axes(s)

    def test_quantity_tree_budget_prevents_unbounded_programs(self):
        s=axis_spec();term=cardinality('all_members')
        for _ in range(25):term={'op':'divide','numerator':term,'denominator':cardinality('bins')}
        s['options'][0]['axes']['x']=term
        with self.assertRaises(ValueError):M.histogram_axes(s)

    def test_current_source_answer_compares_to_computed_candidate_text(self):
        data=json.loads((ROOT/'data/questions.json').read_text())
        q=next(q for q in data if q['id']=='cnm_107_q3')
        s=axis_spec()
        for option,original in zip(s['options'],q['choices']):option['text']=original['text']
        self.assertTrue(compare_choice(q,M.histogram_axes(s))[0])


if __name__=='__main__':unittest.main()
