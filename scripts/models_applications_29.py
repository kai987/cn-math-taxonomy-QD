"""Rotation construction and canonical descriptive-field verification.

The target is the declared textbook representation, not every sufficient set
of geometric information and not a count of independent real parameters.
Field expressions are typed mathematical objects; option wording is unused.
The geometric certificate covers every angle in the forward construction.
Inverse identification is asserted only where it is mathematically unique.
"""
from dataclasses import dataclass
from functools import lru_cache
import re
import sympy as S
from model_types import select_unique
from models_applications_36 import _number, _record


def _name(value):
    if not isinstance(value,str) or not re.fullmatch('[A-Za-z][A-Za-z0-9_]{0,15}',value):
        raise ValueError('bounded parameter identifier required')
    return value


def _zero(value):
    return S.cancel(S.expand(value)) == 0


def _matrix_zero(value):
    return all(_zero(entry) for entry in value)


@lru_cache(maxsize=1)
def rotation_certificate():
    """General-angle forward proof plus exact inverse and endpoint charts."""
    a=S.Symbol('a',real=True);x,y,p,q=S.symbols('x y p q',real=True)
    vector=S.Matrix([x-p,y-q]);center=S.Matrix([p,q])
    for direction in (-1,1):
        r=S.Matrix([[S.cos(a),-direction*S.sin(a)],[direction*S.sin(a),S.cos(a)]])
        if any(S.trigsimp(entry)!=0 for entry in r.T*r-S.eye(2)) or S.trigsimp(r.det()-1)!=0:
            raise ValueError('the all-angle orientation-preserving isometry failed')
        output=center+r*vector
        if any(S.trigsimp(entry)!=0 for entry in output.subs({x:p,y:q})-center):
            raise ValueError('the given center is not fixed')
        if S.trigsimp(S.expand((output-center).dot(output-center)-vector.dot(vector)))!=0:
            raise ValueError('the all-query-point radius identity failed')
        signed=S.Matrix([[S.cos(direction*a),-S.sin(direction*a)],[S.sin(direction*a),S.cos(direction*a)]])
        if any(S.trigsimp(entry)!=0 for entry in r-signed):
            raise ValueError('separate orientation and magnitude do not reconstruct a signed turn')
    # This symbolic proof is for ALL reala, including0,pi,reflex angles and
    # arbitrary full turns. The charts below add inverse identification and
    # explicitly record where the descriptive fields are redundant.
    t=S.Symbol('t',positive=True);c=(1-t*t)/(1+t*t);u=2*t/(1+t*t)
    if not _zero(c*c+u*u-1) or S.factor(S.diff(c,t)).is_negative is not True:
        raise ValueError('half-angle magnitude parameter is not uniquely ordered')
    charts=[]
    for direction in (-1,1):
        for kind,cosine,sine in [('minor',c,direction*u),('reflex',c,-direction*u),
                                 ('identity',S.Integer(1),S.Integer(0)),
                                 ('half_turn',S.Integer(-1),S.Integer(0)),
                                 ('full_turn',S.Integer(1),S.Integer(0))]:
            r=S.Matrix([[cosine,-sine],[sine,cosine]])
            translation=(S.eye(2)-r)*center
            if not _matrix_zero(r.T*r-S.eye(2)) or not _zero(r.det()-1):
                raise ValueError('an angle chart is not a planar rotation')
            determinant=S.factor((S.eye(2)-r).det())
            if kind in ('identity','full_turn'):
                if determinant!=0 or not _matrix_zero(translation):
                    raise ValueError('identity center non-uniqueness was not established')
                unique_center=False
            else:
                if determinant.is_positive is not True:
                    raise ValueError('the nonidentity center inverse is unresolved')
                recovered=(S.eye(2)-r).inv()*translation
                if not _matrix_zero(recovered-center):raise ValueError('fixed-center inversion failed')
                unique_center=True
            if kind=='minor':
                if S.sign(sine)!=direction or not _zero(abs(sine)/(1+cosine)-t):
                    raise ValueError('minor-turn direction/magnitude inversion failed')
            if kind in ('identity','half_turn','full_turn'):
                other=S.Matrix([[cosine,sine],[-sine,cosine]])
                if not _matrix_zero(r-other):raise ValueError('endpoint direction redundancy unproved')
            charts.append((kind,direction,unique_center))
    # For a nonidentity chart I-R is invertible, so changing its center changes
    # its translation. On minor charts changing the sign changes a nonzero
    # sine, and changingt changesc strictly. These are real roles in the full
    # family, not a claim that each particular endpoint needs every field.
    if S.factor(2*u).is_positive is not True:raise ValueError('direction effect unproved')
    k=S.Symbol('k',integer=True)
    if S.trigsimp(S.cos(a+2*S.pi*k)-S.cos(a))!=0 or S.trigsimp(S.sin(a+2*S.pi*k)-S.sin(a))!=0:
        raise ValueError('full-turn periodicity unproved')
    return tuple(charts)


@dataclass(frozen=True)
class Field:
    sort: str
    value: object
    dependencies: frozenset
    primitive: object = None


def _parameter(node):
    _record(node,('op','name','sort'))
    if node['op']!='parameter' or node['sort'] not in ('point2','orientation','unsigned_turn','signed_turn'):
        raise ValueError('typed geometric parameter required')
    return _name(node['name']),node['sort']


class Description:
    def __init__(self,construction,encoding,unit):
        _record(construction,('op','center','signed_turn'))
        if construction['op']!='rotate_about_center' or unit not in ('degree','radian'):
            raise ValueError('a whole-plane rotation construction and angle unit required')
        center,sort=_parameter(construction['center'])
        if sort!='point2':raise ValueError('rotation center must be a point')
        self.parameters={center:'point2'}
        self.center_name=center;self.unit=unit
        if encoding=='separate_orientation_and_unsigned_turn':
            turn=_record(construction['signed_turn'],('op','factors'))
            if turn['op']!='multiply' or not isinstance(turn['factors'],list) or len(turn['factors'])!=2:
                raise ValueError('signed turn must multiply separate orientation and unsigned magnitude')
            factors=[_parameter(node) for node in turn['factors']]
            if {sort for _,sort in factors}!={'orientation','unsigned_turn'}:
                raise ValueError('separate binary orientation and unsigned angle are required')
            for name,sort in factors:
                if name in self.parameters:raise ValueError('rotation parameters must be distinct')
                self.parameters[name]=sort
        elif encoding=='signed_turn_includes_orientation':
            name,sort=_parameter(construction['signed_turn'])
            if sort!='signed_turn' or name in self.parameters:raise ValueError('one signed turn parameter required')
            self.parameters[name]=sort
        else:raise ValueError('angle convention is unspecified')
        self.encoding=encoding
        self.center=S.Matrix([S.Dummy('center_x',real=True),S.Dummy('center_y',real=True)])
        self.query=S.Matrix([S.Dummy('query_x',real=True),S.Dummy('query_y',real=True)])
        self.values={center:self.center}
        for name,sort in self.parameters.items():
            if sort!='point2':self.values[name]=S.Dummy(name,real=True,**({'nonnegative':True} if sort=='unsigned_turn' else {}))
        rotation_certificate()

    def field(self,node,budget=None):
        if budget is None:budget=[0]
        budget[0]+=1
        if budget[0]>50 or not isinstance(node,dict):raise ValueError('bounded field expression required')
        op=node.get('op')
        if op=='parameter':
            name,sort=_parameter(node)
            if self.parameters.get(name)!=sort:raise ValueError('undeclared parameter or inconsistent sort')
            return Field(sort,self.values[name],frozenset({name}),name)
        if op=='query_point':
            _record(node,('op',));return Field('point2',self.query,frozenset({'query'}))
        if op=='external_time':
            _record(node,('op',));return Field('scalar',S.Symbol('external_time',real=True),frozenset({'external_time'}))
        if op=='external_axis':
            _record(node,('op',));return Field('line',S.symbols('axis_m axis_b',real=True),frozenset({'axis'}))
        if op=='squared_distance':
            _record(node,('op','left','right'))
            left,right=self.field(node['left'],budget),self.field(node['right'],budget)
            if left.sort!='point2' or right.sort!='point2':raise ValueError('distance needs two points')
            difference=left.value-right.value
            return Field('scalar',S.expand(difference.dot(difference)),left.dependencies|right.dependencies)
        if op=='apply_rotation':
            _record(node,('op','point'));point=self.field(node['point'],budget)
            if point.sort!='point2':raise ValueError('the rotated object must be a point')
            if self.encoding=='separate_orientation_and_unsigned_turn':
                direction=next(name for name,sort in self.parameters.items() if sort=='orientation')
                magnitude=next(name for name,sort in self.parameters.items() if sort=='unsigned_turn')
                turn=self.values[direction]*self.values[magnitude]
            else:turn=self.values[next(name for name,sort in self.parameters.items() if sort=='signed_turn')]
            if self.unit=='degree':turn*=S.pi/180
            r=S.Matrix([[S.cos(turn),-S.sin(turn)],[S.sin(turn),S.cos(turn)]])
            return Field('point2',self.center+r*(point.value-self.center),point.dependencies|frozenset(self.parameters))
        if op=='point_pair':
            _record(node,('op','first','second'))
            first,second=self.field(node['first'],budget),self.field(node['second'],budget)
            if first.sort!='point2' or second.sort!='point2':raise ValueError('correspondence needs two points')
            return Field('point_pair',(first.value,second.value),first.dependencies|second.dependencies)
        raise ValueError('unknown field expression')


def rotation_parameters(spec):
    _record(spec,('kind','angle_encoding','angle_unit','construction','options'))
    if spec['kind']!='app29_rotation_parameters':raise ValueError('rotation-description contract required')
    description=Description(spec['construction'],spec['angle_encoding'],spec['angle_unit'])
    def check(option):
        _record(option,('key','text','fields'))
        if not isinstance(option['fields'],list) or not 1<=len(option['fields'])<=8:
            raise ValueError('bounded descriptor field list required')
        # Every field is checked, including composite or extraneous fields of
        # an already nonmatching candidate. Only a primitive construction
        # operand is a field of THIS representation. Composite observations
        # may be sufficient by other inverse methods; that is a different task.
        fields=[description.field(node) for node in option['fields']]
        primitives=[field.primitive for field in fields]
        return (len(primitives)==len(description.parameters) and None not in primitives
            and len(set(primitives))==len(primitives) and set(primitives)==set(description.parameters))
    return select_unique(spec['options'],check)


def rotate_point(center,direction,magnitude,point,unit='degree'):
    """Exact executable instances of the forward description, including endpoints."""
    if (not isinstance(center,list) or len(center)!=2 or not isinstance(point,list) or len(point)!=2
            or type(direction)is not int or direction not in (-1,1) or unit not in ('degree','radian')):
        raise ValueError('two points and a binary orientation with an angle unit required')
    try:
        c=S.Matrix([S.Rational(_number(v)) for v in center]);p=S.Matrix([S.Rational(_number(v)) for v in point])
        a=_number(magnitude)
    except (ValueError,TypeError,ArithmeticError) as error:raise ValueError('exact bounded numeric geometry required') from error
    if a<0:raise ValueError('the separate magnitude must be unsigned')
    turn=S.Rational(a)*direction*(S.pi/180 if unit=='degree' else 1)
    r=S.Matrix([[S.cos(turn),-S.sin(turn)],[S.sin(turn),S.cos(turn)]])
    return (c+r*(p-c)).applyfunc(S.simplify)


HANDLERS={'app29_rotation_parameters':rotation_parameters}
