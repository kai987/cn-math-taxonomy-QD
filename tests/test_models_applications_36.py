"""Exact whole-reference, trial execution and adversarial spinner regressions."""
from copy import deepcopy
from fractions import Fraction
from itertools import product
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import models_applications_36 as M
from model_types import SelfReferenceProof, TextProof
from verify_questions import compare_self_reference


REFERENCE = ('把均匀转盘分为两个相等的180°扇区，分别标甲、乙。'
    '指针落在哪一区就由对应的人获胜，落在边界则重转，双方奖励和失败代价相同。'
    '在指针停止方向均匀的理想模型下，两人获胜概率都为180°/360°=1/2，所以理论上公平。'
    '可做大量同条件独立试验，记录甲、乙胜次并计算频率，以观察是否在1/2附近波动。'
    '试验只能提供经验依据，有限次频率接近1/2不能证明公平，也不保证每增加一次试验都更接近1/2。')


def spinner_spec(first='甲', second='乙'):
    return {'kind': 'app36_spinner_reference', 'reference_only': True,
        'spinner': {'radius': 1, 'angle_unit': 'degree',
            'law': {'kind': 'uniform_continuous_angle', 'start': 0, 'period': 360},
            'sectors': [{'start': 0, 'end': 180, 'winner': first}, {'start': 180, 'end': 360, 'winner': second}],
            'boundary': 'respin'},
        'payoffs': [{'player': first, 'win_reward': 1, 'loss_cost': 1},
                    {'player': second, 'win_reward': 1, 'loss_cost': 1}],
        'trial_protocol': {'sampling': {'op': 'product_law', 'base': 'spinner', 'conditions': 'fixed'},
            'record': {'op': 'count', 'input': {'op': 'winner_events'}},
            'report': {'op': 'divide', 'numerator': {'op': 'counts'},
                'denominator': {'op': 'length', 'input': {'op': 'winner_events'}}}}}


class SpinnerGeometryTests(unittest.TestCase):
    def test_complete_reference_and_exact_probabilities_expectations(self):
        proof = M.spinner_reference(spinner_spec())
        self.assertIsInstance(proof, SelfReferenceProof)
        self.assertEqual(proof.probabilities, {'乙': Fraction(1,2), '甲': Fraction(1,2)})
        self.assertEqual(proof.expectations, {'乙': 0, '甲': 0})
        self.assertTrue(proof.matches(REFERENCE))

    def test_interval_and_payoff_order_does_not_return_a_stored_option(self):
        s = spinner_spec(); s['spinner']['sectors'].reverse(); s['payoffs'].reverse()
        self.assertTrue(M.spinner_reference(s).matches(REFERENCE))
        sentences = REFERENCE[:-1].split('。')
        self.assertTrue(M.spinner_reference(s).matches('。'.join(reversed(sentences))+'。'))

    def test_positive_radius_and_common_payoff_parameters_do_not_change_probability(self):
        for radius, reward, cost in [('7/3', '5/2', '1/7'), ('0.01', 0, 0), (1000, 17, 3)]:
            s = spinner_spec(); s['spinner']['radius'] = radius
            for row in s['payoffs']: row.update(win_reward=reward, loss_cost=cost)
            proof = M.spinner_reference(s)
            self.assertTrue(proof.matches(REFERENCE))
            self.assertEqual(len(set(proof.expectations.values())), 1)

    def test_labels_are_parameters_not_answer_identity(self):
        proof = M.spinner_reference(spinner_spec('A', 'B'))
        self.assertTrue(proof.matches(REFERENCE.replace('甲','A').replace('乙','B')))
        self.assertFalse(proof.matches(REFERENCE))
        self.assertTrue(M.spinner_reference(spinner_spec('乙','甲')).matches(REFERENCE))

    def test_rotated_semicircles_crossing_zero_are_still_two_connected_sectors(self):
        s = spinner_spec(); s['spinner']['sectors'] = [
            {'start': 270, 'end': 360, 'winner': '甲'},
            {'start': 0, 'end': 90, 'winner': '甲'},
            {'start': 90, 'end': 270, 'winner': '乙'}]
        self.assertTrue(M.spinner_reference(s).matches(REFERENCE))

    def test_equal_mass_disconnected_regions_are_not_two_semicircular_sectors(self):
        s = spinner_spec(); s['spinner']['sectors'] = [
            {'start': 0, 'end': 90, 'winner': '甲'}, {'start': 90, 'end': 180, 'winner': '乙'},
            {'start': 180, 'end': 270, 'winner': '甲'}, {'start': 270, 'end': 360, 'winner': '乙'}]
        proof = M.spinner_reference(s)
        self.assertEqual(proof.probabilities['甲'], Fraction(1,2))
        self.assertFalse(proof.matches(REFERENCE))

    def test_unequal_angles_boundary_rule_and_payoffs_invalidate_the_reference(self):
        s = spinner_spec(); s['spinner']['sectors'][0]['end'] = 120; s['spinner']['sectors'][1]['start'] = 120
        self.assertFalse(M.spinner_reference(s).matches(REFERENCE))
        s = spinner_spec(); s['spinner']['boundary'] = 'assign_clockwise'
        self.assertFalse(M.spinner_reference(s).matches(REFERENCE))
        s = spinner_spec(); s['payoffs'][0]['win_reward'] = 2
        self.assertFalse(M.spinner_reference(s).matches(REFERENCE))

    def test_overlaps_gaps_zero_sectors_and_third_or_duplicate_players_fail_closed(self):
        mutations = [lambda s: s['spinner']['sectors'][1].update(start=179),
            lambda s: s['spinner']['sectors'][1].update(start=181),
            lambda s: s['spinner']['sectors'][0].update(end=0),
            lambda s: s['spinner']['sectors'][1].update(end=359),
            lambda s: s['spinner']['sectors'][1].update(winner='甲'),
            lambda s: s['payoffs'][1].update(player='甲')]
        for mutate in mutations:
            s = spinner_spec(); mutate(s)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError): M.spinner_reference(s)

    def test_explicit_uniform_continuity_and_reference_contract_are_required(self):
        for flag in (False, 1, 'true', None):
            s = spinner_spec(); s['reference_only'] = flag
            with self.subTest(flag=flag), self.assertRaises(ValueError): M.spinner_reference(s)
        for law in ({'kind':'discrete_atoms','start':0,'period':360}, {'kind':'uniform_continuous_angle','start':0,'period':180}):
            s = spinner_spec(); s['spinner']['law'] = law
            with self.subTest(law=law), self.assertRaises(ValueError): M.spinner_reference(s)
        for field in ('law', 'boundary'):
            s = spinner_spec(); del s['spinner'][field]
            with self.subTest(field=field), self.assertRaises(ValueError): M.spinner_reference(s)
        s = spinner_spec(); s['spinner']['boundary'] = 'unknown'
        with self.assertRaises(ValueError): M.spinner_reference(s)

    def test_nonpositive_radius_negative_payoff_and_extra_truth_flags_fail(self):
        for value in (0, -1, True, '1。5', '¹', '①'):
            s = spinner_spec(); s['spinner']['radius'] = value
            with self.subTest(value=value), self.assertRaises(ValueError): M.spinner_reference(s)
        s = spinner_spec(); s['payoffs'][0]['loss_cost'] = -1
        with self.assertRaises(ValueError): M.spinner_reference(s)
        s = spinner_spec(); s['fair'] = True
        with self.assertRaises(ValueError): M.spinner_reference(s)


class TrialEvidenceTests(unittest.TestCase):
    def test_protocol_really_counts_every_trial_and_divides_by_its_length(self):
        proof = M.spinner_reference(spinner_spec())
        result = proof.run(['甲', '乙', '甲', '甲'])
        self.assertEqual(result, {'counts': {'乙':1,'甲':3}, 'trials':4,
            'frequencies': {'乙':Fraction(1,4),'甲':Fraction(3,4)}})
        self.assertEqual(proof.run(['甲'])['counts']['乙'], 0)

    def test_all_short_paths_have_exact_normalized_frequencies_and_two_positive_likelihoods(self):
        proof = M.spinner_reference(spinner_spec())
        for n in range(1,6):
            total = total_alt = Fraction(0)
            for path in product(proof.owners, repeat=n):
                result = proof.run(path)
                self.assertEqual(sum(result['counts'].values()), n)
                self.assertEqual(sum(result['frequencies'].values()), 1)
                likelihood, alternative = proof.likelihood(path), proof.likelihood(path, True)
                self.assertGreater(likelihood, 0); self.assertGreater(alternative, 0)
                total += likelihood; total_alt += alternative
            self.assertEqual(total, 1); self.assertEqual(total_alt, 1)

    def test_iid_variance_is_an_exact_all_n_identity(self):
        proof = M.spinner_reference(spinner_spec())
        self.assertEqual(proof.variance_coefficient, Fraction(1,4))
        for n in (1,2,100,1000000):
            self.assertEqual(proof.variance_coefficient/Fraction(n), Fraction(1,4*n))
        self.assertLess(proof.variance_coefficient/1000, proof.variance_coefficient/100)

    def test_alternative_is_a_legal_biased_angular_density_not_an_unsupported_verdict(self):
        proof = M.spinner_reference(spinner_spec())
        self.assertTrue(proof.finite_nonidentification)
        self.assertEqual(sum(proof.alternative_densities[o]*proof.angles[o] for o in proof.owners), 1)
        self.assertTrue(all(v > 0 for v in proof.alternative_densities.values()))
        self.assertNotEqual(proof.alternative, proof.probabilities)
        self.assertGreater(proof.likelihood(['甲']*50 + ['乙']*50, True), 0)

    def test_nonmonotone_witness_is_a_legal_positive_probability_path(self):
        proof = M.spinner_reference(spinner_spec()); witness = proof.nonmonotone_witness
        self.assertEqual(witness['before'], 0); self.assertEqual(witness['after'], Fraction(1,6))
        self.assertEqual(proof.likelihood(witness['path']), witness['probability'])
        self.assertGreater(witness['probability'], 0)

    def test_unknown_missing_outcomes_empty_data_and_wrong_joint_law_do_not_get_dropped(self):
        proof = M.spinner_reference(spinner_spec())
        for path in ([], ['unknown'], ['甲',None], ['乙',True], '甲乙'):
            with self.subTest(path=path), self.assertRaises(ValueError): proof.run(path)
        s = spinner_spec(); s['trial_protocol']['sampling']['op'] = 'dependent_repeats'
        with self.assertRaises(ValueError): M.spinner_reference(s)
        s = spinner_spec(); s['trial_protocol']['sampling']['conditions'] = 'changing'
        with self.assertRaises(ValueError): M.spinner_reference(s)

    def test_incomplete_recording_unknown_operator_or_wrong_denominator_fail_closed(self):
        mutations = [lambda t: t['record'].update(op='guess'),
            lambda t: t['record']['input'].update(op='only_first_wins'),
            lambda t: t['report'].update(denominator={'op':'fixed_number','value':100}),
            lambda t: t['report'].update(numerator={'op':'expected_counts'}),
            lambda t: t.pop('sampling')]
        for mutate in mutations:
            s = spinner_spec(); mutate(s['trial_protocol'])
            with self.subTest(mutate=mutate), self.assertRaises(ValueError): M.spinner_reference(s)


class WholeReferenceTests(unittest.TestCase):
    def test_missing_duplicate_or_additional_claim_is_not_partially_matched(self):
        proof = M.spinner_reference(spinner_spec()); parts = REFERENCE[:-1].split('。')
        for i in range(5):
            self.assertFalse(proof.matches('。'.join(parts[:i]+parts[i+1:])+'。'))
            changed = parts[:]; changed[i] = parts[(i+1)%5]
            self.assertFalse(proof.matches('。'.join(changed)+'。'))
        for extra in ('游戏永远甲乙交替获胜。', '所以每100次都恰好各胜50次。', '试验已经证明绝对公平。'):
            self.assertFalse(proof.matches(REFERENCE+extra))
            self.assertFalse(proof.matches(REFERENCE[:-1]+'，'+extra))

    def test_each_quantitative_and_object_claim_is_checked(self):
        proof = M.spinner_reference(spinner_spec())
        for bad in (REFERENCE.replace('180','90'), REFERENCE.replace('360','180'),
                    REFERENCE.replace('1/2','1/3'), REFERENCE.replace('甲、乙','甲、甲'),
                    REFERENCE.replace('甲、乙','甲、丙')):
            self.assertFalse(proof.matches(bad))
        self.assertFalse(proof.matches(REFERENCE.replace('都为180°/360°=1/2','都为180°/360°=0.5001')))

    def test_every_condition_and_negation_is_consumed(self):
        proof = M.spinner_reference(spinner_spec())
        replacements = [('落在边界则重转','落在边界则甲胜'),('双方奖励和失败代价相同','双方奖励相同'),
            ('同条件独立试验','同条件试验'),('停止方向均匀','停止方向不均匀'),
            ('有限次频率接近1/2不能证明公平','有限次频率接近1/2能证明公平'),
            ('不保证每增加一次试验都更接近1/2','保证每增加一次试验都更接近1/2')]
        for before, after in replacements:
            with self.subTest(before=before): self.assertFalse(proof.matches(REFERENCE.replace(before, after)))

    def test_approved_fullwidth_typography_is_not_general_nfkc(self):
        proof = M.spinner_reference(spinner_spec())
        text = REFERENCE.translate(str.maketrans('0123456789/', '０１２３４５６７８９／'))
        self.assertTrue(proof.matches(text))
        self.assertTrue(proof.matches(REFERENCE.replace('180°','180.0°')))
        for bad in ('¹⁸⁰', '①⑧⓪', '١٨٠', '1 80', '1。80', '180..0', '180e0', '１８⁰'):
            with self.subTest(bad=bad): self.assertFalse(proof.matches(REFERENCE.replace('180', bad)))
        for bad in ('１²/２', '1／②', '1。0/2', '1 / 2', '1/０'):
            with self.subTest(bad=bad): self.assertFalse(proof.matches(REFERENCE.replace('1/2', bad)))

    def test_exact_reference_integration_does_not_grade_student_free_text(self):
        proof = M.spinner_reference(spinner_spec())
        q = {'type':'self','id':'test','answer':REFERENCE}
        self.assertTrue(compare_self_reference(q, proof)[0])
        for wrong in ('各180度，多做试验', '100次各50胜就证明公平', REFERENCE+'另一个断言。'):
            self.assertFalse(compare_self_reference(dict(q, answer=wrong), proof)[0])
        self.assertFalse(compare_self_reference(q, TextProof(REFERENCE))[0])



def action_spec():
    encode = {'relation':'reversible_encoding','inputs':['observations'],'output':'representation'}
    infer = {'relation':'entailed_assertion','inputs':['observations','representation'],'output':'proposition'}
    propose = {'relation':'depends_on_assertion','inputs':['proposition'],'output':'prescription'}
    group = {'relation':'partition_aggregate','inputs':['observations'],'output':'frequency_table'}
    collect = {'relation':'new_observations','inputs':['instrument'],'output':'observations'}
    return {'kind':'app36_statistical_action_signatures',
        'records':[{'day':'Mon','hours':7},{'day':'Tue','hours':6},{'day':'Wed','hours':8}],
        'actions':[
            {'op':'line_plot','input':{'op':'observed_rows'},'scale':2,'offset':1},
            {'op':'argmin','input':{'op':'previous','index':0}},
            {'op':'propose','input':{'op':'previous','index':1},'action':'review_routine',
                'targets':{'op':'claim_subjects'}}],
        'options':[{'key':'a','text':'first','signatures':[encode,infer,propose]},
                   {'key':'b','text':'second','signatures':[group,encode,infer]},
                   {'key':'c','text':'third','signatures':[infer,encode,collect]}]}


class StatisticalActionTests(unittest.TestCase):
    def test_every_action_is_executed_before_matching_typed_definition(self):
        s = action_spec(); self.assertEqual(M.statistical_action_signatures(s),'first')
        execution = M.StatisticalActions(s['records'])
        results = [execution.step(node) for node in s['actions']]
        self.assertEqual(results[0].payload,((0,15),(1,13),(2,17)))
        self.assertEqual(results[1].payload,(('Tue',),6))
        self.assertEqual(results[2].payload,('review_routine',('Tue',)))
        self.assertIs(results[1].basis,results[0]); self.assertIs(results[2].basis,results[1])

    def test_arbitrary_positive_scales_offsets_record_order_and_all_ties(self):
        for records in ([{'day':'A','hours':'1/2'}],
                        [{'day':'B','hours':8},{'day':'A','hours':8}],
                        [{'day':'C','hours':9},{'day':'A','hours':'13/2'},{'day':'B','hours':'13/2'}]):
            for scale, offset in (('1/3',-10),(7,'2/5')):
                s = action_spec(); s['records'] = records; s['actions'][0].update(scale=scale,offset=offset)
                self.assertEqual(M.statistical_action_signatures(s),'first')
                execution = M.StatisticalActions(records)
                results = [execution.step(node) for node in s['actions']]
                minimum = min(Fraction(r['hours']) for r in records)
                subjects = tuple(r['day'] for r in records if Fraction(r['hours']) == minimum)
                self.assertEqual(results[1].payload,(subjects,minimum))
                self.assertEqual(results[2].payload[1],subjects)

    def test_candidate_order_keys_text_and_definition_input_order_are_irrelevant(self):
        s = action_spec(); s['options'].reverse()
        for i, option in enumerate(s['options']): option.update(key=str(i),text='choice'+str(i))
        for option in s['options']:
            for signature in option['signatures']: signature['inputs'].reverse()
        self.assertEqual(M.statistical_action_signatures(s),'choice2')

    def test_suggestion_contents_are_not_assigned_an_arbitrary_optimality_score(self):
        s = action_spec(); s['actions'][2]['action'] = 'discuss_with_teacher'
        self.assertEqual(M.statistical_action_signatures(s),'first')
        s['actions'][2]['must_be_optimal'] = True
        with self.assertRaises(ValueError): M.statistical_action_signatures(s)

    def test_argmin_and_advice_cannot_precede_their_required_artifacts(self):
        for actions in ([action_spec()['actions'][1]], [action_spec()['actions'][2]],
                        [action_spec()['actions'][0],action_spec()['actions'][2]]):
            s = action_spec(); s['actions'] = actions
            with self.subTest(actions=actions),self.assertRaises(ValueError): M.statistical_action_signatures(s)
        s = action_spec(); s['actions'][2]['input']['index'] = 0
        with self.assertRaises(ValueError): M.statistical_action_signatures(s)
        s = action_spec(); s['actions'][1]['input']['index'] = True
        with self.assertRaises(ValueError): M.statistical_action_signatures(s)

    def test_missing_or_unknown_measurements_days_and_units_fail_closed(self):
        for records in ([],[{'day':'A','hours':True}],[{'day':'A','hours':25}],
                        [{'day':'A','hours':-1}],[{'day':'A','hours':'unknown'}],
                        [{'day':'A','hours':3},{'day':'A','hours':4}],
                        [{'day':'A','hours':3,'unit':'minutes'}]):
            s = action_spec(); s['records'] = records
            with self.subTest(records=records),self.assertRaises(ValueError): M.statistical_action_signatures(s)

    def test_noninvertible_or_reverse_scale_is_not_silently_used_for_argmin(self):
        for scale in (0,-1,True,'¹','①','1。5'):
            s = action_spec(); s['actions'][0]['scale'] = scale
            with self.subTest(scale=scale),self.assertRaises(ValueError): M.statistical_action_signatures(s)

    def test_unknown_operation_even_in_valid_first_position_fails_closed(self):
        s = action_spec(); s['actions'][0]['op'] = 'pretend_description'
        with self.assertRaises(ValueError): M.statistical_action_signatures(s)
        s = action_spec(); s['actions'][1]['op'] = 'pick_one_minimizer'
        with self.assertRaises(ValueError): M.statistical_action_signatures(s)

    def test_proposal_targets_must_come_from_the_computed_claim(self):
        s = action_spec(); s['actions'][2]['targets'] = {'op':'fixed_days','value':['Wed']}
        with self.assertRaises(ValueError): M.statistical_action_signatures(s)

    def test_unknown_or_ill_typed_signature_in_rejected_candidate_is_not_called_false(self):
        s = action_spec(); s['options'][2]['signatures'][0]['relation'] = 'opinion'
        with self.assertRaises(ValueError): M.statistical_action_signatures(s)
        s = action_spec(); s['options'][2]['signatures'][0]['output'] = 'prescription'
        with self.assertRaises(ValueError): M.statistical_action_signatures(s)
        s = action_spec(); s['options'][2]['signatures'][0]['inputs'] = ['observations','observations']
        with self.assertRaises(ValueError): M.statistical_action_signatures(s)

    def test_missing_or_duplicate_complete_candidate_does_not_choose_first(self):
        s = action_spec(); s['options'] = s['options'][1:]
        with self.assertRaises(ValueError): M.statistical_action_signatures(s)
        s = action_spec(); extra = deepcopy(s['options'][0]); extra['key'] = 'extra'; s['options'].append(extra)
        with self.assertRaises(ValueError): M.statistical_action_signatures(s)
        s = action_spec(); s['options'][1]['signatures'].pop()
        with self.assertRaises(ValueError): M.statistical_action_signatures(s)

    def test_extra_candidate_conditions_are_rejected_even_on_nonmatching_options(self):
        for index in (0, 1, 2):
            s = action_spec(); s['options'][index]['condition'] = {'op':'unverified_extra_assertion'}
            with self.subTest(index=index), self.assertRaises(ValueError):
                M.statistical_action_signatures(s)


if __name__ == '__main__': unittest.main()
