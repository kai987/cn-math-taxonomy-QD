#!/usr/bin/env python3
"""Bind all original 63 manual questions to their current review evidence."""
import json
from pathlib import Path
from check_manual_review import review_errors as validate_review
from math_models import MODEL_PATH

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'data/answer_review_remaining_63.json'
SCOPE_SHA256 = 'ab1704700e199229266ae6ede40a6a9e77e12a654d9b879b367573cd2c3bd629'
BASELINE = '71d1f7d61bff62c5850f49d6ab0581df1e6f3ec3'


def review_errors(questions, review, records, topics=None):
    return validate_review(questions, review, records, topics, scope_count=63,
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
    print('PASS: all 63 reviewed references, models and human-judgement boundaries are current')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
