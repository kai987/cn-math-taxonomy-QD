"""Route-compensation guarantees and exact fraction-free substitution steps.

Opaque nongeometric premises stay free: a countermodel may make them true.
They are never classified as false facts.  Candidate policies and algebraic
actions are executed, and unsupported syntax or unproved domains reject.
"""
from dataclasses import dataclass
from fractions import Fraction
import re
import sympy as S

from model_types import select_unique


def _record(value, fields):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise ValueError('complete typed record without extra fields required')
    return value


def _q(value):
    if type(value) is int:
        text = str(value)
    elif isinstance(value, str) and len(value) <= 64:
        text = value.translate(str.maketrans('０１２３４５６７８９＋－．／−', '0123456789+-./-'))
    else:
        raise ValueError('bounded exact rational required')
    atom = r'[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)'
    if re.fullmatch(atom + '(?:/' + atom + ')?', text) is None:
        raise ValueError('unsupported numeric spelling')
    try:
        parts = text.split('/')
        number = Fraction(parts[0]) / (Fraction(parts[1]) if len(parts) == 2 else 1)
    except ArithmeticError as error:
        raise ValueError('undefined rational') from error
    if max(abs(number.numerator).bit_length(), number.denominator.bit_length()) > 256:
        raise ValueError('number exceeds arithmetic budget')
    return number


def _s(number):
    return S.Rational(number.numerator, number.denominator)


def _name(value):
    if not isinstance(value, str) or re.fullmatch('[a-z]', value) is None:
        raise ValueError('single lower-case variable required')
    return value


@dataclass(frozen=True)
class Quantity:
    expression: object
    length_power: int


class TrackGuarantee:
    def __init__(self, geometry, distance, target):
        _record(geometry, ('straight_pieces', 'arc_pieces', 'arc_shape', 'straight_relation', 'radius_relation',
                           'finish_relation', 'advance_measure', 'reference_lap'))
        if (type(geometry['straight_pieces']) is not int or geometry['straight_pieces'] != 2
                or type(geometry['arc_pieces']) is not int or geometry['arc_pieces'] != 2
                or geometry['arc_shape'] != 'semicircle'
                or geometry['straight_relation'] != 'equal_across_lanes'
                or geometry['radius_relation'] != 'outer_strictly_larger'
                or geometry['finish_relation'] != 'shared_finish_line'
                or geometry['advance_measure'] != 'along_lane_forward_distance'
                or geometry['reference_lap'] != 'inner_full_lap'
                or target != 'guarantee_equal_remaining_distance'):
            raise ValueError('two shared straights and two semicircles with larger outer radius required')
        self.distance = _q(distance)
        if self.distance <= 0:
            raise ValueError('positive target race distance required')
        self.t, self.g = S.symbols('t g', positive=True)
        length = _s(self.distance)
        # t=pi*r/s>0 and g=2*pi*d>0 parameterize EVERY r,s,d>0 with
        # 2s+2pi*r=L. Conversely r=L*t/(2pi(1+t)),s=L/(2(1+t)).
        self.radius = length*self.t/(2*S.pi*(1+self.t))
        self.straight = length/(2*(1+self.t))
        self.increment = self.g/(2*S.pi)
        r, s, d = S.symbols('r s d', positive=True)
        substitutions = {self.t:S.pi*r/s, self.g:2*S.pi*d}
        source_length = 2*s+2*S.pi*r
        for value, original in ((self.radius,r),(self.straight,s),(self.increment,d)):
            # For fixed rational L, prove the inverse with an independent L.
            symbolic_l = S.Symbol('l', positive=True)
            template = value / length * symbolic_l if original != d else value
            replacement = template.subs(substitutions).subs(symbolic_l,source_length)
            if S.cancel(replacement-original) != 0:
                raise ValueError('the full positive track parameterization is not invertible')
        inner_arc = S.cancel(2*S.pi*self.radius)
        straight_total = 2*self.straight
        if S.cancel(inner_arc+straight_total-length) != 0:
            raise ValueError('inner route does not equal the target distance')
        self.lengths = {
            ('straight_total','inner'):straight_total, ('straight_total','outer'):straight_total,
            ('curved_total','inner'):inner_arc, ('curved_total','outer'):inner_arc+self.g,
            ('full_lap','inner'):length, ('full_lap','outer'):length+self.g,
        }

    def term(self, node, budget=None):
        if budget is None: budget=[0]
        budget[0]+=1
        if budget[0]>40 or not isinstance(node,dict):
            raise ValueError('bounded geometric quantity tree required')
        op=node.get('op')
        if op=='length':
            _record(node,('op','part','lane'))
            key=(node['part'],node['lane'])
            if key not in self.lengths:raise ValueError('unknown track part or lane')
            return Quantity(self.lengths[key],1)
        if op in ('scalar','fixed_length'):
            _record(node,('op','value'))
            return Quantity(_s(_q(node['value'])),int(op=='fixed_length'))
        if op in ('add','subtract','multiply','divide'):
            _record(node,('op','left','right'))
            left,right=self.term(node['left'],budget),self.term(node['right'],budget)
            if op in ('add','subtract'):
                if left.length_power!=right.length_power:raise ValueError('incompatible dimensions')
                return Quantity(left.expression+(right.expression if op=='add' else -right.expression),left.length_power)
            if op=='multiply':
                power=left.length_power+right.length_power
                if power>1:raise ValueError('only scalar scaling of lengths supported')
                return Quantity(left.expression*right.expression,power)
            if right.length_power!=0 or right.expression.free_symbols or right.expression==0:
                raise ValueError('only nonzero constant scalar divisors are supported')
            return Quantity(left.expression/right.expression,left.length_power)
        raise ValueError('unknown quantity operation or unsupported original domain')

    def premise(self, node):
        if not isinstance(node,dict):raise ValueError('a typed premise required')
        if node.get('op')=='independent_claim':
            _record(node,('op','name'))
            if not isinstance(node['name'],str) or re.fullmatch('[a-z][a-z_]{0,39}',node['name']) is None:
                raise ValueError('bounded independent proposition name required')
            return node['name'],True
        _record(node,('op','left','right'))
        if node['op'] not in ('equal','greater','less'):raise ValueError('unknown geometric relation')
        left,right=self.term(node['left']),self.term(node['right'])
        if left.length_power!=right.length_power:raise ValueError('incompatible premise dimensions')
        difference=S.factor(S.cancel(left.expression-right.expression))
        if node['op']=='equal':
            if difference==0:return None,True
            if difference.is_zero is False:return None,False
        elif node['op']=='greater':
            if difference.is_positive is True:return None,True
            if difference.is_nonpositive is True:return None,False
        else:
            if difference.is_negative is True:return None,True
            if difference.is_nonnegative is True:return None,False
        raise ValueError('premise not proved on the full parameter domain')

    def inspect(self, explanation):
        _record(explanation,('premises','advance_policy','counterexample'))
        premises=explanation['premises']
        if not isinstance(premises,list) or not 1<=len(premises)<=12:raise ValueError('nonempty bounded premises required')
        interpreted=[self.premise(node) for node in premises]
        policy=explanation['advance_policy']
        if policy=={'op':'unspecified'}:
            advance=None
        else:
            advance=self.term(policy)
            if advance.length_power!=1:raise ValueError('advance must have length dimension')
        raw=explanation['counterexample'];witness=None
        if raw is not None:
            _record(raw,('shape_ratio','extra_arc','advance'))
            t,g,a=(_q(raw[k]) for k in ('shape_ratio','extra_arc','advance'))
            if t<=0 or g<=0 or not 0<a<self.distance+g:raise ValueError('counterexample must be a legal track and positive, nonwrapping advance')
            witness=(t,g,a)
        if any(not value for _,value in interpreted):
            if witness is not None:raise ValueError('inconsistent geometric premise has no satisfying counterexample')
            # A valid explanation must fit the stated geometry. This rejects
            # an inconsistent proposed fact, rather than using a vacuous
            # material implication to infer the target from contradiction.
            return {'guarantees':False,'reason':'inconsistent_geometric_premise'}
        if advance is not None:
            residual=S.cancel(self.lengths['full_lap','outer']-advance.expression-_s(self.distance))
            if residual==0:
                if (S.factor(advance.expression).is_positive is not True
                        or S.factor(self.lengths['full_lap','outer']-advance.expression).is_positive is not True):
                    raise ValueError('the policy is not proved legal throughout the domain')
                if witness is not None:raise ValueError('an identity cannot have a counterexample')
                return {'guarantees':True,'advance':advance.expression,'residual':residual}
        if witness is None:raise ValueError('a legal satisfying counterexample is required for non-guarantees')
        t,g,a=witness;assignment={self.t:_s(t),self.g:_s(g)}
        if advance is not None and S.cancel(advance.expression.subs(assignment)-_s(a))!=0:
            raise ValueError('counterexample does not execute the stated policy')
        if self.distance+g-a==self.distance:raise ValueError('the supposed counterexample is equal-route')
        # A product valuation makes EVERY independent premise true. This
        # refutes sufficiency without declaring real fitness/beauty facts false.
        return {'guarantees':False,'counterexample':witness,
                'external_valuation':{name:True for name,_ in interpreted if name is not None}}


def track_explanation(spec):
    _record(spec,('kind','geometry','race_distance','target','options'))
    if spec['kind']!='f29_track_explanation_guarantee':raise ValueError('typed track explanation model required')
    proof=TrackGuarantee(spec['geometry'],spec['race_distance'],spec['target'])
    def check(option):
        _record(option,('key','text','explanation'))
        return proof.inspect(option['explanation'])['guarantees']
    return select_unique(spec['options'],check)


def _variables(values):
    if not isinstance(values,list) or len(values)!=2:raise ValueError('two declared variables required')
    names=tuple(_name(v) for v in values)
    if len(set(names))!=2:raise ValueError('distinct variables required')
    return names


def _equation(row, names):
    _record(row,('coefficients','rhs'))
    coefficients=row['coefficients']
    if not isinstance(coefficients,dict) or set(coefficients)!=set(names):raise ValueError('complete affine coefficient row required')
    return tuple(_q(coefficients[name]) for name in names),_q(row['rhs'])


def _index(value):
    if type(value) is not int or value not in (0,1):raise ValueError('source/target equation index must be0 or1')
    return value


class SubstitutionActions:
    def __init__(self, variables, equations, target):
        self.variables=_variables(variables)
        if target!='equivalent_integral_linear_isolation_then_substitute':raise ValueError('explicit fraction-avoidance target required')
        if not isinstance(equations,list) or len(equations)!=2:raise ValueError('two source equations required')
        self.equations=tuple(_equation(row,self.variables) for row in equations)
        (a,b),u=self.equations[0];(c,d),v=self.equations[1]
        determinant=a*d-b*c
        if determinant==0:raise ValueError('a nonempty uniquely solvable source system is required')
        self.solution=((u*d-b*v)/determinant,(a*v-u*c)/determinant)
        if any(sum(c*x for c,x in zip(row,self.solution))!=rhs for row,rhs in self.equations):raise ValueError('source-system solution failed')

    def execute(self, program):
        if not isinstance(program,dict):raise ValueError('typed algebraic action required')
        op=program.get('op')
        if op=='scale_equation':
            _record(program,('op','from','factor'))
            row,rhs=self.equations[_index(program['from'])];factor=_q(program['factor'])
            if factor==0:raise ValueError('zero scaling loses equivalence')
            scaled=tuple(factor*c for c in row)
            return {'kind':'equation','coefficients':scaled,'rhs':factor*rhs}
        if op!='isolate_then_substitute':raise ValueError('unknown algebraic action')
        _record(program,('op','from','variable','into','rhs'))
        source,destination=_index(program['from']),_index(program['into'])
        if source==destination:raise ValueError('substitute into the other original equation')
        variable=_name(program['variable'])
        if variable not in self.variables:raise ValueError('undeclared isolated variable')
        i=self.variables.index(variable);j=1-i;other=self.variables[j]
        row,rhs=self.equations[source]
        if row[i]==0:raise ValueError('cannot isolate a zero-coefficient variable')
        expression=_record(program['rhs'],('constant','coefficients'))
        if not isinstance(expression['coefficients'],dict) or set(expression['coefficients'])!={other}:
            raise ValueError('the isolated right side must use only the other variable')
        supplied=(_q(expression['constant']),_q(expression['coefficients'][other]))
        derived=(rhs/row[i],-row[j]/row[i])
        equivalent=supplied==derived
        target_row,target_rhs=self.equations[destination]
        substituted=(target_row[j]+target_row[i]*supplied[1],target_rhs-target_row[i]*supplied[0])
        if equivalent and substituted[0]*self.solution[j]!=substituted[1]:raise ValueError('the substituted equation lost the original solution')
        return {'kind':'isolated_then_substituted','equivalent':equivalent,'rhs':supplied,
                'linear':supplied[1]!=0,'integral':all(value.denominator==1 for value in supplied),
                'substituted_equation':substituted}


def integral_substitution(spec):
    _record(spec,('kind','domain','variables','equations','target','options'))
    if spec['kind']!='f29_integral_substitution' or spec['domain']!='all_real':raise ValueError('typed real substitution model required')
    proof=SubstitutionActions(spec['variables'],spec['equations'],spec['target'])
    def check(option):
        _record(option,('key','text','program'))
        result=proof.execute(option['program'])
        return (result['kind']=='isolated_then_substituted' and result['equivalent']
                and result['linear'] and result['integral'])
    return select_unique(spec['options'],check)


HANDLERS={'f29_track_explanation_guarantee':track_explanation,
          'f29_integral_substitution':integral_substitution}
