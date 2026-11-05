"""Frame-coverage risk and historical sales-frequency definitions.

All verdicts follow mathematical operations on sets, count blocks or complete
frequency maps.  Examples are executions/countermodels, never observations of
the city/shop in the question.  Preference and procurement optimisation are
outside these two explicitly scoped tasks.
"""
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
import re
import sympy as S

from model_types import select_unique


def _record(value, fields):
    if not isinstance(value,dict) or set(value) != set(fields):
        raise ValueError('a complete typed object without extra fields is required')
    return value


def _integer(value, lower=0):
    if type(value) is not int or value < lower or value.bit_length() > 128:
        raise ValueError('a bounded exact integer in the declared domain is required')
    return value


def _q(value):
    if type(value) is int:
        result = Fraction(value)
    elif isinstance(value,str) and len(value) <= 64:
        atom = r'[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)'
        if not re.fullmatch(atom+'(?:/'+atom+')?',value):
            raise ValueError('strict ASCII decimal/fraction spelling required')
        first,*second = value.split('/')
        try:
            result = Fraction(first)/(Fraction(second[0]) if second else 1)
        except ArithmeticError as error:
            raise ValueError('undefined rational') from error
    else:
        raise ValueError('a bounded exact rational is required')
    if max(abs(result.numerator).bit_length(),result.denominator.bit_length()) > 256:
        raise ValueError('number exceeds the arithmetic budget')
    return result


def _candidates(options, extra):
    if not isinstance(options,list) or not 1 <= len(options) <= 16:
        raise ValueError('a bounded nonempty candidate list is required')
    for option in options:
        _record(option,('key','text',extra))


class FrameCoverage:
    def __init__(self,premises,example):
        _record(premises,('target','frame','frame_relation','sampling','time_unit','reading_bounds'))
        if (premises['target'] != 'all_city_residents' or premises['frame'] != 'resident_library_visitors'
                or premises['frame_relation'] != 'proper_subset' or premises['time_unit'] != 'hours_per_day'):
            raise ValueError('the complete city target and its proper visitor frame are required')
        bounds = _record(premises['reading_bounds'],('lower','upper'))
        if _q(bounds['lower']) != 0 or _q(bounds['upper']) != 24:
            raise ValueError('daily reading duration must have the physical[0,24]hour domain')
        sampling = _record(premises['sampling'],('op','from','size'))
        if sampling['op'] != 'select_distinct' or sampling['from'] != 'frame':
            raise ValueError('distinct sampled residents must come only from this frame')
        self.n = _integer(sampling['size'],1)
        _record(example,('frame_size','omitted_size','inside_hours','outside_hours'))
        self.k,self.m = _integer(example['frame_size'],1),_integer(example['omitted_size'],1)
        if self.k < self.n:
            raise ValueError('a distinct sample cannot be larger than its frame')
        self.example = self.run(example['inside_hours'],example['outside_hours'])
        # Every feasible proper frame has K=n+q,q>=0 and N=K+m,m>0.
        # These independent integers cover the ENTIRE count domain, not one
        # school/city size. A constant readinga on the frame makes ANY
        # nonempty within-frame sample mean a, whatever its selection law.
        q = S.Symbol('q',integer=True,nonnegative=True)
        m = S.Symbol('m',integer=True,positive=True)
        a,b = S.symbols('a b',real=True)
        k = S.Integer(self.n)+q
        population = k+m
        bias = S.factor(a-(k*a+m*b)/population)
        target = m*(a-b)/population
        if S.cancel(bias-target) != 0 or S.cancel(S.Integer(self.n)*a/self.n-a) != 0:
            raise ValueError('the constant-block sampling identities failed')
        omitted_share = S.factor(m/population)
        if (omitted_share.is_positive is not True or S.factor(1-omitted_share).is_positive is not True
                or (k-self.n).is_nonnegative is not True):
            raise ValueError('the proper-frame count inequalities are unresolved')
        signs = (S.factor(bias.subs({a:1,b:0})),S.factor(bias.subs({a:1,b:2})),
                 S.cancel(bias.subs({a:1,b:1})))
        if signs[0].is_positive is not True or signs[1].is_negative is not True or signs[2] != 0:
            raise ValueError('positive, negative and zero bias possibilities were not proved')
        # These are legal population counterworlds, not inferred actual city
        # means. Keeping EVERY observed frame reading at1 while the omitted
        # readings are0,2 or1 also proves nonidentification from identical
        # observed data, independently of choosing a particular estimator.
        self.worlds = tuple(self.run(x,y) for x,y in ((1,0),(1,2),(1,1)))
        if not (self.worlds[0]['bias']>0 and self.worlds[1]['bias']<0 and self.worlds[2]['bias']==0):
            raise ValueError('the concrete counterworld execution disagrees with the all-count proof')
        if (len({w['sample_mean'] for w in self.worlds})!=1
                or self.worlds[0]['population_mean']==self.worlds[1]['population_mean']):
            raise ValueError('the identical-frame-data nonidentification witness failed')
        gap = S.factor(2*m/population)
        if gap.is_positive is not True:
            raise ValueError('the all-count omitted-population identification gap is unresolved')
        # An age assignment compatible with every given visitor-frame fact:
        # members[0,K) are elderly and members[K,K+m) are nonelderly. These
        # disjoint index sets exhaust the SAME city. No actual age counts are
        # inferred, and no age threshold or sampling preference is invented.
        self.age_counterworld = {'elderly_indices':(0,self.k),
            'nonelderly_indices':(self.k,self.k+self.m)}
        start,end = self.age_counterworld['elderly_indices']
        outside_start,outside_end = self.age_counterworld['nonelderly_indices']
        self.age_counterworld.update(eligible_count=end-start,
            omitted_count=outside_end-outside_start,population_count=self.k+self.m)
        if (start != 0 or end != outside_start or outside_end != self.k+self.m
                or end-start+outside_end-outside_start != self.k+self.m
                or self.age_counterworld['omitted_count'] <= 0):
            raise ValueError('the proper age-frame counterworld was not constructed')

    def run(self,inside,outside):
        a,b = _q(inside),_q(outside)
        if not 0 <= a <= 24 or not 0 <= b <= 24:
            raise ValueError('reading times must stay within a legal day')
        # U={0,...,K+m-1}; F={0,...,K-1}; the example sample is
        # {0,...,n-1}. Set membership and cardinality need no huge row list.
        population_mean = (self.k*a+self.m*b)/(self.k+self.m)
        sample_mean = self.n*a/self.n
        return {'population_size':self.k+self.m,'frame_size':self.k,'sample_size':self.n,
            'sample_mean':sample_mean,'population_mean':population_mean,
            'bias':sample_mean-population_mean,'omitted_count':self.m}

    def claim(self,node,budget=None,depth=0):
        if budget is None:
            budget=[0]
        budget[0]+=1
        if budget[0]>64 or depth>16 or not isinstance(node,dict):
            raise ValueError('bounded complete coverage claim required')
        op=node.get('op')
        if op=='all':
            _record(node,('op','claims'))
            if not isinstance(node['claims'],list) or not 1<=len(node['claims'])<=8:
                raise ValueError('a bounded nonempty conjunction is required')
            results=[self.claim(child,budget,depth+1) for child in node['claims']]
            return all(results)
        _record(node,('op',))
        if op=='frame_omits_population_members':
            return self.m>0
        if op=='positive_bias_possible':
            return self.worlds[0]['bias']>0
        if op=='negative_bias_possible':
            return self.worlds[1]['bias']<0
        if op=='zero_bias_possible':
            return self.worlds[2]['bias']==0
        if op=='sample_size_exceeds_available_frame':
            return self.n>self.k
        if op=='everyone_has_sampling_chance':
            # Every omitted unit has probability0 under ANY law supported
            # onF; randomness insideF cannot change that support.
            return self.m==0
        if op=='frame_randomness_guarantees_zero_bias':
            if self.worlds[0]['bias']<=0:
                raise ValueError('the legal biased counterworld was not established')
            return False
        if op=='elderly_only_guarantees_population_coverage':
            # One city compatible with ALL premises may labelF as elderly
            # and U\F as nonelderly. This proper age frame refutes a universal
            # guarantee; it does not assert the actual city's age composition.
            if self.age_counterworld['omitted_count']<=0 or self.k<self.n:
                raise ValueError('a legal proper age-frame counterworld is required')
            return self.age_counterworld['eligible_count']==self.age_counterworld['population_count']
        if op=='actual_bias_must_be_positive':
            return self.worlds[1]['bias']>=0
        if op=='actual_bias_must_be_nonzero':
            return self.worlds[2]['bias']!=0
        raise ValueError('unknown claim; absence of evidence is not a false verdict')


def frame_coverage_risk(spec):
    _record(spec,('kind','premises','example','options'))
    if spec['kind']!='g25_frame_coverage_risk':
        raise ValueError('a typed frame-coverage proof is required')
    _candidates(spec['options'],'claim')
    proof=FrameCoverage(spec['premises'],spec['example'])
    return select_unique(spec['options'],lambda option:proof.claim(option['claim']))


def _category(value):
    if type(value) is int:
        return _q(value)
    if isinstance(value,str):
        if value.lower() in ('nan','inf','infinity','none','true','false'):
            raise ValueError('missing/nonfinite tokens are not size categories')
        if re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,23}',value):
            return value
        return _q(value)
    raise ValueError('a finite size category or exact numeric size is required')


@dataclass(frozen=True)
class Result:
    sort: str
    value: object
    lineage: str = ''
    mode_certificate: bool = False


class Sales:
    def __init__(self,values):
        if not isinstance(values,list) or not 1<=len(values)<=256:
            raise ValueError('a nonempty bounded per-item sales record is required')
        self.values=tuple(_category(v) for v in values)
        self.counts=Counter(self.values)
        if sum(self.counts.values())!=len(self.values):
            raise ValueError('a sold item was dropped or counted twice')
        greatest=max(self.counts.values())
        self.modes=frozenset(key for key,count in self.counts.items() if count==greatest)
        if not self.modes or any((key in self.modes)!=(count==greatest) for key,count in self.counts.items()):
            raise ValueError('the complete argmax set is not certified')

    def evaluate(self,node,budget=None,depth=0):
        if budget is None:
            budget=[0]
        budget[0]+=1
        if budget[0]>48 or depth>16 or not isinstance(node,dict):
            raise ValueError('a bounded mathematical statistic program is required')
        op=node.get('op')
        if op=='values':
            _record(node,('op',))
            return Result('list',self.values,'all_sales')
        if op=='divide':
            _record(node,('op','numerator','denominator'))
            numerator=self.evaluate(node['numerator'],budget,depth+1)
            denominator=self.evaluate(node['denominator'],budget,depth+1)
            if numerator.sort!='scalar' or denominator.sort!='scalar' or denominator.value==0:
                raise ValueError('a numeric quotient with a nonzero divisor is required')
            return Result('scalar',numerator.value/denominator.value)
        _record(node,('op','input'))
        source=self.evaluate(node['input'],budget,depth+1)
        if op in ('sum','length','sort','middle'):
            if source.sort!='list':
                raise ValueError('this numeric operation needs a list')
            if op=='length':
                return Result('scalar',Fraction(len(source.value)))
            if op=='sort':
                # Sorting here is only a permutation. Give the validated
                # category types a deterministic total order, without treating
                # a nominal label as a numeric size. This allows the same
                # multiset certificate for numeric, nominal and mixed codes.
                values=tuple(sorted(source.value,key=lambda v:(0,v) if isinstance(v,Fraction) else (1,v)))
                if Counter(values)!=Counter(source.value):
                    raise ValueError('sorting changed the sales multiplicities')
                return Result('list',values,source.lineage)
            if any(not isinstance(v,Fraction) for v in source.value):
                raise ValueError('numeric mean/median execution needs numeric size codes')
            if op=='sum':
                return Result('scalar',sum(source.value,Fraction(0)))
            if tuple(source.value)!=tuple(sorted(source.value)):
                raise ValueError('the middle-value operation requires ordered data')
            n=len(source.value)
            value=source.value[n//2] if n%2 else (source.value[n//2-1]+source.value[n//2])/2
            return Result('scalar',value)
        if op=='frequencies':
            if source.sort!='list' or source.lineage!='all_sales':
                raise ValueError('frequencies must tally the complete original multiset')
            counts=Counter(source.value)
            if sum(counts.values())!=len(self.values) or counts!=self.counts:
                raise ValueError('the frequency map lost sold items')
            return Result('counts',counts,'complete_counts')
        if op=='argmax_keys':
            if source.sort!='counts' or source.lineage!='complete_counts':
                raise ValueError('the maximum-frequency selector needs every size count')
            top=max(source.value.values())
            keys=frozenset(k for k,v in source.value.items() if v==top)
            if keys!=self.modes:
                raise ValueError('the selector omitted a tied mode or included a nonmode')
            # This is a complete finite-domain proof: every sold item
            # contributes once to one category and EVERY key is tested
            # against the same maximum. It works for arbitrary labels and
            # multiplicities, not only the numeric execution example.
            return Result('keys',keys,'maximum_frequency_keys',True)
        raise ValueError('unknown statistic operation')


def _as_keys(result):
    if result.sort=='keys':
        return result.value
    if result.sort=='scalar':
        return frozenset({result.value})
    if result.sort=='list':
        return frozenset(result.value)
    raise ValueError('this object is not a proposed set of size results')


def historical_sales_modes(spec):
    _record(spec,('kind','goal','example','counterexample','options'))
    if spec['kind']!='g25_historical_sales_modes' or spec['goal']!='all_historical_maximum_frequency_sizes':
        raise ValueError('the historical frequency target, not procurement optimality, must be explicit')
    _candidates(spec['options'],'program')
    # Numeric examples let the mean and median execute as well. They are
    # legal size codes, not a restriction on the general frequency-map proof.
    example,witness=Sales(spec['example']),Sales(spec['counterexample'])
    def check(option):
        actual=example.evaluate(option['program'])
        counter=witness.evaluate(option['program'])
        if actual.mode_certificate and counter.mode_certificate:
            if _as_keys(actual)!=example.modes or _as_keys(counter)!=witness.modes:
                raise ValueError('the frequency-definition certificate failed')
            return True
        if _as_keys(counter)==witness.modes:
            raise ValueError('a noncertified program needs a legal distinguishing sales counterexample')
        return False
    return select_unique(spec['options'],check)


HANDLERS={'g25_frame_coverage_risk':frame_coverage_risk,
          'g25_historical_sales_modes':historical_sales_modes}
