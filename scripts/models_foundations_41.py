"""Exact reference-only verification of rational-number classifications.

The mathematical input contains the given numbers and category definitions,
never the reference's classified lists.  The proof computes every membership
and compares a strictly parsed reference with the complete result, including
multiplicity.  It does not grade the browser's free-form self responses.
"""
from collections import Counter
from fractions import Fraction
import re

from model_types import SelfReferenceProof, fraction


_DEFINITIONS = {'正数': '>', '0': '=', '负数': '<'}
_ORDER = tuple(_DEFINITIONS)
_LIMIT = 128
_NUMERIC_TRANSLATION = str.maketrans('０１２３４５６７８９＋－．／−', '0123456789+-./-')
_REFERENCE_TRANSLATION = str.maketrans({'，': ',', '；': ';', '：': ':'})
_RATIONAL = r'[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:/[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+))?'


def _number(value):
    if type(value) is not int and not isinstance(value, str):
        raise ValueError('exact rational integers or strings required')
    if len(str(value)) > _LIMIT:
        raise ValueError('rational representation is too large')
    text = str(value).translate(_NUMERIC_TRANSLATION)
    # Check the original numeric tokens before the shared parser's broader
    # text normalization.  NFKC would turn 3⁵ into35; Chinese sentence stops
    # must not be interpreted as decimal points.  Neither is a rational token.
    if re.fullmatch(_RATIONAL, text) is None:
        raise ValueError('unsupported exact rational notation')
    return fraction(text)


def _reference_groups(reference):
    if not isinstance(reference, str) or len(reference) > 4096:
        raise ValueError('bounded classification reference text required')
    text = reference.translate(_NUMERIC_TRANSLATION).translate(_REFERENCE_TRANSLATION)
    # Do not join separated numerals ("3 5") or separated signs/fractions.
    # Surrounding whitespace is accepted only around structural separators.
    text = text.strip()
    groups = {}
    parts = text.split(';')
    if len(parts) != len(_ORDER):
        raise ValueError('each of the three sign classes is required once')
    for part in parts:
        match = re.fullmatch(r'\s*(正数|0|负数)\s*:\s*(.*?)\s*', part)
        if not match:
            raise ValueError('unknown class label or reference structure')
        label, items = match.groups()
        if label in groups:
            raise ValueError('duplicate class label')
        if items in ('无', '∅'):
            values = []
        else:
            tokens = [item.strip() for item in items.split(',')]
            if not tokens or len(tokens) > _LIMIT or any(not token for token in tokens):
                raise ValueError('empty or excessive reference items')
            # A number may not contain whitespace; this also rejects "- 2"
            # and "1 / 3" rather than guessing their intended tokenization.
            if any(re.search(r'\s', token) for token in tokens):
                raise ValueError('ambiguous whitespace inside a number')
            values = [_number(token) for token in tokens]
        groups[label] = Counter(values)
    if set(groups) != set(_ORDER):
        raise ValueError('missing sign category')
    return groups


class RationalSignPartitionProof(SelfReferenceProof):
    """Compare the whole reference partition, with no student-scoring effect."""

    def __init__(self, values):
        if (not isinstance(values, (list, tuple)) or not 1 <= len(values) <= _LIMIT
                or any(type(value) is not Fraction for value in values)):
            raise ValueError('computed exact rational values are required')
        groups = {label: Counter() for label in _ORDER}
        for value in values:
            if value > 0:
                groups['正数'][value] += 1
            elif value == 0:
                groups['0'][value] += 1
            else:
                groups['负数'][value] += 1
        self._groups = groups

    def matches(self, reference):
        try:
            return _reference_groups(reference) == self._groups
        except (ValueError, TypeError, ZeroDivisionError):
            return False

    def __repr__(self):
        return 'RationalSignPartitionProof(%r)' % self._groups


def rational_sign_partition(spec):
    if (not isinstance(spec, dict) or set(spec) != {'kind', 'numbers', 'classes'}
            or spec.get('kind') != 'f41_rational_sign_partition'):
        raise ValueError('given numbers and explicit category definitions required')
    numbers, classes = spec['numbers'], spec['classes']
    if not isinstance(numbers, list) or not 1 <= len(numbers) <= _LIMIT:
        raise ValueError('a bounded nonempty list of given numbers is required')
    if not isinstance(classes, list) or len(classes) != len(_ORDER):
        raise ValueError('all sign definitions are required')
    seen = set()
    for category in classes:
        if not isinstance(category, dict) or set(category) != {'label', 'relation', 'cutoff'}:
            raise ValueError('explicit mathematical class definition required')
        label = category['label']
        if not isinstance(label, str) or label not in _DEFINITIONS or label in seen:
            raise ValueError('unknown, repeated or missing sign category')
        if category['relation'] != _DEFINITIONS[label] or _number(category['cutoff']) != 0:
            raise ValueError('a sign category must use its defining relation to zero')
        seen.add(label)
    # Exact trichotomy of rational order makes the three classes disjoint and
    # exhaustive.  Every given occurrence is retained, including duplicates.
    values = [_number(number) for number in numbers]
    return RationalSignPartitionProof(values)


HANDLERS = {'f41_rational_sign_partition': rational_sign_partition}
