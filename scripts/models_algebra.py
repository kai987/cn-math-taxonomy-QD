"""Exact, answer-independent models for the elementary-algebra audit.

Inputs contain mathematical expressions, hypotheses and candidate meanings, never
answer keys or precomputed truth values. Choice models evaluate every candidate.
Linear implications use Fourier--Motzkin elimination over rational numbers;
counterexample search is never used to prove a universal statement.
"""
import ast
from fractions import Fraction
from itertools import product
from math import isqrt
import re

from exact_polynomial import _add, _multiply, _parse, _source
from model_types import TextProof, select_unique


def number(expression):
    source = str(expression).replace('^', '**').replace('−', '-')
    if len(source) > 256: raise ValueError('oversized number expression')
    tree = ast.parse(source, mode='eval')
    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return Fraction(ast.get_source_segment(source, node))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            return visit(node.operand) * (-1 if isinstance(node.op, ast.USub) else 1)
        if isinstance(node, ast.BinOp):
            a, b = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Add): return a+b
            if isinstance(node.op, ast.Sub): return a-b
            if isinstance(node.op, ast.Mult): return a*b
            if isinstance(node.op, ast.Div): return a/b
            if isinstance(node.op, ast.Pow) and b.denominator == 1 and abs(b) <= 100:
                if a == b == 0: raise ValueError('zero to zero power')
                return a**int(b)
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and len(node.args) == 1 and not node.keywords):
            x = visit(node.args[0])
            if node.func.id == 'abs': return abs(x)
            if node.func.id == 'sqrt' and x >= 0:
                n, d = isqrt(x.numerator), isqrt(x.denominator)
                if n*n == x.numerator and d*d == x.denominator: return Fraction(n,d)
        raise ValueError('unsupported exact rational arithmetic')
    return visit(tree.body)


def compare(left, op, right):
    if op == '=': return left == right
    if op == '!=': return left != right
    if op == '<': return left < right
    if op == '<=': return left <= right
    if op == '>': return left > right
    if op == '>=': return left >= right
    raise ValueError('unknown comparison ' + op)


def numeric_relations(spec):
    def predicate(option):
        try:
            relations=option.get('relations',[option])
            valid = all(compare(number(r['left']),r['op'],number(r['right'])) for r in relations)
        except ZeroDivisionError:
            # An explicitly undefined arithmetic expression is not a true equality.
            if not option.get('allow_undefined'): raise
            valid = False
        return valid if spec.get('want', 'true') == 'true' else not valid
    return select_unique(spec['options'], predicate)


def scientific_notation(spec):
    target = number(spec['number'])
    def predicate(option):
        coefficient = number(option['coefficient'])
        exponent = option['exponent']
        if type(exponent) is not int: raise ValueError('integer exponent required')
        return (1 <= abs(coefficient) < 10 and
                coefficient * Fraction(10) ** exponent == target)
    return select_unique(spec['options'], predicate)


def polynomial_identity(spec):
    return select_unique(spec['options'], lambda o: _parse(o['left']) == _parse(o['right']))


def equation_operation(spec):
    left, right = map(_parse, _equation(spec['before']))
    target_left, target_right = map(_parse, _equation(spec['after']))
    def predicate(option):
        amount = number(option['amount']); constant = {(): amount}
        def transform(side):
            if option['operation'] == 'add': return _add(side, constant)
            if option['operation'] == 'subtract': return _add(side, constant, -1)
            if option['operation'] == 'multiply': return _multiply(side, constant)
            if option['operation'] == 'divide' and amount:
                return {m:c/amount for m,c in side.items()}
            raise ValueError('undefined equality operation')
        return transform(left) == target_left and transform(right) == target_right
    return select_unique(spec['options'], predicate)


def polynomial_implications(spec):
    def substitute_polynomial(terms, variable, replacement):
        result = {}
        for monomial, coefficient in terms.items():
            term = {(): coefficient}
            for name in monomial:
                term = _multiply(term, replacement if name == variable else {(name,): Fraction(1)})
            result = _add(result, term)
        return result
    def predicate(option):
        premises = [_difference(*_equation(e)) for e in option['premises']]
        conclusion = _difference(*_equation(option['conclusion']))
        reduced = conclusion
        for premise in premises:
            if premise and max(map(len,premise)) == 1:
                variable = sorted(m[0] for m in premise if m)[-1]
                a = premise[(variable,)]
                replacement = {m:-c/a for m,c in premise.items() if m != (variable,)}
                reduced = substitute_polynomial(reduced, variable, replacement)
        if not reduced: return True  # exact symbolic substitution proves the implication
        variables = sorted({v for p in premises+[conclusion] for m in p for v in m})
        if len(variables) > 5: raise ValueError('too many variables for counterexample search')
        for numbers in product((-1,0,1), repeat=len(variables)):
            values = dict(zip(variables,numbers))
            if all(_substitute(p,values)==0 for p in premises) and _substitute(conclusion,values)!=0:
                return False  # a concrete exact witness disproves, never proves, a universal claim
        raise ValueError('no symbolic proof or counterexample; requires independent review')
    return select_unique(spec['options'],predicate)


def like_terms(left, right):
    a, b = _parse(left), _parse(right)
    if len(a) != 1 or len(b) != 1:
        raise ValueError('like-term comparison needs nonzero single monomials')
    return set(a) == set(b)


def monomial_pairs(spec):
    if 'options' in spec:
        return select_unique(spec['options'], lambda o: like_terms(o['left'], o['right']))
    result = like_terms(spec['left'], spec['right'])
    return TextProof('是' if result else '不是', 'like_terms')


def _algebra_tree(text):
    # An algebraic expression is an expression, not an equation/inequality.
    source = _source(text.replace('π', 'p'))
    tree = ast.parse(source, mode='eval')
    allowed = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Name,
               ast.Load, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.UAdd, ast.USub)
    if any(not isinstance(n, allowed) for n in ast.walk(tree)):
        raise ValueError('not an algebraic-expression tree')
    return tree


def _equation(text):
    parts = text.split('=')
    if len(parts) != 2 or any(c in text for c in '<>!≤≥'):
        raise ValueError('one equality is required')
    _algebra_tree(parts[0]); _algebra_tree(parts[1])
    return parts


def expression_has_kind(text, kind):
    if kind == 'equation':
        if text.count('=')!=1 or any(c in text for c in '<>!≤≥'):return False
        parts = _equation(text)
        return any(re.search('[a-z]',p) for p in parts)
    if kind in ('linear1', 'linear2'):
        if text.count('=')!=1 or any(c in text for c in '<>!≤≥'):return False
        left,right=_equation(text)
        a,b=_definition_terms(left),_definition_terms(right)
        if a is None or b is None:return False
        terms=_add(a,b,-1)
        variables = {v for m in terms for v in m}
        return (len(variables) == int(kind[-1]) and
                max(map(len, terms), default=0) == 1)
    if any(c in text for c in '=<>!≤≥'):return False
    tree=_algebra_tree(text)
    if kind == 'algebraic': return True
    terms = _definition_terms(text)
    if terms is None:return False
    if kind == 'polynomial': return True
    if kind == 'monomial':
        variable_sum=any(isinstance(n,ast.BinOp) and isinstance(n.op,(ast.Add,ast.Sub))
                         and any(isinstance(c,ast.Name) for c in ast.walk(n))
                         for n in ast.walk(tree))
        return len(terms) <= 1 and not variable_sum
    raise ValueError('unsupported expression kind')


def _definition_terms(text):
    """Return None only for a proved variable-denominator/negative-power type.

    Parser/degree/coefficient limits remain errors (unknown), never false.
    This distinction is essential when a question asks which is NOT a polynomial.
    """
    source=_source(text)
    tree=ast.parse(source,mode='eval')
    for node in ast.walk(tree):
        if (isinstance(node,ast.BinOp) and isinstance(node.op,ast.Pow)
                and isinstance(node.right,ast.UnaryOp) and isinstance(node.right.op,ast.USub)
                and isinstance(node.right.operand,ast.Constant)
                and type(node.right.operand.value) is int and node.right.operand.value>0
                and any(isinstance(n,ast.Name) for n in ast.walk(node.left))):
            return None
    try:return _parse(text)
    except ValueError as error:
        if str(error)!='unsupported polynomial operation':raise
        for node in ast.walk(tree):
            if isinstance(node,ast.BinOp) and isinstance(node.op,ast.Div):
                denominator=_definition_terms(ast.get_source_segment(source,node.right))
                if denominator is None:return None
                if not denominator:raise ValueError('undefined zero denominator')
                if any(m for m in denominator):return None
        raise


def expression_kind(spec):
    if 'expressions' in spec:
        return sum(expression_has_kind(e, spec['target']) for e in spec['expressions'])
    want = spec.get('want', 'true') == 'true'
    return select_unique(spec['options'], lambda o: expression_has_kind(o['expression'], spec['target']) == want)


def equation_classification(spec):
    left, right = _equation(spec['equation'])
    terms = _difference(left, right)
    degree = max(map(len, terms), default=0)
    return TextProof({'answer': expression_has_kind(spec['equation'], spec['target']),
                      'degree': degree}, 'equation_classification')


def commutative_identity(spec):
    a, b = spec['operands']
    if not all(re.fullmatch('[a-z]', x) for x in (a,b)): raise ValueError('single-letter operands')
    operator = {'addition': '+', 'multiplication': '*'}[spec['operation']]
    left, right = a+operator+b, b+operator+a
    if _parse(left) != _parse(right): raise ValueError('failed commutative identity')
    return TextProof(left+'='+right, 'identity_equation')


def law_identification(spec):
    left, right = _equation(spec['equation'])
    def additive_terms(expression):
        def visit(node):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
                return visit(node.left)+visit(node.right)
            return [ast.dump(node, include_attributes=False)]
        return visit(ast.parse(_source(expression), mode='eval').body)
    l, r = additive_terms(left), additive_terms(right)
    if sorted(l) != sorted(r) or l == r:
        raise ValueError('not a nontrivial permutation of additive terms')
    return select_unique(spec['options'], lambda o: o['law'] == 'addition_commutativity')


def power_base(spec):
    source = _source(spec['expression'])
    node = ast.parse(source, mode='eval').body
    if not isinstance(node, ast.BinOp) or not isinstance(node.op, ast.Pow):
        raise ValueError('power expression required')
    base = number(ast.get_source_segment(source,node.left))
    return select_unique(spec['options'], lambda o: number(o['value']) == base)


def system_kind(spec):
    def predicate(option):
        equations = option['equations']
        variables = set()
        for equation in equations:
            if equation.count('=')!=1 or any(c in equation for c in '<>!≤≥'):return False
            left,right=_equation(equation)
            a,b=_definition_terms(left),_definition_terms(right)
            if a is None or b is None:return False
            terms=_add(a,b,-1)
            if max(map(len, terms), default=0) != 1: return False
            variables.update(v for m in terms for v in m)
        return len(variables) == spec['unknown_count'] and len(equations) == spec['equation_count']
    return select_unique(spec['options'], predicate)


def _difference(left, right):
    result = dict(_parse(left))
    for m, c in _parse(right).items(): result[m] = result.get(m, 0) - c
    return {m: c for m, c in result.items() if c}


def _substitute(terms, values):
    total = Fraction(0)
    for monomial, coefficient in terms.items():
        value = coefficient
        for name in monomial:
            if name not in values: raise ValueError('missing variable ' + name)
            value *= number(values[name])
        total += value
    return total


def _satisfies(equations, values):
    return all(_substitute(_difference(*_equation(e)), values) == 0 for e in equations)


def equation_solution(spec):
    if 'options' in spec:
        def predicate(option):
            values=option.get('values',spec.get('values'))
            if values is None: raise ValueError('variable assignment required')
            results=[_satisfies([e],values) for e in spec['equations']]
            claim=option.get('claim','solution')
            if claim=='solution':return all(results)
            if claim=='not_solution':return not all(results)
            if claim=='first_only':return results[0] and not any(results[1:])
            if claim=='undetermined':return False # all expressions were evaluated exactly
            raise ValueError('unknown equation-solution claim')
        return select_unique(spec['options'], predicate)
    return TextProof('是' if _satisfies(spec['equations'], spec['values']) else '不是', 'equation_solution')


def _affine(expression):
    terms = _parse(expression)
    if any(len(m) > 1 for m in terms): raise ValueError('linear expression required')
    return {m[0]: c for m, c in terms.items() if m}, terms.get((), Fraction(0))


def _constraints(relation):
    # Each row means dot(coefficients, variables) <= bound, with optional strict <.
    terms = _difference(relation['left'], relation['right'])
    if any(len(m) > 1 for m in terms): raise ValueError('linear relation required')
    coeff = {m[0]: c for m, c in terms.items() if m}
    bound = -terms.get((), Fraction(0))
    op = relation['op']
    if op in ('>', '>='):
        coeff = {v: -c for v, c in coeff.items()}; bound = -bound
    if op == '=':
        return [(coeff, bound, False), ({v: -c for v, c in coeff.items()}, -bound, False)]
    if op not in ('<', '<=', '>', '>='): raise ValueError('unsupported linear relation')
    return [(coeff, bound, op in ('<', '>'))]


def feasible(relations):
    """Exact feasibility of real affine equalities/inequalities (strict included)."""
    rows = [row for relation in relations for row in _constraints(relation)]
    variables = sorted({v for coeff, _, _ in rows for v in coeff})
    for variable in variables:
        positive, negative, keep = [], [], []
        for coeff, bound, strict in rows:
            c = coeff.get(variable, 0)
            remaining = {v: a for v, a in coeff.items() if v != variable}
            if c > 0: positive.append((remaining, bound, strict, c))
            elif c < 0: negative.append((remaining, bound, strict, c))
            else: keep.append((remaining, bound, strict))
        for p, pb, ps, pc in positive:
            for n, nb, ns, nc in negative:
                coeff = {v: p.get(v, 0)/pc - n.get(v, 0)/nc for v in set(p) | set(n)}
                keep.append(({v: c for v, c in coeff.items() if c}, pb/pc - nb/nc, ps or ns))
        rows = keep
        if len(rows) > 4096: raise ValueError('linear proof exceeds elimination bound')
    return all(bound > 0 if strict else bound >= 0 for _, bound, strict in rows)


def implies(premises, conclusion):
    if not feasible(premises): raise ValueError('inconsistent hypotheses')
    opposite = {'<': '>=', '<=': '>', '>': '<=', '>=': '<'}
    if conclusion['op'] == '=':
        return all(not feasible(premises + [{**conclusion, 'op': op}]) for op in ('<', '>'))
    if conclusion['op'] == '!=':
        return not feasible(premises + [{**conclusion, 'op': '='}])
    return not feasible(premises + [{**conclusion, 'op': opposite[conclusion['op']]}])


def linear_implications(spec):
    def predicate(option):
        premises = spec.get('premises', []) + option.get('premises', [])
        conclusions = option.get('conclusions', [option.get('conclusion')])
        valid = all(implies(premises, c) for c in conclusions)
        return valid if spec.get('want', 'true') == 'true' else not valid
    return select_unique(spec['options'], predicate)


def _expand_absolute(expression, signs):
    def replace(match):
        operand = match[1]
        if operand.lstrip('-') in signs:
            variable = operand.lstrip('-')
            return '('+str(signs[variable])+'*'+variable+')'
        return '('+str(abs(number(operand)))+')'
    # abs(-x) and abs(x) are identical on a sign partition of x.
    expanded = re.sub(r'abs\((-?[a-z]|-?\d+(?:/\d+)?)\)', replace, expression)
    if 'abs' in expanded: raise ValueError('only single-variable/constant absolute values supported')
    return expanded


def absolute_implications(spec):
    variables = spec['variables']
    if len(variables) > 4: raise ValueError('too many absolute-value variables')
    def predicate(option):
        for values in product((-1,1), repeat=len(variables)):
            signs = dict(zip(variables, values))
            domain = [{'left': v, 'op': '>=' if s > 0 else '<=', 'right': '0'} for v,s in signs.items()]
            def expand(r):
                return {**r,'left':_expand_absolute(r['left'],signs),
                        'right':_expand_absolute(r['right'],signs)}
            premises = domain + [expand(r) for r in spec.get('premises',[]) + option.get('premises',[])]
            if not feasible(premises): continue
            conclusions=option.get('conclusions',[option.get('conclusion')])
            if not all(implies(premises,expand(c)) for c in conclusions): return False
        return True
    return select_unique(spec['options'], predicate)


def absolute_domain(spec):
    variable = spec['variable']
    def predicate(option):
        for sign in (-1,1):
            domain=[{'left':variable,'op':'>=' if sign>0 else '<=','right':'0'}]
            target=domain+[{'left':str(sign)+'*'+variable,'op':'=','right':spec['right']}]
            candidate=domain+option['constraints']
            if feasible(target) != feasible(candidate): return False
            if feasible(target) and not (all(implies(target,c) for c in candidate)
                                         and all(implies(candidate,c) for c in target)): return False
        return True
    return select_unique(spec['options'],predicate)


def positive_polynomial_sign(spec):
    """Complete for affine expressions and nonzero monomials on v>0."""
    variable = spec['variable']
    def predicate(option):
        p = _parse(option['expression'])
        if any(set(m) - {variable} for m in p): raise ValueError('one variable required')
        if not p: possible = {0}
        elif len(p) == 1:
            c = next(iter(p.values())); possible = {1 if c > 0 else -1}
        elif max(map(len, p)) <= 1:
            a, b = p.get((variable,), 0), p.get((), 0)
            possible = {1 if a > 0 else -1}
            if a*b < 0: possible = {-1, 0, 1}
        else: raise ValueError('unsupported positive-domain polynomial; do not infer false')
        return possible == {spec['sign']}
    return select_unique(spec['options'], predicate)


def linear_interval(spec):
    if 'options' in spec:
        target = spec['constraints']
        if not feasible(target): raise ValueError('empty target requires explicit empty-set support')
        def predicate(option):
            if option.get('empty'): return False
            candidate = option['constraints']
            return (feasible(candidate) and all(implies(target, c) for c in candidate) and
                    all(implies(candidate, c) for c in target))
        return select_unique(spec['options'], predicate)
    constraints = spec['constraints']
    if len(constraints) != 1: raise ValueError('short normalization currently needs one relation')
    r = constraints[0]
    coeff, constant = _affine('(' + r['left'] + ')-(' + r['right'] + ')')
    if set(coeff) != {spec.get('variable', 'x')}: raise ValueError('one nonzero unknown required')
    variable, a = next(iter(coeff.items()))
    op = r['op']
    if a < 0: op = {'<': '>', '<=': '>=', '>': '<', '>=': '<='}[op]
    endpoint = -constant/a
    symbol = {'<=': '≤', '>=': '≥'}.get(op, op)
    return TextProof(variable + symbol + str(endpoint), 'relation')


def coordinate_choices(spec):
    target = [number(x) for x in spec['point']]
    return select_unique(spec['options'], lambda o: [number(x) for x in o['point']] == target)


def coordinate_value(spec):
    return tuple(number(x) for x in spec['point'])


def quadrant(spec):
    def predicate(option):
        x, y = map(number, option['point'])
        signs = (1 if x > 0 else -1 if x < 0 else 0, 1 if y > 0 else -1 if y < 0 else 0)
        return signs == tuple(spec['signs'])
    return select_unique(spec['options'], predicate)


def two_focus_minimum(spec):
    # Triangle inequality is global in R^n; the segment joining the foci attains it.
    a, b = spec['a'], spec['b']
    if len(a) != len(b): raise ValueError('equal coordinate dimension required')
    d2 = sum((number(x)-number(y))**2 for x, y in zip(a, b))
    n, d = isqrt(d2.numerator), isqrt(d2.denominator)
    if n*n != d2.numerator or d*d != d2.denominator: raise ValueError('nonrational minimum')
    return Fraction(n, d)


def angle_vertex(spec):
    labels = spec['angle'].replace('∠', '')
    if not re.fullmatch('[A-Z]{3}', labels): raise ValueError('three-point angle required')
    return select_unique(spec['options'], lambda o: o['point'] == labels[1])


def vertical_angle_pairs(spec):
    opposite = {}
    for a, b in spec['opposite_rays']:
        if a in opposite or b in opposite or a == b: raise ValueError('inconsistent opposite rays')
        opposite[a] = b; opposite[b] = a
    def predicate(option):
        first, second = option['angles']
        return {opposite[a] for a in first} == set(second)
    return select_unique(spec['options'], predicate)


def numeric_property(spec):
    """Finite numeric domain tests such as integral admissibility; no rounding."""
    value = number(spec['value'])
    property_name = spec['property']
    if property_name == 'nonnegative_integer': result = value >= 0 and value.denominator == 1
    else: raise ValueError('unknown numeric property')
    def predicate(option):
        if option['claim']=='admissible':return result
        if option['claim']=='inadmissible':return not result
        if option['claim']=='value':return result and value==number(option['value'])
        raise ValueError('unknown admissibility claim')
    return select_unique(spec['options'],predicate)


def real_root_sets(spec):
    def roots(radicand, degree, principal):
        n=number(radicand)
        if degree!=2:raise ValueError('only exact square-root sets supported')
        if n<0:return set()
        root=number('sqrt('+str(n)+')')
        return {root} if principal else {root,-root}
    def predicate(option):
        actual=roots(option['radicand'],option.get('degree',2),option.get('principal',False))
        actual={x*number(option.get('multiplier','1')) for x in actual}
        return actual=={number(x) for x in option['claimed_roots']}
    return select_unique(spec['options'],predicate)


def positive_sqrt_compare(spec):
    n,q=number(spec['radicand']),number(spec['other'])
    if n<0:raise ValueError('real square root required')
    def predicate(option):
        if q<0:
            # A nonnegative principal root is strictly greater than a negative number.
            return compare(Fraction(1),option['op'],Fraction(0))
        return compare(n,option['op'],q*q)
    return select_unique(spec['options'],predicate)


def point_location(spec):
    x,y=map(number,spec['point'])
    if x==y==0:location='origin'
    elif x==0:location='y_positive' if y>0 else 'y_negative'
    elif y==0:location='x_positive' if x>0 else 'x_negative'
    else:location={(1,1):'Q1',(-1,1):'Q2',(-1,-1):'Q3',(1,-1):'Q4'}[(1 if x>0 else -1,1 if y>0 else -1)]
    return select_unique(spec['options'],lambda o:o['location']==location)


def coordinate_equality(spec):
    equal=tuple(map(number,spec['first']))==tuple(map(number,spec['second']))
    return select_unique(spec['options'],lambda o:(o['claim']=='equal' and equal) or
                         (o['claim']=='different' and not equal))


def linear_elimination(spec):
    equations=[_difference(*_equation(e)) for e in spec['equations']]
    if any(len(m)>1 for p in equations for m in p):raise ValueError('elimination requires affine source equations')
    def predicate(option):
        if len(option['weights'])!=len(equations):raise ValueError('one weight per equation')
        combined={}
        for p,w in zip(equations,option['weights']):combined=_add(combined,_multiply(p,{():number(w)}))
        return (not any(spec['eliminate'] in m for m in combined) and
                any(m for m in combined))
    return select_unique(spec['options'],predicate)


def system_from_heads_legs(spec):
    x,y=spec['variables'];a,b=map(number,spec['legs_per_animal'])
    target=[{'left':x+'+'+y,'op':'=','right':str(spec['heads'])},
            {'left':str(a)+'*'+x+'+'+str(b)+'*'+y,'op':'=','right':str(spec['legs'])}]
    options=[]
    for option in spec['options']:
        equations=[{'left':p[0],'op':'=','right':p[1]} for p in map(_equation,option['equations'])]
        options.append({**option,'constraints':equations})
    return linear_interval({'constraints':target,'options':options})


def window_empty_parameter(spec):
    # An interval (a,b), [a,b), or (a,b] is empty at a=b; [a,b] is not.
    op='>=' if spec.get('left_open',True) or spec.get('right_open',True) else '>'
    return linear_interval({**spec,'constraints':[{'left':spec['lower_variable'],'op':op,
                                                 'right':str(spec['upper'])}]})


def positive_factor_inequality(spec):
    sign=spec['other_factor_sign']
    if sign not in (-1,1):raise ValueError('strictly signed factor required')
    op=spec['op']
    if sign<0:op={'<':'>','<=':'>=','>':'<','>=':'<='}[op]
    return linear_interval({**spec,'constraints':[{'left':spec['factor'],'op':op,'right':'0'}]})


def point_line_distance(spec):
    d=number(spec['perpendicular_distance']); length=number(spec['candidate_length'])
    if d<0 or length<0:raise ValueError('nonnegative lengths required')
    possible=length>=d and (spec.get('foot_allowed',True) or length!=d)
    def predicate(option):
        if option['claim'] not in ('possible','impossible'):raise ValueError('unknown possibility claim')
        return (option['claim']=='possible')==possible
    return select_unique(spec['options'],predicate)


def distance_bound(spec):
    distances=list(map(number,spec['distances']))
    if not distances or min(distances)<=0:raise ValueError('positive observed distances required')
    premises=[{'left':'d','op':'>','right':'0'},
              {'left':'d','op':'<=','right':str(min(distances))}]
    return linear_implications({**spec,'premises':premises})


def translation_equal_length(spec):
    # Prove symbolically for arbitrary points and arbitrary translation vector.
    for coordinate,offset in [('x','u'),('y','v')]:
        if _difference('('+coordinate+'+'+offset+')-'+coordinate,offset):
            raise ValueError('translation displacement identity failed')
    length=number(spec['displacement_length'])
    if length<0:raise ValueError('a length cannot be negative')
    return length


def signed_quantity(spec):
    sign = {'increase':1,'decrease':-1}[spec['change']]
    value = sign*number(spec['magnitude'])*number(spec.get('positive_unit','1'))
    return select_unique(spec['options'],lambda o:number(o['value'])==value)


def number_axis(spec):
    def predicate(option):
        if option.get('origin') is None or option.get('direction') not in (-1,1): return False
        points=option.get('labels',[])
        if not points: return False
        scales=[]
        for label,position in points:
            label,position=number(label),number(position)
            if not label:
                if position!=number(option['origin']):return False
            else:scales.append((position-number(option['origin']))/(label*option['direction']))
        return bool(scales) and all(s>0 and s==scales[0] for s in scales)
    return select_unique(spec['options'],predicate)


HANDLERS = {
    'numeric_relations': numeric_relations, 'scientific_notation': scientific_notation,
    'polynomial_identity': polynomial_identity, 'monomial_pairs': monomial_pairs,
    'expression_kind': expression_kind, 'system_kind': system_kind,
    'equation_solution': equation_solution, 'linear_implications': linear_implications,
    'positive_polynomial_sign': positive_polynomial_sign, 'linear_interval': linear_interval,
    'coordinate_choices': coordinate_choices, 'coordinate_value': coordinate_value,
    'quadrant': quadrant, 'two_focus_minimum': two_focus_minimum,
    'angle_vertex': angle_vertex, 'vertical_angle_pairs': vertical_angle_pairs,
    'numeric_property': numeric_property,
    'absolute_implications': absolute_implications, 'absolute_domain': absolute_domain,
    'power_base': power_base, 'law_identification': law_identification,
    'commutative_identity': commutative_identity, 'equation_classification': equation_classification,
    'equation_operation': equation_operation, 'polynomial_implications': polynomial_implications,
    'signed_quantity': signed_quantity, 'number_axis': number_axis,
    'real_root_sets':real_root_sets,'positive_sqrt_compare':positive_sqrt_compare,
    'point_location':point_location,'coordinate_equality':coordinate_equality,
    'linear_elimination':linear_elimination,'system_from_heads_legs':system_from_heads_legs,
    'window_empty_parameter':window_empty_parameter,'positive_factor_inequality':positive_factor_inequality,
    'point_line_distance':point_line_distance,'distance_bound':distance_bound,
    'translation_equal_length':translation_equal_length,
}
