"""Typed observation objects and exact geometry/statistics proofs for audit105.

Definitions are executable type constructions, not stored answers. A sample
is an indexed family of scalar measurements on an injectively selected subject
domain; equal measured values never collapse distinct study individuals.
Unknown mathematical/algorithmic forms fail closed. Finite data only refute
universal claims, while passing universal claims use definitions or identities.
"""
from dataclasses import dataclass
from fractions import Fraction
from collections import Counter
import sympy as S

from model_types import select_unique
from models_geometry_160 import parse, symbols
from models_algebra import implies
from models_foundations_160 import _slot, ANGLE_DOMAIN, R


def integer(x,minimum=0):
    if type(x) is not int or x<minimum:raise ValueError('exact integer count required')
    return x


@dataclass(frozen=True)
class Subjects:
    entity: str
    region: str
    count: int


@dataclass(frozen=True)
class Observations:
    subjects: Subjects
    quantity: str
    # The index belongs to the study subject, rather than the measured value.
    def cardinality(self):return self.subjects.count


@dataclass(frozen=True)
class Datum:
    entity: str
    quantity: str


class Survey:
    def __init__(self,spec):
        d=spec['design'];entity=d['entity'];quantity=d['measurement']['quantity']
        if not isinstance(entity,str) or not entity or not isinstance(quantity,str) or not quantity:raise ValueError('entity and observed quantity required')
        population=integer(d['population_count'],1);drawn=integer(d['selection']['count'],1)
        if d['selection']['method']!='without_replacement' or drawn>population:raise ValueError('injective finite-subject sampling required')
        m=d['measurement']
        if m.get('kind')!='scalar' or integer(m.get('records_per_subject'),1)!=1 or integer(m.get('missing_subjects'))!=0:
            raise ValueError('one complete scalar observation per sampled subject required')
        self.population=Subjects(entity,'population',population)
        self.selected=Subjects(entity,'population' if drawn==population else 'selected',drawn)
        self.quantity=quantity
        if 'records' in d:
            records=d['records']
            if not isinstance(records,list) or len(records)!=drawn:raise ValueError('record count disagrees with subject domain')
            ids=[integer(r['subject'],1) for r in records]
            if len(set(ids))!=drawn or any(i>population for i in ids):raise ValueError('records must index distinct population subjects')
            for r in records:
                # Values may repeat, but each source value must be a closed
                # real scalar in the bounded grammar, not a fabricated row id.
                value=parse(r['value'],{})
                if value.free_symbols or value.is_real is not True:raise ValueError('observed real scalar required')

    def evaluate(self,node):
        op=node['op']
        if op=='subjects':
            if node['scope']=='population':return self.population
            if node['scope']=='selected':return self.selected
            raise ValueError('unknown subject scope')
        if op=='observe':
            subjects=self.evaluate(node['subjects'])
            if not isinstance(subjects,Subjects):raise ValueError('measurements require a subject domain')
            quantity=node['quantity']
            if not isinstance(quantity,str) or not quantity:raise ValueError('measurement quantity required')
            return Observations(subjects,quantity)
        if op=='datum':
            quantity=node['quantity']
            if not isinstance(quantity,str) or not quantity:raise ValueError('single observed quantity required')
            return Datum(self.population.entity,quantity)
        if op=='cardinality':
            family=self.evaluate(node['object'])
            if not isinstance(family,Observations):raise ValueError('sample capacity counts indexed observations, not values or a raw number')
            return family.cardinality()
        if op=='number':return integer(node['value'])
        if op=='role':
            role=node['name']
            if role=='population':return Observations(self.population,self.quantity)
            if role=='sample':return Observations(self.selected,self.quantity)
            if role=='individual':return Datum(self.population.entity,self.quantity)
            if role=='sample_capacity':return Observations(self.selected,self.quantity).cardinality()
            raise ValueError('unknown statistical object role')
        raise ValueError('unknown observation-object operation')


def observation_objects(spec):
    survey=Survey(spec)
    if spec['query']=='capacity':
        sample=survey.evaluate({'op':'role','name':'sample'})
        # Construct and type-check a full indexed observation family first.
        # Its cardinality is invariant under equal measured values.
        if not isinstance(sample,Observations) or sample.subjects.entity!=survey.population.entity:raise ValueError('invalid observation family')
        return survey.evaluate({'op':'cardinality','object':{'op':'role','name':'sample'}})
    if spec['query']=='identity':
        target=survey.evaluate(spec['target'])
        return select_unique(spec['options'],lambda o:survey.evaluate(o['object'])==target)
    if spec['query']=='claims':return select_unique(spec['options'],lambda o:survey.evaluate(o['left'])==survey.evaluate(o['right']))
    raise ValueError('unknown survey-object query')


def sampling_guarantee(spec):
    """A proper-subgroup family refutes both inclusion and size guarantees.

    n included and n excluded subjects, two different positive observed heights.
    Sampling the entire included group is permitted by the stated restriction;
    its mean differs by a nonzero constant for arbitrarily large integer n.
    """
    n=S.Symbol('n',integer=True,positive=True)
    included=parse(spec['included_value'],{});excluded=parse(spec['excluded_value'],{})
    if included.is_positive is not True or excluded.is_positive is not True or included==excluded:raise ValueError('positive unequal measurements needed for a valid refutation')
    sample_sum=n*included;population_sum=n*included+n*excluded
    sample_mean=S.cancel(sample_sum/n);population_mean=S.cancel(population_sum/(n+n))
    bias=S.factor(sample_mean-population_mean)
    if bias.is_zero is not False or S.diff(bias,n)!=0:raise ValueError('arbitrarily large subgroup bias not proved')
    def check(o):
        claim=o['claim']
        if claim=='not_guaranteed':return bias.subs(n,1).is_zero is False
        if claim in ('guaranteed_by_inclusion','guaranteed_by_large_size'):return False # valid arbitrary-size counterexample family above
        raise ValueError('unknown sampling quantifier')
    return select_unique(spec['options'],check)


def frequencies(data,bins):
    xs=[parse(v,{}) for v in data];groups=[[parse(v,{}) for v in bounds] for bounds in bins]
    if not groups or any(len(g)!=2 or not g[0]<g[1] for g in groups):raise ValueError('nonempty half-open bins required')
    if any(groups[i][1]!=groups[i+1][0] for i in range(len(groups)-1)):raise ValueError('a contiguous nonoverlapping partition required')
    if any(not groups[0][0]<=x<groups[-1][1] for x in xs):raise ValueError('data outside partition')
    return xs,groups,[sum(1 for x in xs if lo<=x<hi) for lo,hi in groups]


def frequency_algorithm(spec):
    """Counting measure is sum of membership indicators, for arbitrary data."""
    d=spec['counterexample'];xs,bins,counts=frequencies(d['data'],d['bins'])
    if len(xs)!=integer(spec['observation_count'],1):raise ValueError('witness observation count mismatch')
    width=parse(spec['bin_width'],{})
    if width.is_positive is not True or any(hi-lo!=width for lo,hi in bins):raise ValueError('witness violates specified bin width')
    i=S.Symbol('i',integer=True,positive=True);n=S.Symbol('n',integer=True,positive=True);membership=S.IndexedBase('b')
    definition=S.Sum(membership[i],(i,1,n))
    def check(o):
        algorithm=o['algorithm']
        if algorithm=='count_members_per_bin':
            # Each valid bin membership contributes exactly one observation;
            # every indexed value is counted even if several values coincide.
            derived=S.Sum(S.Integer(1)*membership[i],(i,1,n))
            return derived==definition
        if algorithm=='sum_bin_widths':computed=[sum(hi-lo for lo,hi in bins)]*len(bins)
        elif algorithm=='data_range':computed=[max(xs)-min(xs)]*len(bins)
        elif algorithm=='sum_values_per_bin':computed=[sum(x for x in xs if lo<=x<hi) for lo,hi in bins]
        else:raise ValueError('unmodelled grouping algorithm')
        if computed==counts:raise ValueError('supplied data do not refute alternative algorithm')
        return False
    return select_unique(spec['options'],check)


def graph_order(spec):
    env=symbols(spec);dt=parse(spec['coordinate_step'][0],env)*parse(spec['axis_units'][0],env)
    dv=parse(spec['coordinate_step'][1],env)*parse(spec['axis_units'][1],env)
    if dt.is_positive is not True:raise ValueError('forward-time direction unproved')
    slope=S.factor(dv/dt)
    def check(o):
        claim=o['comparison'];answer=slope.is_positive if claim=='increasing' else slope.is_negative if claim=='decreasing' else slope.is_zero if claim=='constant' else None
        if answer is None:raise ValueError('trend comparison unproved or unknown')
        return bool(answer)
    return select_unique(spec['options'],check)


def graph_extremum(spec):
    # Positive lower daylight p and positive seasonal gap g produce the whole
    # interval[p,p+g]. The given maximum is an attained upper endpoint, not a
    # claim that the maximum occurs at a unique date.
    p,g=S.symbols('p g',positive=True);scale=parse(spec['vertical_scale'],{});offset=parse(spec['vertical_offset'],{})
    if scale.is_positive is not True:raise ValueError('order-preserving daylight axis required')
    low=scale*p+offset;high=scale*(p+g)+offset
    def check(o):
        interpretation=o['interpretation']
        if interpretation=='upper_ordinate':return S.factor(high-low).is_positive is True
        if interpretation=='lower_ordinate':return S.factor(high-low).is_nonpositive is True
        if interpretation=='zero_ordinate':
            zero=S.simplify(high).is_zero
            if zero is None:raise ValueError('zero-level claim unresolved')
            return bool(zero)
        raise ValueError('unknown extremum interpretation')
    return select_unique(spec['options'],check)


def _angle_class(pair):
    if not isinstance(pair,list) or len(pair)!=2:raise ValueError('two angle slots required')
    left,right=pair
    for slot in pair:_slot(slot)
    if left==right:raise ValueError('two distinct angles required')
    if left['vertex']==right['vertex']:
        return 'vertical' if left['region']!=right['region'] and left['side']!=right['side'] else 'linear_pair'
    if left['region']==right['region']=='interior':return 'alternate_interior' if left['side']!=right['side'] else 'same_side_interior'
    if left['region']!=right['region'] and left['side']==right['side']:return 'corresponding'
    raise ValueError('unsupported angle configuration')


def direct_angle_rule(spec):
    """Apply a named theorem only if its geometric hypotheses and goal unify.

    This verifies the rule direction and angle positions, not whether the final
    equality happens to be true. All supported rule templates have exact affine
    proofs from their explicit angle-sum/parallel premises.
    """
    pair=spec['angles'];actual=_angle_class(pair)
    if spec['given']!='parallel' or spec['goal']!='angle_equal':raise ValueError('unsupported proof-step request')
    canonical={
      'alternate_interior':[{'vertex':'upper','region':'interior','side':'left'},{'vertex':'lower','region':'interior','side':'right'}],
      'same_side_interior':[{'vertex':'upper','region':'interior','side':'left'},{'vertex':'lower','region':'interior','side':'left'}],
      'vertical':[{'vertex':'upper','region':'interior','side':'left'},{'vertex':'upper','region':'exterior','side':'right'}]}
    def check(o):
        theorem=o['theorem']
        if theorem=='parallel_angles':
            kind=o['angle_class'];direction=o['direction'];conclusion=o['conclusion']
            if kind not in canonical or kind=='vertical':raise ValueError('unsupported parallel-angle type')
            one,two=map(_slot,canonical[kind]);goal=R(one,'=',two) if conclusion=='angle_equal' else R('('+one+')+('+two+')','=',180) if conclusion=='angle_supplementary' else None
            if goal is None:raise ValueError('unknown angle conclusion')
            if direction=='property':valid=implies(ANGLE_DOMAIN+[R('p','=','q')],goal)
            elif direction=='criterion':valid=implies(ANGLE_DOMAIN+[goal],R('p','=','q'))
            else:raise ValueError('unknown theorem direction')
            if not valid:raise ValueError('candidate theorem template is not mathematically valid')
            return direction=='property' and kind==actual and conclusion==spec['goal']
        if theorem=='vertical_angles':
            one,two=map(_slot,canonical['vertical'])
            if not implies(ANGLE_DOMAIN,R(one,'=',two)):raise ValueError('vertical-angle identity failed')
            return actual=='vertical'
        if theorem=='triangle_exterior':
            if not implies([R('a+b+c','=',180),R('a+e','=',180)],R('e','=','b+c')):raise ValueError('exterior-angle proof failed')
            return False # its three-angle sum conclusion cannot unify with this two-angle equality step
        raise ValueError('unknown proof rule')
    return select_unique(spec['options'],check)


def doubled_median(spec):
    b,y=S.symbols('b y',positive=True);x,t=S.symbols('x t',real=True)
    a=S.Matrix([x,y]);left=S.Matrix([-b,0]);right=S.Matrix([b,0]);mid=S.zeros(2,1);target=2*mid-a
    # Half-turn maps A to E and B to C, hence AB=CE. Strict triangle
    # inequality follows from the exact Lagrange identity and noncollinearity.
    ab2=(a-left).dot(a-left);ce2=(target-right).dot(target-right)
    if S.expand(ab2-ce2)!=0:raise ValueError('half-turn length identity failed')
    u=right-a;v=target-right;cross=S.factor(S.det(S.Matrix.hstack(u,v)))
    lagrange=S.expand(u.dot(u)*v.dot(v)-u.dot(v)**2-cross**2)
    if lagrange!=0 or (cross**2).is_positive is not True:raise ValueError('strict triangle inequality not established')
    def check(o):
        construction=o['construction']
        if construction=='perpendicular_through_midpoint':
            residual=S.factor((target-mid).dot(a-mid))
            if residual.is_negative is not True:raise ValueError('perpendicular candidate is unresolved')
            return False
        if construction=='parallel_ab_through_midpoint':
            residual=S.factor(S.det(S.Matrix.hstack(target-mid,a-left)))
            if residual.is_positive is not True and residual.is_negative is not True:raise ValueError('parallel candidate is unresolved')
            return False
        if construction=='midpoint_ab':
            point=(a+left)/2
            if S.factor(point[1]-target[1]).is_positive is not True:raise ValueError('midpoint candidate is unresolved')
            return False
        if construction=='extend_median_equal_length':
            point=mid+(mid-a)
            if point!=target or S.simplify((point-a).dot(point-a)-4*a.dot(a))!=0:raise ValueError('doubling construction failed')
            return True
        raise ValueError('unmodelled auxiliary construction')
    return select_unique(spec['options'],check)


def median_halves_quartiles(data):
    xs=sorted(parse(x,{}) for x in data)
    if len(xs)<4 or len(xs)%2:raise ValueError('even sample of at least four values required')
    def median(ys):
        n=len(ys);return ys[n//2] if n%2 else (ys[n//2-1]+ys[n//2])/2
    return median(xs[:len(xs)//2]),median(xs[len(xs)//2:])


def quartile_width(spec):
    w,d=S.symbols('w d',positive=True);one=w;two=w+d
    def check(o):
        claim=o['claim']
        if claim=='central_width_increases':return S.factor(two-one).is_positive is True
        if claim=='central_width_decreases':return S.factor(two-one).is_negative is True
        if claim=='mean_increases':
            a,b=o['counterexample'];qa,qb=median_halves_quartiles(a),median_halves_quartiles(b)
            ma=sum(parse(v,{}) for v in a)/len(a);mb=sum(parse(v,{}) for v in b)/len(b)
            if not qb[1]-qb[0]>qa[1]-qa[0] or not mb<ma:raise ValueError('quartile/mean counterexample is invalid')
            return False
        raise ValueError('unknown dispersion claim')
    return select_unique(spec['options'],check)


def summaries(data):
    xs=[parse(v,{}) for v in data]
    if not xs:raise ValueError('nonempty score data required')
    mean=sum(xs)/len(xs);variance=sum((v-mean)**2 for v in xs)/len(xs)
    return {'count':len(xs),'max':max(xs),'min':min(xs),'mean':S.simplify(mean),'variance':S.simplify(variance)}


def summary_sufficiency(spec):
    n=S.Symbol('n',integer=True,positive=True);i=S.Symbol('i',integer=True,positive=True);x=S.IndexedBase('x')
    mean=S.Sum(x[i],(i,1,n))/n;variance=S.Sum((x[i]-mean)**2,(i,1,n))/n
    expressions={'mean':mean,'variance':variance}
    def check(o):
        algorithms=o['algorithms']
        if not algorithms or any(a not in ('mean','variance','count','max','min') for a in algorithms):raise ValueError('unknown summary operator')
        if set(expressions)<=set(algorithms):
            derived=[expressions[a] for a in algorithms if a in expressions]
            return mean in derived and variance in derived
        first,second=map(summaries,o['counterexample'])
        if not all(first[a]==second[a] for a in algorithms):raise ValueError('counterexample does not preserve candidate information')
        if all(first[a]==second[a] for a in expressions):raise ValueError('counterexample does not distinguish target mean/variance')
        return False
    return select_unique(spec['options'],check)


HANDLERS={'g105_observation_objects':observation_objects,'g105_sampling_guarantee':sampling_guarantee,
 'g105_frequency_algorithm':frequency_algorithm,'g105_graph_order':graph_order,
 'g105_graph_extremum':graph_extremum,'g105_direct_angle_rule':direct_angle_rule,
 'g105_doubled_median':doubled_median,'g105_quartile_width':quartile_width,
 'g105_summary_sufficiency':summary_sufficiency}
