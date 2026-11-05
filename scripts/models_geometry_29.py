"""Information guaranteed by a finite partial function table.

The real function is NOT assumed polynomial.  Interpolating polynomials are
explicit compatible possibilities, sufficient to refute a claimed uniqueness
guarantee.  General finite-product/interpolation identities establish the
construction for every finite table; a bounded rational example also executes
the whole construction and lookup without reading answer text.
"""
from fractions import Fraction
import re
import sympy as S

from model_types import select_unique


def _record(value, fields):
    if not isinstance(value,dict) or set(value) != set(fields):
        raise ValueError('a complete typed record without extra fields is required')
    return value


def _q(value):
    if type(value) is int:
        result = Fraction(value)
    elif isinstance(value,str) and len(value) <= 64:
        number = r'[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)'
        if not re.fullmatch(number+'(?:/'+number+')?',value):
            raise ValueError('strict ASCII decimal/fraction syntax required')
        numerator,*denominator = value.split('/')
        result = Fraction(numerator)/(Fraction(denominator[0]) if denominator else 1)
    else:
        raise ValueError('a bounded exact rational is required')
    if max(abs(result.numerator).bit_length(),result.denominator.bit_length()) > 256:
        raise ValueError('number exceeds the arithmetic budget')
    return result


def _sym(value):
    return S.Rational(value.numerator,value.denominator)


class Interval:
    def __init__(self, spec):
        _record(spec,('left','right','left_closed','right_closed'))
        if type(spec['left_closed']) is not bool or type(spec['right_closed']) is not bool:
            raise ValueError('endpoint closure must be explicitly boolean')
        self.left = None if spec['left'] is None else _q(spec['left'])
        self.right = None if spec['right'] is None else _q(spec['right'])
        self.left_closed,self.right_closed = spec['left_closed'],spec['right_closed']
        if ((self.left is None and self.left_closed) or (self.right is None and self.right_closed)
                or (self.left is not None and self.right is not None and self.left >= self.right)):
            raise ValueError('a nondegenerate real interval with legal endpoints is required')

    def contains(self, value, interior=False):
        lower = (self.left is None or value > self.left
            or not interior and self.left_closed and value == self.left)
        upper = (self.right is None or value < self.right
            or not interior and self.right_closed and value == self.right)
        return lower and upper

    def unlisted_interior(self, inputs):
        # Every nondegenerate (possibly unbounded) interval contains an open
        # finite interval(a,b). Its n+1 distinct internal subdivision points
        # cannot all lie in a set of n listed inputs (pigeonhole principle).
        if self.left is not None and self.right is not None:
            a,b = self.left,self.right
        elif self.left is not None:
            a,b = self.left,self.left+1
        elif self.right is not None:
            a,b = self.right-1,self.right
        else:
            a,b = Fraction(-1),Fraction(1)
        n = len(inputs)
        candidates = tuple(a+(b-a)*Fraction(k+1,n+2) for k in range(n+1))
        if (len(set(candidates)) != n+1 or not all(self.contains(u,interior=True) for u in candidates)):
            raise ValueError('the interval subdivision proof failed')
        choices = [u for u in candidates if u not in inputs]
        if not choices:
            raise ValueError('the finite-set exclusion proof failed')
        return choices[0]


def _general_algebra_certificate():
    """Local identities used in induction on ANY finite number of inputs.

    Base P0=0,H0=1. For a new distinct input z, H(z)!=0 by finite
    nonzero-product closure. Updating P to P+(y-P(z))*H/H(z) interpolates
    the new row and leaves every old row unchanged; updating H to H*(x-z)
    preserves old zeros and creates the new zero. This is induction, not a
    test of finitely many degrees. The same uniqueness-free interpolant can
    equivalently be written in the Lagrange form used below.
    """
    h,k = S.symbols('h k',real=True,nonzero=True)
    p,y,c = S.symbols('p y c',real=True)
    if (S.cancel(p+(y-p)*h/h-y) != 0 or S.expand(p+c*0-p) != 0
            or (h*k).is_zero is not False):
        raise ValueError('the finite interpolation induction identities failed')
    x,u = S.symbols('x u',real=True)
    H = S.Function('H')
    derivative = S.diff((x-u)*H(x)**2,x).subs(x,u)
    if S.expand(derivative-H(u)**2) != 0:
        raise ValueError('the generic vanishing perturbation derivative failed')
    # At an unlisted interior u, h=H(u)!=0. The following identities prove
    # unequal values and opposite LOCAL trends of compatible functions.
    if (S.cancel((p+h)-p-h) != 0
            or S.cancel(p+(1-p)*h*h/(h*h)-1) != 0
            or S.cancel(p+(-1-p)*h*h/(h*h)+1) != 0
            or (h*h).is_positive is not True):
        raise ValueError('the generic counterfunction identities failed')


class PartialFunctionTable:
    def __init__(self, example):
        _general_algebra_certificate()
        _record(example,('interval','pairs'))
        self.interval = Interval(example['interval'])
        pairs = example['pairs']
        if not isinstance(pairs,list) or not 1 <= len(pairs) <= 16:
            raise ValueError('a bounded nonempty list of exact known pairs is required')
        self.lookup = {}
        original = []
        for pair in pairs:
            if not isinstance(pair,list) or len(pair) != 2:
                raise ValueError('each known row needs one input and one output')
            a,b = map(_q,pair)
            if not self.interval.contains(a):
                raise ValueError('a listed input is outside the function domain')
            if a in self.lookup and self.lookup[a] != b:
                raise ValueError('two different outputs contradict a function table')
            self.lookup[a] = b
            original.append((a,b))
        if len(self.lookup) > 8:
            raise ValueError('execution example exceeds the interpolation budget')
        self.rows = tuple(original)
        self.points = tuple(sorted(self.lookup.items()))
        self.lookup_preserved = all(self.lookup[a] == b for a,b in self.rows)
        self.witness = self.interval.unlisted_interior(self.lookup)
        self.x = S.Symbol('x',real=True)
        polynomial = S.Integer(0)
        H = S.Integer(1)
        for a,_ in self.points:
            H *= self.x-_sym(a)
        for a,b in self.points:
            basis = S.Integer(1)
            for c,_ in self.points:
                if c != a:
                    basis *= (self.x-_sym(c))/(_sym(a)-_sym(c))
            polynomial += _sym(b)*basis
        self.polynomial,self.vanishing = S.expand(polynomial),S.expand(H)
        u = _sym(self.witness)
        h = self.vanishing.subs(self.x,u)
        if h == 0:
            raise ValueError('the unlisted-point nonzero product failed')
        self.value_alternative = S.expand(self.polynomial+self.vanishing)
        d = S.diff(self.polynomial,self.x).subs(self.x,u)
        R = (self.x-u)*self.vanishing**2
        self.increasing = S.expand(self.polynomial+(1-d)*R/(h*h))
        self.decreasing = S.expand(self.polynomial+(-1-d)*R/(h*h))
        # All constructed possibilities are polynomials, hence continuous
        # with continuous derivative on the whole interval. Derivatives+1
        # and-1 at the interior witness imply opposite trends nearby.
        for candidate in (self.polynomial,self.value_alternative,self.increasing,self.decreasing):
            if any(S.cancel(candidate.subs(self.x,_sym(a))-_sym(b)) != 0 for a,b in self.points):
                raise ValueError('a counterfunction does not preserve every known pair')
        self.values_differ = S.cancel(self.value_alternative.subs(self.x,u)-self.polynomial.subs(self.x,u)).is_zero is False
        self.opposite_local_trends = (S.diff(self.increasing,self.x).subs(self.x,u) == 1
            and S.diff(self.decreasing,self.x).subs(self.x,u) == -1)
        if not self.lookup_preserved or not self.values_differ or not self.opposite_local_trends:
            raise ValueError('the complete information certificate failed')

    def claim(self, node):
        _record(node,('op',))
        if node['op'] == 'read_all_listed_values':
            return self.lookup_preserved
        if node['op'] == 'uniquely_determine_trend_everywhere':
            if not self.opposite_local_trends:
                raise ValueError('opposite local trends were not established')
            return False
        if node['op'] == 'table_lists_entire_interval_domain':
            if not self.interval.contains(self.witness,interior=True) or self.witness in self.lookup:
                raise ValueError('the omitted-domain-point proof failed')
            return False
        if node['op'] == 'uniquely_determine_every_unlisted_value':
            if not self.values_differ:
                raise ValueError('compatible different values were not established')
            return False
        raise ValueError('unknown information claim')


def partial_function_information(spec):
    _record(spec,('kind','premises','example','options'))
    if spec['kind'] != 'g29_partial_function_information':
        raise ValueError('a partial-function information proof is required')
    premises = _record(spec['premises'],('domain','known_pairs','additional_constraints'))
    if premises != {'domain':'nondegenerate_real_interval','known_pairs':'finite_nonempty_exact_pairs',
            'additional_constraints':'none'}:
        raise ValueError('the interval and absence of additional laws must be explicit')
    options = spec['options']
    if not isinstance(options,list) or not 1 <= len(options) <= 16:
        raise ValueError('bounded candidate definitions required')
    for option in options:
        _record(option,('key','text','claim'))
    proof = PartialFunctionTable(spec['example'])
    return select_unique(options,lambda option:proof.claim(option['claim']))


HANDLERS = {'g29_partial_function_information':partial_function_information}
