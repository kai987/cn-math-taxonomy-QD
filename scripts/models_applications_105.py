"""Answer-independent symbolic geometry, light fields and finite experiments.

Input strings use the bounded school-math AST parser only. A universal claim
needs a whole parameter-family proof; a negative implication needs a legal
countermodel. No handler knows a question id, key, or declared truth array.
"""
from itertools import permutations
from math import comb
import sympy as S
from sympy.calculus.util import function_range

from model_types import select_unique
from models_symbolic import parse_math
from models_algebra import implies, number, compare


def math(source,assumptions=None):
    if isinstance(source,bool):raise ValueError('Boolean is not mathematical data')
    expression,conditions=parse_math(str(source),assumptions or {})
    if any(S.simplify(c) is not S.true for c in conditions):raise ValueError('unproved arithmetic domain')
    if any(str(symbol) not in (assumptions or {}) for symbol in expression.free_symbols):raise ValueError('undeclared mathematical variable')
    return expression


def zero(expression):
    expression=S.simplify(expression)
    if expression.is_zero is None:raise ValueError('exact equality is unresolved')
    return bool(expression.is_zero)


def points(values,convex=False):
    ps=[S.Matrix([math(v) for v in row]) for row in values]
    if not 3<=len(ps)<=5 or any(len(p)!=2 for p in ps) or len({tuple(p) for p in ps})!=len(ps):raise ValueError('distinct planar vertices required')
    if zero(S.det(S.Matrix.hstack(ps[1]-ps[0],ps[2]-ps[0]))):raise ValueError('noncollinear vertices required')
    if convex:
        orientations=[]
        for i,p in enumerate(ps):
            edge=ps[(i+1)%len(ps)]-p
            sides=[S.simplify(S.det(S.Matrix.hstack(edge,ps[j]-p))) for j in range(len(ps)) if j not in (i,(i+1)%len(ps))]
            if all(s.is_positive is True for s in sides):orientations.append(1)
            elif all(s.is_negative is True for s in sides):orientations.append(-1)
            else:raise ValueError('simple strictly convex cyclic order required')
        if len(set(orientations))!=1:raise ValueError('inconsistent polygon orientation')
    return ps


def _centre(ps,construction):
    if len(ps)!=3:raise ValueError('a triangle must have exactly three vertices')
    x,y=S.symbols('x y',real=True);center=S.Matrix([x,y]);equations=[]
    if construction=='perpendicular_bisectors':
        squared=[S.expand((center-p).dot(center-p)) for p in ps]
        equations=[squared[0]-squared[i] for i in (1,2)]
    elif construction=='altitudes':
        equations=[(center-ps[i]).dot(ps[(i+2)%3]-ps[(i+1)%3]) for i in (0,1)]
    else:raise ValueError('unknown intersection construction')
    solution=S.solve(equations,[x,y],dict=True)
    if len(solution)!=1 or set(solution[0])!={x,y}:raise ValueError('intersection not unique')
    return center.subs(solution[0])


def _inscribed_center(ps,center):
    if len(ps)!=3:raise ValueError('a triangle must have exactly three vertices')
    weights=S.Matrix.hstack(ps[0]-ps[2],ps[1]-ps[2]).inv()*(center-ps[2])
    barycentric=[weights[0],weights[1],1-sum(weights)]
    signs=[S.simplify(v).is_positive for v in barycentric]
    if any(sign is False for sign in signs):return False
    if any(sign is None for sign in signs):raise ValueError('interiority is unresolved')
    distances=[]
    for i,p in enumerate(ps):
        edge=ps[(i+1)%3]-p
        distances.append(S.factor(S.det(S.Matrix.hstack(edge,center-p))**2/edge.dot(edge)))
    if not all(zero(d-distances[0]) for d in distances[1:]):return False
    if distances[0].is_positive is None:raise ValueError('positive incircle radius unresolved')
    return bool(distances[0].is_positive)


def incenter_intersections(spec):
    """Every triangle: a=x+y,b=x+z,c=y+z, x,y,z>0 (strict triangle inequalities).

    Derive the common intersection from unit-side bisector directions and show
    positive barycentrics, all three equal perpendicular distances, uniqueness.
    """
    if spec.get('family')!='nondegenerate_triangle':raise ValueError('triangle family missing')
    x,y,z=S.symbols('x y z',positive=True);a=x+y;b=x+z;c=y+z;s=x+y+z
    u=S.factor((b*b+c*c-a*a)/(2*c));v=2*S.sqrt(x*y*z*s)/c
    ps=[S.Matrix([0,0]),S.Matrix([c,0]),S.Matrix([u,v])]
    if not zero((ps[2]-ps[0]).dot(ps[2]-ps[0])-b*b) or not zero((ps[2]-ps[1]).dot(ps[2]-ps[1])-a*a):raise ValueError('triangle parametrization failed')
    center=S.simplify((b*ps[1]+c*ps[2])/(2*s));radius=S.factor(c*v/(2*s))
    if radius.is_positive is not True:raise ValueError('positive incircle radius unproved')
    lengths={(0,1):c,(0,2):b,(1,2):a};directions=[]
    for i in range(3):
        j=(i+1)%3;k=(i+2)%3
        # Squared lengths were proved above; positive a,b,c are their unique
        # positive roots. Do not repeatedly simplify a large radical norm.
        lij=lengths[tuple(sorted((i,j)))];lik=lengths[tuple(sorted((i,k)))]
        direction=S.simplify((ps[j]-ps[i])/lij+(ps[k]-ps[i])/lik);directions.append(direction)
        multiplier=S.factor(lij*lik/(2*s))
        if multiplier.is_positive is not True or any(not zero(v) for v in center-ps[i]-multiplier*direction):raise ValueError('internal bisector incidence unproved')
    determinant=S.factor(S.det(S.Matrix.hstack(directions[0],directions[1])))
    if determinant.is_positive is not True and determinant.is_negative is not True:raise ValueError('unique intersection unproved')
    for i,p in enumerate(ps):
        edge=ps[(i+1)%3]-p
        if not zero(S.det(S.Matrix.hstack(edge,center-p))**2/edge.dot(edge)-radius**2):raise ValueError('unequal side distances')
    # a,b,c are positive barycentric weights: center is strictly inside.
    def check(o):
        if o['intersection']=='internal_angle_bisectors':return True
        witness=points(o['counterexample'])
        if len(witness)!=3:raise ValueError('triangle counterexample must have exactly three vertices')
        constructed=_centre(witness,o['intersection'])
        if _inscribed_center(witness,constructed):raise ValueError('counterexample actually constructs an incenter')
        return False
    return select_unique(spec['options'],check)


def regular_polygon_metrics(spec):
    """Regular n>=3: alpha=pi/n lies in (0,pi/3].

    Vertices have normR; the side support normal at half-angle alpha has
    constant offsetR*cos(alpha). Three side support equations have determinant
    8*cos(alpha)*sin(alpha)^3>0, so their equidistant interior center is unique.
    """
    if spec.get('minimum_vertices')!=3:raise ValueError('regular polygon n>=3 required')
    alpha=S.Symbol('a',real=True);r=S.Symbol('r',positive=True)
    domain=S.Interval.Lopen(0,S.pi/3)
    cosine_range=function_range(S.cos(alpha),alpha,domain);sine_range=function_range(S.sin(alpha),alpha,domain)
    if cosine_range!=S.Interval.Ropen(S.Rational(1,2),1) or sine_range.inf!=0 or not sine_range.left_open:raise ValueError('strictly positive angular ranges unproved')
    c,t=S.symbols('c t',positive=True)
    normals=S.Matrix([[S.chebyshevt(k,c),S.chebyshevu(k-1,c)*t,1] for k in (1,3,5)])
    determinant=S.expand(normals.det());basis=S.groebner([c*c+t*t-1],c,t)
    if basis.reduce(S.expand(determinant-8*c*t**3))[1]!=0:raise ValueError('support-line uniqueness identity failed')
    angle=S.Symbol('b',real=True)
    v0=S.Matrix([r,0]);v1=S.Matrix([r*S.cos(2*alpha),r*S.sin(2*alpha)])
    unit=S.Matrix([S.cos(alpha),S.sin(alpha)])
    if not zero(S.trigsimp(unit.dot(v0)-r*S.cos(alpha))) or not zero(S.trigsimp(unit.dot(v1)-r*S.cos(alpha))):raise ValueError('apothem support formula failed')
    metrics={'apothem':r*S.cos(alpha),'circumradius':r,'incenter':S.zeros(2,1),'circumcenter':S.zeros(2,1),'central_angle':2*alpha,'interior_angle':S.pi-2*alpha}
    n=spec['counterexample_vertices'];rv=math(spec['counterexample_radius'])
    if type(n) is not int or n<3 or rv.is_positive is not True:raise ValueError('legal regular polygon witness required')
    def check(o):
        if o['left'] not in metrics or o['right'] not in metrics or o['op']!='=':raise ValueError('unknown metric claim')
        difference=metrics[o['left']]-metrics[o['right']]
        components=list(difference) if isinstance(difference,S.MatrixBase) else [difference]
        if all(S.simplify(v)==0 for v in components):return True
        witness={alpha:S.pi/n,r:rv}
        if any(S.simplify(v.subs(witness)).is_zero is False for v in components):return False
        raise ValueError('witness does not refute the universal metric equality')
    return select_unique(spec['options'],check)


def inscribed_angle_relations(spec):
    """A=(1,0), B=(cos2t,sin2t), C=(cos2(t+s),sin2(t+s)).

    0<t,0<s,t+s<pi gives every C on the complementary arc. The two
    positive chord lengths are2sin(t+s),2sin(s); their dot equals their product
    cos(t), so the inscribed angle is t on the unique (0,pi) angle branch.
    The opposite arc gives pi-t. Equal arcs give the same t on any equal circle.
    """
    if spec.get('circle_domain')!='nondegenerate_inscribed_angles':raise ValueError('circular domain missing')
    t,s=S.symbols('t s',real=True)
    p,q=S.symbols('p q',real=True)
    # A generic chord factorization proves both chord directions at once:
    # X(2p)-X(2q)=2sin(q-p)*(sin(p+q),-cos(p+q)).
    chord_identities=[S.cos(2*p)-S.cos(2*q)-2*S.sin(p+q)*S.sin(q-p),
                      S.sin(2*p)-S.sin(2*q)+2*S.cos(p+q)*S.sin(q-p)]
    if any(S.trigsimp(S.expand_trig(value))!=0 for value in chord_identities):raise ValueError('generic circle chord factorization failed')
    # The two unit directions have phases t+s and2t+s; their dot iscos(t).
    unit_identity=S.expand(S.expand_trig(S.sin(p)*S.sin(q)+S.cos(p)*S.cos(q)-S.cos(p-q)))
    if unit_identity!=0:raise ValueError('unit-chord cosine identity failed')
    metrics={'inscribed':t,'central':2*t,'same_arc_other':t,'opposite_arc':S.pi-t}
    tv=math(spec['counterexample_half_angle']);sv=math(spec['counterexample_offset'])
    if tv.is_positive is not True or sv.is_positive is not True or S.simplify(S.pi-tv-sv).is_positive is not True:raise ValueError('illegal circle witness')
    def check(o):
        if o['left'] not in metrics or o['right'] not in metrics or o['op']!='=':raise ValueError('unknown inscribed-angle claim')
        difference=S.simplify(metrics[o['left']]-metrics[o['right']])
        if difference==0:return True
        if S.simplify(difference.subs(t,tv)).is_zero is False:return False
        raise ValueError('circle witness does not refute equality')
    return select_unique(spec['options'],check)


def _similarity(first,second):
    if len(first)!=len(second):return False
    source=S.Matrix.hstack(first[1]-first[0],first[2]-first[0])
    if zero(source.det()):raise ValueError('nondegenerate polygon required')
    for ordered in permutations(second):
        matrix=S.Matrix.hstack(ordered[1]-ordered[0],ordered[2]-ordered[0])*source.inv()
        offset=ordered[0]-matrix*first[0];gram=matrix.T*matrix;scale=S.simplify(gram[0,0])
        if scale.is_positive is None:raise ValueError('similarity scale sign unresolved')
        if scale.is_positive is False:continue
        if not all(zero(v) for v in gram-S.eye(2)*scale):continue
        if all(all(zero(v) for v in matrix*p+offset-q) for p,q in zip(first,ordered)):return True
    return False


def _polygon_properties(ps):
    n=len(ps);edges=[ps[(i+1)%n]-p for i,p in enumerate(ps)];squares=[S.simplify(v.dot(v)) for v in edges]
    equal_sides=all(zero(v-squares[0]) for v in squares[1:])
    cosines=[S.simplify(-edges[i-1].dot(edges[i])/S.sqrt(squares[i-1]*squares[i])) for i in range(n)]
    equal_angles=all(zero(v-cosines[0]) for v in cosines[1:])
    right=all(zero(edges[i-1].dot(edges[i])) for i in range(n))
    return {'rectangle':n==4 and right,'rhombus':n==4 and equal_sides,'square':n==4 and right and equal_sides,'equiangular':equal_angles}


def polygon_similarity_families(spec):
    # Any square can be taken to this cyclic family by a rigid motion; a,b>0
    # then the explicit similarity matrix(b/a)I maps all four vertices.
    a,b=S.symbols('a b',positive=True)
    first=[S.Matrix(p) for p in [(0,0),(a,0),(a,a),(0,a)]];second=[S.Matrix(p) for p in [(0,0),(b,0),(b,b),(0,b)]]
    matrix=S.eye(2)*b/a
    if any(any(not zero(v) for v in matrix*p-q) for p,q in zip(first,second)):raise ValueError('square family map failed')
    if S.factor((matrix.T*matrix)[0,0]).is_positive is not True:raise ValueError('square similarity singular')
    def check(o):
        family=o['family']
        if family=='square':return True
        if family not in ('rectangle','rhombus','equiangular'):raise ValueError('unknown polygon family')
        p,q=[points(value,convex=True) for value in o['counterexample']]
        if len(p)!=len(q):raise ValueError('paired polygon counterexamples need the same number of vertices')
        if family=='equiangular':
            def angle_cosines(ps):
                edges=[ps[(i+1)%len(ps)]-point for i,point in enumerate(ps)]
                return [S.simplify(-edges[i-1].dot(edges[i])/S.sqrt(edges[i-1].dot(edges[i-1])*edges[i].dot(edges[i]))) for i in range(len(ps))]
            if not all(zero(a-b) for a,b in zip(angle_cosines(p),angle_cosines(q))):raise ValueError('corresponding angles of the pair are unequal')
        pprops,qprops=_polygon_properties(p),_polygon_properties(q)
        if not pprops[family] or not qprops[family]:raise ValueError('counterexample violates the named family')
        if _similarity(p,q):raise ValueError('counterexample polygons are actually similar')
        return False
    return select_unique(spec['options'],check)


def similarity_metrics(spec):
    """Gram matrix proof, including both orientation parities and positive scale."""
    k,a,b=S.symbols('k a b',positive=True);t,q=S.symbols('t q',real=True)
    for parity in (-1,1):
        matrix=k*S.Matrix([[S.cos(t),-parity*S.sin(t)],[S.sin(t),parity*S.cos(t)]])
        if any(S.trigsimp(v)!=0 for v in matrix.T*matrix-k*k*S.eye(2)):raise ValueError('similarity Gram identity failed')
    # Dot scales byk²; positive norms scale byk, so normalized cosine cancels.
    image_cosine=S.cancel((k*k*q*a*b)/((k*a)*(k*b)))
    original_cosine=q;side_ratio=S.cancel(k*a/a)
    if S.cancel((k*a+k*b)/(a+b))-k!=0:raise ValueError('common perimeter scale failed')
    metrics={'image_cosine':image_cosine,'original_cosine':original_cosine,'negative_original_cosine':-q,'side_ratio':side_ratio,'perimeter_ratio':k,'scale':k,'one':S.Integer(1)}
    triangle=points(spec['counterexample_triangle']);scale=math(spec['counterexample_scale'])
    if len(triangle)!=3 or scale.is_positive is not True:raise ValueError('positive nondegenerate similarity witness required')
    u,v=triangle[1]-triangle[0],triangle[2]-triangle[0]
    cosine=S.simplify(u.dot(v)/S.sqrt(u.dot(u)*v.dot(v)));witness={k:scale,q:cosine}
    def check(o):
        results=[]
        for relation in o['relations']:
            if relation['op']!='=' or relation['left'] not in metrics or relation['right'] not in metrics:raise ValueError('unsupported metric relation')
            difference=S.simplify(metrics[relation['left']]-metrics[relation['right']])
            if difference==0:results.append(True)
            elif S.simplify(difference.subs(witness)).is_zero is False:results.append(False)
            else:raise ValueError('physical similarity witness does not refute the universal relation')
        if not results:raise ValueError('no metric assertions')
        return all(results)
    return select_unique(spec['options'],check)


def _ray_family(kind,height):
    # All targets(u,v,0) on the projection plane, rather than a sampled pair
    # or a single two-dimensional cross-section of a spatial light field.
    u,v,w,z,x,y,k=S.symbols('u v w z x y k',real=True)
    if kind=='fixed_direction':
        origin=S.Matrix([u,v,0]);direction=S.Matrix([0,0,-1]);other=direction
    elif kind=='point_source':
        origin=S.Matrix([0,0,height]);direction=S.Matrix([u,v,-height]);other=S.Matrix([w,z,-height])
    else:raise ValueError('unknown ray parametrization')
    crossed=direction.cross(other)
    parallel=all(S.expand(component)==0 for component in crossed)
    if not parallel:
        if not any(S.simplify(component.subs({u:0,v:0,w:1,z:0})).is_zero is False for component in crossed):raise ValueError('nonparallel rays need a valid pair')
    incidence=(S.Matrix([x,y,k])-origin).cross(direction)
    coefficients=[]
    for expression in incidence:coefficients+=S.Poly(S.expand(expression),u,v).coeffs()
    solution=S.linsolve(coefficients,[x,y,k])
    if solution is S.EmptySet:concurrent=False
    elif len(solution)==1 and all(not value.free_symbols-{height} for value in next(iter(solution))):concurrent=True
    else:raise ValueError('common-ray locus unresolved')
    return {'parallel':parallel,'concurrent':concurrent}


def ray_family_properties(spec):
    h=S.Symbol('h',positive=True)
    families={name:_ray_family(kind,h) for name,kind in spec['families'].items()}
    def check(o):
        results=[]
        for relation in o['properties']:
            if relation['family'] not in families or relation['property'] not in ('parallel','concurrent'):raise ValueError('unknown ray property')
            results.append(families[relation['family']][relation['property']])
        if not results:raise ValueError('empty ray claim')
        return all(results)
    return select_unique(spec['options'],check)


def parallel_light_fields(spec):
    h=S.Symbol('h',positive=True)
    return select_unique(spec['options'],lambda o:_ray_family(o['ray_field'],h)['parallel'])


def symmetric_game_conditions(spec):
    assumptions={'r':'positive','l':'positive'}
    payoffs=[[math(value,assumptions) for value in row] for row in spec['payoffs']]
    if len(payoffs)!=2 or any(len(row)!=3 for row in payoffs):raise ValueError('two players and three outcomes required')
    p=S.Symbol('p',real=True);q=S.Symbol('q',real=True);probabilities=[p,q,1-p-q]
    difference=S.expand(sum(prob*(a-b) for prob,a,b in zip(probabilities,*payoffs)))
    polynomial=S.Poly(difference,p,q);coefficient=polynomial.coeff_monomial(p)
    if coefficient.is_positive is not True or S.simplify(difference-coefficient*(p-q))!=0:raise ValueError('symmetric positive gain/loss fairness unproved')
    fairness={'left':str(S.cancel(difference/coefficient)),'op':'=','right':'0'}
    base=[{'left':'p','op':'>=','right':'0'},{'left':'q','op':'>=','right':'0'},{'left':'1-p-q','op':'>=','right':'0'}, {'left':'n','op':'>','right':'0'},{'left':'m','op':'>','right':'0'},fairness]
    def check(o):
        conclusions=o['conclusions']
        if not conclusions:raise ValueError('missing necessary condition')
        results=[implies(base,claim) for claim in conclusions]
        if all(results):return True
        witness=o.get('counterexample')
        if not isinstance(witness,dict) or set(witness)!=set('pqnm'):raise ValueError('complete probability/count counterexample required')
        values={name:number(value) for name,value in witness.items()}
        if values['n'].denominator!=1 or values['m'].denominator!=1:raise ValueError('participant counts must be integers')
        def holds(r):
            left,right=r['left'],r['right']
            for key,value in values.items():
                left=left.replace(key,'('+str(value)+')');right=right.replace(key,'('+str(value)+')')
            return compare(number(left),r['op'],number(right))
        if not all(holds(r) for r in base) or all(holds(r) for r in conclusions):raise ValueError('counterexample does not refute necessity')
        return False
    return select_unique(spec['options'],check)


def lottery_inclusion(spec):
    if spec.get('mechanism')!='uniform_fixed_size_subsets' or spec.get('sample_range')!='1<=k<=n':raise ValueError('simple random without-replacement domain missing')
    n,k=S.symbols('n k',integer=True,positive=True)
    probability=S.combsimp(S.binomial(n-1,k-1)/S.binomial(n,k))
    if S.simplify(probability-k/n)!=0:raise ValueError('combinatorial inclusion identity failed')
    # Choosing a specific labelled member leaves k-1 of the other n-1 labels;
    # no label occurs in the final expression. Formula also holds at k=n.
    def check(o):
        if o['op'] not in ('=','!=') or o['quantifier'] not in ('all_labels','some_ordered_labels'):raise ValueError('unknown label comparison')
        difference=S.simplify(probability-probability)
        return zero(difference) if o['op']=='=' else not zero(difference)
    return select_unique(spec['options'],check)


def _uniform_from_constraints(option):
    count=option['outcomes']
    if type(count) is not int or not 1<=count<=12:raise ValueError('bounded finite sample space required')
    parents=list(range(count))
    def find(i):
        while parents[i]!=i:i=parents[i]
        return i
    pairs=option.get('equal_mass_pairs',[])
    for i,j in pairs:
        if type(i) is not int or type(j) is not int or not 0<=i<count or not 0<=j<count:raise ValueError('invalid probability equality')
        parents[find(i)]=find(j)
    if len({find(i) for i in range(count)})==1:return True
    witness=[math(value) for value in option.get('counterexample',[])]
    if len(witness)!=count or any(value.is_nonnegative is not True for value in witness) or not zero(sum(witness)-1):raise ValueError('normalized nonnegative probability witness required')
    if any(not zero(witness[i]-witness[j]) for i,j in pairs):raise ValueError('witness violates known equal masses')
    if all(zero(value-witness[0]) for value in witness[1:]):raise ValueError('witness is uniform, not a countermodel')
    return False


def uniformity_guarantees(spec):return select_unique(spec['options'],_uniform_from_constraints)


def classical_sample_spaces(spec):
    def check(o):
        if o.get('sample_space')=='positive_integers':
            # Countably many equal positive masses have unbounded partial sums;
            # equal zero masses have total0. Neither is a probability law.
            n=S.Symbol('n',integer=True,positive=True);p=S.Symbol('p',positive=True)
            if S.limit(n*p,n,S.oo)!=S.oo:raise ValueError('infinite equal-mass obstruction unproved')
            return False
        if o.get('sample_space')!='finite':raise ValueError('unknown sample space')
        return _uniform_from_constraints(o)
    return select_unique(spec['options'],check)


def replacement_protocols(spec):
    if spec.get('allowed_actions')!=['draw','return_same_ball'] or spec.get('population_lower_bound')!=2:raise ValueError('closed same-urn protocol required')
    def check(o):
        possible=[]
        for returned in o['possible_returns_between_draws']:
            if type(returned) is not int or returned not in (0,1):raise ValueError('only one previously drawn ball can return')
            before_first=0;before_second=-1+returned # offsets from arbitrary N>=2
            if o.get('equal_pre_draw_counts') and before_second!=before_first:continue
            possible.append(returned)
        if not possible:raise ValueError('inconsistent urn observations')
        # A simultaneous two-ball draw has exactly the distinct no-return
        # ordered outcomes; its supplied action expansion therefore has r=0.
        if o.get('simultaneous_draw_size') not in (None,2):raise ValueError('only two-ball expansion supported')
        if o.get('simultaneous_draw_size')==2 and possible!=[0]:raise ValueError('simultaneous distinct draw cannot restore an intermediate ball')
        if set(possible)=={0}:return True
        if set(possible)=={1}:return False
        raise ValueError('whether a ball is returned is not determined')
    return select_unique(spec['options'],check)


def precipitation_interpretations(spec):
    probability=math(spec['event_probability'])
    if probability.is_nonnegative is not True or S.simplify(1-probability).is_nonnegative is not True:raise ValueError('valid probability required')
    def check(o):
        if o['claim']=='probability_bounds':
            lower,upper=math(o['lower']),math(o['upper'])
            low=S.simplify(probability-lower).is_positive;high=S.simplify(upper-probability).is_positive
            if low is None or high is None:raise ValueError('probability comparison unresolved')
            return bool(low and high)
        if o['claim']=='certain_event':return zero(probability-1)
        if o['claim']!='fixed_realized_fraction':raise ValueError('unknown probability interpretation')
        target=math(o['fraction']);rain,dry=[math(v) for v in o['counterexample_fractions']]
        if any(v.is_nonnegative is not True or S.simplify(1-v).is_nonnegative is not True for v in [target,rain,dry]):raise ValueError('fractions outside[0,1]')
        if rain.is_positive is not True or dry!=0 or not(0<probability<1):raise ValueError('rain/dry countermodel inconsistent')
        # Two outcomes have masses p,1-p and event iff fraction>0.
        if zero(rain-target) and zero(dry-target):raise ValueError('fractions do not refute fixed realization')
        return False
    return select_unique(spec['options'],check)


HANDLERS={
 'app105_incenter_intersections':incenter_intersections,'app105_regular_polygon_metrics':regular_polygon_metrics,
 'app105_inscribed_angle_relations':inscribed_angle_relations,'app105_polygon_similarity_families':polygon_similarity_families,
 'app105_similarity_metrics':similarity_metrics,'app105_ray_family_properties':ray_family_properties,
 'app105_parallel_light_fields':parallel_light_fields,'app105_symmetric_game_conditions':symmetric_game_conditions,
 'app105_lottery_inclusion':lottery_inclusion,'app105_uniformity_guarantees':uniformity_guarantees,
 'app105_classical_sample_spaces':classical_sample_spaces,'app105_replacement_protocols':replacement_protocols,
 'app105_precipitation_interpretations':precipitation_interpretations,
}
