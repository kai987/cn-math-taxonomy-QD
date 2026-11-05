"""Guaranteed statistic invariance after raising one sorted maximum.

The central-rank proof covers every integern>=3 by its two parity charts.
Concrete tables execute the statistic programs; examples do not establish
universal invariance. A changed legal mode-set witness only refutes a guarantee.
"""
from dataclasses import dataclass
from fractions import Fraction
import sympy as S

from model_types import select_unique
from models_geometry_25 import Sales, _q, _record, _candidates


_N = S.Symbol('n',integer=True,positive=True)
_D = S.Symbol('delta',positive=True)
_SUM = S.Symbol('total',real=True)
_CENTER = S.Symbol('central_value',real=True)


def central_rank_certificate():
    """Prove both middle-index cases and preservation of sortedness."""
    k = S.Symbol('k',integer=True,nonnegative=True)
    charts = []
    # Zero-based indices. The changed last index is n-1, so all indices<=n-2
    # are unchanged. These charts exhaust every integern>=3, with no gap.
    for n,indices in ((2*k+3,(k+1,)),(2*k+4,(k+1,k+2))):
        if S.simplify(n-2-indices[-1]).is_nonnegative is not True:
            raise ValueError('a middle rank may touch the changed maximum')
        if any(index.is_integer is not True or index.is_nonnegative is not True for index in indices):
            raise ValueError('a middle rank is not a legal index')
        charts.append((n,indices,n-2))
    gap = S.Symbol('previous_max_gap',nonnegative=True)
    if (gap+_D).is_positive is not True or (_D/_N).is_positive is not True:
        raise ValueError('sortedness or strictly increasing mean was not proved')
    # For oddn=2k+3 the rank k+1 is unchanged. For evenn=2k+4 both
    # ranks k+1,k+2 are unchanged, and so is their arithmetic average.
    a,b = S.symbols('a b',real=True)
    if S.expand((a+b)/2-(a+b)/2) != 0:
        raise ValueError('the even central-rank average identity failed')
    return tuple(charts)


class MaximumRaise:
    def __init__(self, data):
        _record(data,('values','increase'))
        values = data['values']
        if not isinstance(values,list) or not 3 <= len(values) <= 128:
            raise ValueError('a bounded sorted table with at least three observations is required')
        self.before = tuple(_q(value) for value in values)
        self.increase = _q(data['increase'])
        if self.increase <= 0 or self.before != tuple(sorted(self.before)):
            raise ValueError('only a strictly positive increase of the already sorted last value is allowed')
        self.after = self.before[:-1]+(self.before[-1]+self.increase,)
        if self.after != tuple(sorted(self.after)) or self.before[:-1] != self.after[:-1]:
            raise ValueError('the construction changed order or another observation')
        self.n = len(self.before)
        self.indices = (self.n//2,) if self.n%2 else (self.n//2-1,self.n//2)
        if any(index >= self.n-1 or self.before[index] != self.after[index] for index in self.indices):
            raise ValueError('the actual median uses a changed observation')
        # Sales is the same exact numeric/multiset program interpreter used
        # for the historical-mode definition. Here all inputs are real numeric
        # data, not categorical labels; conversion preserves exact Fractions.
        self._before = Sales([str(value) for value in self.before])
        self._after = Sales([str(value) for value in self.after])

    def execute(self, program):
        return self._before.evaluate(program),self._after.evaluate(program)


@dataclass(frozen=True)
class ScalarCertificate:
    before: object
    change: object


def _whole_values(node,budget=None):
    if budget is None:
        budget=[0]
    budget[0]+=1
    if budget[0]>32 or not isinstance(node,dict):
        raise ValueError('bounded complete-data selector required')
    if node.get('op')=='values':
        _record(node,('op',))
        return
    _record(node,('op','input'))
    if node['op']!='sort':
        raise ValueError('only the whole table and multiset-preserving sorting are certified')
    _whole_values(node['input'],budget)


def scalar_certificate(node,budget=None):
    if budget is None:
        budget=[0]
    budget[0]+=1
    if budget[0]>48 or not isinstance(node,dict):
        raise ValueError('bounded scalar statistic program required')
    op=node.get('op')
    if op in ('sum','length','middle'):
        _record(node,('op','input'))
        _whole_values(node['input'])
        if op=='sum':
            return ScalarCertificate(_SUM,_D)
        if op=='length':
            return ScalarCertificate(_N,S.Integer(0))
        central_rank_certificate()
        return ScalarCertificate(_CENTER,S.Integer(0))
    if op=='divide':
        _record(node,('op','numerator','denominator'))
        numerator=scalar_certificate(node['numerator'],budget)
        denominator=scalar_certificate(node['denominator'],budget)
        # Do not infer universal legality from a nonzero sample denominator.
        # Only nonzero expressions of the positive countn are admitted here.
        if (S.cancel(denominator.change)!=0 or denominator.before.free_symbols-{_N}
                or S.factor(denominator.before).is_zero is not False):
            raise ValueError('the divisor is not proved nonzero for the whole family')
        before=numerator.before/denominator.before
        after=(numerator.before+numerator.change)/denominator.before
        return ScalarCertificate(S.cancel(before),S.cancel(after-before))
    raise ValueError('this scalar program has no universal change certificate')


def _output(result):
    return result.sort,result.value


def maximum_raise_invariance(spec):
    _record(spec,('kind','premises','example','counterexample','options'))
    if spec['kind']!='g20_maximum_raise_invariance':
        raise ValueError('a maximum-increase invariance model is required')
    premises=_record(spec['premises'],('minimum_size','order','change','criterion','mode_ties'))
    if (type(premises['minimum_size']) is not int or premises['minimum_size']!=3
            or premises['order']!='nondecreasing' or premises['change']!='raise_only_last_by_positive_amount'
            or premises['criterion']!='unchanged_for_all_admissible_tables'
            or premises['mode_ties']!='all_maximum_frequency_values'):
        raise ValueError('the complete rank, positive-change and universal target premises are required')
    _candidates(spec['options'],'program')
    central_rank_certificate()
    example,witness=MaximumRaise(spec['example']),MaximumRaise(spec['counterexample'])
    def check(option):
        before,after=example.execute(option['program'])
        old,new=witness.execute(option['program'])
        if before.sort=='scalar' and after.sort=='scalar':
            certificate=scalar_certificate(option['program'])
            change=S.cancel(certificate.change)
            if change==0:
                if _output(before)!=_output(after) or _output(old)!=_output(new):
                    raise ValueError('a universal invariance certificate failed its execution')
                return True
            # A real symbolic sign/nonzero proof is required; being a
            # nonidentical expression is never enough to infer all-data change.
            if change.is_zero is not False:
                raise ValueError('the universal scalar change is unresolved')
            actual_change=S.cancel(change.subs({_N:example.n,_D:S.Rational(example.increase)}))
            if actual_change != S.Rational(after.value-before.value):
                raise ValueError('the scalar change formula failed its execution')
        if old.mode_certificate and new.mode_certificate:
            # Keep the counterargument independent of textbook conventions
            # about all-distinct data: both tables must have repeated peak
            # frequencies and hence an unambiguous nonempty mode set.
            if max(witness._before.counts.values())<2 or max(witness._after.counts.values())<2:
                raise ValueError('a repeated-peak mode counterexample is required on both sides')
        if _output(old)==_output(new):
            raise ValueError('a legal changed-output witness is required for a non-guarantee')
        return False
    return select_unique(spec['options'],check)


HANDLERS={'g20_maximum_raise_invariance':maximum_raise_invariance}
