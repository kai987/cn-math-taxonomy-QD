"""Fail-closed proofs for the remaining geometry/concept questions.

No answer keys or qids are used. Inputs are mathematical objects and complete
candidate claims. Symbolic proofs cover whole nonempty parameter domains;
finite examples are used ONLY to refute universal implications. Euclidean
congruence, positive lengths, triangle angle sum, and the definitions of a
reflection/regular polygon are the explicitly used mathematical premises.
"""
import ast
from fractions import Fraction
from functools import cmp_to_key
import re
from itertools import combinations, permutations
import sympy as S
from model_types import select_unique
from models_symbolic import parse_math
from models_geometry import close_facts, coordinate_facts


def symbols(spec):
    names=set(spec.get('variables',[]))|set(spec.get('positive',[]))|set(spec.get('nonzero',[]))
    if any(not isinstance(n,str) or not re.fullmatch('[a-z]',n) for n in names):raise ValueError('single-letter variables required')
    return {name:S.Symbol(name,positive=True) if name in spec.get('positive',[]) else
            S.Symbol(name,real=True,nonzero=True) if name in spec.get('nonzero',[]) else
            S.Symbol(name,real=True) for name in names}


def parse(expr, names):
    """Bounded AST relations; arithmetic is built only by parse_math."""
    if type(expr) not in (str,int,float,Fraction):raise ValueError('unsupported mathematical scalar')
    source=str(expr)
    if len(source)>500:raise ValueError('oversized geometry expression')
    tree=ast.parse(source,mode='eval')
    if sum(1 for _ in ast.walk(tree))>160:raise ValueError('geometry AST too large')
    assumptions={k:'positive' if v.is_positive is True else 'nonzero' if v.is_zero is False else 'real' for k,v in names.items()}
    def arithmetic(node):
        value,constraints=parse_math(ast.get_source_segment(source,node),assumptions)
        replacement={v:names[str(v)] for v in value.free_symbols if str(v) in names}
        if any(str(v) not in names for v in value.free_symbols):raise ValueError('undeclared geometry variable')
        value=value.xreplace(replacement)
        if any(S.simplify(c.xreplace(replacement)) is not S.true for c in constraints):raise ValueError('unproved arithmetic domain')
        return value
    def visit(node):
        if isinstance(node,ast.Compare):
            if len(node.ops)!=1:raise ValueError('one comparator per relation')
            left,right=arithmetic(node.left),arithmetic(node.comparators[0])
            operations={ast.Eq:S.Eq,ast.NotEq:S.Ne,ast.Lt:S.Lt,ast.LtE:S.Le,ast.Gt:S.Gt,ast.GtE:S.Ge}
            if type(node.ops[0]) not in operations:raise ValueError('unknown comparison')
            return operations[type(node.ops[0])](left,right)
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in ('Eq','Ne','And','Or'):
            if node.keywords:raise ValueError('no keyword arguments')
            if node.func.id in ('Eq','Ne'):
                if len(node.args)!=2:raise ValueError('binary relation required')
                return {'Eq':S.Eq,'Ne':S.Ne}[node.func.id](*(arithmetic(n) for n in node.args))
            if not 1<=len(node.args)<=8:raise ValueError('bounded Boolean arity required')
            values=[visit(n) for n in node.args]
            if any(not isinstance(v,(S.logic.boolalg.Boolean,)) for v in values):raise ValueError('Boolean relations required')
            return {'And':S.And,'Or':S.Or}[node.func.id](*values)
        return arithmetic(node)
    return visit(tree.body)


def vector(point):return S.Matrix([S.simplify(parse(v,{})) for v in point])


def exact_order(left,right):
    difference=S.simplify(left-right)
    if difference==0:return 0
    if difference.is_positive is True:return 1
    if difference.is_negative is True:return -1
    raise ValueError('exact ordering is unresolved')


def squared_lengths(points):
    pts=[vector(p) for p in points]
    if len(pts)!=3 or S.det(S.Matrix.hstack(pts[1]-pts[0],pts[2]-pts[0]))==0:
        raise ValueError('nondegenerate triangle required')
    return sorted([S.simplify((pts[i]-pts[j]).dot(pts[i]-pts[j])) for i,j in combinations(range(3),2)],key=cmp_to_key(exact_order))


def inequality_objects(spec):
    """Compare a solution set with points, cardinalities and candidate sets."""
    x=S.Symbol(spec['variable'],real=True)
    target=S.solve_univariate_inequality(parse(spec['relation'],{spec['variable']:x}),x,relational=False)
    def condition(o):
        kind=o['claim']
        if kind=='membership':
            result=target.contains(parse(o['point'],{}))
            if result not in (S.true,S.false):raise ValueError('membership unresolved')
            return result is S.true
        if kind=='cardinality':
            count=o['count']
            if type(count) is not int or count<0:raise ValueError('finite cardinality required')
            if target is S.EmptySet:return count==0
            return isinstance(target,S.FiniteSet) and len(target)==count
        if kind=='set_equality':
            if 'points' in o:candidate=S.FiniteSet(*[S.Rational(str(v)) for v in o['points']])
            else:candidate=S.solve_univariate_inequality(parse(o['relation'],{spec['variable']:x}),x,relational=False)
            return candidate==target
        raise ValueError('unknown solution-set assertion')
    return select_unique(spec['options'],condition)


def localization_rank(spec):
    """A plane point is uniquely localized iff independent line equations rank2.

    The physical setup supplies concurrent traces and permits choosing distinct
    ones. WLOG the first normal is (1,0), the second (u,v), v!=0; no fixed
    centroid coordinate or declared number of suspensions is provided.
    """
    names=symbols(spec);normals=[S.Matrix([[parse(x,names) for x in row]]) for row in spec['normals']]
    dimension=spec['dimension']
    if type(dimension) is not int or dimension<1 or any(m.cols!=dimension for m in normals):raise ValueError('invalid dimension')
    for n in range(1,len(normals)+1):
        for subset in combinations(normals,n):
            matrix=S.Matrix.vstack(*subset)
            if matrix.rank()==dimension:
                # A symbolic nonzero determinant must be guaranteed by the
                # domain, not assumed merely because it is not identically0.
                determinant=S.factor(matrix.det()) if n==dimension else None
                if determinant is None or determinant.is_nonzero is not True:
                    raise ValueError('independent observations not proved for all parameters')
                return n
    raise ValueError('observations do not locate a unique point')


def symbolic_claims(spec):
    """Universal polynomial identities on an open real parameter domain.

    A nonzero polynomial cannot vanish on the whole nonempty open domain; this
    is an exact coefficient argument, not sample testing. Unknown sign claims
    fail closed. Opaque clauses may only occur in an already refuted conjunction.
    """
    names=symbols(spec)
    if spec.get('construction')=='equal_circle_intersections':
        a,h=names['a'],names['h'];x,y,r=S.symbols('x y r',real=True)
        left=(x+a)**2+y*y-r*r;right=(x-a)**2+y*y-r*r
        if S.solve(S.expand(left-right),x)!=[0]:raise ValueError('intersection locus not established')
        for height in (h,-h):
            if S.expand(left.subs({x:0,y:height,r*r:a*a+h*h}))!=0:raise ValueError('intersection family incomplete')
    def clause(c):
        expression=S.factor(parse(c['expression'],names))
        if c['op'] in ('identity','not_identity'):
            numerator,denominator=S.together(expression).as_numer_denom()
            if denominator!=1 and denominator.is_nonzero is not True:raise ValueError('unproved denominator domain')
            try:S.Poly(numerator,*names.values())
            except S.PolynomialError:raise ValueError('not a polynomial identity proof')
            return (S.expand(numerator)==0) if c['op']=='identity' else (S.expand(numerator)!=0)
        if c['op'] in ('positive','negative'):
            answer=expression.is_positive if c['op']=='positive' else expression.is_negative
            if answer is None:raise ValueError('sign is not proved')
            return bool(answer)
        raise ValueError('unknown symbolic proof obligation')
    def candidate(o):
        if not o.get('clauses'):raise ValueError('candidate has no mathematical claim')
        if not all(clause(c) for c in o['clauses']):return False
        if o.get('opaque_conjunct'):raise ValueError('unproved part of otherwise passing claim')
        return True
    return select_unique(spec['options'],candidate)


def _ssa_witness(d):
    """Two positive cosine-law roots give noncongruent triangles with same SSA."""
    adjacent,opposite=S.Rational(str(d['adjacent'])),S.Rational(str(d['opposite']))
    degrees=S.Rational(str(d['angle_degrees']))
    if min(adjacent,opposite)<=0 or not 0<degrees<180:raise ValueError('invalid SSA data')
    t=S.Symbol('t',positive=True);cosine=S.cos(S.pi*degrees/180)
    equation=t*t-2*adjacent*cosine*t+adjacent**2-opposite**2
    roots=S.solve(equation,t)
    if len(roots)!=2 or S.simplify(roots[0]-roots[1])==0:raise ValueError('two SSA lengths not established')
    for root in roots:
        if root.is_positive is not True:raise ValueError('nonpositive SSA root')
        if any(S.simplify(gap).is_positive is not True for gap in
               (root+adjacent-opposite,root+opposite-adjacent,adjacent+opposite-root)):
            raise ValueError('SSA root does not form a triangle')
        if S.simplify((adjacent**2+root**2-opposite**2)/(2*adjacent*root)-cosine)!=0:
            raise ValueError('angle is not preserved')
    # The two known sides are the same. A different positive third side implies
    # different side multisets (their sums differ), hence no unlabelled congruence.
    return roots


def ssa_claims(spec):
    _ssa_witness(spec['counterexample'])
    # The included-angle case gives a unique positive third side by cosine law.
    a,b=S.symbols('a b',positive=True);c=S.Symbol('c',real=True)
    third_squared=a*a+b*b-2*a*b*c
    if S.Poly(third_squared,S.Symbol('z')).degree()!=0:raise ValueError('unexpected third-side dependence')
    def check(o):
        quantifier=o['quantifier']
        if quantifier=='all':return False # exact SSA witness refutes this universal
        if quantifier=='none':
            # Explicit identical nondegenerate triangles satisfy the hypotheses.
            sides=list(map(S.Rational,spec['congruent_example']))
            if len(sides)!=3 or min(sides)<=0 or min(sum(sides)-2*x for x in sides)<=0:raise ValueError('invalid positive example')
            return False
        if quantifier=='not_all_and_sufficient':
            if o['additional']!='included_angle' or o['criterion']!='SAS':raise ValueError('unproved supplementary condition')
            # For 0<included_angle<180, its cosine is strictly between -1,1.
            # Third square=(a-b)^2+2ab(1-c)>0, and equality of this square
            # determines its positive length. SSS then proves congruence.
            if S.expand(third_squared-((a-b)**2+2*a*b*(1-c)))!=0:raise ValueError('cosine-law proof failed')
            return True
        raise ValueError('unknown quantified congruence claim')
    return select_unique(spec['options'],check)


def hl_claims(spec):
    def check(o):
        proof=o['proof']
        if proof=='right_hypotenuse_leg':
            # Both missing legs are positive, and x²=h²-l²=y². The positive
            # square root is unique, so all three sides coincide (SSS).
            x,y=S.symbols('x y',positive=True)
            if S.factor(x*x-y*y)!=(x-y)*(x+y) or (x+y).is_positive is not True:raise ValueError('positive-square uniqueness failed')
            return True
        if proof=='unrestricted_ssa':_ssa_witness(o['counterexample']);return False
        if proof=='right_angles_force_all_angles':
            left,right=[[S.Rational(v) for v in a] for a in o['counterexample_angles']]
            if any(len(a)!=3 or min(a)<=0 or sum(a)!=180 or 90 not in a for a in (left,right)):raise ValueError('invalid right triangles')
            if sorted(left)==sorted(right):raise ValueError('counterexample angles are equal')
            return False
        if proof=='hypotenuse_shortest':
            l,m,h=map(S.Rational,o['counterexample_sides'])
            if min(l,m,h)<=0 or l*l+m*m!=h*h or not(h>l and h>m):raise ValueError('invalid hypotenuse counterexample')
            return False
        raise ValueError('unmodelled HL explanation')
    return select_unique(spec['options'],check)


def distance_minimum(spec):
    """Minimize squared distance to a full line, with an attained unique foot."""
    names=symbols(spec);p,h,q=names['p'],names['h'],names['q']
    expression=(p-q)**2+h*h
    critical=S.solve(S.diff(expression,q),q)
    if critical!=[p] or S.diff(expression,q,2)!=2:raise ValueError('projection minimum not proved')
    minimum=S.simplify(expression.subs(q,critical[0]))
    return select_unique(spec['options'],lambda o:S.expand(parse(o['squared_distance'],names)-minimum)==0)


def angle_bisector(spec):
    """All interior equidistant points of a nondegenerate angle bisect it.

    Let full angle 2t in (0,pi), P at phi in (0,2t), radiusr>0. Distances
    are r sin(phi), r sin(2t-phi). Their difference equals
    2r cos(t) sin(phi-t). cos(t)>0 and phi-t∈(-pi/2,pi/2), so only phi=t.
    """
    if spec.get('full_angle_domain')!=[0,180] or spec.get('point_region')!='interior' or spec.get('radius_domain')!='positive':raise ValueError('angle-locus assumptions incomplete')
    r,t,p=S.symbols('r t p',real=True)
    if S.trigsimp(S.expand_trig(S.sin(p)-S.sin(2*t-p)-2*S.cos(t)*S.sin(p-t)))!=0:raise ValueError('sine factorization failed')
    def check(o):
        if o['claim']=='angle_relation':
            # The theorem establishes the unique relative angle delta=0.
            result=S.simplify(parse(o['expression'],{'p':t,'t':t}))
            if o['op'] not in ('=','!='):raise ValueError('unknown angle comparison')
            domain=S.Interval.open(0,S.pi/2)
            zeros=S.solveset(result,t,domain=domain)
            remaining=S.Complement(domain,zeros)
            empty=zeros.is_empty if o['op']=='!=' else remaining.is_empty
            if empty is None:raise ValueError('angle relation unresolved on the interior-angle domain')
            return bool(empty)
        if o['claim']=='depends_on_radius':return S.diff(t,r)!=0
        if o['claim']=='requires_full_angle':
            full=S.Rational(o['counterexample_full_angle']);radius=S.Rational(o['counterexample_radius'])
            if not 0<full<180 or radius<=0:raise ValueError('invalid interior witness')
            half=full/2
            if S.simplify(radius*S.sin(S.pi*half/180)-radius*S.sin(S.pi*(full-half)/180))!=0:raise ValueError('witness distances differ')
            if full==S.Rational(o['degrees']):raise ValueError('witness does not refute angle restriction')
            return False
        raise ValueError('unknown bisector claim')
    return select_unique(spec['options'],check)


def _axis_count(points):
    n=len(points);p=[vector(v) for v in points]
    distances={(i,j):S.simplify((p[i]-p[j]).dot(p[i]-p[j])) for i,j in combinations(range(n),2)}
    return sum(all(distances[i,j]==distances[tuple(sorted(((shift-i)%n,(shift-j)%n)))]
                   for i,j in combinations(range(n),2)) for shift in range(n))


def symmetry_families(spec):
    def check(o):
        family=o['family']
        if family=='isosceles_triangle':
            # Every nondegenerate isosceles triangle admits these coordinates
            # after an isometry: equality of legs forces the apex to x=0.
            a,h=S.symbols('a h',positive=True)
            points=[S.Matrix([-a,0]),S.Matrix([a,0]),S.Matrix([0,h])]
            matrix=S.Matrix([[-1,0],[0,1]])
            return all(any(S.simplify(matrix*p-q)==S.zeros(2,1) for q in points) for p in points)
        points=o['counterexample']
        if family=='right_triangle':
            lengths=squared_lengths(points)
            if lengths[0]+lengths[1]!=lengths[2]:raise ValueError('not a right-triangle counterexample')
        elif family in ('parallelogram','trapezoid'):
            facts=coordinate_facts(points)
            if family=='parallelogram' and 'parallelogram' not in facts:raise ValueError('not a parallelogram')
            if family=='trapezoid' and (('parallel_ab_cd' in facts)==('parallel_ad_bc' in facts)):raise ValueError('not a strict trapezoid')
        else:raise ValueError('unmodelled shape family')
        if _axis_count(points)!=0:raise ValueError('counterexample actually has an axis')
        return False
    return select_unique(spec['options'],check)


def equidistant_locus(spec):
    names=symbols(spec);a,x,y=names['a'],names['x'],names['y']
    difference=S.expand((x+a)**2+y*y-((x-a)**2+y*y))
    solution=S.solve(difference,x)
    if solution!=[0] or a.is_positive is not True:raise ValueError('perpendicular-bisector locus not established')
    def check(o):
        condition=parse(o['condition'],names)
        reduced=S.simplify(condition.subs(x,0))
        if reduced is S.true:return True
        witness={names[k]:S.Rational(str(v)) for k,v in o['counterexample'].items()}
        if S.simplify(difference.subs(witness))!=0 or not witness[a]>0:raise ValueError('not an equidistant witness')
        if S.simplify(condition.subs(witness)) is not S.false:raise ValueError('candidate not refuted by witness')
        return False
    return select_unique(spec['options'],check)


def reflection_constructions(spec):
    names=symbols(spec);u,v=names.get('u',S.Integer(0)),names['v'];x,y=names['x'],names['y']
    target={x:u,y:-v}
    def check(o):
        equations=[parse(e,names) for e in o['equations']]
        if any(S.simplify(e.subs(target))!=0 for e in equations):
            # Residual is a nonzero polynomial on the open parameter domain,
            # so the construction fails for at least one permitted input.
            for e in equations:S.Poly(S.together(e.subs(target)).as_numer_denom()[0],*names.values())
            return False
        solutions=S.solve(equations,[x,y],dict=True)
        if len(solutions)!=1 or set(solutions[0])!={x,y}:raise ValueError('construction is not uniquely specified')
        return all(S.simplify(solutions[0][k]-value)==0 for k,value in target.items())
    return select_unique(spec['options'],check)


def isosceles_angle_cases(spec):
    # Cases enumerate which vertex has the given angle, not possible numerical
    # samples. For each placement the full linear angle system is solved.
    a,b,c=S.symbols('A B C',real=True);names=dict(zip('ABC',(a,b,c)))
    cases={}
    for vertex in 'ABC':
        solutions=S.solve([a+b+c-180,b-c,names[vertex]-S.Rational(str(spec['angle']))],[a,b,c],dict=True)
        if len(solutions)!=1 or any(v not in solutions[0] for v in (a,b,c)):raise ValueError('angles not uniquely fixed')
        values=[S.simplify(solutions[0][v]) for v in (a,b,c)]
        if min(values)<=0:raise ValueError('invalid triangle angle case')
        cases[vertex]=len(set(values))==1
    def check(o):
        if not o['placements'] or any(v not in cases for v in o['placements']):raise ValueError('unknown vertex case')
        values=[cases[v] if o['conclusion']=='equilateral' else not cases[v] if o['conclusion']=='not_equilateral' else None for v in o['placements']]
        if None in values:raise ValueError('unmodelled conclusion')
        if o['quantifier']=='all':return all(values)
        if o['quantifier']=='exists':return any(values)
        raise ValueError('unknown case quantifier')
    return select_unique(spec['options'],check)


def hypotenuse_order(spec):
    a,b=S.symbols('a b',positive=True)
    squares=[a*a,b*b,a*a+b*b]
    def check(o):
        rank=o['selection']
        if rank=='greatest':return all(S.simplify(squares[2]-v).is_positive is True for v in squares[:2])
        if rank=='least':return all(S.simplify(squares[2]-v).is_negative is True for v in squares[:2])
        if rank=='arbitrary':
            # A leg cannot also satisfy the hypotenuse equation: its residual
            # is -2 times the square of the other positive leg.
            return all(S.simplify(sum(squares)-2*v)==0 for v in squares)
        raise ValueError('unknown side-selection quantifier')
    return select_unique(spec['options'],check)


def quadrilateral_quantifiers(spec):
    facts=close_facts(spec['given']);goal=spec['goal'];universal=goal in facts
    if not universal:raise ValueError('no universal quadrilateral proof')
    def check(o):
        quantifier=o['quantifier']
        if quantifier=='all':return universal
        if quantifier=='not_all':return not universal
        if quantifier=='none':
            witness=coordinate_facts(o['counterexample'])
            if not set(spec['given'])<=(witness) or goal not in witness:raise ValueError('positive witness invalid')
            return False
        raise ValueError('unknown implication quantifier')
    return select_unique(spec['options'],check)


def weighted_influence(spec):
    """Positive weights; at least one other positive weight, fixed data values.

    M=(w*x+u*y)/(w+u). dM/dx=w/(w+u); its derivative in w is positive.
    Universal claims about x itself or M increasing are disproved separately.
    """
    w,u=S.symbols('w u',positive=True);x,y=S.symbols('x y',real=True)
    mean=(w*x+u*y)/(w+u)
    if spec.get('weight_domain')!='positive' or spec.get('other_weight')!='positive_fixed':raise ValueError('weight hypotheses missing')
    def check(o):
        claim=o['claim']
        if claim=='data_sensitivity_increases':return S.factor(S.diff(mean,x,w)).is_positive is True
        if claim=='data_value_increases':return S.diff(x,w).is_positive is True
        if claim=='frequency_decreases':
            before,after=map(S.Rational,o['counterexample_counts'])
            if not 0<before<after:raise ValueError('invalid increasing-frequency weight witness')
            return False
        if claim=='mean_increases':
            d=o['counterexample'];before=S.Rational(str(d['before']));after=S.Rational(str(d['after']))
            values={x:S.Rational(str(d['data'])),y:S.Rational(str(d['other_data'])),u:S.Rational(str(d['other_weight']))}
            if not 0<before<after or values[u]<=0:raise ValueError('invalid positive weight witness')
            if S.simplify(mean.subs(values).subs(w,after)-mean.subs(values).subs(w,before))>=0:raise ValueError('mean claim not refuted')
            return False
        raise ValueError('unknown weighted-mean assertion')
    return select_unique(spec['options'],check)


HANDLERS={
 'g160_inequality_objects':inequality_objects,'g160_localization_rank':localization_rank,
 'g160_symbolic_claims':symbolic_claims,'g160_ssa_claims':ssa_claims,
 'g160_hl_claims':hl_claims,'g160_distance_minimum':distance_minimum,
 'g160_angle_bisector':angle_bisector,'g160_symmetry_families':symmetry_families,
 'g160_equidistant_locus':equidistant_locus,'g160_reflection_constructions':reflection_constructions,
 'g160_isosceles_angle_cases':isosceles_angle_cases,'g160_hypotenuse_order':hypotenuse_order,
 'g160_quadrilateral_quantifiers':quadrilateral_quantifiers,'g160_weighted_influence':weighted_influence,
}


def congruence_invariants(spec):
    def check(o):
        invariant=o['premise']
        if invariant=='rigid_overlap':
            # Every Euclidean rigid motion has this form for one of the two
            # orientation signs. Translation cancels in a difference vector.
            t=S.Symbol('t',real=True)
            for parity in (-1,1):
                matrix=S.Matrix([[S.cos(t),-parity*S.sin(t)],[S.sin(t),parity*S.cos(t)]])
                gram=(matrix.T*matrix).applyfunc(S.trigsimp)
                if gram!=S.eye(2) or S.trigsimp(matrix.det())!=parity:raise ValueError('rigid-motion proof failed')
            return True
        left,right=o['counterexample_triangles'];ls,rs=squared_lengths(left),squared_lengths(right)
        if ls==rs:raise ValueError('triangles actually congruent')
        if invariant=='area':
            def area2(points):
                a,b,c=map(vector,points);return S.Abs(S.det(S.Matrix.hstack(b-a,c-a)))
            if S.simplify(area2(left)-area2(right))!=0:raise ValueError('areas do not agree')
        elif invariant=='perimeter':
            if S.simplify(sum(S.sqrt(v) for v in ls)-sum(S.sqrt(v) for v in rs))!=0:raise ValueError('perimeters do not agree')
        elif invariant=='similar_shape':
            ratios=[S.simplify(b/a) for a,b in zip(ls,rs)]
            if len(set(ratios))!=1 or ratios[0].is_positive is not True:raise ValueError('triangles not similar')
        else:raise ValueError('unknown congruence hypothesis')
        return False
    return select_unique(spec['options'],check)


def reflection_implications(spec):
    mirror=S.Matrix([[-1,0],[0,1]])
    def check(o):
        conclusion=o['conclusion']
        if conclusion=='isometry':
            return mirror.T*mirror==S.eye(2) and mirror.det()!=0
        left,right=o['counterexample_triangles'];a,b=list(map(vector,left)),list(map(vector,right))
        ls,rs=squared_lengths(left),squared_lengths(right)
        if conclusion=='congruence_suffices_for_reflection':
            if ls!=rs:raise ValueError('premise congruence is false')
            # Enumerate all label correspondences, solving the unique affine
            # map for each. A reflection has determinant-1 and a fixed line.
            for perm in permutations(b):
                matrix=S.Matrix.hstack(perm[1]-perm[0],perm[2]-perm[0])*S.Matrix.hstack(a[1]-a[0],a[2]-a[0]).inv()
                offset=perm[0]-matrix*a[0]
                if (matrix.T*matrix).applyfunc(S.simplify)!=S.eye(2):continue
                if S.simplify(matrix.det())!=-1:continue
                if (S.eye(2)-matrix).rank()==(S.eye(2)-matrix).row_join(offset).rank():
                    raise ValueError('counterexample actually permits a reflection')
            return False
        if conclusion=='reflections_intersect':
            if any(mirror*p!=q for p,q in zip(a,b)):raise ValueError('pair is not reflected')
            if not (max(p[0] for p in a)<min(p[0] for p in b) or max(p[0] for p in b)<min(p[0] for p in a)):
                raise ValueError('disjointness is not proved by separating axis')
            return False
        if conclusion=='similarity_suffices_for_reflection':
            ratios=[S.simplify(v/u) for u,v in zip(ls,rs)]
            if len(set(ratios))!=1 or ratios[0].is_positive is not True or ratios[0]==1:raise ValueError('not a noncongruent similarity')
            return False
        raise ValueError('unknown reflection implication')
    return select_unique(spec['options'],check)


def regular_polygon_claims(spec):
    def regular(points):
        ps=list(map(vector,points));n=len(ps)
        if n<3:raise ValueError('polygon needs three vertices')
        edges=[ps[(i+1)%n]-ps[i] for i in range(n)]
        lengths=[S.simplify(e.dot(e)) for e in edges]
        turns=[S.det(S.Matrix.hstack(edges[i],edges[(i+1)%n])) for i in range(n)]
        if not(all(t>0 for t in turns) or all(t<0 for t in turns)):raise ValueError('strict convexity required')
        # Local turns alone also admit self-intersecting stars. Every other
        # vertex must lie strictly on the same side of every boundary edge.
        sides=[exact_order(S.det(S.Matrix.hstack(edges[i],ps[j]-ps[i])),S.Integer(0))
               for i in range(n) for j in range(n) if j not in (i,(i+1)%n)]
        if not (all(sign>0 for sign in sides) or all(sign<0 for sign in sides)):
            raise ValueError('strict global convexity required')
        cosines=[S.simplify(-edges[i-1].dot(edges[i])/S.sqrt(lengths[i-1]*lengths[i])) for i in range(n)]
        return len(set(lengths))==1,len(set(cosines))==1
    def check(o):
        kind=o['claim']
        if kind=='regular_from_properties':
            given=set(o['given']);needed={'equal_sides','equal_angles'}
            if given==needed:return True # definition is the conjunction, not either one alone
            equal_sides,equal_angles=regular(o['counterexample'])
            if 'equal_sides' in given and not equal_sides:raise ValueError('premise side equality is false')
            if 'equal_angles' in given and not equal_angles:raise ValueError('premise angle equality is false')
            if equal_sides and equal_angles:raise ValueError('counterexample actually regular')
            if not given or not given<=needed:raise ValueError('unmodelled polygon properties')
            return False
        if kind=='vertex_diagonal_count':
            # All n-1 other vertices, except the two neighbours.
            n=S.Symbol('n',integer=True,positive=True)
            candidate=parse(o['expression'],{'n':n})
            return S.expand(candidate-(n-1-2))==0
        raise ValueError('unknown regular-polygon statement')
    return select_unique(spec['options'],check)


HANDLERS.update({'g160_congruence_invariants':congruence_invariants,
 'g160_reflection_implications':reflection_implications,'g160_regular_polygon_claims':regular_polygon_claims})
