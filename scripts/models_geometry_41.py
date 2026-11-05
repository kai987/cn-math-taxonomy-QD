"""Complete affine reference proofs for the41-question review.

The input is a typed mathematical object, never a stored answer.  The output
checks every claim in a small, whole-reference grammar; it is deliberately not
a student free-text grader.  Unrecognised prose and extra assertions reject.
All arithmetic and one-dimensional feasibility decisions are exact.
"""
from fractions import Fraction
import re

from model_types import SelfReferenceProof, fraction


def _record(value, fields):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise ValueError('complete typed object required, without extra fields')
    return value


def _name(value):
    if not isinstance(value, str) or not re.fullmatch('[a-z]', value):
        raise ValueError('single lower-case coordinate name required')
    return value


def _rational(value):
    if type(value) not in (int, str, Fraction) or isinstance(value, str) and len(value) > 64:
        raise ValueError('bounded exact rational required')
    if isinstance(value, str):
        # Check the original spelling BEFORE broad reference normalisation:
        # a Chinese sentence stop must not become a decimal point, nor may a
        # superscript/NFKC digit turn into an ordinary integer digit.
        number = r'[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)'
        if not re.fullmatch(number + r'(?:\s*/\s*' + number + r')?', value.strip()):
            raise ValueError('ASCII rational numeric syntax required')
    result = fraction(value)
    if max(abs(result.numerator).bit_length(), result.denominator.bit_length()) > 256:
        raise ValueError('rational outside the arithmetic budget')
    return result


def _function(value):
    obj = _record(value, ('independent', 'dependent', 'slope', 'intercept', 'domain'))
    x, y = _name(obj['independent']), _name(obj['dependent'])
    if x == y or obj['domain'] != 'all_real':
        raise ValueError('two distinct coordinates and a full real domain required')
    slope, intercept = _rational(obj['slope']), _rational(obj['intercept'])
    if slope == 0:
        raise ValueError('a nonconstant affine function is required')
    return x, y, slope, intercept


def _strict_affine_feasible(constraints):
    """Decide existence of real x with m*x+c>0 for EVERY input pair.

    Each nonconstant constraint is exactly an open lower or upper half-line.
    Their intersection is nonempty iff its greatest lower endpoint is strictly
    below its least upper endpoint (or the relevant endpoint is unbounded).
    This proves both existence and nonexistence; it is not finite sampling.
    """
    lower = upper = None
    impossible = False
    for m, c in constraints:
        m, c = _rational(m), _rational(c)
        if m == 0:
            if c <= 0:
                impossible = True
        elif m > 0:
            endpoint = -c / m
            lower = endpoint if lower is None else max(lower, endpoint)
        else:
            endpoint = -c / m
            upper = endpoint if upper is None else min(upper, endpoint)
    return not impossible and (lower is None or upper is None or lower < upper)


def _reference(value):
    if not isinstance(value, str) or len(value) > 256:
        raise ValueError('bounded complete reference text required')
    # A single terminal Chinese stop is punctuation.  An interior one is a
    # sentence boundary, never the decimal point in e.g. "3。5".
    if '。' in value.rstrip().removesuffix('。'):
        raise ValueError('interior sentence stop is not a decimal point')
    # Apply only reviewed typography substitutions.  General NFKC also turns
    # circled/superscript numerals into ordinary digits, which can silently
    # change a reference's numeric spelling before the strict parser sees it.
    ascii_characters = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ+-/.,;'
    table = {ord(chr(ord(c) + 0xFEE0)): c for c in ascii_characters}
    table[ord('−')] = '-'
    text = value.translate(table)
    if re.search(r'[0-9]\s+[0-9]', text):
        raise ValueError('digit-separated whitespace is ambiguous')
    text = re.sub(r'\s+', '', text)
    if text.endswith('。'):
        text = text[:-1]
    elif text.endswith('.') and not text.endswith('..'):
        text = text[:-1]
    return text


class AffineMonotonicQuadrantsProof(SelfReferenceProof):
    """Derive both global monotonicity and the exact open-quadrant set."""

    def __init__(self, function):
        self.x, self.y, self.slope, self.intercept = _function(function)
        # For any x2>x1, f(x2)-f(x1)=a*(x2-x1), whose sign is sign(a).
        self.direction = 1 if self.slope > 0 else -1
        signs = ((1, 1), (-1, 1), (-1, -1), (1, -1))
        self.quadrants = frozenset(index for index, (sx, sy) in enumerate(signs, 1)
            if _strict_affine_feasible(((sx, 0), (sy * self.slope, sy * self.intercept))))

    def _monotonic(self, text):
        match = re.fullmatch(self.y + '随' + self.x + '增大而(增大|减小)', text)
        if match:
            return 1 if match[1] == '增大' else -1
        aliases = {'递增': 1, '单调递增': 1, '递减': -1, '单调递减': -1}
        if text in aliases:
            return aliases[text]
        raise ValueError('unsupported complete monotonicity clause')

    def _quadrants(self, text):
        match = re.fullmatch(r'(?:图象)?经过(第?[一二三四1234](?:[、,]第?[一二三四1234])*)象限', text)
        if not match:
            raise ValueError('unsupported exhaustive quadrant clause')
        aliases = dict(zip('一二三四1234', (1, 2, 3, 4, 1, 2, 3, 4)))
        values = [aliases[part.removeprefix('第')] for part in re.split('[、,]', match[1])]
        if len(set(values)) != len(values):
            raise ValueError('duplicate quadrant is not a complete set description')
        return frozenset(values)

    def matches(self, reference):
        try:
            parts = _reference(reference).split(';')
            if len(parts) != 2:
                return False
            # Clause order is immaterial, but neither component may be omitted
            # or replaced by a second copy of the other component.
            if '经过' in parts[0]:
                parts.reverse()
            return self._monotonic(parts[0]) == self.direction and self._quadrants(parts[1]) == self.quadrants
        except (ValueError, TypeError, ArithmeticError):
            return False


class AxisEquationProof(SelfReferenceProof):
    """Independently derive a graph's horizontal-axis coordinate and a root."""

    def __init__(self, function, axis, equation):
        self.x, self.y, a, b = _function(function)
        axis = _record(axis, ('zero_coordinate', 'reported_coordinate'))
        if axis != {'zero_coordinate': self.y, 'reported_coordinate': self.x}:
            raise ValueError('the horizontal-axis intersection abscissa is required')
        equation = _record(equation, ('variable', 'slope', 'intercept', 'rhs', 'domain'))
        if equation['variable'] != self.x or equation['domain'] != 'all_real':
            raise ValueError('equation must use the same unrestricted independent variable')
        m, c, rhs = (_rational(equation[key]) for key in ('slope', 'intercept', 'rhs'))
        if m == 0:
            raise ValueError('a unique equation root is required')
        # y=0 iff a*x+b=0 iff x=-b/a (a!=0).  Independently,
        # m*x+c=rhs iff x=(rhs-c)/m (m!=0).  These implications are reversible
        # over all reals.  No stored relation or numeric answer is an input.
        self.coordinate = -b / a
        self.equation_root = (rhs - c) / m
        self.same = self.coordinate == self.equation_root

    def matches(self, reference):
        try:
            text = _reference(reference)
            equal = re.fullmatch(r'(?:相等|相同),(?:都是|均为)([^,、;]+)', text)
            if equal:
                return self.same and _rational(equal[1]) == self.coordinate
            different = re.fullmatch(r'不相等,分别为([^,、;]+)[,、]([^,、;]+)', text)
            if different:
                return (not self.same and _rational(different[1]) == self.coordinate
                    and _rational(different[2]) == self.equation_root)
            return False
        except (ValueError, TypeError, ArithmeticError):
            return False


def affine_reference(spec):
    _record(spec, ('kind', 'reference_only', 'function'))
    if spec['kind'] != 'g41_affine_monotonic_quadrants_reference' or spec['reference_only'] is not True:
        raise ValueError('reference-only affine proof kind required')
    return AffineMonotonicQuadrantsProof(spec['function'])


def axis_equation_reference(spec):
    _record(spec, ('kind', 'reference_only', 'function', 'axis', 'equation'))
    if spec['kind'] != 'g41_axis_equation_reference' or spec['reference_only'] is not True:
        raise ValueError('reference-only axis/equation proof kind required')
    return AxisEquationProof(spec['function'], spec['axis'], spec['equation'])


HANDLERS = {
    'g41_affine_monotonic_quadrants_reference': affine_reference,
    'g41_axis_equation_reference': axis_equation_reference,
}
