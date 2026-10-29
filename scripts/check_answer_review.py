#!/usr/bin/env python3
"""Validate the per-question review fixture; no generated answers or file writes."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW_PATH = ROOT / 'data/answer_review_2026-10-30.json'
# The 532 questions without verify at be357c0, independent of current coverage.
SCOPE_SHA256 = '536bdb7df06dd82c52a8926c52fa0e2e492196964c074b2104929abf379ee636'


def fingerprint(question):
    source = json.dumps(question, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(source.encode('utf-8')).hexdigest()


def review_errors(questions, review, topics=None):
    errors = []
    entries = review.get('entries', [])
    if not isinstance(entries, list):
        return ['entries must be a list']
    ids = [entry.get('id', '') for entry in entries]
    digest = hashlib.sha256('\n'.join(sorted(ids)).encode('utf-8')).hexdigest()
    if len(ids) != 532 or len(set(ids)) != 532 or digest != SCOPE_SHA256:
        errors.append('review must cover exactly the original 532 question IDs once each')
    by_id = {question['id']: question for question in questions}
    by_topic = {topic['id']: topic for topic in topics} if topics is not None else None
    for entry in entries:
        qid = entry.get('id')
        question = by_id.get(qid)
        if not question:
            errors.append('%s: question missing' % qid)
            continue
        if entry.get('question_sha256') != fingerprint(question):
            errors.append('%s: source changed since review; re-review wording, options and grading' % qid)
        if entry.get('expected_answer') != question['answer']:
            errors.append('%s: reference disagrees with reviewed answer' % qid)
        if entry.get('verify') != question.get('verify'):
            errors.append('%s: reviewed independent calculation was removed or changed' % qid)
        if not isinstance(entry.get('reason'), str) or len(entry['reason']) < 12:
            errors.append('%s: missing specific reasoning' % qid)
        if entry.get('basis') not in ('calculation', 'definition', 'open'):
            errors.append('%s: unsupported review basis' % qid)
        grading = entry.get('grading', [])
        if question['type'] in ('short', 'self') and not grading:
            errors.append('%s: missing short/open grading boundaries' % qid)
        if any(not isinstance(case.get('input'), str) or case.get('result') not in (
                'correct', 'wrong', 'manual') for case in grading):
            errors.append('%s: invalid grading case' % qid)
        if by_topic is not None and 'catalogue_preview' in entry:
            actual = by_topic.get(question['topicId'], {}).get('diagnostic_question')
            if actual != entry['catalogue_preview']:
                errors.append('%s: catalogue preview differs from the reviewed conditions/reference' % qid)
    return errors


def main():
    questions = json.loads((ROOT / 'data/questions.json').read_text())
    review = json.loads(REVIEW_PATH.read_text())
    topics = json.loads((ROOT / 'data/topics.json').read_text())
    errors = review_errors(questions, review, topics)
    for error in errors:
        print(error)
    if errors:
        return 1
    print('PASS: all 532 reviewed references, reasoning and source fingerprints are current')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
