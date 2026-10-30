"""Typed implication signatures and general affine projection classifications.

Definitions/claims are mathematical object trees, not option verdicts. The
geometric lemmas are proved on full parameter domains; finite matrix worlds
only establish strict class refinement or refute a broader classification.
"""
import json
import re
import sympy as S
from sympy.calculus.util import function_range
from model_types import select_unique


def identifier(value):
    if not isinstance(value,str) or not re.fullmatch('[a-z]',value):raise ValueError('single-letter geometric identifier required')
    return value


def _predicate(node,budget=None):
    if budget is None:budget=[0]
    budget[0]+=1
    if budget[0]>50 or not isinstance(node,dict):raise ValueError('bounded typed predicate required')
    op=node.get('op')
    if op in ('implies','iff','equal'):
        if set(node)!={'op','left','right'}:raise ValueError('binary predicate structure required')
        left,right=_predicate(node['left'],budget),_predicate(node['right'],budget)
        if op in ('iff','equal'):left,right=sorted((left,right),key=repr)
        return op,left,right
    if op=='member':
        if set(node)!={'op','point','set'}:raise ValueError('typed set membership required')
        return op,identifier(node['point']),_predicate(node['set'],budget)
    if op=='internal_angle_bisector':
        if set(node)!={'op','angle'} or len(node['angle'])!=3:raise ValueError('a three-point angle required')
        a,o,b=map(identifier,node['angle']);a,b=sorted((a,b))
        return op,a,o,b
    if op in ('angle','distance_to_line'):
        key='points' if op=='angle' else 'line';allowed={'op',key} if op=='angle' else {'op','point','line'}
        if set(node)!=allowed:raise ValueError('typed geometric measurement required')
        args=node[key]
        if not isinstance(args,list) or len(args)!=(3 if op=='angle' else 2):raise ValueError('invalid geometric arity')
        args=tuple(identifier(v) for v in args)
        if len(set(args))!=len(args):raise ValueError('degenerate defining labels')
        if op=='angle':
            a,o,b=args;a,b=sorted((a,b));return op,a,o,b
        return op,identifier(node['point']),tuple(sorted(args))
    raise ValueError('unknown predicate or formula type')


def angle_criterion_signature(spec):
    context=spec['context'];a,o,b=map(identifier,context['angle']);p=identifier(context['point'])
    domain=context.get('full_angle_domain')
    if (not isinstance(domain,dict) or set(domain)!={'kind','lower','upper'}
            or domain.get('kind')!='open_interval' or type(domain.get('lower'))is not int or type(domain.get('upper'))is not int
            or domain.get('lower')!=0 or domain.get('upper')!=180 or len({a,o,b,p})!=4
            or context.get('point_region')!='strict_interior'
            or context.get('distance')!='perpendicular_to_supporting_lines'):
        raise ValueError('explicit open ordinary-angle/interior/supporting-line domain required')
    membership={'op':'member','point':p,'set':{'op':'internal_angle_bisector','angle':[a,o,b]}}
    equal_angles={'op':'equal','left':{'op':'angle','points':[a,o,p]},'right':{'op':'angle','points':[p,o,b]}}
    equal_distances={'op':'equal','left':{'op':'distance_to_line','point':p,'line':[o,a]},'right':{'op':'distance_to_line','point':p,'line':[o,b]}}
    imp=lambda x,y:{'op':'implies','left':x,'right':y}
    known=[imp(membership,equal_distances),imp(equal_distances,membership),{'op':'iff','left':membership,'right':equal_angles}]
    # Full nondegenerate angle domain: full angle2t in(0,pi), radial r>0,
    # directionphi in(0,2t). Equal distances factor into
    # 2r cos(t) sin(phi-t)=0. cos(t)>0; phi-t∈(-pi/2,pi/2) has only zero0.
    t,phi,delta=S.symbols('t p d',real=True)
    factor=S.sin(phi)-S.sin(2*t-phi)-2*S.cos(t)*S.sin(phi-t)
    if S.trigsimp(S.expand_trig(factor))!=0:raise ValueError('distance-factorization proof failed')
    cosine_range=function_range(S.cos(t),t,S.Interval.open(0,S.pi/2))
    if cosine_range.inf!=0 or not cosine_range.left_open:raise ValueError('strict positive cosine unproved')
    zeros=S.solveset(S.sin(delta),delta,domain=S.Interval.open(-S.pi/2,S.pi/2))
    if zeros!=S.FiniteSet(0):raise ValueError('bisector angle uniqueness unproved')
    if S.solve(phi-(2*t-phi),phi)!=[t] or S.simplify((S.sin(phi)-S.sin(2*t-phi)).subs(phi,t))!=0:
        raise ValueError('angle definition/property direction unproved')
    schemas=[_predicate(n) for n in known];source=_predicate(spec['theorem'])
    if source not in schemas:raise ValueError('the supplied theorem is not one of the proved signatures')
    def check(option):
        candidate=_predicate(option['signature'])
        if candidate not in schemas:raise ValueError('unverified definition/theorem signature')
        return candidate==source
    return select_unique(spec['options'],check)


def _zero(expression):
    value=S.factor(S.cancel(expression))
    if value==0:return True
    if value.is_zero is False:return False
    raise ValueError('exact scalar equality is unresolved')


def _matrix_equal(left,right):
    if left.shape!=right.shape:raise ValueError('matrix dimensions differ')
    differences=[S.factor(S.cancel(v)) for v in left-right]
    if all(v==0 for v in differences):return True
    norm=S.factor(S.cancel(sum(v*v for v in differences)))
    if norm.is_positive is True:return False
    raise ValueError('matrix equality/non-equality unproved on whole parameter chart')


def _self_adjoint_characterization(n):
    """Onn·d!=0, P=Pᵀ iff d is a nonzero multiple of the normaln.

    P-Pᵀ=(ndᵀ-dnᵀ)/(n·d). A nonzero normal component permits exact
    elimination of the wedge equations, forcing d=(d_j/n_j)n. Transversality
    then excludes the zero multiplier. No sampled direction proves this lemma.
    """
    pivot=next((i for i in range(3) if n[i].is_zero is False),None)
    if pivot is None:raise ValueError('a nonzero normal chart component required')
    direction=S.Matrix(S.symbols('x y z',real=True))
    equations=[direction[i]*n[pivot]-n[i]*direction[pivot] for i in range(3) if i!=pivot]
    indices=[i for i in range(3) if i!=pivot]
    solutions=S.linsolve(equations,[direction[i] for i in indices])
    if len(solutions)!=1:raise ValueError('normal-direction characterization unresolved')
    solved=direction.copy()
    for i,value in zip(indices,next(iter(solutions))):solved[i]=value
    scale=solved[pivot]/n[pivot]
    if any(not _zero(v) for v in solved-scale*n):raise ValueError('self-adjoint wedge equations do not imply parallel direction')
    if not _zero(n.dot(solved)-scale*n.dot(n)):raise ValueError('nonzero normal-multiplier implication unproved')
    return True


def _case(n,d,offset,tangent):
    denominator=S.factor(n.dot(d));normal_squared=S.factor(n.dot(n))
    if normal_squared.is_positive is not True or denominator.is_zero is not False:raise ValueError('nonzero normal/transverse direction unproved')
    p=(S.eye(3)-d*n.T/denominator).applyfunc(S.cancel);shift=(d*offset/denominator).applyfunc(S.cancel)
    if not _matrix_equal(p*p,p) or not _matrix_equal(p*d,S.zeros(3,1)) or not _matrix_equal(n.T*p,S.zeros(1,3)):
        raise ValueError('parallel projection construction failed')
    if not _matrix_equal(p*shift,S.zeros(3,1)) or not _zero(n.dot(shift)-offset):raise ValueError('affine plane/offset conditions failed')
    trace=S.simplify(S.trace(p))
    if trace!=2:raise ValueError('projection rank2 unproved')
    # Idempotence implies diagonalizability with eigenvalues0/1; rank=trace2.
    if tangent.dot(tangent).is_positive is not True or not _zero(n.dot(tangent)) or not _matrix_equal(p*tangent,tangent):raise ValueError('independent plane fibre unproved')
    # Fibres through0 andtangent are disjoint: iftangent=alpha*d then
    # n·tangent=0 andn·d!=0 implyalpha=0, contradicting|tangent|²>0.
    return {'matrix':p,'direction':d,'rank':2,'normal':n,'tangent':tangent}


def _term(node,case,budget=None):
    if budget is None:budget=[0]
    budget[0]+=1
    if budget[0]>40 or not isinstance(node,dict):raise ValueError('bounded matrix term required')
    op=node.get('op')
    if op=='linear_part' and set(node)=={'op'}:return case['matrix']
    if op=='transpose' and set(node)=={'op','argument'}:return _term(node['argument'],case,budget).T
    if op=='multiply' and set(node)=={'op','left','right'}:return _term(node['left'],case,budget)*_term(node['right'],case,budget)
    raise ValueError('unknown projection matrix term')


def _requirement(node,case):
    if not isinstance(node,dict):raise ValueError('mathematical class requirement required')
    op=node.get('op')
    if op in ('matrix_equal','matrix_not_equal'):
        if set(node)!={'op','left','right'}:raise ValueError('binary matrix relation required')
        equal=_matrix_equal(_term(node['left'],case),_term(node['right'],case))
        return equal if op=='matrix_equal' else not equal
    if op=='rank':
        if set(node)!={'op','value'} or type(node['value'])is not int or not 0<=node['value']<=3:raise ValueError('exact matrix rank required')
        return case['rank']==node['value']
    if op=='parallel_fibres' and set(node)=={'op'}:
        # The construction proves the nonzero direction spans the1D kernel.
        return _matrix_equal(case['matrix']*case['direction'],S.zeros(3,1)) and case['rank']==2
    if op=='finite_fibre_concurrency' and set(node)=={'op'}:
        # _case proves two fibres disjoint on the full chart, so the entire
        # family cannot have a finite common point.
        return False
    raise ValueError('unknown projection class predicate')


def _key(requirement):
    node=dict(requirement)
    if node.get('op') in ('matrix_equal','matrix_not_equal'):
        left,right=sorted((node['left'],node['right']),key=lambda n:json.dumps(n,sort_keys=True))
        node['left'],node['right']=left,right
    return json.dumps(node,sort_keys=True,separators=(',',':'))


def most_specific_projection(spec):
    if (spec.get('normal_domain')!='all_nonzero_real_normals' or spec.get('direction')!='nonzero_normal_multiple'
            or spec.get('plane_offset_domain')!='all_real_offsets'):
        raise ValueError('general perpendicular-to-plane projection assumptions required')
    r=S.Symbol('r',real=True,nonzero=True);u,v,h=S.symbols('u v h',real=True);k=S.Symbol('k',real=True,nonzero=True)
    # Three disjoint coordinate charts cover every nonzero real normal:
    # nx!=0; nx=0,ny!=0; nx=ny=0,nz!=0. Offseth is arbitrary in each.
    charts=[(S.Matrix([r,u,v]),S.Matrix([-u,r,0])),
            (S.Matrix([0,r,u]),S.Matrix([0,-u,r])),
            (S.Matrix([0,0,r]),S.Matrix([1,0,0]))]
    for n,_ in charts:_self_adjoint_characterization(n)
    cases=[_case(n,k*n,h,t) for n,t in charts]
    # These two legal matrices only disprove class implications. They never
    # establish the all-normal/all-offset source classification above.
    n=S.Matrix([0,0,1]);t=S.Matrix([1,0,0])
    witnesses=[_case(n,S.Matrix([0,0,1]),S.Integer(0),t),
               _case(n,S.Matrix([1,0,1]),S.Integer(0),t)]
    requirements=[];eligible=[]
    for option in spec['options']:
        nodes=option['requirements']
        if not isinstance(nodes,list) or not nodes:raise ValueError('a nonempty class definition required')
        # Evaluate every predicate and every chart even when one fails.
        outcomes=[[_requirement(n,c) for n in nodes] for c in cases]
        requirements.append(nodes);eligible.append(all(all(row) for row in outcomes))
    relation=[{_key(n) for n in nodes} for nodes in requirements]
    def holds(nodes,case):return all([_requirement(n,case) for n in nodes])
    maximal=[]
    for i,nodes in enumerate(requirements):
        if not eligible[i]:continue
        refined=False
        for j,other in enumerate(requirements):
            if not eligible[j] or not relation[i]<relation[j]:continue
            if any(holds(nodes,w) and not holds(other,w) for w in witnesses):refined=True
            else:raise ValueError('strict class refinement has no legal separating projection')
        # A merely general name that still permits oblique fibres is not the
        # specialized name requested by the perpendicular source assumption.
        specialized=not holds(nodes,witnesses[1])
        if not refined and specialized:maximal.append(i)
    indices={id(o):i for i,o in enumerate(spec['options'])}
    return select_unique(spec['options'],lambda o:indices[id(o)] in maximal)


HANDLERS={'g43_angle_criterion_signature':angle_criterion_signature,
          'g43_most_specific_projection':most_specific_projection}
