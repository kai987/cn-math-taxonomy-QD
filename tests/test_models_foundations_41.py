"""Reference meaning, multiplicity and missing-premise regression tests."""
import copy
from fractions import Fraction
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from model_types import SelfReferenceProof
from models_foundations_41 import RationalSignPartitionProof, rational_sign_partition


def source(numbers=None):
    return {
        'kind': 'f41_rational_sign_partition',
        'numbers': ['-2', '0', '3.5', '-1/3', '7'] if numbers is None else numbers,
        'classes': [{'label': '正数', 'relation': '>', 'cutoff': '0'},
                    {'label': '0', 'relation': '=', 'cutoff': '0'},
                    {'label': '负数', 'relation': '<', 'cutoff': '0'}],
    }


class RationalPartitionTests(unittest.TestCase):
    def test_current_reference_is_a_complete_partition(self):
        proof = rational_sign_partition(source())
        self.assertIsInstance(proof, SelfReferenceProof)
        self.assertTrue(proof.matches('正数：3.5，7；0：0；负数：-2，-1/3'))

    def test_class_and_item_order_and_exact_representations_are_irrelevant(self):
        spec = source(); spec['numbers'].reverse(); spec['classes'].reverse()
        proof = rational_sign_partition(spec)
        self.assertTrue(proof.matches(' 负数: -2/1,−2/6 ; 0: -0.0 ; 正数: 7.0,7/2 '))

    def test_number_changes_change_the_computed_partition(self):
        spec = source(); spec['numbers'][-1] = '-7'
        proof = rational_sign_partition(spec)
        self.assertFalse(proof.matches('正数:3.5,7;0:0;负数:-2,-1/3'))
        self.assertTrue(proof.matches('正数:3.5;0:0;负数:-2,-1/3,-7'))

    def test_multiplicity_is_preserved_including_equal_rationals(self):
        proof = rational_sign_partition(source(['0', '0.0', '2', '4/2', '-1']))
        self.assertTrue(proof.matches('正数:2,2;0:0,0;负数:-1'))
        for text in ('正数:2;0:0,0;负数:-1', '正数:2,2;0:0;负数:-1',
                     '正数:2,2,2;0:0,0;负数:-1'):
            with self.subTest(text=text): self.assertFalse(proof.matches(text))

    def test_empty_classes_are_explicit_and_cannot_hide_missing_members(self):
        proof = rational_sign_partition(source(['1', '1/2']))
        self.assertTrue(proof.matches('正数:1,0.5;0:无;负数:∅'))
        self.assertFalse(proof.matches('正数:1,0.5;0:;负数:∅'))
        self.assertFalse(proof.matches('正数:无;0:无;负数:∅'))

    def test_wrong_cross_class_missing_and_extra_members_are_rejected(self):
        proof = rational_sign_partition(source())
        bad = [
            '正数:3.5;0:0;负数:-2,-1/3',
            '正数:3.5,7,8;0:0;负数:-2,-1/3',
            '正数:3.5,-2;0:0;负数:7,-1/3',
            '正数:3.5,7,0;0:0;负数:-2,-1/3',
            '正数:3.5,7;正数:0;负数:-2,-1/3',
            '正数:3.5,7;0:0;负数:-2,-1/3;零:0',
        ]
        for text in bad:
            with self.subTest(text=text): self.assertFalse(proof.matches(text))

    def test_unsupported_reference_notation_fails_closed(self):
        proof = rational_sign_partition(source())
        for text in ('正数:350%,7;0:0;负数:-2,-1/3',
                     '正数:3 5,7;0:0;负数:-2,-1/3',
                     '正数:3.5,7;0:0;负数:- 2,-1/3',
                     '正数:3.5,7;0:0;负数:-2,-1/0',
                     '正数:3.5,7;0:0;负数:-2,-1/3。这是正确答案',
                     '正数:3.5,7,;0:0;负数:-2,-1/3', '', None, 3):
            with self.subTest(text=text): self.assertFalse(proof.matches(text))

    def test_zero_signs_and_small_decimals_use_exact_order(self):
        proof = rational_sign_partition(source(['-0', '+0.000', '.0001', '-.0001']))
        self.assertTrue(proof.matches('正数:1/10000;0:0,0;负数:-1/10000'))

    def test_compatibility_glyphs_cannot_change_numeric_meaning(self):
        proof = rational_sign_partition(source(['35']))
        self.assertFalse(proof.matches('正数:3⁵;0:无;负数:无'))
        proof = rational_sign_partition(source(['3.5']))
        self.assertFalse(proof.matches('正数:3。5;0:无;负数:无'))
        proof = rational_sign_partition(source(['3']))
        self.assertFalse(proof.matches('正数:③;0:无;负数:无'))
        self.assertTrue(proof.matches('正数：３；０：无；负数：无'))
        for token in ('3⁵', '3。5', '③', '3 5', '- 2', '1 / 2'):
            with self.subTest(token=token), self.assertRaises(ValueError): rational_sign_partition(source([token]))

    def test_missing_unknown_or_contradictory_definitions_are_rejected(self):
        bad = []
        spec = source(); del spec['classes']; bad.append(spec)
        spec = source(); spec['classes'].pop(); bad.append(spec)
        spec = source(); spec['classes'][0]['relation'] = '>='; bad.append(spec)
        spec = source(); spec['classes'][0]['cutoff'] = '1'; bad.append(spec)
        spec = source(); spec['classes'][0]['label'] = '非负数'; bad.append(spec)
        spec = source(); spec['classes'][0]['cutoff'] = False; bad.append(spec)
        spec = source(); spec['classes'][0]['relation'] = '<'; bad.append(spec)
        spec = source(); spec['classes'][2] = copy.deepcopy(spec['classes'][0]); bad.append(spec)
        spec = source(); spec['classes'][0]['extra'] = 1; bad.append(spec)
        for spec in bad:
            with self.subTest(spec=spec), self.assertRaises(ValueError): rational_sign_partition(spec)

    def test_invalid_or_excessive_source_numbers_are_rejected(self):
        for values in ([], ['1/0'], [True], [0.5], ['1e-3'], ['1 cm'],
                       ['9' * 129], ['0'] * 129, [None], [[1]]):
            with self.subTest(values=values), self.assertRaises((ValueError, ZeroDivisionError)):
                rational_sign_partition(source(values))

    def test_no_undeclared_source_or_result_fields_are_accepted(self):
        spec = source(); spec['answer'] = 'anything'
        with self.assertRaises(ValueError): rational_sign_partition(spec)
        spec = source(); spec['kind'] = 'unknown'
        with self.assertRaises(ValueError): rational_sign_partition(spec)

    def test_proof_constructor_requires_computed_exact_values(self):
        for values in ('正数:1;0:无;负数:无', [True], [1], [0.1], [], None):
            with self.subTest(values=values), self.assertRaises(ValueError): RationalSignPartitionProof(values)
        proof = RationalSignPartitionProof([Fraction(1, 10**50), Fraction(-1, 10**50)])
        self.assertTrue(proof.matches('正数:1/' + str(10**50) + ';0:无;负数:-1/' + str(10**50)))


if __name__ == '__main__': unittest.main()
