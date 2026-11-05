"""Finite sampling support, with exact inclusion proofs and concrete set checks.

The target is positive inclusion opportunity for every population member.
Nothing here equates coverage with unbiasedness, small realized error, optimal
loss, or a globally simple random sample. Role names never determine subsets.
"""
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
import re
import sympy as S
from model_types import select_unique
from models_applications_36 import _record


def _integer(value,lower=0):
    if type(value) is not int or value<lower or value.bit_length()>128:
        raise ValueError('a bounded native integer in the original count domain is required')
    return value


def _name(value):
    if not isinstance(value,str) or not re.fullmatch('[A-Za-z][A-Za-z0-9_]{0,31}',value):
        raise ValueError('bounded frame identifier required')
    return value


@lru_cache(maxsize=1)
def inclusion_certificate():
    # K=n+q covers EVERY K>=n>=1, including the full-frame sample n=K.
    # A fixed member belongs to C(K-1,n-1) of the C(K,n) equally likely
    # n-subsets; the ratio is n/K>0 without assuming independence of draws.
    n=S.Symbol('n',integer=True,positive=True);q=S.Symbol('q',integer=True,nonnegative=True)
    k=n+q;ratio=S.combsimp(S.binomial(k-1,n-1)/S.binomial(k,n))
    if S.cancel(ratio-n/k)!=0 or ratio.is_positive is not True:
        raise ValueError('the all-count positive inclusion identity failed')
    if S.factor(1-ratio).is_nonnegative is not True or S.cancel(ratio.subs(q,0)-1)!=0:
        raise ValueError('the n=K inclusion endpoint was not established')
    return ratio


@dataclass(frozen=True)
class FiniteSet:
    population_size:int
    intervals:tuple

    @property
    def size(self):return sum(high-low for low,high in self.intervals)

    def contains(self,index):return any(low<=index<high for low,high in self.intervals)

    def complement(self):
        output=[];cursor=0
        for low,high in self.intervals:
            if cursor<low:output.append((cursor,low))
            cursor=high
        if cursor<self.population_size:output.append((cursor,self.population_size))
        return FiniteSet(self.population_size,tuple(output))


def finite_set(size,intervals):
    if not isinstance(intervals,list) or len(intervals)>128:
        raise ValueError('a bounded finite interval-union representation required')
    parsed=[]
    for interval in intervals:
        if not isinstance(interval,list) or len(interval)!=2:raise ValueError('half-open integer endpoints required')
        low,high=(_integer(value) for value in interval)
        if not 0<=low<high<=size:raise ValueError('interval is not a legal population subset')
        parsed.append((low,high))
    merged=[]
    for low,high in sorted(parsed):
        if merged and low<=merged[-1][1]:merged[-1]=(merged[-1][0],max(merged[-1][1],high))
        else:merged.append((low,high))
    result=FiniteSet(size,tuple(merged))
    if result.size+result.complement().size!=size:raise ValueError('subset and complement do not exhaust the population')
    return result


@dataclass(frozen=True)
class SamplingSupport:
    population_size:int
    support:FiniteSet
    components:tuple
    sample_size:object

    def probability(self,index):
        index=_integer(index)
        if index>=self.population_size:raise ValueError('member index is outside the population')
        matching=[chance for frame,chance in self.components if frame.contains(index)]
        if len(matching)>1:raise ValueError('sampling components were not a disjoint partition')
        if matching and matching[0] is None:
            raise ValueError('within-frame inclusion probabilities were not specified')
        return matching[0] if matching else Fraction(0)

    @property
    def all_positive(self):
        omitted=self.support.complement()
        if omitted.size:
            witness=omitted.intervals[0][0]
            if self.probability(witness)!=0:raise ValueError('the excluded-member witness is invalid')
            return False
        if not self.components or any(chance is None or chance<=0 for _,chance in self.components):
            raise ValueError('full set union alone does not establish positive probabilities')
        return self.support.size==self.population_size


class Coverage:
    def __init__(self,population,frames,constraints):
        _record(population,('op','size'))
        if population['op']!='index_range':raise ValueError('a finite indexed population required')
        self.n=_integer(population['size'],1)
        self.population=FiniteSet(self.n,((0,self.n),))
        if not isinstance(frames,dict) or len(frames)>32:raise ValueError('bounded mathematical frame definitions required')
        self.frames={}
        for name,node in frames.items():
            _name(name);_record(node,('op','intervals'))
            if node['op']!='interval_union':raise ValueError('frame membership must be supplied as an actual finite set')
            self.frames[name]=finite_set(self.n,node['intervals'])
        if not isinstance(constraints,list) or len(constraints)>32:raise ValueError('explicit frame constraints required')
        seen=set()
        for constraint in constraints:
            _record(constraint,('frame','relation'));name=_name(constraint['frame'])
            if name not in self.frames or name in seen:raise ValueError('unknown or duplicate constrained frame')
            if constraint['relation']!='nonempty_proper_subset':raise ValueError('unknown frame relation')
            if not 0<self.frames[name].size<self.n:raise ValueError('the supplied set does not satisfy its proper-frame premise')
            seen.add(name)
        inclusion_certificate()

    def frame(self,node):
        if not isinstance(node,dict):raise ValueError('a complete frame reference required')
        if node.get('op')=='population':
            _record(node,('op',));return self.population
        _record(node,('op','name'))
        if node['op']!='frame':raise ValueError('unknown frame operation')
        name=_name(node['name'])
        if name not in self.frames:raise ValueError('undeclared sampling frame')
        return self.frames[name]

    def _component(self,node):
        _record(node,('frame','size'))
        frame=self.frame(node['frame']);count=_integer(node['size'])
        if frame.size==0:raise ValueError('sampling frames and strata must be nonempty')
        if count>frame.size:raise ValueError('the distinct sample exceeds its frame')
        chance=Fraction(count,frame.size)
        if not 0<=chance<=1:raise ValueError('marginal inclusion is outside the probability domain')
        return frame,chance,count

    def sampling(self,node):
        if not isinstance(node,dict):raise ValueError('complete sampling procedure required')
        op=node.get('op')
        if op=='restricted_to_frame':
            _record(node,('op','frame'));frame=self.frame(node['frame'])
            if not frame.size:raise ValueError('an executable restricted frame must be nonempty')
            # This is a support UPPER BOUND, not an invented within-frame
            # distribution. Outside membership is impossible under every
            # such law; inside chances remain unknown. If the frame is the
            # entire population, no positive verdict may be inferred.
            return SamplingSupport(self.n,frame,((frame,None),),None)
        if op=='uniform_without_replacement':
            _record(node,('op','frame','size'))
            frame,chance,count=self._component({'frame':node['frame'],'size':node['size']})
            support=frame if count else FiniteSet(self.n,())
            return SamplingSupport(self.n,support,((frame,chance),),count)
        if op!='stratified_uniform_without_replacement':raise ValueError('unsupported sampling law; no inclusion probabilities may be assumed')
        _record(node,('op','strata'))
        if not isinstance(node['strata'],list) or not 1<=len(node['strata'])<=32:
            raise ValueError('a bounded nonempty complete partition required')
        components=[self._component(part) for part in node['strata']]
        intervals=sorted((low,high) for frame,_,_ in components for low,high in frame.intervals)
        cursor=0
        for low,high in intervals:
            if low!=cursor:raise ValueError('strata overlap or leave an omitted population segment')
            cursor=high
        if cursor!=self.n:raise ValueError('the supplied strata do not exhaust the population')
        # Within stratumh the same general counting proof gives n_h/N_h>0
        # when n_h>=1. A zero quota is a legal no-op with inclusion0, so
        # its nonempty stratum is omitted from the positive support.
        # Strata need not have equal sampling fractions; no global SRS,
        # proportional allocation, independence or estimator claim is made.
        positive_intervals=[[low,high] for frame,chance,_ in components if chance>0 for low,high in frame.intervals]
        union=finite_set(self.n,positive_intervals)
        return SamplingSupport(self.n,union,tuple((frame,chance) for frame,chance,_ in components),
                               sum(count for _,_,count in components))


def positive_inclusion_support(spec):
    _record(spec,('kind','population','frames','frame_constraints','target','options'))
    if (spec['kind']!='app20_positive_inclusion_support'
            or spec['target']!='every_population_member_has_positive_inclusion_probability'):
        raise ValueError('only the explicit population-support target is verified')
    context=Coverage(spec['population'],spec['frames'],spec['frame_constraints'])
    def check(option):
        _record(option,('key','text','sampling'))
        return context.sampling(option['sampling']).all_positive
    return select_unique(spec['options'],check)


HANDLERS={'app20_positive_inclusion_support':positive_inclusion_support}
