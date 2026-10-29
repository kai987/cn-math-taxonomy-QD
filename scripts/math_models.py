"""Dispatch source-bound mathematical models without reading answer keys.

Inputs are reviewed translations of wording/options, not automatic NLP. Each
handler must derive its result from those mathematical inputs. Binding checks
run separately against the question bank and reject stale translations.
"""
import ast
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / 'data/verification_models.json'


def signature(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode('utf-8')).hexdigest()


@lru_cache(maxsize=1)
def handlers():
    from models_algebra import HANDLERS as algebra
    from models_geometry import HANDLERS as geometry
    from models_applications import HANDLERS as applications
    from models_symbolic import HANDLERS as symbolic
    result = {'cube_net': cube_net}
    for group in (algebra, geometry, applications, symbolic):
        if set(result).intersection(group):
            raise ValueError('duplicate model kind')
        result.update(group)
    return result


def cube_net(spec):
    from cube_folding import fold_cube_net
    from model_types import select_unique
    if spec.get('predicate') not in ('cannot_fold_to_cube', 'can_fold_to_cube'):
        raise ValueError('unsupported cube-net predicate')

    def check(option):
        cases = option.get('cases', [])
        if not cases:
            raise ValueError('missing geometric interpretation')
        outcomes = {fold_cube_net(case['cells'])['folds'] for case in cases}
        if len(outcomes) != 1:
            raise ValueError('wording permits inconsistent folding results')
        folds = next(iter(outcomes))
        return not folds if spec['predicate'] == 'cannot_fold_to_cube' else folds

    return select_unique(spec['options'], check)


@lru_cache(maxsize=1)
def catalogue():
    records = json.loads(MODEL_PATH.read_text(encoding='utf-8'))
    if records.get('schema_version') != 1 or not isinstance(records.get('models'), dict):
        raise ValueError('unsupported model catalogue')
    return records['models']


def evaluate(spec):
    kind = spec.get('kind')
    if kind not in handlers():
        raise ValueError('unsupported mathematical model: ' + str(kind))
    return handlers()[kind](spec)


def model(question_id):
    if not isinstance(question_id, str) or not re.fullmatch(r'cnm_(?:p)?\d+_q\d+', question_id):
        raise ValueError('invalid model question id')
    record = catalogue().get(question_id)
    if not record:
        raise ValueError('no mathematical model for ' + question_id)
    return evaluate(record['spec'])


def model_id(expression):
    try:
        tree = ast.parse(expression, mode='eval').body
        if (isinstance(tree, ast.Call) and isinstance(tree.func, ast.Name) and tree.func.id == 'model'
                and len(tree.args) == 1 and not tree.keywords and isinstance(tree.args[0], ast.Constant)
                and isinstance(tree.args[0].value, str)):
            return tree.args[0].value
    except (SyntaxError, TypeError):
        pass
    return None


def binding_errors(questions, records):
    errors = []
    by_id = {q['id']: q for q in questions}
    forbidden = {'answer', 'expected', 'correct', 'is_true', 'truth', 'verdict'}

    def has_outcome(value):
        if isinstance(value, dict):
            return bool(forbidden.intersection(value)) or any(has_outcome(v) for v in value.values())
        return isinstance(value, list) and any(has_outcome(v) for v in value)

    for qid, record in records.items():
        question = by_id.get(qid)
        if not question:
            errors.append(qid + ': model question missing')
            continue
        if record.get('question_sha256') != signature(question):
            errors.append(qid + ': mathematical translation is stale')
        if model_id(question.get('verify')) != qid:
            errors.append(qid + ': expression must call its own mathematical model')
        spec = record.get('spec', {})
        if has_outcome(spec):
            errors.append(qid + ': a model input contains a declared answer/truth value')
        if question['type'] == 'choice':
            options = spec.get('options', [])
            visible = [{k: o.get(k) for k in ('key', 'text')} for o in options]
            if visible != question['choices']:
                errors.append(qid + ': mathematical candidates differ from source options')
    for question in questions:
        qid = model_id(question.get('verify'))
        if qid is not None and (qid != question['id'] or qid not in records):
            errors.append(question['id'] + ': missing or cross-question model')
    return errors
