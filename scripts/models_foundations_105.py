"""Continuous and logical certificates for the remaining foundations questions.

All choice candidates describe mathematical objects. No question IDs, answer
keys, truth flags, shape-to-answer table, numeric sampling proof or string eval
are used. A failed proof/unsupported domain raises rather than becoming False.
"""
import ast
from fractions import Fraction
from itertools import combinations
import re
import sympy as S

from exact_polynomial import _source
from model_types import select_unique
from models_algebra import feasible, implies, number
from models_foundations_160 import ANGLE_DOMAIN, _angle_relation, _formula_equivalent


def _symbols(declarations):
    if not isinstance(declarations,dict) or len(declarations)>10:raise ValueError('bounded declared symbols required')
    result={}
    for name,kind in declarations.items():
        if not re.fullmatch('[a-z]',name) or kind not in ('real','positive','nonnegative','integer','positive_integer'):
            raise ValueError('unsupported symbol declaration')
        properties={'real':True}
        if kind in ('positive','nonnegative','integer'):properties[kind]=True
        if kind=='positive_integer':properties.update(positive=True,integer=True)
        result[name]=S.Symbol(name,**properties)
    return result


def _parse(source,symbols):
    """Bounded mathematical AST, adding only sin/cos to school arithmetic."""
    if not isinstance(source,str) or not source.strip() or len(source)>500:raise ValueError('invalid mathematical source')
    source=source.strip();tree=ast.parse(source,mode='eval')
    if sum(1 for _ in ast.walk(tree))>160:raise ValueError('oversized mathematical AST')
    constraints=[]
    def visit(node):
        if isinstance(node,ast.Constant) and type(node.value) in (int,float):
            value=S.Rational(ast.get_source_segment(source,node))
            if abs(value.p)>10**15 or value.q>10**15:raise ValueError('oversized literal')
            return value
        if isinstance(node,ast.Name):
            if node.id=='pi':return S.pi
            if node.id in symbols:return symbols[node.id]
            raise ValueError('undeclared mathematical symbol')
        if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.UAdd,ast.USub)):
            x=visit(node.operand);return x if isinstance(node.op,ast.UAdd) else -x
        if isinstance(node,ast.BinOp):
            a,b=visit(node.left),visit(node.right)
            if isinstance(node.op,ast.Add):return a+b
            if isinstance(node.op,ast.Sub):return a-b
            if isinstance(node.op,ast.Mult):return a*b
            if isinstance(node.op,ast.Div):constraints.append(S.Ne(b,0));return a/b
            if isinstance(node.op,ast.Pow):
                if b.is_Integer is not True or abs(b)>12:raise ValueError('small integer exponent required')
                if b<=0:constraints.append(S.Ne(a,0))
                return a**b
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and len(node.args)==1 and not node.keywords:
            x=visit(node.args[0])
            if node.func.id=='sin':return S.sin(x)
            if node.func.id=='cos':return S.cos(x)
            if node.func.id=='sqrt':constraints.append(S.Ge(x,0));return S.sqrt(x)
            if node.func.id=='Abs':return S.Abs(x)
        raise ValueError('unsupported mathematical syntax')
    value=visit(tree.body)
    if any(S.simplify(c)is not S.true for c in constraints):raise ValueError('expression domain was not proved by assumptions')
    if value.has(S.zoo,S.nan,S.oo,-S.oo):raise ValueError('nonfinite mathematical expression')
    return value


def _vector(values,symbols,dimension=None):
    if not isinstance(values,list) or not 1<=len(values)<=4 or (dimension is not None and len(values)!=dimension):
        raise ValueError('wrong vector dimension')
    return S.Matrix([_parse(v,symbols) for v in values])


def _zero(expression):
    expression=S.trigsimp(S.cancel(expression))
    if expression==0:return True
    if expression.is_zero is False:return False
    if expression.is_rational_function():return S.cancel(expression)==0
    raise ValueError('symbolic zero test is unresolved')


def _positive(expression):
    # Expansion can hide h²+(u-w)² behind an undecided mixed polynomial.
    # Every attempted form is symbolically equivalent; accept only a proved sign.
    if expression.is_positive is True:return expression
    candidate=S.trigsimp(expression)
    if candidate.is_positive is True:return candidate
    candidate=S.trigsimp(S.factor(expression))
    if candidate.is_positive is True:return candidate
    raise ValueError('strict positivity was not proved')


def _rank(matrix):
    """Certified rank: higher minors zero, one maximal minor provably nonzero."""
    if matrix.rows>4 or matrix.cols>4:raise ValueError('matrix exceeds reviewed dimension')
    for size in range(min(matrix.shape),0,-1):
        determinants=[S.trigsimp(S.factor(matrix.extract(rows,cols).det()))
                      for rows in combinations(range(matrix.rows),size)
                      for cols in combinations(range(matrix.cols),size)]
        if any(d.is_nonzero is True for d in determinants):return size
        if any(d!=0 for d in determinants):raise ValueError('rank depends on unproved parameter conditions')
    return 0


def _box_domain(parameters,bounds,symbols):
    if len(parameters)!=len(set(parameters)) or set(parameters)!=set(bounds):raise ValueError('one interval per parameter required')
    for p in parameters:
        if p not in symbols:raise ValueError('undeclared domain parameter')
        if len(bounds[p])!=2:raise ValueError('two bounds per parameter required')
        def endpoint(raw):
            if raw=='inf':return S.oo
            if raw=='-inf':return -S.oo
            return _parse(raw,symbols)
        low,high=map(endpoint,bounds[p])
        if (low.free_symbols|high.free_symbols)&{symbols[v] for v in parameters}:
            raise ValueError('a Cartesian box cannot have parameter-dependent bounds')
        if symbols[p].is_integer is True:raise ValueError('smooth charts need continuous parameter intervals')
        if (symbols[p].is_positive is True or symbols[p].is_nonnegative is True) and low.is_nonnegative is not True:
            raise ValueError('box bounds conflict with the declared parameter domain')
        if low in (S.oo,-S.oo) or high in (S.oo,-S.oo):
            if S.Lt(low,high)is not S.true:raise ValueError('empty infinite parameter interval')
        else:_positive(high-low)


def _polygon(vertices,symbols):
    points=[_vector(p,symbols,2) for p in vertices]
    if len(points) not in (3,4):raise ValueError('reviewed boundary family is triangle/quadrilateral')
    edges=[points[(i+1)%len(points)]-points[i] for i in range(len(points))]
    for e in edges:_positive(e.dot(e))
    turns=[S.factor(edges[i][0]*edges[(i+1)%len(edges)][1]-edges[i][1]*edges[(i+1)%len(edges)][0]) for i in range(len(edges))]
    if not (all(t.is_positive is True for t in turns) or all(t.is_negative is True for t in turns)):
        raise ValueError('nondegenerate convex polygon was not proved')
    return edges


def _boundary_signature(region,symbols):
    kind=region['kind']
    if kind=='polygon':
        edges=_polygon(region['vertices'],symbols)
        if len(edges)!=4:return ('linear',len(edges),'not_rectangle')
        right=True
        for i in range(4):
            dot=S.trigsimp(S.factor(edges[i].dot(edges[(i+1)%4])))
            if dot==0:continue
            if dot.is_nonzero is True:right=False
            else:raise ValueError('rectangularity depends on an unproved parameter condition')
        return ('linear',4,'rectangle' if right else 'other')
    if kind in ('disk','sector'):
        center=_vector(region['center'],symbols,2);radius=_positive(_parse(region['radius'],symbols))
        t=S.Symbol('_t',real=True)
        curve=center+radius*S.Matrix([S.cos(t),S.sin(t)])
        first=curve.diff(t);second=first.diff(t)
        _positive(S.trigsimp(first[0]*second[1]-first[1]*second[0]))
        if kind=='disk':return ('curved','smooth_closed')
        sweep=_parse(region['sweep'],symbols)
        _positive(sweep);_positive(2*S.pi-sweep)
        return ('curved','arc_and_radial_segments')
    raise ValueError('unknown plane-region constructor')


def cylinder_unroll(spec):
    symbols=_symbols(spec['symbols']);parameters=spec['parameters']
    if len(parameters)!=2:raise ValueError('a surface needs two parameters')
    if spec['seam']!='separated_boundary_copies':raise ValueError('the generator seam must be cut open')
    _box_domain(parameters,spec['bounds'],symbols)
    surface=_vector(spec['surface'],symbols,3)
    radius=_positive(_parse(spec['radius'],symbols));s,z=map(symbols.get,parameters)
    if radius.free_symbols&{s,z}:raise ValueError('cylinder radius cannot depend on surface coordinates')
    if not _zero(surface[0]**2+surface[1]**2-radius**2) or not _zero(surface[2]-z):
        raise ValueError('a right circular cylindrical surface was not proved')
    width=_parse(spec['bounds'][parameters[0]][1],symbols)-_parse(spec['bounds'][parameters[0]][0],symbols)
    if not _zero(width-2*S.pi*radius):raise ValueError('the cut strip must cover one circumference exactly')
    turn_rate=S.trigsimp((surface[0]*surface[1].diff(s)-surface[1]*surface[0].diff(s))/radius**2)
    if not _zero(turn_rate.diff(s)) or not _zero(turn_rate**2-1/radius**2):
        raise ValueError('single continuous angular winding was not proved')
    jacobian=surface.jacobian([symbols[p] for p in parameters]);metric=jacobian.T*jacobian
    if any(not _zero(metric[i,j]-int(i==j)) for i in range(2) for j in range(2)):
        raise ValueError('the proposed unrolling coordinates are not isometric')
    s,z=parameters;sl,sh=spec['bounds'][s];zl,zh=spec['bounds'][z]
    signature=_boundary_signature({'kind':'polygon','vertices':[[sl,zl],[sh,zl],[sh,zh],[sl,zh]]},symbols)
    return select_unique(spec['options'],lambda o:_boundary_signature(o['region'],symbols)==signature)


def affine_dimensions(spec):
    symbols=_symbols(spec['symbols']);target=spec['dimension']
    if type(target)is not int or not 0<=target<=3:raise ValueError('invalid target affine dimension')
    def check(option):
        obj=option['set']
        if obj['kind']=='linear_ball':
            radius=_positive(_parse(obj['radius'],symbols));basis=S.Matrix([[_parse(v,symbols) for v in row] for row in obj['basis']])
            if basis.rows!=3:raise ValueError('ambient R3 required')
            # Upper bound: all points are in image(B). Lower bound: 0 and
            # r/2 times each independent image basis vector lie in the ball.
            dimension=_rank(basis)
            if radius.is_positive is not True:raise ValueError('empty ball parameter domain')
        elif obj['kind']=='convex_hull':
            vertices=[_vector(p,symbols,3) for p in obj['vertices']]
            if not 1<=len(vertices)<=4:raise ValueError('bounded nonempty vertex set required')
            basis=S.Matrix.hstack(*(v-vertices[0] for v in vertices[1:])) if len(vertices)>1 else S.zeros(3,0)
            dimension=_rank(basis)
            # Every convex combination remains in the affine span; vertices
            # themselves attain the lower bound, so no finite-sample upper bound.
        else:raise ValueError('unknown continuous set constructor')
        return dimension==target
    return select_unique(spec['options'],check)


def cylinder_projection(spec):
    symbols=_symbols(spec['symbols']);r=_positive(_parse(spec['radius'],symbols));h=_positive(_parse(spec['height'],symbols))
    coordinates=spec['coordinates'];axis=spec['axis'];radial=spec['radial']
    if len(coordinates)!=3 or len(set(coordinates))!=3 or len(radial)!=2 or len(set(radial))!=2 or set(radial+[axis])!=set(coordinates) or any(c not in symbols for c in coordinates):
        raise ValueError('cylinder axes must partition declared R3 coordinates')
    if any(spec['symbols'][c]!='real' for c in coordinates):
        raise ValueError('ambient cylinder coordinates must range over the full real axes')
    if (r.free_symbols|h.free_symbols)&{symbols[c] for c in coordinates}:
        raise ValueError('cylinder dimensions cannot depend on ambient coordinates')
    result=[]
    for keep in spec['views']:
        if len(keep)!=2 or len(set(keep))!=2 or set(keep)-set(coordinates):raise ValueError('orthogonal two-coordinate projection required')
        if axis in keep:
            retained=next(x for x in keep if x!=axis);omitted=next(x for x in radial if x!=retained)
            x,y=symbols[retained],symbols[omitted]
            residual=S.expand(x*x+y*y-x*x)
            if residual.is_nonnegative is not True or residual.subs(y,0)!=0:raise ValueError('projection elimination certificate failed')
            allowed=S.solve_univariate_inequality(x*x<=r*r,x,relational=False)
            if allowed!=S.Interval(-r,r):raise ValueError('radial interval was not proved')
            result.append(('linear',4,'rectangle'))
        else:
            # Choosing z=0 realizes every radial disk point because h>0;
            # the radial inequality is unchanged by dropping z.
            if set(keep)!=set(radial) or not _zero(S.Integer(0)):raise ValueError('invalid radial projection')
            result.append(('curved','smooth_closed'))
    def check(option):
        if len(option['regions'])!=len(result):raise ValueError('one region per requested view')
        return all(_boundary_signature(region,symbols)==signature for region,signature in zip(option['regions'],result))
    return select_unique(spec['options'],check)


def revolution(spec):
    symbols=_symbols(spec['symbols']);z=symbols[spec['axis']]
    if not _zero(_parse(spec['turn_angle'],symbols)-2*S.pi):raise ValueError('one full revolution is required')
    if len(spec['axial_interval'])!=2:raise ValueError('two axial bounds required')
    low,high=[_parse(v,symbols) for v in spec['axial_interval']]
    if z in low.free_symbols|high.free_symbols:raise ValueError('axial bounds cannot depend on their own coordinate')
    _positive(high-low)
    radius=_parse(spec['radial_profile'],symbols);profile=S.Poly(S.expand(radius),z)
    if profile.degree()!=1:raise ValueError('reviewed source is an affine triangular profile')
    endpoint_values=[S.simplify(radius.subs(z,a)) for a in (low,high)]
    if endpoint_values[1]!=0:raise ValueError('triangle apex was not proved')
    _positive(endpoint_values[0]);_positive(radius.subs(z,(low+high)/2))
    rho,t=S.symbols('_rho _theta',real=True)
    sweep=S.Matrix([rho*S.cos(t),rho*S.sin(t),z])
    if not _zero(sweep[0]**2+sweep[1]**2-rho**2):raise ValueError('full-turn radial norm identity failed')
    source_cap=S.Poly(S.expand(radius**2),z)
    def check(option):
        solid=option['solid']
        if solid['kind']=='disk_sections':
            if len(solid['axial_interval'])!=2:raise ValueError('two candidate axial bounds required')
            candidate=S.Poly(S.expand(_parse(solid['radius_squared'],symbols)),z)
            difference=source_cap-candidate
            if not difference.is_zero:
                # A coefficient nonzero throughout the parameter domain rules
                # out accidental equality for a special positive height/radius.
                if any(c.is_nonzero is True for c in difference.all_coeffs()):return False
                raise ValueError('section comparison is unresolved for some parameters')
            bounds=[_parse(a,symbols) for a in solid['axial_interval']]
            if any(z in a.free_symbols for a in bounds):raise ValueError('candidate axial bounds cannot depend on the axis')
            _positive(bounds[1]-bounds[0])
            if any(not _zero(a-b) for a,b in zip((low,high),bounds)):raise ValueError('matching axial domains were not proved')
            return True
        if solid['kind']=='polyhedral_sections':
            # A generic nonzero polygon edge is affine in t, so its curvature
            # numerator is zero on an open edge. The interior circular section
            # of the sweep has strictly positive curvature at every point.
            a,b,l,q,t=S.symbols('_a _b _l _q _t',real=True)
            edge=S.Matrix([a+t*l*S.cos(q),b+t*l*S.sin(q)])
            v=edge.diff(t);acc=v.diff(t)
            if not _zero(v[0]*acc[1]-v[1]*acc[0]):raise ValueError('polygon-edge certificate failed')
            middle=radius.subs(z,(low+high)/2);_positive(middle**2)
            return False
        raise ValueError('unknown swept-solid representation')
    return select_unique(spec['options'],check)


def _chart(chart,symbols):
    parameters=chart['parameters']
    if len(parameters)!=len(set(parameters)) or len(parameters)>3 or any(p not in symbols for p in parameters):raise ValueError('invalid chart parameter list')
    if chart['kind']=='regular_curve':
        if len(parameters)!=1:raise ValueError('regular curve has one local parameter')
        t=symbols[parameters[0]]
        # Every regular C1 curve has locally a coordinate with nonzero
        # derivative. Reparameterize by that coordinate; f,g remain arbitrary.
        value=S.Matrix([t,S.Function('_f',real=True)(t),S.Function('_g',real=True)(t)])
    elif chart['kind']=='explicit':value=_vector(chart['coordinates'],symbols,3)
    else:raise ValueError('unknown smooth-chart constructor')
    if parameters:
        _box_domain(parameters,chart['bounds'],symbols)
        dimension=_rank(value.jacobian([symbols[p] for p in parameters]))
    else:dimension=0
    return dimension


def sweep_dimensions(spec):
    symbols=_symbols(spec['symbols'])
    def dimensions(obj):return [_chart(obj['initial'],symbols),_chart(obj['sweep'],symbols)]
    if spec['query']=='classify':
        actual=dimensions(spec['motion'])
        def check(option):
            pair=option['dimensions']
            if len(pair)!=2 or any(type(n)is not int or not 0<=n<=3 for n in pair):raise ValueError('invalid proposed dimensions')
            return pair==actual
    elif spec['query']=='select':
        target=spec['dimensions']
        if len(target)!=2 or any(type(n)is not int or not 0<=n<=3 for n in target):raise ValueError('invalid target dimensions')
        def check(option):return dimensions(option['motion'])==target
    else:raise ValueError('unknown dimension query')
    return select_unique(spec['options'],check)


def first_collinearity(spec):
    t=S.Symbol('_theta',real=True)
    initial=S.Matrix([1,0]);terminal=S.Matrix([S.cos(t),S.sin(t)])
    cross=S.det(S.Matrix.hstack(initial,terminal))
    roots=S.solveset(cross,t,domain=S.Interval.open(0,S.pi))
    if roots!=S.S.EmptySet or S.simplify(cross.subs(t,S.pi))!=0:raise ValueError('first positive collinearity was not proved')
    angle=S.Integer(180)
    def check(option):
        if 'degrees' in option:return angle==number(option['degrees'])
        low,high=map(number,option['interval'])
        if low>=high:raise ValueError('empty angle class')
        return bool(low<angle<high)
    return select_unique(spec['options'],check)


def _angle(angle):
    symbols={};vertex=_vector(angle['vertex'],symbols,2)
    rays=[_vector(v,symbols,2) for v in angle['rays']]
    if len(rays)!=2:raise ValueError('two ray directions required')
    norms=[_positive(v.dot(v)) for v in rays]
    cross=S.simplify(rays[0][0]*rays[1][1]-rays[0][1]*rays[1][0])
    if cross.is_nonzero is not True:raise ValueError('proper noncollinear ordinary angle required')
    unit=[v/S.sqrt(n) for v,n in zip(rays,norms)]
    return vertex,unit,S.simplify(unit[0].dot(unit[1]))


def _same_vector(a,b):return all(_zero(x-y) for x,y in zip(a,b))


def _vertical(a,b):
    va,ra,_=_angle(a);vb,rb,_=_angle(b)
    if not _same_vector(va,vb):return False
    return ((_same_vector(ra[0],-rb[0]) and _same_vector(ra[1],-rb[1])) or
            (_same_vector(ra[0],-rb[1]) and _same_vector(ra[1],-rb[0])))


def _adjacent(a,b):
    va,ra,_=_angle(a);vb,rb,_=_angle(b)
    if not _same_vector(va,vb):return False
    return any(_same_vector(ra[i],rb[j]) and _same_vector(ra[1-i],-rb[1-j]) for i in (0,1) for j in (0,1))


def _vertical_certificate():
    a,b,c,d=S.symbols('_a _b _c _d',real=True)
    u=S.Matrix([a,b]);v=S.Matrix([c,d])
    # These identities hold on the nonempty domain det(u,v)!=0. Thus all
    # denominators are positive and principal cosines determine equal angles.
    if not _zero(u.dot(v)-(-u).dot(-v)) or not _zero(u.dot(u)-(-u).dot(-u)) or not _zero(v.dot(v)-(-v).dot(-v)):
        raise ValueError('opposite-ray cosine identity failed')
    return True


def _equal_not_vertical(witness,require_right=False):
    first,second=witness;_,_,a=_angle(first);_,_,b=_angle(second)
    if not _zero(a-b) or _vertical(first,second):raise ValueError('not a counterexample to equal-implies-vertical')
    if require_right and (a!=0 or b!=0):raise ValueError('the stated counterexample requires two right angles')
    return True


def _angle_statement(statement):
    claim=statement['claim']
    if claim=='vertical_equal':return _vertical_certificate()
    if claim=='equal_implies_vertical':_equal_not_vertical(statement['counterexample']);return False
    if claim in ('transversal','parallel_transversal'):
        premises=list(ANGLE_DOMAIN)
        if claim=='parallel_transversal':premises.append({'left':'p','op':'=','right':'q'})
        conclusion=_angle_relation(statement['angles'],statement['relation'])
        if implies(premises,conclusion):return True
        p,q=map(number,statement['counterexample'])
        if not -90<p<90 or not -90<q<90 or (claim=='parallel_transversal' and p!=q):raise ValueError('illegal directional counterexample')
        values={'p':str(p),'q':str(q)}
        def value(expr):
            for name,replacement in values.items():expr=re.sub(r'\b'+name+r'\b','('+replacement+')',expr)
            return number(expr)
        if conclusion['op']!='=' or value(conclusion['left'])==value(conclusion['right']):raise ValueError('counterexample does not violate the conclusion')
        return False
    raise ValueError('unknown geometric proposition')


def angle_propositions(spec):
    return sum(_angle_statement(s) for s in spec['statements'])


def equal_angle_converse(spec):
    _equal_not_vertical(spec['counterexample'])
    def check(option):
        claim=option['claim']
        if claim=='equal_implies_vertical':return False
        if claim=='deny_using_vertical_inequality':return not _vertical_certificate()
        if claim=='deny_with_right_angle_counterexample':return _equal_not_vertical(option['counterexample'],True)
        raise ValueError('unknown converse/reason claim')
    return select_unique(spec['options'],check)


def adjacent_angle_claims(spec):
    theta=S.Symbol('_theta',real=True)
    common=S.Matrix([S.cos(theta),S.sin(theta)]);first=S.Matrix([1,0]);last=-first
    if not _zero(common.dot(common)-1) or not _zero(first.dot(common)-S.cos(theta)) or not _zero(common.dot(last)-S.cos(S.pi-theta)):
        raise ValueError('the common-ray/opposite-ray neighbor identity failed')
    ambient=[{'left':'t','op':'>','right':'0'},{'left':'t','op':'<','right':'180'}]
    def check(option):
        claim=option['claim']
        if claim=='neighbor_relation':
            relation=option['relation']
            conclusion={'left':'t','op':'=','right':'180-t'} if relation=='equal' else {
                'left':'t+(180-t)','op':'=','right':str({'supplementary':180,'complementary':90}[relation])}
            if implies(ambient,conclusion):return True
            witness=number(option['counterexample_degrees'])
            if not 0<witness<180:raise ValueError('invalid adjacent-angle witness')
            left=number(conclusion['left'].replace('t','('+str(witness)+')'));right=number(conclusion['right'].replace('t','('+str(witness)+')'))
            if left==right:raise ValueError('the witness does not refute the relation')
            return False
        if claim=='supplementary_implies_adjacent':
            first,second=option['counterexample'];_,_,a=_angle(first);_,_,b=_angle(second)
            if not _zero(a+b) or _adjacent(first,second):raise ValueError('illegal nonadjacent supplementary witness')
            return False
        raise ValueError('unknown adjacent-angle proposition')
    return select_unique(spec['options'],check)


def angle_notation(spec):
    def named(name):
        if not re.fullmatch('[A-Z]{3}',name) or len(set(name))!=3:raise ValueError('a proper three-point angle name is required')
        return name[1],frozenset((name[0],name[2]))
    def check(option):
        claim=option['claim']
        if claim=='different_named_angles':return named(option['names'][0])!=named(option['names'][1])
        if claim=='vertex':return named(option['name'])[0]==option['vertex']
        if claim=='uppercase_count':
            count=option['count']
            if type(count)is not int or count<0:raise ValueError('integer notation count required')
            return len(re.findall('[A-Z]',option['notation']))==count
        if claim=='all_single_vertex_names_unambiguous':
            witness=option['counterexample'];diagram={name:_vector(p,{},2) for name,p in witness['points'].items()}
            objects=[]
            for name in witness['names']:
                vertex,_=named(name)
                if any(label not in diagram for label in name):raise ValueError('undefined diagram point')
                rays=[diagram[name[i]]-diagram[vertex] for i in (0,2)]
                obj={'vertex':[str(x) for x in diagram[vertex]],'rays':[[str(x) for x in v] for v in rays]}
                _,unit,_=_angle(obj);objects.append((vertex,unit))
            if len(objects)<2 or any(v!=objects[0][0] for v,_ in objects):raise ValueError('one vertex and multiple proper angles required')
            a,b=objects[0][1],objects[1][1]
            same=(_same_vector(a[0],b[0]) and _same_vector(a[1],b[1])) or (_same_vector(a[0],b[1]) and _same_vector(a[1],b[0]))
            if same:raise ValueError('the supplied labels do not exhibit ambiguity')
            return False
        raise ValueError('unknown angle-notation proposition')
    return select_unique(spec['options'],check)


def decimal_claims(spec):
    base=spec['base']
    if type(base)is not int or not 2<=base<=16:raise ValueError('reviewed integer positional base required')
    def periodic_rationality():
        i,f,p=S.symbols('_i _f _p',integer=True);m=S.Symbol('_m',integer=True,nonnegative=True);k=S.Symbol('_k',integer=True,positive=True)
        denominator=base**m*(base**k-1)
        if denominator.is_positive is not True:raise ValueError('periodic denominator is not positive')
        value=i+f/base**m+p/denominator
        if value.is_rational is not True:raise ValueError('general periodic expansion rationality unresolved')
        n=S.Symbol('_n',integer=True,positive=True)
        if S.limit(base**(-k*n),n,S.oo)!=0:raise ValueError('geometric-series tail did not vanish')
        return True
    def check(option):
        claim=option['claim']
        if claim=='irrationals_are_nonterminating_nonperiodic':return periodic_rationality()
        if claim=='all_infinite_decimals_irrational':
            w=option['counterexample'];m=w['prefix_length'];k=w['period_length']
            if type(m)is not int or type(k)is not int or not 0<=m<=12 or not 1<=k<=12:raise ValueError('bounded nonempty repeating block required')
            i,f,p=[number(w[name]) for name in ('integer','prefix','period')]
            if any(v.denominator!=1 for v in (i,f,p)) or not 0<=f<base**m or not 0<p<base**k:raise ValueError('illegal positional digits')
            value=i+f/Fraction(base)**m+p/(Fraction(base)**m*(base**k-1));q=value.denominator
            # A reduced rational terminates iff all denominator primes divide
            # the positional base. Repeated gcd stripping is exact.
            while True:
                divisor=S.igcd(q,base)
                if divisor==1:break
                q//=int(divisor)
            if q==1:raise ValueError('the witness has a terminating expansion')
            return False
        if claim=='all_radical_expressions_irrational':
            raw=option['counterexample'];tree=ast.parse(raw,mode='eval')
            if not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='sqrt' for n in ast.walk(tree)):
                raise ValueError('a genuine radical-expression witness is required')
            value=_parse(raw,{})
            if value.is_rational is not True:raise ValueError('the radical witness is not proved rational')
            return False
        if claim=='irrational_addition_closed':
            values=[_parse(x,{}) for x in option['counterexample']]
            if len(values)!=2 or any(v.is_rational is not False for v in values) or S.simplify(sum(values)).is_rational is not True:
                raise ValueError('two irrational summands with rational sum were not proved')
            return False
        raise ValueError('unknown positional-number statement')
    return select_unique(spec['options'],check)


def real_axis_claims(spec):
    a,b,t=S.symbols('_a _b _t',real=True);u=S.Symbol('_u',positive=True);s=S.Symbol('_s',real=True)
    d=S.Matrix([S.cos(t),S.sin(t)]);origin=S.Matrix([a,b]);image=origin+u*s*d
    inverse=S.trigsimp((image-origin).dot(d)/u)
    if inverse!=s or not _zero(d.dot(d)-1):raise ValueError('full real-axis affine inverse failed')
    def check(option):
        claim=option['claim']
        if claim=='coordinate_bijection':return True # established above for every real origin/direction and u>0
        if claim=='all_coordinates_rational':
            value=_parse(option['counterexample'],{})
            if value.is_real is not True or value.is_rational is not False:raise ValueError('a real irrational coordinate witness is required')
            return False
        if claim=='real_sign_partition':
            signs=option['signs']
            if any(type(n)is not int or n not in (-1,0,1) for n in signs) or len(set(signs))!=len(signs):raise ValueError('invalid proposed partition')
            formula=' or '.join('x'+{-1:'<',0:'==',1:'>'}[n]+'0' for n in signs) or 'False'
            return _formula_equivalent(formula,'True')
        if claim=='number_class':
            value=_parse(option['value'],{})
            if value.is_rational is True:actual='rational'
            elif value.is_real is True and value.is_rational is False:actual='irrational'
            else:raise ValueError('number classification is unresolved')
            if option['number_class'] not in ('rational','irrational','neither'):raise ValueError('unknown number class')
            return actual==option['number_class']
        raise ValueError('unknown real-axis statement')
    return select_unique(spec['options'],check)


def canonical_product(source):
    if not isinstance(source,str) or len(source)>160:raise ValueError('bounded notation source required')
    if re.search(r'\d\s+\d',source):raise ValueError('ambiguous digit-separated whitespace')
    normalized=source.replace('×','*').replace('÷','/')
    tree=ast.parse(_source(normalized),mode='eval').body
    def product(node):
        coefficient=1;letters=[]
        def visit(n):
            nonlocal coefficient
            if isinstance(n,ast.Constant) and type(n.value)is int:coefficient*=n.value;return
            if isinstance(n,ast.Name) and re.fullmatch('[a-z]',n.id):
                if n.id in letters:raise ValueError('repeated-letter/power notation is outside this formatter')
                letters.append(n.id);return
            if isinstance(n,ast.UnaryOp) and isinstance(n.op,ast.USub):coefficient*=-1;visit(n.operand);return
            if isinstance(n,ast.BinOp) and isinstance(n.op,ast.Mult):visit(n.left);visit(n.right);return
            raise ValueError('notation formatter supports integer-coefficient products only')
        visit(node)
        if not coefficient:return '0'
        prefix='' if coefficient==1 and letters else '-' if coefficient==-1 and letters else str(coefficient)
        return prefix+''.join(letters)
    if isinstance(tree,ast.BinOp) and isinstance(tree.op,ast.Div):
        numerator=product(tree.left);denominator=product(tree.right)
        if denominator=='0':raise ValueError('zero denominator')
        if len(denominator)>1:denominator='('+denominator+')'
        return numerator+'/'+denominator
    return product(tree)


def notation_format(spec):
    def check(option):
        raw=option['expression']
        # Whitespace is not a style error; multiplication/division glyphs are.
        return re.sub(r'\s+','',raw)==canonical_product(raw)
    return select_unique(spec['options'],check)


def ruler_construction(spec):
    symbols=_symbols(spec['symbols']);p=_parse(spec['point'][0],symbols);h=_positive(_parse(spec['point'][1],symbols))
    point=S.Matrix([p,h]);baseline=S.Matrix([1,0])
    def check(option):
        plan=option['plan']
        if plan=='aligned_leg_slide':
            vertices=[_vector(v,symbols,2) for v in option['triangle']]
            if len(vertices)!=3:raise ValueError('three ruler vertices required')
            a,b=vertices[1]-vertices[0],vertices[2]-vertices[0]
            _positive(a.dot(a));_positive(b.dot(b))
            if not _zero(a.dot(b)) or not _zero(a[1]) or not _zero(b[0]):raise ValueError('aligned right-angle legs were not proved')
            t=S.Symbol('_slide',real=True);origin=S.Matrix([t,0])
            incidence=S.expand((point-origin)[0]*b[1]-(point-origin)[1]*b[0])
            solutions=S.solve(incidence,t)
            if len(solutions)!=1 or solutions[0].is_real is not True:raise ValueError('slide-to-point was not solved exactly')
            if not _zero(incidence.subs(t,solutions[0])):raise ValueError('point incidence failed')
            return _zero(b.dot(baseline))
        if plan=='draw_in_aligned_hypotenuse_direction':
            direction=baseline
            return _zero(direction.dot(baseline))
        if plan=='approximate_right_angle':
            epsilon=S.Symbol('_epsilon',real=True)
            low,high=[_parse(v,symbols) for v in option['tolerance_interval']]
            if low!=0 or high.is_positive is not True or S.simplify(S.pi-high).is_positive is not True:
                raise ValueError('positive sub-pi angle tolerance required')
            # delta=pi/2-epsilon/2 lies within every positive tolerance,
            # but its dot product with the baseline is sin(epsilon/2)!=0.
            roots=S.solveset(S.sin(epsilon/2),epsilon,domain=S.Interval.open(0,high))
            if roots!=S.S.EmptySet:raise ValueError('nonperpendicular allowed direction was not proved')
            return False
        if plan=='acute_vertex_draw_hypotenuse':
            vertices=[_vector(v,symbols,2) for v in option['counterexample']]
            if len(vertices)!=3 or not _same_vector(vertices[0],point):raise ValueError('the acute vertex must be P')
            a,b,c=vertices
            if not _zero((a-c).dot(b-c)):raise ValueError('counterexample ruler has no right angle')
            _positive((b-a).dot(c-a));_positive((b-a).dot(b-a))
            if _zero((b-a).dot(baseline)):raise ValueError('counterexample hypotenuse is perpendicular after all')
            return False
        raise ValueError('unknown ruler construction plan')
    return select_unique(spec['options'],check)


def shortest_canal(spec):
    symbols=_symbols(spec['symbols']);p=_parse(spec['point'][0],symbols);h=_positive(_parse(spec['point'][1],symbols))
    point=S.Matrix([p,h]);t=S.Symbol('_endpoint',real=True);endpoint=S.Matrix([t,0])
    squared=S.expand((point-endpoint).dot(point-endpoint));minimum=h*h;gap=S.factor(squared-minimum)
    if not _zero(gap-(t-p)**2) or gap.is_nonnegative is not True:raise ValueError('global perpendicular-distance minimum failed')
    def check(option):
        plan=option['plan']
        if plan=='orthogonal_projection':
            foot=point-S.Matrix([0,point[1]])
            if foot[1]!=0 or not _zero((point-foot).dot(S.Matrix([1,0]))):raise ValueError('foot construction failed')
            return _zero(squared.subs(t,foot[0])-minimum)
        if plan in ('all_endpoints_equal_length','arbitrary_endpoint_is_minimum'):
            # The legal point t=p+1 is on the bank and has squared gap 1.
            difference=S.simplify(gap.subs(t,p+1))
            _positive(difference);return False
        if plan=='parallel_to_bank':
            # Every point of the proposed canal has y=h>0, hence never reaches y=0.
            _positive(point[1]);return False
        raise ValueError('unknown canal plan')
    return select_unique(spec['options'],check)


HANDLERS={
    'f105_cylinder_unroll':cylinder_unroll,'f105_affine_dimensions':affine_dimensions,
    'f105_cylinder_projection':cylinder_projection,'f105_revolution':revolution,
    'f105_sweep_dimensions':sweep_dimensions,'f105_first_collinearity':first_collinearity,
    'f105_angle_propositions':angle_propositions,'f105_equal_angle_converse':equal_angle_converse,
    'f105_adjacent_angle_claims':adjacent_angle_claims,'f105_angle_notation':angle_notation,
    'f105_decimal_claims':decimal_claims,'f105_real_axis_claims':real_axis_claims,
    'f105_notation_format':notation_format,
    'f105_ruler_construction':ruler_construction,'f105_shortest_canal':shortest_canal,
}
