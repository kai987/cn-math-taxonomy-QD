"""Finite-table information certificates and legal interval counterfunctions."""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import json
import sys
import unittest
import sympy as S

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import models_geometry_29 as M
from verify_questions import compare_choice


def interval(left=-2,right=3,left_closed=True,right_closed=True):
    return dict(left=left,right=right,left_closed=left_closed,right_closed=right_closed)


def information_spec():
    return {'kind':'g29_partial_function_information',
        'premises':{'domain':'nondegenerate_real_interval','known_pairs':'finite_nonempty_exact_pairs',
            'additional_constraints':'none'},
        'example':{'interval':interval(),'pairs':[[0,0],[1,1]]},
        'options':[
            {'key':'A','text':'trend','claim':{'op':'uniquely_determine_trend_everywhere'}},
            {'key':'B','text':'known pairs','claim':{'op':'read_all_listed_values'}},
            {'key':'C','text':'entire domain','claim':{'op':'table_lists_entire_interval_domain'}},
            {'key':'D','text':'any missing value','claim':{'op':'uniquely_determine_every_unlisted_value'}}]}


class PartialTableConstructionTests(unittest.TestCase):
    def test_lookup_and_all_constructed_polynomials_preserve_the_whole_table(self):
        s=information_spec();proof=M.PartialFunctionTable(s['example'])
        self.assertTrue(proof.lookup_preserved)
        for polynomial in (proof.polynomial,proof.value_alternative,proof.increasing,proof.decreasing):
            for x,y in proof.rows:
                self.assertEqual(polynomial.subs(proof.x,M._sym(x)),M._sym(y))
        self.assertEqual([proof.claim(o['claim']) for o in s['options']],[False,True,False,False])
        self.assertEqual(M.partial_function_information(s),'known pairs')

    def test_values_and_local_derivatives_really_differ_at_an_unlisted_interior(self):
        proof=M.PartialFunctionTable(information_spec()['example'])
        u=M._sym(proof.witness)
        self.assertTrue(proof.interval.contains(proof.witness,interior=True))
        self.assertNotIn(proof.witness,proof.lookup)
        self.assertNotEqual(proof.value_alternative.subs(proof.x,u),proof.polynomial.subs(proof.x,u))
        self.assertEqual(S.diff(proof.increasing,proof.x).subs(proof.x,u),1)
        self.assertEqual(S.diff(proof.decreasing,proof.x).subs(proof.x,u),-1)

    def test_one_constant_nonmonotone_and_fractional_tables_are_parameters(self):
        examples=[[[0,7]], [[-1,3],[0,3],[1,3]],
            [[-1,7],[0,-4],[1,9],[2,-11]],
            [['-1/2','3/7'],['1/3','-2/5'],['3/2','5/11']]]
        for pairs in examples:
            s=information_spec();s['example']['pairs']=pairs
            with self.subTest(pairs=pairs):
                self.assertEqual(M.partial_function_information(s),'known pairs')
                proof=M.PartialFunctionTable(s['example'])
                self.assertTrue(proof.values_differ and proof.opposite_local_trends)

    def test_every_endpoint_closure_and_unbounded_interval_is_handled(self):
        intervals=[interval(-1,2,lc,rc) for lc in (False,True) for rc in (False,True)]
        intervals += [interval(None,None,False,False),interval(None,2,False,False),
            interval(-1,None,False,False)]
        for domain in intervals:
            s=information_spec();s['example']['interval']=domain
            with self.subTest(domain=domain):
                self.assertEqual(M.partial_function_information(s),'known pairs')

    def test_tiny_intervals_do_not_depend_on_grid_sampling_or_epsilon(self):
        s=information_spec();s['example']={'interval':interval('0','1/100000000000000000000'),
            'pairs':[[0,1],['1/100000000000000000000',3]]}
        proof=M.PartialFunctionTable(s['example'])
        self.assertTrue(Fraction(0)<proof.witness<Fraction(1,10**20))
        self.assertEqual(M.partial_function_information(s),'known pairs')

    def test_the_n_plus_one_candidate_construction_cannot_be_exhausted_by_n_points(self):
        s=information_spec();s['example']={'interval':interval(0,1,False,False),
            'pairs':[['1/4',1],['1/2',2],['3/4',3]]}
        proof=M.PartialFunctionTable(s['example'])
        self.assertTrue(proof.interval.contains(proof.witness,interior=True))
        self.assertNotIn(proof.witness,proof.lookup)

    def test_consistent_repeated_rows_add_no_new_function_information(self):
        s=information_spec();s['example']['pairs'] += [[0,0],[1,1]]
        proof=M.PartialFunctionTable(s['example'])
        self.assertEqual(len(proof.rows),4);self.assertEqual(len(proof.points),2)
        self.assertTrue(proof.lookup_preserved)
        self.assertEqual(M.partial_function_information(s),'known pairs')

    def test_row_candidate_key_and_text_order_are_not_answer_inputs(self):
        s=information_spec();s['example']['pairs'].reverse();s['options'].reverse()
        for i,option in enumerate(s['options']):option.update(key=str(i),text='anonymous'+str(i))
        self.assertEqual(M.partial_function_information(s),'anonymous2')
        forward=M.PartialFunctionTable(information_spec()['example'])
        reversed_table=M.PartialFunctionTable(s['example'])
        self.assertEqual(forward.polynomial,reversed_table.polynomial)
        self.assertEqual(forward.vanishing,reversed_table.vanishing)

    def test_affine_changes_to_known_outputs_do_not_create_an_unknown_function_law(self):
        for scale,offset in [(3,-7),(-2,5),(0,11)]:
            s=information_spec();s['example']['pairs']=[[x,scale*y+offset] for x,y in s['example']['pairs']]
            self.assertEqual(M.partial_function_information(s),'known pairs')


class StrictPremiseAndReferenceGuards(unittest.TestCase):
    def test_empty_nonfunctional_unknown_or_malformed_rows_fail_closed(self):
        for pairs in ([],[[0,0],[0,1]],[[0]],[[0,0,1]],[[True,1]],[[0,None]],'rows'):
            s=information_spec();s['example']['pairs']=pairs
            with self.subTest(pairs=pairs),self.assertRaises(ValueError):M.partial_function_information(s)

    def test_noninterval_degenerate_reversed_and_out_of_domain_data_reject(self):
        domains=[interval(1,1),interval(2,0),interval(0,2,False,True),
            interval(None,2,True,True),interval(-1,None,True,True),interval(-1,2,1,True)]
        for domain in domains:
            s=information_spec();s['example']['interval']=domain
            with self.subTest(domain=domain),self.assertRaises(ValueError):M.partial_function_information(s)

    def test_no_hidden_affine_continuity_or_interpolation_law_can_be_assumed(self):
        for key in ('domain','known_pairs','additional_constraints'):
            s=information_spec();del s['premises'][key]
            with self.subTest(key=key),self.assertRaises(ValueError):M.partial_function_information(s)
        for constraint in ('affine','is_the_interpolating_polynomial','monotone','known_formula'):
            s=information_spec();s['premises']['additional_constraints']=constraint
            with self.subTest(constraint=constraint),self.assertRaises(ValueError):M.partial_function_information(s)
        s=information_spec();s['premises']['domain']='finite_listed_inputs'
        with self.assertRaises(ValueError):M.partial_function_information(s)

    def test_numeric_unicode_nan_float_and_expression_injection_cannot_be_normalized(self):
        for value in (True,0.5,float('inf'),'nan','3。5','3⁵','③','３','1 2','1/0','__import__("os")',10**100):
            s=information_spec();s['example']['pairs'][0][1]=value
            with self.subTest(value=value),self.assertRaises((ValueError,ZeroDivisionError)):
                M.partial_function_information(s)

    def test_unknown_fields_at_all_levels_and_unknown_false_claims_reject(self):
        for path in [(),('premises',),('example',),('example','interval'),('options',0),('options',0,'claim')]:
            s=information_spec();node=s
            for part in path:node=node[part]
            node['unknown']='claim'
            with self.subTest(path=path),self.assertRaises(ValueError):M.partial_function_information(s)
        s=information_spec();s['options'][0]['claim']['op']='unknown'
        with self.assertRaises(ValueError):M.partial_function_information(s)

    def test_duplicate_equivalent_or_missing_successful_option_never_chooses_first(self):
        s=information_spec();extra=deepcopy(s['options'][1]);extra['key']='extra';s['options'].append(extra)
        with self.assertRaises(ValueError):M.partial_function_information(s)
        s=information_spec();s['options'].pop(1)
        with self.assertRaises(ValueError):M.partial_function_information(s)
        s=information_spec();s['options'][0]['key']='B'
        with self.assertRaises(ValueError):M.partial_function_information(s)

    def test_execution_budget_cannot_be_used_as_an_incomplete_table(self):
        s=information_spec();s['example']={'interval':interval(-1,10),
            'pairs':[[i,i*i] for i in range(9)]}
        with self.assertRaises(ValueError):M.partial_function_information(s)
        s=information_spec();s['example']['pairs'] *= 9
        with self.assertRaises(ValueError):M.partial_function_information(s)

    def test_current_reference_answer_matches_the_computed_option_text(self):
        q=next(q for q in json.loads((ROOT/'data/questions.json').read_text()) if q['id']=='cnm_198_q1')
        s=information_spec()
        for option,choice in zip(s['options'],q['choices']):option.update(key=choice['key'],text=choice['text'])
        self.assertTrue(compare_choice(q,M.partial_function_information(s))[0])


if __name__=='__main__':unittest.main()
