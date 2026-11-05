"""Exact countermodels and resource/identifiability guarantees for surveys.

The input options are reviewed translations of claims, not method-name verdicts.
False universal claims require actual legal worlds.  The reserve theorem uses
N=R+Q, R=1+U, U,Q nonnegative integers, covering every 1<=R<=N.
"""
from fractions import Fraction
from math import ceil, floor

from model_types import select_unique
from models_geometry_25 import _q, _record, _candidates


def _values(values):
    if not isinstance(values, list) or not 2 <= len(values) <= 128:
        raise ValueError('a bounded finite population with at least two records is required')
    return tuple(_q(value) for value in values)


def _indices(values, size, *, census=False):
    if (not isinstance(values, list) or not 1 <= len(values) <= size
            or any(type(index) is not int or not 0 <= index < size for index in values)
            or len(set(values)) != len(values)):
        raise ValueError('distinct valid observed-person indices are required')
    if census:
        if set(values) != set(range(size)):
            raise ValueError('the census must measure every population member exactly once')
    elif len(values) >= size:
        raise ValueError('the sample must be a nonempty proper subset of the population')
    return tuple(values)


def _mean(values):
    return sum(values, Fraction(0)) / len(values)


def _measurements(record, population, *, census=False):
    _record(record, ('indices', 'readings'))
    indices = _indices(record['indices'], len(population), census=census)
    if not isinstance(record['readings'], list) or len(record['readings']) != len(indices):
        raise ValueError('each observed member needs exactly one explicit reading')
    return indices, tuple(_q(value) for value in record['readings'])


def error_countermodel(claim):
    _record(claim, ('op', 'population', 'measurement_domain', 'census', 'sample'))
    if claim['op'] != 'census_always_strictly_less_absolute_mean_error':
        raise ValueError('the asserted strict mean-error comparison is required')
    if claim['measurement_domain'] != 'arbitrary_real_readings_allowed':
        raise ValueError('the absence of a no-measurement-error premise must be explicit')
    population = _values(claim['population'])
    _, census = _measurements(claim['census'], population, census=True)
    _, sample = _measurements(claim['sample'], population)
    truth = _mean(population)
    census_error, sample_error = abs(_mean(census)-truth), abs(_mean(sample)-truth)
    if census_error < sample_error:
        raise ValueError('this execution does not refute the asserted strict error ordering')
    return {'population_mean': truth, 'census_mean': _mean(census),
            'sample_mean': _mean(sample), 'census_error': census_error, 'sample_error': sample_error}


def sample_identity_countermodel(claim):
    _record(claim, ('op', 'population', 'sample_indices', 'measurement'))
    if claim['op'] != 'proper_sample_mean_always_equals_true_mean':
        raise ValueError('the asserted universal sample-mean identity is required')
    if claim['measurement'] != 'exact':
        raise ValueError('the sample-identity countermodel must not rely on measurement error')
    population = _values(claim['population'])
    indices = _indices(claim['sample_indices'], len(population))
    sample = tuple(population[index] for index in indices)
    if _mean(sample) == _mean(population):
        raise ValueError('a coincident sample mean is not a counterexample to universal identity')
    return {'population_mean': _mean(population), 'sample_mean': _mean(sample), 'sample': sample}


def record_countermodel(claim):
    _record(claim, ('op', 'population', 'observed_indices', 'measurement', 'knowledge', 'alternative_delta'))
    if claim['op'] != 'proper_observation_always_identifies_all_records':
        raise ValueError('the asserted individual-record identification guarantee is required')
    if claim['measurement'] != 'exact' or claim['knowledge'] != 'only_observed_individual_records':
        raise ValueError('exact partial records with no additional information are required')
    population = _values(claim['population'])
    indices = _indices(claim['observed_indices'], len(population))
    delta = _q(claim['alternative_delta'])
    if delta == 0:
        raise ValueError('the alternative legal world must differ at an unobserved record')
    missing = next(index for index in range(len(population)) if index not in indices)
    alternative = list(population)
    alternative[missing] += delta
    observed = tuple(population[index] for index in indices)
    other_observed = tuple(alternative[index] for index in indices)
    if observed != other_observed or tuple(alternative) == population:
        raise ValueError('the two-world indistinguishability construction failed')
    return {'first_world': population, 'second_world': tuple(alternative),
            'observed': observed, 'other_observed': other_observed, 'changed_index': missing}


def _sub(left, right):
    return tuple(a-b for a, b in zip(left, right))


def _relation(value, comparison):
    return {'lt': value < 0, 'le': value <= 0, 'eq': value == 0,
            'ge': value >= 0, 'gt': value > 0}[comparison]


def _universal_affine_relation(coefficients, comparison):
    """Decide a relation for c+a*U+b*Q on all nonnegative integer U,Q.

    Any negative slope is unbounded below. Otherwise the minimum is the
    attainable origin. Failed universals also execute their constructed legal
    counterexample; finite testing is never used for the positive result.
    """
    if comparison not in ('lt', 'le', 'eq', 'ge', 'gt'):
        raise ValueError('unknown exact comparison')
    c, a, b = map(Fraction, coefficients)
    if comparison == 'eq':
        if c == a == b == 0:
            return True
        u, q = ((0, 0) if c != 0 else ((1, 0) if a != 0 else (0, 1)))
    else:
        oriented = tuple(-v for v in (c, a, b)) if comparison in ('lt', 'le') else (c, a, b)
        z, x, y = oriented
        strict = comparison in ('lt', 'gt')
        if x >= 0 and y >= 0 and (z > 0 if strict else z >= 0):
            return True
        u = q = 0
        if (z > 0 if strict else z >= 0):
            coefficient, axis = (x, 0) if x < 0 else (y, 1)
            if coefficient >= 0:
                raise ValueError('the universal sign decision is unresolved')
            step = max(0, ceil(z/(-coefficient)) if strict else floor(z/(-coefficient))+1)
            u, q = (step, 0) if axis == 0 else (0, step)
    if u < 0 or q < 0 or _relation(c+a*u+b*q, comparison):
        raise ValueError('the sign counterexample is not legal or does not refute the claim')
    return False


def reserve_relation(claim):
    _record(claim, ('op', 'domain', 'plan', 'relation'))
    if claim['op'] != 'universal_remaining_count_relation':
        raise ValueError('a universal remaining-count comparison is required')
    domain = _record(claim['domain'], ('population', 'reserve', 'destruction_per_test'))
    if (domain['population'] != 'positive_integer'
            or domain['reserve'] != 'integer_from_one_through_population'
            or type(domain['destruction_per_test']) is not int
            or domain['destruction_per_test'] != 1):
        raise ValueError('one destroyed item per test and the complete 1<=R<=N domain are required')
    # Affine coefficients in (1,U,Q): R=1+U, N=1+U+Q.
    population, reserve, zero = (1, 1, 1), (1, 1, 0), (0, 0, 0)
    plan = _record(claim['plan'], ('op',))
    if plan['op'] == 'all_items':
        tested = population
    elif plan['op'] == 'all_except_reserved':
        tested = _sub(population, reserve)
    elif plan['op'] == 'no_items':
        tested = zero
    else:
        raise ValueError('unknown tested-item construction')
    remaining = _sub(population, tested)
    objects = {'population': population, 'reserve': reserve, 'tested': tested,
               'remaining': remaining, 'zero': zero}
    relation = _record(claim['relation'], ('left', 'comparison', 'right'))
    if (not isinstance(relation['left'], str) or not isinstance(relation['right'], str)
            or relation['left'] not in objects or relation['right'] not in objects):
        raise ValueError('unknown count object in resource relation')
    return _universal_affine_relation(_sub(objects[relation['left']], objects[relation['right']]),
                                      relation['comparison'])


def survey_claims(spec):
    _record(spec, ('kind', 'options'))
    if spec['kind'] != 'f16_survey_guarantees':
        raise ValueError('a typed survey-guarantee model is required')
    _candidates(spec['options'], 'claim')

    def check(option):
        claim = option['claim']
        if not isinstance(claim, dict):
            raise ValueError('a complete mathematical claim is required')
        op = claim.get('op')
        if op == 'census_always_strictly_less_absolute_mean_error':
            error_countermodel(claim)
            return False
        if op == 'proper_sample_mean_always_equals_true_mean':
            sample_identity_countermodel(claim)
            return False
        if op == 'proper_observation_always_identifies_all_records':
            record_countermodel(claim)
            return False
        if op == 'universal_remaining_count_relation':
            return reserve_relation(claim)
        raise ValueError('unknown mathematical survey claim')

    return select_unique(spec['options'], check)


HANDLERS = {'f16_survey_guarantees': survey_claims}
