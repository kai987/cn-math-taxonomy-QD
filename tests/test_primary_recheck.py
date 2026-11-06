"""Source-only replay and narrow make-ten/definition regression coverage."""
from copy import deepcopy
from itertools import permutations
from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import primary_recheck as P
import second_pass as SP


class SourceOnly(dict):
    def __getitem__(self, key):
        if key in ('answer', 'verify', 'explanation', 'accept'):
            raise AssertionError('the solver must not read hidden reference fields')
        return super().__getitem__(key)

    def get(self, key, default=None):
        if key in ('answer', 'verify', 'explanation', 'accept'):
            raise AssertionError('the solver must not read hidden reference fields')
        return super().get(key, default)


def source_only(question):
    return SourceOnly({k:deepcopy(question[k]) for k in ('id', 'type', 'prompt', 'choices') if k in question})


def make_ten(a=9, b=3, split=None, texts=None):
    return {'type':'choice',
            'prompt':f'用凑十法算 {a}＋{b} 时，把 {b if split is None else split} 拆成几和几更方便？',
            'choices':[{'key':'key'+str(i), 'text':text}
                       for i,text in enumerate(texts or ['1和2', '3和0', '2和3'])]}


class PrimaryNarrowReplay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.questions = json.loads((ROOT/'data/questions.json').read_text())
        cls.by_id = {q['id']:q for q in cls.questions}

    def test_all_five_real_sources_without_hidden_fields_and_with_every_candidate_order(self):
        for qid in ('cnm_p003_q2', 'cnm_p015_q1', 'cnm_p019_q1', 'cnm_p072_q1', 'cnm_p099_q1'):
            original = self.by_id[qid]
            expected_text = next(c['text'] for c in original['choices'] if c['key']==original['answer'])
            for order in permutations(range(len(original['choices']))):
                question = source_only(original)
                question['choices'] = [deepcopy(original['choices'][i]) for i in order]
                for index, candidate in enumerate(question['choices']): candidate['key'] = 'changed-key-'+str(index)
                expected_key = next(c['key'] for c in question['choices'] if c['text']==expected_text)
                with self.subTest(qid=qid, order=order): self.assertEqual(P.solve_question(question), expected_key)
                self.assertFalse(set(question)&{'answer', 'verify', 'explanation', 'accept'})

    def test_all_legal_single_digit_make_ten_parameters_and_unordered_splits(self):
        checked = 0
        for a in range(1,10):
            for b in range(1,10):
                if a+b < 10: continue
                first, second = 10-a, b-(10-a)
                for pair in ((first,second), (second,first)):
                    texts = [f'{b}和{b}', f'{pair[0]}和{pair[1]}', '0和0']
                    question = make_ten(a,b,texts=texts)
                    self.assertEqual(P.solve_question(source_only(question)), 'key1')
                    checked += 1
        self.assertEqual(checked, 90)
        # At a+b=10, the valid split can contain a zero remainder.
        self.assertEqual(P.solve_question(make_ten(8,2,texts=['0和2','1和1','2和2'])), 'key0')

    def test_make_ten_is_computed_from_the_question_not_the_original_one_and_two(self):
        question = make_ten(8,7,texts=['1和2','5和2','7和0'])
        self.assertEqual(P.solve_question(question), 'key1')
        question['prompt'] = question['prompt'].replace('8＋7','6＋7')
        with self.assertRaises(P.ParseError): P.solve_question(question)
        question['choices'][0]['text'] = '4和3'
        self.assertEqual(P.solve_question(question), 'key0')

    def test_missing_or_duplicate_equivalent_make_ten_candidates_are_rejected(self):
        for texts in (['3和0','2和3','0和0'], ['1和2','2和1','3和0'],
                      ['1和2','1和2','3和0'], ['1和2',' 2和1 ','3和0']):
            with self.subTest(texts=texts), self.assertRaises(P.ParseError): P.solve_question(make_ten(texts=texts))

    def test_illegal_make_ten_domains_spelling_and_mismatched_split_operand_reject(self):
        for a,b in ((0,9),(-1,9),(10,1),(9,10),(9,0),(2,3),('09',3),('９',3),(9,'③'),(9,'3⁵'),(9,'3.0')):
            with self.subTest(a=a,b=b), self.assertRaises(P.ParseError): P.solve_question(make_ten(a,b))
        with self.assertRaises(P.ParseError): P.solve_question(make_ten(9,3,split=9))
        with self.assertRaises(P.ParseError): P.solve_question(make_ten(texts=['1和2','不知道','3和0']))
        with self.assertRaises(P.ParseError): P.solve_question(make_ten(texts=['1+2','3和0','2和3']))

    def test_negated_or_changed_meaning_prompts_do_not_use_the_new_definition_rules(self):
        changes = {
            'cnm_p003_q2':'从左数，排在最后面的是第几个？',
            'cnm_p015_q1':'面向黑板站好，你背对着的那一边叫什么？',
            'cnm_p072_q1':'笔算加法算完后，不常用什么方法验算？',
            'cnm_p099_q1':'线段和直线相比，下面哪一句不是说线段？',
            'cnm_p019_q1':'用凑十法算 9＋3 时，把 3 拆成几和几更不方便？',
        }
        for qid,prompt in changes.items():
            question = source_only(self.by_id[qid]);question['prompt'] = prompt
            with self.subTest(qid=qid), self.assertRaises(P.ParseError): P.solve_question(question)
        for qid in ('cnm_p003_q2','cnm_p015_q1','cnm_p072_q1','cnm_p099_q1'):
            question = source_only(self.by_id[qid]);question['prompt'] += ' 请改成相反意思。'
            with self.subTest(qid=qid), self.assertRaises(P.ParseError): P.solve_question(question)

    def test_new_and_existing_fact_rules_require_exactly_one_stripped_candidate(self):
        for qid in ('cnm_p003_q2','cnm_p015_q1','cnm_p072_q1','cnm_p099_q1'):
            question = source_only(self.by_id[qid]);correct = P.solve_question(question)
            text = next(c['text'] for c in question['choices'] if c['key']==correct)
            question['choices'].append({'key':'duplicate', 'text':' '+text+' '})
            with self.subTest(qid=qid), self.assertRaises(P.ParseError): P.solve_question(question)
            with self.subTest(qid=qid), self.assertRaises(P.ParseError): P.expected_choice_text(question['prompt'],[text,' '+text+' '])
        for texts in (['正数','负数'], ['既不是正数，也不是负数','既不是正数，也不是负数'],
                      ['既不是正数，也不是负数',' 既不是正数，也不是负数 ']):
            with self.subTest(texts=texts), self.assertRaises(P.ParseError): P.expected_choice_text('0 是哪种数？',texts)

    def test_arithmetic_choice_aliases_are_also_unique_not_first_match(self):
        with self.assertRaises(P.ParseError): P.expected_choice_text('计算：1+1＝？',['2','2.0','3'])
        self.assertEqual(P.expected_choice_text('计算：1+1＝？',[' 2 ','3','4']), '2')
        with self.assertRaises(P.ParseError): P.expected_choice_text('面向黑板站好，你正对着的那一边叫什么？',['前面',None])

    def test_full_current_primary_bank_replays_source_only(self):
        primary = [q for q in self.questions if q['id'].startswith('cnm_p')]
        self.assertEqual(len(primary),864)
        for question in primary:
            result = P.solve_question(source_only(question))
            with self.subTest(qid=question['id']):
                if question['type']=='numeric': self.assertTrue(SP.same_numeric(question,result))
                else: self.assertEqual(result,question['answer'])


if __name__ == '__main__': unittest.main()
