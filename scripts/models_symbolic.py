"""Bounded symbolic models for reviewed school algebra, using exact SymPy.

Only our AST converter constructs expressions; neither eval, sympify nor
parse_expr executes input strings. Original denominator/radical constraints
are retained separately from cancellation. Choice candidates are all checked.
"""
import ast
from fractions import Fraction
from itertools import product
import re
import sympy as S
from model_types import TextProof, select_unique


def _assumptions(name, assumptions):
    kind = (assumptions or {}).get(name, 'real')
    if kind not in ('real', 'positive', 'negative', 'nonnegative', 'nonpositive', 'nonzero'):
        raise ValueError('unsupported symbol assumption')
    return {'real': True, **({kind: True} if kind != 'real' else {})}


def parse_math(source, assumptions=None):
    if not isinstance(source, str) or len(source) > 500:
        raise ValueError('invalid symbolic expression')
    tree = ast.parse(source.strip(), mode='eval')
    if sum(1 for _ in ast.walk(tree)) > 160:
        raise ValueError('symbolic expression too large')
    constraints = []

    def convert(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            value = S.Rational(ast.get_source_segment(source.strip(), node))
            if abs(value.p) > 10**15 or value.q > 10**15:
                raise ValueError('numeric literal too large')
            return value
        if isinstance(node, ast.Name):
            if node.id == 'pi':
                return S.pi
            if re.fullmatch('[a-z]', node.id):
                return S.Symbol(node.id, **_assumptions(node.id, assumptions))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = convert(node.operand)
            return value if isinstance(node.op, ast.UAdd) else S.Mul(-1, value, evaluate=False)
        if isinstance(node, ast.BinOp):
            left, right = convert(node.left), convert(node.right)
            if isinstance(node.op, ast.Add):
                return S.Add(left, right, evaluate=False)
            if isinstance(node.op, ast.Sub):
                return S.Add(left, S.Mul(-1, right, evaluate=False), evaluate=False)
            if isinstance(node.op, ast.Mult):
                return S.Mul(left, right, evaluate=False)
            if isinstance(node.op, ast.Div):
                if S.simplify(right) == 0:
                    raise ValueError('zero denominator')
                constraints.append(S.Ne(right, 0))
                return S.Mul(left, S.Pow(right, -1, evaluate=False), evaluate=False)
            if isinstance(node.op, ast.Pow):
                exponent = S.simplify(right)
                if exponent.is_Integer is not True or abs(exponent) > 12:
                    raise ValueError('exponent must be a small integer')
                if exponent <= 0:
                    constraints.append(S.Ne(left, 0))
                if left == 0 and exponent == 0:
                    raise ValueError('undefined zero power')
                return S.Pow(left, exponent, evaluate=False)
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and len(node.args) == 1 and not node.keywords):
            argument = convert(node.args[0])
            if node.func.id == 'sqrt':
                constraints.append(S.Ge(argument, 0))
                return S.Pow(argument, S.Rational(1, 2), evaluate=False)
            if node.func.id == 'Abs':
                return S.Abs(argument)
            if node.func.id == 'cbrt':
                return S.real_root(S.simplify(argument), 3)
        raise ValueError('unsupported symbolic syntax')

    expression = convert(tree.body)
    if len(expression.free_symbols) > 4:
        raise ValueError('too many symbolic variables')
    return expression, constraints


def _equal(left, right):
    difference = S.simplify(left - right)
    if difference == 0:
        return True
    if difference.is_zero is False:
        return False
    # Polynomial/rational nonzero normal forms prove non-identity even when
    # they have zeros at particular points. No numerical probing is used.
    if difference.is_rational_function():
        return S.cancel(difference) == 0
    raise ValueError('symbolic equality is unresolved')


def _has_domain(conditions, variables):
    conditions = [S.simplify(c) for c in conditions]
    if any(c is S.false for c in conditions):
        return False
    conditions = [c for c in conditions if c is not S.true]
    if not conditions:
        return True
    variables = variables | set().union(*(c.free_symbols for c in conditions))
    if len(variables) == 1:
        domain_set = _constraint_set(conditions, next(iter(variables)))
        if domain_set.is_empty is not None:
            return not domain_set.is_empty
    if len(variables) <= 4:
        names = sorted(variables, key=str)
        for values in product((0, 1, -1, 2, -2), repeat=len(names)):
            assignment = dict(zip(names, values))
            if any((v.is_positive is True and n <= 0) or (v.is_negative is True and n >= 0)
                   or (v.is_nonnegative is True and n < 0) or (v.is_nonpositive is True and n > 0)
                   or (v.is_zero is False and n == 0) for v, n in assignment.items()):
                continue
            if all(S.simplify(c.subs(assignment)) is S.true for c in conditions):
                return True  # one exact witness proves existence, never a universal identity
    raise ValueError('could not prove a nonempty original/common domain')


def _domain_compatible(source_constraints, candidate_constraints, variables, common=False):
    if any(S.simplify(c) is S.false for c in source_constraints + candidate_constraints):
        return False
    if not _has_domain(source_constraints + (candidate_constraints if common else []), variables):
        return False
    additional = [S.simplify(c) for c in candidate_constraints if S.simplify(c) is not S.true]
    if not additional or common:
        return True
    if len(variables) == 1:
        variable = next(iter(variables))
        missing = S.Complement(_constraint_set(source_constraints, variable),
                               _constraint_set(candidate_constraints, variable))
        if missing.is_empty is not None:
            return bool(missing.is_empty)
    if all(any(c == S.simplify(known) for known in source_constraints) for c in additional):
        return True
    # A product is nonzero iff every irreducible factor is nonzero. This
    # proves rational-domain inclusion with several variables without probes.
    source_factors = []
    for condition in source_constraints:
        condition = S.simplify(condition)
        if condition is S.true:
            continue
        if not isinstance(condition, S.Unequality):
            raise ValueError('multivariable domain is unresolved')
        numerator, denominator = S.cancel(condition.lhs-condition.rhs).as_numer_denom()
        for part in (numerator, denominator):
            if part.free_symbols:
                source_factors.extend(factor for factor, _ in S.factor_list(part)[1])
    for condition in additional:
        if not isinstance(condition, S.Unequality):
            raise ValueError('multivariable candidate domain is unresolved')
        numerator, denominator = S.cancel(condition.lhs-condition.rhs).as_numer_denom()
        for part in (numerator, denominator):
            if not part.free_symbols:
                continue
            for factor, _ in S.factor_list(part)[1]:
                if not any(_equal(factor, known) or _equal(factor, -known) for known in source_factors):
                    return False
    return True


def identity(spec):
    sources = spec['source'] if isinstance(spec['source'], list) else [spec['source']]
    parsed = [parse_math(source, spec.get('assumptions')) for source in sources]
    source_constraints = sum((constraints for _, constraints in parsed), [])
    source_variables = set().union(*(source.free_symbols for source, _ in parsed))

    def check(option):
        candidates = option['expression'] if isinstance(option['expression'], list) else [option['expression']]
        if len(candidates) != len(parsed):
            return False
        for (source, _), candidate_text in zip(parsed, candidates):
            candidate, candidate_constraints = parse_math(candidate_text, spec.get('assumptions'))
            if not _equal(source, candidate):
                return False
            if not _domain_compatible(source_constraints, candidate_constraints,
                                      source_variables | candidate.free_symbols,
                                      spec.get('domain_policy') == 'common_defined'):
                return False
        return True

    return select_unique(spec['options'], check)


def _irreducible(expression):
    expression = S.expand(expression)
    symbols = sorted(expression.free_symbols, key=str)
    if not symbols:
        return True
    polynomial = S.Poly(expression, *symbols, domain=S.QQ)
    if polynomial.total_degree() > 6:
        raise ValueError('factorization degree outside reviewed bounds')
    # Primitive polynomial factors must also have their rational content
    # extracted (x*(2x+2) is incomplete next to 2x*(x+1)).
    content, primitive = polynomial.primitive()
    return abs(content.p) == 1 and bool(primitive.is_irreducible)


def _fully_factored(expression):
    if isinstance(expression, S.Mul):
        return all(_fully_factored(part) for part in expression.args)
    if isinstance(expression, S.Pow) and expression.exp.is_Integer and expression.exp > 0:
        return _fully_factored(expression.base)
    return _irreducible(expression)


def factorization(spec):
    source, constraints = parse_math(spec['source'])
    if any(S.simplify(c) is not S.true for c in constraints) or not source.is_polynomial():
        raise ValueError('factorization model requires a polynomial over Q')

    def check(option):
        candidate, conditions = parse_math(option['expression'])
        if any(S.simplify(c) is not S.true for c in conditions):
            raise ValueError('factorization candidate has a denominator/domain restriction')
        if not _equal(source, candidate):
            return False
        return _fully_factored(candidate) if spec.get('complete', True) else True

    return select_unique(spec['options'], check)


def _constraint_set(constraints, variable):
    result = S.S.Reals
    for condition in constraints:
        condition = S.simplify(condition)
        if condition is S.true:
            continue
        if condition is S.false:
            return S.S.EmptySet
        if condition.free_symbols - {variable}:
            raise ValueError('domain contains an unquantified parameter')
        if isinstance(condition, S.Unequality):
            allowed = S.Complement(S.S.Reals, S.solveset(condition.lhs-condition.rhs, variable, domain=S.S.Reals))
        elif isinstance(condition, S.Equality):
            allowed = S.solveset(condition.lhs-condition.rhs, variable, domain=S.S.Reals)
        else:
            allowed = S.solve_univariate_inequality(condition, variable, relational=False)
        if allowed.has(S.ConditionSet):
            raise ValueError('domain solver is unresolved')
        result = S.Intersection(result, allowed)
    return result


def condition_set(source, variable):
    source = source.replace('≤', '<=').replace('≥', '>=').replace('≠', '!=')
    tree = ast.parse(source, mode='eval').body

    def convert(node):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in ('And', 'Or') and not node.keywords):
            sets = [convert(part) for part in node.args]
            return S.Intersection(*sets) if node.func.id == 'And' else S.Union(*sets)
        if isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.And, ast.Or)):
            sets = [convert(part) for part in node.values]
            return S.Intersection(*sets) if isinstance(node.op, ast.And) else S.Union(*sets)
        if isinstance(node, ast.Compare):
            left, conditions = parse_math(ast.get_source_segment(source, node.left))
            conditions = list(conditions)
            constructors = {ast.Eq: S.Eq, ast.NotEq: S.Ne, ast.Lt: S.Lt,
                            ast.LtE: S.Le, ast.Gt: S.Gt, ast.GtE: S.Ge}
            for operator, right_node in zip(node.ops, node.comparators):
                if type(operator) not in constructors:
                    raise ValueError('unsupported domain comparator')
                right, domain_constraints = parse_math(ast.get_source_segment(source, right_node))
                conditions.extend(domain_constraints)
                conditions.append(constructors[type(operator)](left, right))
                left = right
            return _constraint_set(conditions, variable)
        if isinstance(node, ast.Constant) and node.value is True:
            return S.S.Reals
        raise ValueError('unsupported domain condition')

    return convert(tree)


def domain(spec):
    variable = S.Symbol(spec.get('variable', 'x'), real=True)
    _, constraints = parse_math(spec['expression'])
    actual = _constraint_set(constraints, variable)
    if spec.get('query') == 'excluded_values':
        excluded = S.Complement(S.S.Reals, actual)
        if not isinstance(excluded, S.FiniteSet) or any(not n.is_Rational for n in excluded):
            raise ValueError('excluded values are not a finite rational list')
        values = [Fraction(int(n.p), int(n.q)) for n in sorted(excluded)]
        return values[0] if len(values) == 1 else values
    return select_unique(spec['options'], lambda option: actual == condition_set(option['condition'], variable))


def equation(spec):
    variable = S.Symbol(spec.get('variable', 'x'), real=True)
    left, lc = parse_math(spec['lhs'])
    right, rc = parse_math(spec.get('rhs', '0'))
    numerator = S.cancel(left-right).as_numer_denom()[0]
    polynomial = S.Poly(numerator, variable)
    if polynomial.degree() > 2:
        raise ValueError('equation degree outside reviewed bounds')
    domain_set = _constraint_set(lc+rc, variable)
    roots = S.Intersection(S.solveset(numerator, variable, domain=S.S.Reals), domain_set)
    if roots.is_FiniteSet is not True:
        raise ValueError('equation does not have a finite computed root set')
    if spec.get('query') == 'count':
        return len(roots)
    if spec.get('query') == 'roots':
        if any(not value.is_Rational for value in roots):
            raise ValueError('numeric roots must be rational')
        values = [Fraction(int(value.p), int(value.q)) for value in sorted(roots)]
        return values[0] if len(values) == 1 else values
    return select_unique(spec['options'], lambda option: roots == S.FiniteSet(
        *(parse_math(value)[0] for value in option.get('roots', option.get('expression', [])))))


def radical_domain(spec):
    def check(option):
        if option['degree'] != 2:
            return False
        expression, conditions = parse_math(option['expression'])
        if any(S.simplify(c) is S.false for c in conditions):
            return False
        variables = expression.free_symbols
        if not variables:
            return True
        if len(variables) != 1:
            raise ValueError('multivariable radical domain is unresolved')
        return _constraint_set(conditions, next(iter(variables))) == S.S.Reals
    return select_unique(spec['options'], check)


def radical_simplest(spec):
    def check(option):
        radicand, conditions = parse_math(option['radicand'])
        radicand = S.simplify(radicand)
        if conditions and any(c is S.false for c in conditions):
            return False
        if not radicand.is_Integer or radicand <= 0:
            return False
        return all(power == 1 for power in S.factorint(radicand).values())
    return select_unique(spec['options'], check)


def symbolic_statements(spec):
    def check(option):
        left, lc = parse_math(option['lhs'], spec.get('assumptions'))
        right, rc = parse_math(option['rhs'], spec.get('assumptions'))
        return _equal(left, right) and _domain_compatible(lc, rc, left.free_symbols | right.free_symbols)
    return select_unique(spec['options'], check)


def _product_form(expression):
    if isinstance(expression, S.Pow) and expression.exp.is_Integer and expression.exp >= 2:
        return bool(expression.base.free_symbols and expression.base.is_polynomial())
    if not isinstance(expression, S.Mul):
        return False
    factors = []
    def flatten(part):
        if isinstance(part, S.Mul):
            for factor in part.args:
                flatten(factor)
        else:
            factors.append(part)
    flatten(expression)
    nonconstant = [factor for factor in factors if factor.free_symbols]
    coefficient = S.simplify(S.Mul(*(factor for factor in factors if not factor.free_symbols)))
    count = len(nonconstant) + (coefficient not in (0, 1, -1))
    return count >= 2 and bool(nonconstant) and all(factor.is_polynomial() for factor in factors)


def factorization_form(spec):
    def check(option):
        left, lc = parse_math(option['lhs'])
        right, rc = parse_math(option['rhs'])
        return (not lc and not rc and isinstance(left, S.Add) and _product_form(right) and _equal(left, right))
    return select_unique(spec['options'], check)


def factorization_explanation(spec):
    left, lc = parse_math(spec['lhs'])
    right, rc = parse_math(spec['rhs'])
    if lc or rc or not left.is_polynomial() or not right.is_polynomial():
        raise ValueError('factorization explanation requires polynomials')
    if not _equal(left, right):
        category = 'unequal'
    elif isinstance(left, S.Add) and _product_form(right):
        category = 'product_of_polynomials'
    elif _product_form(left) and isinstance(right, S.Add):
        category = 'multiplication'
    else:
        raise ValueError('factorization direction is unresolved')
    return select_unique(spec['options'], lambda option: option['argument'] == category)


def rational_form(spec):
    def check(option):
        source = option['expression']
        parse_math(source)  # Reject an identically zero original denominator.
        tree = ast.parse(source, mode='eval').body
        if not isinstance(tree, ast.BinOp) or not isinstance(tree.op, ast.Div):
            return False
        numerator, nc = parse_math(ast.get_source_segment(source, tree.left))
        denominator, dc = parse_math(ast.get_source_segment(source, tree.right))
        if any(c.free_symbols for c in nc+dc):
            return False
        denominator = S.simplify(denominator)
        return bool(numerator.is_polynomial() and denominator.is_polynomial() and denominator.free_symbols)
    return select_unique(spec['options'], check)


def rational_reduced(spec):
    def check(option):
        numerator, denominator = S.fraction(parse_math(option['expression'])[0], exact=True)
        numerator, denominator = S.expand(S.simplify(numerator)), S.expand(S.simplify(denominator))
        symbols = sorted(numerator.free_symbols | denominator.free_symbols, key=str)
        if not symbols:
            raise ValueError('reduced-form model needs polynomial variables')
        pn, pd = S.Poly(numerator, *symbols, domain=S.ZZ), S.Poly(denominator, *symbols, domain=S.ZZ)
        return pn.gcd(pd).total_degree() == 0 and S.igcd(pn.content(), pd.content()) == 1
    return select_unique(spec['options'], check)


def difference_squares(spec):
    def check(option):
        expression, conditions = parse_math(option['expression'])
        if conditions or not expression.is_polynomial():
            return False
        polynomial = S.Poly(expression, *sorted(expression.free_symbols, key=str), domain=S.QQ)
        terms = polynomial.terms()
        if len(terms) != 2 or terms[0][1] * terms[1][1] >= 0:
            return False
        return all(all(power % 2 == 0 for power in powers) and S.sqrt(abs(coefficient)).is_Rational
                   for powers, coefficient in terms)
    return select_unique(spec['options'], check)


def product_conjugates(spec):
    def check(option):
        expression, _ = parse_math(option['expression'])
        if not isinstance(expression, S.Mul) or len(expression.args) != 2:
            return False
        left, right = (S.Add.make_args(S.expand(part)) for part in expression.args)
        if len(left) != 2 or len(right) != 2:
            return False
        return any(_equal(left[i], right[j]) and _equal(left[1-i], -right[1-j])
                   for i in (0, 1) for j in (0, 1))
    return select_unique(spec['options'], check)


def number_rationality(spec):
    """Use exact algebraic/theorem metadata, never finite decimal rounding.

    The recurring-gap certificate uses the theorem: an ultimately periodic,
    nonterminating base-10 expansion has bounded zero runs if a nonzero digit
    occurs infinitely often. A strictly growing arithmetic gap contradicts it.
    """
    def classify(value):
        if isinstance(value, dict):
            if value.get('kind') != 'growing_decimal_gaps':
                raise ValueError('unknown decimal certificate')
            start, step, digit = value['start'], value['step'], value['digit']
            if any(type(v) is not int for v in (start, step, digit)) or start < 0 or step <= 0 or not 1 <= digit <= 9:
                raise ValueError('zero gaps must grow unboundedly between infinitely many nonzero digits')
            n = S.Symbol('n', integer=True, positive=True)
            if S.limit(start + step*n, n, S.oo) != S.oo:
                raise ValueError('unbounded gaps not proved')
            return False
        else:
            expression, constraints = parse_math(value)
            if expression.free_symbols or not _has_domain(constraints, set()):
                raise ValueError('classification needs a defined real constant')
            result = S.simplify(expression).is_rational
            if result is None:
                raise ValueError('rationality is unresolved')
            return bool(result)
    if spec.get('query') == 'classification':
        category = 'rational' if classify(spec['source']) else 'irrational'
        return select_unique(spec['options'], lambda option: option['number_class'] == category)
    target = spec['target']
    if target not in ('rational', 'irrational'):
        raise ValueError('unsupported number class')
    if 'options' in spec:
        return select_unique(spec['options'], lambda option: classify(option['expression']) == (target == 'rational'))
    classifications = [classify(value) for value in spec['values']]
    return sum(result == (target == 'rational') for result in classifications)


def affine_incidence(spec):
    """Universal planar coordinate proofs after a stated invertible frame change.

    A nonzero row in R^2 has rank one, hence its homogeneous kernel has
    dimension one; all nonzero kernel vectors name the same line through P.
    Two distinct parallels can be normalized to y=0,y=h (h!=0); a transversal
    has nonzero x coefficient. All calculations below retain these parameters.
    """
    query = spec['query']
    if query in ('perpendicular_through_point', 'parallel_through_point'):
        u, v, x, y = S.symbols('u v x y', real=True)
        if spec.get('plane_dimension') != 2 or spec.get('given_direction_nonzero') is not True:
            raise ValueError('the planar/nonzero direction hypotheses are required')
        if query == 'parallel_through_point' and spec.get('point_off_line') is not True:
            raise ValueError('a distinct parallel requires the point to be off the given line')
        if query == 'perpendicular_through_point':
            row, vector = S.Matrix([[u, v]]), S.Matrix([-v, u])
        else:
            row, vector = S.Matrix([[v, -u]]), S.Matrix([u, v])
        if S.simplify((row*vector)[0]) != 0 or S.expand(vector.dot(vector)) != u*u+v*v:
            raise ValueError('direction-space identity failed')
        # The row is nonzero by the given hypothesis, so rank=1 for every
        # admitted u,v, including u=0 or v=0. Rank-nullity gives one span.
        nullity = row.cols - 1
        if nullity != 1:
            raise ValueError('direction span is not unique')
        return nullity
    if query == 'two_parallels_and_transversal':
        if spec.get('parallel_lines_distinct') is not True or spec.get('transversal_meets_first') is not True:
            raise ValueError('distinct parallels and a genuine transversal are required')
        h, p = S.symbols('h p', real=True, nonzero=True)
        q, r, x, y = S.symbols('q r x y', real=True)
        lines = [y, y-h, p*x+q*y-r]
        points = []
        for i in range(len(lines)):
            for j in range(i+1, len(lines)):
                solutions = S.solve([lines[i], lines[j]], [x, y], dict=True)
                for solution in solutions:
                    if set(solution) != {x,y} or any(S.simplify(eq.subs(solution)) != 0 for eq in (lines[i],lines[j])):
                        raise ValueError('intersection proof unresolved')
                    points.append((S.simplify(solution[x]), S.simplify(solution[y])))
        if len(points) != 2 or S.simplify(points[0][1]-points[1][1]).is_zero is not False:
            raise ValueError('distinct intersections not proved')
        return len(set(points))
    raise ValueError('unsupported affine-incidence question')


HANDLERS = {'symbolic_identity': identity, 'symbolic_simplify': identity,
            'symbolic_factorization': factorization, 'symbolic_domain': domain,
            'symbolic_equation': equation, 'symbolic_radical_domain': radical_domain,
            'symbolic_radical_simplest': radical_simplest,
            'symbolic_statements': symbolic_statements, 'symbolic_factorization_form': factorization_form,
            'symbolic_factorization_explanation': factorization_explanation,
            'symbolic_rational_form': rational_form, 'symbolic_rational_reduced': rational_reduced,
            'symbolic_difference_squares': difference_squares, 'symbolic_product_conjugates': product_conjugates}
HANDLERS.update({'symbolic_number_rationality': number_rationality, 'symbolic_affine_incidence': affine_incidence})
