#!/usr/bin/env python3
"""Check the fixed 13-item review without conflating formal and contextual proof."""
from collections import Counter
import json
from pathlib import Path
from check_manual_review import review_errors as validate_review
from math_models import MODEL_PATH

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'data/answer_review_remaining_13.json'
SCOPE_SHA256 = 'b22252f3ad49960a9e753fa90a715591848d9e06f09fdde5ca6115746de3b91d'
BASELINE = 'b93c37f440ecb95e8c6b5cf38c260b0b56709a8c'
SELF_ASSESSED_IDS = {'cnm_' + suffix for suffix in (
    '085_q1', '102_q1', '102_q2', '102_q3', '105_q1', '105_q2',
    '130_q4', '198_q2', '292_q2', '292_q3', '292_q4')}


def review_errors(questions, review, records, topics=None):
    errors = validate_review(questions, review, records, topics, scope_count=13,
                             scope_sha256=SCOPE_SHA256, baseline=BASELINE)
    categories = {'comparative_criterion', 'curriculum_convention', 'design_or_evidence', 'open_response'}
    counts = Counter()
    for entry in review.get('entries', []):
        gap = entry.get('automation_gap')
        if entry.get('status') != 'manual':
            if gap is not None:
                errors.append(entry['id'] + ': complete proof cannot retain an unresolved automation gap')
            continue
        if not isinstance(gap, dict) or gap.get('category') not in categories:
            errors.append(entry['id'] + ': manual item needs a concrete automation-gap category')
            continue
        counts[gap['category']] += 1
        for field in ('missing_basis', 'revisit_if'):
            if not isinstance(gap.get(field), str) or len(gap[field]) < 12:
                errors.append(entry['id'] + ': missing automation boundary: ' + field)
    if review.get('summary', {}).get('manual_gap_categories') != dict(counts):
        errors.append('manual-gap category counts disagree with current reviewed entries')
    by_id = {q['id']: q for q in questions}
    reference_models = sum(entry.get('status') == 'model' and by_id.get(entry['id'], {}).get('type') == 'self'
                           for entry in review.get('entries', []))
    if review.get('summary', {}).get('self_reference_models') != reference_models:
        errors.append('self reference model count disagrees with reviewed entries')
    self_assessed = {q['id'] for q in questions if q.get('self_assess') is True}
    if self_assessed != SELF_ASSESSED_IDS:
        errors.append('self-assessment policy must cover exactly the 11 reviewed conditional choices')
    if review.get('summary', {}).get('self_assessed_choices') != len(self_assessed):
        errors.append('self-assessed choice count disagrees with current policy')
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
    print('PASS: all 13 references, formal evidence and contextual grading boundaries are current')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
