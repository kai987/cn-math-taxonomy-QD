#!/usr/bin/env python3
"""Validate the original 105 questions, including all partial-proof boundaries."""
import json
from pathlib import Path
from check_manual_review import review_errors as validate_review
from math_models import MODEL_PATH

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'data/answer_review_remaining_105.json'
SCOPE_SHA256 = '0df452968486ae6089be5bab924c552c9254a9c26f2cd25a7c094e48cff6a476'
BASELINE = '2c40fd2624d9830d4b52739169b843cd2c649f86'


def review_errors(questions, review, records, topics=None):
    return validate_review(questions, review, records, topics, scope_count=105,
                           scope_sha256=SCOPE_SHA256, baseline=BASELINE)


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
    print('PASS: all 105 reviewed references, mathematical proofs and manual boundaries are current')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
