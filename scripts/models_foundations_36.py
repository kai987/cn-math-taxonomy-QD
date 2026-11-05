"""Complete dimensional reference proofs for a constant-outflow tank example.

This model verifies one possible interpretation of a formula, not every story
a student might give.  Its inputs are the source formula and a typed physical
interpretation.  Every number/unit/role/domain in the reference is parsed and
checked; no reference sentence or computed answer is supplied to the model.
"""
from fractions import Fraction
import re

from exact_polynomial import Polynomial
from model_types import SelfReferenceProof


_NUM = r'[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:/[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+))?'
_NUMERIC = str.maketrans('０１２３４５６７８９＋－．／−', '0123456789+-./-')
_PUNCTUATION = str.maketrans({'，': ',', '：': ':', '（': '(', '）': ')'})
_VOLUME = {'L': Fraction(1), '升': Fraction(1), 'mL': Fraction(1, 1000),
           '毫升': Fraction(1, 1000), 'm³': Fraction(1000), '立方米': Fraction(1000)}
_TIME = {'minute': Fraction(1), 'second': Fraction(1, 60), 'hour': Fraction(60)}
_TIME_WORD = {'分钟': Fraction(1), '秒': Fraction(1, 60), '小时': Fraction(60)}
_INTERPRETATION = {'system': 'tank', 'quantity': 'remaining_volume',
                   'flows': 'single_constant_outflow', 'time_origin': 'initial_state',
                   'domain': 'maximal_nonnegative_time_and_volume'}


def _record(value, fields):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise ValueError('a complete typed record without extra fields is required')
    return value


def _number(value):
    if not isinstance(value, str) or len(value) > 64 or re.fullmatch(_NUM, value) is None:
        raise ValueError('bounded exact decimal/fraction notation required')
    parts = value.split('/')
    result = Fraction(parts[0]) / (Fraction(parts[1]) if len(parts) == 2 else 1)
    if max(abs(result.numerator).bit_length(), result.denominator.bit_length()) > 256:
        raise ValueError('number exceeds the arithmetic budget')
    return result


def _unit(value, table):
    if not isinstance(value, str) or value not in table:
        raise ValueError('unsupported or dimensionally wrong unit')
    return table[value]


def _affine(expression, variable):
    if not isinstance(variable, str) or re.fullmatch('[a-z]', variable) is None:
        raise ValueError('one lower-case elapsed-time variable is required')
    if not isinstance(expression, str) or not 1 <= len(expression) <= 256:
        raise ValueError('a bounded source formula is required')
    source = expression.translate(_NUMERIC)
    if (re.fullmatch(r'[0-9a-z+*/().\s-]+', source) is None
            or re.search(r'[0-9]\s+[0-9]', source)
            or set(re.findall('[a-z]', source)) != {variable}):
        raise ValueError('unsupported numeric notation or undeclared formula variable')
    # Polynomial canonicalization can erase a variable-base zero power and
    # therefore its 0**0 hole.  This reference claims a whole closed interval
    # including t=0: conservatively reject all power syntax before parsing.
    # Remaining +,-,*,constant-division operations preserve the full real
    # source domain; the exact parser rejects nonconstant/zero denominators.
    if '**' in re.sub(r'\s+', '', source):
        raise ValueError('source powers need an original-domain proof and are unsupported')
    terms = Polynomial(source).terms
    if not set(terms) <= {(), (variable,)}:
        raise ValueError('remaining volume must be affine in elapsed time')
    initial, slope = terms.get((), Fraction(0)), terms.get((variable,), Fraction(0))
    if initial <= 0 or slope >= 0:
        raise ValueError('a positive initial tank volume and constant positive outflow are required')
    return initial, -slope


_V = '(?:' + '|'.join(sorted(map(re.escape, _VOLUME), key=len, reverse=True)) + ')'
_T = '(?:' + '|'.join(sorted(map(re.escape, _TIME_WORD), key=len, reverse=True)) + ')'
_REFERENCE = re.compile(
    r'\s*(?:(?:如|例如):\s*)?水箱原有\s*(?P<initial>' + _NUM + r')\s*(?P<initial_unit>' + _V + r')\s*水,\s*'
    r'每(?P<rate_time>' + _T + r')流出\s*(?P<rate>' + _NUM + r')\s*(?P<rate_volume>' + _V + r'),\s*'
    r'(?P<elapsed_variable>[a-z])\s*(?P<elapsed_unit>' + _T + r')后剩余的水量\s*\((?P<output_unit>' + _V + r')\)[。.]?\s*'
    r'\(此例中\s*(?P<lower>' + _NUM + r')\s*≤\s*(?P<domain_variable>[a-z])\s*≤\s*(?P<upper>' + _NUM + r'),\s*'
    r'(?P<unit_variable>[a-z])\s*的单位为(?P<domain_unit>' + _T + r')[。.]?\)[。.]?\s*'
)


class TankOutflowReferenceProof(SelfReferenceProof):
    """Derive conservation and the maximal physical time interval exactly."""

    def __init__(self, quantity, interpretation):
        quantity = _record(quantity, ('variable', 'expression', 'output_unit', 'input_unit'))
        interpretation = _record(interpretation, _INTERPRETATION)
        if interpretation != _INTERPRETATION:
            raise ValueError('remaining-volume, single-outflow and maximal physical-domain premises required')
        self.variable = quantity['variable']
        self.volume_unit = _unit(quantity['output_unit'], _VOLUME)
        self.time_unit = _unit(quantity['input_unit'], _TIME)
        initial, outflow = _affine(quantity['expression'], self.variable)
        self.initial_litres = initial * self.volume_unit
        self.outflow_litres_per_minute = outflow * self.volume_unit / self.time_unit
        self.horizon = initial / outflow
        # Dimensions: [outflow]=volume/time, hence [outflow*elapsed]=volume.
        # V(t)+q*t = V0 is an exact polynomial identity.  q>0 and V0>0
        # imply V(t)>=0,t>=0 iff 0<=t<=V0/q, with positive time length.
        self.initial = initial
        self.outflow = outflow
        if self.initial - self.outflow * self.horizon != 0 or self.horizon <= 0:
            raise ValueError('conservation or the nonempty physical interval was not proved')

    def matches(self, reference):
        try:
            if not isinstance(reference, str) or len(reference) > 1024:
                return False
            # No general NFKC: 3⁵/③ may not become35/3.  A Chinese sentence
            # stop remains punctuation; the whole grammar must consume it.
            text = reference.translate(_NUMERIC).translate(_PUNCTUATION)
            text = text.replace('<=', '≤')
            match = _REFERENCE.fullmatch(text)
            if match is None:
                return False
            data = match.groupdict()
            if any(data[key] != self.variable for key in ('elapsed_variable', 'domain_variable', 'unit_variable')):
                return False
            initial = _number(data['initial']) * _unit(data['initial_unit'], _VOLUME)
            outflow = (_number(data['rate']) * _unit(data['rate_volume'], _VOLUME)
                       / _unit(data['rate_time'], _TIME_WORD))
            return (initial == self.initial_litres and outflow == self.outflow_litres_per_minute
                    and _unit(data['output_unit'], _VOLUME) == self.volume_unit
                    and _unit(data['elapsed_unit'], _TIME_WORD) == self.time_unit
                    and _unit(data['domain_unit'], _TIME_WORD) == self.time_unit
                    and _number(data['lower']) == 0 and _number(data['upper']) == self.horizon)
        except (ValueError, TypeError, ArithmeticError):
            return False


def tank_outflow_reference(spec):
    _record(spec, ('kind', 'reference_only', 'quantity_function', 'interpretation'))
    if spec['kind'] != 'f36_tank_outflow_reference' or spec['reference_only'] is not True:
        raise ValueError('a typed reference-only tank proof is required')
    return TankOutflowReferenceProof(spec['quantity_function'], spec['interpretation'])


HANDLERS = {'f36_tank_outflow_reference': tank_outflow_reference}
