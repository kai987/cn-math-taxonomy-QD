#!/usr/bin/env python3
"""Check the fixed 43-item review without conflating formal and contextual proof."""
from collections import Counter
import json
from pathlib import Path
from check_manual_review import review_errors as validate_review
from math_models import MODEL_PATH

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'data/answer_review_remaining_43.json'
SCOPE_SHA256 = '59e6e26bb1035d20256a00df0ddbc72266d132adb5f9b4cdfd83ef030728fac7'
BASELINE = '8edd94ffb32593a33eb2ec7a50fc383f22fe589d'


def review_errors(questions, review, records, topics=None):
    errors = validate_review(questions, review, records, topics, scope_count=43,
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
    print('PASS: all 43 references, formal evidence and contextual grading boundaries are current')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
