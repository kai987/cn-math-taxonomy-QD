"""Executable rectangle/projection proof for a frequency-height histogram.

Candidate axes are mathematical quantity programs, not answer labels.  Each
program is evaluated on the example and interpreted on a generic bin.  A
successful contract is an exact symbolic identity for arbitrary bin origins,
positive widths and nonnegative integer frequencies.  Nonidentities need a
legal counterexample as well; one coincident numeric table is never a proof.
"""
from dataclasses import dataclass
from fractions import Fraction
import re
import sympy as S

from model_types import select_unique


def _record(value, fields):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise ValueError('a complete typed object without extra fields is required')
    return value


def _rational(value):
    if type(value) is int:
        result = Fraction(value)
    elif isinstance(value, str) and len(value) <= 64:
        number = r'[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)'
        if not re.fullmatch(number + '(?:/' + number + ')?', value):
            raise ValueError('strict ASCII decimal/fraction notation required')
        first, *second = value.split('/')
        result = Fraction(first) / (Fraction(second[0]) if second else 1)
    else:
        raise ValueError('bounded exact rational required')
    if max(abs(result.numerator).bit_length(), result.denominator.bit_length()) > 256:
        raise ValueError('number outside the exact arithmetic budget')
    return result


def _count(value):
    if type(value) is not int or value < 0 or value.bit_length() > 256:
        raise ValueError('a bounded nonnegative integer cardinality is required')
    return value


# These symbols are created internally, never parsed from an input string.
_L = S.Symbol('l', real=True)
_W = S.Symbol('w', positive=True)
_F = S.Symbol('f', integer=True, nonnegative=True)
_G = S.Symbol('g', integer=True, nonnegative=True)
_N = S.Symbol('n', integer=True, positive=True)


def _same(left, right):
    if len(left) != len(right):
        return False
    return all(S.cancel(a-b) == 0 for a, b in zip(left, right))


def _rectangle(left, right, frequency, bin_axis):
    points = ((left, 0), (right, 0), (right, frequency), (left, frequency))
    return points if bin_axis == 'x' else tuple((y, x) for x, y in points)


def _projection(vertices, axis):
    index = {'x': 0, 'y': 1}[axis]
    coordinates = [p[index] for p in vertices]
    return S.Min(*coordinates), S.Max(*coordinates)


class Histogram:
    """Construct every bar and decode its bin endpoints and cardinality."""
    def __init__(self, table, bin_axis):
        _record(table, ('endpoints', 'frequencies'))
        if bin_axis not in ('x', 'y'):
            raise ValueError('one coordinate must index the bins')
        endpoints, frequencies = table['endpoints'], table['frequencies']
        if (not isinstance(endpoints, list) or not 2 <= len(endpoints) <= 65
                or not isinstance(frequencies, list) or len(frequencies) != len(endpoints)-1):
            raise ValueError('one frequency for every adjacent endpoint pair is required')
        self.endpoints = tuple(_rational(v) for v in endpoints)
        self.frequencies = tuple(_count(v) for v in frequencies)
        self.widths = tuple(b-a for a, b in zip(self.endpoints, self.endpoints[1:]))
        if any(w <= 0 for w in self.widths) or len(set(self.widths)) != 1:
            raise ValueError('strictly increasing contiguous equal-width bins are required')
        self.total = sum(self.frequencies)
        if self.total == 0:
            raise ValueError('a nonempty dataset is needed to define the frequency-ratio candidate')
        self.bin_axis, self.count_axis = bin_axis, 'y' if bin_axis == 'x' else 'x'
        self.intervals = tuple(zip(self.endpoints, self.endpoints[1:]))
        self.bars = tuple(_rectangle(a,b,f,bin_axis)
            for (a,b),f in zip(self.intervals,self.frequencies))
        self.projections = {axis: tuple(tuple(Fraction(v) for v in _projection(bar,axis))
            for bar in self.bars) for axis in ('x','y')}
        decoded_intervals = self.projections[self.bin_axis]
        decoded_counts = tuple(hi-lo for lo,hi in self.projections[self.count_axis])
        if decoded_intervals != self.intervals or decoded_counts != self.frequencies:
            raise ValueError('the coordinate projections did not reconstruct the complete table')
        if any(lo != 0 for lo,_ in self.projections[self.count_axis]):
            raise ValueError('the count coordinate lost its zero origin')


@dataclass(frozen=True)
class Field:
    scope: str
    form: str
    symbolic: object
    values: object

    def generic_projection(self):
        return self.symbolic if self.form == 'intervals' else (S.Integer(0),self.symbolic)

    def projections(self, count):
        if self.form == 'intervals':
            return self.values
        values = self.values if self.scope == 'per_bin' else (self.values,)*count
        return tuple((Fraction(0),v) for v in values)


def quantity(node, table, budget=None):
    """Execute a bounded quantity language and derive its scope/value shape."""
    if budget is None:
        budget = [0]
    budget[0] += 1
    if budget[0] > 24 or not isinstance(node,dict):
        raise ValueError('a bounded mathematical quantity tree is required')
    op = node.get('op')
    if op == 'bin_intervals':
        _record(node, ('op',))
        return Field('per_bin','intervals',(_L,_L+_W),table.intervals)
    if op == 'cardinality':
        _record(node, ('op','of'))
        collection = _record(node['of'],('op',))['op']
        if collection == 'bin_members':
            # Model each bin's disjoint observation set as {(i,j):0<=j<f_i}.
            # Its cardinality is f_i even for zero frequencies; no set of
            # measured values is used, so equal observations are not lost.
            return Field('per_bin','scalars',_F,tuple(Fraction(v) for v in table.frequencies))
        if collection == 'all_members':
            return Field('global','scalars',_F+_G,Fraction(table.total))
        if collection == 'bins':
            return Field('global','scalars',_N,Fraction(len(table.frequencies)))
        raise ValueError('unknown finite collection')
    if op == 'length':
        _record(node, ('op','of'))
        intervals = quantity(node['of'],table,budget)
        if intervals.form != 'intervals' or intervals.scope != 'per_bin':
            raise ValueError('interval length requires the bin intervals')
        return Field('per_bin','scalars',intervals.symbolic[1]-intervals.symbolic[0],
            tuple(b-a for a,b in intervals.values))
    if op == 'divide':
        _record(node, ('op','numerator','denominator'))
        numerator = quantity(node['numerator'],table,budget)
        denominator = quantity(node['denominator'],table,budget)
        if (numerator.form != 'scalars' or denominator.form != 'scalars'
                or denominator.scope != 'global' or denominator.values <= 0):
            raise ValueError('a scalar quotient needs an explicitly positive global divisor')
        values = (tuple(v/denominator.values for v in numerator.values)
            if numerator.scope == 'per_bin' else numerator.values/denominator.values)
        return Field(numerator.scope,'scalars',numerator.symbolic/denominator.symbolic,values)
    raise ValueError('unknown mathematical quantity operation')


def histogram_axes(spec):
    _record(spec, ('kind','construction','example','counterexample','options'))
    if spec['kind'] != 'g33_histogram_axis_encoding':
        raise ValueError('a histogram projection proof is required')
    options = spec['options']
    if not isinstance(options,list) or not 1 <= len(options) <= 16:
        raise ValueError('a bounded nonempty candidate list is required')
    for option in options:
        _record(option, ('key','text','axes'))
    construction = _record(spec['construction'],('shape','bin_axis','frequency_origin','frequency_scale','bin_spacing'))
    if (construction['shape'] != 'axis_aligned_rectangles' or construction['bin_spacing'] != 'equal_width'
            or _rational(construction['frequency_origin']) != 0
            or _rational(construction['frequency_scale']) != 1):
        raise ValueError('the direct zero-origin frequency-height construction must be explicit')
    example = Histogram(spec['example'],construction['bin_axis'])
    witness = Histogram(spec['counterexample'],construction['bin_axis'])
    generic = _rectangle(_L,_L+_W,_F,example.bin_axis)
    projected = {axis:_projection(generic,axis) for axis in ('x','y')}
    # W>0,F>=0 make these Min/Max identities true for every bin.  They also
    # prove decoding is left inverse for arbitrary origins, widths and counts;
    # the concrete example above is execution evidence, not a sampled proof.
    if (not _same(projected[example.bin_axis],(_L,_L+_W))
            or not _same(projected[example.count_axis],(0,_F))):
        raise ValueError('the universal projection/reconstruction identities failed')
    def check(option):
        _record(option, ('key','text','axes'))
        axes = _record(option['axes'],('x','y'))
        # Evaluate every coordinate and both tables before deciding false.
        fields = {axis:quantity(axes[axis],example) for axis in ('x','y')}
        counterfields = {axis:quantity(axes[axis],witness) for axis in ('x','y')}
        identical = [_same(fields[axis].generic_projection(),projected[axis]) for axis in ('x','y')]
        for axis,is_identity in zip(('x','y'),identical):
            actual = fields[axis].projections(len(example.frequencies))
            counter = counterfields[axis].projections(len(witness.frequencies))
            if is_identity:
                if actual != example.projections[axis] or counter != witness.projections[axis]:
                    raise ValueError('a claimed universal quantity contract failed reconstruction')
            elif counter == witness.projections[axis]:
                raise ValueError('nonidentity alone is insufficient; a legal counterexample is required')
        return all(identical)
    return select_unique(options,check)


HANDLERS = {'g33_histogram_axis_encoding':histogram_axes}
