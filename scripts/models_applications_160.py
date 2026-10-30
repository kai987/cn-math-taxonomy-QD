"""Exact source-bound application proofs for the remaining-question audit.

Candidate claims are mathematical relations, never declared truth values or
answer keys. Universal conclusions require an exact proof; refutations require
an exact, premise-satisfying counterexample. Every candidate is evaluated.
"""
from fractions import Fraction
from itertools import permutations
import re
import sympy as S

from exact_polynomial import _parse, _source
from model_types import select_unique
from models_symbolic import parse_math


_ASSUMPTIONS={'real':{'real':True},'positive':{'positive':True},
              'nonnegative':{'nonnegative':True},'nonzero':{'real':True,'nonzero':True}}


def symbols(assumptions):
    if not isinstance(assumptions,dict) or not assumptions or len(assumptions)>8:raise ValueError('bounded mathematical variables required')
    if any(not re.fullmatch('[a-z]',name) or kind not in _ASSUMPTIONS for name,kind in assumptions.items()):raise ValueError('invalid variable assumption')
    return {name:S.Symbol(name,**_ASSUMPTIONS[kind]) for name,kind in assumptions.items()}


def polynomial(source,variables):
    normalized=_source(str(source))
    unknown=set(re.findall('[a-z]',normalized))-set(variables)
    terms=_parse(normalized)
    if unknown:raise ValueError('undeclared polynomial variable')
    return S.Add(*(S.Rational(c.numerator,c.denominator)*S.Mul(*(variables[name] for name in m)) for m,c in terms.items()))


def exact_number(source):
    # This is still the bounded arithmetic grammar; no Python eval/sympify.
    normalized=_source(str(source))
    if re.search('[a-z]',normalized):raise ValueError('witness must be a closed rational number')
    terms=_parse(normalized)
    if set(terms)-{()}:raise ValueError('witness must be a rational number')
    return S.Rational(terms.get((),Fraction(0)))


def relation(r,variables):
    if set(r)!={'left','op','right'} or r['op'] not in ('=','!=','<','<=','>','>='):raise ValueError('unsupported mathematical relation')
    return polynomial(r['left'],variables)-polynomial(r['right'],variables),r['op']


def decide_constant(value,op):
    value=S.factor(value)
    if op=='=':result=value.is_zero
    elif op=='!=':result=None if value.is_zero is None else not value.is_zero
    elif op=='>':result=value.is_positive
    elif op=='>=':result=value.is_nonnegative
    elif op=='<':result=value.is_negative
    else:result=value.is_nonpositive
    return None if result is None else bool(result)


def _assignment(case,variables,key):
    source=case.get(key)
    if not isinstance(source,dict) or set(source)!=set(variables):raise ValueError('a complete exact '+key+' is required')
    values={variables[name]:exact_number(value) for name,value in source.items()}
    for symbol,value in values.items():
        if symbol.is_positive is True and value<=0:raise ValueError('witness violates positivity')
        if symbol.is_nonnegative is True and value<0:raise ValueError('witness violates nonnegativity')
        if symbol.is_zero is False and value==0:raise ValueError('witness violates nonzero premise')
    return values


def homothety_exists(first,second):
    """Existence for *sets*, checking every bijection, not a chosen ordering."""
    if len(first)!=len(second) or not 3<=len(first)<=5:raise ValueError('three to five paired planar vertices required')
    if len({tuple(p) for p in first})!=len(first) or len({tuple(p) for p in second})!=len(second):raise ValueError('vertices must be distinct')
    if any(len(p)!=2 for p in first+second):raise ValueError('planar vertices required')
    if S.det(S.Matrix.hstack(first[1]-first[0],first[2]-first[0]))==0:raise ValueError('noncollinear first three vertices required')
    k,t,u=S.symbols('k t u',real=True)
    for ordering in permutations(second):
        equations=[coordinate for p,q in zip(first,ordering) for coordinate in (k*p[0]+t-q[0],k*p[1]+u-q[1])]
        solutions=S.linsolve(equations,[k,t,u])
        for solution in solutions:
            if solution[0].is_zero is False:
                unit_scale = S.simplify(solution[0]-1).is_zero
                if unit_scale is None:raise ValueError('unit-scale case is unresolved')
                if not unit_scale:return True  # centre = translation/(1-k)
                # A nonzero pure translation has no finite homothety centre.
                # The identity (k=1, translation=0) is allowed.
                if all(value.is_zero is True for value in solution[1:]):return True
                if any(value.is_zero is None for value in solution[1:]):
                    raise ValueError('identity translation is unresolved')
            if solution[0].is_zero is None:raise ValueError('set homothety existence unresolved')
    return False


def similarity_homothety_refutation(case):
    """A valid exact similarity pair can refute, never establish, universality."""
    first=[S.Matrix([exact_number(v) for v in point]) for point in case['points']]
    matrix=S.Matrix([[exact_number(v) for v in row] for row in case['matrix']])
    shift=S.Matrix([exact_number(v) for v in case.get('translation',[0,0])])
    if matrix.shape!=(2,2) or shift.shape!=(2,1):raise ValueError('planar affine similarity required')
    gram=matrix.T*matrix;scale=gram[0,0]
    if scale.is_positive is not True or gram!=S.eye(2)*scale:raise ValueError('matrix is not a nonsingular similarity')
    second=[matrix*p+shift for p in first]
    if homothety_exists(first,second):raise ValueError('the constructed similar pair does not refute the universal implication')
    return False


def prove_case(case):
    if case.get('construction')=='similarity_pair':return similarity_homothety_refutation(case)
    variables=symbols(case['variables'])
    premises=[relation(r,variables) for r in case.get('premises',[])]
    conclusions=[relation(r,variables) for r in case['conclusions']]
    if not conclusions:raise ValueError('missing mathematical conclusion')
    witness=_assignment(case,variables,'witness')
    if not all(decide_constant(e.subs(witness),op) is True for e,op in premises):raise ValueError('premises have no valid supplied witness')
    equations=[e for e,op in premises if op=='=']
    # Saturation encodes only explicit nonzero premises; it cannot infer an
    # inverse for a variable allowed to be zero. This avoids division by zero.
    inverses=[]
    for e,op in premises:
        if op=='!=':
            inv=S.Dummy('inverse',real=True);inverses.append(inv);equations.append(e*inv-1)
    unknowns=list(variables.values())+inverses
    basis=S.groebner(equations,*unknowns,domain=S.QQ) if equations else None
    if basis is not None and basis.contains(S.Integer(1)):raise ValueError('inconsistent equalities')
    normal=lambda e:S.factor(basis.reduce(S.expand(e))[1]) if basis is not None else S.factor(e)
    mode=case.get('mode','forall')
    if mode not in ('forall','not_forall','exists'):raise ValueError('unknown mathematical quantifier')
    if mode=='exists':
        if not all(decide_constant(e.subs(witness),op) is True for e,op in conclusions):raise ValueError('existential witness does not establish every conclusion')
        return True
    certificates=case.get('certificates',{})
    proven=[]
    for index,(e,op) in enumerate(conclusions):
        reduced=normal(e);result=decide_constant(reduced,op)
        if result is not True and str(index) in certificates:
            squares=certificates[str(index)]['squares']
            if not squares or op not in ('>=','<='):raise ValueError('sum-of-squares certificate requires a weak sign goal')
            sos=sum(polynomial(source,variables)**2 for source in squares)
            if normal(e-(sos if op=='>=' else -sos))!=0:raise ValueError('incorrect sum-of-squares certificate')
            result=True
        if result is not True:
            # A directly supplied inequality can establish an identical goal
            # after exact equality elimination, including strict versus weak.
            for known,kop in premises:
                if normal(known-reduced)==0 and (kop==op or kop=='>' and op in ('>=','!=') or kop=='<' and op in ('<=','!=')):
                    result=True;break
        proven.append(result is True)
    if all(proven):holds=True
    else:
        counterexample=_assignment(case,variables,'counterexample')
        if not all(decide_constant(e.subs(counterexample),op) is True for e,op in premises):raise ValueError('counterexample violates premise')
        if all(decide_constant(e.subs(counterexample),op) is True for e,op in conclusions):raise ValueError('counterexample does not refute the conclusion')
        holds=False
    return holds if mode=='forall' else not holds


def relation_proofs(spec):
    def check(option):
        cases=option.get('cases')
        if not isinstance(cases,list) or not cases:raise ValueError('missing candidate proof obligations')
        results=[prove_case(case) for case in cases]
        return all(results)
    return select_unique(spec['options'],check)


def _symbolic(source,assumptions):
    expression,conditions=parse_math(str(source),assumptions)
    if any(S.simplify(condition) is not S.true for condition in conditions):raise ValueError('unproved symbolic domain')
    return expression


def circle_pairs(spec):
    """Arc = r*theta, chord² from the exact squared Euclidean distance.

    A(r,0), B(r cos(theta),r sin(theta)) gives 2r²(1-cos(theta)).
    Each case supplies two circles/arcs and compares computed quantities.
    Equal expressions prove a universal equality; nonidentity is rejected only
    after a valid exact pair with different quantities is checked.
    """
    def case_holds(case):
        assumptions=case['variables'];env=symbols(assumptions)
        if len(env)>4:raise ValueError('at most four circle parameters')
        circles=[]
        for circle in case['circles']:
            r=_symbolic(circle['radius'],assumptions);theta=_symbolic(circle['angle'],assumptions)
            circles.append({'arc':r*theta,'angle':theta,'chord_squared':S.simplify((r*S.cos(theta)-r)**2+(r*S.sin(theta))**2)})
        if len(circles)!=2:raise ValueError('two arcs required')
        if set(case['witness'])!=set(env):raise ValueError('complete circular witness required')
        substitutions={env[name]:_symbolic(value,{}) for name,value in case['witness'].items()}
        for symbol,value in substitutions.items():
            if value.free_symbols or value.is_real is not True:raise ValueError('closed real witness required')
            if symbol.is_positive is True and value.is_positive is not True:raise ValueError('witness violates positivity')
            if symbol.is_nonnegative is True and value.is_nonnegative is not True:raise ValueError('witness violates nonnegativity')
            if symbol.is_zero is False and value.is_zero is not False:raise ValueError('witness violates nonzero premise')
        for circle in case['circles']:
            radius=_symbolic(circle['radius'],assumptions).subs(substitutions)
            theta=_symbolic(circle['angle'],assumptions).subs(substitutions)
            if radius.is_positive is not True or S.simplify(theta).is_positive is not True or S.simplify(2*S.pi-theta).is_positive is not True:raise ValueError('invalid circular witness')
        quantity=case['quantity']
        if quantity not in circles[0]:raise ValueError('unknown circle quantity')
        difference=S.simplify(circles[0][quantity]-circles[1][quantity])
        if difference==0:equal=True
        else:
            value=S.simplify(difference.subs(substitutions))
            if value.is_zero is not False:raise ValueError('circle nonidentity requires exact unequal witness')
            equal=False
        mode=case['mode']
        if mode not in ('equal','not_always_equal'):raise ValueError('unknown arc comparison')
        return equal if mode=='equal' else not equal
    def check(o):
        if not isinstance(o.get('cases'),list) or not o['cases']:raise ValueError('missing circular proof obligations')
        return all([case_holds(c) for c in o['cases']])
    return select_unique(spec['options'],check)


def cone_development(spec):
    """Compute boundary lengths of the actual conical surface parametrization.

    X(t,a)=(tr cos a,tr sin a,th). Generator speed is sqrt(r²+h²).
    At t=1 the rim speed is r; integrating 0..2pi gives the sector arc.
    """
    assumptions=spec['variables'];r=_symbolic(spec['radius'],assumptions);h=_symbolic(spec['height'],assumptions)
    if r.is_positive is not True or h.is_positive is not True:raise ValueError('positive nondegenerate cone required')
    t,a=S.symbols('t a',real=True)
    surface=S.Matrix([t*r*S.cos(a),t*r*S.sin(a),t*h])
    generator=S.diff(surface,t);rim=S.diff(surface.subs(t,1),a)
    radius=S.integrate(S.sqrt(S.simplify(generator.dot(generator))),(t,0,1))
    arc=S.integrate(S.sqrt(S.simplify(rim.dot(rim))),(a,0,2*S.pi))
    env=symbols(assumptions);values=_assignment({'witness':spec['witness']},env,'witness')
    def check(o):
        differences=[S.simplify(radius-_symbolic(o['radius'],assumptions)),S.simplify(arc-_symbolic(o['arc'],assumptions))]
        if all(value==0 for value in differences):return True
        if any(S.simplify(value.subs(values)).is_zero is False for value in differences):return False
        raise ValueError('cone nonidentity has no legal exact counterexample')
    return select_unique(spec['options'],check)


def circumcircle_chord(spec):
    """Solve equal-distance equations for supplied nondegenerate vertices."""
    assumptions=spec['variables'];env=symbols(assumptions)
    vertices=[S.Matrix([_symbolic(value,assumptions) for value in point]) for point in spec['vertices']]
    if len(vertices)!=3 or any(len(v)!=2 for v in vertices):raise ValueError('three planar vertices required')
    determinant=S.simplify(S.det(S.Matrix.hstack(vertices[1]-vertices[0],vertices[2]-vertices[0])))
    if determinant.is_zero is not False:raise ValueError('nondegeneracy is unproved')
    x,y=S.Dummy('center_x',real=True),S.Dummy('center_y',real=True)
    distance=lambda point:S.expand((x-point[0])**2+(y-point[1])**2)
    solution=S.solve([distance(vertices[0])-distance(v) for v in vertices[1:]],[x,y],dict=True)
    if len(solution)!=1:raise ValueError('circumcircle is not unique')
    radius_squared=S.factor(distance(vertices[0]).subs(solution[0]))
    i,j=spec['chord']
    if type(i) is not int or type(j) is not int or not 0<=i<3 or not 0<=j<3 or i==j:raise ValueError('invalid chord')
    vector=vertices[i]-vertices[j];chord_squared=S.factor(vector.dot(vector))
    witness=_assignment({'witness':spec['witness']},env,'witness')
    def check(o):
        ratio=exact_number(o['radius_squared_factor']);difference=S.factor(chord_squared-ratio*radius_squared)
        if o['op'] not in ('=','!=','<','<=','>','>='):raise ValueError('unknown chord comparison')
        quantifier=o.get('quantifier','forall')
        if quantifier not in ('forall','not_forall'):raise ValueError('unknown chord quantifier')
        result=decide_constant(difference,o['op'])
        if result is None:
            if decide_constant(difference.subs(witness),o['op']) is False:result=False
            else:raise ValueError('chord comparison unresolved')
        return result if quantifier=='forall' else not result
    return select_unique(spec['options'],check)


def tangent_conditions(spec):
    """Substitute a parametric line into a circle and derive its discriminant.

    A positive leading quadratic coefficient excludes a zero direction vector.
    Exactly one real intersection is equivalent to zero discriminant.
    """
    def check(o):
        case=dict(o['case']);env=symbols(case['variables'])
        center=[polynomial(e,env) for e in spec['center']];r=polynomial(spec['radius'],env)
        if r.is_positive is not True:raise ValueError('positive radius required')
        point=[polynomial(e,env) for e in o['point']];direction=[polynomial(e,env) for e in o['direction']]
        if any(len(v)!=2 for v in (center,point,direction)):raise ValueError('planar coordinates required')
        u=S.Dummy('line_parameter',real=True)
        equation=sum((point[k]+u*direction[k]-center[k])**2 for k in range(2))-r**2
        q=S.Poly(S.expand(equation),u)
        a,b,c=q.nth(2),q.nth(1),q.nth(0)
        # A line has a nonzero direction; this is a domain condition, never
        # a false option manufactured from a degenerate point parametrization.
        case['premises']=list(case.get('premises',[]))+[{'left':str(S.expand(a)),'op':'>','right':'0'}]
        case['conclusions']=[{'left':str(S.expand(b*b-4*a*c)),'op':'=','right':'0'}]
        return prove_case(case)
    return select_unique(spec['options'],check)


def obtuse_circumcenter(spec):
    """General normalized triangle (0,0),(1,0),(u,v), v>0.

    The third angle is obtuse precisely when its two incident edge vectors
    have negative dot product. A positive gap g is its negation. Equal-distance
    equations derive the centre; exact reduction gives centre_y=-g/(2v)<0.
    All triangle points are in y>=0, so the centre is strictly outside.
    """
    if spec.get('normalization')!={'base':[[0,0],[1,0]],'third':['u','v'],'obtuse_at':'third'}:raise ValueError('source must declare the normalized obtuse-vertex geometry')
    u,v,g=S.symbols('u v g',real=True)
    v=S.Symbol('v',positive=True);g=S.Symbol('g',positive=True)
    env={'u':u,'v':v,'g':g}
    witness=_assignment({'witness':spec['witness']},env,'witness')
    third=S.Matrix([u,v]);a=S.Matrix([0,0]);b=S.Matrix([1,0])
    dot=S.expand((a-third).dot(b-third));constraint=dot+g
    if S.simplify(constraint.subs(witness))!=0:raise ValueError('witness does not satisfy the obtuse-angle gap')
    x,y=S.Dummy('center_x',real=True),S.Dummy('center_y',real=True)
    dist=lambda p:(x-p[0])**2+(y-p[1])**2
    solutions=S.solve([dist(a)-dist(b),dist(a)-dist(third)],[x,y],dict=True)
    if len(solutions)!=1:raise ValueError('circumcenter is not unique')
    cy=S.together(solutions[0][y]);numerator,denominator=cy.as_numer_denom()
    numerator=S.groebner([constraint],u,v,g).reduce(S.expand(numerator))[1]
    if numerator.is_negative is not True or denominator.is_positive is not True:raise ValueError('outside half-plane is unproved')
    def check(o):
        if o['region'] not in ('inside','longest_side_midpoint','outside'):raise ValueError('unknown region')
        return o['region']=='outside'
    return select_unique(spec['options'],check)


HANDLERS={'app160_relation_proofs':relation_proofs,'app160_circle_pairs':circle_pairs,
          'app160_cone_development':cone_development,'app160_circumcircle_chord':circumcircle_chord,'app160_tangent_conditions':tangent_conditions,'app160_obtuse_circumcenter':obtuse_circumcenter}
