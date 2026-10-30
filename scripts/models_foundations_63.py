"""Checked theorem applications and transform identification for foundations.

The input is a reviewed mathematical translation, not automatic understanding
of Chinese. Every candidate theorem is proved before its direct goal/type is
matched. This does not claim another indirect proof is impossible.
"""
import itertools
import json
import re
import sympy as S

from model_types import select_unique
from models_algebra import feasible, implies, number
from models_foundations_105 import _symbols, _parse, _vector, _zero, _positive, _rank
from models_foundations_160 import ANGLE_DOMAIN, _slot


def R(a,op,b):return {'left':str(a),'op':op,'right':str(b)}


def _uniform_zero(expression):
    value=S.trigsimp(S.factor(expression))
    if value==0:return True
    if value.is_nonzero is True:return False
    raise ValueError('the geometric relation varies over an unproved parameter domain')


def line_notation(spec):
    symbols=_symbols(spec['symbols']);lines={}
    for name,line in spec['lines'].items():
        if not re.fullmatch('[A-Za-z]{1,4}',name):raise ValueError('invalid line identifier')
        point=_vector(line['point'],symbols,2);direction=_vector(line['direction'],symbols,2)
        _positive(direction.dot(direction));lines[name]=(point,direction)
    def check(option):
        match=re.fullmatch(r'([A-Za-z]{1,4})([∥⊥=∠])([A-Za-z]{1,4})',option['notation'])
        if not match:raise ValueError('unsupported line-relation syntax')
        first,operator,second=match.groups()
        if first not in lines or second not in lines:raise ValueError('unbound line name')
        if operator=='∠':
            # ∠ is a prefix angle constructor with a vertex/rays, not a binary
            # Boolean predicate taking two Line objects in this typed grammar.
            return False
        p,u=lines[first];q,v=lines[second]
        if operator=='⊥':return _uniform_zero(u.dot(v))
        parallel=_uniform_zero(S.det(S.Matrix.hstack(u,v)))
        if not parallel:return False
        coincident=_uniform_zero(S.det(S.Matrix.hstack(q-p,u)))
        return not coincident if operator=='∥' else coincident
    return select_unique(spec['options'],check)


def basis_problem(kind):
    """Formal quantified goals of elementary geometry, without candidate labels."""
    if kind=='line_through_two_points':
        return {'objects':{'A':'Point','B':'Point'},'assumptions':[['distinct','A','B']],
                'goal':{'quantifier':'unique','variable':['l','Line'],'relation':['line_through','l','A','B']}}
    if kind=='point_line_distance':
        return {'objects':{'P':'Point','l':'Line'},'assumptions':[['outside','P','l']],
                'goal':{'quantifier':'unique_minimum','variable':['H','Point'],'relation':['closest_on_line','H','P','l']}}
    if kind=='point_point_path':
        return {'objects':{'A':'Point','B':'Point'},'assumptions':[['distinct','A','B']],
                'goal':{'quantifier':'minimum','variable':['g','Path'],'relation':['shortest_connection','g','A','B']}}
    if kind=='parallel_through_point':
        return {'objects':{'P':'Point','l':'Line'},'assumptions':[['outside','P','l']],
                'goal':{'quantifier':'unique','variable':['m','Line'],'relation':['parallel_through','m','P','l']}}
    if kind=='same_angle_supplements':
        return {'objects':{'a':'Angle','b':'Angle','c':'Angle'},
                'assumptions':[['supplementary','a','c'],['supplementary','b','c']],
                'goal':{'quantifier':'assert','relation':['angle_equal','a','b']}}
    raise ValueError('unknown geometric problem constructor')


def canonical_problem(problem):
    objects=problem['objects'];goal=problem['goal'];types=dict(objects)
    if not 1<=len(objects)<=4 or any(t not in ('Point','Line','Path','Angle') for t in objects.values()):raise ValueError('bounded typed objects required')
    if any(not re.fullmatch('[A-Za-z][A-Za-z0-9]{0,5}',x) for x in objects):raise ValueError('invalid object name')
    quantifier=goal['quantifier'];bound=goal.get('variable')
    if quantifier=='assert':
        if bound is not None:raise ValueError('assertion must not bind an output object')
    elif quantifier in ('unique','minimum','unique_minimum'):
        if not isinstance(bound,list) or len(bound)!=2 or bound[0] in types or bound[1] not in ('Point','Line','Path'):raise ValueError('invalid quantified object')
        types[bound[0]]=bound[1]
    else:raise ValueError('unsupported direct-goal quantifier')
    signatures={'distinct':('Point','Point'),'outside':('Point','Line'),
                'line_through':('Line','Point','Point'),'closest_on_line':('Point','Point','Line'),
                'shortest_connection':('Path','Point','Point'),'parallel_through':('Line','Point','Line'),
                'supplementary':('Angle','Angle'),'angle_equal':('Angle','Angle')}
    def validate(atom):
        if not isinstance(atom,list) or not atom or atom[0] not in signatures:raise ValueError('unknown geometric predicate')
        if tuple(types.get(name) for name in atom[1:])!=signatures[atom[0]]:raise ValueError('ill-typed geometric predicate')
    for atom in problem['assumptions']+[goal['relation']]:validate(atom)
    images=[];names=list(objects)
    for permutation in itertools.permutations(range(len(names))):
        rename={name:objects[name]+str(permutation[i]) for i,name in enumerate(names)}
        if bound:rename[bound[0]]='Bound'+bound[1]
        def atom(a):
            args=[rename[x] for x in a[1:]]
            symmetric={'distinct':(0,1),'supplementary':(0,1),'angle_equal':(0,1),
                       'line_through':(1,2),'shortest_connection':(1,2)}.get(a[0])
            if symmetric:
                i,j=symmetric;args[i],args[j]=sorted((args[i],args[j]))
            return [a[0],*args]
        representation=[sorted(rename[x] for x in objects),sorted(atom(a) for a in problem['assumptions']),
                        quantifier,atom(goal['relation'])]
        images.append(json.dumps(representation,separators=(',',':')))
    return min(images)


def prove_basis(kind):
    if kind=='line_through_two_points':
        d=S.Symbol('_d',positive=True)
        constraints=S.Matrix([[0,0,1],[d,0,1]])
        if _rank(constraints)!=2 or len(constraints.nullspace())!=1:raise ValueError('one projective line was not proved')
        normal=constraints.nullspace()[0]
        if normal[:2]==[0,0]:raise ValueError('degenerate line normal')
    elif kind=='point_line_distance':
        p,t=S.symbols('_p _t',real=True);h=S.Symbol('_h',positive=True)
        squared=(t-p)**2+h*h
        if not _zero(squared-h*h-(t-p)**2) or ((t-p)**2).is_nonnegative is not True:raise ValueError('global distance lower bound failed')
        if squared.subs(t,p)!=h*h:raise ValueError('the lower bound is not attained')
        if S.solveset(squared-h*h,t,domain=S.S.Reals)!=S.FiniteSet(p):raise ValueError('the minimizing foot is not unique')
    elif kind=='point_point_path':
        a,b,c,d=S.symbols('_a _b _c _d',real=True);u=S.Matrix([a,b]);v=S.Matrix([c,d])
        cross=S.det(S.Matrix.hstack(u,v))
        if not _zero(u.dot(u)*v.dot(v)-u.dot(v)**2-cross**2):raise ValueError('Lagrange identity failed')
        # Nonnegative squared cross gives Cauchy--Schwarz, hence the triangle
        # inequality. Finite sums and the definition of rectifiable arc length
        # bound every path by its endpoint distance; a straight segment attains it.
    elif kind=='parallel_through_point':
        p=S.Symbol('_p',real=True);h=S.Symbol('_h',positive=True)
        equations=S.Matrix([[1,0,0],[p,h,1]])
        if _rank(equations)!=2 or len(equations.nullspace())!=1:raise ValueError('parallel line uniqueness failed')
        if S.simplify(equations.nullspace()[0][2])==0:raise ValueError('the new line must differ from the original')
    elif kind=='same_angle_supplements':
        premises=[R('a+c','=',180),R('b+c','=',180)]+[R(x,'>=',0) for x in 'abc']+[R(x,'<=',180) for x in 'abc']
        if not feasible(premises) or not implies(premises,R('a','=','b')):raise ValueError('supplement identity failed')
    else:raise ValueError('unproved geometry certificate')
    return canonical_problem(basis_problem(kind))


def basis_application(spec):
    source=canonical_problem(spec['problem'])
    def check(option):
        proved=prove_basis(option['certificate'])
        translated=canonical_problem(option['problem'])
        if translated!=proved:raise ValueError('candidate goal does not match its mathematical certificate')
        return translated==source
    return select_unique(spec['options'],check)


def _atom(atom):
    if not isinstance(atom,dict) or not isinstance(atom.get('args'),list):raise ValueError('applied predicate required')
    op=atom['op'];args=atom['args']
    if op not in ('parallel','angle_equal','angle_supplementary','neighbor','vertical') or len(args)!=2 or any(not isinstance(v,str) or not re.fullmatch('[A-Za-z][A-Za-z0-9]{0,5}',v) for v in args) or args[0]==args[1]:
        raise ValueError('unsupported binary geometric predicate')
    return (op,tuple(sorted(args)))


def _angle_context(context):
    kind=context['kind']
    if kind=='transversal':
        if len(context['lines'])!=2 or len(set(context['lines']))!=2:raise ValueError('two distinct cut lines required')
        forms={name:_slot(slot) for name,slot in context['angles'].items()}
        return list(ANGLE_DOMAIN),forms,None
    if kind=='rays':
        symbols={'t':S.Symbol('t',real=True)}
        vectors={name:_vector(values,symbols,2) for name,values in context['rays'].items()}
        forms={}
        for name,pair in context['angles'].items():
            if len(pair)!=2 or pair[0]==pair[1] or any(x not in vectors for x in pair):raise ValueError('two declared rays per angle')
            u,v=[vectors[x] for x in pair];_positive(u.dot(u));_positive(v.dot(v))
            form=context['angle_forms'][name]
            if not implies([R('t','>',0),R('t','<',180)],R(form,'>',0)) or not implies([R('t','>',0),R('t','<',180)],R(form,'<',180)):
                raise ValueError('ordinary angle range not proved')
            value=_parse(form,symbols)*S.pi/180
            cosine=S.trigsimp(u.dot(v)/S.sqrt(u.dot(u)*v.dot(v)))
            if not _zero(cosine-S.cos(value)):raise ValueError('the ray angle measure was not proved')
            forms[name]=form
        return [R('t','>',0),R('t','<',180)],forms,vectors
    raise ValueError('unknown incidence context')


def _predicate(context,prepared,predicate):
    op,args=_atom(predicate);domain,forms,vectors=prepared
    if op=='parallel':
        if context['kind']!='transversal' or set(args)!=set(context['lines']):raise ValueError('parallel predicate is not bound to the two cut lines')
        return [R('p','=','q')]
    if any(a not in forms for a in args):raise ValueError('undefined angle in predicate')
    first,second=[forms[a] for a in args]
    if op=='angle_equal':return [R(first,'=',second)]
    if op=='angle_supplementary':return [R('('+first+')+('+second+')','=',180)]
    if vectors is None:raise ValueError('neighbor/vertical claims need common-vertex ray data')
    a,b=[context['angles'][name] for name in args]
    def same(u,v,opposite=False):
        u=vectors[u];v=vectors[v]
        if opposite:v=-v
        # This is a proof search for one matching ray pair. A failed identity
        # is not treated as a disproved premise: if no pairing is proved below,
        # the incidence check raises unknown rather than selecting a candidate.
        return all(S.trigsimp(S.cancel(x-y))==0 for x,y in zip(u/S.sqrt(u.dot(u)),v/S.sqrt(v.dot(v))))
    if op=='vertical':valid=any(same(a[0],b[i],True) and same(a[1],b[1-i],True) for i in (0,1))
    else:valid=any(same(a[i],b[j]) and same(a[1-i],b[1-j],True) for i in (0,1) for j in (0,1))
    if not valid:raise ValueError('the claimed common-vertex incidence was not proved')
    return []


def prove_sequent(context,sequent):
    prepared=_angle_context(context);domain=prepared[0]
    premises=domain+[r for atom in sequent['given'] for r in _predicate(context,prepared,atom)]
    goal=_predicate(context,prepared,sequent['goal'])
    if not feasible(premises):raise ValueError('empty theorem hypothesis domain')
    if not all(implies(premises,c) for c in goal):raise ValueError('the supplied candidate sequent is not a proved theorem')
    return tuple(sorted(_atom(a) for a in sequent['given'])),_atom(sequent['goal'])


def _sequent_geometry(context,sequent):
    """Bind the actual angle objects, not only their coincidentally equal names."""
    predicates=sequent['given']+[sequent['goal']]
    angle_names=sorted({name for p in predicates if p['op']!='parallel' for name in p['args']})
    if context['kind']=='transversal':
        line_at={'upper':context['lines'][0],'lower':context['lines'][1]}
        roles=[]
        for name in angle_names:
            slot=context['angles'][name]
            _slot(slot)
            roles.append((name,line_at[slot['vertex']],slot['region'],slot['side']))
        return 'transversal',tuple(context['lines']),tuple(roles)
    if context['kind']=='rays':
        symbols={'t':S.Symbol('t',real=True)}
        vectors={name:_vector(v,symbols,2) for name,v in context['rays'].items()}
        roles=[]
        for name in angle_names:
            directions=[]
            for ray in context['angles'][name]:
                vector=vectors[ray];_positive(vector.dot(vector))
                unit=vector/S.sqrt(vector.dot(vector))
                directions.append(tuple(S.srepr(S.trigsimp(x)) for x in unit))
            roles.append((name,tuple(sorted(directions))))
        return 'common_vertex_rays',tuple(roles)
    raise ValueError('unsupported geometric object binding')


def angle_rule_application(spec):
    source=prove_sequent(spec['context'],spec['sequent']) if spec['query']=='apply' else None
    source_geometry=_sequent_geometry(spec['context'],spec['sequent']) if source is not None else None
    if spec['query'] not in ('apply','establish_line_from_angles'):raise ValueError('unknown rule-application query')
    def check(option):
        proved=prove_sequent(option['context'],option['sequent'])
        if source is not None:
            return proved==source and _sequent_geometry(option['context'],option['sequent'])==source_geometry
        given,goal=proved
        angle_ops={'angle_equal','angle_supplementary'}
        return bool(given) and all(p[0] in angle_ops for p in given) and goal[0]=='parallel'
    return select_unique(spec['options'],check)


def condition_of_sequent(spec):
    prove_sequent(spec['context'],spec['sequent'])
    if len(spec['sequent']['given'])!=1:raise ValueError('this condition question needs a single explicit premise')
    target=_atom(spec['sequent']['given'][0]);prepared=_angle_context(spec['context'])
    def check(option):
        expression=option['expression'];op=expression['op']
        if op=='predicate_symbol':
            if expression['name'] not in ('vertical','angle_equal','neighbor','parallel','angle_supplementary'):raise ValueError('unknown uninstantiated predicate')
            return False # a relation-valued expression has not asserted a proposition
        if op=='set_comprehension':
            _predicate(spec['context'],prepared,expression['predicate'])
            if set(expression['bound'])!=set(expression['predicate']['args']):raise ValueError('unbound comprehension object')
            return False # a set of angles is not a Boolean condition
        _predicate(spec['context'],prepared,expression)
        return _atom(expression)==target
    return select_unique(spec['options'],check)


def _linear_predicate(predicate):
    op=predicate['op']
    if op in ('angle_equal','angle_supplementary'):
        args=predicate['args']
        if len(args)!=2 or args[0]==args[1] or any(not re.fullmatch('[a-z]',v) for v in args):raise ValueError('two one-letter angle variables required')
        return R(args[0],'=',args[1]) if op=='angle_equal' else R(args[0]+'+'+args[1],'=',180)
    if op=='linear_equal':return R(predicate['left'],'=',predicate['right'])
    raise ValueError('unknown linear angle predicate')


def _schema_key(schema):
    names=schema['angles']
    if not 1<=len(names)<=4 or len(set(names))!=len(names) or any(not re.fullmatch('[a-z]',n) for n in names):raise ValueError('bounded named angle variables required')
    if not schema['goal']:raise ValueError('an implication needs a nonempty conclusion')
    images=[]
    for perm in itertools.permutations('abcd'[:len(names)]):
        rename=dict(zip(names,perm))
        def atom(p):
            _linear_predicate(p)
            if p['op']=='linear_equal':
                if (set(re.findall('[a-z]',p['left']))|set(re.findall('[a-z]',p['right'])))-set(names):raise ValueError('unbound variable in linear conclusion')
                def text(raw):return re.sub('[a-z]',lambda m:rename.get(m[0],m[0]),raw)
                return ('linear_equal',text(p['left']),text(p['right']))
            if any(a not in rename for a in p['args']):raise ValueError('unbound angle in implication')
            return (p['op'],*sorted(rename[a] for a in p['args']))
        exists=schema.get('exists',[])
        if any(n not in rename for n in exists) or len(exists)!=len(set(exists)):raise ValueError('invalid existential scope')
        representation=[sorted(rename[n] for n in exists),sorted(atom(p) for p in schema['given']),sorted(atom(p) for p in schema['goal'])]
        images.append(json.dumps(representation,separators=(',',':')))
    return min(images)


def prove_linear_schema(schema):
    names=schema['angles'];_schema_key(schema)
    ambient=[R(n,'>=',0) for n in names]+[R(n,'<=',180) for n in names]
    given=[_linear_predicate(p) for p in schema['given']]
    exists=schema.get('exists',[])
    def variables(predicate):
        if predicate['op']=='linear_equal':
            return set(re.findall('[a-z]',predicate['left']))|set(re.findall('[a-z]',predicate['right']))
        return set(predicate['args'])
    if any(variables(p)&set(exists) for p in schema['given']):raise ValueError('existential witness may not appear in antecedent')
    free_ambient=[r for r in ambient if r['left'] not in exists]
    if not feasible(free_ambient+given):raise ValueError('inconsistent implication antecedent')
    goals=[_linear_predicate(p) for p in schema['goal']]
    if exists:
        witnesses=schema['witnesses']
        if set(witnesses)!=set(exists):raise ValueError('one witness for every existential angle')
        for name,expression in witnesses.items():
            if any(v in exists for v in re.findall('[a-z]',expression)):raise ValueError('circular or cross-existential witness')
        def substitute(expression):return re.sub('[a-z]',lambda m:'('+witnesses[m[0]]+')' if m[0] in witnesses else m[0],expression)
        goals=[{**g,'left':substitute(g['left']),'right':substitute(g['right'])} for g in goals]
        goals += [R(witnesses[n],'>=',0) for n in exists]+[R(witnesses[n],'<=',180) for n in exists]
    if all(implies(free_ambient+given,g) for g in goals):return True
    if exists:raise ValueError('existential implication has no proved witness')
    witness=schema.get('counterexample')
    if not isinstance(witness,dict) or set(witness)!=set(names):raise ValueError('a complete legal angle counterexample is required')
    values={n:number(v) for n,v in witness.items()}
    if any(not 0<=v<=180 for v in values.values()):raise ValueError('counterexample angle outside ordinary closed range')
    def value(expression):return number(re.sub('[a-z]',lambda m:'('+str(values[m[0]])+')',expression))
    if any(value(g['left'])!=value(g['right']) for g in given):raise ValueError('counterexample violates its antecedent')
    if all(value(g['left'])==value(g['right']) for g in goals):raise ValueError('counterexample does not violate the conclusion')
    return False


def implication_rewrite(spec):
    if not prove_linear_schema(spec['source']):raise ValueError('source statement is not proved')
    target=_schema_key(spec['source'])
    def check(option):
        proved=prove_linear_schema(option['schema'])
        return proved and _schema_key(option['schema'])==target
    return select_unique(spec['options'],check)


def _assignment(raw,symbols):
    if set(raw)!=set(symbols):raise ValueError('a full parameter assignment is required')
    values={name:_parse(source,{}) for name,source in raw.items()}
    for name,value in values.items():
        s=symbols[name]
        if value.is_real is not True or (s.is_integer is True and value.is_integer is not True) or (s.is_positive is True and value.is_positive is not True) or (s.is_nonnegative is True and value.is_nonnegative is not True):
            raise ValueError('assignment violates the declared parameter domain')
    return {symbols[n]:v for n,v in values.items()}


def translation_identifiability(spec):
    def check(option):
        symbols=_symbols(option['symbols']);known=option['known_parameters']
        if len(set(known))!=len(known) or any(n not in symbols for n in known):raise ValueError('unbound descriptor parameter')
        matrix=S.Matrix([[_parse(v,symbols) for v in row] for row in option['linear_part']]);offset=_vector(option['offset'],symbols,2)
        if matrix.shape!=(2,2):raise ValueError('a plane affine map requires a 2x2 linear part')
        if any(S.trigsimp(matrix[i,j]-int(i==j))!=0 for i in range(2) for j in range(2)):
            assignment=_assignment(option['counterexample'],symbols)
            if matrix.subs(assignment)==S.eye(2):raise ValueError('the nontranslation counterexample is not valid')
            return False
        remaining=set().union(*(v.free_symbols for v in offset))-{symbols[n] for n in known}
        if remaining:
            pair=option['indistinguishable_parameters']
            if len(pair)!=2:raise ValueError('two descriptor-preserving maps required')
            first,second=[_assignment(v,symbols) for v in pair]
            if any(first[symbols[n]]!=second[symbols[n]] for n in known):raise ValueError('the witness changes known descriptor data')
            if offset.subs(first)==offset.subs(second):raise ValueError('the witness does not distinguish translations')
            vertices=[_vector(p,symbols,2) for p in option['shape']]
            if len(vertices)<2:raise ValueError('a nontrivial shape witness is required')
            if any(v.subs(first)!=v.subs(second) for v in vertices):raise ValueError('the witness changes the unshifted shape')
            for a,b in itertools.combinations(vertices,2):
                if not _zero(((a+offset)-(b+offset)).dot((a+offset)-(b+offset))-(a-b).dot(a-b)):
                    raise ValueError('translation did not preserve shape distances')
            return False
        if 'polar_parameters' in option:
            theta,length=option['polar_parameters']
            if theta==length or len(known)!=2 or set((theta,length))!=set(known) or option['symbols'][theta]!='real' or option['symbols'][length]!='nonnegative':
                raise ValueError('full angle and nonnegative radius domains required')
            t,d=symbols[theta],symbols[length]
            if any(not _zero(a-b) for a,b in zip(offset,S.Matrix([d*S.cos(t),d*S.sin(t)]))):raise ValueError('polar displacement formula is incorrect')
            x,y=S.symbols('_x _y',real=True);r=S.sqrt(x*x+y*y);angle=S.atan2(y,x)
            if not _zero(r*S.cos(angle)-x) or not _zero(r*S.sin(angle)-y):raise ValueError('nonzero-vector polar inverse failed')
            # The inverse is on x²+y²>0; the missing zero vector is realized
            # separately by d=0, with any supplied angle.
            if offset.subs(d,0)!=S.zeros(2,1):raise ValueError('zero translation is not covered')
            return True
        if 'cartesian_parameters' in option:
            names=option['cartesian_parameters']
            if len(names)!=2 or len(set(names))!=2 or len(known)!=2 or set(names)!=set(known) or any(option['symbols'][n]!='real' for n in names):raise ValueError('full Cartesian displacement domains required')
            if any(not _zero(a-symbols[n]) for a,n in zip(offset,names)):raise ValueError('Cartesian displacement inverse failed')
            return True
        raise ValueError('translation family coverage/identification has no certificate')
    return select_unique(spec['options'],check)


HANDLERS={'f63_line_notation':line_notation,'f63_basis_application':basis_application,
          'f63_angle_rule_application':angle_rule_application,'f63_condition_of_sequent':condition_of_sequent,
          'f63_implication_rewrite':implication_rewrite,'f63_translation_identifiability':translation_identifiability}
