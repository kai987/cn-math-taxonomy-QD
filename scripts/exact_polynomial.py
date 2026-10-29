"""Small, bounded exact polynomial parser for offline reference-answer checks.

This never evaluates source code. It accepts single-letter variables, rational
coefficients and + - * / ** (division by a nonzero constant only). Coefficients
are Fractions; equality compares every coefficient, rather than sample points.
"""
import ast
from fractions import Fraction
import re

MAX_DEGREE = 8
MAX_TERMS = 128


def _bounded(terms):
    terms = {monomial: value for monomial, value in terms.items() if value}
    if (len(terms) > MAX_TERMS or any(len(m) > MAX_DEGREE for m in terms)
            or any(abs(c.numerator) > 10**15 or c.denominator > 10**15 for c in terms.values())):
        raise ValueError('polynomial exceeds exact-check limits')
    return terms


def _add(left, right, sign=1):
    result = dict(left)
    for monomial, value in right.items():
        result[monomial] = result.get(monomial, Fraction(0)) + sign * value
    return _bounded(result)


def _multiply(left, right):
    result = {}
    for lm, lv in left.items():
        for rm, rv in right.items():
            monomial = tuple(sorted(lm + rm))
            result[monomial] = result.get(monomial, Fraction(0)) + lv * rv
    return _bounded(result)


def _source(expression):
    if not isinstance(expression, str) or not expression.strip() or len(expression) > 256:
        raise ValueError('empty or oversized polynomial')
    source = expression.replace(' ', '').replace('−', '-').replace('·', '*')
    source = re.sub('[⁰¹²³⁴⁵⁶⁷⁸⁹]+', lambda m: '**' + m[0].translate(
        str.maketrans('⁰¹²³⁴⁵⁶⁷⁸⁹', '0123456789')), source).replace('^', '**')
    if re.search(r'(?:sqrt|sin|cos|tan|log|exp|abs|pow)\(', source):
        raise ValueError('function notation is not supported')
    tokens = re.findall(r'\d+(?:\.\d+)?|[a-z]|\*\*|[()+*/-]', source)
    if ''.join(tokens) != source or len(tokens) > 120:
        raise ValueError('unsupported polynomial notation')
    output = []
    for token in tokens:
        if output:
            before = output[-1]
            if (before == ')' or re.fullmatch(r'[a-z]|\d+(?:\.\d+)?', before)) and (
                    token == '(' or re.fullmatch(r'[a-z]', token)):
                output.append('*')
        output.append(token)
    return ''.join(output)


def _parse(expression):
    source = _source(expression)
    tree = ast.parse(source, mode='eval')

    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            # AST float values have already rounded long decimal literals.
            # Parse their original decimal token, never that rounded float.
            return _bounded({(): Fraction(ast.get_source_segment(source, node))})
        if isinstance(node, ast.Name) and re.fullmatch('[a-z]', node.id):
            return {(node.id,): Fraction(1)}
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            return {m: c * (-1 if isinstance(node.op, ast.USub) else 1) for m, c in visit(node.operand).items()}
        if isinstance(node, ast.BinOp):
            left = visit(node.left)
            if isinstance(node.op, ast.Pow):
                if not (isinstance(node.right, ast.Constant) and type(node.right.value) is int
                        and 0 <= node.right.value <= MAX_DEGREE):
                    raise ValueError('power must be a bounded nonnegative integer')
                if not left and node.right.value == 0:
                    raise ValueError('zero to the zero power is undefined in this checker')
                result = {(): Fraction(1)}
                for _ in range(node.right.value):
                    result = _multiply(result, left)
                return result
            right = visit(node.right)
            if isinstance(node.op, ast.Add):
                return _add(left, right)
            if isinstance(node.op, ast.Sub):
                return _add(left, right, -1)
            if isinstance(node.op, ast.Mult):
                return _multiply(left, right)
            if isinstance(node.op, ast.Div) and set(right) == {()}:
                return _bounded({m: c / right[()] for m, c in left.items()})
        raise ValueError('unsupported polynomial operation')

    return visit(tree.body)


class Polynomial:
    def __init__(self, expression, dependent=None):
        if dependent is not None and not re.fullmatch('[a-z]', dependent):
            raise ValueError('dependent variable must be a single letter')
        self.terms = _parse(expression)
        self.dependent = dependent
        if dependent and any(dependent in m for m in self.terms):
            raise ValueError('dependent variable occurs on right-hand side')

    def matches(self, text):
        text = text.strip()
        expressions = [text]
        if self.dependent:
            parts = text.split('=')
            if len(parts) >= 2 and parts[0].strip() == self.dependent:
                expressions = parts[1:]
            elif len(parts) != 1:
                return False
        try:
            return all(self.terms == _parse(expression) for expression in expressions)
        except (ValueError, SyntaxError, ZeroDivisionError, RecursionError):
            return False

    def __repr__(self):
        return 'Polynomial(%r, dependent=%r)' % (self.terms, self.dependent)


def poly(expression, dependent=None):
    return Polynomial(expression, dependent)
