#!/usr/bin/env node
/* 诊断引擎测试：node tests/test_engine.js （无依赖，仅用 assert） */
'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const E = require('../diagnose/engine.js');

let passed = 0;
let failed = 0;
function test(name, fn) {
  try { fn(); passed++; console.log('  ok   ' + name); }
  catch (e) { failed++; console.log('  FAIL ' + name + '\n       ' + (e && e.stack || e).split('\n').slice(0, 4).join('\n       ')); }
}
const sorted = (it) => Array.from(it).sort();

/* ------------------------------------------------------------ 手造小图
 *   X(外部) <- F <- E <- C <---hard--- T
 *              F <- D <---hard--- T
 *              F <- B <---soft--- T
 *   Z 与 T 无关
 * topics 顺序：X F E C D B T Z（同级先修按此顺序出题）
 */
function mk(id, extra) {
  return Object.assign({
    id: id, name: id, external: false,
    diagnostic_question: { question: id + '?', answer: '1' }
  }, extra || {});
}
const smallTopics = [
  mk('X', { external: true, diagnostic_question: undefined }),
  mk('F'), mk('E'), mk('C'), mk('D'), mk('B'), mk('T'), mk('Z')
];
const smallDeps = [
  { topicId: 'F', prerequisiteId: 'X', strength: 'hard' },
  { topicId: 'E', prerequisiteId: 'F', strength: 'hard' },
  { topicId: 'C', prerequisiteId: 'E', strength: 'hard' },
  { topicId: 'D', prerequisiteId: 'F', strength: 'hard' },
  { topicId: 'B', prerequisiteId: 'F', strength: 'hard' },
  { topicId: 'T', prerequisiteId: 'B', strength: 'soft' },   // 故意把 soft 写在 hard 前面
  { topicId: 'T', prerequisiteId: 'D', strength: 'hard' },
  { topicId: 'T', prerequisiteId: 'C', strength: 'hard' }
];
const G = E.buildGraph(smallTopics, smallDeps);

function run(session, script) {
  // script: {id: 'correct'|'wrong'|'skip'} —— 按引擎的出题顺序作答，返回 [会话, 出题顺序]
  const asked = [];
  let s = session;
  for (let guard = 0; guard < 100; guard++) {
    const q = E.nextQuestion(G, s);
    if (!q) break;
    asked.push(q);
    assert.ok(script[q], '脚本里没有 ' + q + ' 的答案');
    s = E.applyAnswer(G, s, q, script[q]);
  }
  return [s, asked];
}

function assertTopological(order, graph) {
  const pos = new Map(order.map((id, i) => [id, i]));
  order.forEach((id) => {
    graph.prereqs[id].forEach((p) => {
      if (pos.has(p.id)) assert.ok(pos.get(p.id) < pos.get(id), p.id + ' 应排在 ' + id + ' 之前');
    });
  });
}

console.log('小型手造图（每个知识点只有一道题——回退模式：答错即薄弱）');

test('祖先子图：目标 + 全部祖先（含外部节点），不含无关点', () => {
  assert.deepStrictEqual(sorted(E.ancestors(G, 'T')), ['B', 'C', 'D', 'E', 'F', 'X']);
  assert.deepStrictEqual(sorted(E.ancestors(G, 'E')), ['F', 'X']);
  assert.deepStrictEqual(sorted(E.ancestors(G, 'X')), []);
  const sub = E.subgraph(G, ['T']);
  assert.deepStrictEqual(sorted(sub.nodes), ['B', 'C', 'D', 'E', 'F', 'T', 'X']);
});

test('拓扑序：每个先修都排在依赖它的点之前', () => {
  const sub = E.subgraph(G, ['T']);
  assertTopological(sub.nodes, G);
  assert.strictEqual(sub.nodes[0], 'X');
  assert.strictEqual(sub.nodes[sub.nodes.length - 1], 'T');
  const multi = E.subgraph(G, ['C', 'D']);
  assertTopological(multi.nodes, G);
  assert.deepStrictEqual(sorted(multi.nodes), ['C', 'D', 'E', 'F', 'X']);
});

test('先修按 hard 优先、再 soft', () => {
  assert.deepStrictEqual(G.prereqs.T.map((p) => p.id + ':' + p.strength), ['C:hard', 'D:hard', 'B:soft']);
});

test('第一题问目标本身', () => {
  const s = E.createSession(G, ['T']);
  assert.strictEqual(E.nextQuestion(G, s), 'T');
});

test('答对：该点及所有祖先（含外部）视为掌握并跳过', () => {
  let s = E.createSession(G, ['T']);
  s = E.applyAnswer(G, s, 'T', 'correct');
  assert.strictEqual(E.nextQuestion(G, s), null);
  ['B', 'C', 'D', 'E', 'F', 'X', 'T'].forEach((id) => assert.strictEqual(E.statusOf(s, id), 'mastered', id));
  assert.strictEqual(s.status.T.src, 'direct');
  assert.strictEqual(s.status.F.src, 'inferred');
  assert.strictEqual(E.statusOf(s, 'Z'), 'unknown');
  const sum = E.summarize(G, s);
  assert.deepStrictEqual(sum.weak, []);
  assert.deepStrictEqual(sum.roots, []);
  assert.deepStrictEqual(sum.path, []);
  assert.strictEqual(sum.asked, 1);
});

test('答错：回溯先修，hard 先于 soft，深度优先', () => {
  const s0 = E.createSession(G, ['T']);
  const [s, asked] = run(s0, { T: 'wrong', C: 'wrong', E: 'correct', D: 'correct', B: 'correct' });
  // T 错 -> 先修 C,D（hard，按文件顺序）再 B（soft）；C 错 -> 先问 C 的先修 E，再回到 D、B
  assert.deepStrictEqual(asked, ['T', 'C', 'E', 'D', 'B']);
  assert.strictEqual(E.nextQuestion(G, s), null);
});

test('答错后首个追问是 hard 先修，soft 排最后', () => {
  let s = E.createSession(G, ['T']);
  s = E.applyAnswer(G, s, 'T', 'wrong');
  assert.strictEqual(E.nextQuestion(G, s), 'C');
  s = E.applyAnswer(G, s, 'C', 'correct'); // C 对 -> E、F、X 掌握
  assert.strictEqual(E.nextQuestion(G, s), 'D');
  s = E.applyAnswer(G, s, 'D', 'correct');
  assert.strictEqual(E.nextQuestion(G, s), 'B');
});

test('「不会」(skip) 与答错等效', () => {
  const [a] = run(E.createSession(G, ['T']), { T: 'skip', C: 'skip', E: 'correct', D: 'correct', B: 'correct' });
  const [b] = run(E.createSession(G, ['T']), { T: 'wrong', C: 'wrong', E: 'correct', D: 'correct', B: 'correct' });
  assert.deepStrictEqual(a.status, b.status);
});

test('已判定的点不重复问；共享先修只问一次', () => {
  const [, asked] = run(E.createSession(G, ['T']), { T: 'wrong', C: 'wrong', E: 'wrong', F: 'correct', D: 'wrong', B: 'wrong' });
  assert.strictEqual(new Set(asked).size, asked.length);
  assert.deepStrictEqual(asked, ['T', 'C', 'E', 'F', 'D', 'B']);
});

test('题量上限生效，剩余标为未测', () => {
  const s0 = E.createSession(G, ['T'], { limit: 2 });
  const [s, asked] = run(s0, { T: 'wrong', C: 'wrong' });
  assert.deepStrictEqual(asked, ['T', 'C']);
  assert.strictEqual(E.nextQuestion(G, s), null);
  const sum = E.summarize(G, s);
  assert.strictEqual(sum.asked, 2);
  assert.strictEqual(sum.limitReached, true);
  assert.deepStrictEqual(sorted(sum.untested), ['B', 'D', 'E', 'F', 'X']);
  assert.deepStrictEqual(sorted(sum.weak), ['C', 'T']);
  // 根因 C：它的先修 E 还没测到，要标出来
  assert.deepStrictEqual(sum.roots.map((r) => r.id), ['C']);
  assert.deepStrictEqual(sum.roots[0].pendingPrereqs, ['E']);
});

test('limit 默认 16，limit=1 只问目标', () => {
  assert.strictEqual(E.DEFAULT_LIMIT, 16);
  assert.strictEqual(E.createSession(G, ['T']).limit, 16);
  const s0 = E.createSession(G, ['T'], { limit: 1 });
  const [, asked] = run(s0, { T: 'wrong' });
  assert.deepStrictEqual(asked, ['T']);
});

test('根因：薄弱且先修中没有薄弱点；路径为拓扑序且不含已掌握', () => {
  const [s] = run(E.createSession(G, ['T']), { T: 'wrong', C: 'wrong', E: 'correct', D: 'correct', B: 'correct' });
  const sum = E.summarize(G, s);
  assert.deepStrictEqual(sorted(sum.weak), ['C', 'T']);
  assert.deepStrictEqual(sum.roots.map((r) => r.id), ['C']);
  assert.deepStrictEqual(sum.path.map((p) => p.id), ['C', 'T']);
  assert.strictEqual(sum.path[0].isRoot, true);
  assert.strictEqual(sum.path[1].isTarget, true);
  assert.deepStrictEqual(sorted(sum.mastered), ['B', 'D', 'E', 'F', 'X']);
  assert.strictEqual(sum.finished, true);
  assert.strictEqual(sum.limitReached, false);
});

test('多个根因：路径含根因到目标之间所有未掌握点，拓扑序', () => {
  // T、C、E、D 薄弱；F 掌握 -> E、D 都是根因；B 掌握
  const [s] = run(E.createSession(G, ['T']), { T: 'wrong', C: 'wrong', E: 'wrong', F: 'correct', D: 'wrong', B: 'correct' });
  const sum = E.summarize(G, s);
  assert.deepStrictEqual(sorted(sum.roots.map((r) => r.id)), ['D', 'E']);
  assert.deepStrictEqual(sorted(sum.path.map((p) => p.id)), ['C', 'D', 'E', 'T']);
  assertTopological(sum.path.map((p) => p.id), G);
  sum.path.forEach((p) => assert.notStrictEqual(p.status, 'mastered'));
  assert.deepStrictEqual(sum.path.filter((p) => p.isRoot).map((p) => p.id).sort(), ['D', 'E']);
});

test('外部（小学）节点不出题；根因的外部先修单独标出', () => {
  const [s, asked] = run(E.createSession(G, ['T']), { T: 'wrong', C: 'wrong', E: 'wrong', F: 'wrong', D: 'wrong', B: 'wrong' });
  assert.ok(!asked.includes('X'));
  const sum = E.summarize(G, s);
  assert.deepStrictEqual(sum.roots.map((r) => r.id), ['F']);
  assert.deepStrictEqual(sum.roots[0].externalPrereqs, ['X']);
  assert.deepStrictEqual(sum.roots[0].pendingPrereqs, []);
  assert.deepStrictEqual(sum.untested, ['X']);
});

test('多目标：离目标最近的先问；答对一个即覆盖其余祖先目标', () => {
  const s0 = E.createSession(G, ['C', 'T', 'D']);
  assert.strictEqual(E.nextQuestion(G, s0), 'T');
  const s1 = E.applyAnswer(G, s0, 'T', 'correct');
  assert.strictEqual(E.nextQuestion(G, s1), null);
  assert.deepStrictEqual(E.summarize(G, s1).path, []);
});

test('多目标：互不相关的目标都会被问到', () => {
  const s0 = E.createSession(G, ['T', 'Z']);
  const [, asked] = run(s0, { T: 'correct', Z: 'correct' });
  assert.deepStrictEqual(sorted(asked), ['T', 'Z']);
});

test('直接作答的判定不会被推断覆盖', () => {
  let s = E.createSession(G, ['T']);
  s = E.applyAnswer(G, s, 'E', 'wrong');
  s = E.applyAnswer(G, s, 'T', 'correct');
  assert.strictEqual(E.statusOf(s, 'E'), 'weak');
  assert.strictEqual(E.statusOf(s, 'C'), 'mastered');
});

test('applyAnswer 不修改入参；replay 与逐步作答一致', () => {
  const s0 = E.createSession(G, ['T']);
  const snap = JSON.stringify(s0);
  const s1 = E.applyAnswer(G, s0, 'T', 'wrong');
  assert.strictEqual(JSON.stringify(s0), snap);
  const s2 = E.applyAnswer(G, s1, 'C', 'correct');
  const r = E.replay(G, ['T'], [{ id: 'T', result: 'wrong' }, { id: 'C', result: 'correct' }]);
  assert.deepStrictEqual(r, s2);
  assert.deepStrictEqual(JSON.parse(JSON.stringify(s2)), s2); // 可序列化
  assert.throws(() => E.applyAnswer(G, s0, 'T', 'maybe'));
  assert.throws(() => E.createSession(G, ['nope']));
});

test('路径图布局：先修在上层，边不跨回', () => {
  const [s] = run(E.createSession(G, ['T']), { T: 'wrong', C: 'wrong', E: 'wrong', F: 'correct', D: 'wrong', B: 'correct' });
  const sum = E.summarize(G, s);
  const lay = E.layout(G, s, sum);
  const layer = Object.fromEntries(lay.nodes.map((n) => [n.id, n.layer]));
  lay.edges.forEach((e) => assert.ok(layer[e.from] < layer[e.to], e.from + '->' + e.to));
  assert.ok(lay.nodes.some((n) => n.id === 'T' && n.isTarget));
  assert.ok(lay.nodes.some((n) => n.id === 'E' && n.isRoot));
});


/* ------------------------------------------------------------ 两题判定（手造题库） */
console.log('两题判定');

const DIFFS = { b: 'basic', s: 'standard', a: 'advanced' };
function mq(topicId, n, diff, extra) {
  return Object.assign({
    id: topicId + '_q' + n, topicId: topicId, difficulty: DIFFS[diff] || diff, type: 'numeric',
    prompt: topicId + ' 第 ' + n + ' 题', answer: '1', explanation: '解析'
  }, extra || {});
}
// T 的先修：P1(hard) <- R，P2(hard)；每个知识点 4 题：q1 标准、q2 标准、q3 基础、q4 提高
const bankTopics = ['R', 'P1', 'P2', 'T'].map((id) => mk(id, { diagnostic_question: undefined }));
const bankDeps = [
  { topicId: 'P1', prerequisiteId: 'R', strength: 'hard' },
  { topicId: 'T', prerequisiteId: 'P1', strength: 'hard' },
  { topicId: 'T', prerequisiteId: 'P2', strength: 'hard' }
];
const bankQs = [];
['R', 'P1', 'P2', 'T'].forEach((id) => {
  bankQs.push(mq(id, 1, 's'), mq(id, 2, 's'), mq(id, 3, 'b'), mq(id, 4, 'a'));
});
const G2 = E.buildGraph(bankTopics, bankDeps, bankQs);

/** 按脚本作答：script[id] = [第一题结果, 第二题结果]；返回 [会话, 出过的 (知识点#第几题) 序列]。 */
function run2(session, script) {
  const seq = [];
  let s = session;
  for (let guard = 0; guard < 100; guard++) {
    const it = E.nextItem(G2, s);
    if (!it) break;
    seq.push(it.topicId + '#' + it.attempt);
    const r = script[it.topicId][it.attempt - 1];
    assert.ok(r, '脚本缺少 ' + it.topicId + ' 第 ' + it.attempt + ' 题');
    s = E.applyAnswer(G2, s, it.topicId, r);
  }
  return [s, seq];
}

test('题库：isTestable 看题库；有题库时 hasBank 为 true，回退模式为 false', () => {
  assert.strictEqual(G2.hasBank, true);
  assert.strictEqual(G.hasBank, false);
  assert.strictEqual(G2.bank.T.length, 4);
  assert.strictEqual(G.bank.T[0].type, 'legacy');
});

test('第一题答对 → 掌握，并推断祖先掌握；只问 1 题', () => {
  const [s, seq] = run2(E.createSession(G2, ['T']), { T: ['correct'] });
  assert.deepStrictEqual(seq, ['T#1']);
  ['T', 'P1', 'P2', 'R'].forEach((id) => assert.strictEqual(E.statusOf(s, id), 'mastered', id));
  assert.strictEqual(s.status.T.src, 'direct');
  assert.strictEqual(s.status.R.src, 'inferred');
});

test('第一题错 → 再出第二题（同一知识点），此时还没有结论、不回溯', () => {
  let s = E.createSession(G2, ['T']);
  s = E.applyAnswer(G2, s, 'T', 'wrong');
  assert.strictEqual(E.nextQuestion(G2, s), 'T');
  const it = E.nextItem(G2, s);
  assert.strictEqual(it.attempt, 2);
  assert.notStrictEqual(it.question.id, s.answers[0].qid);
  assert.strictEqual(s.status.T, undefined);
  assert.strictEqual(E.isUnconfirmed(s, 'T'), true);
});

test('错 + 错 → 薄弱，并向先修回溯（P1、P2 依次，再深入 R）', () => {
  const [s, seq] = run2(E.createSession(G2, ['T']), {
    T: ['wrong', 'skip'], P1: ['wrong', 'wrong'], R: ['correct'], P2: ['correct']
  });
  assert.deepStrictEqual(seq, ['T#1', 'T#2', 'P1#1', 'P1#2', 'R#1', 'P2#1']);
  assert.strictEqual(E.statusOf(s, 'T'), 'weak');
  assert.strictEqual(E.statusOf(s, 'P1'), 'weak');
  assert.strictEqual(E.statusOf(s, 'R'), 'mastered');
  const sum = E.summarize(G2, s);
  assert.deepStrictEqual(sum.roots.map((r) => r.id), ['P1']);
  assert.deepStrictEqual(sum.shaky, []);
});

test('错 + 对 → 不稳（shaky），且不向先修回溯', () => {
  const [s, seq] = run2(E.createSession(G2, ['T']), { T: ['wrong', 'correct'] });
  assert.deepStrictEqual(seq, ['T#1', 'T#2']);
  assert.strictEqual(E.statusOf(s, 'T'), 'shaky');
  assert.strictEqual(E.nextQuestion(G2, s), null);
  ['P1', 'P2', 'R'].forEach((id) => assert.strictEqual(E.statusOf(s, id), 'unknown', id));
  const sum = E.summarize(G2, s);
  assert.deepStrictEqual(sum.shaky, ['T']);
  assert.deepStrictEqual(sum.weak, []);
  assert.deepStrictEqual(sum.roots, []);
  assert.deepStrictEqual(sorted(sum.untested), ['P1', 'P2', 'R']);
  // 不稳的点要进学习路径
  assert.deepStrictEqual(sum.path.map((p) => [p.id, p.status]), [['T', 'shaky']]);
});

test('不稳的先修若同时被别处判为薄弱，路径含它及其后代', () => {
  const [s] = run2(E.createSession(G2, ['T']), {
    T: ['wrong', 'wrong'], P1: ['wrong', 'correct'], P2: ['wrong', 'wrong'], R: ['correct']
  });
  assert.strictEqual(E.statusOf(s, 'P1'), 'shaky');
  assert.strictEqual(E.statusOf(s, 'P2'), 'weak');
  const sum = E.summarize(G2, s);
  assert.deepStrictEqual(sum.roots.map((r) => r.id), ['P2']);
  assert.deepStrictEqual(sorted(sum.path.map((p) => p.id)), ['P1', 'P2', 'T']);
  assert.strictEqual(sum.path.find((p) => p.id === 'P1').status, 'shaky');
  assertTopological(sum.path.map((p) => p.id), G2);
});

test('第二题优先 basic；第一题已是 basic 时取同难度，没有就取最容易的剩余题', () => {
  const firstDiffs = new Set();
  for (let i = 0; i < 60; i++) {
    const s1 = E.applyAnswer(G2, E.createSession(G2, ['P2'], { seed: 'k' + i }), 'P2', 'wrong');
    const first = E.questionById(G2, s1.answers[0].qid);
    firstDiffs.add(first.difficulty);
    assert.notStrictEqual(first.difficulty, 'advanced', '有非 advanced 题时第一题不出 advanced');
    const second = E.nextItem(G2, s1).question;
    if (first.difficulty === 'standard') assert.strictEqual(second.id, 'P2_q3', '第二题应是唯一的 basic');
    else assert.strictEqual(second.difficulty, 'standard', '第一题是 basic 时没有别的 basic，取同级以上最容易的');
  }
  assert.ok(firstDiffs.has('standard') && firstDiffs.has('basic'), '随机应能抽到不同难度');
  // 没有 basic 时取同难度：标准×3 + 提高×1
  const topics3 = [mk('M', { diagnostic_question: undefined })];
  const qs3 = [mq('M', 1, 's'), mq('M', 2, 's'), mq('M', 3, 's'), mq('M', 4, 'a')];
  const G3 = E.buildGraph(topics3, [], qs3);
  for (let i = 0; i < 20; i++) {
    const s1 = E.applyAnswer(G3, E.createSession(G3, ['M'], { seed: i }), 'M', 'wrong');
    assert.strictEqual(E.nextItem(G3, s1).question.difficulty, 'standard');
  }
  // 第一题是 standard 且存在更容易的非 basic 题不可能（只有 3 档）；提高题只在没有其它选择时才出
  const qs4 = [mq('M', 1, 'a'), mq('M', 2, 'a')];
  const G4 = E.buildGraph(topics3, [], qs4);
  const s4 = E.applyAnswer(G4, E.createSession(G4, ['M'], { seed: 1 }), 'M', 'wrong');
  assert.strictEqual(E.nextItem(G4, s4).question.difficulty, 'advanced');
});

test('种子固定时选题确定；不同种子能得到不同选题', () => {
  const trace = (seed) => {
    const [s] = run2(E.createSession(G2, ['T'], { seed: seed }), {
      T: ['wrong', 'wrong'], P1: ['wrong', 'wrong'], R: ['wrong', 'wrong'], P2: ['wrong', 'wrong']
    });
    return s.answers.map((a) => a.qid).join(',');
  };
  assert.strictEqual(trace('abc'), trace('abc'));
  assert.strictEqual(trace(42), trace('42'));
  const variants = new Set();
  for (let i = 0; i < 40; i++) variants.add(trace('s' + i));
  assert.ok(variants.size > 5, '不同种子应产生不同的题目序列（得到 ' + variants.size + ' 种）');
  // 重放与逐步作答一致，题号也一致
  const [s2] = run2(E.createSession(G2, ['T'], { seed: 9 }), { T: ['wrong', 'correct'] });
  const r = E.replay(G2, ['T'], s2.answers, { seed: 9 });
  assert.deepStrictEqual(r, s2);
});

test('已出题避让：优先出没出过的题，全出过也不会卡住', () => {
  const avoid = ['T_q1', 'T_q2'];
  for (let i = 0; i < 40; i++) {
    const s0 = E.createSession(G2, ['T'], { seed: i, avoid: avoid });
    const first = E.nextItem(G2, s0).question;
    assert.ok(!avoid.includes(first.id), '第一题应避开出过的题：' + first.id);
  }
  const all = G2.bank.T.map((q) => q.id);
  const s1 = E.createSession(G2, ['T'], { seed: 1, avoid: all });
  const it = E.nextItem(G2, s1);
  assert.ok(it && all.includes(it.question.id));
  // 第二题：basic 优先于“没出过”——q3 是唯一 basic，即使它出过也还是 q3
  let hit = 0;
  for (let i = 0; i < 40; i++) {
    const s0 = E.createSession(G2, ['T'], { seed: i, avoid: ['T_q3'] });
    const a1 = E.nextItem(G2, s0).question;
    if (a1.difficulty !== 'standard') continue;
    const s2 = E.applyAnswer(G2, s0, 'T', 'wrong');
    assert.strictEqual(E.nextItem(G2, s2).question.id, 'T_q3');
    hit++;
  }
  assert.ok(hit > 5);
  // 同一次会话里不会重复出同一道题
  const [s3] = run2(E.createSession(G2, ['T']), { T: ['wrong', 'wrong'], P1: ['wrong', 'wrong'], P2: ['wrong', 'wrong'], R: ['wrong', 'wrong'] });
  const qids = s3.answers.map((a) => a.qid);
  assert.strictEqual(new Set(qids).size, qids.length);
});

test('题量上限按“题”计：2 题一个知识点；只答错第一题就到上限 → 暂按薄弱，标为未复测', () => {
  const [s, seq] = run2(E.createSession(G2, ['T'], { limit: 3 }), {
    T: ['wrong', 'wrong'], P1: ['wrong', 'wrong'], R: ['wrong', 'wrong'], P2: ['wrong', 'wrong']
  });
  assert.deepStrictEqual(seq, ['T#1', 'T#2', 'P1#1']);
  assert.strictEqual(s.answers.length, 3);
  assert.strictEqual(E.nextQuestion(G2, s), null);
  assert.strictEqual(E.statusOf(s, 'P1'), 'weak');
  const sum = E.summarize(G2, s);
  assert.deepStrictEqual(sum.unconfirmed, ['P1']);
  assert.strictEqual(sum.limitReached, true);
  assert.deepStrictEqual(sorted(sum.untested), ['P2', 'R']);
});

test('同一知识点只有一道题时：答错直接薄弱（无第二题）', () => {
  const G5 = E.buildGraph(bankTopics, bankDeps, [mq('T', 1, 's'), mq('P1', 1, 's'), mq('P2', 1, 's'), mq('R', 1, 's')]);
  let s = E.applyAnswer(G5, E.createSession(G5, ['T']), 'T', 'wrong');
  assert.strictEqual(E.statusOf(s, 'T'), 'weak');
  assert.strictEqual(E.nextQuestion(G5, s), 'P1');
});

test('applyAnswer 不修改入参（含 attempts）；答题记录带 qid 与用户答案', () => {
  const s0 = E.createSession(G2, ['T'], { seed: 5 });
  const snap = JSON.stringify(s0);
  const s1 = E.applyAnswer(G2, s0, 'T', 'wrong', { text: '42' });
  assert.strictEqual(JSON.stringify(s0), snap);
  assert.strictEqual(s1.answers[0].text, '42');
  assert.ok(/^T_q\d$/.test(s1.answers[0].qid));
  const snap1 = JSON.stringify(s1);
  E.applyAnswer(G2, s1, 'T', 'correct');
  assert.strictEqual(JSON.stringify(s1), snap1);
  assert.deepStrictEqual(JSON.parse(JSON.stringify(s1)), s1);
});

test('判题（按题型）：choice 比字母，也接受选项文字；numeric 数值等价；short 精确匹配 + accept；self 自评', () => {
  const ch = { type: 'choice', answer: 'B', choices: [{ key: 'A', text: '1/2' }, { key: 'B', text: '-3' }, { key: 'C', text: '相切' }] };
  const j = (q, u) => E.judgeQuestion(q, u).verdict;
  assert.strictEqual(j(ch, 'B'), 'correct');
  assert.strictEqual(j(ch, ' b '), 'correct');
  assert.strictEqual(j(ch, '(B)'), 'correct');
  assert.strictEqual(j(ch, 'B.'), 'correct');
  assert.strictEqual(j(ch, 'A'), 'wrong');
  assert.strictEqual(j(ch, '-3'), 'correct');
  assert.strictEqual(j(ch, '－３'), 'correct');
  assert.strictEqual(j(ch, '1/2'), 'wrong');
  assert.strictEqual(j(ch, '相切'), 'wrong');
  assert.strictEqual(j(ch, 'E'), 'manual');
  assert.strictEqual(j(ch, '随便写'), 'manual');
  assert.strictEqual(j(ch, ''), 'manual');
  const num = { type: 'numeric', answer: '-1/2' };
  assert.strictEqual(j(num, '-0.5'), 'correct');
  assert.strictEqual(j(num, '－１/２'), 'correct');
  assert.strictEqual(j(num, '1/2'), 'wrong');
  const ord = { type: 'numeric', answer: '3，-2' };
  assert.strictEqual(j(ord, '3，-2'), 'correct');
  assert.strictEqual(j(ord, '3, -2'), 'correct');
  assert.strictEqual(j(ord, '-2，3'), 'wrong');       // 有序：顺序错
  assert.strictEqual(j(ord, '3'), 'wrong');
  const unord = { type: 'numeric', answer: '3，-2', unordered: true };
  assert.strictEqual(j(unord, '-2，3'), 'correct');
  assert.strictEqual(j(unord, '-2 和 3'), 'correct');
  assert.strictEqual(j(unord, '-2，4'), 'wrong');
  const sh = { type: 'short', answer: 'y=2x+1', accept: ['2x+1', 'f(x)=2x+1'] };
  assert.strictEqual(j(sh, 'y = 2x + 1'), 'correct');
  assert.strictEqual(j(sh, 'Y＝2X+1'), 'correct');
  assert.strictEqual(j(sh, 'f(x)=2x+1'), 'correct');
  assert.strictEqual(j(sh, 'y=1+2x'), 'manual');       // 等价写法无法可靠判断，交给自评
  const quad = { type: 'short', answer: '第三象限' };
  assert.strictEqual(j(quad, '第三象限'), 'correct');
  assert.strictEqual(j(quad, '第二象限'), 'manual');
  assert.strictEqual(j({ type: 'self', answer: '略' }, '略'), 'manual');
  assert.strictEqual(j({ type: 'legacy', answer: '3' }, '3.0'), 'correct');
});

test('PRNG：mulberry32 相同种子相同序列，输出在 [0,1)', () => {
  const a = E.mulberry32(123), b = E.mulberry32(123);
  for (let i = 0; i < 100; i++) { const x = a(); assert.strictEqual(x, b()); assert.ok(x >= 0 && x < 1); }
});

/* ------------------------------------------------------------ 答案规范化与判题 */
console.log('答案规范化与判题');

function verdict(user, ref) { return E.judgeAnswer(user, ref).verdict; }

test('规范化：全角转半角、去空格、中文标点、度', () => {
  assert.strictEqual(E.normalizeText('　１／２ '), '1/2');
  assert.strictEqual(E.normalizeText('90 度'), '90°');
  assert.strictEqual(E.normalizeText('－３，（２）'), '-3,(2)');
  assert.strictEqual(E.normalizeText('x²'), 'x^2');
  assert.strictEqual(E.normalizeText('A、B；C'), 'a,b;c');
  assert.strictEqual(E.normalizeText('答：60°。'), '60°');
});

test('分数与小数等价："１/２" vs "0.5"', () => {
  assert.strictEqual(verdict('１/２', '0.5'), 'correct');
  assert.strictEqual(verdict('0.5', '1/2'), 'correct');
  assert.strictEqual(verdict('2/4', '1/2'), 'correct');
  assert.strictEqual(verdict('-1/2', '-0.5'), 'correct');
  assert.strictEqual(verdict('－１／２', '-(1/2)'), 'correct');
  assert.strictEqual(verdict('1/3', '0.333'), 'wrong');
  assert.strictEqual(verdict('1又1/2', '3/2'), 'correct');
  assert.strictEqual(verdict('1 1/2', '1.5'), 'correct');
  assert.strictEqual(verdict('50%', '1/2'), 'correct');
  assert.strictEqual(verdict('3/5', '3/5'), 'correct');
  assert.strictEqual(verdict('3/5', '5/3'), 'wrong');
});

test('角度："90 度" vs "90°"', () => {
  assert.strictEqual(verdict('90 度', '90°'), 'correct');
  assert.strictEqual(verdict('90', '90°'), 'correct');
  assert.strictEqual(verdict('６０°', '60度'), 'correct');
  assert.strictEqual(verdict('50°', '60°'), 'wrong');
});

test('多个答案顺序无关："-3 和 -1/2" vs "-1/2，-3"', () => {
  assert.strictEqual(verdict('-3 和 -1/2', '-1/2，-3'), 'correct');
  assert.strictEqual(verdict('-1/2、-3', '-3 和 -1/2'), 'correct');
  assert.strictEqual(verdict('-3', '-3 和 -1/2'), 'wrong');
  assert.strictEqual(verdict('-3，-1/2，0', '-3 和 -1/2'), 'wrong');
  assert.strictEqual(verdict('x=3 或 x=2', 'x=2 或 x=3'), 'correct');
  assert.strictEqual(verdict('2,3', 'x=2 或 x=3'), 'correct');
  assert.strictEqual(verdict('3；3', '3；3'), 'correct');
});

test('带变量名的答案：x=… 可省略变量名，但 x、y 不能互换', () => {
  assert.strictEqual(verdict('3', 'x=3'), 'correct');
  assert.strictEqual(verdict('x=3', '3'), 'manual'); // 参考答案没有变量契约时不能猜测 x
  assert.strictEqual(verdict('y=2，x=3', 'x=3，y=2'), 'correct');
  assert.strictEqual(verdict('3，2', 'x=3，y=2'), 'correct');
  assert.strictEqual(verdict('x=2，y=3', 'x=3，y=2'), 'wrong');
  assert.strictEqual(verdict('2，3', 'x=3，y=2'), 'wrong');
});

test('单位：别名等价，缺省单位放行，不同单位判错', () => {
  assert.strictEqual(verdict('12米', '12 m'), 'correct');
  assert.strictEqual(verdict('12', '12 m'), 'correct');
  assert.strictEqual(verdict('12 cm', '12 m'), 'wrong');
  assert.strictEqual(verdict('25 平方米', '25 m²'), 'correct');
  assert.strictEqual(verdict('1,000', '1000'), 'correct');
});

test('坐标等有括号的多值答案', () => {
  assert.strictEqual(verdict('（１，２）', '(1,2)'), 'correct');
  assert.strictEqual(verdict('(1, 2)', '(1,2)'), 'correct');
  assert.strictEqual(verdict('(2,1)', '(1,2)'), 'wrong');
  assert.strictEqual(verdict('(0.5,2)', '(1/2,2)'), 'correct');
});

test('无法可靠解析的答案（文字、代数式）：只在完全相同时判对，否则交给用户自评', () => {
  assert.strictEqual(verdict('相切', '相切'), 'correct');
  assert.strictEqual(verdict('相离', '相切'), 'manual');
  assert.strictEqual(verdict('y=2x+3', 'y=2x+3'), 'correct');
  assert.strictEqual(verdict('2x+3', 'y=2x+3'), 'correct');
  assert.strictEqual(verdict('y=3x+2', 'y=2x+3'), 'manual');
  assert.strictEqual(verdict('(x-2)^2-1', 'y=(x-2)²-1'), 'correct');
  assert.strictEqual(verdict('共 11 种', '共 11 种，每种有 6 个正方形'), 'manual');
  assert.strictEqual(verdict('', '3'), 'manual');
  assert.strictEqual(verdict('不知道', '3'), 'manual');
});

test('判题不抛异常：奇怪输入', () => {
  ['', ' ', '(', ')))', '1/0', '/', '--1', '1/2/3', '％', '😀', null, undefined, '１２３４５６７８９０１２３４５６７８９０/３'].forEach((u) => {
    ['3', '1/2', '相切', 'x=2 或 x=3', '', '(1,2)'].forEach((r) => {
      const v = E.judgeAnswer(u, r).verdict;
      assert.ok(['correct', 'wrong', 'manual'].includes(v));
    });
  });
});

/* ------------------------------------------------------------ 真实数据 */
console.log('真实数据');

const dataDir = path.join(__dirname, '..', 'data');
const topics = JSON.parse(fs.readFileSync(path.join(dataDir, 'topics.json'), 'utf8'));
const deps = JSON.parse(fs.readFileSync(path.join(dataDir, 'dependencies.json'), 'utf8'));
const stdFile = JSON.parse(fs.readFileSync(path.join(dataDir, 'cn-curriculum-standards.json'), 'utf8'));
const RG = E.buildGraph(topics, deps);
const formal = topics.filter((t) => !t.external);

function bfsAncestors(id) {
  const pre = new Map();
  deps.forEach((d) => { (pre.get(d.topicId) || pre.set(d.topicId, []).get(d.topicId)).push(d.prerequisiteId); });
  const seen = new Set();
  const q = [id];
  while (q.length) { (pre.get(q.shift()) || []).forEach((p) => { if (!seen.has(p)) { seen.add(p); q.push(p); } }); }
  return seen;
}

test('数据可加载：小学 216 + 初中 315，没有外部节点；课标含第一学段', () => {
  assert.strictEqual(topics.length, 531);
  assert.strictEqual(deps.length, 909);
  assert.strictEqual(topics.filter((t) => t.external).length, 0);
  assert.strictEqual(topics.filter((t) => t.grade <= 6).length, 216);
  assert.strictEqual(topics.filter((t) => t.grade >= 7).length, 315);
  assert.ok(formal.every((t) => E.isTestable(RG, t.id)));
  assert.ok(stdFile.items.length > 200);
  assert.ok(stdFile.items[0].id.indexOf('cms-2022:1.') === 0);
});

test('真实数据：祖先集合与独立 BFS 一致（全部知识点）', () => {
  topics.forEach((t) => {
    assert.deepStrictEqual(sorted(E.ancestors(RG, t.id)), sorted(bfsAncestors(t.id)), t.id);
  });
});

test('真实数据：先修子图不含外部节点，初中目标能回到小学，拓扑序合法', () => {
  let sawPrimary = false;
  formal.forEach((t) => {
    const sub = E.subgraph(RG, [t.id]);
    assert.strictEqual(sub.nodes[sub.nodes.length - 1], t.id);
    assertTopological(sub.nodes, RG);
    assert.ok(sub.nodes.every((id) => !RG.byId[id].external));
    if (t.grade >= 7 && sub.nodes.some((id) => RG.byId[id].grade <= 6)) sawPrimary = true;
  });
  assert.ok(sawPrimary, '至少有一个初中知识点的祖先里有小学知识点');
});

test('旧 id 别名：cnm_ext_* 已不在图中，resolveTargets 跳到小学正式知识点', () => {
  const aliases = JSON.parse(fs.readFileSync(path.join(dataDir, 'id-aliases.json'), 'utf8')).aliases;
  assert.strictEqual(Object.keys(aliases).length, 18);
  for (let i = 1; i <= 18; i++) {
    const key = 'cnm_ext_' + String(i).padStart(3, '0');
    assert.ok(!RG.byId[key], key + ' 不应再作为知识点');
    assert.ok(aliases[key] && aliases[key].name && aliases[key].targets.length);
    const ids = E.resolveTargets([key], aliases);
    assert.ok(ids.length >= 1 && ids.length === new Set(ids).size, key);
    ids.forEach((id) => {
      const t = RG.byId[id];
      assert.ok(t && t.grade <= 6 && !t.external, key + ' -> ' + id);
    });
    const s = E.createSession(RG, ids, { limit: 2 });
    assert.ok(ids.indexOf(E.nextQuestion(RG, s)) >= 0, key);
  }
  const mixed = E.resolveTargets(['cnm_ext_002', 'cnm_001'], aliases);
  assert.ok(mixed.indexOf('cnm_001') >= 0);
  assert.ok(mixed.some((id) => RG.byId[id].grade <= 6));
  assert.deepStrictEqual(E.resolveTargets(['nope'], aliases), ['nope']);
  assert.deepStrictEqual(E.resolveTargets(['cnm_221'], null), ['cnm_221']);
});

test('真实数据：cnm_221（配方法）——首问目标；答错后 hard 先修在前', () => {
  let s = E.createSession(RG, ['cnm_221']);
  assert.strictEqual(E.nextQuestion(RG, s), 'cnm_221');
  s = E.applyAnswer(RG, s, 'cnm_221', 'wrong');
  const prereqs = RG.prereqs.cnm_221;
  const firstHard = prereqs.find((p) => p.strength === 'hard').id;
  assert.strictEqual(E.nextQuestion(RG, s), firstHard);
});

test('真实数据：答对目标即跳过全部祖先', () => {
  const s = E.applyAnswer(RG, E.createSession(RG, ['cnm_221']), 'cnm_221', 'correct');
  assert.strictEqual(E.nextQuestion(RG, s), null);
  const anc = bfsAncestors('cnm_221');
  assert.ok(anc.size > 30);
  anc.forEach((id) => assert.strictEqual(E.statusOf(s, id), 'mastered', id));
});

// 简单可复现的伪随机数
function rng(seed) { let x = seed >>> 0; return () => { x = (Math.imul(x, 1664525) + 1013904223) >>> 0; return x / 4294967296; }; }

/** 一致的“学生”：已掌握集合对祖先封闭。 */
function makeStudent(rand, p) {
  const known = new Set();
  topics.forEach((t) => {
    if (rand() < p) { known.add(t.id); bfsAncestorsCached(t.id).forEach((a) => known.add(a)); }
  });
  return known;
}
const ancCache = new Map();
function bfsAncestorsCached(id) { if (!ancCache.has(id)) ancCache.set(id, bfsAncestors(id)); return ancCache.get(id); }

function simulate(targets, known, limit) {
  let s = E.createSession(RG, targets, { limit: limit });
  const asked = [];
  for (let guard = 0; guard < 500; guard++) {
    const q = E.nextQuestion(RG, s);
    if (!q) break;
    asked.push(q);
    s = E.applyAnswer(RG, s, q, known.has(q) ? 'correct' : 'wrong');
  }
  return { s: s, asked: asked };
}

test('真实数据：一致的学生 + 无限题量 => 薄弱集合与根因精确还原', () => {
  const rand = rng(20261017);
  let cases = 0;
  for (let round = 0; round < 3; round++) {
    const known = makeStudent(rand, [0.04, 0.12, 0.3][round]);
    formal.forEach((t) => {
      const { s, asked } = simulate([t.id], known, 9999);
      cases++;
      assert.strictEqual(new Set(asked).size, asked.length, '不应重复出题 ' + t.id);
      assert.ok(asked.every((id) => !RG.byId[id].external));
      const sum = E.summarize(RG, s);
      const sub = E.subgraph(RG, [t.id]);
      const unknown = sub.nodes.filter((id) => E.isTestable(RG, id) && !known.has(id));
      assert.deepStrictEqual(sorted(sum.weak), sorted(unknown), '薄弱集合 ' + t.id);
      sum.mastered.forEach((id) => assert.ok(known.has(id), id + ' 被判掌握但学生不会'));
      const expectRoots = unknown.filter((id) => RG.prereqs[id].every((p) => !unknown.includes(p.id)));
      assert.deepStrictEqual(sorted(sum.roots.map((r) => r.id)), sorted(expectRoots), '根因 ' + t.id);
      // 路径：拓扑序、不含已掌握、覆盖所有薄弱点、含全部根因
      const pathIds = sum.path.map((p) => p.id);
      assertTopological(pathIds, RG);
      sum.path.forEach((p) => assert.notStrictEqual(p.status, 'mastered'));
      sum.weak.forEach((id) => assert.ok(pathIds.includes(id), '薄弱点应在路径中 ' + id));
      sum.roots.forEach((r) => assert.ok(pathIds.includes(r.id)));
      if (unknown.length) assert.strictEqual(pathIds[pathIds.length - 1], t.id);
      // 要么全对（1 题），要么 hard/soft 回溯
      if (known.has(t.id)) assert.strictEqual(asked.length, 1);
      assert.strictEqual(sum.finished, true);
      assert.strictEqual(sum.limitReached, false);
    });
  }
  assert.ok(cases >= 900);
});

test('真实数据：题量上限（8/12/20）永远不被突破，且仍满足根因/路径定义', () => {
  const rand = rng(7);
  [8, 12, 20].forEach((limit) => {
    const known = makeStudent(rand, 0.02);
    let capped = 0;
    formal.forEach((t) => {
      const { s, asked } = simulate([t.id], known, limit);
      assert.ok(asked.length <= limit);
      if (asked.length === limit) capped++;
      const sum = E.summarize(RG, s);
      assert.strictEqual(sum.asked, asked.length);
      sum.roots.forEach((r) => {
        assert.strictEqual(E.statusOf(s, r.id), 'weak');
        RG.prereqs[r.id].forEach((p) => assert.notStrictEqual(E.statusOf(s, p.id), 'weak'));
      });
      const pathIds = sum.path.map((p) => p.id);
      assertTopological(pathIds, RG);
      sum.path.forEach((p) => assert.notStrictEqual(p.status, 'mastered'));
      if (sum.limitReached) assert.ok(sum.untested.length > 0);
      const all = new Set(sum.mastered.concat(sum.weak, sum.untested));
      assert.strictEqual(all.size, s.order.length);
    });
    if (limit === 8) assert.ok(capped > 0, '应有触发上限的目标');
  });
});

test('真实数据：什么都不会的学生，在上限处停下，未测节点被标出', () => {
  const none = new Set();
  const { s, asked } = simulate(['cnm_221'], none, 12);
  assert.strictEqual(asked.length, 12);
  const sum = E.summarize(RG, s);
  assert.strictEqual(sum.limitReached, true);
  assert.ok(sum.untested.length > 0);
  assert.ok(sum.roots.length >= 1);
});

test('真实数据：整章作为目标——会的学生只需问“最末端”的目标', () => {
  const chapter = formal.filter((t) => t.chapter.startsWith('七上 第一章 '));
  const ids = chapter.map((t) => t.id);
  assert.ok(ids.length >= 5);
  const known = new Set(topics.map((t) => t.id));
  const { s, asked } = simulate(ids, known, 12);
  const idSet = new Set(ids);
  const maximal = ids.filter((id) => !ids.some((o) => o !== id && bfsAncestorsCached(o).has(id) && idSet.has(o)));
  assert.strictEqual(asked.length, maximal.length);
  ids.forEach((id) => assert.strictEqual(E.statusOf(s, id), 'mastered'));
  // 什么都不会：每个目标都会被问到或被标未测，不会漏
  const r = simulate(ids, new Set(), 20);
  const sum = E.summarize(RG, r.s);
  ids.forEach((id) => assert.ok(sum.weak.includes(id) || sum.untested.includes(id), id));
});

test('真实数据：replay 与 JSON 往返得到相同会话', () => {
  const known = makeStudent(rng(3), 0.1);
  const { s } = simulate(['cnm_232'], known, 12);
  const r = E.replay(RG, ['cnm_232'], s.answers, { limit: 12 });
  assert.deepStrictEqual(r, s);
  assert.deepStrictEqual(E.replay(RG, JSON.parse(JSON.stringify(s.targets)), JSON.parse(JSON.stringify(s.answers)), { limit: 12 }), s);
});

test('真实数据：路径图布局——所有边方向一致，节点不丢', () => {
  const { s } = simulate(['cnm_232'], new Set(), 12);
  const sum = E.summarize(RG, s);
  const lay = E.layout(RG, s, sum);
  const layer = Object.fromEntries(lay.nodes.map((n) => [n.id, n.layer]));
  lay.edges.forEach((e) => assert.ok(layer[e.from] < layer[e.to]));
  sum.path.forEach((p) => assert.ok(layer[p.id] !== undefined));
  assert.ok(layer.cnm_232 === lay.layers - 1);
});

test('真实数据：诊断题答案能被自己的判题器接受（判对率检查）', () => {
  let bad = [];
  formal.forEach((t) => {
    const a = t.diagnostic_question.answer;
    if (E.judgeAnswer(a, a).verdict !== 'correct') bad.push(t.id);
  });
  assert.deepStrictEqual(bad, []);
});

test('真实数据：章节名可解析', () => {
  formal.forEach((t) => {
    const c = E.parseChapter(t.chapter);
    assert.ok(c.volume && c.chapterNo && c.chapterName, t.chapter);
  });
});

/* ------------------------------------------------------------ 题库数据（data/questions.json） */
console.log('题库数据');

const questions = JSON.parse(fs.readFileSync(path.join(dataDir, 'questions.json'), 'utf8'));
const RGQ = E.buildGraph(topics, deps, questions);
const qByTopic = {};
questions.forEach((q) => { (qByTopic[q.topicId] = qByTopic[q.topicId] || []).push(q); });
const NUM_RE = /^-?\d+(\.\d+)?(\/\d+(\.\d+)?)?$/;

test('题库：每个正式知识点至少 3 题；id 唯一且格式正确；外部节点无题；含 basic 与 standard', () => {
  const ids = new Set();
  questions.forEach((q) => {
    assert.ok(!ids.has(q.id), '重复 id ' + q.id);
    ids.add(q.id);
    assert.ok(new RegExp('^' + q.topicId + '_q[1-9]\\d*$').test(q.id), q.id);
    assert.ok(RG.byId[q.topicId] && !RG.byId[q.topicId].external, q.id + ' 的 topicId 无效');
  });
  formal.forEach((t) => {
    const qs = qByTopic[t.id] || [];
    assert.ok(qs.length >= 3, t.id + ' 只有 ' + qs.length + ' 题');
    const ds = new Set(qs.map((q) => q.difficulty));
    assert.ok(ds.has('basic') && ds.has('standard'), t.id + ' 缺少 basic 或 standard');
    assert.ok(qs.some((q) => q.id === t.id + '_q1'), t.id + ' 缺 q1');
    assert.ok(qs.filter((q) => q.id !== t.id + '_q1').some((q) => q.difficulty === 'basic'), t.id + ' 除 q1 外没有 basic');
  });
});

test('题库：type / difficulty 合法；必填字段非空；numeric + choice 占 60% 以上', () => {
  let auto = 0;
  questions.forEach((q) => {
    assert.ok(['numeric', 'choice', 'short', 'self'].includes(q.type), q.id);
    assert.ok(['basic', 'standard', 'advanced'].includes(q.difficulty), q.id);
    ['prompt', 'answer', 'explanation'].forEach((f) => assert.ok(typeof q[f] === 'string' && q[f].trim(), q.id + ' ' + f));
    if (q.type === 'numeric' || q.type === 'choice') auto++;
  });
  assert.ok(auto / questions.length >= 0.6, 'numeric+choice 占比 ' + (auto / questions.length));
});

test('题库：choice 题有 3–4 个选项、key 不重复、answer 是某个选项的 key', () => {
  let n = 0;
  questions.filter((q) => q.type === 'choice').forEach((q) => {
    n++;
    assert.ok(Array.isArray(q.choices) && q.choices.length >= 3 && q.choices.length <= 4, q.id);
    const keys = q.choices.map((c) => c.key);
    assert.strictEqual(new Set(keys).size, keys.length, q.id + ' key 重复');
    assert.ok(keys.includes(q.answer), q.id + ' answer 不在选项里');
    assert.strictEqual(new Set(q.choices.map((c) => c.text.trim())).size, keys.length, q.id + ' 选项文字重复');
  });
  assert.ok(n > 100);
});

test('题库：numeric 题的 answer 能被解析为数（整数/小数/分数/负数，多个答案用「，」分隔）', () => {
  let n = 0;
  questions.filter((q) => q.type === 'numeric').forEach((q) => {
    n++;
    const parts = q.answer.split(/[，,]/).map((x) => x.replace(/\s/g, ''));
    parts.forEach((x) => assert.ok(NUM_RE.test(x), q.id + ' answer=' + q.answer));
    if (q.unordered) assert.ok(parts.length > 1, q.id + ' unordered 但只有一个答案');
  });
  assert.ok(n > 500);
});

test('题库：q1 由 diagnostic_question 迁移（题干以原题开头，或标注了 fixed_from_source）', () => {
  formal.forEach((t) => {
    const q1 = qByTopic[t.id].find((q) => q.id === t.id + '_q1');
    assert.ok(q1.prompt.startsWith(t.diagnostic_question.question) || q1.fixed_from_source, t.id);
  });
});

test('题库：判题器接受每道题自己的参考答案（self 一律自评）', () => {
  const bad = [];
  questions.forEach((q) => {
    const v = E.judgeQuestion(q, q.type === 'choice' ? q.answer : q.answer).verdict;
    const want = q.type === 'self' ? 'manual' : 'correct';
    if (v !== want) bad.push(q.id + ':' + v);
    if (q.type === 'choice') {
      const text = q.choices.find((c) => c.key === q.answer).text;
      // 选项文字本身是单个字母（如 x、D）时和选项字母无法区分，按字母处理；界面里选择题是点选项，不受影响
      if (!/^[A-Za-z]$/.test(text.trim()) && E.judgeQuestion(q, text).verdict !== 'correct') bad.push(q.id + ':text');
      q.choices.filter((c) => c.key !== q.answer).forEach((c) => {
        if (E.judgeQuestion(q, c.key).verdict !== 'wrong') bad.push(q.id + ':wrong-' + c.key);
      });
    }
    if (q.type === 'numeric' && !q.unordered && E.judgeQuestion(q, '999999').verdict === 'correct') bad.push(q.id + ':999999');
  });
  assert.deepStrictEqual(bad.slice(0, 20), []);
});

test('带题库的图：每个正式知识点可测、外部节点不可测；hasBank 为 true', () => {
  assert.strictEqual(RGQ.hasBank, true);
  assert.ok(formal.every((t) => E.isTestable(RGQ, t.id)));
  assert.ok(topics.filter((t) => t.external).every((t) => !E.isTestable(RGQ, t.id)));
});

console.log('带题库的真实诊断');

/** 学生：known 一次答对；flaky 第一题错第二题对；其余两题都错 */
function simulateBank(targets, known, flaky, limit, seed) {
  let s = E.createSession(RGQ, targets, { limit: limit, seed: seed == null ? 'sim' : seed });
  const asked = [];
  for (let guard = 0; guard < 2000; guard++) {
    const it = E.nextItem(RGQ, s);
    if (!it) break;
    asked.push(it.topicId + '#' + it.attempt);
    let r = 'wrong';
    if (known.has(it.topicId)) r = 'correct';
    else if (flaky.has(it.topicId)) r = it.attempt === 1 ? 'wrong' : 'correct';
    s = E.applyAnswer(RGQ, s, it.topicId, r);
  }
  return { s: s, asked: asked };
}

test('小学回溯：答错初中「正数与负数」会问到小学，学习路径按年级从低到高', () => {
  const { s, asked } = simulateBank(['cnm_001'], new Set(), new Set(), 80, 'primary');
  const ids = asked.map((x) => x.split('#')[0]);
  assert.ok(ids.indexOf('cnm_001') >= 0);
  assert.ok(ids.filter((id) => id === 'cnm_001').length <= 2);
  assert.ok(ids.some((id) => RGQ.byId[id].grade === 6), '应问到六年级');
  assert.ok(ids.some((id) => RGQ.byId[id].grade === 1), '应继续问到一年级');
  const per = {};
  ids.forEach((id) => { per[id] = (per[id] || 0) + 1; });
  Object.keys(per).forEach((id) => assert.ok(per[id] <= 2, id + ' 超过 2 题'));
  const sum = E.summarize(RGQ, s);
  const ranks = sum.path.map((p) => E.gradeRank(RGQ, p.id));
  for (let i = 1; i < ranks.length; i++) {
    assert.ok(ranks[i] >= ranks[i - 1], '路径应按年级从低到高：' + sum.path[i - 1].id + ' -> ' + sum.path[i].id);
  }
  assert.ok(sum.path.some((p) => RGQ.byId[p.id].grade <= 6));
  assert.strictEqual(sum.path[sum.path.length - 1].id, 'cnm_001');
  assertTopological(sum.path.map((p) => p.id), RGQ);
});

test('带题库：一致的学生 + 无限题量 => 薄弱集合与根因精确还原；会的 1 题、不会的 2 题', () => {
  const rand = rng(20261018);
  let cases = 0;
  for (let round = 0; round < 3; round++) {
    const known = makeStudent(rand, [0.04, 0.12, 0.3][round]);
    formal.forEach((t) => {
      const { s, asked } = simulateBank([t.id], known, new Set(), 9999);
      cases++;
      const sum = E.summarize(RGQ, s);
      const sub = E.subgraph(RGQ, [t.id]);
      const unknown = sub.nodes.filter((id) => E.isTestable(RGQ, id) && !known.has(id));
      assert.deepStrictEqual(sorted(sum.weak), sorted(unknown), '薄弱集合 ' + t.id);
      assert.deepStrictEqual(sum.shaky, []);
      assert.deepStrictEqual(sum.unconfirmed, []);
      sum.mastered.forEach((id) => assert.ok(known.has(id), id + ' 被判掌握但学生不会'));
      const expectRoots = unknown.filter((id) => RGQ.prereqs[id].every((p) => !unknown.includes(p.id)));
      assert.deepStrictEqual(sorted(sum.roots.map((r) => r.id)), sorted(expectRoots), '根因 ' + t.id);
      const perTopic = {};
      asked.forEach((a) => { const id = a.split('#')[0]; perTopic[id] = (perTopic[id] || 0) + 1; });
      Object.keys(perTopic).forEach((id) => assert.strictEqual(perTopic[id], known.has(id) ? 1 : 2, id));
      const pathIds = sum.path.map((p) => p.id);
      assertTopological(pathIds, RGQ);
      sum.weak.forEach((id) => assert.ok(pathIds.includes(id), '薄弱点应在路径中 ' + id));
      assert.strictEqual(sum.finished, true);
    });
  }
  assert.ok(cases >= 900);
});

test('带题库：任何一个知识点“第一题错、第二题对” => 不稳、只问 2 题、不回溯先修、进学习路径', () => {
  let withPrereq = 0;
  formal.forEach((t) => {
    const { s, asked } = simulateBank([t.id], new Set(), new Set([t.id]), 9999);
    assert.deepStrictEqual(asked, [t.id + '#1', t.id + '#2'], t.id);
    assert.strictEqual(E.statusOf(s, t.id), 'shaky');
    const sum = E.summarize(RGQ, s);
    assert.deepStrictEqual(sum.shaky, [t.id]);
    assert.deepStrictEqual(sum.weak, []);
    assert.deepStrictEqual(sum.roots, []);
    assert.deepStrictEqual(sum.path.map((p) => p.id), [t.id]);
    assert.strictEqual(sum.path[0].status, 'shaky');
    if (RGQ.prereqs[t.id].length) withPrereq++;
  });
  assert.ok(withPrereq > 200);
});

test('带题库：混合学生（会 / 不稳 / 不会）——每个点最多 2 题，记录的状态与学生一致', () => {
  const rand = rng(99);
  const known = makeStudent(rand, 0.1);
  const flaky = new Set(topics.filter((t) => !t.external && !known.has(t.id) && rand() < 0.3).map((t) => t.id));
  formal.forEach((t) => {
    const { s, asked } = simulateBank([t.id], known, flaky, 9999);
    const cnt = {};
    asked.forEach((a) => { const id = a.split('#')[0]; cnt[id] = (cnt[id] || 0) + 1; });
    Object.keys(cnt).forEach((id) => assert.ok(cnt[id] <= 2, id));
    Object.keys(s.status).forEach((id) => {
      const st = s.status[id];
      if (st.src !== 'direct') { assert.strictEqual(st.s, 'mastered'); return; }
      const want = known.has(id) ? 'mastered' : flaky.has(id) ? 'shaky' : 'weak';
      assert.strictEqual(st.s, want, id);
    });
    const sum = E.summarize(RGQ, s);
    sum.shaky.forEach((id) => assert.ok(sum.path.some((p) => p.id === id), '不稳的点应在路径里 ' + id));
    const all = new Set(sum.mastered.concat(sum.shaky, sum.weak, sum.untested));
    assert.strictEqual(all.size, s.order.length);
    assert.strictEqual(sum.mastered.length + sum.shaky.length + sum.weak.length + sum.untested.length, s.order.length);
  });
});

test('带题库：题量上限（8/16/30）按题计、永不突破；未复测的点标出', () => {
  const rand = rng(11);
  [8, 16, 30].forEach((limit) => {
    const known = makeStudent(rand, 0.02);
    let capped = 0;
    formal.forEach((t) => {
      const { s, asked } = simulateBank([t.id], known, new Set(), limit);
      assert.ok(asked.length <= limit, t.id);
      if (asked.length === limit) capped++;
      const sum = E.summarize(RGQ, s);
      assert.strictEqual(sum.asked, asked.length);
      sum.unconfirmed.forEach((id) => assert.ok(sum.weak.includes(id)));
      const all = new Set(sum.mastered.concat(sum.shaky, sum.weak, sum.untested));
      assert.strictEqual(all.size, s.order.length);
    });
    if (limit === 8) assert.ok(capped > 0, '应有触发上限的目标');
  });
});

test('带题库：种子固定 => 整个诊断的出题序列确定；换种子序列会变；重放一致', () => {
  const known = new Set(); // 什么都不会：两题都错，序列最长，选题的随机性最明显
  const a = simulateBank(['cnm_232'], known, new Set(), 16, 'fixed');
  const b = simulateBank(['cnm_232'], known, new Set(), 16, 'fixed');
  assert.deepStrictEqual(a.s.answers.map((x) => x.qid), b.s.answers.map((x) => x.qid));
  const qs = new Set();
  for (let i = 0; i < 30; i++) qs.add(simulateBank(['cnm_232'], known, new Set(), 16, 'seed' + i).s.answers.map((x) => x.qid).join());
  assert.ok(qs.size > 3);
  const r = E.replay(RGQ, ['cnm_232'], a.s.answers, { limit: 16, seed: 'fixed' });
  assert.deepStrictEqual(r, a.s);
});

test('带题库：重测时避开已出过的题（avoid 里的题尽量不再出）', () => {
  const known = makeStudent(rng(8), 0.1);
  const first = simulateBank(['cnm_232'], known, new Set(), 16, 'one');
  const seen = first.s.answers.map((x) => x.qid);
  let s = E.createSession(RGQ, ['cnm_232'], { limit: 16, seed: 'two', avoid: seen });
  let repeats = 0, total = 0;
  for (let guard = 0; guard < 100; guard++) {
    const it = E.nextItem(RGQ, s);
    if (!it) break;
    total++;
    if (it.attempt === 1 && seen.includes(it.question.id)) {
      // 只有当该知识点的非 advanced 题全都出过时才可能重复
      const fresh = RGQ.bank[it.topicId].filter((q) => !seen.includes(q.id) && q.difficulty !== 'advanced');
      assert.strictEqual(fresh.length, 0, it.topicId + ' 还有没出过的题却重复了');
      repeats++;
    }
    s = E.applyAnswer(RGQ, s, it.topicId, known.has(it.topicId) ? 'correct' : 'wrong');
  }
  assert.ok(total > 0);
});

/* ------------------------------------------------------------ 更正 / 存档与单位回归 */
console.log('更正、存档与单位回归');

test('真实更正：第一题改对后丢弃第二题与不再需要的先修记录，不覆盖已掌握状态', () => {
  let s = E.createSession(RGQ, ['cnm_221'], { seed: 'review' });
  for (const result of ['wrong', 'wrong', 'correct']) {
    const item = E.nextItem(RGQ, s);
    s = E.applyAnswer(RGQ, s, item.topicId, result, { text: '原始输入' });
  }
  const original = JSON.stringify(s);
  const corrected = s.answers.map((a, i) => i === 0 ? { ...a, result: 'correct' } : a);
  const replayed = E.replayWithReport(RGQ, s.targets, corrected, { seed: s.seed, limit: s.limit });
  assert.strictEqual(E.statusOf(replayed.session, 'cnm_221'), 'mastered');
  assert.strictEqual(E.nextItem(RGQ, replayed.session), null);
  assert.deepStrictEqual(replayed.session.answers, [corrected[0]]);
  assert.deepStrictEqual(replayed.dropped.map(x => x.index), [1, 2]);
  assert.strictEqual(JSON.stringify(s), original, '不能改写原会话或题号');
});

test('更正第二题为对：保留两道原题，不再重放先修作答', () => {
  const [s] = run2(E.createSession(G2, ['T'], { seed: 5 }), {
    T: ['wrong', 'wrong'], P1: ['correct'], P2: ['correct']
  });
  const corrected = s.answers.map((a, i) => i === 1 ? { ...a, result: 'correct' } : a);
  const { session: result, dropped } = E.replayWithReport(G2, s.targets, corrected, { seed: s.seed });
  assert.deepStrictEqual(result.answers, corrected.slice(0, 2));
  assert.strictEqual(E.statusOf(result, 'T'), 'shaky');
  assert.strictEqual(E.nextItem(G2, result), null);
  assert.strictEqual(dropped.length, s.answers.length - 2);
});

test('更正一个分支只删除失效记录，其他仍符合新流程的分支记录保留', () => {
  const [s] = run2(E.createSession(G2, ['T'], { seed: 8 }), {
    T: ['wrong', 'wrong'], P1: ['wrong', 'wrong'], R: ['correct'], P2: ['correct']
  });
  const corrected = s.answers.map((a, i) => i === 2 ? { ...a, result: 'correct' } : a);
  const { session: result, dropped } = E.replayWithReport(G2, s.targets, corrected, { seed: s.seed });
  assert.deepStrictEqual(result.answers, [corrected[0], corrected[1], corrected[2], corrected[5]]);
  assert.deepStrictEqual(dropped.map(x => x.index), [3, 4]);
  assert.strictEqual(E.statusOf(result, 'P1'), 'mastered');
  assert.strictEqual(E.statusOf(result, 'R'), 'mastered');
  assert.strictEqual(E.statusOf(result, 'P2'), 'mastered');
});

test('重放已有 qid 时不按新随机选择替换题目；缺 qid 的旧存档仍可恢复', () => {
  const [s] = run2(E.createSession(G2, ['T'], { seed: 9 }), { T: ['wrong', 'correct'] });
  const newSeed = Array.from({ length: 30 }, (_, i) => 'changed-' + i).find(seed =>
    E.nextItem(G2, E.createSession(G2, ['T'], { seed })).question.id !== s.answers[0].qid);
  assert.ok(newSeed, '回归需要确实改变下一道随机题');
  const report = E.replayWithReport(G2, ['T'], s.answers, { seed: newSeed });
  assert.deepStrictEqual(report.session.answers, s.answers);
  assert.deepStrictEqual(report.dropped, []);
  const legacy = s.answers.map(({ qid, ...record }) => record);
  assert.deepStrictEqual(E.replay(G2, ['T'], legacy, { seed: s.seed }), s);
});

test('已删除的历史题、重复题号和超过新上限的记录不会被重新分配到其他题', () => {
  const s = E.createSession(G2, ['T']);
  const first = E.nextItem(G2, s).question.id;
  const removed = E.replayWithReport(G2, ['T'], [
    { id: 'T', qid: 'T_q999', result: 'wrong' },
    { id: 'T', qid: first, result: 'correct' }
  ]);
  assert.strictEqual(removed.session.answers.length, 0);
  assert.deepStrictEqual(removed.dropped.map(x => x.reason), ['missing-question', 'after-invalid-record']);
  const repeated = E.replayWithReport(G2, ['T'], [
    { id: 'T', qid: first, result: 'wrong' },
    { id: 'T', qid: first, result: 'wrong' }
  ]);
  assert.strictEqual(repeated.session.answers.length, 1);
  assert.strictEqual(repeated.dropped[0].reason, 'duplicate-question');
  const [full] = run2(s, { T: ['wrong', 'wrong'], P1: ['correct'], P2: ['correct'] });
  const capped = E.replayWithReport(G2, ['T'], full.answers, { limit: 1 });
  assert.strictEqual(capped.session.answers.length, 1);
  assert.strictEqual(capped.dropped.length, full.answers.length - 1);
  assert.throws(() => E.applyAnswer(G2, s, 'T', 'correct', { qid: 'R_q1' }));
});

test('真实换算题：确认的厘米 / 角单位可省略，写对别名可判对，错误单位不能判对', () => {
  const length = questions.find(q => q.id === 'cnm_p041_q2');
  const money = questions.find(q => q.id === 'cnm_p036_q2');
  assert.strictEqual(length.unit, '厘米');
  assert.strictEqual(money.unit, '角');
  for (const answer of ['200', '200厘米', '200 cm', '２００ｃｍ'])
    assert.strictEqual(E.judgeQuestion(length, answer).verdict, 'correct', answer);
  for (const answer of ['200米', '200千克'])
    assert.strictEqual(E.judgeQuestion(length, answer).verdict, 'wrong', answer);
  for (const answer of ['30', '30角'])
    assert.strictEqual(E.judgeQuestion(money, answer).verdict, 'correct', answer);
  assert.strictEqual(E.judgeQuestion(money, '30元').verdict, 'wrong');
});

test('没有期望单位时带单位输入转人工，不能用正确数字掩盖错误量纲', () => {
  const unannotated = questions.find(q => q.id === 'cnm_p040_q2');
  for (const answer of ['40毫米', '40米', '40千克', '4厘米'])
    assert.strictEqual(E.judgeQuestion(unannotated, answer).verdict, 'manual', answer);
  assert.strictEqual(E.judgeQuestion(unannotated, '40').verdict, 'correct');
  assert.strictEqual(E.judgeQuestion({ type: 'numeric', answer: '200' }, '200米').verdict, 'manual');
  assert.strictEqual(E.judgeAnswer('(1米,2)', '(1,2)').verdict, 'manual');
  assert.strictEqual(E.judgeAnswer('(1米,2)', '(1厘米,2)').verdict, 'wrong');
  assert.strictEqual(E.judgeAnswer('5朵', '5').verdict, 'manual');
});

test('单位修复保留分数 / 百分数 / 负数 / 多值和已有单位别名的正确数值判定', () => {
  for (const [answer, expected] of [['1/4', 'correct'], ['25%', 'correct'], ['0.25', 'correct'], ['75%', 'wrong']])
    assert.strictEqual(E.judgeQuestion({ type: 'numeric', answer: '1/4' }, answer).verdict, expected, answer);
  assert.strictEqual(E.judgeQuestion({ type: 'numeric', answer: '-3/2' }, '-1又1/2').verdict, 'correct');
  assert.strictEqual(E.judgeQuestion({ type: 'numeric', answer: '1/2，2', unordered: true }, '2，50%').verdict, 'correct');
  assert.strictEqual(E.judgeQuestion({ type: 'numeric', answer: '1/2', unit: '厘米' }, '0.5 cm').verdict, 'correct');
  assert.strictEqual(E.judgeQuestion({ type: 'numeric', answer: '1/2', unit: '厘米' }, '0.5 kg').verdict, 'wrong');
  assert.strictEqual(E.judgeQuestion({ type: 'numeric', answer: '1/2', unit: '厘米' }, '0.5朵').verdict, 'manual');
  assert.strictEqual(E.judgeAnswer('12米', '12 m').verdict, 'correct');
  assert.strictEqual(E.judgeAnswer('12', '12 m').verdict, 'correct');
  assert.strictEqual(E.judgeAnswer('12 cm', '12 m').verdict, 'wrong');
});

/* ------------------------------------------------------------ 深入判题准确性回归 */
console.log('深入判题准确性回归');

test('真实多答案不与千分位混淆，错误的连写数字不能判对', () => {
  for (const [id, collapsed] of [['cnm_059_q1', '40130'], ['cnm_295_q1', '90120']]) {
    const q = questions.find(question => question.id === id);
    assert.strictEqual(E.judgeQuestion(q, q.answer).verdict, 'correct', id);
    assert.strictEqual(E.judgeQuestion(q, q.answer.replace(/，/g, ',')).verdict, 'correct', id);
    assert.strictEqual(E.judgeQuestion(q, collapsed).verdict, 'wrong', id);
    assert.strictEqual(E.judgeQuestion(q, q.answer.split('，').reverse().join(',')).verdict, 'wrong', id);
  }
  assert.strictEqual(E.judgeQuestion({ type: 'numeric', answer: '1，234' }, '1234').verdict, 'wrong');
  assert.strictEqual(E.judgeQuestion({ type: 'numeric', answer: '1，234' }, '1,234').verdict, 'correct');
});

test('只有明确单个数值才识别规范千分位，并保留分数 / 百分数的精确等值', () => {
  for (const [input, answer] of [['1,000', '1000'], ['1,000,000', '1000000'], ['1,000/2', '500'],
    ['1,000%', '10'], ['25%', '1/4'], ['５０％', '0.5'], ['-1又1/2', '-3/2']]) {
    assert.strictEqual(E.judgeQuestion({ type: 'numeric', answer }, input).verdict, 'correct', input);
  }
  for (const [input, answer] of [['1/0', '0'], ['0/0', '0'], ['25%%', '0.25'], ['1/2/3', '1/6']]) {
    assert.notStrictEqual(E.judgeQuestion({ type: 'numeric', answer }, input).verdict, 'correct', input);
  }
  assert.strictEqual(E.judgeQuestion({ type: 'numeric', answer: '0.333' }, '1/3').verdict, 'wrong');
});

test('全部明确变量契约支持正确标签重排，拒绝错标签和重复替代标签', () => {
  const annotated = questions.filter(question => question.variables);
  assert.ok(annotated.length >= 32);
  for (const q of annotated) {
    const values = q.answer.split(/[，,]/);
    const labelled = q.variables.map((name, index) => name + '=' + values[index]);
    const wrongName = ['w', 'v', 'z'].find(name => !q.variables.includes(name));
    const wrongLabel = labelled.slice(); wrongLabel[0] = wrongName + '=' + values[0];
    assert.strictEqual(E.judgeQuestion(q, labelled.join(',')).verdict, 'correct', q.id + ' labels');
    assert.strictEqual(E.judgeQuestion(q, labelled.slice().reverse().join(',')).verdict, 'correct', q.id + ' reordered');
    assert.strictEqual(E.judgeQuestion(q, wrongLabel.join(',')).verdict, 'wrong', q.id + ' wrong label');
    if (q.variables.length > 1) {
      const duplicated = labelled.slice(); duplicated[1] = q.variables[0] + '=' + values[1];
      assert.strictEqual(E.judgeQuestion(q, duplicated.join(',')).verdict, 'wrong', q.id + ' duplicate label');
    }
  }
  const q = questions.find(question => question.id === 'cnm_089_q2');
  assert.strictEqual(E.judgeQuestion(q, 'y=3,x=2').verdict, 'wrong');
  assert.strictEqual(E.judgeQuestion(q, 'x=3,x=2').verdict, 'wrong');
  assert.strictEqual(E.judgeQuestion(q, 'y=2,x=3').verdict, 'correct');
});

test('没有变量契约时不猜测标签；已有明确标签的参考答案严格绑定变量', () => {
  assert.strictEqual(E.judgeQuestion({ type: 'numeric', answer: '3' }, 'x=3').verdict, 'manual');
  assert.strictEqual(E.judgeQuestion({ type: 'numeric', answer: '3,2' }, 'y=3,x=2').verdict, 'manual');
  assert.strictEqual(E.judgeAnswer('z=3', 'x=3').verdict, 'wrong');
  assert.strictEqual(E.judgeAnswer('x=2,x=3', 'y=2,y=3').verdict, 'wrong');
  assert.strictEqual(E.judgeAnswer('x=3,x=2', 'x=2,x=3').verdict, 'correct');
  assert.strictEqual(E.judgeAnswer('y=2,x=3', 'x=3,y=2').verdict, 'correct');
  assert.strictEqual(E.judgeAnswer('3', 'x=3').verdict, 'correct');
  const labelled = { type: 'numeric', answer: '3，2', variables: ['x', 'y'] };
  for (const variables of [[], ['x'], ['x', 'x'], null, ['x', 2]])
    assert.strictEqual(E.judgeQuestion({ ...labelled, variables }, '3,2').verdict, 'manual');
  assert.strictEqual(E.judgeQuestion({ ...labelled, unordered: true }, '3,2').verdict, 'manual');
});

test('阶乘、重复小数点和数字间空白不会被吞掉后判对', () => {
  for (const [input, answer] of [['3!', '3'], ['3!!', '3'], ['3..', '3'], ['3...', '3'], ['1 2', '12'], ['1\n2', '12']])
    assert.notStrictEqual(E.judgeQuestion({ type: 'numeric', answer }, input).verdict, 'correct', input);
  assert.strictEqual(E.judgeQuestion({ type: 'numeric', answer: '1.5' }, '1 1/2').verdict, 'correct');
  assert.strictEqual(E.judgeQuestion({ type: 'numeric', answer: '3' }, '答：３。').verdict, 'correct');
});

test('空答案项、错误坐标括号和非法度数后缀不被丢弃后判对', () => {
  for (const input of ['1,,2', ',1,2', '1,2,', '1;;2', '(1,,2)', '[1,2)', '{1,2}'])
    assert.notStrictEqual(E.judgeAnswer(input, '(1,2)').verdict, 'correct', input);
  assert.notStrictEqual(E.judgeAnswer('1,,2', '1,2').verdict, 'correct');
  assert.notStrictEqual(E.judgeAnswer('1;', '1').verdict, 'correct');
  assert.strictEqual(E.judgeAnswer('（１，２）', '(1,2)').verdict, 'correct');
  assert.strictEqual(E.judgeAnswer('(0.5,2)', '(1/2,2)').verdict, 'correct');
  assert.strictEqual(E.judgeAnswer('(2,1)', '(1,2)').verdict, 'wrong');
  assert.strictEqual(E.judgeAnswer('(1,2)', '1,2').verdict, 'manual');
  assert.notStrictEqual(E.judgeAnswer('90°米', '90°').verdict, 'correct');
  assert.notStrictEqual(E.judgeAnswer('90°角', '90°').verdict, 'correct');
  assert.strictEqual(E.judgeAnswer('90度', '90°').verdict, 'correct');
});

test('short文字列表与坐标序列保持题目次序，不能靠集合重排自动判对', () => {
  const axes = questions.find(question => question.id === 'cnm_202_q1');
  const probability = questions.find(question => question.id === 'cnm_307_q1');
  assert.strictEqual(E.judgeQuestion(axes, '(0.0,4.0),(2.0,0.0)').verdict, 'correct');
  assert.strictEqual(E.judgeQuestion(axes, '(2,0),(0,4)').verdict, 'manual');
  assert.strictEqual(E.judgeQuestion(probability, '红球，白球，黄球').verdict, 'correct');
  assert.strictEqual(E.judgeQuestion(probability, '黄球，白球，红球').verdict, 'manual');
  assert.strictEqual(E.judgeQuestion({ type: 'short', answer: '甲，乙' }, '乙，甲').verdict, 'manual');
  assert.strictEqual(E.judgeAnswer('乙，甲', '甲，乙').verdict, 'manual');
});

test('choice全库正确文字与全角key可识别，文字/key歧义仍按有效key优先', () => {
  let checked = 0, collisions = 0;
  for (const q of questions.filter(question => question.type === 'choice')) {
    const text = q.choices.find(choice => choice.key === q.answer).text;
    const keyMatch = /^[(（]?([a-z])[)）.．、:：]?$/.exec(E.normalizeText(text));
    if (keyMatch && q.choices.some(choice => choice.key === keyMatch[1].toUpperCase())) {
      collisions++;
      assert.strictEqual(E.judgeQuestion(q, text).verdict, keyMatch[1].toUpperCase() === q.answer ? 'correct' : 'wrong', q.id);
    } else { checked++; assert.strictEqual(E.judgeQuestion(q, text).verdict, 'correct', q.id + ' text'); }
    for (const choice of q.choices) {
      const fullwidth = String.fromCharCode(choice.key.charCodeAt(0) + 0xFEE0);
      assert.strictEqual(E.judgeQuestion(q, fullwidth).verdict, choice.key === q.answer ? 'correct' : 'wrong', q.id + ' ' + fullwidth);
    }
  }
  assert.ok(checked > 600);
  assert.ok(collisions > 0);
  assert.strictEqual(E.judgeQuestion(questions.find(q => q.id === 'cnm_162_q1'), 'x').verdict, 'correct');
  assert.strictEqual(E.judgeQuestion(questions.find(q => q.id === 'cnm_194_q3'), 't').verdict, 'correct');
  const ambiguous = { type: 'choice', answer: 'A', choices: [{ key: 'A', text: '相切' }, { key: 'B', text: '相切。' }, { key: 'C', text: '相离' }] };
  assert.strictEqual(E.judgeQuestion(ambiguous, '相切').verdict, 'manual');
});

test('单位多重集合优先完整的确定匹配，不能因贪心次序把正确答案判错', () => {
  assert.strictEqual(E.judgeAnswer('1,1cm', '1cm,1m').verdict, 'correct');
  assert.strictEqual(E.judgeAnswer('1朵,1cm', '1cm,1m').verdict, 'manual');
  assert.strictEqual(E.judgeAnswer('1kg,1cm', '1cm,1m').verdict, 'wrong');
  assert.strictEqual(E.judgeQuestion({ type: 'numeric', answer: '1，2', accept: ['3，4'] }, '3.0,4.0').verdict, 'correct');
});

test('显式按顺序的真实题拒绝答案倒置', () => {
  for (const [id, right, wrong] of [['cnm_001_q1', '-3,-1/2', '-1/2,-3'], ['cnm_115_q5', '20,80', '80,20']]) {
    const q = questions.find(question => question.id === id);
    assert.strictEqual(q.unordered, undefined, id);
    assert.strictEqual(E.judgeQuestion(q, right).verdict, 'correct', id);
    assert.strictEqual(E.judgeQuestion(q, wrong).verdict, 'wrong', id);
  }
});

test('非法作答结果不会利用对象原型属性混入存档', () => {
  const session = E.createSession(G2, ['T']);
  for (const result of ['constructor', '__proto__', 'toString']) {
    assert.throws(() => E.applyAnswer(G2, session, 'T', result));
    const replayed = E.replayWithReport(G2, ['T'], [{ id: 'T', result }]);
    assert.strictEqual(replayed.session.answers.length, 0);
    assert.strictEqual(replayed.dropped[0].reason, 'invalid-record');
  }
});

test('超长输入与超量答案项安全交给自评，不参与大整数或组合匹配', () => {
  assert.deepStrictEqual(E.judgeQuestion({ type: 'numeric', answer: '3' }, ''), { verdict: 'manual', reason: 'empty' });
  assert.strictEqual(E.judgeQuestion({ type: 'numeric', answer: '3' }, '3'.repeat(5000)).verdict, 'manual');
  assert.strictEqual(E.judgeQuestion({ type: 'numeric', answer: '3' }, Array(70).fill('3').join(',')).verdict, 'manual');
  assert.strictEqual(E.judgeQuestion({ type: 'short', answer: '略' }, '略'.repeat(5000)).verdict, 'manual');
});

test('所有Unicode上标保留幂语义，不把指数变成普通数字或多个幂', () => {
  const byId = new Map(JSON.parse(fs.readFileSync(path.join(__dirname, '../data/questions.json'), 'utf8')).map(q => [q.id, q]));
  for (const [id, right, unsafe] of [
    ['cnm_142_q1', 'x^7', 'x7'],
    ['cnm_143_q1', 'a^6 与 8b^3', 'a6 与 8b^3'],
    ['cnm_144_q1', '-6a^3b^4', '-6a^3b4'],
    ['cnm_163_q1', 'x^5', 'x5'],
    ['cnm_164_q1', '1/8；3.2×10^-4', '1/8；3.2×10-4'],
  ]) {
    assert.strictEqual(E.judgeQuestion(byId.get(id), right).verdict, 'correct', id);
    assert.notStrictEqual(E.judgeQuestion(byId.get(id), unsafe).verdict, 'correct', id);
  }
  assert.strictEqual(E.normalizeText('x¹²'), 'x^12');
  assert.strictEqual(E.normalizeText('x²⁴'), 'x^24');
});

console.log('\n' + passed + ' passed, ' + failed + ' failed');
process.exit(failed ? 1 : 0);
