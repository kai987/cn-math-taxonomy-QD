'use strict';
const { test, expect } = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');
const E = require('../../diagnose/engine.js');
const root = path.resolve(__dirname, '../..');
const read = name => JSON.parse(fs.readFileSync(path.join(root, 'data', name + '.json'), 'utf8'));
const questions = read('questions');
const topics = read('topics');
const graph = E.buildGraph(topics, read('dependencies'), questions);
const topicCount = topics.filter(topic => !topic.external).length;
const basePath = process.env.PLAYWRIGHT_BASE_URL ? new URL(process.env.PLAYWRIGHT_BASE_URL).pathname.replace(/\/$/, '') : '';
const siteURL = relative => basePath + relative;

function seedFor(topicId, predicate) {
  for (let index = 0; index < 200; index++) {
    const seed = 'browser-' + index;
    const item = E.nextItem(graph, E.createSession(graph, [topicId], { seed, avoid: [] }));
    if (item && predicate(item.question)) return { seed, question: item.question };
  }
  throw new Error('No deterministic question matched ' + topicId);
}
const numeric = seedFor('cnm_p001', question => question.type === 'numeric');
const choice = seedFor('cnm_221', question => question.type === 'choice');
const conversion = seedFor('cnm_p041', question => question.id === 'cnm_p041_q2');
const shortAnswer = seedFor('cnm_025', question => question.type === 'short');
const openAnswer = seedFor('cnm_003', question => question.type === 'self');
const orderedAnswers = seedFor('cnm_059', question => question.id === 'cnm_059_q1');
const variableAnswers = seedFor('cnm_089', question => question.id === 'cnm_089_q2');
const simplifiedFormula = seedFor('cnm_209', question => question.id === 'cnm_209_q1');
const waterMeaning = seedFor('cnm_028', question => question.id === 'cnm_028_q1');
const parallelDefinition = seedFor('cnm_067', question => question.id === 'cnm_067_q4');
const probabilityRange = seedFor('cnm_285', question => question.id === 'cnm_285_q2');
const suspension = seedFor('cnm_119', question => question.id === 'cnm_119_q2');
const histogramConvention = seedFor('cnm_107', question => question.id === 'cnm_107_q1');
const daylightMaximum = seedFor('cnm_109', question => question.id === 'cnm_109_q1');
const varianceInference = seedFor('cnm_306', question => question.id === 'cnm_306_q4');
const targetURL = (topic, seed) => siteURL('/diagnose/?target=' + topic + '&seed=' + seed);
const sessionKey = 'cnmDiagnose.session.v2';

test.beforeEach(async ({ page }) => {
  page.__runtimeErrors = [];
  page.__consoleErrors = [];
  page.on('pageerror', error => page.__runtimeErrors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') page.__consoleErrors.push(message.text()); });
});

test.afterEach(async ({ page }, info) => {
  expect(page.__runtimeErrors).toEqual([]);
  // Deliberate HTTP failures may log resource errors, but never JS exceptions.
  const expectedFailure = info.title.startsWith('unavailable question bank') || info.title.startsWith('stale asset paths');
  expect(page.__consoleErrors.filter(message => !expectedFailure || !message.startsWith('Failed to load resource:'))).toEqual([]);
});

async function noHorizontalOverflow(page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
}

async function activate(page, locator) {
  await locator.waitFor({ state: 'visible' });
  if (await page.evaluate(() => matchMedia('(pointer: coarse)').matches)) await locator.tap();
  else await locator.click();
}

async function savedSession(page) {
  return page.evaluate(key => JSON.parse(localStorage.getItem(key)), sessionKey);
}

async function answerCorrectly(page, item) {
  if (item.question.type === 'choice') await activate(page, page.locator('#choice-' + item.question.answer));
  else await page.locator('#ans').fill(item.question.answer);
  if (item.question.type === 'self') {
    await activate(page, page.locator('#btn-peek'));
    await activate(page, page.locator('#btn-right'));
  } else {
    await activate(page, page.locator('#btn-submit'));
    if (await page.locator('#btn-right').isVisible()) await activate(page, page.locator('#btn-right'));
    else {
      await expect(page.locator('.verdict')).toHaveText('自动判定：正确');
      await activate(page, page.locator('#btn-next'));
    }
  }
}

test('catalogue filters, touch panels and current-topic diagnosis link', async ({ page }, info) => {
  await page.goto(siteURL('/'));
  await expect(page).toHaveTitle(/中小学数学知识图谱/);
  await expect(page.locator('.topic-pick')).toHaveCount(topicCount);
  if (await page.locator('#filter-toggle').isVisible()) await page.locator('#filter-toggle').click();
  await page.locator('#fGrade').selectOption('9');
  expect(await page.locator('.topic-pick').count()).toBeLessThan(topicCount);
  await page.locator('#reset-filters').click();
  await expect(page.locator('.topic-pick')).toHaveCount(topicCount);
  await page.locator('#q').fill('配方法');
  await page.locator('[data-id="cnm_221"] button').click();
  await expect(page.locator('#main .title')).toHaveText('配方法');
  const link = page.locator('#diagnose-current');
  await expect(link).toHaveText('诊断当前知识点');
  expect(new URL(await link.getAttribute('href'), page.url()).searchParams.get('target')).toBe('cnm_221');
  await noHorizontalOverflow(page);
  await page.screenshot({ path: info.outputPath('current-topic.png') });
  await link.click();
  await expect(page).toHaveURL(/\/diagnose\/\?target=cnm_221/);
  await expect(page.locator('#q-text')).toBeVisible();
  await expect(page.locator('.q-title')).toContainText('配方法');
  await noHorizontalOverflow(page);
});

test('text answer draft survives an ordinary refresh', async ({ page }) => {
  const url = targetURL('cnm_p001', numeric.seed);
  await page.goto(url);
  await expect(page.locator('#ans')).toBeVisible();
  await page.locator('#ans').fill('123');
  await page.reload();
  await expect(page.locator('#ans')).toHaveValue('123');
  await expect(page.locator('#q-text')).toHaveText(numeric.question.prompt);
  await noHorizontalOverflow(page);
});

test('changed question content preserves the old draft for review without applying it to the new question', async ({ page }) => {
  await page.goto(targetURL('cnm_p001', numeric.seed));
  await expect(page.locator('#q-text')).toHaveText(numeric.question.prompt);
  await page.locator('#ans').fill('123');
  const updatedPrompt = numeric.question.prompt + '（题目内容已更新）';
  await page.route('**/data/questions.json*', async route => {
    const response = await route.fetch();
    const bank = await response.json();
    const question = bank.find(item => item.id === numeric.question.id);
    question.prompt = updatedPrompt;
    await route.fulfill({ response, body: JSON.stringify(bank) });
  });
  await page.reload();
  await expect(page.locator('#q-text')).toHaveText(updatedPrompt);
  await expect(page.locator('#ans')).toHaveValue('');
  await expect(page.locator('#session-notice')).toContainText('未自动填入新题');
  await page.locator('#draft-backup summary').click();
  await expect(page.locator('#draft-backup p')).toHaveText(numeric.question.prompt);
  await expect(page.locator('#draft-backup pre')).toHaveText('123');

  await page.reload();
  await expect(page.locator('#ans')).toHaveValue('');
  await expect(page.locator('#session-notice')).toBeVisible();
  await page.locator('#draft-backup summary').click();
  await expect(page.locator('#draft-backup p')).toHaveText(numeric.question.prompt);
  await expect(page.locator('#draft-backup pre')).toHaveText('123');
  await page.getByRole('button', { name: '关闭诊断提示', exact: true }).click();
  await expect(page.locator('#draft-backup')).toHaveCount(0);
  await page.reload();
  await expect(page.locator('#q-text')).toHaveText(updatedPrompt);
  await expect(page.locator('#draft-backup')).toHaveCount(0);
});

test('choice selection and feedback survive refresh without skipping a question', async ({ page }) => {
  await page.goto(targetURL('cnm_221', choice.seed));
  const correct = page.locator('#choice-' + choice.question.answer);
  await correct.click();
  await expect(correct).toHaveAttribute('aria-pressed', 'true');
  await page.reload();
  await expect(correct).toHaveAttribute('aria-pressed', 'true');
  await page.locator('#btn-submit').click();
  await expect(page.locator('.verdict')).toHaveText('自动判定：正确');
  await page.reload();
  await expect(page.locator('.verdict')).toHaveText('自动判定：正确');
  await expect(page.locator('#q-text')).toHaveText(choice.question.prompt);
  await page.locator('#btn-next').click();
  await expect(page.locator('#summary')).toBeVisible();
  await expect(page.locator('#summary')).toContainText('目标知识点已掌握');
});

test('wrong conversion unit is rejected and valid numeric answer remains accepted', async ({ page }) => {
  await page.goto(targetURL('cnm_p041', conversion.seed));
  await expect(page.locator('#q-text')).toHaveText(conversion.question.prompt);
  await page.locator('#ans').fill('200米');
  await page.locator('#btn-submit').click();
  await expect(page.locator('.verdict')).toContainText('不正确');
  await page.getByRole('button', { name: '重新作答', exact: true }).click();
  await page.locator('#ans').fill('200');
  await page.locator('#btn-submit').click();
  await expect(page.locator('.verdict')).toHaveText('自动判定：正确');
});

test('correcting the first answer recalculates the result and drops obsolete follow-ups', async ({ page }) => {
  await page.goto(siteURL('/diagnose/?target=cnm_221&demo=1'));
  await expect(page.locator('#summary')).toBeVisible();
  expect(Number(await page.locator('#summary .stat.bad b').innerText())).toBeGreaterThan(0);
  await page.locator('#log select').first().selectOption('correct');
  await expect(page.locator('#summary')).toContainText('目标知识点已掌握');
  await expect(page.locator('#summary .stat.bad b')).toHaveText('0');
  await expect(page.locator('#log tbody tr')).toHaveCount(1);
  await page.reload();
  // The demo URL is deliberately deterministic; the corrected UI itself is checked above.
  await expect(page.locator('#summary')).toBeVisible();
});

for (const failure of ['404', 'invalid-json', 'network', 'incomplete-bank', 'invalid-question-id']) {
  test('unavailable question bank ' + failure + ' blocks diagnosis and retries without clearing progress', async ({ page }) => {
    const url = targetURL('cnm_p001', numeric.seed);
    await page.goto(url);
    await page.locator('#ans').fill('123');
    const saved = await page.evaluate(key => JSON.parse(localStorage.getItem(key)), sessionKey);
    delete saved.savedAt;
    let fail = true;
    await page.route('**/data/questions.json*', async route => {
      if (!fail) return route.continue();
      if (failure === 'network') return route.abort();
      const body = failure === '404' ? '{}' : failure === 'incomplete-bank' ? JSON.stringify(questions.slice(0, 1))
        : failure === 'invalid-question-id' ? JSON.stringify(questions.map((question, index) => index ? question : { ...question, id: 'invalid-id' })) : '{broken-json';
      await route.fulfill({ status: failure === '404' ? 404 : 200, contentType: 'application/json', body });
    });
    await page.reload();
    await expect(page.locator('#question-bank-error')).toBeVisible();
    await expect(page.locator('#q-text')).toHaveCount(0);
    const retained = await page.evaluate(key => JSON.parse(localStorage.getItem(key)), sessionKey);
    delete retained.savedAt;
    expect(retained).toEqual(saved);
    fail = false;
    await page.locator('#btn-retry-data').click();
    await expect(page.locator('#ans')).toHaveValue('123');
    await expect(page.locator('#q-text')).toHaveText(numeric.question.prompt);
  });
}

test('late update checker prompts before reloading and preserves an already typed draft', async ({ page }) => {
  const latest = 'b'.repeat(40);
  let releaseChecker;
  const gate = new Promise(resolve => { releaseChecker = resolve; });
  await page.route('**/update-check.js*', async route => { await gate; await route.continue(); });
  await page.route('**/version.json?*', route => route.fulfill({ contentType: 'application/json', body: JSON.stringify({ version: latest }) }));
  await page.goto(targetURL('cnm_p001', numeric.seed) + '#draft', { waitUntil: 'commit' });
  await page.locator('#ans').fill('123');
  releaseChecker();
  await expect(page.locator('#release-update')).toBeVisible();
  await expect(page.locator('#ans')).toHaveValue('123');
  expect(new URL(page.url()).searchParams.has('_v')).toBe(false);
  await page.locator('#release-update button').click();
  await expect(page).toHaveURL(new RegExp('_v=' + latest));
  await expect(page.locator('#ans')).toHaveValue('123');
  expect(new URL(page.url()).hash).toBe('#draft');
});

test('diagnosis update detection never automatically refreshes an untouched question', async ({ page }) => {
  await page.route('**/version.json?*', route => route.fulfill({ contentType: 'application/json', body: JSON.stringify({ version: 'b'.repeat(40) }) }));
  await page.goto(targetURL('cnm_p001', numeric.seed));
  await expect(page.locator('#release-update')).toBeVisible();
  await expect(page.locator('#q-text')).toBeVisible();
  expect(new URL(page.url()).searchParams.has('_v')).toBe(false);
});

test('stale catalogue HTML reloads once to the current version and preserves the anchor', async ({ page }) => {
  const old = '0'.repeat(40);
  let altered = 0;
  await page.route('**/*', async route => {
    const request = route.request();
    if (!request.isNavigationRequest() || new URL(request.url()).searchParams.has('_v')) return route.continue();
    const response = await route.fetch();
    const html = (await response.text()).replace(/name="app-version" content="[a-f0-9]{40}"/, 'name="app-version" content="' + old + '"');
    altered++;
    await route.fulfill({ response, body: html });
  });
  await page.goto(siteURL('/?filter=retained#cnm_221'));
  await expect(page).toHaveURL(/_v=[a-f0-9]{40}/);
  await expect(page.locator('#main .title')).toHaveText('配方法');
  expect(new URL(page.url()).hash).toBe('#cnm_221');
  expect(new URL(page.url()).searchParams.get('filter')).toBe('retained');
  expect(altered).toBe(1);
});

test('production assets and JSON requests use the deployed version on refresh', async ({ page }) => {
  const requested = [];
  page.on('request', request => requested.push(new URL(request.url())));
  await page.goto(targetURL('cnm_p001', numeric.seed));
  await expect(page.locator('#q-text')).toBeVisible();
  const version = await page.locator('meta[name="app-version"]').getAttribute('content');
  await page.reload();
  await expect(page.locator('#q-text')).toBeVisible();
  const appAssets = requested.filter(url => /\/(?:app|engine)\.js$|\/style\.css$|\/data\/.+\.json$/.test(url.pathname));
  expect(appAssets.length).toBeGreaterThan(6);
  for (const url of appAssets) {
    expect(url.pathname).toContain('/assets/' + version + '/');
  }
});

test('stale asset paths offer a working update even when application files cannot load', async ({ page }) => {
  const old = '0'.repeat(40);
  let version;
  await page.route('**/*', async route => {
    const request = route.request();
    if (!request.isNavigationRequest() || new URL(request.url()).searchParams.has('_v')) return route.continue();
    const response = await route.fetch();
    const html = await response.text();
    version = html.match(/name="app-version" content="([a-f0-9]{40})"/)[1];
    await route.fulfill({ response, body: html.replaceAll(version, old) });
  });
  await page.goto(targetURL('cnm_p001', numeric.seed));
  await expect(page.locator('#release-update')).toBeVisible();
  await expect(page.locator('#q-text')).toHaveCount(0);
  expect(new URL(page.url()).searchParams.has('_v')).toBe(false);
  await page.locator('#release-update button').click();
  await expect(page).toHaveURL(new RegExp('_v=' + version));
  await expect(page.locator('#q-text')).toBeVisible();
});

test('small phone width and tablet landscape retain usable controls', async ({ page }) => {
  for (const viewport of [{ width: 320, height: 568 }, { width: 1024, height: 768 }]) {
    await page.setViewportSize(viewport);
    await page.goto(siteURL('/#cnm_221'));
    await expect(page.locator('#main .title')).toHaveText('配方法');
    await noHorizontalOverflow(page);
    await expect(page.locator('#diagnose-current')).toBeVisible();
    const smallTargets = await page.locator('#main button, #main summary, #diagnose-current').evaluateAll(elements => elements.filter(element => {
      const rect = element.getBoundingClientRect();
      return rect.width && rect.height && rect.height < 43.5;
    }).map(element => element.textContent));
    expect(smallTargets).toEqual([]);
  }
});

test('short answers support manual judgement, undo and restored feedback', async ({ page }) => {
  await page.goto(targetURL('cnm_025', shortAnswer.seed));
  await expect(page.locator('#q-text')).toHaveText(shortAnswer.question.prompt);
  await page.locator('#ans').fill(shortAnswer.question.answer);
  await activate(page, page.locator('#btn-submit'));
  await expect(page.locator('.verdict')).toHaveText('自动判定：正确');
  await activate(page, page.locator('#btn-next'));
  await expect(page.locator('#summary')).toBeVisible();
  await activate(page, page.getByRole('button', { name: '撤销上一题', exact: true }));
  await expect(page.locator('#q-text')).toHaveText(shortAnswer.question.prompt);
  await expect(page.locator('#ans')).toHaveValue('');
  await page.locator('#ans').fill('我用自己的方法作了说明');
  await activate(page, page.locator('#btn-submit'));
  await expect(page.locator('#btn-right')).toBeVisible();
  await expect(page.locator('.refans')).toContainText(shortAnswer.question.answer);
  await page.reload();
  await expect(page.locator('#btn-right')).toBeVisible();
  await activate(page, page.locator('#btn-right'));
  await expect(page.locator('#summary')).toContainText('目标知识点已掌握');
  await expect(page.locator('#log tbody tr')).toHaveCount(1);
});

test('automatic grading can be overridden in both directions and undone without losing the question', async ({ page }) => {
  await page.goto(targetURL('cnm_p001', numeric.seed));
  await page.locator('#ans').fill('999999');
  await activate(page, page.locator('#btn-submit'));
  await expect(page.locator('.verdict')).toHaveText('自动判定：不正确');
  await activate(page, page.locator('#btn-flip'));
  await expect(page.locator('#summary')).toContainText('目标知识点已掌握');
  expect((await savedSession(page)).answers[0].result).toBe('correct');
  await activate(page, page.getByRole('button', { name: '撤销上一题', exact: true }));
  await expect(page.locator('#q-text')).toHaveText(numeric.question.prompt);
  await page.locator('#ans').fill(numeric.question.answer);
  await activate(page, page.locator('#btn-submit'));
  await expect(page.locator('.verdict')).toHaveText('自动判定：正确');
  await activate(page, page.locator('#btn-flip'));
  await expect(page.locator('.question-card')).toContainText('本知识点第 2 题');
  expect((await savedSession(page)).answers[0].result).toBe('wrong');
  await activate(page, page.locator('#btn-skip'));
  await activate(page, page.locator('#btn-next'));
  await expect(page.locator('#summary .stat.bad b')).toHaveText('1');
  await page.reload();
  await expect(page.locator('#summary .stat.bad b')).toHaveText('1');
});

test('open answer drafts and self assessment survive rotation, refresh and prerequisite backtracking', async ({ page }, info) => {
  await page.goto(targetURL('cnm_003', openAnswer.seed));
  await expect(page.locator('textarea#ans')).toBeVisible();
  const draft = '先按正数、零和负数分类。\n保留这个尚未提交的解题思路。';
  await page.locator('#ans').fill(draft);
  for (const viewport of [{ width: 320, height: 568 }, { width: 844, height: 390 }, { width: 768, height: 1024 }, { width: 1024, height: 768 }]) {
    await page.setViewportSize(viewport);
    await expect(page.locator('#ans')).toHaveValue(draft);
    await noHorizontalOverflow(page);
  }
  await activate(page, page.locator('#btn-peek'));
  await expect(page.locator('.refans')).toContainText(openAnswer.question.answer);
  await page.reload();
  await expect(page.locator('#btn-wrong')).toBeVisible();
  await page.screenshot({ path: info.outputPath('open-answer-landscape.png') });
  await activate(page, page.locator('#btn-wrong'));
  await expect(page.locator('.question-card')).toContainText('本知识点第 2 题');
  await activate(page, page.locator('#btn-skip'));
  await activate(page, page.locator('#btn-next'));
  const saved = await savedSession(page);
  const replayed = E.replay(graph, saved.targets, saved.answers, { seed: saved.seed, limit: saved.limit, avoid: saved.avoid });
  expect(E.statusOf(replayed, 'cnm_003')).toBe('weak');
  const next = E.nextItem(graph, replayed);
  expect(next.topicId).not.toBe('cnm_003');
  await expect(page.locator('#q-text')).toHaveText(next.question.prompt);
  await noHorizontalOverflow(page);
});

test('a whole chapter can be completed after leaving and continuing the saved session', async ({ page }) => {
  await page.goto(siteURL('/diagnose/'));
  await page.locator('#stage').selectOption('j');
  await page.locator('#search').fill('第一章 有理数');
  await activate(page, page.getByRole('button', { name: '以整章为目标', exact: true }).first());
  await expect(page.locator('#q-text')).toBeVisible();
  const saved = await savedSession(page);
  expect(saved.targets.length).toBeGreaterThan(1);
  expect(saved.label).toContain('整章');
  let modeled = E.createSession(graph, saved.targets, { seed: saved.seed, limit: saved.limit, avoid: saved.avoid });
  let item = E.nextItem(graph, modeled);
  await answerCorrectly(page, item);
  modeled = E.applyAnswer(graph, modeled, item.topicId, 'correct');
  await activate(page, page.locator('.topbar .back'));
  await expect(page.locator('.topic-pick').first()).toBeVisible();
  await activate(page, page.locator('header .tool-link'));
  await activate(page, page.getByRole('button', { name: '继续', exact: true }));
  for (let guard = 0; (item = E.nextItem(graph, modeled)) && guard < saved.targets.length; guard++) {
    await expect(page.locator('#q-text')).toHaveText(item.question.prompt);
    await answerCorrectly(page, item);
    modeled = E.applyAnswer(graph, modeled, item.topicId, 'correct');
  }
  expect(E.nextItem(graph, modeled)).toBeNull();
  await expect(page.locator('#summary')).toContainText('整章');
  await expect(page.locator('#summary')).toContainText('目标知识点已掌握');
  await expect(page.locator('#summary .stat.ask b')).toHaveText(String(modeled.answers.length));
  await noHorizontalOverflow(page);
});

test('two wrong answers backtrack, the question limit can be extended and undo stays consistent', async ({ page }) => {
  const seed = 'browser-limit-eight';
  let modeled = E.createSession(graph, ['cnm_221'], { seed, limit: 8, avoid: [] });
  await page.goto(targetURL('cnm_221', seed) + '&limit=8');
  for (let index = 0; index < 8; index++) {
    const item = E.nextItem(graph, modeled);
    await expect(page.locator('#q-text')).toHaveText(item.question.prompt);
    if (index === 1) await expect(page.locator('.question-card')).toContainText('本知识点第 2 题');
    if (index === 2) expect(item.topicId).not.toBe('cnm_221');
    await activate(page, page.locator('#btn-skip'));
    await activate(page, page.locator('#btn-next'));
    modeled = E.applyAnswer(graph, modeled, item.topicId, 'skip');
  }
  await expect(page.locator('#summary .stat.ask b')).toHaveText('8');
  await expect(page.locator('#summary')).toContainText('已达到题量上限');
  await page.reload();
  await expect(page.locator('#summary .stat.ask b')).toHaveText('8');
  await activate(page, page.getByRole('button', { name: '再多答 4 题', exact: true }));
  await expect(page.locator('#q-text')).toBeVisible();
  expect((await savedSession(page)).limit).toBe(12);
  await activate(page, page.getByRole('button', { name: '撤销上一题', exact: true }));
  const saved = await savedSession(page);
  expect(saved.answers).toHaveLength(7);
  expect(saved.limit).toBe(12);
  const expected = E.replay(graph, saved.targets, saved.answers, { seed, limit: 12, avoid: [] });
  await expect(page.locator('#q-text')).toHaveText(E.nextItem(graph, expected).question.prompt);
  await page.reload();
  await expect(page.locator('#q-text')).toHaveText(E.nextItem(graph, expected).question.prompt);
  await noHorizontalOverflow(page);
});

test('the maximum extended question limit does not expose a dead add-more action', async ({ page }) => {
  const seed = 'browser-limit-sixty';
  let session = E.createSession(graph, ['cnm_221'], { seed, limit: 60, avoid: [] });
  for (let index = 0; index < 60; index++) {
    const item = E.nextItem(graph, session);
    expect(item).not.toBeNull();
    session = E.applyAnswer(graph, session, item.topicId, 'skip');
  }
  await page.addInitScript(({ key, saved }) => localStorage.setItem(key, JSON.stringify(saved)), {
    key: sessionKey, saved: { v: 2, targets: session.targets, limit: 60, label: '配方法', answers: session.answers, seed, avoid: [] }
  });
  await page.goto(targetURL('cnm_221', seed));
  await expect(page.locator('#summary .stat.ask b')).toHaveText('60');
  await expect(page.getByRole('button', { name: '再多答 4 题', exact: true })).toHaveCount(0);
});

test('the final one-question extension is accurately labelled and persists after refresh', async ({ page }) => {
  const seed = 'browser-limit-fifty-nine';
  let session = E.createSession(graph, ['cnm_221'], { seed, limit: 59, avoid: [] });
  for (let index = 0; index < 59; index++) {
    const item = E.nextItem(graph, session);
    expect(item).not.toBeNull();
    session = E.applyAnswer(graph, session, item.topicId, 'skip');
  }
  await page.addInitScript(({ key, saved }) => {
    if (!localStorage.getItem(key)) localStorage.setItem(key, JSON.stringify(saved));
  }, {
    key: sessionKey, saved: { v: 2, targets: session.targets, limit: 59, label: '配方法', answers: session.answers, seed, avoid: [] }
  });
  await page.goto(targetURL('cnm_221', seed));
  await expect(page.locator('#summary .stat.ask b')).toHaveText('59');
  await activate(page, page.getByRole('button', { name: '再多答 1 题', exact: true }));
  await expect(page.locator('#q-text')).toBeVisible();
  expect((await savedSession(page)).limit).toBe(60);
  await activate(page, page.locator('#btn-skip'));
  await activate(page, page.locator('#btn-next'));
  await expect(page.locator('#summary .stat.ask b')).toHaveText('60');
  await expect(page.getByRole('button', { name: /再多答/ })).toHaveCount(0);
  await page.reload();
  await expect(page.locator('#summary .stat.ask b')).toHaveText('60');
  expect((await savedSession(page)).limit).toBe(60);
});

test('ordered answers and named variables cannot be accepted after separators or names are changed', { tag: '@grading-contract' }, async ({ page }) => {
  for (const example of [
    { topic: 'cnm_059', item: orderedAnswers, incorrect: '40130', correct: '40,130' },
    { topic: 'cnm_089', item: variableAnswers, incorrect: 'y=3,x=2', correct: 'y=2,x=3' }
  ]) {
    await page.goto(targetURL(example.topic, example.item.seed));
    await expect(page.locator('#q-text')).toHaveText(example.item.question.prompt);
    await page.locator('#ans').fill(example.incorrect);
    await activate(page, page.locator('#btn-submit'));
    await expect(page.locator('.verdict')).toHaveText('自动判定：不正确');
    await activate(page, page.getByRole('button', { name: '重新作答', exact: true }));
    await page.locator('#ans').fill(example.correct);
    await activate(page, page.locator('#btn-submit'));
    await expect(page.locator('.verdict')).toHaveText('自动判定：正确');
  }
});

test('a required simplified formula keeps unfinished algebra in manual review after refresh', { tag: '@grading-contract' }, async ({ page }) => {
  await page.goto(targetURL('cnm_209', simplifiedFormula.seed));
  await expect(page.locator('#q-text')).toHaveText(simplifiedFormula.question.prompt);
  await page.locator('#ans').fill('y=10+2(x-3)');
  await activate(page, page.locator('#btn-submit'));
  await expect(page.locator('#btn-right')).toBeVisible();
  await expect(page.locator('.verdict')).toHaveCount(0);
  await page.reload();
  await expect(page.locator('#btn-wrong')).toBeVisible();
  await activate(page, page.locator('#btn-wrong'));
  await activate(page, page.getByRole('button', { name: '撤销上一题', exact: true }));
  await expect(page.locator('#q-text')).toHaveText(simplifiedFormula.question.prompt);
  await page.locator('#ans').fill('y=10+2(x-3)=2x+4');
  await activate(page, page.locator('#btn-submit'));
  await expect(page.locator('.verdict')).toHaveText('自动判定：正确');
  await page.reload();
  await expect(page.locator('.verdict')).toHaveText('自动判定：正确');
  await noHorizontalOverflow(page);
});

test('the reviewed water example retains its physical time domain and self assessment after refresh', { tag: '@grading-contract' }, async ({ page }) => {
  await page.goto(targetURL('cnm_028', waterMeaning.seed));
  await expect(page.locator('#q-text')).toHaveText(waterMeaning.question.prompt);
  await page.locator('#ans').fill('水箱原有100升，每分钟流出5升；20分钟后需停止这个模型。');
  await activate(page, page.locator('#btn-peek'));
  await expect(page.locator('.refans')).toContainText('0≤t≤20');
  await expect(page.locator('#btn-right')).toBeVisible();
  await expect(page.locator('.verdict')).toHaveCount(0);
  await page.reload();
  await expect(page.locator('.refans')).toContainText('0≤t≤20');
  await noHorizontalOverflow(page);
  await activate(page, page.locator('#btn-right'));
  await expect(page.locator('#summary')).toContainText('目标知识点已掌握');
  await page.reload();
  await expect(page.locator('#summary')).toContainText('目标知识点已掌握');
});

for (const [topic, item, wording, option] of [
  ['cnm_067', parallelDefinition, /线段/, 'B'],
  ['cnm_285', probabilityRange, /完整/, 'A']
]) {
  test('reviewed choice ' + topic + ' has unambiguous conditions and stable feedback after refresh', { tag: '@grading-contract' }, async ({ page }) => {
    await page.goto(targetURL(topic, item.seed));
    await expect(page.locator('#q-text')).toHaveText(item.question.prompt);
    await expect(topic === 'cnm_067' ? page.locator('#choice-B') : page.locator('#q-text')).toContainText(wording);
    await activate(page, page.locator('#choice-' + option));
    await activate(page, page.locator('#btn-submit'));
    await expect(page.locator('.verdict')).toContainText('不正确');
    await activate(page, page.getByRole('button', { name: '重新作答', exact: true }));
    await activate(page, page.locator('#choice-' + item.question.answer));
    await activate(page, page.locator('#btn-submit'));
    await expect(page.locator('.verdict')).toHaveText('自动判定：正确');
    await page.reload();
    await expect(page.locator('#q-text')).toHaveText(item.question.prompt);
    await expect(page.locator('.verdict')).toHaveText('自动判定：正确');
    await noHorizontalOverflow(page);
  });
}

test('suspension question states independent traces and preserves its answer after refresh', { tag: '@grading-contract' }, async ({ page }) => {
  await page.goto(targetURL('cnm_119', suspension.seed));
  await expect(page.locator('#q-text')).toHaveText(suspension.question.prompt);
  await expect(page.locator('#q-text')).toContainText(/不重合/);
  await page.locator('#ans').fill('2');
  await activate(page, page.locator('#btn-submit'));
  await expect(page.locator('.verdict')).toHaveText('自动判定：正确');
  await page.reload();
  await expect(page.locator('.verdict')).toHaveText('自动判定：正确');
  await expect(page.locator('#q-text')).toContainText(/不重合/);
  await noHorizontalOverflow(page);
});

for (const [topic, item, wrong] of [
  ['cnm_107', histogramConvention, 'A'], ['cnm_109', daylightMaximum, 'B'],
  ['cnm_306', varianceInference, 'A']
]) {
  test('105-item reviewed conditions ' + topic + ' retain correct grading after refresh', { tag: '@grading-contract' }, async ({ page }) => {
    await page.goto(targetURL(topic, item.seed));
    await expect(page.locator('#q-text')).toHaveText(item.question.prompt);
    await activate(page, page.locator('#choice-' + wrong));
    await activate(page, page.locator('#btn-submit'));
    await expect(page.locator('.verdict')).toContainText('不正确');
    await activate(page, page.getByRole('button', { name: '重新作答', exact: true }));
    await activate(page, page.locator('#choice-' + item.question.answer));
    await activate(page, page.locator('#btn-submit'));
    await expect(page.locator('.verdict')).toHaveText('自动判定：正确');
    await page.reload();
    await expect(page.locator('#q-text')).toHaveText(item.question.prompt);
    await expect(page.locator('.verdict')).toHaveText('自动判定：正确');
    await noHorizontalOverflow(page);
  });
}
