"""Exact branch enumeration, calibration guarantees and finite game evidence.

Candidate text is never inspected. Mathematical trees specify experiments,
axis-rule families or explicit logical claims. Finite witnesses only refute a
guarantee; positive claims use exhaustive enumeration or symbolic identities.
"""
from collections import Counter
from fractions import Fraction
from itertools import product
from math import comb
import re
import sympy as S
from model_types import select_unique
from models_applications_36 import _number, _record


def _q(value):
    try:
        return _number(value)
    except (ValueError,TypeError,ArithmeticError) as error:
        raise ValueError('bounded exact rational input required') from error


def _label(value):
    if not isinstance(value,str) or not re.fullmatch('[A-Za-z甲乙丙丁][A-Za-z0-9_]{0,19}',value):
        raise ValueError('bounded event/player label required')
    return value


def _integer(value, lower, upper):
    value = _q(value)
    if value.denominator != 1 or not lower <= value <= upper:
        raise ValueError('integer outside the declared domain')
    return int(value)


def _trial_values(node):
    if not isinstance(node,dict):raise ValueError('finite trial description required')
    op = node.get('op')
    if op == 'finite_outcomes':
        _record(node,('op','values')); values=node['values']
    elif op == 'draw_with_replacement':
        _record(node,('op','population')); values=node['population']
    else:raise ValueError('unknown single-result trial')
    if not isinstance(values,list) or not 1 <= len(values) <= 12:
        raise ValueError('bounded nonempty outcome set required')
    values=tuple(_label(value) for value in values)
    if len(set(values)) != len(values):raise ValueError('single-trial outcomes must be distinct')
    return values


def experiment_tree(node):
    """Return all ordered outcomes and its prefix tree, not probabilities.

    Factors are single-result coordinates. In a simultaneous product they are
    ordered record components, NOT successive physical times. The declared
    nondeterministic product permits every factor combination; no inference
    of probabilistic independence is made from marginal uniformity.
    """
    if not isinstance(node,dict):raise ValueError('typed experiment required')
    op=node.get('op')
    if op == 'repeat':
        _record(node,('op','count','trial'))
        count=_integer(node['count'],1,6); factors=[_trial_values(node['trial'])]*count
    elif op in ('sequential_product','simultaneous_product'):
        _record(node,('op','factors'))
        if not isinstance(node['factors'],list) or not 1 <= len(node['factors']) <= 6:
            raise ValueError('bounded ordered result factors required')
        factors=[_trial_values(trial) for trial in node['factors']]
    else:raise ValueError('unknown experiment constructor')
    size=1
    for factor in factors:size*=len(factor)
    if size > 4096:raise ValueError('outcome space outside enumeration budget')
    outcomes=tuple(product(*factors)); tree={}
    for outcome in outcomes:
        cursor=tree
        for value in outcome:cursor=cursor.setdefault(value,{})
    paths=[]
    def visit(cursor,prefix):
        if not cursor:
            paths.append(prefix);return
        for value,child in cursor.items():visit(child,prefix+(value,))
    visit(tree,())
    if len(paths)!=size or len(set(paths))!=size or set(paths)!=set(outcomes):
        raise ValueError('prefix-tree paths do not bijectively enumerate all outcomes')
    if any(len(path)!=len(factors) for path in paths):raise ValueError('tree loses result coordinates')
    return {'components':len(factors),'outcomes':outcomes,'tree':tree,'paths':tuple(paths)}


def three_component_tree(spec):
    _record(spec,('kind','components','combination_semantics','options'))
    if spec['kind']!='app33_three_component_tree' or spec['combination_semantics']!='all_factor_combinations':
        raise ValueError('explicit ordered-product support required')
    components=_integer(spec['components'],1,6)
    def check(option):
        _record(option,('key','text','experiment'))
        result=experiment_tree(option['experiment'])
        return result['components']==components
    return select_unique(spec['options'],check)


def _piecewise(knots):
    if not isinstance(knots,list) or not 3<=len(knots)<=12:
        raise ValueError('a bounded increasing physical calibration required')
    rows=[]
    for knot in knots:
        if not isinstance(knot,list) or len(knot)!=2:raise ValueError('numeric tick and physical position required')
        rows.append(tuple(_q(value) for value in knot))
    if rows[0]!=(0,0) or any(x1>=x2 or y1>=y2 for (x1,y1),(x2,y2) in zip(rows,rows[1:])):
        raise ValueError('zero-origin strictly increasing calibration required')
    slopes=[(y2-y1)/(x2-x1) for (x1,y1),(x2,y2) in zip(rows,rows[1:])]
    if len(set(slopes))==1:raise ValueError('the proposed nonuniform witness is actually uniform')
    def height(value):
        for (x1,y1),(x2,y2),slope in zip(rows,rows[1:],slopes):
            if value<=x2:return y1+slope*(value-x1)
        x,y=rows[-1];return y+slopes[-1]*(value-x)
    return rows,height


def _calibration_guarantee(rule):
    if not isinstance(rule,dict):raise ValueError('axis-rule family required')
    kind=rule.get('family')
    if kind=='uniform_positive_scale':
        _record(rule,('family','baseline'))
        baseline=_q(rule['baseline']); a,x,y=S.symbols('a x y',positive=True)
        b=S.Rational(baseline.numerator,baseline.denominator)
        discrepancy=S.expand(a*(x-b)*y-a*(y-b)*x)
        if discrepancy==0:return True # ALL a>0 and ALL nonnegative x,y
        # A legal displayed pair stays above the chosen axis start. This
        # disproves the guarantee; no sampled pair proves the positive case.
        v=max(baseline,Fraction(0))+1; w=v+1
        if (v-baseline)*w==(w-baseline)*v:raise ValueError('truncated-origin counterexample failed')
        return False
    if kind=='arbitrary_origin_positive_scale':
        _record(rule,('family','witness'))
        witness=_record(rule['witness'],('scale','baseline','values'))
        scale,baseline=_q(witness['scale']),_q(witness['baseline'])
        values=witness['values']
        if scale<=0 or not isinstance(values,list) or len(values)!=2:
            raise ValueError('legal positive-scale display counterexample required')
        x,y=map(_q,values)
        if min(x,y)<=max(baseline,Fraction(0)) or x==y:
            raise ValueError('both displayed values must be distinct and above the axis start')
        discrepancy=scale*(x-baseline)*y-scale*(y-baseline)*x
        if discrepancy==0:raise ValueError('counterexample does not refute proportional heights')
        return False
    if kind=='unequal_physical_spacing_per_equal_value_difference':
        _record(rule,('family','witness'))
        witness=_record(rule['witness'],('knots','values'))
        rows,height=_piecewise(witness['knots'])
        values=witness['values']
        if not isinstance(values,list) or len(values)!=2:raise ValueError('two display values required')
        x,y=map(_q,values)
        if min(x,y)<=0 or x==y:raise ValueError('positive distinct comparison values required')
        if height(x)*y==height(y)*x:raise ValueError('nonuniform witness does not break the displayed ratio')
        return False
    raise ValueError('unknown axis-rule family')


def proportional_axis(spec):
    _record(spec,('kind','domain','encoding','requirement','options'))
    if (spec['kind']!='app33_proportional_axis' or spec['domain']!='all_nonnegative_values'
            or spec['encoding']!='upright_bar_height' or spec['requirement']!='preserve_all_value_ratios'):
        raise ValueError('the complete nonnegative proportional-height target is required')
    # More generally, f(x)*y=f(y)*x for all positive x,y forces
    # f(x)=f(1)*x (put y=1). Positive scale plus f(0)=0 suffices conversely.
    def check(option):
        _record(option,('key','text','rule'))
        return _calibration_guarantee(option['rule'])
    return select_unique(spec['options'],check)


class FairEvidence:
    def __init__(self,ideal,observed,goal):
        _record(ideal,('outcomes','probabilities_knowledge'))
        if ideal['probabilities_knowledge']!='ideal_single_trial_only':
            raise ValueError('current actual independence must not be silently assumed')
        rows=ideal['outcomes']
        if not isinstance(rows,list) or len(rows)!=2:raise ValueError('two ideal outcomes required')
        weights={}
        for row in rows:
            _record(row,('player','weight'));player=_label(row['player']);weight=_q(row['weight'])
            if player in weights or weight<=0:raise ValueError('distinct positive outcome weights required')
            weights[player]=weight
        self.players=tuple(sorted(weights));total=sum(weights.values())
        self.p={player:weight/total for player,weight in weights.items()}
        if len(set(self.p.values()))!=1:raise ValueError('this evidence problem specifies an equal-chance ideal game')
        _record(observed,('total','counts','actual_joint_law'))
        if observed['actual_joint_law']!='not_specified':raise ValueError('actual finite trials are not given an iid law')
        self.n=_integer(observed['total'],1,400);counts=observed['counts']
        if not isinstance(counts,list) or len(counts)!=2:raise ValueError('both observed counts required')
        self.counts={}
        for row in counts:
            _record(row,('player','count'));player=_label(row['player'])
            if player not in self.players or player in self.counts:raise ValueError('unknown or duplicate count label')
            self.counts[player]=_integer(row['count'],0,self.n)
        if sum(self.counts.values())!=self.n:raise ValueError('counts must exhaust all recorded trials')
        _record(goal,('op','players','quantity'))
        if (goal['op']!='equal' or goal['quantity']!='single_trial_win_probability'
                or not isinstance(goal['players'],list) or len(goal['players'])!=2
                or len(set(goal['players']))!=2 or set(goal['players'])!=set(self.players)):
            raise ValueError('the fairness goal must specify equal single-trial winning chances')
        # Construct a complete error-free trial log compatible with the counts.
        # Completing the ideal single-trial law by an independent product law
        # is one admissible world, NOT an assumption about the actual trials.
        self.trace=tuple(player for player in self.players for _ in range(self.counts[player]))
        self.record_valid=Counter(self.trace)==Counter(self.counts)
        self.path_probability=Fraction(1)
        for player in self.players:self.path_probability*=self.p[player]**self.counts[player]
        self.count_probability=comb(self.n,self.counts[self.players[0]])*self.path_probability
        self.valid_fair_world=self.record_valid and self.path_probability>0
        n,d,epsilon=S.symbols('n d e',positive=True)
        p=S.Rational(1,2)
        moment=S.cancel((n*p+n*(n-1)*p*p)/(n*n)-p*p)
        if S.cancel(moment-p*(1-p)/n)!=0:raise ValueError('all-n iid frequency variance proof failed')
        difference=S.cancel(moment-moment.subs(n,n+d))
        if S.factor(difference).is_positive is not True:
            raise ValueError('frequency variance monotonicity unresolved')
        if S.limit(moment/(epsilon*epsilon),n,S.oo)!=0:
            raise ValueError('Chebyshev all-epsilon concentration limit failed')
        self.variance_coefficient=Fraction(1,4)
        # A nonmonotonic path for any rational p=a/b: at n=b,k=a
        # frequency equals p; a next win makes deviation (1-p)/(b+1)>0.
        # Its probability is positive because all outcome probabilities are
        # positive and all multiplicities are nonnegative integers.
        value=self.p[self.players[0]];a,b=value.numerator,value.denominator
        self.witness=(b,a,(1-value)/(b+1))
        self.nonmonotone=(0<a<b and self.witness[2]>0)

    def _conclusion(self,node):
        _record(node,('op',))
        if node['op']=='unequal_probabilities':
            if not self.valid_fair_world:raise ValueError('fair-world counterexample not established')
            return False
        if node['op']=='invalid_recording_and_redesign':
            if not self.valid_fair_world:raise ValueError('valid-record counterexample not established')
            return False
        raise ValueError('unrecognized modal conclusion')

    def claim(self,node,budget=None):
        if budget is None:budget=[0]
        budget[0]+=1
        if budget[0]>80:raise ValueError('claim tree outside proof budget')
        if not isinstance(node,dict):raise ValueError('complete mathematical claim tree required')
        op=node.get('op')
        if op=='all':
            _record(node,('op','claims'))
            if not isinstance(node['claims'],list) or not 1<=len(node['claims'])<=8:raise ValueError('bounded conjunction required')
            results=[self.claim(claim,budget) for claim in node['claims']]
            return all(results)
        if op in ('forced_by_counts','not_forced_by_counts'):
            _record(node,('op','conclusion'));value=self._conclusion(node['conclusion'])
            return value if op=='forced_by_counts' else not value
        if op=='compatible_with_ideal':
            _record(node,('op',))
            return self.path_probability>0 and self.count_probability>0
        if op in ('iid_frequency_concentrates','no_stepwise_closeness_guarantee'):
            _record(node,('op','law','center'))
            if node['law']!='future_same_condition_iid':raise ValueError('future iid condition must be explicit')
            center=_q(node['center'])
            if center!=self.p[self.players[0]]:return False
            return self.variance_coefficient>0 if op=='iid_frequency_concentrates' else self.nonmonotone
        if op=='recommend_strict_advantage_from_counts':
            _record(node,('op','greater','less','target'))
            greater,less=_label(node['greater']),_label(node['less'])
            if {greater,less}!=set(self.players) or greater==less:raise ValueError('both distinct players required')
            if node['target']!='equal_single_trial_chances':raise ValueError('unknown recommendation objective')
            gap=S.Symbol('gap',positive=True)
            # Every proposed strict advantage has probability difference>0;
            # equality requires0. This refutes it as a fairness repair,
            # independent of compensation for historical gains or losses.
            if S.Eq(gap,0) is not S.false:raise ValueError('goal conflict was not established')
            return False
        raise ValueError('unknown claim: no verdict may be inferred')


def fair_game_evidence(spec):
    _record(spec,('kind','ideal','observed','goal','options'))
    if spec['kind']!='app33_fair_game_evidence':raise ValueError('typed finite game evidence required')
    proof=FairEvidence(spec['ideal'],spec['observed'],spec['goal'])
    def check(option):
        _record(option,('key','text','claim'))
        return proof.claim(option['claim'])
    return select_unique(spec['options'],check)


HANDLERS={'app33_three_component_tree':three_component_tree,
          'app33_proportional_axis':proportional_axis,
          'app33_fair_game_evidence':fair_game_evidence}
