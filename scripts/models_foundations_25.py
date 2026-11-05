"""Execute four quadratic methods before checking a stated first-step goal.

All methods preserve the source equation over the reals.  The criterion is
an explicitly produced variable-factor zero product, not a speed score or a
mapping from a method's name to an answer key.
"""
from dataclasses import dataclass
from fractions import Fraction
from math import gcd, lcm
import re
import sympy as S
from model_types import select_unique


def _record(value, fields):
    if not isinstance(value,dict) or set(value)!=set(fields):
        raise ValueError('complete typed record without extra fields required')
    return value


def _q(value):
    if type(value) is int:
        if value.bit_length()>256:raise ValueError('integer exceeds arithmetic budget')
        text=str(value)
    elif isinstance(value,str) and len(value)<=64:
        text=value.translate(str.maketrans('０１２３４５６７８９＋－．／−','0123456789+-./-'))
    else:raise ValueError('bounded exact rational required')
    number=r'[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)'
    if re.fullmatch(number+'(?:/'+number+')?',text) is None:
        raise ValueError('unsupported exact numeric spelling')
    try:
        parts=text.split('/')
        value=Fraction(parts[0])/(Fraction(parts[1]) if len(parts)==2 else 1)
    except ArithmeticError as error:raise ValueError('undefined rational') from error
    if max(abs(value.numerator).bit_length(),value.denominator.bit_length())>256:
        raise ValueError('number exceeds arithmetic budget')
    return value


def _generic_identities():
    a=S.Symbol('a',real=True,nonzero=True);b,x,u=S.symbols('b x u',real=True)
    p=a*x*x-b*x;h=b/(2*a)
    identities=[p-x*(a*x-b),p/a-((x-h)**2-h*h),
                p.subs(x,u+h)/a-(u*u-h*h)]
    for root in ((b+S.Abs(b))/(2*a),(b-S.Abs(b))/(2*a)):
        identities.append(S.simplify(p.subs(x,root)))
    if any(S.simplify(S.cancel(identity))!=0 for identity in identities):
        raise ValueError('the all-parameter quadratic method identities failed')


def _multiply(first,second):
    return (first[0]*second[0],first[0]*second[1]+first[1]*second[0],first[1]*second[1])


@dataclass(frozen=True)
class MethodResult:
    roots: tuple
    identity_verified: bool
    first_product: object = None
    first_right: object = None
    preparation_required: bool = False
    square_shift: object = None
    discriminant: object = None


class QuadraticFirstStep:
    def __init__(self,equation,domain,target):
        _record(equation,('variable','quadratic_coefficient','linear_rhs_coefficient'))
        if domain!='all_real' or target!='first_variable_factor_zero_product':
            raise ValueError('real domain and explicit variable-factor first-step goal required')
        variable=equation['variable']
        if not isinstance(variable,str) or re.fullmatch('[a-z]',variable) is None:
            raise ValueError('one lower-case variable required')
        self.variable=variable
        self.a=_q(equation['quadratic_coefficient']);self.b=_q(equation['linear_rhs_coefficient'])
        if self.a==0:raise ValueError('a genuine quadratic source equation is required')
        _generic_identities()
        self.polynomial=(Fraction(0),-self.b,self.a)
        # Zero-product equivalence is complete over R: x=0 or a*x-b=0.
        # a!=0 makes the second factor's root unique; b=0 coalesces them.
        self.all_roots=tuple(sorted({Fraction(0),self.b/self.a}))

    def _check_roots(self,roots):
        roots=tuple(sorted(set(roots)))
        if (roots!=self.all_roots or any(self.a*x*x-self.b*x!=0 for x in roots)):
            raise ValueError('a purported equivalent method lost or added a source root')
        return roots

    def execute(self,program):
        if not isinstance(program,dict):raise ValueError('typed algebraic program required')
        op=program.get('op')
        if op=='extract_variable_factor':
            _record(program,('op',))
            content=Fraction(gcd(abs(self.a.numerator),abs(self.b.numerator)),
                             lcm(self.a.denominator,self.b.denominator))
            if content<=0:raise ValueError('nonzero quadratic content required')
            factors=((Fraction(0),content),(-self.b/content,self.a/content))
            if _multiply(*factors)!=self.polynomial:raise ValueError('computed factor extraction is not an identity')
            roots=self._check_roots(-factor[0]/factor[1] for factor in factors)
            return MethodResult(roots,True,first_product=factors,first_right=(Fraction(0),))
        if op=='display_linear_product':
            _record(program,('op','factors'))
            if not isinstance(program['factors'],list) or len(program['factors'])!=2:
                raise ValueError('two affine factors required')
            factors=[]
            for pair in program['factors']:
                if not isinstance(pair,list) or len(pair)!=2:raise ValueError('constant and linear coefficient required')
                pair=tuple(_q(v) for v in pair)
                if pair[1]==0:raise ValueError('both factors must be genuinely linear')
                factors.append(pair)
            factors=tuple(factors)
            identical=_multiply(*factors)==self.polynomial
            roots=tuple(sorted({-factor[0]/factor[1] for factor in factors}))
            if identical:roots=self._check_roots(roots)
            return MethodResult(roots,identical,first_product=factors,first_right=(Fraction(0),))
        if op=='prepare_then_open_square_root':
            _record(program,('op',))
            # x²=(b/a)x is not x²=constant unless b=0. The reversible
            # translation u=x-h gives u²=h² before opening the square.
            h=self.b/(2*self.a)
            shifted=(self.a*h*h-self.b*h,2*self.a*h-self.b,self.a)
            if shifted!=(-self.a*h*h,Fraction(0),self.a):
                raise ValueError('affine substitution did not preserve the equation')
            roots=self._check_roots((h-abs(h),h+abs(h)))
            return MethodResult(roots,True,first_right=(h*h,),preparation_required=self.b!=0,square_shift=h)
        if op=='complete_square':
            _record(program,('op',))
            h=self.b/(2*self.a)
            # Adding h² to both sides gives (x-h)²=h². Subtracting the
            # right side reconstructs the normalized original coefficients.
            expanded=(h*h,-2*h,Fraction(1))
            normalized=tuple(v/self.a for v in self.polynomial)
            if (expanded[0]-h*h,expanded[1],expanded[2])!=normalized:
                raise ValueError('completed square is not an equivalent equation')
            roots=self._check_roots((h-abs(h),h+abs(h)))
            return MethodResult(roots,True,first_right=(h*h,),square_shift=h)
        if op=='quadratic_formula':
            _record(program,('op',))
            discriminant=self.b*self.b
            root=abs(self.b)
            if discriminant<0 or root*root!=discriminant:
                raise ValueError('the exact real square root was not established')
            roots=self._check_roots(((self.b-root)/(2*self.a),(self.b+root)/(2*self.a)))
            return MethodResult(roots,True,discriminant=discriminant)
        raise ValueError('unknown method; no false verdict inferred')

    def meets_first_step(self,result):
        factors=result.first_product
        if not result.identity_verified or factors is None:return False
        # Check the ACTUAL produced product and zero RHS, not the op/name.
        # A nonzero scalar multiple of x is a legitimate variable factor.
        if (result.first_right!=(0,) or _multiply(*factors)!=self.polynomial
                or not any(constant==0 and slope!=0 for constant,slope in factors)):
            return False
        return result.roots==self.all_roots


def quadratic_first_step(spec):
    _record(spec,('kind','domain','equation','target','options'))
    if spec['kind']!='f25_quadratic_variable_factor_first_step':
        raise ValueError('typed quadratic first-step model required')
    if not isinstance(spec['options'],list) or not 1<=len(spec['options'])<=16:
        raise ValueError('bounded nonempty candidate list required')
    proof=QuadraticFirstStep(spec['equation'],spec['domain'],spec['target'])
    def check(option):
        _record(option,('key','text','program'))
        return proof.meets_first_step(proof.execute(option['program']))
    return select_unique(spec['options'],check)


HANDLERS={'f25_quadratic_variable_factor_first_step':quadratic_first_step}
