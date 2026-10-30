#!/usr/bin/env python3
"""Bind the fixed 160-question review to its mathematical and grading evidence."""
from collections import Counter
from fractions import Fraction
import json
from pathlib import Path

from check_remaining_review import review_errors as validate_review
from math_models import MODEL_PATH

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'data/answer_review_remaining_160.json'
SCOPE_SHA256 = '4f241ecfc220a2956bb515681fae108fbb28e4d0ff573b9bc7feb72f3801228c'
BASELINE = '65a63b7a406cf603cdd9aefcfb9e7cba34d56e49'


def check_supporting_proof(proof):
    """Execute partial mathematics without promoting the whole question."""
    from exact_polynomial import Polynomial
    from verify_questions import num_equal, safe_eval
    actual = safe_eval(proof['expression'])
    expected = proof['value']
    comparison = proof.get('comparison', 'equal')
    if comparison == 'polynomial':
        valid = isinstance(actual, Polynomial) and actual.matches(expected)
    elif comparison == 'lt':
        valid = (not isinstance(actual, bool) and isinstance(actual, (int, float, Fraction))
                 and actual < Fraction(expected))
    elif comparison == 'equal':
        actuals = list(actual) if isinstance(actual, (list, tuple)) else [actual]
        expecteds = expected if isinstance(expected, list) else [expected]
        valid = len(actuals) == len(expecteds) and all(
            not isinstance(e, bool) and num_equal(Fraction(str(e)), a)
            for a, e in zip(actuals, expecteds))
    else:
        raise ValueError('unsupported component comparison')
    if not valid:
        raise ValueError('component result disagrees with its independent reference')


def review_errors(questions, review, records, topics=None, *, scope_count=160,
                  scope_sha256=SCOPE_SHA256, baseline=BASELINE):
    errors = validate_review(questions, review, records, scope_count=scope_count, scope_sha256=scope_sha256)
    if review.get('baseline_commit') != baseline or review.get('scope_count') != scope_count:
        errors.append('%s-question baseline or declared scope changed' % scope_count)
    by_id = {question['id']: question for question in questions}
    by_topic = {topic['id']: topic for topic in topics} if topics is not None else None
    entries = review.get('entries', [])
    for entry in entries:
        qid = entry.get('id')
        question = by_id.get(qid)
        if question is None:
            continue
        if entry.get('expected_answer') != question['answer']:
            errors.append(qid + ': reviewed reference changed')
        for case in entry.get('grading', []):
            if not isinstance(case.get('input'), str) or case.get('result') not in ('correct', 'wrong', 'manual'):
                errors.append(qid + ': invalid grading case')
        if question['type'] == 'self' and not entry.get('grading'):
            errors.append(qid + ': open response needs explicit human-grading examples')
        for proof in entry.get('supporting_proofs', []):
            try:
                if entry.get('status') != 'manual':
                    raise ValueError('partial proof must retain whole-question human judgement')
                check_supporting_proof(proof)
            except (KeyError, ValueError, TypeError, ArithmeticError) as error:
                errors.append(qid + ': invalid component proof: ' + str(error))
        if by_topic is not None and 'catalogue_preview' in entry:
            if by_topic.get(question['topicId'], {}).get('diagnostic_question') != entry['catalogue_preview']:
                errors.append(qid + ': catalogue preview changed')
    outcomes = Counter(entry.get('status') for entry in entries)
    remaining = Counter(by_id[entry['id']]['type'] for entry in entries
                        if entry.get('status') == 'manual' and entry['id'] in by_id)
    kinds = Counter(records[entry['id']]['spec']['kind'] for entry in entries
                    if entry.get('status') == 'model' and entry['id'] in records)
    repairs = sum(bool(entry.get('corrected_fields')) for entry in entries)
    components = sum(len(entry.get('supporting_proofs', [])) for entry in entries)
    summary = review.get('summary', {})
    for key, actual in (('reviewed', len(entries)), ('outcomes', dict(outcomes)),
                        ('remaining_by_type', dict(remaining)), ('models_by_kind', dict(kinds)),
                        ('repaired_questions', repairs), ('component_checks', components)):
        if summary.get(key) != actual:
            errors.append('%s-question summary disagrees with entries: %s' % (scope_count, key))
    return errors


def main():
    questions = json.loads((ROOT / 'data/questions.json').read_text())
    review = json.loads(PATH.read_text())
    records = json.loads(MODEL_PATH.read_text())['models']
    topics = json.loads((ROOT / 'data/topics.json').read_text())
    errors = review_errors(questions, review, records, topics)
    for error in errors:
        print(error)
    if errors:
        return 1
    print('PASS: all 160 reviewed derivations, model inputs and grading boundaries are current')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
