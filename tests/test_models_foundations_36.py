"""Whole-story slots, units, physical domain and mathematical perturbations."""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from models_foundations_36 import tank_outflow_reference
from model_types import SelfReferenceProof


REFERENCE = '如：水箱原有 100 L 水，每分钟流出 5 L，t 分钟后剩余的水量（L）。（此例中 0≤t≤20，t 的单位为分钟。）'


def spec(expression='100-5*t', output='L', time='minute', variable='t'):
    return {'kind': 'f36_tank_outflow_reference', 'reference_only': True,
            'quantity_function': {'variable': variable, 'expression': expression,
                                  'output_unit': output, 'input_unit': time},
            'interpretation': {'system': 'tank', 'quantity': 'remaining_volume',
                'flows': 'single_constant_outflow', 'time_origin': 'initial_state',
                'domain': 'maximal_nonnegative_time_and_volume'}}


def story(initial='100', rate='5', horizon='20', initial_unit='L', rate_unit='L',
          output='L', rate_time='分钟', elapsed='分钟', domain_time='分钟', variable='t'):
    return (f'如：水箱原有{initial}{initial_unit}水，每{rate_time}流出{rate}{rate_unit}，'
            f'{variable}{elapsed}后剩余的水量（{output}）。（此例中0≤{variable}≤{horizon}，'
            f'{variable}的单位为{domain_time}。）')


class TankReferenceTests(unittest.TestCase):
    def test_actual_full_reference_derived_from_source(self):
        proof = tank_outflow_reference(spec())
        self.assertIsInstance(proof, SelfReferenceProof)
        self.assertTrue(proof.matches(REFERENCE))
        self.assertEqual(proof.initial_litres, 100)
        self.assertEqual(proof.outflow_litres_per_minute, 5)
        self.assertEqual(proof.horizon, 20)

    def test_initial_rate_and_noninteger_horizons_vary_independently(self):
        for initial in (Fraction(1, 7), Fraction(9, 2), Fraction(137)):
            for rate in (Fraction(1, 3), Fraction(2), Fraction(29, 5)):
                with self.subTest(initial=initial, rate=rate):
                    proof = tank_outflow_reference(spec(f'({initial})-({rate})*t'))
                    self.assertTrue(proof.matches(story(str(initial), str(rate), str(initial/rate))))
                    self.assertFalse(proof.matches(story(str(initial), str(rate), str(initial/rate+1))))

    def test_equivalent_source_forms_are_checked_by_full_coefficients(self):
        for expression in ('5*(20-t)', '(200-10*t)/2', '100-5t', '100+(-5)*t'):
            with self.subTest(expression=expression):
                self.assertTrue(tank_outflow_reference(spec(expression)).matches(REFERENCE))
        self.assertFalse(tank_outflow_reference(spec('110-5*t')).matches(REFERENCE))
        self.assertFalse(tank_outflow_reference(spec('100-10*t')).matches(REFERENCE))

    def test_whole_reference_roles_cannot_be_replaced_omitted_or_extended(self):
        proof = tank_outflow_reference(spec())
        for old, new in [('原有', '现在增加'), ('流出', '流入'), ('剩余', '流出的'),
                         ('水箱', '油箱'), ('100 L', '101 L'), ('5 L', '4 L'),
                         ('0≤t≤20', '0≤t≤21'), ('0≤t≤20', '1≤t≤20'),
                         ('0≤t≤20', '0<t<20'), ('t 的单位', 'x 的单位')]:
            with self.subTest(old=old,new=new): self.assertFalse(proof.matches(REFERENCE.replace(old,new)))
        for text in (REFERENCE.split('。')[0], REFERENCE + '所以每小时只流出5L。',
                     REFERENCE + '；且1=2', '100，5，20', ''):
            with self.subTest(text=text): self.assertFalse(proof.matches(text))

    def test_unit_conversion_checks_initial_flow_and_result_roles_separately(self):
        proof = tank_outflow_reference(spec())
        self.assertTrue(proof.matches(story('100000', '5000', initial_unit='mL', rate_unit='mL')))
        self.assertTrue(proof.matches(story('0.1', '0.005', initial_unit='m³', rate_unit='m³')))
        self.assertTrue(proof.matches(story(rate='1/12', rate_time='秒')))
        self.assertTrue(proof.matches(story(rate='300', rate_time='小时')))
        for kwargs in ({'initial_unit':'mL'}, {'rate_unit':'mL'}, {'rate_time':'小时'},
                       {'output':'mL'}, {'elapsed':'小时'}, {'domain_time':'秒'}):
            with self.subTest(kwargs=kwargs): self.assertFalse(proof.matches(story(**kwargs)))

    def test_declared_formula_units_change_the_expected_example(self):
        proof = tank_outflow_reference(spec(output='mL', time='second'))
        self.assertTrue(proof.matches(story(output='mL', initial_unit='mL', rate_unit='mL',
                                            rate_time='秒', elapsed='秒', domain_time='秒')))
        self.assertFalse(proof.matches(REFERENCE))
        proof = tank_outflow_reference(spec('1-1/2*t', output='m³', time='hour'))
        self.assertTrue(proof.matches(story('1000', '500', '2', initial_unit='L', rate_unit='L',
                                            output='m³', rate_time='小时', elapsed='小时', domain_time='小时')))

    def test_variable_renaming_is_structural_and_every_occurrence_is_bound(self):
        proof = tank_outflow_reference(spec('100-5*x', variable='x'))
        self.assertTrue(proof.matches(story(variable='x')))
        self.assertFalse(proof.matches(REFERENCE))
        self.assertFalse(proof.matches(story(variable='x').replace('0≤x', '0≤t')))

    def test_numeric_unicode_cannot_change_a_quantity_or_bound(self):
        proof = tank_outflow_reference(spec())
        self.assertTrue(proof.matches(REFERENCE.replace('100', '１００').replace('5 L', '５ L')))
        for old, new in [('100', '1⁰⁰'), ('100', '①00'), ('100', '1 00'),
                         ('100', '100。0'), ('5 L', '⑤ L'), ('20', '2⁰')]:
            with self.subTest(old=old,new=new): self.assertFalse(proof.matches(REFERENCE.replace(old,new)))
        for expression in ('1⁰⁰-5*t', '①00-5*t', '100。0-5*t', '1 00-5*t'):
            with self.subTest(expression=expression), self.assertRaises(ValueError): tank_outflow_reference(spec(expression))

    def test_missing_or_different_physical_premises_fail_closed(self):
        for key in spec()['interpretation']:
            for mutation in ('missing', 'unknown'):
                changed = spec()
                if mutation=='missing': changed['interpretation'].pop(key)
                else: changed['interpretation'][key]='unknown'
                with self.subTest(key=key,mutation=mutation), self.assertRaises(ValueError): tank_outflow_reference(changed)
        for value in (False, 1, 'true'):
            changed=spec();changed['reference_only']=value
            with self.subTest(value=value), self.assertRaises(ValueError): tank_outflow_reference(changed)

    def test_wrong_dimensions_degenerate_unknown_or_nonaffine_formulas_reject(self):
        for expression in ('100', '100+5*t', '-100-5*t', '0-5*t', '100-t*t',
                           '100-5*t+0*x', '100-5*t+unknown', '100-5*t+1/(t-t)', '__import__("os")'):
            with self.subTest(expression=expression), self.assertRaises((ValueError, SyntaxError, ZeroDivisionError)):
                tank_outflow_reference(spec(expression))
        for output,time in (('kg','minute'),('L','L'),('minute','hour'),('L','day')):
            with self.subTest(output=output,time=time), self.assertRaises(ValueError): tank_outflow_reference(spec(output=output,time=time))

    def test_unsupported_numbers_and_incomplete_data_fail_closed(self):
        proof=tank_outflow_reference(spec())
        for value in ('1e2', '1/0', 'nan', '100%', '100.0.0', '9'*100):
            with self.subTest(value=value): self.assertFalse(proof.matches(story(initial=value)))
        for part in ('quantity_function','interpretation'):
            changed=spec();changed.pop(part)
            with self.subTest(part=part), self.assertRaises(ValueError): tank_outflow_reference(changed)
        changed=spec();changed['answer']='reference'
        with self.assertRaises(ValueError):tank_outflow_reference(changed)

    def test_canonical_cancellation_cannot_erase_an_original_domain_hole(self):
        # All these canonicalize to100-5t, but zero powers introduce holes
        # at an endpoint, an interior time, or another real source argument.
        for expression in ('100-5*t+t**0-1', '100-5*t+0*t**0',
                           '100-5*t+1/t**0-1', '100-5*t+(t-1)**0-1',
                           '100-5*t+(t-10)**0-1', '100-5*t+(t+1)**0-1',
                           '100-5*t+t* *0-1', '100-5*t+0/t'):
            with self.subTest(expression=expression), self.assertRaises(ValueError):
                tank_outflow_reference(spec(expression))


if __name__ == '__main__': unittest.main()
