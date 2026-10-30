/* Regression contracts from the 532-item independent review. Frozen answers
 * catch future key/ordering/normalization drift; they are not mathematical
 * proofs. Computational proof expressions run separately in Python. */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const E = require('../diagnose/engine.js');
const read = name => JSON.parse(fs.readFileSync(path.join(__dirname, '../data', name), 'utf8'));
const questions = new Map(read('questions.json').map(q => [q.id, q]));
const review = read('answer_review_2026-10-30.json');
let assertions = 0;
const seen = new Set();
function check(q, input, expected) {
  assertions++;
  seen.add(JSON.stringify([q.id, input, expected]));
  assert.equal(E.judgeQuestion(q, input).verdict, expected, q.id + ' input=' + JSON.stringify(input));
}
for (const item of review.entries) {
  const q = questions.get(item.id);
  assert.ok(q, item.id);
  check(q, '', 'manual');
  check(q, item.expected_answer, q.type === 'self' ? 'manual' : 'correct');
  if (q.type === 'choice') {
    for (const choice of q.choices) {
      const result = choice.key === item.expected_answer ? 'correct' : 'wrong';
      for (const input of [choice.key, choice.key.toLowerCase(),
        String.fromCharCode(choice.key.charCodeAt(0) + 0xfee0)]) check(q, input, result);
      // A bare valid letter is always an option key (e.g. algebra text "a"
      // in option B still means key A when submitted as a bare letter).
      const normalized = E.normalizeText(choice.text).toUpperCase();
      if (!q.choices.some(candidate => candidate.key === normalized)) check(q, choice.text, result);
    }
    check(q, 'Z', 'manual');
  } else if (q.type === 'numeric') {
    const parts = item.expected_answer.split(/[，,]/);
    const numeratorPlusOne = parts[0].includes('/')
      ? parts[0].replace(/^(-?\d+)\/(\d+)$/, (_, n, d) => (Number(n) + Number(d)) + '/' + d)
      : String(Number(parts[0]) + 1);
    check(q, [numeratorPlusOne, ...parts.slice(1)].join(','), 'wrong');
    check(q, parts.join(','), 'correct');
    if (parts.length > 1 && !q.unordered && new Set(parts).size > 1) {
      check(q, parts.slice().reverse().join(','), 'wrong');
    }
  } else if (q.type === 'short') {
    for (const accepted of q.accept || []) check(q, accepted, 'correct');
    check(q, '无法确认的写法', 'manual');
  } else if (q.type === 'self') {
    check(q, '无关或错误的答案', 'manual');
  }
  for (const grading of item.grading || []) check(q, grading.input, grading.result);
}
for (const item of [...read('answer_review_remaining_455.json').entries,
  ...read('answer_review_remaining_160.json').entries,
  ...read('answer_review_remaining_105.json').entries]) {
  for (const grading of item.grading || []) {
    if (!seen.has(JSON.stringify([item.id, grading.input, grading.result]))) {
      check(questions.get(item.id), grading.input, grading.result);
    }
  }
}
console.log('PASS: 532 reviewed questions, 455, 160 and 105 follow-up records; ' + assertions + ' answer grading assertions');
