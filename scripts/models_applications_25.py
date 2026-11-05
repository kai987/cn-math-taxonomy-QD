"""Executable survey protocols from explicit initial information states.

No stage-name ordering table is an input or verdict. Operations create actual
records, tables, faithful encodings, statistics and a report referencing the
computed analysis. Missing information blocks an action; unknown or malformed
programs raise, including unknown steps after an already blocked step.
"""
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
import re
import sympy as S
from model_types import select_unique
from models_applications_36 import _number, _record


class MissingInformation(Exception):
    """A known operation has not obtained the information it actually uses."""


def _q(value):
    try:return _number(value)
    except (ValueError,TypeError,ArithmeticError) as error:
        raise ValueError('bounded exact numeric field required') from error


def _name(value):
    if not isinstance(value,str) or not re.fullmatch('[A-Za-z][A-Za-z0-9_]{0,31}',value):
        raise ValueError('bounded data identifier required')
    return value


@dataclass(frozen=True)
class Question:
    population:str
    variable:str
    unit:str
    window:str
    lower:Fraction
    upper:Fraction


def question(value):
    _record(value,('population','variable','unit','window','value_domain'))
    domain=value['value_domain']
    if not isinstance(domain,list) or len(domain)!=2:raise ValueError('an explicit numeric interval required')
    lower,upper=map(_q,domain)
    if lower>upper:raise ValueError('measurement domain is empty')
    return Question(*(_name(value[field]) for field in ('population','variable','unit','window')),lower,upper)


@dataclass(frozen=True)
class Dataset:
    schema:Question
    rows:tuple


def dataset(rows,schema):
    if not isinstance(rows,list) or len(rows)>128:raise ValueError('bounded actual record list required')
    parsed=[]
    for row in rows:
        _record(row,('id','value'));identifier=_name(row['id']);value=_q(row['value'])
        if not schema.lower<=value<=schema.upper:raise ValueError('record lies outside the declared original domain')
        parsed.append((identifier,value))
    if len({key for key,_ in parsed})!=len(parsed):raise ValueError('record identities must be unique')
    return Dataset(schema,tuple(parsed))


@dataclass(frozen=True)
class Table:
    source:Dataset
    frequencies:tuple


@dataclass(frozen=True)
class Plot:
    source:Dataset
    layout:str
    points:tuple
    scale:Fraction
    offset:Fraction


@dataclass(frozen=True)
class Analysis:
    source:Dataset
    size:int
    mean:Fraction
    minimum:Fraction
    maximum:Fraction
    minimum_ids:tuple


@dataclass(frozen=True)
class Report:
    question:Question
    basis:Analysis
    proposed_action:str
    targets:tuple


class Survey:
    def __init__(self,study,world,initial):
        self.study=question(study)
        _record(world,('schema','potential_records'))
        if question(world['schema'])!=self.study:raise ValueError('potential responses do not match the study metadata')
        # These are protocol execution parameters, not already collected data
        # and not claims about the real classroom in the natural-language task.
        self.potential=dataset(world['potential_records'],self.study)
        _record(initial,('question','records'))
        self.question=None if initial['question'] is None else question(initial['question'])
        if self.question is not None and self.question!=self.study:raise ValueError('initial question belongs to a different study')
        self.raw=None if initial['records'] is None else dataset(initial['records'],self.study)
        self.organized=None;self.plot=None;self.analysis=None;self.report=None
        self.trace=[]

    def validate_action(self,node):
        if not isinstance(node,dict):raise ValueError('a typed operation required')
        op=node.get('op')
        if op=='formulate':
            _record(node,('op','question'))
            if question(node['question'])!=self.study:raise ValueError('operation formulates a different study')
        elif op in ('collect','organize'):
            _record(node,('op',))
        elif op=='encode_plot':
            _record(node,('op','input','scale','offset'))
            if node['input'] not in ('raw','organized'):raise ValueError('unknown chart source')
            if _q(node['scale'])<=0:raise ValueError('a positive, invertible chart scale required')
            _q(node['offset'])
        elif op=='analyze':
            _record(node,('op','input'))
            if node['input'] not in ('raw','organized','plot'):raise ValueError('unknown analysis source')
        elif op=='report':
            _record(node,('op','action'));_name(node['action'])
        else:raise ValueError('unknown operation, not a known unavailable step')

    def _source(self,name):
        result=getattr(self,name)
        if result is None:raise MissingInformation('missing '+name)
        return result

    def _values(self,name):
        artifact=self._source(name)
        if isinstance(artifact,Dataset):
            source=artifact;values=tuple(value for _,value in source.rows)
        elif isinstance(artifact,Table):
            source=artifact.source
            values=tuple(value for value,count in artifact.frequencies for _ in range(count))
        elif isinstance(artifact,Plot):
            source=artifact.source;a,b=artifact.scale,artifact.offset
            if artifact.layout=='raw':
                if len(artifact.points)!=len(source.rows):raise ValueError('plot lost records')
                values=tuple((encoded-b)/a for _,encoded in artifact.points)
            elif artifact.layout=='organized':
                recovered=[]
                for value,encoded in artifact.points:
                    count=(encoded-b)/a
                    if count.denominator!=1 or count<0:raise ValueError('decoded frequency is not a nonnegative integer')
                    recovered.extend([value]*int(count))
                values=tuple(recovered)
            else:raise ValueError('unrecognized plot layout')
        else:raise ValueError('artifact is not numeric observations')
        if Counter(values)!=Counter(value for _,value in source.rows):
            raise ValueError('data transformation changed multiplicities or values')
        return source,values

    def step(self,node):
        self.validate_action(node);op=node['op']
        if op=='formulate':
            # Formulating an already identical question is idempotent. We do
            # not forbid legitimate review merely to force a next-stage label.
            self.question=question(node['question']);result=self.question
        elif op=='collect':
            if self.question is None:raise MissingInformation('record fields/population not yet formulated')
            self.raw=Dataset(self.question,tuple(self.potential.rows))
            # A new collection invalidates artifacts made from older data.
            self.organized=self.plot=self.analysis=self.report=None
            result=self.raw
        elif op=='organize':
            source=self._source('raw');counts=Counter()
            for index,(_,value) in enumerate(source.rows,1):
                counts[value]+=1
                # Loop invariant: every new row contributes exactly one vote.
                # Induction proves total conservation for ANY finite dataset.
                if sum(counts.values())!=index:raise ValueError('classification duplicated or dropped a record')
            self.organized=Table(source,tuple(sorted(counts.items())))
            self._values('organized');result=self.organized
        elif op=='encode_plot':
            source,values=self._values(node['input'])
            if not values:raise MissingInformation('no numeric data to display')
            a,b=_q(node['scale']),_q(node['offset']);x=S.Dummy('x',real=True)
            sa,sb=S.Rational(a),S.Rational(b)
            if S.cancel((sa*x+sb-sb)/sa-x)!=0:raise ValueError('chart decoder not universally inverse')
            if node['input']=='raw':points=tuple((index,a*value+b) for index,(_,value) in enumerate(source.rows))
            else:points=tuple((value,a*count+b) for value,count in self.organized.frequencies)
            self.plot=Plot(source,node['input'],points,a,b)
            self._values('plot');result=self.plot
        elif op=='analyze':
            source,values=self._values(node['input'])
            if not values:raise MissingInformation('a mean and extrema need at least one valid record')
            mean=sum(values,Fraction(0))/len(values);minimum=min(values);maximum=max(values)
            # IDs are read from the retained original-record provenance, not
            # inferred from an aggregate graphic that omits identities.
            ids=tuple(key for key,value in source.rows if value==minimum)
            if not ids or any((key in ids)!=(value==minimum) for key,value in source.rows):
                raise ValueError('the complete minimum set is not established')
            self.analysis=Analysis(source,len(values),mean,minimum,maximum,ids);result=self.analysis
        else:
            if self.question is None:raise MissingInformation('report must state its research question')
            analysis=self._source('analysis')
            if analysis.source is not self.raw or analysis.source.schema!=self.question:
                raise MissingInformation('analysis is not based on the current study records')
            self.report=Report(self.question,analysis,node['action'],analysis.minimum_ids)
            # It is a proposal explicitly linked to computed facts. No claim
            # of optimality, medical benefit or compulsory action is made.
            result=self.report
        self.trace.append((op,result));return result

    def execute(self,program):
        if not isinstance(program,list) or not 1<=len(program)<=24:raise ValueError('bounded full operation sequence required')
        # Validate EVERY node before availability checking. A missing input in
        # step1 must never hide unknown assertions/fields in a later step.
        for node in program:self.validate_action(node)
        try:
            for node in program:self.step(node)
        except MissingInformation:
            return False
        return self.report is not None and self.report.basis.source is self.raw


def _context(spec,kind):
    _record(spec,('kind','study','world','initial','options'))
    if spec['kind']!=kind:raise ValueError('unknown survey proof task')


def executable_report(spec):
    _context(spec,'app25_executable_survey_report')
    def check(option):
        _record(option,('key','text','program'))
        return Survey(spec['study'],spec['world'],spec['initial']).execute(option['program'])
    return select_unique(spec['options'],check)


def executable_first_action(spec):
    _context(spec,'app25_executable_first_action')
    def check(option):
        _record(option,('key','text','action'))
        protocol=Survey(spec['study'],spec['world'],spec['initial'])
        protocol.validate_action(option['action'])
        try:protocol.step(option['action'])
        except MissingInformation:return False
        return True
    return select_unique(spec['options'],check)


HANDLERS={'app25_executable_survey_report':executable_report,
          'app25_executable_first_action':executable_first_action}
