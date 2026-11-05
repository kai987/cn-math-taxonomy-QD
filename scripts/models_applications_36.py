"""Exact spinner design and complete reference-only trial-protocol proof.

The mathematical input is the design, not a stored answer or a verdict. The
whole-reference grammar is intentionally narrow: it is an offline reference
check, never an automatic grader for arbitrary student game designs.
"""
from collections import Counter
from fractions import Fraction
from dataclasses import dataclass
import re
import sympy as S
from model_types import SelfReferenceProof


_NUMERIC_TRANSLATION = str.maketrans('０１２３４５６７８９＋－．／−', '0123456789+-./-')
_RATIONAL = r'[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:/[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+))?'


def _record(value, fields):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise ValueError('a complete typed record without extra fields is required')
    return value


def _number(value):
    if type(value) is int:
        text = str(value)
    elif isinstance(value, str) and len(value) <= 80:
        text = value.translate(_NUMERIC_TRANSLATION)
    else:
        raise ValueError('a bounded exact rational is required')
    # Check raw tokens before any broad Unicode normalization. Chinese stops,
    # superscripts, circled digits and separated numerals are not decimals.
    if not re.fullmatch(_RATIONAL, text):
        raise ValueError('unsupported exact rational spelling')
    numerator, *denominator = text.split('/')
    result = Fraction(numerator) / (Fraction(denominator[0]) if denominator else 1)
    if max(abs(result.numerator).bit_length(), result.denominator.bit_length()) > 256:
        raise ValueError('rational outside the arithmetic budget')
    return result


def _owner(value):
    if not isinstance(value, str) or not re.fullmatch('[A-Za-z甲乙丙丁]', value):
        raise ValueError('one bounded player identifier is required')
    return value


def _reference(value):
    if not isinstance(value, str) or len(value) > 2048:
        raise ValueError('a bounded complete reference is required')
    text = value.strip().translate(_NUMERIC_TRANSLATION).translate(str.maketrans({'，': ',', '、': ','}))
    # Keep sentence stops distinct from decimal points. No whitespace removal
    # may join numeric tokens, and no unknown suffix is silently discarded.
    if not text.endswith('。'):
        raise ValueError('the complete five-sentence reference must terminate')
    parts = text[:-1].split('。')
    if len(parts) != 5 or any(not part for part in parts):
        raise ValueError('all five reference claims are required exactly once')
    return parts


class SpinnerReferenceProof(SelfReferenceProof):
    def __init__(self, spinner, payoffs, trial):
        _record(spinner, ('radius', 'angle_unit', 'law', 'sectors', 'boundary'))
        self.radius = _number(spinner['radius'])
        if self.radius <= 0 or spinner['angle_unit'] != 'degree':
            raise ValueError('a positive-radius circular spinner in degrees is required')
        _record(spinner['law'], ('kind', 'start', 'period'))
        if (spinner['law']['kind'] != 'uniform_continuous_angle'
                or _number(spinner['law']['start']) != 0 or _number(spinner['law']['period']) != 360):
            raise ValueError('the full continuous uniform angular law must be explicit')
        if spinner['boundary'] not in ('respin', 'assign_clockwise'):
            raise ValueError('unknown boundary rule')
        self.boundary = spinner['boundary']
        rows = spinner['sectors']
        if not isinstance(rows, list) or not 2 <= len(rows) <= 16:
            raise ValueError('a bounded sector partition is required')
        sectors = []
        for row in rows:
            _record(row, ('start', 'end', 'winner'))
            start, end = _number(row['start']), _number(row['end'])
            if not 0 <= start < end <= 360:
                raise ValueError('a positive nonwrapping sector interval is required')
            sectors.append((start, end, _owner(row['winner'])))
        sectors.sort()
        cursor = Fraction(0)
        for start, end, _ in sectors:
            if start != cursor:
                raise ValueError('sector interiors must form a disjoint exhaustive full-circle partition')
            cursor = end
        if cursor != 360:
            raise ValueError('sector partition does not cover the circle')
        self.owners = tuple(sorted({owner for _, _, owner in sectors}))
        if len(self.owners) != 2:
            raise ValueError('exactly two distinct players are required')
        lengths = {owner: Fraction(0) for owner in self.owners}
        components = []
        for start, end, owner in sectors:
            lengths[owner] += end - start
            if not components or components[-1] != owner:
                components.append(owner)
        # The zero-angle cut may split a single connected circular sector.
        if len(components) > 1 and components[0] == components[-1]:
            components.pop()
        self.two_sectors = len(components) == 2
        self.angles = lengths
        # Integrating uniform angular density1/360 on each disjoint interval
        # gives its length/360. Finite boundary points have measure0; respins
        # therefore leave these winning probabilities unchanged.
        self.probabilities = {owner: lengths[owner] / 360 for owner in self.owners}
        if sum(self.probabilities.values()) != 1:
            raise ValueError('angular probability does not normalize')
        if not isinstance(payoffs, list) or len(payoffs) != 2:
            raise ValueError('both players need explicit gains and loss costs')
        self.payoffs = {}
        for payoff in payoffs:
            _record(payoff, ('player', 'win_reward', 'loss_cost'))
            player = _owner(payoff['player'])
            reward, cost = _number(payoff['win_reward']), _number(payoff['loss_cost'])
            if player not in self.owners or player in self.payoffs or reward < 0 or cost < 0:
                raise ValueError('payoff players must be unique and amounts nonnegative')
            self.payoffs[player] = (reward, cost)
        self.expectations = {owner: self.probabilities[owner] * self.payoffs[owner][0]
            - (1 - self.probabilities[owner]) * self.payoffs[owner][1] for owner in self.owners}
        self._trial(trial)
        p = self.probabilities[self.owners[0]]
        # Independence gives E[(sum Xi)^2]=n*p+n(n-1)*p²; subtracting p²
        # proves Var(relative frequency)=p(1-p)/n for EVERY positive integern.
        n = S.Symbol('n', integer=True, positive=True)
        exact_p = S.Rational(p.numerator, p.denominator)
        computed = S.cancel((n * exact_p + n * (n - 1) * exact_p**2) / n**2 - exact_p**2)
        coefficient = p * (1 - p)
        if S.cancel(computed - S.Rational(coefficient.numerator, coefficient.denominator) / n) != 0:
            raise ValueError('the iid variance identity failed')
        self.variance_coefficient = coefficient
        # For any epsilon>0, Chebyshev gives P(|frequency-p|>=epsilon)
        # <=p(1-p)/(n*epsilon²)->0. This is convergence in probability, never
        # a claim that a realised finite sequence approaches p monotonically.
        self.chebyshev_numerator = coefficient
        first, second = self.owners
        path = [first, second, first]
        before, after = self.run(path[:2]), self.run(path)
        self.nonmonotone_witness = {
            'path': tuple(path),
            'before': abs(before['frequencies'][first] - p),
            'after': abs(after['frequencies'][first] - p),
            'probability': p**2 * (1 - p)}
        # An alternative, genuinely biased continuous stopping density can
        # give the first region massq and the other1-q. Piecewise densities
        # q/angle1 and(1-q)/angle2 are positive and integrate exactly to1.
        q = Fraction(1, 3) if p != Fraction(1, 3) else Fraction(1, 4)
        self.alternative = {first: q, second: 1 - q}
        self.alternative_densities = {owner: self.alternative[owner] / lengths[owner] for owner in self.owners}
        integral = sum(self.alternative_densities[owner] * lengths[owner] for owner in self.owners)
        self.finite_nonidentification = (integral == 1 and q != p and 0 < p < 1
            and all(value > 0 for value in self.alternative_densities.values()))
        # For EVERY finite sequence with k first-player wins and n-k other
        # wins, both likelihoods p^k(1-p)^(n-k) and q^k(1-q)^(n-k) are >0:
        # each base is positive and every exponent a nonnegative integer.
        # Hence proximity of a finite frequency to1/2 cannot prove exact
        # physical fairness. It may still be useful statistical evidence.

    def _trial(self, trial):
        _record(trial, ('sampling', 'record', 'report'))
        if trial['sampling'] != {'op': 'product_law', 'base': 'spinner', 'conditions': 'fixed'}:
            raise ValueError('independent identical same-condition repetitions are required')
        if trial['record'] != {'op': 'count', 'input': {'op': 'winner_events'}}:
            raise ValueError('the protocol must tally every observed winner')
        if trial['report'] != {'op': 'divide', 'numerator': {'op': 'counts'},
                'denominator': {'op': 'length', 'input': {'op': 'winner_events'}}}:
            raise ValueError('each frequency must be its count divided by all trials')

    def run(self, sequence):
        if not isinstance(sequence, (list, tuple)) or not 1 <= len(sequence) <= 1024:
            raise ValueError('a bounded nonempty trial sequence is required')
        if any(not isinstance(owner, str) or owner not in self.owners for owner in sequence):
            raise ValueError('unknown outcomes may not be silently discarded')
        counts = Counter(sequence)
        result = {owner: counts[owner] for owner in self.owners}
        if sum(result.values()) != len(sequence):
            raise ValueError('the trial tally failed conservation')
        frequencies = {owner: Fraction(result[owner], len(sequence)) for owner in self.owners}
        if sum(frequencies.values()) != 1:
            raise ValueError('trial frequencies failed normalization')
        return {'counts': result, 'trials': len(sequence), 'frequencies': frequencies}

    def likelihood(self, sequence, alternative=False):
        counts = self.run(sequence)['counts']
        probabilities = self.alternative if alternative else self.probabilities
        result = Fraction(1)
        for owner in self.owners:
            result *= probabilities[owner] ** counts[owner]
        return result

    def matches(self, reference):
        try:
            claims = {}
            for part in _reference(reference):
                if part.startswith('把均匀转盘'):
                    match = re.fullmatch('把均匀转盘分为两个相等的(' + _RATIONAL + ')°扇区,分别标(.),(.)', part)
                    if not match or 'partition' in claims:
                        return False
                    angle, first, second = match.groups()
                    claims['partition'] = (self.two_sectors and first != second and {first, second} == set(self.owners)
                        and all(_number(angle) == value for value in self.angles.values()))
                elif part.startswith('指针落在哪一区'):
                    if part != '指针落在哪一区就由对应的人获胜,落在边界则重转,双方奖励和失败代价相同' or 'rules' in claims:
                        return False
                    claims['rules'] = self.boundary == 'respin' and len(set(self.payoffs.values())) == 1
                elif part.startswith('在指针停止方向'):
                    match = re.fullmatch('在指针停止方向均匀的理想模型下,两人获胜概率都为(' + _RATIONAL + ')°/(' + _RATIONAL + ')°=(' + _RATIONAL + '),所以理论上公平', part)
                    if not match or 'probability' in claims:
                        return False
                    angle, turn, probability = map(_number, match.groups())
                    claims['probability'] = (turn == 360 and all(angle == v for v in self.angles.values())
                        and angle / turn == probability == Fraction(1, 2)
                        and all(v == probability for v in self.probabilities.values())
                        and len(set(self.expectations.values())) == 1)
                elif part.startswith('可做大量'):
                    match = re.fullmatch('可做大量同条件独立试验,记录(.),(.)胜次并计算频率,以观察是否在(' + _RATIONAL + ')附近波动', part)
                    if not match or 'experiment' in claims:
                        return False
                    first, second, center = match.groups()
                    claims['experiment'] = (first != second and {first, second} == set(self.owners)
                        and all(_number(center) == v for v in self.probabilities.values())
                        and self.variance_coefficient > 0)
                elif part.startswith('试验只能提供经验依据'):
                    match = re.fullmatch('试验只能提供经验依据,有限次频率接近(' + _RATIONAL + ')不能证明公平,也不保证每增加一次试验都更接近(' + _RATIONAL + ')', part)
                    if not match or 'limits' in claims:
                        return False
                    centers = list(map(_number, match.groups()))
                    witness = self.nonmonotone_witness
                    claims['limits'] = (all(center == Fraction(1, 2) for center in centers)
                        and self.finite_nonidentification and witness['probability'] > 0
                        and witness['after'] > witness['before'])
                else:
                    return False
            return set(claims) == {'partition', 'rules', 'probability', 'experiment', 'limits'} and all(claims.values())
        except (ValueError, TypeError, ArithmeticError):
            return False


def spinner_reference(spec):
    _record(spec, ('kind', 'reference_only', 'spinner', 'payoffs', 'trial_protocol'))
    if spec['kind'] != 'app36_spinner_reference' or spec['reference_only'] is not True:
        raise ValueError('the explicit reference-only spinner contract is required')
    return SpinnerReferenceProof(spec['spinner'], spec['payoffs'], spec['trial_protocol'])


HANDLERS = {'app36_spinner_reference': spinner_reference}


@dataclass(frozen=True)
class DataAction:
    input_sort: str
    output_sort: str
    relation: str
    rows: tuple
    payload: tuple
    encoding: tuple = ()
    basis: object = None


def _label(value):
    if not isinstance(value, str) or not re.fullmatch('[A-Za-z][A-Za-z0-9_]{0,19}', value):
        raise ValueError('a bounded observation/action identifier is required')
    return value


class StatisticalActions:
    """Execute data transformations and retain their proved input/output links."""
    def __init__(self, records):
        if not isinstance(records, list) or not 1 <= len(records) <= 128:
            raise ValueError('nonempty finite daily sleep observations are required')
        rows = []
        for record in records:
            _record(record, ('day', 'hours'))
            day, value = _label(record['day']), _number(record['hours'])
            if not 0 <= value <= 24:
                raise ValueError('daily sleep hours must be in[0,24]')
            rows.append((day, value))
        if len({day for day, _ in rows}) != len(rows):
            raise ValueError('each day needs one unambiguous observation')
        self.rows = tuple(rows)
        self.completed = []

    def _input(self, node):
        if not isinstance(node, dict):
            raise ValueError('a typed data reference is required')
        if node == {'op': 'observed_rows'}:
            return DataAction('', 'observations', '', self.rows, self.rows)
        _record(node, ('op', 'index'))
        if (node['op'] != 'previous' or type(node['index']) is not int
                or not 0 <= node['index'] < len(self.completed)):
            raise ValueError('an existing earlier artifact is required')
        return self.completed[node['index']]

    def step(self, node):
        if not isinstance(node, dict):
            raise ValueError('a complete operation is required')
        op = node.get('op')
        if op == 'line_plot':
            _record(node, ('op', 'input', 'scale', 'offset'))
            original = self._input(node['input'])
            if original.output_sort != 'observations':
                raise ValueError('a line encoding needs observed numeric rows')
            a, b = _number(node['scale']), _number(node['offset'])
            if a <= 0:
                raise ValueError('an upward, strictly positive linear scale is required')
            x = S.Symbol('x', real=True)
            sa, sb = S.Rational(a.numerator,a.denominator), S.Rational(b.numerator,b.denominator)
            if S.cancel((sa*x+sb-sb)/sa-x) != 0:
                raise ValueError('the coordinate decoder is not universally inverse')
            # The ordered day legend is an injective x-code. Numeric values
            # are encoded reversibly; the all-x identity proves fidelity,
            # while decoding the actual records checks this execution too.
            points = tuple((i, a*hours+b) for i, (_,hours) in enumerate(original.rows))
            decoded = tuple((day,(height-b)/a) for (day,_),(i,height) in zip(original.rows,points))
            if decoded != original.rows:
                raise ValueError('line encoding changed the observed values')
            result = DataAction('observations', 'representation', 'reversible_encoding',
                original.rows, points, (a,b), original)
        elif op == 'argmin':
            _record(node, ('op', 'input'))
            chart = self._input(node['input'])
            if chart.output_sort != 'representation' or chart.relation != 'reversible_encoding':
                raise ValueError('argmin needs a faithfully encoded numeric chart')
            a,b = chart.encoding
            decoded = tuple((day,(height-b)/a) for (day,_),(_,height) in zip(chart.rows,chart.payload))
            if decoded != chart.rows:
                raise ValueError('the chart provenance does not reconstruct all observations')
            minimum = min(value for _,value in decoded)
            subjects = tuple(day for day,value in decoded if value == minimum)
            # Retain every minimizer, including all ties. The claim is both
            # true and exhaustive: exactly those days have the least value.
            if any((day in subjects) != (value == minimum) for day,value in decoded):
                raise ValueError('the extremal assertion is not complete')
            result = DataAction('representation', 'proposition', 'entailed_assertion',
                chart.rows, (subjects,minimum), basis=chart)
        elif op == 'propose':
            _record(node, ('op', 'input', 'action', 'targets'))
            claim = self._input(node['input'])
            if claim.output_sort != 'proposition' or claim.relation != 'entailed_assertion':
                raise ValueError('a suggestion must reference an established analysis result')
            if node['targets'] != {'op': 'claim_subjects'}:
                raise ValueError('proposal targets must be derived from the actual claim')
            action = _label(node['action'])
            result = DataAction('proposition', 'prescription', 'depends_on_assertion',
                claim.rows, (action,claim.payload[0]), basis=claim)
            # This constructs an action proposal with its factual basis.
            # It does not assert that the action is optimal or compulsory.
        else:
            raise ValueError('unknown statistical operation')
        self.completed.append(result)
        return result


_SIGNATURE_TYPES = {
    'reversible_encoding': (frozenset({'observations'}), 'representation'),
    'entailed_assertion': (frozenset({'observations','representation'}), 'proposition'),
    'depends_on_assertion': (frozenset({'proposition'}), 'prescription'),
    'partition_aggregate': (frozenset({'observations'}), 'frequency_table'),
    'new_observations': (frozenset({'instrument'}), 'observations'),
}


def _data_signature(value):
    _record(value, ('relation','inputs','output'))
    relation = value['relation']
    if not isinstance(relation,str) or relation not in _SIGNATURE_TYPES:
        raise ValueError('unknown mathematical data relation')
    inputs = value['inputs']
    if (not isinstance(inputs,list) or not inputs or any(not isinstance(v,str) for v in inputs)
            or len(set(inputs)) != len(inputs)):
        raise ValueError('distinct declared input sorts required')
    if (frozenset(inputs),value['output']) != _SIGNATURE_TYPES[relation]:
        raise ValueError('the relation definition has an inconsistent typed signature')
    return relation,frozenset(inputs),value['output']


def statistical_action_signatures(spec):
    _record(spec, ('kind','records','actions','options'))
    if spec['kind'] != 'app36_statistical_action_signatures':
        raise ValueError('a typed statistical-action proof is required')
    actions = spec['actions']
    if not isinstance(actions,list) or not 1 <= len(actions) <= 16:
        raise ValueError('a bounded ordered action sequence is required')
    execution = StatisticalActions(spec['records'])
    proved = [execution.step(node) for node in actions]
    def check(option):
        _record(option, ('key', 'text', 'signatures'))
        signatures = option.get('signatures')
        if not isinstance(signatures,list) or len(signatures) != len(proved):
            raise ValueError('every action needs exactly one candidate definition')
        definitions = [_data_signature(value) for value in signatures]
        results = [relation == actual.relation and actual.input_sort in inputs and output == actual.output_sort
            for (relation,inputs,output),actual in zip(definitions,proved)]
        return all(results)
    from model_types import select_unique
    return select_unique(spec['options'], check)


HANDLERS['app36_statistical_action_signatures'] = statistical_action_signatures
