import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from models_statistics_105 import moments, variance_identifiability


def specification():
    population_b = ['100-sqrt(1/50)']*25 + ['100+sqrt(1/50)']*25
    def population_a(values):
        return {'populations': [{'values': values, 'sample_indices': [0,1]},
                {'values': population_b, 'sample_indices': list(range(50))}]}
    return {'variance_divisor': 'n', 'sampling': 'uniform_subsets',
            'observed': [{'count': 2, 'variance': '1/100'}, {'count': 50, 'variance': '1/50'}],
            'countermodels': [population_a(['99.9','100.1']), population_a(['99.9','100.1','1000'])],
            'options': [{'key':'X','text':'guaranteed lower A','claim':'guaranteed_population_order','relation':'<'},
                        {'key':'Y','text':'not identified','claim':'nonidentifiability'},
                        {'key':'Z','text':'wrong observed reason','claim':'nonidentifiability_with_observed_reason','processes':[1,0],'relation':'<'}]}


class VarianceInferenceTests(unittest.TestCase):
    def test_opposite_true_orders_match_both_observed_samples(self):
        spec=specification()
        self.assertEqual(variance_identifiability(spec),'not identified')
        spec['options'].reverse()
        self.assertEqual(variance_identifiability(spec),'not identified')

    def test_one_population_order_or_duplicate_witness_is_not_nonidentifiability(self):
        spec=specification();spec['countermodels'][1]=copy.deepcopy(spec['countermodels'][0])
        with self.assertRaises(ValueError):variance_identifiability(spec)

    def test_wrong_moment_or_wrong_sample_size_is_not_a_countermodel(self):
        for field,value in [('variance','1/101'),('count',3),('count',True)]:
            spec=specification();spec['observed'][0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):variance_identifiability(spec)

    def test_duplicate_or_missing_physical_indices_are_rejected(self):
        for indices in ([0,0],[0,3],[0],['0',1]):
            spec=specification();spec['countermodels'][0]['populations'][0]['sample_indices']=indices
            with self.subTest(indices=indices),self.assertRaises(ValueError):variance_identifiability(spec)

    def test_equal_values_do_not_collapse_distinct_members(self):
        values,mean,variance=moments(['2','2','4','4'])
        self.assertEqual(len(values),4);self.assertEqual(mean,3);self.assertEqual(variance,1)

    def test_unspecified_convention_or_unsupported_claim_is_unresolved(self):
        for field,value in [('variance_divisor','n-1'),('sampling','unknown')]:
            spec=specification();spec[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):variance_identifiability(spec)
        spec=specification();spec['options'][0]['claim']='unproved'
        with self.assertRaises(ValueError):variance_identifiability(spec)

    def test_nonreal_or_executable_strings_are_rejected(self):
        for value in ['sqrt(-1)',"__import__('os').getcwd()",'x+1',True]:
            with self.subTest(value=value),self.assertRaises((ValueError,SyntaxError)):moments([value])


if __name__=='__main__':unittest.main()
