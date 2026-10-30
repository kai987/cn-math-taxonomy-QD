"""Small exact proofs for the foundations follow-up audit.

Models consume mathematical objects/claims, not a question ID or answer key.
Universal affine claims use exact real feasibility; finite witnesses only
disprove universal statements. Unknown syntax/semantics never becomes False.
"""
import ast
from fractions import Fraction
from itertools import combinations
import re
import sympy as S

from model_types import select_unique
from models_algebra import feasible, implies, like_terms, number
from models_symbolic import parse_math, _equal, condition_set


def R(left,op,right):return {'left':str(left),'op':op,'right':str(right)}


def _dnf(source,negate=False):
    """Affine Boolean formulas as a union of conjunctions; != is split exactly."""
    source=source.replace('≤','<=').replace('≥','>=').replace('≠','!=')
    if len(source)>500:raise ValueError('oversized affine condition')
    tree=ast.parse(source,mode='eval').body
    comparisons={ast.Eq:'=',ast.NotEq:'!=',ast.Lt:'<',ast.LtE:'<=',ast.Gt:'>',ast.GtE:'>='}
    opposite={'=':'!=','!=':'=','<':'>=','<=':'>','>':'<=','>=':'<'}
    def combine(groups,conjunction):
        if not conjunction:return [branch for group in groups for branch in group]
        result=[[]]
        for group in groups:
            result=[a+b for a in result for b in group]
            if len(result)>256:raise ValueError('Boolean proof exceeds branch bound')
        return result
    def visit(node,neg):
        if isinstance(node,ast.Constant) and type(node.value) is bool:
            return [[]] if node.value!=neg else []
        if isinstance(node,ast.UnaryOp) and isinstance(node.op,ast.Not):return visit(node.operand,not neg)
        if isinstance(node,ast.BoolOp) and isinstance(node.op,(ast.And,ast.Or)):
            conjunction=isinstance(node.op,ast.And)!=neg
            return combine([visit(n,neg) for n in node.values],conjunction)
        if (isinstance(node,ast.Call) and isinstance(node.func,ast.Name)
                and node.func.id in ('And','Or') and not node.keywords and node.args):
            return combine([visit(n,neg) for n in node.args],(node.func.id=='And')!=neg)
        if isinstance(node,ast.Compare):
            pieces=[];left=node.left
            for operator,right in zip(node.ops,node.comparators):
                if type(operator) not in comparisons:raise ValueError('unsupported affine comparator')
                op=comparisons[type(operator)]
                if neg:op=opposite[op]
                l=ast.get_source_segment(source,left);r=ast.get_source_segment(source,right)
                pieces.append([[R(l,op,r)]] if op!='!=' else [[R(l,'<',r)],[R(l,'>',r)]])
                left=right
            return combine(pieces,not neg)
        raise ValueError('unsupported affine Boolean formula')
    result=visit(tree,negate)
    # Validate every branch, including branches later eliminated by a condition.
    for branch in result:feasible(branch)
    return result


def _formula_possible(source):return any(feasible(branch) for branch in _dnf(source))


def _formula_equivalent(left,right):
    def counterexample(a,b):
        return any(feasible(x+y) for x in _dnf(a) for y in _dnf(b,True))
    return not counterexample(left,right) and not counterexample(right,left)


def real_claims(spec):
    premises=spec.get('premises',[])
    def check(option):
        kind=option['claim']
        if kind=='forall_affine':return implies(premises,option['conclusion'])
        if kind=='each_sign_possible':
            variable=option['variable'];signs=option['signs']
            if not signs or len(set(signs))!=len(signs) or any(type(s)is not int or s not in (-1,0,1) for s in signs):
                raise ValueError('distinct numeric sign classes required')
            return all(feasible(premises+[R(variable,{-1:'<',0:'=',1:'>'}[s],0)]) for s in signs)
        if kind=='sign_partition':
            if option['domain'] not in ('integer','rational','real'):raise ValueError('unsupported ordered-number domain')
            signs=option['signs']
            if len(signs)!=len(set(signs)) or any(type(s)is not int or s not in (-1,0,1) for s in signs):raise ValueError('invalid partition')
            # Trichotomy is exhaustive for all reals and hence for Z and Q.
            # Each sign cell contains the integer -1, 0 or 1, so missing cells
            # really are nonempty in either discrete/dense number domain.
            formula=' or '.join('x'+{-1:'<',0:'==',1:'>'}[s]+'0' for s in signs) or 'False'
            return _formula_equivalent(formula,'True')
        if kind=='fraction_class':
            a=S.Symbol('p',integer=True);b=S.Symbol('q',integer=True,nonzero=True)
            value=a/b
            if value.is_rational is not True:raise ValueError('fraction rationality is unresolved')
            if option['number_class']=='rational':return True
            if option['number_class']=='not_rational':return False
            raise ValueError('unsupported fraction class')
        if kind=='numeric_sign':
            value=number(option['value']);sign=option['sign']
            if type(sign)is not int or sign not in (-1,0,1):raise ValueError('invalid sign')
            return (1 if value>0 else -1 if value<0 else 0)==sign
        raise ValueError('unsupported real-number claim')
    return select_unique(spec['options'],check)


def missing_axis_parameter(spec):
    known=spec['known']
    required={'origin','orientation','unit_length'}
    if set(known)-required:raise ValueError('unknown coordinate parameter')
    if 'orientation' in known and (type(known['orientation'])is not int or known['orientation'] not in (-1,1)):
        raise ValueError('nonzero orientation required')
    if 'unit_length' in known and number(known['unit_length'])<=0:raise ValueError('positive unit required')
    if 'origin' in known:number(known['origin'])
    missing=required-set(known)
    if len(missing)!=1:raise ValueError('the question does not determine exactly one missing parameter')
    def check(option):
        if option['parameter'] not in required:raise ValueError('unknown candidate coordinate parameter')
        return option['parameter'] in missing
    # x=o+orientation*unit_length*t is unique only when all three independent
    # parameters are fixed. Keeping o and orientation fixes no positive scale.
    return select_unique(spec['options'],check)


def reciprocal_claims(spec):
    x=S.Symbol('x',real=True);domain=S.Complement(S.S.Reals,S.FiniteSet(0))
    roots=S.Intersection(S.solveset(x*x-1,x,domain=S.S.Reals),domain)
    def check(option):
        kind=option['claim']
        if kind=='reciprocal_value':
            value=number(option['value'])
            return value!=0 and 1/value==number(option['reciprocal'])
        if kind=='fixed_points':
            candidate=S.FiniteSet(*(S.Rational(number(v)) for v in option['values']))
            return candidate==roots
        if kind=='forall_comparison':
            op=option['operator']
            if op not in ('<','<=','>','>=','==','!='):raise ValueError('unsupported reciprocal comparator')
            allowed=condition_set('1/x'+op+'x',x)
            missing=S.Complement(domain,allowed)
            if missing.is_empty is None:raise ValueError('reciprocal universal comparison is unresolved')
            return bool(missing.is_empty)
        raise ValueError('unknown reciprocal statement')
    return select_unique(spec['options'],check)


def polygon_quantity(spec):
    assumptions=spec.get('assumptions',{})
    def parsed(text):
        expression,conditions=parse_math(text,assumptions)
        if any(str(v) not in assumptions for v in expression.free_symbols):raise ValueError('undeclared polygon symbol')
        if any(S.simplify(c)is not S.true for c in conditions):raise ValueError('unproved polygon expression domain')
        return expression
    vertices=[S.Matrix([parsed(v) for v in p]) for p in spec['vertices']]
    if len(vertices)!=4 or any(len(p)!=2 for p in vertices):raise ValueError('the reviewed square family requires four planar vertices')
    edges=[vertices[(i+1)%4]-vertices[i] for i in range(4)]
    lengths=[S.simplify(e.dot(e)) for e in edges]
    if lengths[0].is_positive is not True or any(S.simplify(x-lengths[0])!=0 for x in lengths):
        raise ValueError('nondegenerate equal square sides were not proved')
    if any(S.simplify(edges[i].dot(edges[(i+1)%4]))!=0 for i in range(4)):
        raise ValueError('four right angles were not proved')
    source=parsed(spec['source'])
    def length(i,j):
        d=vertices[j]-vertices[i];return S.sqrt(S.expand(d.dot(d)))
    perimeter=sum(length(i,(i+1)%len(vertices)) for i in range(len(vertices)))
    area=S.Abs(sum(vertices[i][0]*vertices[(i+1)%len(vertices)][1]-vertices[(i+1)%len(vertices)][0]*vertices[i][1]
                   for i in range(len(vertices))))/2
    def check(option):
        quantity=option['quantity']
        if quantity=='area':value=area
        elif quantity=='perimeter':value=perimeter
        elif quantity=='segment':value=length(*option['vertices'])/number(option.get('divisor',1))
        else:raise ValueError('unknown polygon quantity')
        return _equal(source,value)
    return select_unique(spec['options'],check)


def monomial_claims(spec):
    def check(option):
        kind=option['claim']
        if kind=='pair_like':
            result=like_terms(option['left'],option['right'])
            if result and option.get('reason')=='same_letters_only':
                raise ValueError('letter-set equality alone is not a general exponent criterion')
            return result
        if kind=='all_constants_unlike':
            left,right=option['counterexample']
            number(left);number(right)
            if not like_terms(left,right):raise ValueError('the supplied constants do not disprove the claim')
            return False # one checked constant pair refutes this universal negative
        raise ValueError('unknown monomial proposition')
    return select_unique(spec['options'],check)


def degree_parameter_condition(spec):
    parameters=spec['parameters']
    if len(set(parameters+[spec['unknown']]))!=len(parameters)+1 or any(not re.fullmatch('[a-z]',x) for x in parameters+[spec['unknown']]):
        raise ValueError('distinct one-letter coefficient parameters and unknown required')
    unknown=S.Symbol(spec['unknown'],real=True)
    expression,constraints=parse_math(spec['expression'])
    if any(str(v) not in set(parameters+[spec['unknown']]) for v in expression.free_symbols):raise ValueError('undeclared coefficient symbol')
    if any(S.simplify(c)is not S.true for c in constraints):raise ValueError('unproved coefficient expression domain')
    polynomial=S.Poly(S.expand(expression),unknown)
    degree=spec['degree']
    if type(degree) is not int or degree<1 or degree>4:raise ValueError('unsupported target degree')
    if polynomial.is_zero or polynomial.degree()<degree:raise ValueError('target degree cannot occur')
    conditions=[]
    for power in range(degree+1,int(polynomial.degree())+1):conditions.append('('+str(polynomial.nth(power))+')==0')
    conditions.append('('+str(polynomial.nth(degree))+')!=0')
    target=' and '.join(conditions)
    if not _formula_possible(target):raise ValueError('target degree cannot occur')
    return select_unique(spec['options'],lambda o:_formula_equivalent(target,o['condition']))


def _interval(primitive):
    kind=primitive['kind'];a=number(primitive['a']);b=number(primitive['b'])
    if a==b:raise ValueError('two distinct defining points required')
    a,b=S.Rational(a),S.Rational(b)
    if kind=='line':return S.S.Reals
    if kind=='segment':return S.Interval(min(a,b),max(a,b))
    if kind=='ray':return S.Interval(a,S.oo) if b>a else S.Interval(-S.oo,a)
    raise ValueError('unknown affine primitive')


def primitive_claims(spec):
    target=_interval(spec['primitive']) if 'primitive' in spec else None
    def check(option):
        claim=option['claim']
        if claim in ('unbounded_directions','endpoint_count') and (type(option['count'])is not int or option['count']<0):
            raise ValueError('a proposed geometric count must be a nonnegative integer')
        if claim=='unbounded_directions':
            interval=_interval(option.get('primitive',spec.get('primitive')))
            return int(interval.inf==-S.oo)+int(interval.sup==S.oo)==option['count']
        if claim=='endpoint_count':
            if target is None:raise ValueError('target primitive needed')
            return int(target.inf!=-S.oo)+int(target.sup!=S.oo)==option['count']
        if claim=='same_as_target':return target==_interval(option['primitive'])
        if claim in ('same_set','different_set'):
            equal=_interval(option['first'])==_interval(option['second'])
            return equal if claim=='same_set' else not equal
        if claim=='finite_length':
            interval=_interval(option['primitive']);return interval.measure.is_finite is True
        raise ValueError('unknown affine-primitive claim')
    return select_unique(spec['options'],check)


def affine_order(spec):
    premises=spec['premises'];left=spec['left'];right=spec['right']
    if not feasible(premises):raise ValueError('inconsistent ordering assumptions')
    possible={op for op in ('<','=','>') if feasible(premises+[R(left,op,right)])}
    def check(option):
        op=option['operator']
        if op=='undetermined':return len(possible)>1
        if op not in ('<','=','>'):raise ValueError('unknown order query')
        return possible=={op}
    return select_unique(spec['options'],check)


def affine_reasoning(spec):
    ambient=spec.get('ambient',[]);given=ambient+spec['given']
    if not feasible(given):raise ValueError('inconsistent angle hypotheses')
    def check(option):
        if option['claim']=='undetermined':
            possible={op for op in ('<','=','>') if feasible(given+[R(spec['compare'][0],op,spec['compare'][1])])}
            return len(possible)>1
        if option['claim']!='explained_conclusion':raise ValueError('unknown reasoning claim')
        reasons=option['reasons'];conclusions=option['conclusions']
        if not reasons or not conclusions:raise ValueError('both reason and conclusion are required')
        if not all(implies(given,r) for r in reasons):return False
        if not feasible(ambient+reasons):raise ValueError('inconsistent supplied reason')
        return all(implies(ambient+reasons,c) for c in conclusions)
    return select_unique(spec['options'],check)


def line_relation_family(spec):
    if spec['plane_dimension']!=2:raise ValueError('direction parity proof requires a plane')
    graph={}
    for a,relation,b in spec['relations']:
        if relation not in ('parallel','perpendicular'):raise ValueError('unsupported direction relation')
        parity=int(relation=='perpendicular')
        graph.setdefault(a,[]).append((b,parity));graph.setdefault(b,[]).append((a,parity))
    first,second=spec['query'];orient={first:0};queue=[first]
    while queue:
        a=queue.pop()
        for b,p in graph.get(a,[]):
            value=orient[a]^p
            if b in orient and orient[b]!=value:raise ValueError('inconsistent nonzero line directions')
            if b not in orient:orient[b]=value;queue.append(b)
    if second not in orient:raise ValueError('no proved relation between queried directions')
    parity=orient[second]
    distinct={frozenset(pair) for pair in spec.get('distinct_pairs',[])}
    if not parity and frozenset((first,second)) not in distinct:
        raise ValueError('parallel directions may be coincident; distinctness was not established')
    def check(option):
        relation=option['relation']
        if relation=='parallel':return parity==0
        if relation=='perpendicular':return parity==1
        if relation=='intersect':return parity==1
        if relation=='intersect_nonperpendicular':return False
        if relation in ('coincident','undetermined'):return False
        raise ValueError('unknown line relation query')
    # In R², J(u,v)=(-v,u), J²=-I. Products by nonzero scalars do
    # not change a line direction; the graph stores precisely the parity of J.
    return select_unique(spec['options'],check)


def _slot(slot):
    vertex=slot['vertex'];region=slot['region'];side=slot['side']
    if vertex not in ('upper','lower') or region not in ('interior','exterior') or side not in ('left','right'):
        raise ValueError('unrecognized angle slot')
    sign=(1 if vertex=='upper' else -1)*(1 if region=='interior' else -1)*(1 if side=='right' else -1)
    variable='p' if vertex=='upper' else 'q'
    return '90'+('+' if sign>0 else '-')+variable


def _angle_relation(slots,relation):
    first,second=map(_slot,slots)
    if relation=='equal':return R(first,'=',second)
    if relation=='supplementary':return R('('+first+')+('+second+')','=',180)
    if relation=='complementary':return R('('+first+')+('+second+')','=',90)
    raise ValueError('unknown angle relation')


ANGLE_DOMAIN=[R(v,'>',-90) for v in ('p','q')]+[R(v,'<',90) for v in ('p','q')]


def angle_slot_classification(spec):
    first,second=spec['angles'];_slot(first);_slot(second)
    if first==second:raise ValueError('two different angles required')
    if first['vertex']==second['vertex']:
        actual='vertical' if first['region']!=second['region'] and first['side']!=second['side'] else 'linear_pair'
    elif first['region']==second['region']=='interior':
        actual='alternate_interior' if first['side']!=second['side'] else 'same_side_interior'
    elif first['region']!=second['region'] and first['side']==second['side']:actual='corresponding'
    else:raise ValueError('angle pair is outside the supported named classes')
    allowed={'vertical','linear_pair','alternate_interior','same_side_interior','corresponding'}
    def check(option):
        if option['angle_class'] not in allowed:raise ValueError('unknown named angle class')
        return option['angle_class']==actual
    return select_unique(spec['options'],check)


def parallel_angle_claims(spec):
    mode=spec['mode']
    def check(option):
        if len(option['angles'])!=2 or option['angles'][0]['vertex']==option['angles'][1]['vertex']:
            raise ValueError('transversal proof needs one angle at each crossing')
        relation=_angle_relation(option['angles'],option['relation'])
        if mode=='criterion':return implies(ANGLE_DOMAIN+[relation],R('p','=','q'))
        if mode=='property':return implies(ANGLE_DOMAIN+[R('p','=','q')],relation)
        raise ValueError('unsupported parallel angle proof direction')
    return select_unique(spec['options'],check)


def numeric_angle_lines(spec):
    if len(spec['angles'])!=2 or len(spec['measures'])!=2:raise ValueError('exactly two measured angle slots required')
    values=[]
    for slot,angle in zip(spec['angles'],spec['measures']):
        expression=_slot(slot);a=number(angle)
        if not 0<a<180:raise ValueError('a transverse angle must be strictly between 0 and 180')
        values.append((a-90)*(1 if '+' in expression else -1))
    if len(values)!=2 or spec['angles'][0]['vertex']==spec['angles'][1]['vertex']:
        raise ValueError('one measured angle at each crossing required')
    delta=values[0]-values[1]
    parallel=delta==0;perpendicular=abs(delta)==90
    def check(option):
        relation=option['relation']
        if relation=='parallel':return parallel
        if relation=='perpendicular':return perpendicular
        if relation=='intersect':return not parallel
        if relation=='undetermined':return False
        raise ValueError('unknown line relation')
    return select_unique(spec['options'],check)


def supplementary_quad(spec):
    labels=spec['vertices']
    if len(labels)!=4 or len(set(labels))!=4:raise ValueError('four cyclic vertex labels required')
    pair=spec['supplementary']
    normalized=None
    for start in range(4):
        order=labels[start:]+labels[:start]
        if set(pair)=={order[0],order[3]}:normalized=order;break
    if normalized is None:raise ValueError('the supplementary vertices must be adjacent')
    b,c,h=S.symbols('b c h',positive=True);shift=S.Symbol('s',real=True)
    points=dict(zip(normalized,[S.Matrix([0,0]),S.Matrix([b,0]),S.Matrix([shift+c,h]),S.Matrix([shift,h])]))
    def parallel(edge1,edge2):
        for edge in (edge1,edge2):
            if len(edge)!=2 or any(v not in points for v in edge) or edge[0]==edge[1]:raise ValueError('invalid edge')
        u=points[edge1[1]]-points[edge1[0]];v=points[edge2[1]]-points[edge2[0]]
        determinant=S.Poly(S.expand(u[0]*v[1]-u[1]*v[0]),b,c,h,shift)
        # A nonzero polynomial cannot vanish on the open positive b,c,h-domain.
        return bool(determinant.is_zero)
    def check(option):
        if option['claim']=='parallel_edges':return parallel(*option['edges'])
        if option['claim']=='parallelogram':
            a,bv,cv,d=normalized;return parallel([a,bv],[cv,d]) and parallel([a,d],[bv,cv])
        raise ValueError('unknown quadrilateral claim')
    # The supplementary adjacent interior angles first force the two opposite
    # edges parallel. Rigid motion/reflection then gives exactly this family;
    # b,c,h>0 with arbitrary real horizontal shift is precisely the
    # nondegenerate convex trapezoid order, not merely the right-trapezoid case.
    return select_unique(spec['options'],check)


def cubic_root_counts(spec):
    if spec['degree']!=3:raise ValueError('only the reviewed real cubic proof is supported')
    x,y=S.symbols('x y',real=True)
    quotient=S.cancel((y**3-x**3)/(y-x))
    matrix=S.hessian(quotient,(x,y))/2
    if matrix[0,0]<=0 or matrix.det()<=0:raise ValueError('strict cubic monotonicity was not proved')
    if S.expand((y-x)*quotient-(y**3-x**3))!=0:raise ValueError('incorrect difference factorization')
    if S.limit(x**3,x,S.oo)!=S.oo or S.limit(x**3,x,-S.oo)!=-S.oo:raise ValueError('cubic range was not proved')
    # Positive-definite quotient is positive except x=y=0. Hence x<y
    # implies x³<y³; continuity and the two limits give a bijection R -> R.
    def check(option):
        domain=option['domain']
        if domain not in ('real','positive','negative','zero'):raise ValueError('unsupported radicand domain')
        count=option['count']
        if type(count)is not int or count<0:raise ValueError('invalid proposed root count')
        return count==1
    return select_unique(spec['options'],check)


def _point(values):
    if len(values)!=2:raise ValueError('two-dimensional point required')
    return S.Point(*(S.Rational(number(v)) for v in values))


def parallel_axiom_claims(spec):
    if spec['plane_dimension']!=2:raise ValueError('this incidence proof is restricted to the stated plane')
    def check(option):
        claim=option['claim']
        if claim=='parallel_count':
            if type(option['count'])is not int or option['count']<0:raise ValueError('invalid proposed count')
            if option['point_domain']=='off_line':
                from models_symbolic import affine_incidence
                count=affine_incidence({'query':'parallel_through_point','plane_dimension':2,
                                        'given_direction_nonzero':True,'point_off_line':True})
                return count==option['count']
            if option['point_domain']=='all':
                witness=option['counterexample'];a,b=map(_point,witness['line']);p=_point(witness['point'])
                if a==b:raise ValueError('a nondegenerate counterexample line is required')
                line=S.Line(a,b)
                count=0 if line.contains(p) else 1
                if count==option['count']:raise ValueError('a witness cannot prove this universal count')
                return False
            raise ValueError('unknown point domain')
        if claim=='disjoint_segments_imply_parallel_lines':
            first,second=[S.Segment(*map(_point,pair)) for pair in option['counterexample']]
            if not isinstance(first,S.Segment2D) or not isinstance(second,S.Segment2D):raise ValueError('nondegenerate segments required')
            if first.intersection(second) or S.Line(first.p1,first.p2).is_parallel(S.Line(second.p1,second.p2)):
                raise ValueError('the supplied segments do not refute the universal claim')
            return False
        if claim=='common_parallel_implies_perpendicular':
            a,b,c=[S.Line(*map(_point,pair)) for pair in option['counterexample']]
            if not a.is_parallel(b) or not b.is_parallel(c) or a.is_perpendicular(c):
                raise ValueError('the supplied lines do not refute the universal claim')
            return False
        raise ValueError('unknown parallel-line proposition')
    return select_unique(spec['options'],check)


def translation_relations(spec):
    if spec['translation_domain']!='nonzero':raise ValueError('nonzero translation must be stated explicitly')
    x,y,a,b,u,v=S.symbols('x y a b u v',real=True)
    first=S.Matrix([x+u,y+v])-S.Matrix([x,y]);second=S.Matrix([a+u,b+v])-S.Matrix([a,b])
    determinant=S.expand(first[0]*second[1]-first[1]*second[0])
    norm_difference=S.expand(first.dot(first)-second.dot(second))
    def check(option):
        relation=option['relation']
        if relation=='parallel_or_collinear_and_equal':return determinant==0 and norm_difference==0
        if relation=='parallel_and_unequal':return determinant==0 and norm_difference!=0
        if relation=='always_perpendicular':
            dot=S.expand(first.dot(second))
            if S.expand(dot-u*u-v*v)!=0:raise ValueError('dot-product proof is unresolved')
            return False # u²+v²>0 on the explicit nonzero translation domain
        if relation=='always_one_intersection':
            witness=option['counterexample'];p,q=map(_point,witness['points']);t=_point(witness['vector'])
            if t==S.Point(0,0):raise ValueError('the counterexample translation must be nonzero')
            segments=[S.Segment(p,p+t),S.Segment(q,q+t)]
            intersection=segments[0].intersection(segments[1])
            if len(intersection)==1 and isinstance(intersection[0],S.Point2D):
                raise ValueError('the supplied example does not refute unique intersection')
            return False
        raise ValueError('unknown translation-segment relation')
    return select_unique(spec['options'],check)


def atan_interval(x,terms):
    x=Fraction(x)
    if not 0<x<1 or type(terms)is not int or not 1<=terms<=30:raise ValueError('bounded alternating atan series required')
    partial=sum(((-1)**k*x**(2*k+1)/Fraction(2*k+1) for k in range(terms)),Fraction(0))
    adjacent=partial+(-1)**terms*x**(2*terms+1)/Fraction(2*terms+1)
    return min(partial,adjacent),max(partial,adjacent)


def pi_interval(terms=6):
    a=Fraction(1,5);b=Fraction(1,239)
    twice=2*a/(1-a*a);four=2*twice/(1-twice*twice)
    if (four-b)/(1+four*b)!=1:raise ValueError('Machin tangent identity failed')
    # 0<4 atan(a)-atan(b)<4a<1<pi/2 selects the principal
    # tangent inverse. The lower bound atan(a)>a/(1+a²) gives positivity.
    if not 4*a/(1+a*a)-b>0 or not 4*a<1:raise ValueError('inverse-tangent branch not established')
    al,au=atan_interval(a,terms);bl,bu=atan_interval(b,terms)
    return 16*al-4*bu,16*au-4*bl


def pi_location(spec):
    lower,upper=pi_interval(spec.get('terms',6))
    def check(option):
        a,b=map(number,option['interval'])
        if a>=b:raise ValueError('nonempty candidate location interval required')
        if upper<=a or lower>=b:return False
        if not a<lower<upper<b:raise ValueError('pi bounds do not decide this interval')
        if 'approximation' in option:
            digits=option['decimal_places']
            if type(digits)is not int or not 0<=digits<=8:raise ValueError('unsupported rounding precision')
            approximate=number(option['approximation']);half=Fraction(1,2*10**digits)
            if (approximate*10**digits).denominator!=1:
                raise ValueError('the proposed approximation is not on the stated decimal grid')
            if upper<approximate-half or lower>approximate+half:return False
            if not approximate-half<lower<upper<approximate+half:
                raise ValueError('bounds do not prove the claimed nearest decimal')
        return True
    return select_unique(spec['options'],check)


HANDLERS={
    'f160_real_claims':real_claims,'f160_missing_axis_parameter':missing_axis_parameter,
    'f160_reciprocal_claims':reciprocal_claims,'f160_polygon_quantity':polygon_quantity,
    'f160_monomial_claims':monomial_claims,'f160_degree_parameter_condition':degree_parameter_condition,
    'f160_primitive_claims':primitive_claims,'f160_affine_order':affine_order,
    'f160_affine_reasoning':affine_reasoning,'f160_line_relation_family':line_relation_family,
    'f160_angle_slot_classification':angle_slot_classification,'f160_parallel_angle_claims':parallel_angle_claims,
    'f160_numeric_angle_lines':numeric_angle_lines,'f160_supplementary_quad':supplementary_quad,
    'f160_cubic_root_counts':cubic_root_counts,'f160_pi_location':pi_location,
    'f160_parallel_axiom_claims':parallel_axiom_claims,'f160_translation_relations':translation_relations,
}
