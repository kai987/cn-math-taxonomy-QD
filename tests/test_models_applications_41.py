"""Provenance and category-basis regressions for the remaining41 applications."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import models_applications_41 as M


def empirical_spec(population='seed', condition='controlled', period='current', field='germinated'):
    domain = ['no', 'yes']
    instrument = {'op': 'design_questionnaire', 'population': population, 'field': field, 'domain': domain}
    return {'kind': 'app41_empirical_collection',
        'target': {'population': population, 'field': field, 'domain': domain, 'condition': condition,
                   'period': period, 'basis': 'observed'},
        'resources': {
            'archive': {'kind': 'archive', 'entries': []},
            'seeds': {'kind': 'cohort', 'population': population, 'field': field, 'domain': domain,
                'values': ['yes', 'no', 'yes'], 'condition': condition, 'period': period},
            'people': {'kind': 'respondents', 'population': population, 'field': field, 'domain': domain,
                'values': ['yes', 'yes', 'yes'], 'condition': condition, 'period': period}},
        'options': [
            {'key': 'a', 'text': 'archive', 'plan': {'op': 'read', 'resource': 'archive'}},
            {'key': 'b', 'text': 'questionnaire', 'plan': {'op': 'administer', 'instrument': instrument,
                'respondents': {'op': 'read', 'resource': 'people'}, 'condition': condition, 'period': period}},
            {'key': 'c', 'text': 'experiment', 'plan': {'op': 'observe', 'field': field,
                'input': {'op': 'expose', 'cohort': {'op': 'read', 'resource': 'seeds'},
                    'condition': condition, 'period': period}}}]}


def organization_spec(categories=None):
    categories = categories or ['short', 'medium', 'long']
    raw = {'kind': 'rows', 'population': 'class', 'field': 'sleep', 'domain': categories,
           'basis': 'reported', 'condition': 'school_days', 'period': 'week', 'values': [categories[0], categories[-1], categories[0]]}
    instrument = {'op': 'design_questionnaire', 'population': 'class', 'field': 'sleep', 'domain': categories}
    return {'kind': 'app41_categorical_organization', 'source': 'raw', 'field': 'sleep',
        'resources': {'raw': raw, 'chart': dict(raw, kind='chart', values={value: i+1 for i, value in enumerate(categories)}),
            'pupils': {'kind': 'respondents', 'population': 'class', 'field': 'sleep', 'domain': categories,
                'values': [categories[0]], 'condition': 'school_days', 'period': 'week'}},
        'options': [
            {'key': 'a', 'text': 'design', 'plan': instrument},
            {'key': 'b', 'text': 'distribute', 'plan': {'op': 'administer', 'instrument': instrument,
                'respondents': {'op': 'read', 'resource': 'pupils'}, 'condition': 'school_days', 'period': 'week'}},
            {'key': 'c', 'text': 'compare', 'plan': {'op': 'argmin', 'input': {'op': 'read', 'resource': 'chart'}}},
            {'key': 'd', 'text': 'frequency table', 'plan': {'op': 'tabulate', 'input': {'op': 'group_count',
                'input': {'op': 'read', 'resource': 'raw'}, 'groups': [[v] for v in categories]}}}]}


class EmpiricalProtocolTests(unittest.TestCase):
    def test_new_current_measurement_is_produced_without_answer_labels(self):
        s = empirical_spec()
        self.assertEqual(M.empirical_collection(s), 'experiment')
        s['options'].reverse()
        for i, option in enumerate(s['options']):
            option['key'] = str(i); option['text'] = 'anonymous' + str(i)
        self.assertEqual(M.empirical_collection(s), 'anonymous0')

    def test_identifiers_and_binary_domain_order_are_not_semantic_answers(self):
        s = empirical_spec('culture', 'incubator', 'autumn', 'alive')
        s['target']['domain'].reverse()
        s['resources']['people']['domain'].reverse()
        self.assertEqual(M.empirical_collection(s), 'experiment')

    def test_a_current_applicable_archive_also_qualifies_not_automatically_rejected(self):
        s = empirical_spec()
        s['resources']['archive']['entries'] = [dict(deepcopy(s['target']), values=['no', 'yes'])]
        with self.assertRaises(ValueError): M.empirical_collection(s)
        s['options'][2]['plan']['input']['period'] = 'old'; s['resources']['seeds']['period'] = 'old'
        self.assertEqual(M.empirical_collection(s), 'archive')

    def test_archive_conditions_time_population_and_basis_are_checked(self):
        for key, value in [('condition', 'other'), ('period', 'old'), ('population', 'other'), ('basis', 'reported')]:
            s = empirical_spec(); entry = dict(deepcopy(s['target']), values=['no', 'yes']); entry[key] = value
            s['resources']['archive']['entries'] = [entry]
            with self.subTest(key=key): self.assertEqual(M.empirical_collection(s), 'experiment')

    def test_experiment_is_not_valid_for_wrong_condition_time_population(self):
        for change in ('condition', 'period', 'population'):
            s = empirical_spec()
            if change == 'population': s['resources']['seeds']['population'] = 'different'
            else:
                s['options'][2]['plan']['input'][change] = 'different'
                s['resources']['seeds'][change] = 'different'
            with self.subTest(change=change), self.assertRaises(ValueError): M.empirical_collection(s)

    def test_survey_is_reported_even_if_question_uses_the_measurement_field(self):
        s = empirical_spec(); result = M.Protocol(s['resources']).infer(s['options'][1]['plan'])[0]
        self.assertEqual(result.form, 'rows'); self.assertEqual(result.basis, 'reported')
        self.assertEqual(result.field, s['target']['field'])

    def test_observation_cannot_be_performed_before_exposure(self):
        s = empirical_spec(); s['options'][2]['plan']['input'] = {'op': 'read', 'resource': 'seeds'}
        with self.assertRaises(ValueError): M.empirical_collection(s)

    def test_wrong_field_unknown_operation_and_unknown_source_fail_even_for_rejected_option(self):
        mutations = [lambda s: s['options'][2]['plan'].update(field='unmeasured'),
            lambda s: s['options'][0]['plan'].update(op='assume'),
            lambda s: s['options'][0]['plan'].update(resource='missing')]
        for mutate in mutations:
            s = empirical_spec(); mutate(s)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError): M.empirical_collection(s)

    def test_missing_observation_assumptions_or_binary_domain_fail(self):
        for field in ('basis', 'condition', 'period', 'domain'):
            s = empirical_spec(); del s['target'][field]
            with self.subTest(field=field), self.assertRaises(ValueError): M.empirical_collection(s)
        s = empirical_spec(); s['target']['basis'] = 'reported'
        with self.assertRaises(ValueError): M.empirical_collection(s)
        s = empirical_spec(); s['resources']['seeds']['domain'] = ['a', 'b', 'c']
        with self.assertRaises(ValueError): M.empirical_collection(s)

    def test_duplicate_successful_protocol_is_ambiguity_not_first_match(self):
        s = empirical_spec(); other = deepcopy(s['options'][2]); other['key'] = 'other'; s['options'].append(other)
        with self.assertRaises(ValueError): M.empirical_collection(s)

    def test_real_records_follow_exposure_observation_and_survey_paths(self):
        s = empirical_spec(); checker = M.Protocol(s['resources'])
        result = checker.infer(s['options'][2]['plan'])[0]
        self.assertEqual(result.records, (('seeds:0', 'yes'), ('seeds:1', 'no'), ('seeds:2', 'yes')))
        self.assertEqual(result.trace, (('resource', 'seeds'), ('expose', 'controlled', 'current'), ('observe', 'germinated')))
        reported = M.Protocol(s['resources']).infer(s['options'][1]['plan'])[0]
        self.assertEqual([v for _, v in reported.records], ['yes', 'yes', 'yes'])
        self.assertNotEqual(result.records, reported.records)
        self.assertNotIn(('observe', 'germinated'), reported.trace)

    def test_all_binary_outcomes_produce_data_not_a_preset_rate(self):
        from itertools import product
        for n in (1, 2, 3):
            for values in product(('yes', 'no'), repeat=n):
                s = empirical_spec(); s['resources']['seeds']['values'] = list(values)
                self.assertEqual(M.empirical_collection(s), 'experiment')
                actual = M.Protocol(s['resources']).infer(s['options'][2]['plan'])[0]
                self.assertEqual(tuple(v for _, v in actual.records), values)

    def test_empty_missing_unknown_and_miscontextual_observations_fail(self):
        mutations = [lambda s: s['resources']['seeds'].update(values=[]),
            lambda s: s['resources']['seeds'].update(values=['unknown']),
            lambda s: s['resources']['seeds'].pop('values'),
            lambda s: s['options'][2]['plan']['input'].update(condition='unsupplied')]
        for mutate in mutations:
            s = empirical_spec(); mutate(s)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError): M.empirical_collection(s)


class CategoryBasisTests(unittest.TestCase):
    def test_full_operation_tree_produces_counts_and_other_operations_do_not(self):
        s = organization_spec()
        self.assertEqual(M.categorical_organization(s), 'frequency table')
        self.assertEqual([M.Protocol(s['resources']).infer(o['plan'])[0].form for o in s['options']],
                         ['instrument', 'rows', 'claim', 'frequency_table'])

    def test_arbitrary_category_names_order_and_number(self):
        for domain in (['a'], ['r', 'b'], ['d', 'b', 'c', 'a']):
            s = organization_spec(domain); s['options'].reverse()
            self.assertEqual(M.categorical_organization(s), 'frequency table')
            s['resources']['raw']['domain'].reverse()
            self.assertEqual(M.categorical_organization(s), 'frequency table')

    def test_partition_basis_identity_holds_for_any_multiset_of_rows(self):
        s = organization_spec(['a', 'b', 'c', 'd'])
        s['options'][3]['plan']['input']['groups'] = [['a', 'c'], ['b', 'd']]
        result = M.Protocol(s['resources']).infer(s['options'][3]['plan'])[0]
        self.assertEqual(result.coefficients, ((1, 0, 1, 0), (0, 1, 0, 1)))
        for multiplicities in ((0, 0, 0, 0), (1, 2, 3, 4), (1000000, 1, 0, 9)):
            counts = [sum(a*b for a, b in zip(row, multiplicities)) for row in result.coefficients]
            self.assertEqual(sum(counts), sum(multiplicities))

    def test_overlap_omission_unknown_category_or_duplicates_are_not_valid_partitions(self):
        for groups in ([['short', 'medium'], ['medium', 'long']], [['short'], ['medium']],
                       [['short'], ['medium'], ['long'], ['unknown']], [['short', 'short'], ['medium', 'long']]):
            s = organization_spec(); s['options'][3]['plan']['input']['groups'] = groups
            with self.subTest(groups=groups), self.assertRaises(ValueError): M.categorical_organization(s)

    def test_raw_rows_in_a_table_are_not_category_frequencies(self):
        s = organization_spec(); s['options'][3]['plan'] = {'op': 'tabulate', 'input': {'op': 'read', 'resource': 'raw'}}
        with self.assertRaises(ValueError): M.categorical_organization(s)

    def test_counts_from_an_unrelated_source_do_not_satisfy_target(self):
        s = organization_spec(); s['resources']['other'] = deepcopy(s['resources']['raw'])
        s['options'][3]['plan']['input']['input']['resource'] = 'other'
        with self.assertRaises(ValueError): M.categorical_organization(s)

    def test_impossible_dataflow_is_rejected_instead_of_counted_as_a_false_answer(self):
        s = organization_spec(); s['options'][3]['plan']['input']['input'] = deepcopy(s['options'][0]['plan'])
        with self.assertRaises(ValueError): M.categorical_organization(s)
        s = organization_spec(); s['options'][2]['plan']['input']['resource'] = 'raw'
        with self.assertRaises(ValueError): M.categorical_organization(s)

    def test_unknown_in_a_false_candidate_fails_closed(self):
        s = organization_spec(); s['options'][0]['plan']['op'] = 'guess'
        with self.assertRaises(ValueError): M.categorical_organization(s)

    def test_missing_target_field_or_ambiguous_frequency_table_fails_closed(self):
        s = organization_spec(); s['field'] = 'unknown'
        with self.assertRaises(ValueError): M.categorical_organization(s)
        s = organization_spec(); extra = deepcopy(s['options'][3]); extra['key'] = 'e'; s['options'].append(extra)
        with self.assertRaises(ValueError): M.categorical_organization(s)

    def test_malformed_domains_and_boolean_identifiers_do_not_pass(self):
        for domain in ([], ['a', 'a'], ['a', True], [1, 2]):
            s = organization_spec(); s['resources']['raw']['domain'] = domain
            with self.subTest(domain=domain), self.assertRaises(ValueError): M.categorical_organization(s)
        s = organization_spec(); s['source'] = True
        with self.assertRaises(ValueError): M.categorical_organization(s)

    def test_noncanonical_fields_and_unbounded_trees_are_rejected(self):
        s = organization_spec(); s['resources']['raw']['answer'] = True
        with self.assertRaises(ValueError): M.categorical_organization(s)
        checker = M.Protocol({}); node = {'op': 'read', 'resource': 'absent'}
        checker.budget = 60
        with self.assertRaises(ValueError): checker.infer(node)

    def test_executed_tally_table_and_provenance_conserve_every_record(self):
        s = organization_spec(); result = M.Protocol(s['resources']).infer(s['options'][3]['plan'])[0]
        self.assertEqual(result.result, ((('short',), 2), (('medium',), 0), (('long',), 1)))
        self.assertEqual(len(result.records), 3)
        self.assertEqual(result.trace, (('resource', 'raw'),
            ('group_count', (('short',), ('medium',), ('long',))), ('tabulate',)))
        for values in ([], ['short'], ['long']*10, ['short', 'medium', 'long', 'long']):
            s['resources']['raw']['values'] = values
            result = M.Protocol(s['resources']).infer(s['options'][3]['plan'])[0]
            self.assertEqual(sum(count for _, count in result.result), len(values))
            self.assertEqual(tuple(count for _, count in result.result), tuple(values.count(c) for c in ('short', 'medium', 'long')))
            self.assertEqual(M.categorical_organization(s), 'frequency table')

    def test_unknown_record_is_never_dropped_from_tally(self):
        for value in ('unknown', True, 1):
            s = organization_spec(); s['resources']['raw']['values'].append(value)
            with self.subTest(value=value), self.assertRaises(ValueError): M.categorical_organization(s)

    def test_argmin_is_actually_computed_and_ties_are_retained(self):
        s = organization_spec(); s['resources']['chart']['values'] = {'short': 4, 'medium': 1, 'long': 1}
        result = M.Protocol(s['resources']).infer(s['options'][2]['plan'])[0]
        self.assertEqual(result.result, ('medium', 'long'))
        s['resources']['chart']['values']['medium'] = True
        with self.assertRaises(ValueError): M.categorical_organization(s)


if __name__ == '__main__': unittest.main()
