"""Independent Euclidean models for offline question verification.

No question ids or stored answers are read. Congruence uses the Euclidean
SSS/SAS/ASA/AAS/HL theorems; angle/side closure uses triangle angle sum and
isosceles equivalence. Quadrilateral implication uses the standard simple,
nondegenerate quadrilateral theorems; failure must have a checked rational
coordinate counterexample, never merely a missing inference. Candidate text is
returned only after every candidate has been evaluated and exactly one succeeds.
"""
from fractions import Fraction as F
from itertools import combinations
from exact_polynomial import _parse
from model_types import TextProof, select_unique


class UF:
    def __init__(self): self.p = {}
    def find(self, a):
        self.p.setdefault(a, a)
        if self.p[a] != a: self.p[a] = self.find(self.p[a])
        return self.p[a]
    def union(self, a, b): self.p[self.find(a)] = self.find(b)
    def equal(self, a, b): return self.find(a) == self.find(b)


def side(s):
    if len(s) != 2 or s[0] == s[1]: raise ValueError('invalid side')
    return ''.join(sorted(s))


def angle(s):
    if len(s) != 3 or len(set(s)) != 3: raise ValueError('invalid angle')
    ends = sorted((s[0], s[2]))
    return ends[0] + s[1] + ends[1]


def triangle(t):
    if len(t) != 3 or len(set(t)) != 3: raise ValueError('invalid triangle')
    return list(t)


def at(t, vertex):
    ends = [v for v in t if v != vertex]
    if len(ends) != 2: raise ValueError('angle vertex outside triangle')
    return angle(ends[0] + vertex + ends[1])


def _base(spec):
    s, a = UF(), UF()
    for x, y in spec.get('equal_sides', []): s.union(side(x), side(y))
    for x, y in spec.get('equal_angles', []): a.union(angle(x), angle(y))
    for center, x, y in spec.get('midpoints', []): s.union(side(center+x), side(center+y))
    return s, a


def criteria(spec):
    """Return all *direct* criteria, without silently deriving a third angle."""
    t, u = map(triangle, spec['triangles'])
    s, a = _base(spec)
    rights = {angle(x) for x in spec.get('right_angles', [])}
    if rights:
        first = next(iter(rights))
        for r in rights: a.union(first, r)
    se = {(i,j):s.equal(side(t[i]+t[j]),side(u[i]+u[j])) for i,j in combinations(range(3),2)}
    ae = {i:a.equal(at(t,t[i]),at(u,u[i])) for i in range(3)}
    out = set()
    if all(se.values()): out.add('SSS')
    for i in range(3):
        js = [j for j in range(3) if j != i]
        if ae[i] and all(se[tuple(sorted((i,j)))] for j in js): out.add('SAS')
    for i,j in combinations(range(3),2):
        if ae[i] and ae[j]:
            if se[i,j]: out.add('ASA')
            if any(v for edge,v in se.items() if edge != (i,j)): out.add('AAS')
    for i in range(3):
        if at(t,t[i]) in rights and at(u,u[i]) in rights:
            other = [j for j in range(3) if j != i]
            if se[tuple(other)] and any(se[tuple(sorted((i,j)))] for j in other): out.add('HL')
    return out


def congruence(spec):
    mode = spec.get('query', 'criterion')
    if mode == 'condition':
        def test(o):
            case = dict(spec)
            for field in ('equal_sides','equal_angles','right_angles'):
                case[field] = spec.get(field,[]) + o.get(field,[])
            found = criteria(case)
            return spec['required'] in found if spec.get('required') else bool(found)
        return select_unique(spec['options'], test)
    found = criteria(spec)
    if mode == 'criterion': return select_unique(spec['options'], lambda o:o['criterion'] in found)
    if mode == 'length' or mode == 'angle':
        if not found: raise ValueError('no congruence established')
        t,u = map(triangle,spec['triangles']); s,a = _base(spec)
        for i,j in combinations(range(3),2): s.union(side(t[i]+t[j]),side(u[i]+u[j]))
        for i in range(3): a.union(at(t,t[i]),at(u,u[i]))
        uf, canon = (s,side) if mode == 'length' else (a,angle)
        measured={canon(k):F(v) for k,v in spec['measurements'].items()}
        if any(v<=0 or (mode=='angle' and v>=180) for v in measured.values()):raise ValueError('invalid measurement')
        for x,y in combinations(measured,2):
            if uf.equal(x,y) and measured[x]!=measured[y]:raise ValueError('conflicting equal measurements')
        matches = [v for k,v in measured.items() if uf.equal(k,canon(spec['target']))]
        if not matches or len(set(matches)) != 1: raise ValueError('missing or conflicting measurement')
        return matches[0]
    raise ValueError('unknown congruence query')


def correspondence(spec):
    source,target = map(triangle,spec['triangles'])
    if spec.get('pairs'):
        mapping = dict(spec['pairs'])
        if set(mapping) != set(source) or set(mapping.values()) != set(target): raise ValueError('not a bijection')
    else: mapping = dict(zip(source,target))
    result = ''.join(mapping[v] for v in spec['entity'])
    kind = spec.get('entity_kind','vertex')
    if kind == 'side': result = side(result)
    if spec.get('options'):
        return select_unique(spec['options'],lambda o: (side(o['entity']) if kind=='side' else o['entity']) == result)
    return TextProof(result, 'word')


def triangle_closure(spec):
    triangles = [triangle(t) for t in spec['triangles']]
    s,a = _base(spec)
    values = {angle(k):F(v) for k,v in spec.get('angle_values',{}).items()}
    for key in spec.get('right_angles',[]): values[angle(key)] = F(90)
    for _ in range(12):
        before = (dict(s.p),dict(a.p),dict(values))
        for t in triangles:
            for i,j in combinations(range(3),2):
                ai,aj=at(t,t[i]),at(t,t[j]); si=side(''.join(v for v in t if v!=t[i])); sj=side(''.join(v for v in t if v!=t[j]))
                if s.equal(si,sj): a.union(ai,aj)
                if a.equal(ai,aj): s.union(si,sj)
            known = {i:values[at(t,v)] for i,v in enumerate(t) if at(t,v) in values}
            if len(known)==2:
                missing=next(i for i in range(3) if i not in known); values[at(t,t[missing])] = 180-sum(known.values())
            if len(known)==3 and sum(known.values())!=180: raise ValueError('inconsistent triangle angles')
        # Numerically equal measured/derived angles also entail equal sides.
        for x,y in combinations(list(values),2):
            if values[x]==values[y]:a.union(x,y)
        for x,v in list(values.items()):
            if not 0<v<180: raise ValueError('nonpositive triangle angle')
            for y in a.p:
                if a.equal(x,y):
                    if y in values and values[y]!=v: raise ValueError('conflicting equal angles')
                    values[y]=v
        if before == (s.p,a.p,values): break
    query = spec['query']
    if query=='length':
        matches=[F(v) for k,v in spec['length_values'].items() if s.equal(side(k),side(spec['target']))]
        if not matches or len(set(matches))!=1: raise ValueError('length not entailed')
        return matches[0]
    if query=='angle':
        if angle(spec['target']) not in values: raise ValueError('angle not entailed')
        return values[angle(spec['target'])]
    if query=='equality':
        def test(o):
            equalities=o['equalities']
            uf,canon=(s,side) if o['entity_kind']=='side' else (a,angle)
            return all(uf.equal(canon(x),canon(y)) for x,y in equalities)
        return select_unique(spec['options'],test)
    if query=='classification':
        t=triangles[0]; av=[values.get(at(t,v)) for v in t]
        if any(v is None for v in av): raise ValueError('need all angles')
        result='直角三角形' if max(av)==90 else '钝角三角形' if max(av)>90 else '锐角三角形'
        return TextProof(result,'word')
    raise ValueError('unknown triangle query')


def equal_length(spec):
    s,_=_base(spec)
    found=[F(v) for k,v in spec['length_values'].items() if s.equal(side(k),side(spec['target']))]
    if not found or len(set(found))!=1: raise ValueError('length equality not established')
    return found[0]


def reflection(spec):
    axis=spec['axis']
    if axis not in ('x','y','origin'): raise ValueError('unknown reflection')
    p=list(spec.get('point',spec.get('signs',[])))
    if len(p)!=2: raise ValueError('two coordinates required')
    result=[F(v) for v in p]
    if axis in ('y','origin'): result[0]=-result[0]
    if axis in ('x','origin'): result[1]=-result[1]
    if 'signs' in spec:
        if any(v not in (-1,1) for v in result): raise ValueError('quadrant excludes axes')
        return select_unique(spec['options'],lambda o:o['signs']==list(map(int,result)))
    return select_unique(spec['options'],lambda o:list(map(F,o['point']))==result)


def altitude_positions(spec):
    """Projection onto BC lies inside iff both endpoint angles are acute.

    Signs are signs of each vertex cosine, not a stored altitude location:
    acute=1, right=0, obtuse=-1. Two obtuse/right angles are impossible.
    """
    signs=spec['cosine_signs']
    if len(signs)!=3 or any(v not in (-1,0,1) for v in signs) or sum(v<=0 for v in signs)>1: raise ValueError('invalid triangle angle signs')
    positions=[]
    for i in range(3):
        other=[signs[j] for j in range(3) if j!=i]
        positions.append('outside' if -1 in other else 'boundary' if 0 in other else 'inside')
    if spec['query']=='orthocenter':
        # With B=(0,0), C=(1,0), A=(u,v), v>0,
        # H=(u,u*(1-u)/v); barycentric coordinates change sign exactly
        # when a vertex cosine becomes negative. A right angle gives H
        # at that vertex. This proves the classification for all shapes.
        location='outside' if -1 in signs else 'vertex' if 0 in signs else 'inside'
        return select_unique(spec['options'],lambda o:o['location']==location)
    if spec['query']=='boundary_count': return positions.count('boundary')
    return select_unique(spec['options'],lambda o:(positions.count('outside')==o['outside_count']) if 'outside_count' in o else o['positions']==positions)


def symbolic_isometry_count(spec):
    """Count reflection permutations of a convex cyclically listed polygon.

    Exact complete squared distances certify an isometry. For a noncollinear
    convex polygon, order-reversing distance-preserving permutations are plane
    reflections (a finite set cannot admit a glide reflection). No floating
    points or sample coordinates are used; symbolic equalities are exact.
    """
    n=spec['vertices']; ds={tuple(sorted(map(int,k.split(',')))):_parse(v) for k,v in spec['squared_distances'].items()}
    if set(ds)!=set(combinations(range(n),2)): raise ValueError('incomplete distance matrix')
    count=0
    for shift in range(n):
        perm=[(shift-i)%n for i in range(n)]
        if all(ds[(i,j)]==ds[tuple(sorted((perm[i],perm[j])))] for i,j in combinations(range(n),2)): count+=1
    return count


# Closure theorem assumptions: a simple nondegenerate quadrilateral ABCD in
# cyclic order. Opposite-side equality criterion is the standard SSS proof;
# diagonal equal/perpendicular criteria require an established parallelogram.
RULES=[
 ({'parallel_ab_cd','parallel_ad_bc'},'parallelogram'),
 ({'equal_ab_cd','equal_ad_bc'},'parallelogram'),
 ({'parallel_ab_cd','equal_ab_cd'},'parallelogram'),
 ({'parallel_ad_bc','equal_ad_bc'},'parallelogram'),
 ({'diagonals_bisect'},'parallelogram'),
 ({'three_right_angles'},'rectangle'),({'all_angles_equal'},'rectangle'),
 ({'all_sides_equal'},'rhombus'),
 ({'rectangle'},'parallelogram'),({'rhombus'},'parallelogram'),
 ({'parallelogram'},'parallel_ab_cd'),({'parallelogram'},'parallel_ad_bc'),
 ({'parallelogram'},'equal_ab_cd'),({'parallelogram'},'equal_ad_bc'),
 ({'parallelogram'},'opposite_angles_equal'),({'parallelogram'},'diagonals_bisect'),
 ({'parallelogram','diagonals_equal'},'rectangle'),
 ({'parallelogram','right_angle'},'rectangle'),
 ({'rectangle'},'all_angles_equal'),({'rectangle'},'right_angle'),({'rectangle'},'three_right_angles'),
 ({'rectangle'},'diagonals_equal'),
 ({'parallelogram','diagonals_perpendicular'},'rhombus'),
 ({'parallelogram','equal_ab_bc'},'rhombus'),
 ({'rhombus'},'all_sides_equal'),({'rhombus'},'equal_ab_bc'),
 ({'rhombus'},'diagonals_perpendicular'),
 ({'rectangle','rhombus'},'square'),
 ({'square'},'rectangle'),({'square'},'rhombus'),
]


def close_facts(given):
    facts=set(given)
    unknown=facts-{atom for lhs,rhs in RULES for atom in lhs|{rhs}}
    if unknown: raise ValueError('unknown quadrilateral condition: '+repr(unknown))
    while True:
        before=set(facts)
        for lhs,rhs in RULES:
            if lhs<=facts: facts.add(rhs)
        if facts==before: return facts


def coordinate_facts(points):
    if len(points)!=4: raise ValueError('need four points')
    p=[tuple(map(F,v)) for v in points]
    def sub(a,b): return (a[0]-b[0],a[1]-b[1])
    def dot(a,b):return a[0]*b[0]+a[1]*b[1]
    def cross(a,b):return a[0]*b[1]-a[1]*b[0]
    edges=[sub(p[(i+1)%4],p[i]) for i in range(4)]
    turns=[cross(edges[i],edges[(i+1)%4]) for i in range(4)]
    if not(all(t>0 for t in turns) or all(t<0 for t in turns)): raise ValueError('counterexample must be strictly convex')
    lengths=[dot(e,e) for e in edges];ac=sub(p[2],p[0]);bd=sub(p[3],p[1]);facts=set()
    def add(name,cond):
        if cond:facts.add(name)
    add('parallel_ab_cd',cross(edges[0],edges[2])==0);add('parallel_ad_bc',cross(edges[1],edges[3])==0)
    add('equal_ab_cd',lengths[0]==lengths[2]);add('equal_ad_bc',lengths[1]==lengths[3]);add('equal_ab_bc',lengths[0]==lengths[1])
    add('all_sides_equal',len(set(lengths))==1)
    add('diagonals_bisect',tuple(p[0][i]+p[2][i] for i in range(2))==tuple(p[1][i]+p[3][i] for i in range(2)))
    add('diagonals_equal',dot(ac,ac)==dot(bd,bd));add('diagonals_perpendicular',dot(ac,bd)==0)
    rights=[dot(edges[i],edges[(i+1)%4])==0 for i in range(4)]
    add('right_angle',any(rights));add('three_right_angles',sum(rights)>=3)
    para='parallel_ab_cd' in facts and 'parallel_ad_bc' in facts
    add('parallelogram',para);add('opposite_angles_equal',para)
    add('exclusive_isosceles_trapezoid',('parallel_ab_cd' in facts) != ('parallel_ad_bc' in facts) and (lengths[1]==lengths[3] if 'parallel_ab_cd' in facts else lengths[0]==lengths[2]))
    add('all_angles_equal',all(rights));add('rectangle',all(rights));add('rhombus',len(set(lengths))==1);add('square',all(rights) and len(set(lengths))==1)
    return facts


def quadrilateral(spec):
    base=spec.get('given',[]); mode=spec.get('query','implies')
    def test(o):
        given=base+o.get('given',[]); target=o.get('target',spec.get('target'))
        targets=target if isinstance(target,list) else [target]
        universe={atom for lhs,rhs in RULES for atom in lhs|{rhs}}|{'exclusive_isosceles_trapezoid'}
        if not targets or any(t not in universe for t in targets):raise ValueError('unknown target property')
        positive=all(t in close_facts(given) for t in targets)
        if not positive:
            coords=o.get('counterexample')
            if coords is None:raise ValueError('unproved nonimplication needs checked counterexample')
            facts=coordinate_facts(coords)
            if not set(given)<=facts or all(t in facts for t in targets):raise ValueError('invalid counterexample')
        return not positive if mode=='not_implies' else positive
    return select_unique(spec['options'],test)


def diagonal_transport(spec):
    facts=close_facts(spec['given'])
    if 'diagonals_equal' not in facts:raise ValueError('diagonal equality not proved')
    value=F(spec['known_diagonal'])
    if value<=0:raise ValueError('positive diagonal required')
    return value


HANDLERS={
 'geometry_congruence':congruence,'geometry_correspondence':correspondence,
 'geometry_triangle':triangle_closure,'geometry_equal_length':equal_length,
 'geometry_reflection':reflection,'geometry_altitudes':altitude_positions,
 'geometry_symmetry_axes':symbolic_isometry_count,
 'geometry_quadrilateral':quadrilateral,'geometry_diagonal':diagonal_transport,
}


def affine_model(spec):
    """Exact symbolic affine/determinant computation, no sampled coordinates.

    Free coordinate variables stand for arbitrary nondegenerate Euclidean
    configurations. Equal-area results compare signed area squares. Median and
    centroid constructions use affine definitions; incenter uses the standard
    positive side-length barycentric formula, justified by area/distance ratios.
    """
    import sympy as S
    xs={v:S.Symbol(v,positive=True) for v in spec.get('positive',[])}
    def expr(x):return S.sympify(str(x),locals=xs)
    def vec(v):return S.Matrix([expr(x) for x in v])
    points={k:vec(v) for k,v in spec.get('points',{}).items()}
    for item in spec.get('constructions',[]):
        weights=[expr(x) for x in item['weights']]
        if len(weights)!=len(item['points']) or S.simplify(sum(weights))==0:raise ValueError('invalid affine combination')
        points[item['name']]=sum((w*points[p] for w,p in zip(weights,item['points'])),S.zeros(2,1))/sum(weights)
    query=spec['query']
    if query=='area_relation':
        def area(t):
            a,b,c=[points[p] for p in t];return S.det(S.Matrix.hstack(b-a,c-a))/2
        ratio=S.factor(area(spec['triangles'][0])**2-area(spec['triangles'][1])**2)
        if ratio!=0:raise ValueError('area equality not identically established')
        return select_unique(spec['options'],lambda o:o['comparison']=='equal')
    if query=='centroid_trace':
        a,b,c=[points[p] for p in spec['triangle']]
        g=(a+b+c)/3
        t,l=S.symbols('t l')
        solutions=S.solve(list(a+l*(g-a)-(b+t*(c-b))),(t,l),dict=True)
        if len(solutions)!=1:raise ValueError('centroid median not uniquely established')
        value=S.simplify(solutions[0][t])
        return select_unique(spec['options'],lambda o:any(S.simplify(expr(p)-value)==0 for p in o.get('parameters',[o.get('parameter')])) )
    if query=='barycentric_location':
        # Incenter weights are opposing side lengths: all strictly positive.
        if spec.get('center')!='incenter':raise ValueError('unsupported barycentric center')
        weights=[expr(v) for v in spec['side_lengths']]
        if len(weights)!=3 or not all(w.is_positive for w in weights):raise ValueError('positive sides required')
        normalized=[S.factor(w/sum(weights)) for w in weights]
        if not all(w.is_positive for w in normalized):raise ValueError('cannot prove interior')
        return select_unique(spec['options'],lambda o:o['location']=='inside')
    if query=='centroid_concurrence':
        a,b,c=[points[p] for p in spec['triangle']];g=(a+b+c)/3
        def test(o):
            if o['construction']=='medians':
                return all(S.simplify(S.det(S.Matrix.hstack(g-v,(w+x)/2-v)))==0 for v,w,x in ((a,b,c),(b,c,a),(c,a,b)))
            # Altitudes, angle bisectors, perpendicular bisectors are not all
            # centroid lines: a rational scalene counterexample is verified.
            ex=[S.Matrix(v) for v in o['counterexample']];u,v,w=ex;cent=(u+v+w)/3
            if o['construction']=='altitudes':return all(S.simplify((cent-x).dot(z-y))==0 for x,y,z in ((u,v,w),(v,w,u),(w,u,v)))
            if o['construction']=='perpendicular_bisectors':return all(S.simplify((cent-x).dot(cent-x)-(cent-y).dot(cent-y))==0 for x,y in ((u,v),(v,w)))
            if o['construction']=='angle_bisectors':
                def distancesq(p,x,y):return S.det(S.Matrix.hstack(p-x,y-x))**2/(y-x).dot(y-x)
                return all(S.simplify(distancesq(cent,x,y)-distancesq(cent,x,z))==0 for x,y,z in ((u,v,w),(v,w,u),(w,u,v)))
            raise ValueError('unsupported line construction')
        return select_unique(spec['options'],test)
    raise ValueError('unsupported affine query')


def triangle_ratio(spec):
    """Law of sines with exact trig values, triangle sum and equal-side facts."""
    import sympy as S
    angles={k:S.Rational(v) for k,v in spec['angles'].items()}
    if len(angles)==2:angles[next(v for v in spec['triangle'] if v not in angles)]=180-sum(angles.values())
    if set(angles)!=set(spec['triangle']) or sum(angles.values())!=180 or any(v<=0 for v in angles.values()):raise ValueError('invalid triangle angles')
    def squared_relative(edge):
        vertex=next(v for v in spec['triangle'] if v not in edge)
        return S.simplify(S.sin(angles[vertex]*S.pi/180)**2)
    def test(o):
        left,right=o['sides'];factor=S.Rational(o['factor'])
        # lengths are positive, so equality of squares and positive multiplier
        # implies the unsquared length relation.
        return factor>0 and S.simplify(squared_relative(left)-factor**2*squared_relative(right))==0
    return select_unique(spec['options'],test)


HANDLERS.update({'geometry_affine':affine_model,'geometry_triangle_ratio':triangle_ratio})


def formula_quantities(spec):
    """Classify changing symbols vs fixed numerical parameters in a formula.

    A symbol explicitly fixed by the physical setup is removed; otherwise all
    free symbols in the relation can vary. Mathematical constants pi/e are
    SymPy constants, not variable names. This checks algebraic classification,
    not the natural-language assignment of the model's dependent quantity.
    """
    import sympy as S
    symbols={v:S.Symbol(v,real=True) for v in spec['symbols']}
    expression=S.sympify(spec['relation'],locals=symbols)
    fixed={symbols[k]:S.sympify(str(v)) for k,v in spec.get('fixed',{}).items()}
    substituted=expression.subs(fixed)
    changing=substituted.free_symbols
    constants=set()
    for term in S.Add.make_args(S.expand(substituted)):
        coefficient=term.as_independent(*changing)[0]
        if coefficient!=0 and S.Abs(coefficient)!=1:constants.add(S.Abs(coefficient))
    if spec['query']=='count': return len(changing)
    def parsed(values):return {S.sympify(str(v),locals=symbols) for v in values}
    def test(o):
        if spec['query']=='variables':return parsed(o['quantities'])==changing
        if spec['query']=='constants':
            # Options may contain composite constants, such as 2*pi. Each
            # expression is constant iff it contains no unfixed free symbol.
            return bool(o['quantities']) and all(not (p.free_symbols & changing) and S.Abs(p) in constants for p in parsed(o['quantities']))
        if spec['query']=='classification':
            return parsed(o['variables'])==changing and all(not(p.free_symbols & changing) and S.Abs(p) in constants for p in parsed(o['constants']))
        raise ValueError('unknown quantity query')
    return select_unique(spec['options'],test)


def relation_is_function(relation,variable,dependent,witness=None):
    """Prove linear-in-output uniqueness, or refute by exact real roots.

    This deliberately refuses unproved nonlinear uniqueness. Domains are the
    natural real domains of the supplied relation; division by an expression
    independent of the output does not invalidate uniqueness on that domain.
    """
    import sympy as S
    x,y=S.symbols(variable+' '+dependent,real=True)
    expr=S.sympify(relation,locals={variable:x,dependent:y})
    numerator,denominator=S.together(expr).as_numer_denom()
    if not denominator.has(y):
        try:
            p=S.Poly(numerator,y)
            if p.degree()==1:
                coefficient=p.coeff_monomial(y)
                if not coefficient.free_symbols and coefficient!=0:return True
                zeros=S.solveset(coefficient,x,domain=S.S.Reals)
                excluded=S.solveset(denominator,x,domain=S.S.Reals)
                if zeros-excluded is S.EmptySet:return True
        except S.PolynomialError:pass
    if witness is not None:
        value=S.sympify(str(witness))
        roots=S.solveset(expr.subs(x,value),y,domain=S.S.Reals)
        if isinstance(roots,S.FiniteSet):
            valid=[v for v in roots if S.simplify(denominator.subs({x:value,y:v}))!=0 and S.simplify(expr.subs({x:value,y:v}))==0]
            if len(valid)>=2:return False
    raise ValueError('single-valuedness not proved or refuted')


def function_relation(spec):
    x=spec.get('variable','x');y=spec.get('dependent','y')
    query=spec['query']
    if query=='count':
        return sum(relation_is_function(r['relation'],x,y,r.get('witness')) for r in spec['relations'])
    if query=='select':
        return select_unique(spec['options'],lambda o:relation_is_function(o['relation'],x,y,o.get('witness')))
    if query=='explanation':
        result=relation_is_function(spec['relation'],x,y,spec.get('witness'))
        # A non-unique real-output witness invalidates existence-only and
        # combined±formula arguments. Validity is checked against a proof
        # obligation, not a supplied true/false label.
        return select_unique(spec['options'],lambda o:(not result and o['argument']=='multiple_outputs') or (result and o['argument']=='unique_output'))
    if query=='table':
        outputs={}
        for a,b in spec['pairs']:outputs.setdefault(F(a),set()).add(F(b))
        collisions={a for a,bs in outputs.items() if len(bs)>1}
        def test(o):
            argument=o['argument']
            if argument=='collision':return bool(collisions) and F(o['input']) in collisions
            if argument=='unique_output':return not collisions
            if argument in ('exists_only','increasing_only','undetermined'):return False
            raise ValueError('unknown function argument')
        return select_unique(spec['options'],test)
    raise ValueError('unknown function query')


HANDLERS.update({'formula_quantities':formula_quantities,'function_relation':function_relation})


def circle_intersections(spec):
    """Equal radius r, center distance d>0: y²=r²-d²/4.

    Two distinct intersections require positive y², i.e. normalized r/d>1/2.
    Candidate intervals are solved symbolically and intersected with r/d>0.
    """
    import sympy as S
    t=S.Symbol('t',real=True)
    actual=S.solve_univariate_inequality(t**2-S.Rational(1,4)>0,t,relational=False).intersect(S.Interval.open(0,S.oo))
    def test(o):
        condition=S.sympify(o['condition'],locals={'t':t},evaluate=False)
        candidate=S.solve_univariate_inequality(condition,t,relational=False).intersect(S.Interval.open(0,S.oo))
        return candidate==actual
    return select_unique(spec['options'],test)


def linear_identity(spec):
    """Prove all candidate affine identities under exact linear constraints."""
    import sympy as S
    variables={v:S.Symbol(v,real=True) for v in spec['variables']}
    parse=lambda e:S.sympify(str(e),locals=variables)
    equations=[parse(e) for e in spec['constraints']]
    solutions=S.linsolve(equations,list(variables.values()))
    if solutions is S.EmptySet or len(solutions)!=1:raise ValueError('inconsistent linear assumptions')
    solution=next(iter(solutions));sub=dict(zip(variables.values(),solution))
    source=parse(spec['source'])
    return select_unique(spec['options'],lambda o:S.simplify((source-parse(o['expression'])).subs(sub,simultaneous=True))==0)


def polygon_model(spec):
    """Convex fan recurrence: adding one vertex adds one fan triangle.

    T(3)=1 and T(n+1)=T(n)+1 determine the affine count uniquely. Exterior sum
    follows from n straight angles minus T(n) triangle-angle sums. Conditions
    of convexity and one consistently directed exterior per vertex are required.
    """
    import sympy as S
    if not spec.get('convex'):raise ValueError('convex polygon required')
    n=S.Symbol('n',integer=True,positive=True)
    T=S.Function('T')
    count=S.rsolve(T(n+1)-T(n)-1,T(n),{T(3):1})
    if spec['query']=='fan_triangles':source=count
    elif spec['query']=='exterior_sum':source=180*n-180*count
    else:raise ValueError('unsupported polygon query')
    return select_unique(spec['options'],lambda o:(S.simplify(S.diff(source,n))!=0) if o.get('depends_on')=='n' else S.simplify(source-S.sympify(o['expression'],locals={'n':n}))==0)


def triangle_square_model(spec):
    """Classify a triangle by exact signs of cosine-law numerators.

    Squared sides may be symbolic positive parameters; a right/obtuse/acute
    classification is returned only when every required sign is proved by
    exact symbolic arithmetic. No sample triangles establish universal claims.
    """
    import sympy as S
    symbols={v:S.Symbol(v,positive=True) for v in spec.get('positive',[])}
    values=[S.sympify(e,locals=symbols) for e in spec['squared_sides']]
    if len(values)!=3 or not all(v.is_positive for v in values):raise ValueError('positive squared sides needed')
    normal=lambda value:S.factor(value)
    if spec.get('constraint'):
        # Reduce all cosine/area polynomials modulo the original relation;
        # do not put a solved Pythagorean conclusion into the model inputs.
        variables=[symbols[v] for v in spec['variable_order']]
        constraint=S.sympify(spec['constraint'],locals=symbols)
        basis=S.groebner([constraint],*variables)
        normal=lambda value:S.factor(basis.reduce(S.expand(value))[1])
    # Heron's polynomial is 16*area². With positive side squares its
    # strict positivity excludes both degenerate and impossible triangles.
    heron=normal(2*sum(values[i]*values[j] for i,j in combinations(range(3),2))-sum(v**2 for v in values))
    if heron.is_positive is not True:raise ValueError('nondegenerate triangle not established')
    numerators=[normal(sum(values)-2*v) for v in values]
    if any(v==0 for v in numerators):kind='right'
    elif any(v.is_negative for v in numerators):kind='obtuse'
    elif all(v.is_positive for v in numerators):kind='acute'
    else:raise ValueError('angle sign undetermined')
    if spec.get('query')=='explanation':
        def test(o):
            if o['conclusion']!=kind:return False
            if o['argument']=='pythagoras':
                hyp=o['hypotenuse'];legs=[v for i,v in enumerate(values) if i!=hyp]
                return S.simplify(sum(legs)-values[hyp])==0 and all(S.simplify(values[hyp]-v).is_positive for v in legs)
            if o['argument']=='sum_lengths':
                lhs=sum(S.sqrt(v) for i,v in enumerate(values) if i!=o['hypotenuse'])
                return S.simplify(lhs-S.sqrt(values[o['hypotenuse']]))==0
            # Triangle inequality is necessary for any triangle, and cannot
            # establish a right angle; an incorrect-hypotenuse calculation
            # does not refute all right-angle possibilities.
            return False
        return select_unique(spec['options'],test)
    return select_unique(spec['options'],lambda o:o['classification']==kind)


def reflected_path(spec):
    """Reflection isometry + triangle inequality, with exact attainability.

    A=(u,a), B=(v,b), a,b>0, reflect A'=(u,-a). The intersection parameter
    t=a/(a+b) lies strictly in (0,1), proving equality can actually occur.
    """
    import sympy as S
    a,b=S.symbols('a b',positive=True);u,v=S.symbols('u v',real=True)
    t=a/(a+b)
    if t.is_positive is not True or S.simplify(1-t).is_positive is not True:raise ValueError('crossing not attained')
    if spec['query']=='minimum':
        distance=F(spec['reflected_distance'])
        if distance<=0:raise ValueError('positive reflected distance required')
        return distance
    x=S.factor((1-t)*u+t*v)
    return select_unique(spec['options'],lambda o:S.simplify(S.sympify(o['point_x'],locals={'a':a,'b':b,'u':u,'v':v})-x)==0)


def angle_implication(spec):
    """All valid triangle angle assignments are represented by a linear set.

    Side equalities imply opposite angle equalities. Entailment is equality
    after exact elimination. Failed implications additionally require a checked
    positive 180-degree counterexample, to exclude vacuous/non-triangle cases.
    """
    import sympy as S
    variables=S.symbols('a b c',real=True);lookup=dict(zip('ABC',variables))
    def equations(case):
        out=[sum(variables)-180]
        for x,y in case.get('equal_angles',[]):out.append(lookup[x]-lookup[y])
        for x,y in case.get('equal_sides',[]):
            vx=next(v for v in 'ABC' if v not in x);vy=next(v for v in 'ABC' if v not in y);out.append(lookup[vx]-lookup[vy])
        out += [lookup[k]-S.Rational(v) for k,v in case.get('angle_values',{}).items()]
        return out
    def entailed(case):
        eq=equations(case);solutions=S.linsolve(eq,variables)
        if len(solutions)!=1:raise ValueError('inconsistent angles')
        solution=next(iter(solutions))
        result=all(S.simplify(v-solution[0])==0 for v in solution[1:])
        if not result:
            witness=case.get('counterexample')
            if witness is None:raise ValueError('need positive counterexample angles')
            witness=list(map(S.Rational,witness));subs=dict(zip(variables,witness))
            if any(v<=0 or v>=180 for v in witness) or any(S.simplify(e.subs(subs))!=0 for e in eq) or len(set(witness))==1:raise ValueError('invalid angle counterexample')
        return result
    return select_unique(spec['options'],lambda o:not entailed(o) if spec['query']=='not_equilateral' else entailed(o))


HANDLERS.update({'geometry_circle_intersections':circle_intersections,
 'geometry_linear_identity':linear_identity,'geometry_polygon':polygon_model,
 'geometry_triangle_squares':triangle_square_model,
 'geometry_reflected_path':reflected_path,'geometry_angle_implication':angle_implication})
