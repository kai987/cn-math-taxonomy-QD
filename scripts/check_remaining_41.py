#!/usr/bin/env python3
"""Check the fixed 41-item review without conflating formal and contextual proof."""
from collections import Counter
import json
from pathlib import Path
from check_manual_review import review_errors as validate_review
from math_models import MODEL_PATH

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'data/answer_review_remaining_41.json'
SCOPE_SHA256 = '0c1f42731a0de1dbce91e3707da802e6382df3543b7ea3f8e56c5e29370ca198'
BASELINE = '6be686d53f2a9c854b75d4e88549304b2e3373c3'


def review_errors(questions, review, records, topics=None):
    errors = validate_review(questions, review, records, topics, scope_count=41,
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
    print('PASS: all 41 references, formal evidence and contextual grading boundaries are current')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
