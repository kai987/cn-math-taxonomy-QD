"""Exact form, finite-set and proof-certificate checks for the final applications.

No answer keys, outcome flags, general-purpose evaluation or preference score
are inputs. Structural applicability is decided from a bounded mathematical
AST; finite witnesses only refute universals, never establish them.
"""
import ast
import re
from fractions import Fraction
import sympy as S
from exact_polynomial import _source, _parse
from model_types import select_unique
from models_algebra import number
from models_applications_105 import math, points, zero


class _NotSquareForm(Exception):pass


def _polynomial(source,variable):
    terms=_parse(source)
    if any(set(m)-{variable} for m in terms):raise ValueError('one declared variable required')
    return terms


def _constant(node,source,variable):
    polynomial=_polynomial(ast.get_source_segment(source,node),variable)
    if any(polynomial_key for polynomial_key in polynomial):return None
    return polynomial.get((),Fraction(0))


def _affine(node,source,variable):
    polynomial=_polynomial(ast.get_source_segment(source,node),variable)
    if max(map(len,polynomial),default=0)>1:return None
    slope=polynomial.get((variable,),Fraction(0));intercept=polynomial.get((),Fraction(0))
    return (slope,intercept) if slope else None


def _square_components(node,source,variable):
    """Return explicit affine-square terms plus a constant, without completing squares.

    An atom is an explicitly written affine square, or a product of two
    proportional affine factors. Only outer constant arithmetic and addition
    of like explicit squares are permitted. Any residual linear/other term is
    a proved failure of this syntactic form, not a claim the equation is unsolvable.
    """
    constant=_constant(node,source,variable)
    if constant is not None:return {},constant
    if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.UAdd,ast.USub)):
        atoms,c=_square_components(node.operand,source,variable);sign=-1 if isinstance(node.op,ast.USub) else 1
        return {key:sign*value for key,value in atoms.items()},sign*c
    if isinstance(node,ast.BinOp) and isinstance(node.op,(ast.Add,ast.Sub)):
        left,c1=_square_components(node.left,source,variable);right,c2=_square_components(node.right,source,variable)
        sign=-1 if isinstance(node.op,ast.Sub) else 1
        for key,value in right.items():left[key]=left.get(key,Fraction(0))+sign*value
        return {key:value for key,value in left.items() if value},c1+sign*c2
    if isinstance(node,ast.BinOp) and isinstance(node.op,ast.Pow):
        power=_constant(node.right,source,variable);affine=_affine(node.left,source,variable)
        if power==2 and affine is not None:
            slope,intercept=affine
            return {intercept/slope:slope*slope},Fraction(0)
        raise _NotSquareForm()
    if isinstance(node,ast.BinOp) and isinstance(node.op,(ast.Mult,ast.Div)):
        a=_constant(node.left,source,variable);b=_constant(node.right,source,variable)
        if isinstance(node.op,ast.Div):
            if b is None:raise _NotSquareForm()
            if not b:raise ValueError('zero denominator')
            atoms,c=_square_components(node.left,source,variable);return {key:value/b for key,value in atoms.items()},c/b
        if a is not None or b is not None:
            scale=a if a is not None else b;other=node.right if a is not None else node.left
            atoms,c=_square_components(other,source,variable);return {key:scale*value for key,value in atoms.items() if scale*value},scale*c
        first=_affine(node.left,source,variable);second=_affine(node.right,source,variable)
        if first is not None and second is not None and first[1]/first[0]==second[1]/second[0]:
            return {first[1]/first[0]:first[0]*second[0]},Fraction(0)
    raise _NotSquareForm()



def _collect_equation_terms(node,source,variable):
    """Preserve explicit square atoms while cancelling any like residual terms."""
    def merge(left,right,sign=1):
        atoms=dict(left[0]);residual=dict(left[1])
        for key,value in right[0].items():atoms[key]=atoms.get(key,Fraction(0))+sign*value
        for key,value in right[1].items():residual[key]=residual.get(key,Fraction(0))+sign*value
        return ({key:value for key,value in atoms.items() if value},{key:value for key,value in residual.items() if value})
    if isinstance(node,ast.BinOp) and isinstance(node.op,(ast.Add,ast.Sub)):
        return merge(_collect_equation_terms(node.left,source,variable),_collect_equation_terms(node.right,source,variable),-1 if isinstance(node.op,ast.Sub) else 1)
    if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.UAdd,ast.USub)):
        result=_collect_equation_terms(node.operand,source,variable)
        return merge(({},{}),result,-1 if isinstance(node.op,ast.USub) else 1)
    if isinstance(node,ast.BinOp) and isinstance(node.op,(ast.Mult,ast.Div)):
        left=_constant(node.left,source,variable);right=_constant(node.right,source,variable)
        if isinstance(node.op,ast.Div) and right is not None:
            if not right:raise ValueError('zero denominator')
            scale=1/right;other=node.left
        elif isinstance(node.op,ast.Mult) and (left is not None or right is not None):
            scale=left if left is not None else right;other=node.right if left is not None else node.left
        else:scale=None
        if scale is not None:
            atoms,residual=_collect_equation_terms(other,source,variable)
            return ({key:scale*value for key,value in atoms.items() if scale*value},{key:scale*value for key,value in residual.items() if scale*value})
    try:
        atoms,constant=_square_components(node,source,variable)
        return atoms,({():constant} if constant else {})
    except _NotSquareForm:
        return {},_polynomial(ast.get_source_segment(source,node),variable)

def _direct_square_equation(parts,variable):
    if not isinstance(parts,list) or len(parts)!=2 or any(not isinstance(p,str) or len(p)>250 for p in parts):raise ValueError('two bounded equation sides required')
    normalized=[_source(p) for p in parts]
    trees=[ast.parse(p,mode='eval') for p in normalized]
    if any(sum(1 for _ in ast.walk(t))>120 for t in trees):raise ValueError('equation AST too large')
    # In school algebra U(x)^0 has the original restriction U(x)!=0. The
    # polynomial normalizer intentionally simplifies powers, so reject this
    # unsupported variable-base domain BEFORE cancellation can erase it.
    for tree,source in zip(trees,normalized):
        for node in ast.walk(tree):
            if (isinstance(node,ast.BinOp) and isinstance(node.op,ast.Pow)
                    and isinstance(node.right,ast.Constant) and type(node.right.value)is int
                    and node.right.value==0):
                base=_polynomial(ast.get_source_segment(source,node.left),variable)
                if any(monomial for monomial in base):
                    raise ValueError('variable-base zeroth power requires an original-domain proof')
    # Parse every original side even when structural matching will fail. This
    # rejects executable/undeclared/nonpolynomial data rather than calling it false.
    polys=[_polynomial(p,variable) for p in normalized]
    forms=[_collect_equation_terms(t.body,p,variable) for t,p in zip(trees,normalized)]
    residual=dict(forms[0][1])
    for key,value in forms[1][1].items():residual[key]=residual.get(key,Fraction(0))-value
    residual={key:value for key,value in residual.items() if value}
    if any(key for key in residual):return False
    constant=residual.get((),Fraction(0));atoms=dict(forms[0][0])
    for key,value in forms[1][0].items():atoms[key]=atoms.get(key,Fraction(0))-value
    atoms={key:value for key,value in atoms.items() if value}
    if len(atoms)!=1:return False
    shift,coefficient=next(iter(atoms.items()));radicand=-constant/coefficient
    x=S.Symbol(variable,real=True)
    def expression(polynomial):return sum(S.Rational(c.numerator,c.denominator)*x**len(m) for m,c in polynomial.items())
    original=expression(polys[0])-expression(polys[1])
    roots=(S.EmptySet if radicand<0 else S.FiniteSet(-S.Rational(shift)+S.sqrt(S.Rational(radicand)),-S.Rational(shift)-S.sqrt(S.Rational(radicand))))
    actual=S.solveset(original,x,domain=S.S.Reals)
    if actual!=roots:raise ValueError('the structural square transformation did not preserve all real roots')
    return True


def direct_square_equations(spec):
    variable=spec['variable']
    if not isinstance(variable,str) or not re.fullmatch('[a-z]',variable):raise ValueError('one variable required')
    return select_unique(spec['options'],lambda option:_direct_square_equation(option['equation'],variable))


def _free_variables(node,environment=None):
    environment=dict(environment or {});tag=node.get('tag')
    if tag in ('shape','point'):
        name=node['name']
        if not isinstance(name,str) or not re.fullmatch('[A-Za-z]',name):raise ValueError('single-letter typed variable required')
        if name in environment:
            if environment[name]!=tag:raise ValueError('bound variable sort mismatch')
            return tag,{'shape':set(),'point':set()}
        return tag,{'shape':{name} if tag=='shape' else set(),'point':{name} if tag=='point' else set()}
    if tag=='half_turn':
        ct,cvars=_free_variables(node['center'],environment);st,svars=_free_variables(node['shape'],environment)
        if ct!='point' or st!='shape':raise ValueError('half-turn takes a point center and a shape')
        return 'shape',{kind:cvars[kind]|svars[kind] for kind in ('shape','point')}
    if tag=='equal':
        lt,lvars=_free_variables(node['left'],environment);rt,rvars=_free_variables(node['right'],environment)
        if lt!=rt or lt not in ('shape','point'):raise ValueError('typed equality required')
        return 'formula',{kind:lvars[kind]|rvars[kind] for kind in ('shape','point')}
    if tag=='exists':
        binders=node['variables']
        if not isinstance(binders,list) or not binders or len(binders)>3 or len({v['name'] for v in binders})!=len(binders):raise ValueError('distinct bounded variables required')
        for v in binders:
            if not isinstance(v['name'],str) or not re.fullmatch('[A-Za-z]',v['name']) or v['sort'] not in ('shape','point'):raise ValueError('invalid typed binder')
            environment[v['name']]=v['sort']
        result,free=_free_variables(node['body'],environment)
        if result!='formula':raise ValueError('an existential binder needs a formula')
        return result,free
    raise ValueError('unsupported formal set expression')


def _halfturn_definition(node):
    result,free=_free_variables(node)
    if result!='formula' or free['point']:raise ValueError('all geometric centers must be bound')
    if node.get('tag')!='exists' or len(node['variables'])!=1 or node['variables'][0]['sort']!='point':raise ValueError('one existential half-turn center required')
    body=node['body']
    if body.get('tag')!='equal':raise ValueError('set equality required')
    left,right=body['left'],body['right']
    if left.get('tag')!='half_turn':left,right=right,left
    if left.get('tag')!='half_turn' or right.get('tag')!='shape' or left['shape'].get('tag')!='shape' or left['center']!={'tag':'point','name':node['variables'][0]['name']}:raise ValueError('unsupported half-turn relation form')
    return left['shape']['name'],right['name'],free['shape']


def _centroid(ps):return sum(ps,S.zeros(2,1))/len(ps)


def _set_equal(first,second):
    if len(first)!=len(second):return False
    return all(any(all(zero(a-b) for a,b in zip(p,q)) for q in second) for p in first)


def _rotation_invariant(ps,degrees):
    matrices={90:S.Matrix([[0,-1],[1,0]]),180:-S.eye(2)}
    if type(degrees)is not int or degrees not in matrices:raise ValueError('quarter/half turns only')
    matrix=matrices[degrees];centroid=_centroid(ps)
    # If a nontrivial rotation maps a finite set to itself, taking its mean
    # gives(I-R)(center-centroid)=0. The invertible matrix forces the center.
    if zero((S.eye(2)-matrix).det()):raise ValueError('center not determined by centroid')
    return _set_equal([matrix*(p-centroid)+centroid for p in ps],ps)


def central_symmetry_types(spec):
    rs,rt,rfree=_halfturn_definition(spec['relation_expression']);ps,pt,pfree=_halfturn_definition(spec['property_expression'])
    if rs==rt or ps!=pt or rs!=ps:raise ValueError('a two-shape relation and its same-source diagonal restriction are required')
    def check(option):
        claim=option['claim']
        if claim=='free_shape_arities':
            arities=option['arities']
            if any(type(n)is not int or n<0 for n in arities) or len(arities)!=2:raise ValueError('two integer arities required')
            return arities==[len(rfree),len(pfree)]
        if claim=='identical_predicates':
            shape=points(option['counterexample_shape'],convex=True);center=S.Matrix([math(v) for v in option['half_turn_center']])
            if len(center)!=2:raise ValueError('planar half-turn center required')
            image=[2*center-p for p in shape]
            if not _set_equal([2*center-p for p in shape],image):raise ValueError('pair is not related by the supplied half-turn')
            if _rotation_invariant(shape,180):raise ValueError('the shape also has the intrinsic symmetry; counterexample fails')
            return False
        if claim=='equivalent_rotation_invariance':
            a,b=option['angles'];shape=points(option['counterexample_shape'],convex=True)
            first,second=_rotation_invariant(shape,a),_rotation_invariant(shape,b)
            if first==second:raise ValueError('counterexample does not distinguish the two invariant classes')
            return False
        raise ValueError('unknown set-theoretic assertion')
    return select_unique(spec['options'],check)


def _integer(value):
    if isinstance(value,bool):raise ValueError('Boolean is not a count')
    value=number(value)
    if value.denominator!=1 or value<0:raise ValueError('nonnegative integer count required')
    return int(value)


def partition_table_audit(spec):
    """Known population, exhaustive mutually-exclusive frequencies and total.

    A header edit is validated against BOTH the row sum and the independently
    known population. An inconsistency certificate checks the actual arithmetic,
    not an action label. No unique erroneous individual/row is inferred.
    """
    if spec.get('classification')!='one_category_per_person_exhaustive':raise ValueError('partition/completeness premise required')
    population=_integer(spec['population']);counts=[_integer(v) for v in spec['counts']];header=_integer(spec['header'])
    if not counts or population<=0:raise ValueError('nonempty surveyed population/table required')
    total=sum(counts)
    def check(option):
        claim=option['claim']
        if claim=='valid_table':return total==header==population
        if claim=='valid_after_header_edit':
            proposed=_integer(option['new_header'])
            return proposed!=header and proposed==total==population
        if claim=='inconsistency_certificate':
            stated_sum=_integer(option['row_sum']);stated_population=_integer(option['known_population'])
            return stated_sum==total and stated_population==population and total!=population
        raise ValueError('unknown partition-table claim')
    return select_unique(spec['options'],check)


HANDLERS={'app63_direct_square_equations':direct_square_equations,
          'app63_central_symmetry_types':central_symmetry_types,
          'app63_partition_table_audit':partition_table_audit}


def square_rotation_certificates(spec):
    """Check the supplied finite proof certificates, not all imaginable proofs.

    Primitive steps construct perpendicular feet/quarter turns or assert a
    perpendicularity/congruence. Only verified isometries and asserted proven
    congruences add edge-length equalities. Completion then requires a known
    goal edge and two known summands meeting at an actually intermediate point.
    A true but unrelated final fact is not a completed certificate of this goal.
    """
    if spec.get('figure')!='square_closed_edge_points_with_45_degree_angle' or spec.get('rules')!='isometry_congruence_segment_addition':raise ValueError('explicit geometric certificate system required')
    a=S.Symbol('a',positive=True);e,f=S.symbols('e f',nonnegative=True)
    initial={'A':S.Matrix([0,0]),'B':S.Matrix([a,0]),'C':S.Matrix([a,a]),'D':S.Matrix([0,a]),'E':S.Matrix([a,e]),'F':S.Matrix([f,a])}
    replacement=a*(a-e)/(a+e)
    # The original 45-degree equation is a²-ef=a(e+f). Sincea+e>0,
    # solving it gives the COMPLETE closed family0<=e<=a, f=a(a-e)/(a+e).
    if S.cancel((a*a-e*f-a*(e+f)).subs(f,replacement))!=0:raise ValueError('angle-locus parametrization failed')
    def normal(expression):return S.factor(S.cancel(expression.subs(f,replacement)))
    def identity(expression):
        numerator=S.together(normal(expression)).as_numer_denom()[0]
        if numerator==0:return True
        S.Poly(numerator,a,e) # exact nonidentity, not a numerical near-zero test
        return False
    def positive(expression):
        value=normal(expression)
        if value.is_positive is not True:raise ValueError('strictly positive geometric domain unproved')
    def edge(segment,geometry):
        if not isinstance(segment,list) or len(segment)!=2 or any(v not in geometry for v in segment):raise ValueError('two known segment endpoints required')
        return tuple(sorted(segment))
    def length2(segment,geometry):
        p,q=[geometry[v] for v in segment];return S.expand((p-q).dot(p-q))
    def witness(option):
        values=option.get('failure_witness')
        if not isinstance(values,dict) or set(values)!=set('aef'):raise ValueError('an exact complete legal failure witness is required')
        result={symbol:math(values[str(symbol)]) for symbol in (a,e,f)}
        av,ev,fv=[result[symbol] for symbol in (a,e,f)]
        if not(av>0 and 0<=ev<=av and 0<=fv<=av) or not zero((a*a-e*f-a*(e+f)).subs(result)):raise ValueError('counterexample is outside the closed 45-degree square family')
        return result
    def nondegenerate(triangle,geometry):
        p,q,r=[geometry[v] for v in triangle]
        determinant=S.det(S.Matrix.hstack(q-p,r-p));value=normal(determinant)
        if value.is_positive is True or value.is_negative is True:return True
        # Legal endpoint failures can invalidate an asserted triangle; they
        # are never discarded merely because the interior is nondegenerate.
        for assignment in ({a:1,e:0,f:1},{a:1,e:1,f:0}):
            if zero(determinant.subs(assignment)):return False
        raise ValueError('nondegenerate triangle not proved on the whole family')
    def check(option):
        geometry=dict(initial);parent={}
        def find(segment):
            parent.setdefault(segment,segment)
            if parent[segment]!=segment:parent[segment]=find(parent[segment])
            return parent[segment]
        def unite(first,second):parent[find(first)]=find(second)
        for side in (['B','C'],['C','D'],['D','A']):unite(edge(['A','B'],geometry),edge(side,geometry))
        steps=option['steps']
        if not isinstance(steps,list) or not steps:raise ValueError('a finite proof certificate is required')
        for step in steps:
            operation=step['op']
            if operation=='perpendicular_foot':
                new=step['name'];p=geometry[step['point']];line=step['line'];q,r=[geometry[v] for v in line];v=r-q
                if new in geometry or not re.fullmatch('[A-Z]',new):raise ValueError('a fresh point label is required')
                positive(v.dot(v));geometry[new]=S.simplify(q+v*((p-q).dot(v)/v.dot(v)))
            elif operation=='quarter_turn':
                if step['degrees']!=90 or type(step['degrees'])is not int:raise ValueError('this certificate uses an exact quarter-turn')
                center=geometry[step['center']];source=geometry[step['maps_from']]-center;target=geometry[step['maps_to']]-center
                matrices=[S.Matrix([[0,-1],[1,0]]),S.Matrix([[0,1],[-1,0]])]
                valid=[matrix for matrix in matrices if all(identity(v) for v in matrix*source-target)]
                if len(valid)!=1:raise ValueError('the stated quarter-turn is not uniquely determined')
                new=step['image'];old=step['point']
                if old in (step['center'],step['maps_from']) or new in geometry or not re.fullmatch('[A-Z]',new):raise ValueError('distinct input and fresh image point required')
                matrix=valid[0];geometry[new]=S.simplify(center+matrix*(geometry[old]-center))
                original=[step['center'],step['maps_from'],old];images=[step['center'],step['maps_to'],new]
                for i,j in ((0,1),(0,2),(1,2)):
                    pseg=[original[i],original[j]];qseg=[images[i],images[j]]
                    if not identity(length2(pseg,geometry)-length2(qseg,geometry)):raise ValueError('claimed rotation did not preserve length')
                    unite(edge(pseg,geometry),edge(qseg,geometry))
            elif operation=='perpendicular':
                first,second=step['segments'];p,q=[geometry[v] for v in first];r,s=[geometry[v] for v in second]
                positive((p-q).dot(p-q));positive((r-s).dot(r-s));residual=(p-q).dot(r-s)
                if not identity(residual):
                    assignment=witness(option)
                    if S.simplify(residual.subs(assignment)).is_zero is not False:raise ValueError('the witness does not refute perpendicularity')
                    return False
            elif operation=='congruent':
                first,second=step['triangles']
                if any(len(t)!=3 or len(set(t))!=3 or any(v not in geometry for v in t) for t in (first,second)):raise ValueError('two known three-vertex triangles required')
                paired=[([first[i],first[j]],[second[i],second[j]]) for i,j in ((0,1),(0,2),(1,2))]
                differences=[length2(u,geometry)-length2(v,geometry) for u,v in paired]
                if not all(identity(value) for value in differences):
                    assignment=witness(option)
                    if not all(not zero(S.det(S.Matrix.hstack(geometry[t[1]]-geometry[t[0]],geometry[t[2]]-geometry[t[0]])).subs(assignment)) for t in (first,second)):raise ValueError('congruence counterexample must itself contain two proper triangles')
                    if not any(S.simplify(value.subs(assignment)).is_zero is False for value in differences):raise ValueError('counterexample does not refute the ordered congruence')
                    return False
                if not all(nondegenerate(t,geometry) for t in (first,second)):return False
                for first_edge,second_edge in paired:unite(edge(first_edge,geometry),edge(second_edge,geometry))
            else:raise ValueError('unsupported proof step')
        goal=spec['goal'];lhs=edge(goal['segment'],geometry);summands=[edge(s,geometry) for s in goal['sum']]
        if len(summands)!=2:raise ValueError('two target summands required')
        find(lhs);find(summands[0]);find(summands[1])
        # This is finite certificate completion, not a claim that the geometric
        # goal is false when an outline leaves out its length-transport step.
        known=list(parent)
        lefts=[segment for segment in known if find(segment)==find(summands[0])]
        rights=[segment for segment in known if find(segment)==find(summands[1])]
        for first in lefts:
            for second in rights:
                for middle in set(first)&set(second):
                    outer_first=first[1] if first[0]==middle else first[0];outer_second=second[1] if second[0]==middle else second[0]
                    candidate=tuple(sorted((outer_first,outer_second)))
                    if candidate not in parent or find(candidate)!=find(lhs):continue
                    p,q,r=geometry[outer_first],geometry[middle],geometry[outer_second]
                    if not identity(S.det(S.Matrix.hstack(p-q,r-q))):raise ValueError('a required segment addition is not collinear')
                    dot=S.factor((p-q).dot(r-q))
                    if dot.is_nonpositive is not True and normal(dot).is_nonpositive is not True:raise ValueError('the common endpoint was not proved to lie between the others')
                    return True
        return False
    return select_unique(spec['options'],check)


HANDLERS['app63_square_rotation_certificates']=square_rotation_certificates
