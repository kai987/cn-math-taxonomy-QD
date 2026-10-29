#!/usr/bin/env python3
"""Keep all 455 follow-up outcomes and model translations auditable."""
import hashlib
import json
from pathlib import Path
from math_models import MODEL_PATH, binding_errors, model_id, signature

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'data/answer_review_remaining_455.json'
SCOPE_SHA256 = '424330f6f0102e3cfe6ed7acf28ea39f990156076c91703f4084489db1ef6879'


def review_errors(questions, review, records):
    errors = []
    entries = review.get('entries', [])
    ids = [entry.get('id', '') for entry in entries]
    digest = hashlib.sha256('\n'.join(sorted(ids)).encode()).hexdigest()
    if len(ids) != 455 or len(set(ids)) != 455 or digest != SCOPE_SHA256:
        errors.append('follow-up must cover exactly the original 455 IDs once each')
    by_id = {question['id']: question for question in questions}
    for entry in entries:
        qid = entry['id']
        question = by_id.get(qid)
        if not question:
            errors.append(qid + ': question missing')
            continue
        if entry.get('question_sha256') != signature(question):
            errors.append(qid + ': question changed since follow-up')
        if not isinstance(entry.get('derivation'), str) or len(entry['derivation']) < 12:
            errors.append(qid + ': missing derivation')
        if not isinstance(entry.get('boundary'), str) or len(entry['boundary']) < 12:
            errors.append(qid + ': missing grading/proof boundary')
        status = entry.get('status')
        if status == 'model':
            record = records.get(qid)
            if not record or model_id(question.get('verify')) != qid:
                errors.append(qid + ': model proof missing')
            elif entry.get('model_sha256') != signature(record['spec']):
                errors.append(qid + ': model semantics changed since review')
        elif status == 'expression':
            if not question.get('verify') or entry.get('verify') != question['verify'] or model_id(question['verify']):
                errors.append(qid + ': independent expression missing or changed')
        elif status == 'manual':
            if question.get('verify'):
                errors.append(qid + ': manual outcome cannot be counted as fully automatic')
        else:
            errors.append(qid + ': unsupported review outcome')
        if question['type'] == 'self' and status != 'manual':
            errors.append(qid + ': open response must retain human judgement')
    errors.extend(binding_errors(questions, records))
    return errors


def main():
    questions = json.loads((ROOT / 'data/questions.json').read_text())
    review = json.loads(PATH.read_text())
    records = json.loads(MODEL_PATH.read_text())['models']
    errors = review_errors(questions, review, records)
    for error in errors:
        print(error)
    if errors:
        return 1
    print('PASS: all 455 follow-up outcomes and mathematical model bindings are current')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
