"""Data-flow, real arithmetic, alternative paths and fail-closed regressions."""
from copy import deepcopy
from fractions import Fraction
from itertools import permutations
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import models_applications_25 as M


def report_spec():
    study={'population':'class','variable':'sleep_hours','unit':'hour','window':'weekday','value_domain':[0,24]}
    formulate={'op':'formulate','question':study};collect={'op':'collect'};organize={'op':'organize'}
    plot={'op':'encode_plot','input':'organized','scale':2,'offset':1}
    analyze={'op':'analyze','input':'plot'};report={'op':'report','action':'review_routine'}
    return {'kind':'app25_executable_survey_report','study':study,
        'world':{'schema':study,'potential_records':[{'id':'r1','value':7},{'id':'r2','value':6},{'id':'r3','value':8},{'id':'r4','value':6}]},
        'initial':{'question':None,'records':None},
        'options':[{'key':'A','text':'complete','program':[formulate,collect,organize,plot,analyze,report]},
                   {'key':'B','text':'collect before fields','program':[collect,formulate,organize,{'op':'analyze','input':'raw'},report]},
                   {'key':'C','text':'organize before data','program':[organize,collect,formulate,{'op':'analyze','input':'raw'},report]},
                   {'key':'D','text':'no data and no report','program':[formulate,organize,collect,{'op':'analyze','input':'raw'},
                       {'op':'encode_plot','input':'raw','scale':1,'offset':0}]}]}


def first_spec():
    spec=report_spec();spec['kind']='app25_executable_first_action'
    spec['options']=[{'key':'A','text':'formulate','action':deepcopy(spec['options'][0]['program'][0])},
                     {'key':'B','text':'plot','action':{'op':'encode_plot','input':'raw','scale':1,'offset':0}},
                     {'key':'C','text':'collect','action':{'op':'collect'}}]
    return spec


def runner(spec):return M.Survey(spec['study'],spec['world'],spec['initial'])


class ExecutableReportTests(unittest.TestCase):
    def test_all_original_actions_really_execute_and_report_references_analysis(self):
        s=report_spec();self.assertEqual(M.executable_report(s),'complete')
        p=runner(s);self.assertTrue(p.execute(s['options'][0]['program']))
        self.assertEqual(p.organized.frequencies,((6,2),(7,1),(8,1)))
        self.assertEqual(p.plot.points,((6,5),(7,3),(8,3)))
        self.assertEqual((p.analysis.size,p.analysis.mean,p.analysis.minimum,p.analysis.maximum),(4,Fraction(27,4),6,8))
        self.assertEqual(p.analysis.minimum_ids,('r2','r4'));self.assertIs(p.report.basis,p.analysis)
        self.assertEqual(p.report.targets,('r2','r4'));self.assertIs(p.report.basis.source,p.raw)

    def test_distinct_legal_short_paths_are_not_rejected_for_missing_named_stages(self):
        s=report_spec();formulate,collect,organize,plot,analyze,report=s['options'][0]['program']
        paths=[[formulate,collect,{'op':'analyze','input':'raw'},report],
               [formulate,collect,{'op':'encode_plot','input':'raw','scale':'1/3','offset':-8},analyze,report],
               [formulate,collect,organize,{'op':'analyze','input':'organized'},report],
               [formulate,collect,{'op':'analyze','input':'raw'},organize,report],
               [formulate,collect,formulate,{'op':'analyze','input':'raw'},report]]
        for path in paths:
            with self.subTest(path=path):self.assertTrue(runner(s).execute(path))
        extra={'key':'alternative','text':'short valid path','program':paths[0]};s['options'].append(extra)
        with self.assertRaises(ValueError):M.executable_report(s)

    def test_all_six_operation_permutations_follow_real_prerequisites_not_a_fixed_order_list(self):
        s=report_spec();actions=deepcopy(s['options'][0]['program'])
        actions[3]['input']='raw';actions[4]['input']='raw'
        accepted=0
        for path in permutations(actions):accepted+=runner(s).execute(list(path))
        # Formulate<collect; collection precedes the four data consumers;
        # analysis<report, while organize and raw plotting can vary freely.
        self.assertEqual(accepted,12)

    def test_arbitrary_record_values_multiplicity_units_and_chart_parameters(self):
        for values in ([0],[24],[7,7,7],[Fraction(1,2),Fraction(7,2),Fraction(1,2)],list(range(25))):
            for scale,offset in [('1/7',-10),(9,'2/3')]:
                s=report_spec();s['world']['potential_records']=[{'id':'id'+str(i),'value':str(v)} for i,v in enumerate(values)]
                s['options'][0]['program'][3].update(scale=scale,offset=offset)
                p=runner(s);self.assertTrue(p.execute(s['options'][0]['program']))
                self.assertEqual(p.analysis.mean,sum(values,Fraction(0))/len(values))
                self.assertEqual(sum(c for _,c in p.organized.frequencies),len(values))
                self.assertEqual(p.analysis.minimum_ids,tuple('id'+str(i) for i,v in enumerate(values) if v==min(values)))
        s=report_spec();s['study'].update(population='group',variable='temperature',unit='celsius',value_domain=[-5,5])
        s['world']['potential_records']=[{'id':'a','value':-2},{'id':'b','value':3}]
        self.assertEqual(M.executable_report(s),'complete')

    def test_success_is_independent_of_fixture_ids_nonempty_size_and_specific_measurements(self):
        for size,value in ((1,'0'),(9,'24'),(128,'13/7')):
            s=report_spec();s['world']['potential_records']=[{'id':'person'+str(i),'value':value} for i in reversed(range(size))]
            p=runner(s);self.assertTrue(p.execute(s['options'][0]['program']))
            self.assertEqual(p.analysis.mean,Fraction(value));self.assertEqual(p.analysis.minimum,Fraction(value))
            self.assertEqual(set(p.report.targets),{'person'+str(i) for i in range(size)})
            self.assertEqual(p.organized.frequencies,((Fraction(value),size),))
        s=report_spec();s['world']['potential_records']=[{'id':'r'+str(i),'value':1} for i in range(129)]
        with self.assertRaises(ValueError):M.executable_report(s) # verifier budget, not a population-size decision rule

    def test_empty_collection_and_counting_do_not_fabricate_an_analysis_or_report(self):
        s=report_spec();s['world']['potential_records']=[];p=runner(s)
        for op in s['options'][0]['program'][:3]:p.step(op)
        self.assertEqual(p.raw.rows,());self.assertEqual(p.organized.frequencies,())
        with self.assertRaises(M.MissingInformation):p.step({'op':'analyze','input':'raw'})
        with self.assertRaises(M.MissingInformation):p.step({'op':'encode_plot','input':'organized','scale':1,'offset':0})
        with self.assertRaises(M.MissingInformation):p.step({'op':'report','action':'discuss'})
        self.assertIsNone(p.analysis);self.assertIsNone(p.report)
        with self.assertRaises(ValueError):M.executable_report(s)

    def test_missing_research_fields_records_table_or_plot_block_their_consumers(self):
        s=report_spec()
        for node in ({'op':'collect'},{'op':'organize'}, {'op':'analyze','input':'raw'},
                     {'op':'analyze','input':'organized'},{'op':'analyze','input':'plot'},
                     {'op':'encode_plot','input':'raw','scale':1,'offset':0},{'op':'report','action':'review'}):
            with self.subTest(node=node),self.assertRaises(M.MissingInformation):runner(s).step(node)
        p=runner(s);p.step(s['options'][0]['program'][0]);p.step({'op':'collect'})
        with self.assertRaises(M.MissingInformation):p.step({'op':'analyze','input':'organized'})
        self.assertIsInstance(p.step({'op':'analyze','input':'raw'}),M.Analysis)

    def test_existing_data_support_analysis_before_formalization_and_report_after_formalization(self):
        s=report_spec();s['initial']['records']=deepcopy(s['world']['potential_records']);p=runner(s)
        p.step({'op':'analyze','input':'raw'})
        with self.assertRaises(M.MissingInformation):p.step({'op':'report','action':'review'})
        p.step(s['options'][0]['program'][0]);self.assertIsInstance(p.step({'op':'report','action':'review'}),M.Report)

    def test_new_collection_invalidates_old_derived_artifacts(self):
        s=report_spec();p=runner(s);self.assertTrue(p.execute(s['options'][0]['program']))
        old=p.raw;p.step({'op':'collect'})
        self.assertIsNot(old,p.raw)
        self.assertIsNone(p.organized);self.assertIsNone(p.plot);self.assertIsNone(p.analysis);self.assertIsNone(p.report)
        with self.assertRaises(M.MissingInformation):p.step({'op':'report','action':'review'})

    def test_unknown_later_step_is_rejected_even_after_a_known_missing_first_input(self):
        for bad in ({'op':'unknown'},{'op':'organize','claim':'extra'},
                    {'op':'analyze','input':'unknown'},{'op':'encode_plot','input':'raw','scale':0,'offset':0}):
            s=report_spec();s['options'][1]['program'].append(bad)
            with self.subTest(bad=bad),self.assertRaises(ValueError):M.executable_report(s)

    def test_extra_fields_at_every_candidate_and_nested_level_are_never_ignored(self):
        for i in range(4):
            s=report_spec();s['options'][i]['condition']='unverified'
            with self.subTest(i=i),self.assertRaises(ValueError):M.executable_report(s)
        s=report_spec();s['options'][0]['program'][0]['question']['condition']='extra'
        with self.assertRaises(ValueError):M.executable_report(s)
        s=report_spec();s['world']['potential_records'][0]['guess']='extra'
        with self.assertRaises(ValueError):M.executable_report(s)

    def test_record_ids_units_original_domains_and_numeric_lexing_are_checked(self):
        for bad in (True,'⁷','⑦','7。5','7 5','1/0',7.0,25,-1):
            s=report_spec();s['world']['potential_records'][0]['value']=bad
            with self.subTest(bad=bad),self.assertRaises(ValueError):M.executable_report(s)
        s=report_spec();s['world']['potential_records'][0]['value']='７'
        self.assertEqual(M.executable_report(s),'complete')
        s=report_spec();s['world']['potential_records'][1]['id']='r1'
        with self.assertRaises(ValueError):M.executable_report(s)
        s=report_spec();s['world']['schema']=deepcopy(s['study']);s['world']['schema']['unit']='minute'
        with self.assertRaises(ValueError):M.executable_report(s)
        s=report_spec();s['study']['value_domain']=[24,0]
        with self.assertRaises(ValueError):M.executable_report(s)

    def test_proposal_content_is_not_given_an_invented_utility_or_unique_bestness(self):
        s=report_spec();s['options'][0]['program'][-1]['action']='discuss_with_class'
        self.assertEqual(M.executable_report(s),'complete')
        s=report_spec();s['options'][0]['program'][-1]['must_be_optimal']=True
        with self.assertRaises(ValueError):M.executable_report(s)

    def test_absent_and_duplicate_complete_paths_fail_unique_selection(self):
        s=report_spec();s['options']=s['options'][1:]
        with self.assertRaises(ValueError):M.executable_report(s)
        s=report_spec();extra=deepcopy(s['options'][0]);extra['key']='extra';s['options'].append(extra)
        with self.assertRaises(ValueError):M.executable_report(s)

    def test_question_initial_state_and_provenance_require_complete_schema(self):
        for field in ('study','world','initial'):
            s=report_spec();del s[field]
            with self.subTest(field=field),self.assertRaises(ValueError):M.executable_report(s)
        s=report_spec();s['initial']['question']=deepcopy(s['study']);s['initial']['question']['variable']='other'
        with self.assertRaises(ValueError):M.executable_report(s)
        s=report_spec();s['options'][0]['program'][0]['question']=deepcopy(s['study']);s['options'][0]['program'][0]['question']['window']='other'
        with self.assertRaises(ValueError):M.executable_report(s)


class FirstExecutableActionTests(unittest.TestCase):
    def test_first_step_is_execution_from_empty_information_not_a_name_order(self):
        s=first_spec();self.assertEqual(M.executable_first_action(s),'formulate')
        s['options'].reverse();self.assertEqual(M.executable_first_action(s),'formulate')
        for i,o in enumerate(s['options']):o['key']=str(i);o['text']='choice'+str(i)
        self.assertEqual(M.executable_first_action(s),'choice2')

    def test_first_formulation_does_not_assume_nonempty_future_responses(self):
        s=first_spec();s['world']['potential_records']=[]
        self.assertEqual(M.executable_first_action(s),'formulate')

    def test_other_information_states_do_not_force_the_same_unique_first_step(self):
        for setup in ('question','records'):
            s=first_spec()
            if setup=='question':s['initial']['question']=deepcopy(s['study'])
            else:s['initial']['records']=deepcopy(s['world']['potential_records'])
            # With a preformulated question collection also works; with
            # existing numeric records plotting also works. Both admit
            # reviewing/formulating the study, so there is genuine ambiguity.
            with self.subTest(setup=setup),self.assertRaises(ValueError):M.executable_first_action(s)

    def test_known_empty_records_do_not_make_a_meaningful_plot_available(self):
        s=first_spec();s['initial']['records']=[]
        self.assertEqual(M.executable_first_action(s),'formulate')
        p=runner(s);self.assertEqual(p.step({'op':'organize'}).frequencies,())
        with self.assertRaises(M.MissingInformation):p.step({'op':'encode_plot','input':'raw','scale':1,'offset':0})

    def test_extra_unknown_missing_and_duplicate_candidates_fail_closed(self):
        for i in range(3):
            s=first_spec();s['options'][i]['condition']='extra'
            with self.subTest(i=i),self.assertRaises(ValueError):M.executable_first_action(s)
        s=first_spec();s['options'][1]['action']['input']='unknown'
        with self.assertRaises(ValueError):M.executable_first_action(s)
        s=first_spec();s['options']=s['options'][1:]
        with self.assertRaises(ValueError):M.executable_first_action(s)
        s=first_spec();extra=deepcopy(s['options'][0]);extra['key']='duplicate';s['options'].append(extra)
        with self.assertRaises(ValueError):M.executable_first_action(s)


if __name__=='__main__':unittest.main()
