"""Exact finite-population SRS moments, qualification and claim countermodels.

First/pair inclusion probabilities are counted before moments are derived.
Examples are legal proof witnesses, not school measurements. Nonpopulation
frames are disqualified by the stated task, never declared inherently biased.
"""
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from itertools import combinations
from math import comb
import sympy as S
from model_types import select_unique
from models_applications_20 import finite_set
from models_applications_36 import _number, _record


DATA_MODEL='fixed_population_values_read_exactly_with_full_response'


def _integer(value,lower=0):
    if type(value)is not int or value<lower or value.bit_length()>128:
        raise ValueError('bounded native count in the original integer domain required')
    return value


def _q(value):
    try:return _number(value)
    except (ValueError,TypeError,ArithmeticError) as error:
        raise ValueError('bounded exact finite measurement required') from error


@lru_cache(maxsize=1)
def srs_moment_certificate():
    n=S.Symbol('n',integer=True,positive=True);q=S.Symbol('q',integer=True,nonnegative=True)
    total=n+q
    first=S.combsimp(S.binomial(total-1,n-1)/S.binomial(total,n))
    if S.cancel(first-n/total)!=0:raise ValueError('first inclusion count failed')
    # n>=2 chart. For n=1 a sample cannot contain two distinct members.
    r=S.Symbol('r',integer=True,nonnegative=True);draws=r+2;size=draws+q
    pair=S.combsimp(S.binomial(size-2,draws-2)/S.binomial(size,draws))
    if S.cancel(pair-draws*(draws-1)/(size*(size-1)))!=0:
        raise ValueError('pair inclusion count failed')
    size_one=q+2
    if S.binomial(size_one-2,-1)/S.binomial(size_one,1)!=0:
        raise ValueError('single-draw pair inclusion must be zero')
    # A full N=1 population has just its singleton sample: no N-1 division.
    value=S.Symbol('value',real=True)
    if S.cancel(value/1-value)!=0 or S.cancel(value*value-value*value)!=0:
        raise ValueError('singleton-population moment failed')
    N,k,A,B=S.symbols('N k A B',real=True)
    pi1=k/N;pi2=k*(k-1)/(N*(N-1))
    expectation=pi1*A/k
    mean_residual=S.cancel(expectation-A/N)
    if mean_residual!=0:raise ValueError('all-population mean identity failed')
    second_moment=(pi1*B+pi2*(A*A-B))/(k*k)
    variance=S.cancel(second_moment-(A/N)**2)
    expected=(N-k)/(k*(N-1))*(B/N-(A/N)**2)
    if S.cancel(variance-expected)!=0:raise ValueError('finite-population variance derivation failed')
    # Binary y_i²=y_i: sum squares=sum positives=M.
    M=S.Symbol('M',real=True);p=M/N
    binary=S.cancel(variance.subs({A:M,B:M}))
    formula=p*(1-p)*(N-k)/(k*(N-1))
    if S.cancel(binary-formula)!=0:raise ValueError('binary variance simplification failed')
    if S.cancel(binary.subs(M,0))!=0 or S.cancel(binary.subs(M,N))!=0 or S.cancel(binary.subs(k,N))!=0:
        raise ValueError('constant-status or census variance endpoint failed')
    # Strict improvement for every nondegenerate p and 1<=k<l<=N.
    l=S.Symbol('l',real=True)
    difference=S.cancel(formula-formula.subs(k,l))
    factor=p*(1-p)*N*(l-k)/(k*l*(N-1))
    if S.cancel(difference-factor)!=0:raise ValueError('sample-size variance comparison failed')
    a,b=S.symbols('a b',positive=True)
    x,y,z=S.symbols('x y z',integer=True,nonnegative=True)
    small=x+1;large=small+y+1;population=large+z
    positive=(a*b/(a+b)**2)*population*(large-small)/(small*large*(population-1))
    if S.factor(positive).is_positive is not True:raise ValueError('strict nondegenerate variance improvement unresolved')
    return {'first':first,'pair':pair,'mean':expectation,'mean_residual':mean_residual,'binary_variance':binary}


class BinarySRS:
    def __init__(self,size,positives):
        self.size=_integer(size,1);self.positives=_integer(positives)
        if self.positives>self.size:raise ValueError('positive-status count exceeds population')
        srs_moment_certificate()

    def moments(self,count):
        count=_integer(count,1)
        if count>self.size:raise ValueError('SRS sample exceeds the full population')
        p=Fraction(self.positives,self.size)
        if self.size==1:return p,Fraction(0)
        first=Fraction(count,self.size)
        pair=Fraction(count*(count-1),self.size*(self.size-1))
        mean=first*self.positives/count
        second=(first*self.positives+pair*self.positives*(self.positives-1))/(count*count)
        variance=second-mean*mean
        if mean!=p or variance<0:raise ValueError('indicator moment execution failed')
        if variance!=p*(1-p)*Fraction(self.size-count,count*(self.size-1)):
            raise ValueError('derived and simplified variances disagree')
        return mean,variance


@dataclass(frozen=True)
class Design:
    qualified:bool
    variance:object
    reason:str


class VarianceComparison:
    def __init__(self,population,minimum,condition,goal):
        _record(population,('size','positives'))
        self.population=BinarySRS(population['size'],population['positives']);self.N=self.population.size
        if self.N<_integer(minimum,1):raise ValueError('population does not meet the stated size premise')
        if condition=='both_statuses_present':
            if not 0<self.population.positives<self.N:raise ValueError('the stated nondegenerate population premise is false')
        elif condition!='no_additional_status_condition':raise ValueError('unknown status-count premise')
        _record(goal,('design','statistic','comparison'))
        if goal!={'design':'full_population_uniform_without_replacement','statistic':'sample_proportion','comparison':'minimum_design_variance'}:
            raise ValueError('the exact SRS estimator and design-variance target must be stated')

    def frame(self,node):
        if not isinstance(node,dict):raise ValueError('a mathematical sampling frame required')
        if node.get('op')=='population':
            _record(node,('op',));return finite_set(self.N,[[0,self.N]])
        _record(node,('op','intervals'))
        if node['op']!='interval_union':raise ValueError('unknown finite frame')
        return finite_set(self.N,node['intervals'])

    def plan(self,node):
        if not isinstance(node,dict):raise ValueError('complete selection plan required')
        op=node.get('op')
        if op=='uniform_without_replacement':
            _record(node,('op','frame','size','statistic'))
            frame=self.frame(node['frame']);count=_integer(node['size'],1)
            if not frame.size or count>frame.size:raise ValueError('the proposed uniform sampling law is infeasible')
            if node['statistic']!='sample_proportion':raise ValueError('unknown estimator, not a variance verdict')
            if frame.size!=self.N:
                return Design(False,None,'not_the_full_population_frame')
            return Design(True,self.population.moments(count)[1],'qualified_full_population_SRS')
        if op=='restricted_frame_plan':
            _record(node,('op','frame','frame_relation','requested_count'))
            frame=self.frame(node['frame'])
            if node['frame_relation']!='nonempty_proper_subset' or not 0<frame.size<self.N:
                raise ValueError('the stated nonpopulation-frame premise is not established')
            request=node['requested_count']
            if not isinstance(request,dict):raise ValueError('explicit known or unspecified requested count required')
            if request.get('op')=='constant':
                _record(request,('op','value'));_integer(request['value'],1)
            elif request.get('op')=='unspecified':_record(request,('op',))
            else:raise ValueError('unknown requested-count claim')
            # A rejected candidate is NOT executed as a legal random sample.
            # At N=200 its proper frame may be too small to supply200 people;
            # it is still not the specified full-school design. No mean,
            # variance or bias of this unqualified plan is asserted.
            return Design(False,None,'known_nonpopulation_frame_not_qualified')
        raise ValueError('unsupported sampling plan')


def minimum_binary_variance(spec):
    _record(spec,('kind','data_model','population','minimum_population_size','population_condition','goal','options'))
    if spec['kind']!='app16_minimum_binary_srs_variance' or spec['data_model']!=DATA_MODEL:
        raise ValueError('typed design variance comparison with exact fixed data required')
    proof=VarianceComparison(spec['population'],spec['minimum_population_size'],spec['population_condition'],spec['goal'])
    options=spec['options']
    if not isinstance(options,list) or not 1<=len(options)<=16:raise ValueError('bounded candidates required')
    results={}
    for index,option in enumerate(options):
        _record(option,('key','text','plan'));results[index]=proof.plan(option['plan'])
    eligible=[result.variance for result in results.values() if result.qualified]
    if not eligible:raise ValueError('no qualified full-population design')
    best=min(eligible)
    # select_unique validates all keys/text as well and rejects true variance
    # ties, notably p=0/1 or duplicate sample sizes; it never favors a letter.
    by_identity={id(option):results[index] for index,option in enumerate(options)}
    return select_unique(options,lambda option:by_identity[id(option)].qualified and by_identity[id(option)].variance==best)


@dataclass(frozen=True)
class Law:
    size:int
    samples:tuple
    expectation:Fraction
    variance:Fraction
    population_mean:Fraction


def population_values(values):
    if not isinstance(values,list) or not 1<=len(values)<=12:raise ValueError('bounded nonempty numeric counterpopulation required')
    return tuple(_q(value) for value in values)


def indices(values,total):
    if not isinstance(values,list) or not values:raise ValueError('nonempty distinct index list required')
    result=tuple(_integer(value) for value in values)
    if len(set(result))!=len(result) or any(value>=total for value in result):raise ValueError('sample/frame membership is not a valid subset')
    return result


def execute_law(values,node):
    values=population_values(values);total=len(values)
    if not isinstance(node,dict):raise ValueError('complete finite sampling law required')
    if node.get('op')=='uniform_subsets':
        _record(node,('op','frame','size'));frame=indices(node['frame'],total);count=_integer(node['size'],1)
        if count>len(frame):raise ValueError('the sample exceeds its given frame')
        weight=Fraction(1,comb(len(frame),count))
        draws=tuple((sample,weight) for sample in combinations(frame,count))
    elif node.get('op')=='fixed_sample':
        _record(node,('op','members'));sample=indices(node['members'],total);count=len(sample)
        draws=((sample,Fraction(1)),)
    else:raise ValueError('unknown countermodel sampling law')
    samples=tuple((sample,weight,sum((values[i] for i in sample),Fraction(0))/len(sample)) for sample,weight in draws)
    if sum(weight for _,weight,_ in samples)!=1 or any(weight<=0 for _,weight,_ in samples):
        raise ValueError('the finite law is not a probability distribution')
    expectation=sum((weight*mean for _,weight,mean in samples),Fraction(0))
    variance=sum((weight*(mean-expectation)**2 for _,weight,mean in samples),Fraction(0))
    population_mean=sum(values,Fraction(0))/total
    return Law(count,samples,expectation,variance,population_mean)


class MeanClaims:
    def __init__(self,counterexamples):
        _record(counterexamples,('single_srs_error','larger_sample','frame_only'))
        one=_record(counterexamples['single_srs_error'],('population','sampling'))
        self.one=execute_law(one['population'],one['sampling'])
        if (one['sampling']['op']!='uniform_subsets'
                or set(one['sampling']['frame'])!=set(range(len(one['population'])))):
            raise ValueError('single-sample counterexample must obey full-population SRS')
        if self.one.expectation!=self.one.population_mean:raise ValueError('SRS example violates the general mean theorem')
        if not any(mean!=self.one.population_mean and weight>0 for _,weight,mean in self.one.samples):
            raise ValueError('this example does not refute a universal single-sample equality guarantee')
        big=_record(counterexamples['larger_sample'],('population','smaller','larger'))
        self.small=execute_law(big['population'],big['smaller']);self.large=execute_law(big['population'],big['larger'])
        if self.small.size>=self.large.size:raise ValueError('a genuinely larger sample required')
        min_small=min(abs(mean-self.small.population_mean) for _,_,mean in self.small.samples)
        max_large=max(abs(mean-self.large.population_mean) for _,_,mean in self.large.samples)
        if max_large<=min_small:raise ValueError('the lawful larger-sample counterexample is not worse')
        frame=_record(counterexamples['frame_only'],('population','frame','sampling'))
        allowed=indices(frame['frame'],len(frame['population']));self.frame_law=execute_law(frame['population'],frame['sampling'])
        if any(not set(sample)<=set(allowed) for sample,_,_ in self.frame_law.samples):raise ValueError('countermodel law leaves its stated acquaintance frame')
        if self.frame_law.expectation==self.frame_law.population_mean:raise ValueError('the supplied frame law is not a bias counterexample')
        srs_moment_certificate()

    def claim(self,node,budget=None):
        if budget is None:budget=[0]
        budget[0]+=1
        if budget[0]>64 or not isinstance(node,dict):raise ValueError('bounded complete statistical claim required')
        op=node.get('op')
        if op=='all':
            _record(node,('op','claims'))
            if not isinstance(node['claims'],list) or not 1<=len(node['claims'])<=8:raise ValueError('bounded conjunction required')
            return all([self.claim(child,budget) for child in node['claims']])
        _record(node,('op',))
        if op=='full_srs_sample_mean_is_design_unbiased':
            return srs_moment_certificate()['mean_residual']==0 # symbolic all-N identity, not an example estimate
        if op=='not_all_single_srs_samples_equal_population_mean':
            return any(weight>0 and mean!=self.one.population_mean for _,weight,mean in self.one.samples)
        if op=='larger_sample_cannot_have_larger_error_regardless_of_selection':
            return max(abs(mean-self.large.population_mean) for _,_,mean in self.large.samples)<=min(abs(mean-self.small.population_mean) for _,_,mean in self.small.samples)
        if op=='frame_only_selection_guarantees_design_unbiased':
            return self.frame_law.expectation==self.frame_law.population_mean
        raise ValueError('unknown claim cannot be treated as false')


def mean_design_claims(spec):
    _record(spec,('kind','data_model','target','counterexamples','options'))
    if (spec['kind']!='app16_mean_design_claims' or spec['data_model']!=DATA_MODEL
            or spec['target']!='finite_population_mean_design_expectation_and_realized_error'):
        raise ValueError('the explicit expectation-versus-error target is required')
    proof=MeanClaims(spec['counterexamples'])
    def check(option):
        _record(option,('key','text','claim'));return proof.claim(option['claim'])
    return select_unique(spec['options'],check)


HANDLERS={'app16_minimum_binary_srs_variance':minimum_binary_variance,
          'app16_mean_design_claims':mean_design_claims}
