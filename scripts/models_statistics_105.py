"""Exact finite-population countermodels for unsupported variance inference.

Each constructed population and its distinct sampled indices must reproduce
all given sample moments. Two opposite population orderings prove that those
sample summaries alone do not identify the true ordering. A single sample is
never used to prove a universal population conclusion.
"""
from math import comb
import sympy as S
from model_types import select_unique
from models_symbolic import parse_math


def _scalar(source):
    if type(source) not in (str, int, float):
        raise ValueError('closed real mathematical scalar required')
    value, conditions = parse_math(str(source))
    if (value.free_symbols or value.is_real is not True
            or any(S.simplify(c) is not S.true for c in conditions)):
        raise ValueError('closed real scalar domain unproved')
    return S.simplify(value)


def moments(values):
    if not isinstance(values, list) or not 1 <= len(values) <= 200:
        raise ValueError('bounded nonempty finite population required')
    xs = [_scalar(value) for value in values]
    mean = S.simplify(sum(xs)/len(xs))
    variance = S.simplify(sum((value-mean)**2 for value in xs)/len(xs))
    if variance.is_nonnegative is not True:
        raise ValueError('variance is unresolved')
    return xs, mean, variance


def ordering(first, second):
    difference = S.simplify(first-second)
    if difference.is_zero is True: return '='
    if difference.is_positive is True: return '>'
    if difference.is_negative is True: return '<'
    raise ValueError('variance ordering is unresolved')


def variance_identifiability(spec):
    if spec.get('variance_divisor') != 'n' or spec.get('sampling') != 'uniform_subsets':
        raise ValueError('explicit population-divisor moments and random subset sampling required')
    observed = spec['observed']
    if not isinstance(observed, list) or len(observed) != 2:
        raise ValueError('exactly two measured processes required')
    for item in observed:
        if type(item['count']) is not int or not 2 <= item['count'] <= 200:
            raise ValueError('sample size must be an integer of at least two')
        if _scalar(item['variance']).is_nonnegative is not True:
            raise ValueError('negative sample variance')
    scenarios = spec['countermodels']
    if not isinstance(scenarios, list) or len(scenarios) < 2:
        raise ValueError('two opposite population constructions are required')
    orders = set()
    for scenario in scenarios:
        populations = scenario['populations']
        if not isinstance(populations, list) or len(populations) != 2:
            raise ValueError('two populations per countermodel required')
        variances = []
        for population, observation in zip(populations, observed):
            xs, _, variance = moments(population['values'])
            indices = population['sample_indices']
            if (not isinstance(indices, list) or len(indices) != observation['count']
                    or any(type(i) is not int or not 0 <= i < len(xs) for i in indices)
                    or len(set(indices)) != len(indices)):
                raise ValueError('sample must index distinct physical population members')
            # Equal numeric values remain distinct physical study units.
            sampled = [str(xs[i]) for i in indices]
            _, _, sample_variance = moments(sampled)
            if ordering(sample_variance, _scalar(observation['variance'])) != '=':
                raise ValueError('countermodel does not reproduce the observed sample variance')
            if S.Rational(1, comb(len(xs), len(indices))).is_positive is not True:
                raise ValueError('the indicated random sample has no positive probability')
            variances.append(variance)
        orders.add(ordering(*variances))
    if not {'<', '>'} <= orders:
        raise ValueError('opposite population-variance orderings were not established')

    def check(option):
        claim = option['claim']
        if claim == 'nonidentifiability':
            return True  # Two legal, observation-equivalent opposite orders.
        if claim == 'guaranteed_population_order':
            relation = option['relation']
            if relation not in ('<', '=', '>'): raise ValueError('unknown order claim')
            if any(order != relation for order in orders): return False
            raise ValueError('finite witnesses cannot prove universal identification')
        if claim == 'nonidentifiability_with_observed_reason':
            pair = option['processes']
            if sorted(pair) != [0, 1] or any(type(i) is not int for i in pair):
                raise ValueError('two distinct process indices required')
            relation = option['relation']
            if relation not in ('<', '=', '>'): raise ValueError('unknown observed order claim')
            return ordering(*[_scalar(observed[i]['variance']) for i in pair]) == relation
        raise ValueError('unmodelled population inference')

    return select_unique(spec['options'], check)


HANDLERS = {'stats105_variance_identifiability': variance_identifiability}
