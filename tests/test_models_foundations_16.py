"""Survey countermodels must execute; count guarantees cover their full domain."""
from copy import deepcopy
from fractions import Fraction
from itertools import permutations
from pathlib import Path
import sys
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import models_foundations_16 as M


def survey_spec():
    return {'kind': 'f16_survey_guarantees', 'options': [
        {'key': 'A', 'text': 'strict census accuracy', 'claim': {
            'op': 'census_always_strictly_less_absolute_mean_error',
            'population': [0, 2, 4], 'measurement_domain': 'arbitrary_real_readings_allowed',
            'census': {'indices': [0, 1, 2], 'readings': [1, 3, 5]},
            'sample': {'indices': [1], 'readings': [2]}}},
        {'key': 'B', 'text': 'exact sample identity', 'claim': {
            'op': 'proper_sample_mean_always_equals_true_mean',
            'population': [0, 2], 'sample_indices': [0], 'measurement': 'exact'}},
        {'key': 'C', 'text': 'census violates positive reserve', 'claim': {
            'op': 'universal_remaining_count_relation',
            'domain': {'population': 'positive_integer',
                       'reserve': 'integer_from_one_through_population', 'destruction_per_test': 1},
            'plan': {'op': 'all_items'},
            'relation': {'left': 'remaining', 'comparison': 'lt', 'right': 'reserve'}}},
        {'key': 'D', 'text': 'partial individual identification', 'claim': {
            'op': 'proper_observation_always_identifies_all_records',
            'population': [0, 1, 2], 'observed_indices': [0, 1], 'measurement': 'exact',
            'knowledge': 'only_observed_individual_records', 'alternative_delta': 1}}]}


class SurveyMathematics(unittest.TestCase):
    def test_actual_countermodels_and_unique_count_theorem(self):
        s = survey_spec()
        e = M.error_countermodel(s['options'][0]['claim'])
        self.assertEqual((e['population_mean'], e['census_mean'], e['sample_mean']), (2, 3, 2))
        self.assertEqual((e['census_error'], e['sample_error']), (1, 0))
        self.assertEqual(M.sample_identity_countermodel(s['options'][1]['claim'])['sample_mean'], 0)
        world = M.record_countermodel(s['options'][3]['claim'])
        self.assertEqual(world['observed'], world['other_observed'])
        self.assertNotEqual(world['first_world'], world['second_world'])
        self.assertEqual(M.survey_claims(s), 'census violates positive reserve')

    def test_general_error_worlds_include_fraction_negative_offset_and_equal_precision(self):
        for shift in ('-13/7', '1/2', 9):
            c = survey_spec()['options'][0]['claim']
            c['population'] = ['-4/3', '1/2', '7/3']
            truth = sum(map(Fraction, c['population']))/3
            c['census']['readings'] = [str(Fraction(v)+Fraction(shift)) for v in c['population']]
            c['sample']['readings'] = [str(truth)]
            e = M.error_countermodel(c)
            self.assertEqual(e['census_error'], abs(Fraction(shift)))
            self.assertEqual(e['sample_error'], 0)
        # "Strictly more accurate" is also refuted by equality, not just worse error.
        c = survey_spec()['options'][0]['claim']
        c['census']['readings'] = [0, 2, 4]
        self.assertEqual(M.error_countermodel(c)['census_error'], 0)

    def test_measurement_rows_can_be_permuted_but_must_cover_exactly_the_population(self):
        c = survey_spec()['options'][0]['claim']
        c['census'] = {'indices': [2, 0, 1], 'readings': [5, 1, 3]}
        self.assertEqual(M.error_countermodel(c)['census_error'], 1)
        for indices, readings in [([0, 1], [1, 3]), ([0, 0, 2], [1, 1, 5]),
                                  ([0, 1, 3], [1, 3, 5]), ([0, 1, 2], [1, 3])]:
            c = survey_spec()['options'][0]['claim'];c['census'] = {'indices': indices, 'readings': readings}
            with self.subTest(indices=indices), self.assertRaises(ValueError): M.error_countermodel(c)

    def test_true_sample_membership_and_actual_failure_are_required(self):
        for population, sample in [([0, 1, 5], [0]), ([-4, 2, 8, 14], [0, 1]),
                                   (['1/7', '4/7'], [1])]:
            c = survey_spec()['options'][1]['claim'];c.update(population=population, sample_indices=sample)
            result = M.sample_identity_countermodel(c)
            self.assertNotEqual(result['population_mean'], result['sample_mean'])
        for indices in ([], [0, 0], [0, 1], [2], [True]):
            c = survey_spec()['options'][1]['claim'];c['sample_indices'] = indices
            with self.subTest(indices=indices), self.assertRaises(ValueError): M.sample_identity_countermodel(c)
        c = survey_spec()['options'][1]['claim'];c['population'] = [7, 7]
        with self.assertRaises(ValueError): M.sample_identity_countermodel(c)
        c = survey_spec()['options'][0]['claim'];c['census']['readings'] = [0, 2, 4];c['sample']['readings'] = [100]
        with self.assertRaises(ValueError): M.error_countermodel(c)

    def test_reserve_chart_covers_all_sizes_including_R_equals_N(self):
        c = survey_spec()['options'][2]['claim']
        self.assertTrue(M.reserve_relation(c))
        for n in range(1, 30):
            for r in range(1, n+1):
                u, q = r-1, n-r
                self.assertGreaterEqual(u, 0);self.assertGreaterEqual(q, 0)
                self.assertEqual(1+u+q, n);self.assertEqual(1+u, r)
                self.assertLess(n-n, r)
                if r == n: self.assertEqual(n-r, 0)  # no positive sample promised
        c['plan'] = {'op': 'all_except_reserved'}
        c['relation']['comparison'] = 'eq'
        self.assertTrue(M.reserve_relation(c))
        c['relation']['comparison'] = 'lt'
        self.assertFalse(M.reserve_relation(c))

    def test_affine_sign_decision_is_general_and_has_legal_negative_witnesses(self):
        for comparison, expected in [('lt', False), ('le', False), ('eq', False), ('ge', True), ('gt', False)]:
            self.assertEqual(M._universal_affine_relation((0, 1, 0), comparison), expected)
        for c in (-10, 0, 10, Fraction(1, 7)):
            for a in (-2, 0, 3):
                for b in (-1, 0, 4):
                    for comparison in ('lt', 'le', 'eq', 'ge', 'gt'):
                        actual = M._universal_affine_relation((c, a, b), comparison)
                        if actual:
                            self.assertTrue(all(M._relation(c+a*u+b*q, comparison)
                                                for u in range(10) for q in range(10)))
        self.assertFalse(M._universal_affine_relation((10000, -1, 0), 'gt'))
        self.assertFalse(M._universal_affine_relation((10000, 0, -1), 'ge'))

    def test_two_worlds_for_many_partial_record_patterns_and_both_delta_signs(self):
        for size in range(2, 10):
            for delta in ('-19/3', '1/17', 7):
                for indices in ([0], list(range(size-1)), list(range(1, size))):
                    c = survey_spec()['options'][3]['claim']
                    c.update(population=[str(Fraction(i, 3)) for i in range(size)],
                             observed_indices=indices, alternative_delta=delta)
                    result = M.record_countermodel(c)
                    self.assertEqual(result['observed'], result['other_observed'])
                    self.assertNotEqual(result['first_world'], result['second_world'])
                    self.assertNotIn(result['changed_index'], indices)

    def test_full_records_zero_change_or_external_information_are_not_partial_countermodels(self):
        for patch in ({'observed_indices': [0, 1, 2]}, {'observed_indices': []},
                      {'alternative_delta': 0}, {'knowledge': 'all_records_known_elsewhere'},
                      {'measurement': 'possibly_inexact'}):
            c = survey_spec()['options'][3]['claim'];c.update(patch)
            with self.subTest(patch=patch), self.assertRaises(ValueError): M.record_countermodel(c)


class SurveyGuards(unittest.TestCase):
    def test_keys_text_order_are_independent_and_different_true_math_does_not_depend_on_C(self):
        for order in permutations(range(4)):
            s = survey_spec();s['options'] = [s['options'][i] for i in order]
            for index, option in enumerate(s['options']): option.update(key='key'+str(index), text='claim'+str(order[index]))
            self.assertEqual(M.survey_claims(s), 'claim2')
        s = survey_spec();s['options'][2]['claim']['plan'] = {'op': 'all_except_reserved'}
        s['options'][2]['claim']['relation']['comparison'] = 'eq'
        self.assertEqual(M.survey_claims(s), 'census violates positive reserve')

    def test_unknown_extra_and_missing_fields_are_never_ignored(self):
        paths = [(), ('options', 0), ('options', 0, 'claim'), ('options', 0, 'claim', 'census'),
                 ('options', 2, 'claim', 'domain'), ('options', 2, 'claim', 'plan'),
                 ('options', 2, 'claim', 'relation'), ('options', 3, 'claim')]
        for path in paths:
            s = survey_spec();node = s
            for part in path: node = node[part]
            node['unknown'] = 'not a mathematical premise'
            with self.subTest(path=path), self.assertRaises(ValueError): M.survey_claims(s)
        for option in range(4):
            s = survey_spec();s['options'][option]['claim']['op'] = 'unknown'
            with self.subTest(option=option), self.assertRaises(ValueError): M.survey_claims(s)
        for path, key in [(('options', 0, 'claim'), 'measurement_domain'),
                          (('options', 2, 'claim', 'domain'), 'reserve'),
                          (('options', 3, 'claim'), 'knowledge')]:
            s = survey_spec();node = s
            for part in path: node = node[part]
            del node[key]
            with self.subTest(path=path), self.assertRaises(ValueError): M.survey_claims(s)

    def test_resource_unknown_domain_plan_operand_and_comparison_fail_closed(self):
        for target, key, value in [('domain', 'reserve', 'nonnegative'), ('domain', 'destruction_per_test', True),
                                   ('domain', 'population', 'arbitrary_real'), ('plan', 'op', 'sample_some'),
                                   ('relation', 'left', 'undetected_quality'), ('relation', 'comparison', 'unknown')]:
            c = survey_spec()['options'][2]['claim'];c[target][key] = value
            with self.subTest(target=target, key=key), self.assertRaises(ValueError): M.reserve_relation(c)

    def test_direct_proof_helpers_also_consume_op_and_reject_malformed_indices_or_objects(self):
        functions = [M.error_countermodel, M.sample_identity_countermodel,
                     M.reserve_relation, M.record_countermodel]
        for index, function in enumerate(functions):
            c = survey_spec()['options'][index]['claim'];c['op'] = 'unknown'
            with self.subTest(index=index), self.assertRaises(ValueError): function(c)
        c = survey_spec()['options'][2]['claim'];c['relation']['left'] = {'unknown': 'object'}
        with self.assertRaises(ValueError): M.reserve_relation(c)
        c = survey_spec()['options'][1]['claim'];c['sample_indices'] = [0]*1000
        with self.assertRaises(ValueError): M.sample_identity_countermodel(c)

    def test_numeric_unicode_float_boolean_and_raw_execution_tokens_are_rejected(self):
        for token in (True, 0.5, '③', '3⁵', '3。5', '３', 'NaN', '1/0', '__import__("os")'):
            for path in [('population', 0), ('census', 'readings', 0), ('sample', 'readings', 0)]:
                s = survey_spec();node = s['options'][0]['claim']
                for part in path[:-1]: node = node[part]
                node[path[-1]] = token
                with self.subTest(token=token, path=path), self.assertRaises(ValueError): M.survey_claims(s)
            s = survey_spec();s['options'][3]['claim']['alternative_delta'] = token
            with self.subTest(token=token), self.assertRaises(ValueError): M.survey_claims(s)

    def test_duplicate_or_missing_success_and_bounded_population(self):
        s = survey_spec();extra = deepcopy(s['options'][2]);extra['key'] = 'E';s['options'].append(extra)
        with self.assertRaises(ValueError): M.survey_claims(s)
        s = survey_spec();s['options'].pop(2)
        with self.assertRaises(ValueError): M.survey_claims(s)
        s = survey_spec();s['options'][3]['key'] = 'A'
        with self.assertRaises(ValueError): M.survey_claims(s)
        for population in ([], [1], [0]*129):
            s = survey_spec();s['options'][0]['claim']['population'] = population
            with self.subTest(size=len(population)), self.assertRaises(ValueError): M.survey_claims(s)

    def test_first_model_call_is_under_the_offline_timeout(self):
        start = time.monotonic()
        self.assertEqual(M.survey_claims(survey_spec()), 'census violates positive reserve')
        self.assertLess(time.monotonic()-start, 2)


if __name__ == '__main__': unittest.main()
