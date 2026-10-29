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

for (const failure of ['404', 'invalid-json', 'network', 'incomplete-bank']) {
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
      const body = failure === '404' ? '{}' : failure === 'incomplete-bank' ? JSON.stringify(questions.slice(0, 1)) : '{broken-json';
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
