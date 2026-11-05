"""Typed data provenance and finite categorical aggregation for the 41 review.

The trees specify actual input/output operations. Candidate text and keys are
never inspected. These checks establish protocol/data-type compatibility, not
an arbitrary ranking of methods, source reliability, or causal measurement
validity in a real laboratory. All domains and evidence requirements must be
explicit; unsupported operations fail rather than being called false.
"""
from dataclasses import dataclass
import re
from model_types import select_unique


def _record(value, fields):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise ValueError('an exact typed record is required')
    return value


def _name(value):
    if not isinstance(value, str) or not re.fullmatch('[A-Za-z][A-Za-z0-9_]{0,39}', value):
        raise ValueError('a bounded identifier is required')
    return value


def _names(values):
    if not isinstance(values, list) or not values or len(values) > 12:
        raise ValueError('a nonempty bounded finite category domain is required')
    result = tuple(_name(value) for value in values)
    if len(set(result)) != len(result):
        raise ValueError('category names must be distinct')
    return result


def _values(values, domain, source):
    if not isinstance(values, list) or len(values) > 256:
        raise ValueError('a bounded list of actual categorical records is required')
    if any(not isinstance(value, str) or value not in domain for value in values):
        raise ValueError('every record must have a known category; no silent dropping')
    return tuple((source + ':' + str(i), value) for i, value in enumerate(values))


def _heights(values, domain, source):
    if not isinstance(values, dict) or set(values) != set(domain):
        raise ValueError('a chart must supply one height per category')
    if any(type(value) is not int or value < 0 for value in values.values()):
        raise ValueError('nonnegative integer chart heights required')
    return tuple((category, values[category]) for category in domain)


@dataclass(frozen=True)
class Artifact:
    form: str
    population: str
    field: str
    domain: tuple
    source: str
    basis: str
    condition: str = ''
    period: str = ''
    coefficients: tuple = ()
    records: tuple = ()
    trace: tuple = ()
    result: tuple = ()


class Protocol:
    """A small total type/provenance checker, not a free-form program runner."""
    def __init__(self, resources):
        if not isinstance(resources, dict) or len(resources) > 12:
            raise ValueError('a bounded resource environment is required')
        self.resources = {}
        for name, resource in resources.items():
            _name(name)
            if not isinstance(resource, dict):
                raise ValueError('a resource description is required')
            kind = resource.get('kind')
            if kind in ('cohort', 'respondents'):
                _record(resource, ('kind', 'population', 'field', 'domain', 'values', 'condition', 'period'))
                domain = _names(resource['domain'])
                if kind == 'cohort' and len(domain) != 2:
                    raise ValueError('binary measured state required for this protocol')
                records = _values(resource['values'], domain, name)
                if not records:
                    raise ValueError('a nonempty cohort/respondent frame is required')
                item = Artifact(kind, _name(resource['population']), _name(resource['field']), domain, name, 'unobserved',
                    _name(resource['condition']), _name(resource['period']), records=records, trace=(('resource', name),))
                self.resources[name] = (item,)
            elif kind in ('rows', 'chart'):
                _record(resource, ('kind', 'population', 'field', 'domain', 'basis', 'condition', 'period', 'values'))
                if resource['basis'] not in ('observed', 'reported'):
                    raise ValueError('explicit observed/reported provenance required')
                domain = _names(resource['domain'])
                records = (_heights(resource['values'], domain, name) if kind == 'chart'
                           else _values(resource['values'], domain, name))
                self.resources[name] = (Artifact(kind, _name(resource['population']), _name(resource['field']),
                    domain, name, resource['basis'], _name(resource['condition']), _name(resource['period']),
                    records=records, trace=(('resource', name),)),)
            elif kind == 'archive':
                _record(resource, ('kind', 'entries'))
                if not isinstance(resource['entries'], list) or len(resource['entries']) > 12:
                    raise ValueError('a bounded archive with explicit entries is required')
                entries = []
                for i, entry in enumerate(resource['entries']):
                    _record(entry, ('population', 'field', 'domain', 'basis', 'condition', 'period', 'values'))
                    if entry['basis'] not in ('observed', 'reported'):
                        raise ValueError('archive provenance is missing')
                    domain = _names(entry['domain'])
                    records = _values(entry['values'], domain, name + ':' + str(i))
                    entries.append(Artifact('rows', _name(entry['population']), _name(entry['field']),
                        domain, name + ':' + str(i), entry['basis'],
                        _name(entry['condition']), _name(entry['period']), records=records, trace=(('archive_entry', name, i),)))
                self.resources[name] = tuple(entries)
            else:
                raise ValueError('unknown resource kind')
        self.budget = 0

    def _one(self, node):
        result = self.infer(node)
        if len(result) != 1:
            raise ValueError('this operation needs exactly one input artifact')
        return result[0]

    def infer(self, node):
        self.budget += 1
        if self.budget > 60 or not isinstance(node, dict):
            raise ValueError('a bounded operation tree is required')
        op = node.get('op')
        if op == 'read':
            _record(node, ('op', 'resource'))
            name = _name(node['resource'])
            if name not in self.resources:
                raise ValueError('undeclared data source')
            return self.resources[name]
        if op == 'design_questionnaire':
            _record(node, ('op', 'population', 'field', 'domain'))
            return (Artifact('instrument', _name(node['population']), _name(node['field']),
                _names(node['domain']), '', 'unobserved'),)
        if op == 'administer':
            _record(node, ('op', 'instrument', 'respondents', 'condition', 'period'))
            instrument, respondents = self._one(node['instrument']), self._one(node['respondents'])
            if instrument.form != 'instrument' or respondents.form != 'respondents':
                raise ValueError('questionnaire and respondent frame are required')
            if (instrument.population, instrument.field, frozenset(instrument.domain)) != (respondents.population, respondents.field, frozenset(respondents.domain)):
                raise ValueError('questionnaire does not match its respondent frame')
            # A response is not promoted to an observed physical event, even
            # if it uses the same field/domain names as a measurement.
            condition, period = _name(node['condition']), _name(node['period'])
            if (condition, period) != (respondents.condition, respondents.period):
                raise ValueError('the response context was not supplied')
            return (Artifact('rows', respondents.population, instrument.field, instrument.domain,
                respondents.source, 'reported', condition, period, records=respondents.records,
                trace=respondents.trace + (('administer', instrument.field),)),)
        if op == 'expose':
            _record(node, ('op', 'cohort', 'condition', 'period'))
            cohort = self._one(node['cohort'])
            if cohort.form != 'cohort':
                raise ValueError('an unobserved cohort is needed before controlled exposure')
            condition, period = _name(node['condition']), _name(node['period'])
            if (condition, period) != (cohort.condition, cohort.period):
                raise ValueError('cohort outcomes for these conditions were not supplied')
            return (Artifact('exposed', cohort.population, cohort.field, cohort.domain, cohort.source,
                'unobserved', condition, period, records=cohort.records,
                trace=cohort.trace + (('expose', condition, period),)),)
        if op == 'observe':
            _record(node, ('op', 'input', 'field'))
            cohort = self._one(node['input'])
            if cohort.form != 'exposed' or _name(node['field']) != cohort.field:
                raise ValueError('observation needs the declared state after exposure')
            # The state of every supplied unit is read once. No interview
            # operator can produce this exposure->observation lineage.
            observed = tuple((unit, value) for unit, value in cohort.records)
            return (Artifact('rows', cohort.population, cohort.field, cohort.domain, cohort.source,
                'observed', cohort.condition, cohort.period, records=observed,
                trace=cohort.trace + (('observe', cohort.field),)),)
        if op == 'group_count':
            _record(node, ('op', 'input', 'groups'))
            rows = self._one(node['input'])
            if rows.form != 'rows':
                raise ValueError('group counting needs original rows, not an instrument/chart/claim')
            groups = node['groups']
            if not isinstance(groups, list) or not groups or len(groups) > 12:
                raise ValueError('a bounded grouping partition is required')
            categories = [_names(group) for group in groups]
            flattened = [category for group in categories for category in group]
            if set(flattened) != set(rows.domain) or len(flattened) != len(rows.domain):
                raise ValueError('groups must be a disjoint exhaustive partition')
            matrix = tuple(tuple(int(category in group) for category in rows.domain) for group in categories)
            # For EVERY one-hot category vector, summing the group counts
            # returns1. Linearity proves conservation for any number of rows;
            # this is a finite categorical basis proof, not sample evidence.
            if any(sum(column) != 1 for column in zip(*matrix)):
                raise ValueError('the aggregation does not conserve one count per record')
            # Execute the actual tally as well as the basis proof. Every
            # supplied unit is counted in exactly one group, including zeros.
            counts = tuple(sum(value in group for _, value in rows.records) for group in categories)
            if sum(counts) != len(rows.records):
                raise ValueError('executed tally lost or duplicated records')
            table = tuple((tuple(group), count) for group, count in zip(categories, counts))
            return (Artifact('counts', rows.population, rows.field, rows.domain, rows.source,
                rows.basis, rows.condition, rows.period, matrix, rows.records,
                rows.trace + (('group_count', tuple(categories)),), table),)
        if op == 'tabulate':
            _record(node, ('op', 'input'))
            data = self._one(node['input'])
            if data.form not in ('rows', 'counts'):
                raise ValueError('a table needs rows or computed category counts')
            return (Artifact('frequency_table' if data.form == 'counts' else 'row_table',
                data.population, data.field, data.domain, data.source, data.basis,
                data.condition, data.period, data.coefficients, data.records,
                data.trace + (('tabulate',),), data.result if data.form == 'counts' else data.records),)
        if op == 'argmin':
            _record(node, ('op', 'input'))
            chart = self._one(node['input'])
            if chart.form != 'chart':
                raise ValueError('a numerical chart is required to form this comparison claim')
            minimum = min(value for _, value in chart.records)
            winners = tuple(category for category, value in chart.records if value == minimum)
            return (Artifact('claim', chart.population, chart.field, chart.domain, chart.source,
                chart.basis, chart.condition, chart.period, records=chart.records,
                trace=chart.trace + (('argmin',),), result=winners),)
        raise ValueError('unknown operation; no conclusion can be established')


def empirical_collection(spec):
    _record(spec, ('kind', 'target', 'resources', 'options'))
    target = _record(spec['target'], ('population', 'field', 'domain', 'condition', 'period', 'basis'))
    if target['basis'] != 'observed':
        raise ValueError('this model requires an explicitly empirical, not preference, target')
    requested = (_name(target['population']), _name(target['field']), frozenset(_names(target['domain'])),
                 _name(target['condition']), _name(target['period']))
    if len(requested[2]) != 2:
        raise ValueError('a binary measurement target is required')
    # Construct a fresh checker for each candidate: neither prior candidate
    # order nor a shared evaluation budget changes protocol validity.
    def check(option):
        artifacts = Protocol(spec['resources']).infer(option['plan'])
        return any(item.form in ('rows', 'row_table') and item.records and item.basis == 'observed' and
            (item.population, item.field, frozenset(item.domain), item.condition, item.period) == requested
            for item in artifacts)
    return select_unique(spec['options'], check)


def categorical_organization(spec):
    _record(spec, ('kind', 'source', 'field', 'resources', 'options'))
    source, field = _name(spec['source']), _name(spec['field'])
    checker = Protocol(spec['resources'])
    if source not in checker.resources or len(checker.resources[source]) != 1:
        raise ValueError('one declared original dataset is required')
    original = checker.resources[source][0]
    if original.form != 'rows' or original.field != field:
        raise ValueError('the target must be a field of original rows')
    def check(option):
        outputs = Protocol(spec['resources']).infer(option['plan'])
        return any(item.form == 'frequency_table' and item.source == source and item.field == field
            and bool(item.coefficients) and sum(count for _, count in item.result) == len(original.records)
            and item.records == original.records for item in outputs)
    return select_unique(spec['options'], check)


HANDLERS = {'app41_empirical_collection': empirical_collection,
            'app41_categorical_organization': categorical_organization}
