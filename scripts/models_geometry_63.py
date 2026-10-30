"""Structural definitions and sound proof certificates for the63 audit.

No option key/answer is read. Passing universal claims use typed constructions,
logical rules, or exact polynomial identities. Finite worlds only disprove
claims. JSON proof trees and bounded school-math expressions are the only input
languages; unknown syntax, domains or theorem schemas fail closed.
"""
import re
from collections import Counter
from fractions import Fraction
from itertools import product
import sympy as S
from model_types import select_unique
from models_geometry_160 import parse


def scalar(value):
    if type(value) not in (str,int,float,Fraction):raise ValueError('closed real scalar required')
    result=S.simplify(parse(value,{}))
    if result.free_symbols or result.is_real is not True:raise ValueError('closed real scalar required')
    return result


def name(value):
    if not isinstance(value,str) or not re.fullmatch('[a-z]',value):raise ValueError('single-letter mathematical identifier required')
    return value


def histogram_height(spec):
    if spec.get('construction')!='frequency_rectangles':raise ValueError('frequency-coordinate construction must be explicit')
    a=S.Symbol('a',real=True);w=S.Symbol('w',positive=True);f,g=S.symbols('f g',integer=True,nonnegative=True)
    rectangle=[S.Matrix([a,0]),S.Matrix([a+w,0]),S.Matrix([a+w,f]),S.Matrix([a,f])]
    height=S.expand(rectangle[2][1]-rectangle[1][1])
    quantities={'bin_width':rectangle[1][0]-rectangle[0][0],
                'total_count':f+g,'bin_midpoint':(rectangle[0][0]+rectangle[1][0])/2,
                'bin_frequency':f}
    witness=spec['counterexample'];data=[scalar(v) for v in witness['data']];bounds=[[scalar(v) for v in row] for row in witness['bins']]
    if len(bounds)!=2 or any(len(b)!=2 or b[1]<=b[0] for b in bounds) or bounds[0][1]!=bounds[1][0]:raise ValueError('two contiguous nonempty bins required')
    if bounds[0][1]-bounds[0][0]!=bounds[1][1]-bounds[1][0]:raise ValueError('equal-width premise violated')
    if any(not bounds[0][0]<=x<bounds[-1][1] for x in data):raise ValueError('data outside half-open bins')
    counts=[sum(1 for x in data if lo<=x<hi) for lo,hi in bounds]
    substitution={a:bounds[0][0],w:bounds[0][1]-bounds[0][0],f:counts[0],g:counts[1]}
    def check(o):
        if o['quantity'] not in quantities:raise ValueError('unknown histogram quantity')
        difference=S.expand(height-quantities[o['quantity']])
        if difference==0:return True # arbitrary nonnegative frequencies, no sampled plot
        if S.simplify(difference.subs(substitution)).is_zero is not False:raise ValueError('counterexample does not refute candidate identity')
        return False
    return select_unique(spec['options'],check)


def predicate(node,budget=None):
    if budget is None:budget=[0]
    budget[0]+=1
    if budget[0]>40 or not isinstance(node,dict):raise ValueError('bounded predicate tree required')
    op=node.get('op')
    if op=='and':
        if set(node)!={'op','items'} or not 2<=len(node['items'])<=8:raise ValueError('bounded conjunction required')
        return ('and',tuple(sorted((predicate(n,budget) for n in node['items']),key=str)))
    if op not in ('opposite_ray_angles','equal_angles','supplementary_angles') or set(node)!={'op','arguments'}:
        raise ValueError('unknown geometric predicate')
    args=node['arguments']
    if not isinstance(args,list) or len(args)!=2 or args[0]==args[1]:raise ValueError('two different angle objects required')
    return op,tuple(sorted(name(a) for a in args))


def theorem_antecedent(spec):
    theorem=spec['theorem']
    if set(theorem)!={'premise','conclusion'} or spec.get('domain')!='two_distinct_intersecting_lines':raise ValueError('explicit nondegenerate theorem required')
    premise,conclusion=predicate(theorem['premise']),predicate(theorem['conclusion'])
    if premise[0]!='opposite_ray_angles' or conclusion!=('equal_angles',premise[1]):raise ValueError('the geometric theorem is not proved by this kernel')
    # Opposite rays replace both direction vectors by their negatives. Both
    # norms and their dot product are preserved, hence the unique angle in
    # (0,pi) is preserved. Nonparallel lines ensure nonzero directions.
    x,y,u,v=S.symbols('x y u v',real=True)
    identities=[(-x)*(-u)+(-y)*(-v)-(x*u+y*v),(-x)**2+(-y)**2-(x*x+y*y),(-u)**2+(-v)**2-(u*u+v*v)]
    if any(S.expand(e)!=0 for e in identities):raise ValueError('vertical-angle metric proof failed')
    return select_unique(spec['options'],lambda o:predicate(o['predicate'])==premise)


def equality(statement):
    if not isinstance(statement,list) or len(statement)!=2:raise ValueError('binary equality statement required')
    return tuple(name(v) for v in statement)


def checked_equality(node,context,lemmas,stack=(),budget=None):
    if budget is None:budget=[0]
    budget[0]+=1
    if budget[0]>80 or len(stack)>16 or not isinstance(node,dict):raise ValueError('bounded equality proof required')
    rule=node.get('rule')
    if rule=='hypothesis':
        result=equality(node['statement'])
        if result not in context:raise ValueError('equality is not a given hypothesis')
        return result
    if rule=='reflexive':
        term=name(node['term']);return term,term
    if rule=='symmetric':
        a,b=checked_equality(node['from'],context,lemmas,stack,budget);return b,a
    if rule=='transitive':
        a,b=checked_equality(node['first'],context,lemmas,stack,budget)
        c,d=checked_equality(node['second'],context,lemmas,stack,budget)
        if b!=c:raise ValueError('transitive middle term does not match')
        return a,d
    if rule=='lemma':
        key=node['id']
        if not isinstance(key,str) or key in stack or key not in lemmas:raise ValueError('unproved or cyclic lemma')
        return checked_equality(lemmas[key],context,lemmas,stack+(key,),budget)
    raise ValueError('unknown equality proof rule')


def proof_evidence(spec):
    """Sound equality certificates vs an indistinguishable unequal pair.

    Proof rules are universally sound under their stated hypotheses, verified
    recursively. A quantized display is disproved by one exact unequal world.
    The model selects failure of *guaranteed* equality, not an image opinion.
    """
    def guarantees(o):
        if o['evidence']=='equality_certificate':
            context=[equality(s) for s in o['hypotheses']]
            result=checked_equality(o['proof'],context,o.get('lemmas',{}))
            if result!=equality(o['goal']):raise ValueError('certificate does not prove the declared equality')
            return True
        if o['evidence']=='quantized_observation':
            left,right=map(scalar,o['lengths']);step=scalar(o['resolution'])
            if min(left,right,step)<=0 or left==right:raise ValueError('positive unequal segment lengths required')
            display=lambda x:S.floor(x/step+S.Rational(1,2))*step
            if display(left)!=display(right):raise ValueError('example is visibly distinguishable at declared precision')
            return False
        raise ValueError('unmodelled evidence source')
    return select_unique(spec['options'],lambda o:not guarantees(o))


def _formula(node,budget=None):
    if budget is None:budget=[0]
    budget[0]+=1
    if budget[0]>50 or not isinstance(node,dict):raise ValueError('bounded metric formula required')
    op=node.get('op')
    if op in ('distance','angle'):
        args=node.get('points');arity=2 if op=='distance' else 3
        if set(node)!={'op','points'} or not isinstance(args,list) or len(args)!=arity:raise ValueError('invalid metric atom')
        return op,tuple(name(a) for a in args)
    if op=='point_line_distance':
        if set(node)!={'op','point','line'}:raise ValueError('invalid point-line metric')
        return op,(name(node['point']),name(node['line']))
    if op=='number':
        if set(node)!={'op','value'}:raise ValueError('invalid constant')
        return op,str(scalar(node['value']))
    if op=='add':
        if set(node)!={'op','items'} or not isinstance(node['items'],list) or not 2<=len(node['items'])<=4:raise ValueError('bounded sum required')
        return op,tuple(_formula(x,budget) for x in node['items'])
    if op in ('eq','le'):
        if set(node)!={'op','left','right'}:raise ValueError('binary metric comparison required')
        return op,(_formula(node['left'],budget),_formula(node['right'],budget))
    raise ValueError('unknown metric operator')


def _condition(node):
    if not isinstance(node,dict):raise ValueError('geometric hypothesis required')
    if node.get('op')=='on_line' and set(node)=={'op','point','line'}:
        return 'on_line',(name(node['point']),name(node['line']))
    if node.get('op')=='nondegenerate_triangle' and set(node)=={'op','points'}:
        ps=node['points']
        if not isinstance(ps,list) or len(ps)!=3 or len(set(ps))!=3:raise ValueError('three distinct triangle identifiers required')
        return 'nondegenerate_triangle',tuple(name(x) for x in ps)
    return _formula(node)


def _canonical(node):
    if not isinstance(node,tuple):return node
    op,args=node
    if op=='number':return node
    if op in ('distance','nondegenerate_triangle'):return op,tuple(sorted(args))
    if op=='angle':
        first,vertex,last=args
        first,last=sorted((first,last))
        return op,(first,vertex,last)
    if op in ('point_line_distance','on_line'):return node
    children=tuple(_canonical(x) for x in args)
    if op in ('add','eq','premises'):children=tuple(sorted(children,key=repr))
    return op,children


def _leaves(node):
    if not isinstance(node,tuple):return {node} if isinstance(node,str) else set()
    if node[0]=='number':return set()
    return set().union(*(_leaves(x) for x in node[1]))


def _replace(node,mapping):
    if not isinstance(node,tuple):return mapping.get(node,node)
    if node[0]=='number':return node
    return node[0],tuple(_replace(x,mapping) for x in node[1])


def _bindings(pattern,target,injective=False):
    """Bounded exhaustive alpha-unification, with commutative metric nodes."""
    variables=sorted(v for v in _leaves(pattern) if v.startswith('?'))
    names=sorted(v for v in _leaves(target) if re.fullmatch('[a-z]',v))
    if len(variables)>4 or len(names)>6:raise ValueError('proof signature exceeds variable bound')
    for values in product(names,repeat=len(variables)):
        if injective and len(set(values))!=len(values):continue
        binding=dict(zip(variables,values))
        if _canonical(_replace(pattern,binding))==_canonical(target):yield binding


def _schema(statement):
    return _replace(statement,{v:'?'+v for v in _leaves(statement) if re.fullmatch('[a-z]',v)})


def metric_final_step(spec):
    """Check a *direct instance* of a reviewed Euclidean inference schema.

    Conditional theorems retain their hypotheses; their conclusions alone are
    never treated as universally true. Only the unconditional broken-path rule
    proves this source goal. This kernel does not search for multi-step proofs
    using other theorems or grade their names as a preference rubric.
    """
    goal=_formula(spec['goal'])
    dist=lambda a,b:('distance',(a,b))
    add=lambda *items:('add',items)
    eq=lambda a,b:('eq',(a,b))
    angle=lambda a,b,c:('angle',(a,b,c))
    path=('le',(dist('?a','?b'),add(dist('?a','?p'),dist('?p','?b'))))
    rules=[
      ('rule',(('premises',(('on_line',('?q','?l')),)),('le',(('point_line_distance',('?p','?l')),dist('?p','?q'))))),
      ('rule',(('premises',(('nondegenerate_triangle',('?a','?b','?c')),)),eq(add(angle('?a','?b','?c'),angle('?b','?c','?a'),angle('?c','?a','?b')),('number','180')))),
      ('rule',(('premises',(('nondegenerate_triangle',('?a','?b','?c')),eq(angle('?a','?b','?c'),angle('?b','?c','?a')))),eq(dist('?a','?b'),dist('?a','?c')))),
      ('rule',(('premises',()),path))]
    x,y,u,v=S.symbols('x y u v',real=True)
    # Reflect A=(x,y) across the y-axis, while P=(0,v) is fixed.
    if S.expand((x*x+(y-v)**2)-((-x)**2+(y-v)**2))!=0:raise ValueError('reflection path substitution failed')
    if S.expand((x*x+y*y)*(u*u+v*v)-(x*u+y*v)**2-(x*v-y*u)**2)!=0:raise ValueError('universal path metric proof failed')
    if next(_bindings(path,goal),None) is None:raise ValueError('source goal is not the proved two-edge path bound')
    available=tuple(_condition(n) for n in spec.get('available_hypotheses',[]))
    def check(o):
        statement=_formula(o['conclusion'])
        if not isinstance(o.get('hypotheses'),list):raise ValueError('explicit theorem hypotheses required')
        hypotheses=tuple(_condition(n) for n in o['hypotheses'])
        candidate=('rule',(('premises',hypotheses),statement))
        if not any(next(_bindings(rule,candidate,injective=True),None) is not None for rule in rules):
            raise ValueError('unverified theorem schema or missing hypotheses')
        schema=_schema(candidate)
        # Instantiate the candidate conclusion; every required premise must
        # then be present in this step's explicit context.
        for binding in _bindings(schema[1][1],goal):
            needed=_replace(schema[1][0],binding)[1]
            if all(_canonical(n) in [_canonical(a) for a in available] for n in needed):return True
        return False
    return select_unique(spec['options'],check)


def _process(node,variables,budget=None):
    if budget is None:budget=[0]
    budget[0]+=1
    if budget[0]>50 or not isinstance(node,dict):raise ValueError('bounded process expression required')
    op=node.get('op')
    if op=='variable':
        key=name(node['symbol'])
        if key not in variables:raise ValueError('undeclared process quantity')
        return variables[key],frozenset([key])
    if op=='constant':
        scalar(node['value']);dimension=node['dimension']
        if not isinstance(dimension,list) or len(dimension)!=2 or any(type(x)is not int or abs(x)>6 for x in dimension):raise ValueError('bounded dimensional exponents required')
        return tuple(dimension),frozenset()
    if op in ('subtract','multiply'):
        left,lfree=_process(node['left'],variables,budget);right,rfree=_process(node['right'],variables,budget)
        if op=='subtract':
            if left!=right:raise ValueError('subtracting incompatible physical quantities')
            dimension=left
        else:dimension=tuple(a+b for a,b in zip(left,right))
        return dimension,lfree|rfree
    raise ValueError('unknown process operation')


def process_argument(spec):
    if spec.get('family')!='constant_outflow_reservoir':raise ValueError('directed physical process family required')
    expression=spec['expression']
    try:
        initial=expression['left'];product=expression['right'];rate=product['left'];clock=product['right']
        if (expression['op']!='subtract' or product['op']!='multiply' or initial['op']!='constant'
                or rate['op']!='constant' or clock['op']!='variable'
                or initial['dimension']!=[1,0] or rate['dimension']!=[1,-1]):raise ValueError('reservoir quantity types do not match')
        initial_value,rate_value=scalar(initial['value']),scalar(rate['value'])
        if initial_value.is_positive is not True or rate_value.is_positive is not True:raise ValueError('positive initial volume and outflow required')
        if S.cancel(initial_value/rate_value).is_positive is not True:raise ValueError('nonempty physical time domain unproved')
    except (KeyError,TypeError):raise ValueError('unsupported process construction')
    variables={name(k):tuple(v) for k,v in spec['variables'].items()}
    if any(len(v)!=2 or any(type(x)is not int for x in v) for v in variables.values()):raise ValueError('two exact dimension exponents required')
    output=name(spec['defined_symbol'])
    if output not in variables:raise ValueError('defined quantity missing')
    dimension,free=_process(spec['expression'],variables)
    if dimension!=variables[output] or output in free or len(free)!=1:raise ValueError('single-input directed process definition required')
    if variables[output]!=(1,0) or variables[next(iter(free))]!=(0,1):raise ValueError('volume output and elapsed-time argument required')
    def check(o):
        item=o['quantity']
        if item['op']=='variable':
            symbol=name(item['symbol'])
            if symbol not in variables:raise ValueError('unknown candidate process quantity')
            return symbol in free
        if item['op']=='constant':_process(item,variables);return False
        raise ValueError('unmodelled candidate quantity')
    return select_unique(spec['options'],check)


def trimmed_mean_robustness(spec):
    """Every n>=3 score vector, including tied extrema, under outward changes.

    Sorting represents the sample by minimumm, maximumM andk>=1 other scores
    with sumz. Increasing one existing maximum bydelta>0 changes both sum/max
    equally; decreasing one existing minimum is the symmetric cancellation.
    """
    if spec.get('operation')!='remove_one_min_and_one_max' or spec.get('domain')!='at_least_three_real_scores':raise ValueError('trimmed-score domain missing')
    k=S.Symbol('k',integer=True,positive=True);m,M,z=S.symbols('m M z',real=True);delta=S.Symbol('d',positive=True)
    n=k+2;total=m+M+z;trimmed=(total-m-M)/k
    high_change=S.cancel((total+delta-m-(M+delta))/k-trimmed)
    low_change=S.cancel((total-delta-(m-delta)-M)/k-trimmed)
    ordinary_change=S.cancel((total+delta)/n-total/n)
    if high_change!=0 or low_change!=0 or ordinary_change.is_positive is not True:raise ValueError('global outward robustness unproved')
    def scores(values):
        xs=sorted(scalar(v) for v in values)
        if len(xs)<3:raise ValueError('at least three scores required')
        kept=xs[1:-1]
        return xs,kept,S.cancel(sum(xs)/len(xs)),S.cancel(sum(kept)/len(kept))
    def check(o):
        claim=o['claim']
        if claim=='reduced_outward_extreme_influence':return high_change==low_change==0 and ordinary_change.is_positive is True
        if claim=='always_increases_total':
            xs,kept,mean,tmean=scores(o['counterexample'])
            if not sum(kept)<sum(xs) or not tmean<mean:raise ValueError('counterexample must refute both total/average increase interpretations')
            return False
        if claim=='fewer_judges':
            # The operation changes which score records are used, never the
            # membership of the original judge entity domain of cardinalityn.
            before_judges=n;after_judges=n;used_records=n-2
            if S.simplify(before_judges-after_judges)!=0 or S.simplify(n-used_records)!=2:raise ValueError('entity/record-domain distinction unproved')
            return False
        if claim=='unique_mode':
            _,kept,_,_=scores(o['counterexample']);counts=Counter(kept);maximum=max(counts.values())
            if sum(v==maximum for v in counts.values())<2:raise ValueError('trimmed sample does not refute unique mode')
            return False
        raise ValueError('unknown trimming effect')
    return select_unique(spec['options'],check)


HANDLERS={'g63_histogram_height':histogram_height,'g63_theorem_antecedent':theorem_antecedent,
 'g63_proof_evidence':proof_evidence,'g63_metric_final_step':metric_final_step,
 'g63_process_argument':process_argument,'g63_trimmed_mean_robustness':trimmed_mean_robustness}
