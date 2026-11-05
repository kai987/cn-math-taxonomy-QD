"""Independent counterexamples, complete trees and modal evidence regressions."""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import models_applications_33 as M


def tree_spec():
    coin={'op':'finite_outcomes','values':['H','T']}
    die={'op':'finite_outcomes','values':['d1','d2','d3','d4','d5','d6']}
    return {'kind':'app33_three_component_tree','components':3,'combination_semantics':'all_factor_combinations',
        'options':[
         {'key':'a','text':'coins','experiment':{'op':'repeat','count':3,'trial':coin}},
         {'key':'b','text':'dice','experiment':{'op':'simultaneous_product','factors':[die,die]}},
         {'key':'c','text':'coin and die','experiment':{'op':'sequential_product','factors':[coin,die]}},
         {'key':'d','text':'replaced balls','experiment':{'op':'repeat','count':2,'trial':{'op':'draw_with_replacement','population':['r','b']}}}]}


def axis_spec():
    return {'kind':'app33_proportional_axis','domain':'all_nonnegative_values','encoding':'upright_bar_height',
        'requirement':'preserve_all_value_ratios','options':[
         {'key':'a','text':'arbitrary start','rule':{'family':'arbitrary_origin_positive_scale',
             'witness':{'scale':2,'baseline':1,'values':[2,3]}}},
         {'key':'b','text':'nonuniform spacing','rule':{'family':'unequal_physical_spacing_per_equal_value_difference',
             'witness':{'knots':[[0,0],[1,1],[2,3]],'values':[1,2]}}},
         {'key':'c','text':'zero uniform','rule':{'family':'uniform_positive_scale','baseline':0}}]}


def evidence_spec(n=100,k=46,first='A',second='B'):
    return {'kind':'app33_fair_game_evidence',
        'ideal':{'outcomes':[{'player':first,'weight':1},{'player':second,'weight':1}],
                 'probabilities_knowledge':'ideal_single_trial_only'},
        'observed':{'total':n,'counts':[{'player':first,'count':k},{'player':second,'count':n-k}],
                    'actual_joint_law':'not_specified'},
        'goal':{'op':'equal','players':[first,second],'quantity':'single_trial_win_probability'},
        'options':[
         {'key':'a','text':'certain unfairness','claim':{'op':'forced_by_counts','conclusion':{'op':'unequal_probabilities'}}},
         {'key':'b','text':'invalid and redesign','claim':{'op':'forced_by_counts','conclusion':{'op':'invalid_recording_and_redesign'}}},
         {'key':'c','text':'compatible and conditional concentration','claim':{'op':'all','claims':[
             {'op':'compatible_with_ideal'},
             {'op':'not_forced_by_counts','conclusion':{'op':'unequal_probabilities'}},
             {'op':'iid_frequency_concentrates','law':'future_same_condition_iid','center':'1/2'},
             {'op':'no_stepwise_closeness_guarantee','law':'future_same_condition_iid','center':'1/2'}]}},
         {'key':'d','text':'favor first','claim':{'op':'recommend_strict_advantage_from_counts','greater':first,'less':second,
                                             'target':'equal_single_trial_chances'}}]}


class TreeEnumerationTests(unittest.TestCase):
    def test_exact_full_outcomes_and_prefix_tree_paths(self):
        s=tree_spec();self.assertEqual(M.three_component_tree(s),'coins')
        results=[M.experiment_tree(o['experiment']) for o in s['options']]
        self.assertEqual([len(r['outcomes']) for r in results],[8,36,12,4])
        for result in results:self.assertEqual(set(result['paths']),set(result['outcomes']))
        self.assertEqual(set(results[0]['paths']),{(a,b,c) for a in ('H','T') for b in ('H','T') for c in ('H','T')})

    def test_three_factor_selection_is_not_bound_to_coins_or_option_key(self):
        s=tree_spec();s['options'][0]['experiment']['count']=2
        die=s['options'][1]['experiment']['factors'][0]
        s['options'][1]['experiment']['factors'].append(deepcopy(die))
        s['options'].reverse();self.assertEqual(M.three_component_tree(s),'dice')

    def test_outcome_order_is_record_order_not_a_claim_of_temporal_order(self):
        experiment={'op':'simultaneous_product','factors':[
            {'op':'finite_outcomes','values':['left0','left1']},
            {'op':'finite_outcomes','values':['right0','right1','right2']}]}
        result=M.experiment_tree(experiment)
        self.assertEqual(result['components'],2);self.assertEqual(len(result['paths']),6)
        self.assertTrue(all(path[0].startswith('left') and path[1].startswith('right') for path in result['paths']))

    def test_replacement_bag_size_and_unequal_branch_factors_are_parameters(self):
        for population in (['only'],['a','b','c']):
            s=tree_spec();s['options'][3]['experiment']['trial']['population']=population
            self.assertEqual(M.three_component_tree(s),'coins')
            self.assertEqual(len(M.experiment_tree(s['options'][3]['experiment'])['outcomes']),len(population)**2)
        result=M.experiment_tree({'op':'sequential_product','factors':[
            {'op':'finite_outcomes','values':['x']},{'op':'finite_outcomes','values':['a','b']},
            {'op':'finite_outcomes','values':['q','r','s']}]})
        self.assertEqual(len(result['paths']),6)

    def test_no_pretend_probabilistic_independence_or_unknown_fields(self):
        s=tree_spec();s['combination_semantics']='uniform_marginals_imply_independence'
        with self.assertRaises(ValueError):M.three_component_tree(s)
        s=tree_spec();s['options'][1]['condition']='unverified'
        with self.assertRaises(ValueError):M.three_component_tree(s)
        s=tree_spec();s['options'][1]['experiment']['op']='unknown'
        with self.assertRaises(ValueError):M.three_component_tree(s)

    def test_invalid_duplicate_or_unknown_outcome_cannot_be_silently_dropped(self):
        for values in ([],['H','H'],['H',True],['a','__bad__']):
            s=tree_spec();s['options'][0]['experiment']['trial']['values']=values
            with self.subTest(values=values),self.assertRaises(ValueError):M.three_component_tree(s)
        for count in (True,0,3.0,'3²','③','3。0'):
            s=tree_spec();s['options'][0]['experiment']['count']=count
            with self.subTest(count=count),self.assertRaises(ValueError):M.three_component_tree(s)

    def test_missing_and_duplicate_satisfying_experiments_fail_closed(self):
        s=tree_spec();s['options']=s['options'][1:]
        with self.assertRaises(ValueError):M.three_component_tree(s)
        s=tree_spec();s['options'][2]['experiment']=deepcopy(s['options'][0]['experiment'])
        with self.assertRaises(ValueError):M.three_component_tree(s)


class ProportionalCalibrationTests(unittest.TestCase):
    def test_symbolic_zero_origin_guarantee_and_legal_counterexamples(self):
        s=axis_spec();self.assertEqual(M.proportional_axis(s),'zero uniform')
        s['options'].reverse();self.assertEqual(M.proportional_axis(s),'zero uniform')
        self.assertTrue(M._calibration_guarantee({'family':'uniform_positive_scale','baseline':'0/7'}))
        for baseline in ('1/3',-2,100):
            self.assertFalse(M._calibration_guarantee({'family':'uniform_positive_scale','baseline':baseline}))

    def test_arbitrary_origin_counterexamples_need_positive_display_heights(self):
        for scale,baseline,values in [('1/7',2,[3,9]),(10,-1,[1,2])]:
            rule={'family':'arbitrary_origin_positive_scale','witness':{'scale':scale,'baseline':baseline,'values':values}}
            self.assertFalse(M._calibration_guarantee(rule))
        for scale,baseline,values in [(0,1,[2,3]),(-1,1,[2,3]),(1,0,[1,2]),(1,2,[1,3]),(1,1,[2,2])]:
            s=axis_spec();s['options'][0]['rule']['witness'].update(scale=scale,baseline=baseline,values=values)
            with self.subTest(values=values,baseline=baseline),self.assertRaises(ValueError):M.proportional_axis(s)

    def test_piecewise_physical_units_are_computed_not_treated_as_a_label(self):
        s=axis_spec();s['options'][1]['rule']['witness']={'knots':[[0,0],[2,4],[3,5]],'values':[1,3]}
        self.assertEqual(M.proportional_axis(s),'zero uniform')
        rows,height=M._piecewise([[0,0],[1,1],[2,3]])
        self.assertEqual((height(Fraction(1,2)),height(1),height(2),height(3)),(Fraction(1,2),1,3,5))
        # Different numeric tick gaps with equal physical units is a valid
        # uniform scale, not a legal witness to the nonuniform candidate.
        s=axis_spec();s['options'][1]['rule']['witness']['knots']=[[0,0],[1,2],[3,6]]
        with self.assertRaises(ValueError):M.proportional_axis(s)

    def test_nonuniform_witness_must_really_violate_its_displayed_ratio(self):
        s=axis_spec();s['options'][1]['rule']['witness']['values']=['1/4','1/2']
        with self.assertRaises(ValueError):M.proportional_axis(s)
        for knots in ([[0,0],[1,1],[1,2]],[[0,0],[1,2],[2,1]],[[0,1],[1,2],[2,4]]):
            s=axis_spec();s['options'][1]['rule']['witness']['knots']=knots
            with self.subTest(knots=knots),self.assertRaises(ValueError):M.proportional_axis(s)

    def test_goal_scope_missing_unknown_or_extra_conditions_fail_closed(self):
        for key in ('domain','encoding','requirement'):
            s=axis_spec();s[key]='unspecified'
            with self.subTest(key=key),self.assertRaises(ValueError):M.proportional_axis(s)
        for index in range(3):
            s=axis_spec();s['options'][index]['condition']='extra'
            with self.subTest(index=index),self.assertRaises(ValueError):M.proportional_axis(s)
        s=axis_spec();s['options'][0]['rule']['family']='unknown'
        with self.assertRaises(ValueError):M.proportional_axis(s)

    def test_missing_duplicate_and_unicode_numeric_calibrations_fail_closed(self):
        s=axis_spec();s['options'][2]['rule']['baseline']=1
        with self.assertRaises(ValueError):M.proportional_axis(s)
        s=axis_spec();s['options'][0]['rule']=deepcopy(s['options'][2]['rule'])
        with self.assertRaises(ValueError):M.proportional_axis(s)
        s=axis_spec();s['options'][2]['rule']['baseline']='０'
        self.assertEqual(M.proportional_axis(s),'zero uniform')
        for bad in ('⁰','⓪','0。0','0 0','0/０',False):
            s=axis_spec();s['options'][2]['rule']['baseline']=bad
            with self.subTest(bad=bad),self.assertRaises(ValueError):M.proportional_axis(s)


class FiniteGameEvidenceTests(unittest.TestCase):
    def test_actual_100_46_modal_claims_are_computed_from_a_valid_fair_world(self):
        s=evidence_spec();self.assertEqual(M.fair_game_evidence(s),'compatible and conditional concentration')
        proof=M.FairEvidence(s['ideal'],s['observed'],s['goal'])
        self.assertTrue(proof.record_valid);self.assertEqual(len(proof.trace),100)
        self.assertGreater(proof.path_probability,0)
        self.assertEqual(proof.count_probability,Fraction(__import__('math').comb(100,46),2**100))
        self.assertEqual([proof.claim(o['claim']) for o in s['options']],[False,False,True,False])

    def test_all_finite_counts_are_logically_compatible_not_all_statistically_typical(self):
        for n,k in ((1,0),(1,1),(2,1),(10,0),(10,10),(20,7),(400,177)):
            s=evidence_spec(n,k)
            self.assertEqual(M.fair_game_evidence(s),'compatible and conditional concentration')
            proof=M.FairEvidence(s['ideal'],s['observed'],s['goal'])
            self.assertGreater(proof.count_probability,0)
        # Tiny positive likelihood proves compatibility only: it is not
        # declared common, nonsignificant or free of contrary evidence.
        s=evidence_spec(100,100);p=M.FairEvidence(s['ideal'],s['observed'],s['goal'])
        self.assertLess(p.count_probability,Fraction(1,10**12))

    def test_labels_weight_units_counts_order_and_option_order_are_irrelevant(self):
        s=evidence_spec(17,4,'甲','乙');s['options'].reverse();s['observed']['counts'].reverse();s['goal']['players'].reverse()
        for row in s['ideal']['outcomes']:row['weight']='7/3'
        self.assertEqual(M.fair_game_evidence(s),'compatible and conditional concentration')
        s['ideal']['outcomes'].reverse();self.assertEqual(M.fair_game_evidence(s),'compatible and conditional concentration')

    def test_current_actual_independence_is_not_assumed_from_uniform_marginals(self):
        s=evidence_spec();s['observed']['actual_joint_law']='known_iid'
        with self.assertRaises(ValueError):M.fair_game_evidence(s)
        s=evidence_spec();s['ideal']['probabilities_knowledge']='actual_iid_guaranteed'
        with self.assertRaises(ValueError):M.fair_game_evidence(s)
        s=evidence_spec();s['options'][2]['claim']['claims'][2]['law']='actual_trials_iid'
        with self.assertRaises(ValueError):M.fair_game_evidence(s)

    def test_unequal_ideal_probabilities_and_compensation_goals_are_not_silently_mixed(self):
        s=evidence_spec();s['ideal']['outcomes'][0]['weight']=2
        with self.assertRaises(ValueError):M.fair_game_evidence(s)
        s=evidence_spec();s['goal']['quantity']='equal_total_historical_winnings'
        with self.assertRaises(ValueError):M.fair_game_evidence(s)
        s=evidence_spec();s['options'][3]['claim']['target']='compensate_previous_losses'
        with self.assertRaises(ValueError):M.fair_game_evidence(s)

    def test_missing_counts_negative_counts_wrong_total_duplicate_labels_and_unknown_events_fail(self):
        mutations=[lambda s:s['observed']['counts'][0].update(count=-1),
                   lambda s:s['observed'].update(total=99),
                   lambda s:s['observed']['counts'].pop(),
                   lambda s:s['observed']['counts'][1].update(player='A'),
                   lambda s:s['observed']['counts'][1].update(player='C')]
        for mutate in mutations:
            s=evidence_spec();mutate(s)
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):M.fair_game_evidence(s)

    def test_future_concentration_center_and_nonmonotonic_witness_are_exact(self):
        s=evidence_spec();p=M.FairEvidence(s['ideal'],s['observed'],s['goal'])
        self.assertEqual(p.variance_coefficient,Fraction(1,4));self.assertEqual(p.witness,(2,1,Fraction(1,6)))
        self.assertTrue(p.nonmonotone)
        s['options'][2]['claim']['claims'][2]['center']='0.500000000001'
        with self.assertRaises(ValueError):M.fair_game_evidence(s)

    def test_unknown_fields_claims_and_late_conjunction_terms_fail_even_when_already_false(self):
        for index in range(4):
            s=evidence_spec();s['options'][index]['condition']='unknown'
            with self.subTest(index=index),self.assertRaises(ValueError):M.fair_game_evidence(s)
        s=evidence_spec();s['options'][0]['claim']['conclusion']['op']='unproved'
        with self.assertRaises(ValueError):M.fair_game_evidence(s)
        s=evidence_spec();s['options'][0]['claim']={'op':'all','claims':[s['options'][0]['claim'],{'op':'unknown'}]}
        with self.assertRaises(ValueError):M.fair_game_evidence(s)
        s=evidence_spec();s['options'][3]['claim']['greater']='B'
        with self.assertRaises(ValueError):M.fair_game_evidence(s)

    def test_duplicate_and_missing_complete_conclusion_do_not_select_first(self):
        s=evidence_spec();s['options'][0]['claim']=deepcopy(s['options'][2]['claim'])
        with self.assertRaises(ValueError):M.fair_game_evidence(s)
        s=evidence_spec();s['options']=s['options'][:2]+s['options'][3:]
        with self.assertRaises(ValueError):M.fair_game_evidence(s)

    def test_unicode_and_original_numeric_domains_are_not_normalized_into_wrong_inputs(self):
        s=evidence_spec();s['observed']['total']='１００';s['observed']['counts'][0]['count']='４６'
        self.assertEqual(M.fair_game_evidence(s),'compatible and conditional concentration')
        for bad in ('10²','①⓪⓪','100。0','1 00','100/0',True,'-100'):
            s=evidence_spec();s['observed']['total']=bad
            with self.subTest(bad=bad),self.assertRaises(ValueError):M.fair_game_evidence(s)

    def test_claim_tree_budget_is_bounded_and_required_premises_are_not_defaults(self):
        s=evidence_spec();node=s['options'][2]['claim']
        for _ in range(90):node={'op':'all','claims':[node]}
        s['options'][2]['claim']=node
        with self.assertRaises(ValueError):M.fair_game_evidence(s)
        for field in ('goal','ideal','observed'):
            s=evidence_spec();del s[field]
            with self.subTest(field=field),self.assertRaises(ValueError):M.fair_game_evidence(s)


if __name__=='__main__':unittest.main()
