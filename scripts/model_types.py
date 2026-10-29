"""Proof results and strict reference-format parsers for offline math models.

These parsers compare reference-answer meaning after a model has computed it.
They are not the browser's permissive answer grader, and never solve prompts.
"""
from fractions import Fraction
import re
import unicodedata


def plain(value):
    if not isinstance(value, str) or len(value) > 2048:
        raise ValueError('invalid reference text')
    digits = str.maketrans('⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻', '0123456789+-')
    value = re.sub('[⁺⁻]?[⁰¹²³⁴⁵⁶⁷⁸⁹]+', lambda m: '^' + m[0].translate(digits), value)
    value = unicodedata.normalize('NFKC', value).replace('−', '-').replace('。', '.')
    if re.search(r'\d\s+\d', value):
        raise ValueError('digit-separated whitespace is ambiguous')
    value = re.sub(r'\s+', '', value)
    value = value.replace('<=', '≤').replace('>=', '≥').replace('!=', '≠')
    return value[:-1] if value.endswith('.') and not value.endswith('..') else value


def fraction(value):
    if isinstance(value, bool):
        raise ValueError('boolean is not a measurement')
    if isinstance(value, (int, Fraction)):
        return Fraction(value)
    text = plain(str(value))
    if not re.fullmatch(r'[+-]?(?:\d+(?:\.\d+)?|\.\d+)(?:/[+-]?(?:\d+(?:\.\d+)?|\.\d+))?', text):
        raise ValueError('expected a rational number')
    parts = text.split('/')
    return Fraction(parts[0]) / (Fraction(parts[1]) if len(parts) == 2 else 1)


def relation(value):
    if isinstance(value, (list, tuple)) and len(value) == 3:
        variable, operator, number = value
    else:
        text = plain(value)
        for phrase, symbol in (('不等于', '≠'), ('大于等于', '≥'), ('小于等于', '≤'), ('大于', '>'), ('小于', '<')):
            text = text.replace(phrase, symbol)
        match = re.fullmatch(r'([a-z])([<>=≤≥≠])(.+)', text)
        if match:
            variable, operator, number = match.groups()
        else:
            match = re.fullmatch(r'(.+)([<>=≤≥≠])([a-z])', text)
            if not match:
                raise ValueError('unsupported relation')
            number, operator, variable = match.groups()
            operator = {'<': '>', '>': '<', '≤': '≥', '≥': '≤', '=': '=', '≠': '≠'}[operator]
    if not isinstance(operator, str):
        raise ValueError('unsupported comparator')
    operator = plain(operator)
    if not isinstance(variable, str) or not re.fullmatch('[a-z]', variable) or operator not in {'<', '>', '=', '≤', '≥', '≠'}:
        raise ValueError('unsupported variable or comparator')
    return variable, operator, fraction(number)


def coordinates(value):
    if isinstance(value, (list, tuple)):
        points = value if value and isinstance(value[0], (list, tuple)) else [value]
        if not points or any(len(point) != 2 for point in points):
            raise ValueError('expected ordered coordinate pairs')
        return tuple(tuple(fraction(item) for item in point) for point in points)
    text = plain(value).replace('、', ',').replace('和', ',')
    chunks = re.findall(r'\(([^(),]+),([^(),]+)\)', text)
    if not chunks or ','.join('(%s,%s)' % chunk for chunk in chunks) != text:
        raise ValueError('invalid coordinate structure')
    return tuple((fraction(x), fraction(y)) for x, y in chunks)


def word(value):
    text = plain(value)
    aliases = {
        '是的': '是', '否': '不是',
        '直角': '直角三角形', '不可能': '不可能事件',
    }
    if re.fullmatch('△?[A-Za-z]{3}', text):
        return text.removeprefix('△').upper()
    return aliases.get(text, text)


def contextual_yes_no(value, context):
    text = plain(value)
    if text == {'like_terms': '是同类项', 'equation_solution': '是方程的解'}[context]:
        return '是'
    return word(text)


def ordered_words(value):
    if isinstance(value, (list, tuple)):
        parts = list(value)
    else:
        text = plain(value).replace('、', ',')
        if '>' in text and ',' in text:
            raise ValueError('mixed ordering separators')
        parts = re.split('[>,]', text)
    if not parts or any(not isinstance(part, str) or not part for part in parts):
        raise ValueError('empty ordered item')
    # Only a finite, reviewed colour vocabulary has this noun alias.
    return tuple(part[:-1] if part in ('红球', '白球', '黄球') else part for part in parts)


def identity_equation(value):
    parts = plain(value).split('=')
    if len(parts) != 2 or not all(parts):
        raise ValueError('expected exactly one equation')
    return tuple(sorted(parts))


def equation_classification(value):
    if isinstance(value, dict):
        answer, degree = value.get('answer'), value.get('degree')
        if type(answer) is not bool or type(degree) is not int or degree < 0:
            raise ValueError('missing proved classification/degree')
        return answer, degree
    text = plain(value)
    simple = word(text)
    if simple in ('是', '不是'):
        return simple == '是', None
    match = re.fullmatch(r'(是|不是),未知数次数为(\d+)', text)
    if not match:
        raise ValueError('unsupported classification explanation')
    return match[1] == '是', int(match[2])


NORMALIZERS = {'exact': plain, 'word': word, 'relation': relation,
               'coordinates': coordinates, 'ordered_words': ordered_words,
               'identity_equation': identity_equation, 'equation_classification': equation_classification,
               'like_terms': lambda value: contextual_yes_no(value, 'like_terms'),
               'equation_solution': lambda value: contextual_yes_no(value, 'equation_solution')}


class TextProof:
    def __init__(self, value, normalizer='exact'):
        if normalizer not in NORMALIZERS:
            raise ValueError('unknown proof normalizer: ' + str(normalizer))
        self.normalizer = normalizer
        self.value = NORMALIZERS[normalizer](value)

    def matches(self, reference):
        try:
            actual = NORMALIZERS[self.normalizer](reference)
            if self.normalizer == 'equation_classification':
                return actual[0] == self.value[0] and (actual[1] is None or actual[1] == self.value[1])
            return actual == self.value
        except (ValueError, TypeError, ZeroDivisionError):
            return False

    def __repr__(self):
        return 'TextProof(%r, %r)' % (self.value, self.normalizer)


def select_unique(options, predicate):
    if not isinstance(options, list) or not options:
        raise ValueError('model needs candidate options')
    keys = [option.get('key') for option in options]
    if len(set(keys)) != len(keys) or any(not isinstance(key, str) for key in keys):
        raise ValueError('candidate keys must be unique strings')
    matches = []
    for option in options:
        if not isinstance(option.get('text'), str) or not option['text']:
            raise ValueError('missing candidate text')
        result = predicate(option)
        if type(result) is not bool:
            raise ValueError('candidate is unresolved, not proved false')
        if result:
            matches.append(option['text'])
    if len(matches) != 1:
        raise ValueError('model must prove exactly one candidate; got %d' % len(matches))
    return matches[0]
