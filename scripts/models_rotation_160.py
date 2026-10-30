"""Check right-angle constructions over every nondegenerate triangle.

After a proper rigid motion C=(0,0), A=(r,0), B=(u,v), with r>0,
v!=0. This normalization preserves the stated counterclockwise direction.
"""
import sympy as S
from model_types import select_unique


def right_angle_construction(spec):
    if spec.get('angle_degrees') != 90 or spec.get('direction') != 'counterclockwise':
        raise ValueError('only the specified counterclockwise right-angle construction is supported')
    r = S.Symbol('r', positive=True)
    u = S.Symbol('u', real=True)
    v = S.Symbol('v', real=True, nonzero=True)
    source = S.Matrix([r, 0])
    target = S.Matrix([[0, -1], [1, 0]]) * source
    radii_squared = {'CA': r*r, 'AB': (u-r)**2+v*v}

    def check(option):
        if option.get('perpendicular_through') not in ('source', 'center'):
            raise ValueError('unknown perpendicular construction')
        radius = option.get('radius')
        orientation = option.get('orientation')
        if radius not in (None, 'CA', 'AB') or orientation not in ('either', 'counterclockwise'):
            raise ValueError('unmodelled length or orientation constraint')
        # A line through A perpendicular to CA has x=r. It excludes the
        # desired point x=0 for every r>0, regardless of the free y-coordinate.
        if option['perpendicular_through'] == 'source':
            if target[0] != 0 or r.is_positive is not True:
                raise ValueError('failure of the perpendicular-through-source proof')
            return False
        if radius is None:
            # With no length constraint, both (0,r) and (0,2r) are legal even
            # if the orientation is specified. The construction is not unique.
            return False
        squared = radii_squared[radius]
        if squared.is_positive is not True:
            raise ValueError('nonzero construction radius was not established')
        positive_root = S.sqrt(squared)
        roots = S.FiniteSet(-positive_root, positive_root)
        if (positive_root.is_positive is not True or len(roots) != 2
                or any(S.simplify(root*root-squared) != 0 for root in roots)):
            raise ValueError('the two perpendicular length solutions are unresolved')
        if orientation == 'either':
            # A negative y-root is a clockwise image and cannot equal r>0.
            if not any(root.is_negative is True for root in roots):
                raise ValueError('wrong-direction solution not proved')
            return False
        positive = [root for root in roots if root.is_positive is True]
        if len(positive) != 1:
            raise ValueError('the oriented construction is unresolved')
        difference = S.simplify(positive[0]-target[1])
        if difference == 0:
            return True
        # Equal radii can occur in particular triangles. A nonidentity must
        # be refuted by a legal triangle, rather than assumed from its syntax.
        witness = {r: S.Integer(1), u: S.Integer(1), v: S.Integer(2)}
        if S.simplify(difference.subs(witness)).is_zero is not False:
            raise ValueError('no legal counterexample for this construction')
        return False

    return select_unique(spec['options'], check)


HANDLERS = {'rotation160_right_angle_construction': right_angle_construction}
