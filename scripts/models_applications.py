"""Independent application models: calculate semantic option values, never answer keys.

All choice handlers inspect every supplied option through select_unique.  Inputs
are the mathematical data in the question; option `value` fields are a typed
transcription of the displayed claims, not truth flags.  No handler knows a qid.
"""
from fractions import Fraction
from itertools import combinations, permutations, product
from math import sqrt
import sympy as SP

from exact_polynomial import Polynomial
from model_types import TextProof, select_unique


def F(x):
    if isinstance(x, bool):
        raise ValueError('boolean is not a mathematical number')
    return Fraction(str(x))


def eq(a, b):
    if isinstance(a,bool) or isinstance(b,bool):
        return type(a) is bool and type(b) is bool and a == b
    if isinstance(a, dict) or isinstance(b, dict):
        return isinstance(a, dict) and isinstance(b, dict) and set(a) == set(b) and all(eq(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)) or isinstance(b, (list, tuple)):
        return isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)) and len(a) == len(b) and all(eq(x, y) for x, y in zip(a, b))
    try:
        return F(a) == F(b)
    except (ValueError, TypeError, ZeroDivisionError):
        return a == b


def pick(spec, expected):
    return select_unique(spec['options'], lambda option: eq(option['value'], expected))


def terms(source):
    return Polynomial(source).terms


def linear_quadrants(k, b):
    """Exact sign partition at the two possible coordinate-axis crossings."""
    k, b = F(k), F(b)
    cuts = sorted({Fraction(0), -b / k} if k else {Fraction(0)})
    probes = [cuts[0] - 1, cuts[-1] + 1] + [(a + c) / 2 for a, c in zip(cuts, cuts[1:])]
    return sorted({(1 if x > 0 else 2) if k*x+b > 0 else (4 if x > 0 else 3)
                   for x in probes if x and k*x+b})


def affine(spec):
    d = spec['inputs']; query = spec['query']
    k, b = F(d.get('slope', 0)), F(d.get('intercept', 0))
    if query == 'points':
        return select_unique(spec['options'], lambda o: len({tuple(p) for p in o['points']}) >= 2 and
                             all(F(y) == k*F(x)+b for x, y in o['points']))
    if query == 'quadrants_to_parameters':
        return select_unique(spec['options'], lambda o: linear_quadrants(*o['value']) == d['quadrants'])
    if query == 'axes':
        if not k: raise ValueError('axes query requires nonzero slope')
        result = [(0, b), (-b/k, 0)]
        return pick(spec, result) if 'options' in spec else TextProof(result, 'coordinates')
    if query == 'intersection':
        k2, b2 = F(d['second_slope']), F(d['second_intercept'])
        if k == k2: raise ValueError('lines have no unique intersection')
        x = (b2-b)/(k-k2)
        return TextProof([(x, k*x+b)], 'coordinates')
    if query == 'formula': return pick(spec, [k, b])
    if query == 'monotonic': return pick(spec, 'increasing' if k>0 else 'decreasing' if k<0 else 'constant')
    if query == 'rank':
        ys = [k*F(x)+b for x in d['xs']]
        if len(set(ys)) != len(ys): raise ValueError('strict rank has tied values')
        return pick(spec, sorted(range(len(ys)), key=lambda i: ys[i], reverse=True))
    if query == 'zero': return pick(spec, -b/k)
    if query == 'nonzero_parameter_choice':
        if not k: raise ValueError('coefficient is independent of parameter')
        return pick(spec,['≠',-b/k])
    if query == 'nonzero_parameter':
        if not k: raise ValueError('coefficient is independent of parameter')
        return TextProof('%s≠%s' % (d['variable'], -b/k), 'relation')
    if query == 'positive_set':
        if not k: raise ValueError('strict half-line requires nonzero slope')
        relation = '>' if (k>0) == (d.get('sign', 1)>0) else '<'
        value = [relation, -b/k]
        return pick(spec, value) if 'options' in spec else TextProof('%s%s%s' % (d.get('variable','x'), relation, -b/k), 'relation')
    if query == 'motion':
        # Derivative of distance/time is speed; a horizontal graph has speed 0.
        return pick(spec, 'stationary' if k == 0 else 'forward' if k>0 else 'return')
    raise ValueError('unknown affine query')


def polynomial_class(spec):
    d = spec['inputs']; target = d['degree']; variable = d.get('variable','x')
    def matches(o):
        try:
            p = terms(o['expression'])
        except (ValueError, SyntaxError, ZeroDivisionError):
            return False
        if any(set(m)-{variable} for m in p): return False
        degree = max(map(len, p), default=0)
        return degree == target and (not d.get('zero_constant') or p.get((),0) == 0)
    return select_unique(spec['options'], matches)


def quadratic(spec):
    d=spec['inputs']; query=spec['query']
    if query=='widest':
        values=[abs(F(o['coefficient'])) for o in spec['options']]
        if any(v==0 for v in values): raise ValueError('not all candidates are parabolas')
        return select_unique(spec['options'],lambda o: abs(F(o['coefficient']))==min(values))
    a,b,c=map(F,d['coefficients'])
    if not a: raise ValueError('not quadratic')
    h=-b/(2*a); v=c-b*b/(4*a)
    if query=='roots':
        # Candidate roots center±sqrt(radicand)/scale: compare exact sum/product.
        def root_pair(o):
            scale=F(o['scale']);radicand=F(o['radicand'])
            if scale==0 or radicand<0:return False
            return F(o['center'])*2==-b/a and F(o['center'])**2-radicand/scale**2==c/a
        return select_unique(spec['options'],root_pair)
    if query=='root_count':
        disc=b*b-4*a*c
        return pick(spec, 2 if disc>0 else 1 if disc==0 else 0)
    if query=='graph': return pick(spec, {'opening':'up' if a>0 else 'down','vertex':[h,v],'axis':['x',h]})
    if query=='translation': return pick(spec, {'vertex':[h,v],'axis':['x',h],'shift':[h,v]})
    if query=='rank':
        ys=[a*F(x)**2+b*F(x)+c for x in d['xs']]
        if len(set(ys))!=len(ys): raise ValueError('strict rank has tied values')
        return pick(spec,sorted(range(len(ys)),key=lambda i:ys[i],reverse=True))
    if query=='increasing': return pick(spec,['<' if a<0 else '>',h])
    raise ValueError('unknown quadratic query')


def inverse(spec):
    d=spec['inputs']; query=spec['query']
    if query=='classify':
        return select_unique(spec['options'],lambda o: terms(o['numerator'])!={} and
                             set(terms(o['numerator']))=={()} and set(terms(o['denominator']))=={('x',)})
    k=F(d['k']) if 'k' in d else F(d['point'][0])*F(d['point'][1])
    if k==0: raise ValueError('inverse proportion constant must be nonzero')
    if query=='graph': return pick(spec,{'quadrants':[1,3] if k>0 else [2,4], 'branch_monotonic':'decreasing' if k>0 else 'increasing'})
    if query=='formula': return pick(spec,k)
    if query=='physical_formula': return pick(spec,{'power':-1,'coefficient':k,'positive_domain':True})
    if query=='point': return select_unique(spec['options'],lambda o:F(o['point'][0])*F(o['point'][1])==k and F(o['point'][0])!=0)
    if query=='rank':
        ys=[k/F(x) for x in d['xs']]
        if len(set(ys))!=len(ys): raise ValueError('strict rank has tied values')
        return pick(spec,sorted(range(len(ys)),key=lambda i:ys[i],reverse=True))
    if query=='constant_product': return pick(spec,[-1,k])
    raise ValueError('unknown inverse query')


def rational_sign(spec):
    """Exact open intervals for factored rational inequalities (linear factors).

    roots are numerator zeroes; poles are denominator zeroes; multiplicities
    are represented by repetition.  Leading coefficient and comparison sign
    determine each interval.  This models whole intervals, not sample data.
    """
    d=spec['inputs']; zeros=list(map(F,d['zeros'])); poles=list(map(F,d['poles'])); lead=F(d['leading'])
    if lead==0: raise ValueError('zero rational numerator unsupported')
    cuts=sorted(set(zeros+poles)); edges=[None]+cuts+[None]; intervals=[]
    for left,right in zip(edges,edges[1:]):
        x=(right-1 if left is None else left+1 if right is None else (left+right)/2)
        y=lead
        for z in zeros: y*=x-z
        for p in poles: y/=x-p
        if (y>0)==(d['sign']>0): intervals.append([None if left is None else left,None if right is None else right])
    return pick(spec,intervals)


def statistics_model(spec):
    d=spec['inputs']; query=spec['query']
    if query=='stable':
        variances=[(F(s['spread'])**2 if s['kind']=='sd' else F(s['spread'])) for s in d['samples']]
        if any(v<0 for v in variances): raise ValueError('variance cannot be negative')
        m=min(variances); ids=[i for i,v in enumerate(variances) if v==m]
        return pick(spec,ids)
    if query=='iqr':
        widths=[F(q3)-F(q1) for q1,q3 in d['quartiles']]
        if any(v<0 for v in widths):raise ValueError('quartiles out of order')
        m=min(widths);return pick(spec,[i for i,v in enumerate(widths) if v==m])
    if query=='translate_variance':
        shift=F(d['shift'])
        # Each squared centered deviation is identical for arbitrary x and mean m.
        unchanged=terms('(x+(%s)-(m+(%s)))**2'%(shift,shift))==terms('(x-m)**2')
        if not unchanged:raise ValueError('translation identity did not hold')
        return pick(spec,'same')
    if query=='frequency_sum':
        counts=list(map(F,d['counts']));total=sum(counts)
        if total<=0 or any(x<0 for x in counts):raise ValueError('invalid frequency counts')
        return pick(spec,sum(x/total for x in counts))
    if query=='increments':
        xs=list(map(F,d['data']));delta=[b-a for a,b in zip(xs,xs[1:])];m=max(delta)
        return pick(spec,[i for i,x in enumerate(delta) if x==m])
    if query=='axis_scale':
        maximum=max(map(F,d['data']))
        feasible=[o for o in spec['options'] if F(o['start'])==0 and F(o['stop'])>=maximum and 0<F(o['step'])<=F(o['stop'])]
        if not feasible:raise ValueError('no axis covers the data')
        best=min((F(o['stop']),F(o['step'])) for o in feasible)
        return select_unique(spec['options'],lambda o:o in feasible and (F(o['stop']),F(o['step']))==best)
    if query=='truncated_bar':
        a,b=map(F,d['values']);start=F(d['axis_start'])
        if not 0<start<min(a,b):raise ValueError('not a positive truncated axis')
        result={'actual_ratio':b/a,'height_ratio':(b-start)/(a-start),'cause':'truncated_origin'}
        return select_unique(spec['options'],lambda o:o['cause']==result['cause'] and result['height_ratio']>result['actual_ratio'])
    raise ValueError('unknown statistics query')


def outcomes(d):
    if 'experiments' in d:
        spaces=d['experiments']
        if not spaces or any(not s for s in spaces):raise ValueError('empty experiment')
        if len(spaces)>4 or any(len(s)>30 for s in spaces):raise ValueError('experiment too large')
        return list(product(*spaces))
    urn=d['urn'];balls=[color for color,n in urn['counts'].items() for _ in range(n)];n=urn['draws']
    if not balls or any(type(c) is not int or c<0 for c in urn['counts'].values()):raise ValueError('invalid urn')
    if urn.get('replace'):
        return list(product(balls,repeat=n))
    if not 0<=n<=len(balls):raise ValueError('too many draws')
    # Physical-index permutations preserve draw order and give every ordered
    # sample equal weight, including distinct balls of the same colour.
    return [tuple(balls[i] for i in inds) for inds in permutations(range(len(balls)),n)]


def event(e, xs):
    op=e['op']
    if op=='all':return all(event(c,xs) for c in e['conditions'])
    if op=='any':return any(event(c,xs) for c in e['conditions'])
    if op=='sum_in':return any(eq(sum(F(x) for x in xs),candidate) for candidate in e['values'])
    if op=='count_ge':
        if type(e['count']) is not int:raise ValueError('event count must be an integer')
        return sum(eq(x,e['value']) for x in xs)>=e['count']
    if op=='all_equal':return all(eq(x,e['value']) for x in xs)
    if op=='mod':return eq(F(xs[e.get('index',0)])%F(e['divisor']),e['remainder'])
    value=xs[e.get('index',0)]
    if op=='eq':return eq(value,e['value'])
    if op=='lt':return F(value)<F(e['value'])
    if op=='in':return any(eq(value,candidate) for candidate in e['values'])
    raise ValueError('unknown event predicate')


def probability(spec):
    d=spec['inputs']
    if spec['query']=='certain_option' and all('experiment' in o for o in spec['options']):
        return select_unique(spec['options'],lambda o:all(event(o['event'],x) for x in outcomes(o['experiment'])))
    space=outcomes(d)
    if not space:raise ValueError('empty sample space')
    prob=lambda e:Fraction(sum(event(e,x) for x in space),len(space))
    query=spec['query']
    if query=='classification':
        p=prob(d['event']);name='不可能事件' if p==0 else '必然事件' if p==1 else '随机事件'
        return pick(spec,name) if 'options' in spec else TextProof(name,'word')
    if query=='certain_option':return select_unique(spec['options'],lambda o:prob(o['event'])==1)
    if query=='rank':
        ps=[prob(e) for e in d['events']]
        if len(set(ps))!=len(ps):raise ValueError('strict rank has tied probabilities')
        return pick(spec,sorted(range(len(ps)),key=lambda i:ps[i],reverse=d.get('descending',False)))
    if query=='winner':
        ps=[prob(e) for e in d['events']]
        if len(ps)!=len(d['rewards']) or any(F(r)<=0 for r in d['rewards']):raise ValueError('one positive reward per event is required')
        utility=[p*F(reward) for p,reward in zip(ps,d['rewards'])]
        m=max(utility)
        return pick(spec,[i for i,v in enumerate(utility) if v==m])
    if query=='color_order':
        colors=list(d['urn']['counts']);ps=[prob({'op':'eq','value':c}) for c in colors]
        if len(set(ps))!=len(ps):raise ValueError('strict color order has ties')
        return TextProof([colors[i] for i in sorted(range(len(ps)),key=lambda i:ps[i],reverse=True)],'ordered_words')
    if query=='most_likely':
        ps=[prob({'op':'eq','value':c}) for c in d['colors']];m=max(ps)
        return pick(spec,[i for i,p in enumerate(ps) if p==m])
    raise ValueError('unknown probability query')


def probability_number(spec):
    d=spec['inputs']
    low,high=F(d['lower']),F(d['upper'])
    if low>=high:raise ValueError('invalid probability interval')
    return select_unique(spec['options'],lambda o: low<F(o['value'])<high if d.get('strict') else low<=F(o['value'])<=high)


def sampling(spec):
    d=spec['inputs'];population=d['population'];size=d['sample_size']
    if len(set(population))!=len(population) or not 0<size<=len(population):raise ValueError('invalid population/sample')
    def inclusion(o):
        frame=o['frame']
        if len(set(frame))!=len(frame) or size>len(frame) or not set(frame)<=set(population):raise ValueError('invalid sampling frame')
        if o['method']=='simple_random':return [Fraction(size,len(frame)) if p in frame else Fraction(0) for p in population]
        if o['method']=='unspecified':
            witness=o.get('counterexample')
            if not isinstance(witness,dict) or witness.get('method')=='unspecified':raise ValueError('unspecified design needs a feasible counterexample')
            result=inclusion(witness)
            if all(p==Fraction(size,len(population)) for p in result):raise ValueError('counterexample does not refute equal inclusion')
            return result
        if o['method']=='fixed':return [Fraction(int(p in frame[:size])) for p in population]
        raise ValueError('unmodelled sampling method')
    return select_unique(spec['options'],lambda o:all(p==Fraction(size,len(population)) for p in inclusion(o)))


def circle_position(spec):
    d=spec['inputs'];query=spec['query'];r=F(d.get('radius',1))
    if r<=0:raise ValueError('circle radius must be positive')
    def position(distance2,point=False):
        return ('inside' if point else 'secant') if distance2<r*r else ('on' if point else 'tangent') if distance2==r*r else ('outside' if point else 'disjoint')
    if query=='point':return pick(spec,position(sum(F(x)**2 for x in d['offset']),True))
    if query=='line':return pick(spec,position(F(d['distance'])**2))
    if query=='axes':
        x,y=map(F,d['center']);return pick(spec,[position(y*y),position(x*x)])
    if query=='radius_for_interior':
        dist2=sum(F(x)**2 for x in d['offset']);dist=sqrt(float(dist2))
        return pick(spec,['>',dist])
    if query=='pythagorean_tangent':
        oa,ab,ob=map(F,d['lengths'])
        if oa!=r:raise ValueError('OA must equal the circle radius')
        if min(oa,ab,ob)<=0 or oa+ab<=ob or oa+ob<=ab or ab+ob<=oa:raise ValueError('invalid triangle')
        return pick(spec,'tangent' if oa*oa+ab*ab==ob*ob else 'secant')
    raise ValueError('unknown circle position query')


def proportions(spec):
    return select_unique(spec['options'],lambda o:any(F(a)*F(d)==F(b)*F(c) for a,b,c,d in permutations(o['lengths'])))


def rational_identity(spec):
    """Exact cross-multiplication of rational identities over indeterminates."""
    def valid(o):
        ln,ld=o['left'];rn,rd=o['right']
        if not terms(ld) or not terms(rd):raise ValueError('identically zero denominator')
        return terms('(%s)*(%s)'%(ln,rd))==terms('(%s)*(%s)'%(rn,ld))
    return select_unique(spec['options'],lambda o:valid(o)==spec['inputs'].get('select_true',True))


def triangle_similarity(spec):
    d=spec['inputs'];query=spec['query']
    if query=='angle_equalities':
        # Two distinct corresponding angle equalities imply the third by the
        # exact angle-sum identity, without inventing numerical angle values.
        pairs=d['equal_angle_pairs']
        if len(pairs)!=2 or len({p[0] for p in pairs})!=2 or len({p[1] for p in pairs})!=2:
            raise ValueError('AA requires two distinct corresponding angle pairs')
        if terms('180-a-b')!=terms('180-b-a'):raise ValueError('angle sum identity failed')
        return pick(spec,{'similar':True,'criterion':'AA'})
    if query=='angles':
        triangles=[]
        for known in d['angles']:
            known=list(map(F,known))
            if len(known)==2:known+=[180-sum(known)]
            if len(known)!=3 or min(known)<=0 or sum(known)!=180:raise ValueError('invalid triangle angles')
            triangles.append(sorted(known))
        same=triangles[0]==triangles[1]
        return pick(spec,{'similar':same,'criterion':'AA'} if d.get('include_criterion') else same)
    if query=='sas':
        x,y=d['sides'];same=F(x[0])*F(y[1])==F(x[1])*F(y[0]) and F(d['angles'][0])==F(d['angles'][1])
        return pick(spec,{'similar':same,'criterion':'SAS'})
    if query=='parallel_correspondence':
        # Coordinates along the same two rays give an exact common homothety.
        names=d['names']
        if len(names)!=5 or len(set(names))!=5:raise ValueError('five distinct vertex names required')
        a,small_b,small_c,big_b,big_c=names
        # Let A=(0,0), B=(b,0), C=(c,d).  Parallelism yields
        # det(E-D,C-B)=bd(s-t)=0, so s=t for a nondegenerate triangle.
        vertices={a:['0','0'],big_b:['b','0'],big_c:['c','d'],small_b:['t*b','0'],small_c:['t*c','t*d']}
        def valid(o):
            small,big=o['value']
            if len(small)!=3 or len(big)!=3 or len(set(small))!=3 or len(set(big))!=3:return False
            if any(n not in vertices for n in small+big):raise ValueError('unknown vertex')
            return all(terms('(%s)-(%s)-t*((%s)-(%s))'%(vertices[small[j]][axis],vertices[small[0]][axis],vertices[big[j]][axis],vertices[big[0]][axis]))=={}
                       for j in [1,2] for axis in [0,1])
        return select_unique(spec['options'],valid)
    raise ValueError('unknown triangle similarity query')


def rotation(spec):
    d=spec['inputs'];angle=F(d['angle']);query=spec['query']
    if angle%90:raise ValueError('this exact rotation model accepts quarter turns only')
    matrices=[((1,0),(0,1)),((0,-1),(1,0)),((-1,0),(0,-1)),((0,1),(-1,0))]
    matrix=matrices[int(angle/90)%4]
    if query=='distance_angle':
        # Orthogonality derives length preservation; dot of a vector with its
        # quarter-turn determines its smaller angle independently of radius.
        norm=sum(v*v for v in matrix[0]);small=min(angle%360,360-angle%360)
        return pick(spec,[norm,small])
    if query=='length_angle':return [F(d['length']),F(d['vertex_angle'])]
    if query=='point':
        x,y=map(F,d.get('point',d.get('point_signs')));u=matrix[0][0]*x+matrix[0][1]*y;v=matrix[1][0]*x+matrix[1][1]*y
        quadrant=1 if u>0 and v>0 else 2 if u<0 and v>0 else 3 if u<0 and v<0 else 4 if u>0 and v<0 else 0
        return pick(spec,quadrant)
    raise ValueError('unknown rotation query')


def trig_model(spec):
    d=spec['inputs'];query=spec['query']
    def rational(value):
        f=F(value);return SP.Rational(f.numerator,f.denominator)
    def candidate_value(value):
        if isinstance(value,list):
            if len(value)!=2 or F(value[0])<0 or F(value[1])==0:raise ValueError('invalid real radical')
            return SP.sqrt(rational(value[0]))/rational(value[1])
        return rational(value)
    def equal_values(o,expected):
        return len(o['value'])==len(expected) and all(SP.simplify(candidate_value(x)-y)==0 for x,y in zip(o['value'],expected))
    if query=='special':
        funcs={'sin':SP.sin,'cos':SP.cos,'tan':SP.tan}
        expected=[funcs[f](rational(a)*SP.pi/180) for f,a in d['functions']]
        if any(value.is_real is not True for value in expected):raise ValueError('undefined or nonreal trigonometric value')
        return select_unique(spec['options'],lambda o:equal_values(o,expected))
    if query=='triangle':
        angle=rational(d['angle'])*SP.pi/180;opposite=rational(d['opposite'])
        if not 0<F(d['angle'])<90 or opposite<=0:raise ValueError('nondegenerate acute triangle required')
        expected=[opposite/SP.tan(angle),opposite/SP.sin(angle)]
        return select_unique(spec['options'],lambda o:equal_values(o,expected))
    if query=='parking':
        length,depth=F(d['length']),F(d['depth'])
        if length<=0 or depth<=0:raise ValueError('positive parking dimensions required')
        if any(not 0<=F(o['angle'])<=90 for o in spec['options']):raise ValueError('line angle must be between 0 and 90 degrees')
        def fits(o):
            difference=SP.simplify(rational(length)*SP.sin(rational(o['angle'])*SP.pi/180)-rational(depth))
            if difference.is_nonpositive is None:raise ValueError('exact sign is unresolved')
            return difference.is_nonpositive
        return select_unique(spec['options'],fits)
    if query=='scale_ratio':
        scale=F(d['scale'])
        if scale<=0:raise ValueError('side scale must be positive')
        # Compare (k*u)/(k*v) with u/v by exact cross multiplication.
        numerator=terms('(%s)*u*v'%scale);denominator=terms('(%s)*v*u'%scale)
        if numerator!=denominator:raise ValueError('similarity ratio cancellation failed')
        key=next(iter(denominator));return pick(spec,numerator[key]/denominator[key])
    raise ValueError('unknown trigonometry query')


def orthographic(spec):
    """Axis-aligned ideal solid silhouettes under orthogonal projections.

    Axis convention is z vertical, front is x-z, left is y-z, top is x-y.
    Cone top includes the projected apex center (a standard technical view).
    """
    d=spec['inputs'];query=spec['query']
    def views(solid):
        kind=solid['shape'];a=F(solid.get('side',1));h=F(solid.get('height',2));r=F(solid.get('radius',1))
        if min(a,h,r)<=0:raise ValueError('solid dimensions must be positive')
        if kind=='cylinder':return ['rectangle','rectangle','circle']
        if kind=='cone':return ['isosceles_triangle','isosceles_triangle','circle_with_center']
        if kind=='sphere':return ['circle']*3
        if kind=='cube':return ['square']*3
        if kind=='cuboid':return ['rectangle']*3
        raise ValueError('unknown ideal solid')
    if query=='views':return pick(spec,views(d))
    if query=='solid_for_views':return select_unique(spec['options'],lambda o:views(o['solid'])==d['views'])
    if query=='circle_edge_on':
        # Orthogonal projection along z of a vertical disk has rank one,
        # positive diameter, and hence its image is a line segment.
        basis=d['plane_basis'];projected=[(F(v[0]),F(v[1])) for v in basis]
        determinant=projected[0][0]*projected[1][1]-projected[0][1]*projected[1][0]
        rank=2 if determinant else 1 if any(x or y for x,y in projected) else 0
        return pick(spec,{0:'point',1:'segment',2:'area'}[rank])
    raise ValueError('unknown projection query')


HANDLERS={
 'app_affine':affine,'app_polynomial_class':polynomial_class,'app_quadratic':quadratic,
 'app_inverse':inverse,'app_rational_sign':rational_sign,'app_statistics':statistics_model,
 'app_probability':probability,'app_probability_number':probability_number,'app_sampling':sampling,
 'app_circle_position':circle_position,'app_proportions':proportions,'app_rational_identity':rational_identity,
 'app_triangle_similarity':triangle_similarity,'app_rotation':rotation,'app_trig':trig_model,'app_orthographic':orthographic,
}


def radical_domain(spec):
    d=spec['inputs'];a,b=F(d['slope']),F(d['intercept'])
    if not a:raise ValueError('domain model requires a nonconstant radicand')
    strict=d.get('in_denominator',False)
    op=('>' if strict else '≥') if a>0 else ('<' if strict else '≤')
    return pick(spec,[op,-b/a])


def growth_equation(spec):
    d=spec['inputs'];initial=F(d['initial']);final=F(d['final']);periods=d['periods']
    if initial<=0 or final<=0 or type(periods) is not int or not 1<=periods<=8:raise ValueError('invalid compound-growth data')
    expected=terms('(%s)*(1+x)**%s-(%s)'%(initial,periods,final))
    return select_unique(spec['options'],lambda o:terms('(%s)-(%s)'%(o['left'],o['right']))==expected)


def monomial_product(spec):
    # If y*x**p=C (C nonzero), matching powers forces y=C*x**(-p).
    p=F(spec['inputs']['x_power']);target=-p
    return pick(spec,target)


HANDLERS.update({'app_radical_domain':radical_domain,'app_growth_equation':growth_equation,'app_monomial_product':monomial_product})


def symbolic_ratio(spec):
    d=spec['inputs'];numerator=terms(d['numerator']);denominator=terms(d['denominator'])
    if not denominator:raise ValueError('zero denominator')
    if not numerator:result=Fraction(0)
    else:
        key=next(iter(denominator));result=numerator.get(key,0)/denominator[key]
        if numerator!={k:v*result for k,v in denominator.items() if v*result}:raise ValueError('ratio is not constant')
    return pick(spec,result)

HANDLERS['app_symbolic_ratio']=symbolic_ratio


def weighted_mean_formula(spec):
    d=spec['inputs'];midpoints=d['midpoints'];weights=d['frequencies']
    if not midpoints or len(midpoints)!=len(weights):raise ValueError('missing grouped variables')
    expected_num='+'.join('(%s)*(%s)'%(x,w) for x,w in zip(midpoints,weights))
    expected_den='+'.join('(%s)'%w for w in weights)
    if not terms(expected_den):raise ValueError('total frequency is zero')
    return select_unique(spec['options'],lambda o:terms('(%s)*(%s)'%(o['numerator'],expected_den))==terms('(%s)*(%s)'%(expected_num,o['denominator'])) and bool(terms(o['denominator'])))


def grouping_error(spec):
    """Prove/refute universal bias claims using supplied valid grouped witnesses.

    A counterexample refutes 'always exact' or 'always overestimates'; one valid
    nonzero error proves 'can have error'.  These quantifiers deliberately use
    different proof obligations: no witness is mistaken for universal evidence.
    """
    errors=[]
    for case in spec['inputs']['witnesses']:
        total=0;estimated=Fraction(0);actual=Fraction(0)
        for g in case:
            lo,hi=F(g['lower']),F(g['upper']);xs=list(map(F,g['data']))
            if lo>=hi or not xs or any(not lo<=x<hi for x in xs):raise ValueError('invalid grouped witness')
            total+=len(xs);estimated+=(lo+hi)*len(xs)/2;actual+=sum(xs)
        if not total:raise ValueError('empty grouped witness')
        errors.append((estimated-actual)/total)
    if not errors:raise ValueError('missing witnesses')
    def proved(o):
        claim=o['claim']
        if claim=='possible_error':return any(error!=0 for error in errors)
        if claim=='always_equal':
            if any(error!=0 for error in errors):return False
            raise ValueError('witnesses cannot prove universal equality')
        if claim=='always_overestimate':
            if any(error<=0 for error in errors):return False
            raise ValueError('witnesses cannot prove universal positive bias')
        raise ValueError('unsupported error quantifier')
    return select_unique(spec['options'],proved)


def rotation_invariants(spec):
    """Symbolic proof for arbitrary rotations, c²+s²=1 (not angle sampling)."""
    # The two universal metric identities establish norm and cosine preservation.
    norm=terms('(c*x-s*y)**2+(s*x+c*y)**2')
    base=terms('(c**2+s**2)*(x**2+y**2)')
    dot=terms('(c*x-s*y)*(c*u-s*v)+(s*x+c*y)*(s*u+c*v)')
    dot_base=terms('(c**2+s**2)*(x*u+y*v)')
    if norm!=base or dot!=dot_base:raise ValueError('rotation metric identity failed')
    def claim(o):
        ratio=F(o['length_ratio']);cosine_sign=F(o['cosine_sign'])
        return ratio>=0 and terms('(%s)**2*(x**2+y**2)'%ratio)==terms('x**2+y**2') and terms('(%s)*(x*u+y*v)'%cosine_sign)==terms('x*u+y*v')
    return select_unique(spec['options'],claim)


def equidistant_point(spec):
    """Check symbolic candidate circumcentres by all squared distances.

    Vertices have polynomial coordinates.  Each candidate point has two
    polynomial numerators and one common nonzero denominator; clearing that
    common square preserves exact equality for every allowed parameter value.
    """
    vertices=spec['inputs']['vertices']
    if len(vertices)!=3:raise ValueError('three vertices required')
    def check(o):
        denominator=o['denominator']
        if not terms(denominator):return False
        nx,ny=o['numerators']
        distances=[terms('((%s)-(%s)*(%s))**2+((%s)-(%s)*(%s))**2'%(nx,x,denominator,ny,y,denominator)) for x,y in vertices]
        return distances[0]==distances[1]==distances[2]
    return select_unique(spec['options'],check)


def central_symmetry(spec):
    """Check shape families by exact half-turn identities or polygon indexing."""
    def central(shape):
        kind=shape['shape']
        if kind in ('parallelogram','rectangle','rhombus','square'):
            # Vertices O,U,U+V,V.  Half-turn centre (U+V)/2 pairs O↔U+V,U↔V.
            vertices=[['0','0'],['a','b'],['a+c','b+d'],['c','d']]
            return all(any(terms('(%s)+(%s)-(a+c)'%(x,u))=={} and terms('(%s)+(%s)-(b+d)'%(y,v))=={} for u,v in vertices) for x,y in vertices)
        if kind=='circle':return terms('(-x)**2+(-y)**2-r**2')==terms('x**2+y**2-r**2')
        if kind=='triangle':
            # An order-two permutation on three vertices has a fixed vertex.
            # The other two would be opposite about it, making them collinear.
            return False
        if kind=='regular_polygon':
            n=shape['vertices']
            if type(n) is not int or n<3:raise ValueError('invalid polygon')
            return (Fraction(n,2)).denominator==1
        raise ValueError('unknown shape family')
    return select_unique(spec['options'],lambda o:all(central(shape) for shape in o['shapes']))


def bernoulli_claims(spec):
    """Exact binomial support and concentration proof for independent trials."""
    d=spec['inputs'];p=F(d['p']);n=d['trials']
    if not 0<p<1 or type(n) is not int or not 1<=n<=200:raise ValueError('nondegenerate finite Bernoulli trials required')
    from math import comb
    distribution=[F(comb(n,k))*p**k*(1-p)**(n-k) for k in range(n+1)]
    if sum(distribution)!=1:raise ValueError('distribution does not normalize')
    # Var(mean)=p(1-p)/n.  p(1-p) <= 1/4 follows from the exact
    # identity 1/4-p(1-p)=(p-1/2)^2 >=0; Chebyshev gives convergence.
    concentration=terms('1/4-p*(1-p)')==terms('(p-1/2)**2')
    def check(o):
        claim=o['claim'];local_p=p;local_n=n;local_distribution=distribution
        if 'experiment' in o:
            local_p=F(o['experiment']['p']);local_n=o['experiment']['trials']
            if not 0<local_p<1 or type(local_n) is not int or not 1<=local_n<=2000:raise ValueError('invalid candidate experiment')
            local_distribution=[F(comb(local_n,k))*local_p**k*(1-local_p)**(local_n-k) for k in range(local_n+1)]
        if claim=='fixed_count':return all(prob==0 or k==o['count'] for k,prob in enumerate(local_distribution))
        if claim=='not_fixed_count_with_concentration':return concentration and any(k!=o['count'] and prob>0 for k,prob in enumerate(local_distribution))
        if claim=='single_probability':return local_p==F(o['probability'])
        if claim=='next_probability_greater':
            h=o['history_heads'];t=o['history_trials']
            if type(h) is not int or type(t) is not int or not 0<=h<=t:raise ValueError('invalid trial history')
            history=local_p**h*(1-local_p)**(t-h)
            conditional=history*local_p/history
            return conditional>F(o['probability'])
        if claim=='frequency_always_probability':return all(prob==0 or Fraction(k,local_n)==local_p for k,prob in enumerate(local_distribution))
        if claim=='concentration':return concentration
        if claim=='probability_changes_with_trials':return False  # iid parameters are fixed by model, not observations
        raise ValueError('unknown Bernoulli claim')
    return select_unique(spec['options'],check)


def identifiability(spec):
    """Refute identification by two constraint-satisfying probability models."""
    d=spec['inputs'];n=d['outcome_count'];index=d['target_index'];witnesses=d['distributions']
    if type(n) is not int or n<2 or not 0<=index<n:raise ValueError('invalid outcome index')
    vectors=[]
    for xs in witnesses:
        xs=list(map(F,xs))
        if len(xs)!=n or min(xs)<0 or sum(xs)!=1:raise ValueError('invalid probability vector')
        if len(set(xs))==1:raise ValueError('witness violates nonuniformity premise')
        vectors.append(xs)
    if len(vectors)<2:raise ValueError('two feasible witnesses are required')
    target_values={v[index] for v in vectors}
    def check(o):
        if o['claim']=='forced_probability':
            proposed=F(o['probability'])
            if any(v!=proposed for v in target_values):return False
            raise ValueError('examples cannot establish forced probability')
        if o['claim']=='not_identified':return len(target_values)>1
        if o['claim']=='infinite_outcomes':return False  # count is explicitly finite
        raise ValueError('unknown identification claim')
    return select_unique(spec['options'],check)


def positive_rational_sign(spec):
    """Sign proof for a monomial ratio in strictly positive independent gaps.

    For shadows, h>0 and H-h=g>0, so ds/dd=h/g.  Inputs transcribe
    numerator/denominator exponents after this reversible substitution.
    """
    d=spec['inputs'];variables=set(d['positive_variables']);coefficient=F(d['coefficient'])
    if not variables or not coefficient:raise ValueError('nonzero ratio needs positive variables')
    for side in ['numerator_powers','denominator_powers']:
        if any(name not in variables or type(power) is not int for name,power in d[side].items()):raise ValueError('unsupported sign factor')
    return pick(spec,'increasing' if coefficient>0 else 'decreasing')


HANDLERS.update({'app_weighted_mean_formula':weighted_mean_formula,'app_grouping_error':grouping_error,
 'app_rotation_invariants':rotation_invariants,'app_equidistant_point':equidistant_point,
 'app_central_symmetry':central_symmetry,'app_bernoulli_claims':bernoulli_claims,
 'app_identifiability':identifiability,'app_positive_rational_sign':positive_rational_sign})
