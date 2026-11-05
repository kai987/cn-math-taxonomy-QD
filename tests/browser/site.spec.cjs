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

function seedFor(topicId, predicate, avoid = []) {
  for (let index = 0; index < 200; index++) {
    const seed = 'browser-' + index;
    const item = E.nextItem(graph, E.createSession(graph, [topicId], { seed, avoid }));
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
const explicitAnglePositions = seedFor('cnm_070', question => question.id === 'cnm_070_q5');
const restrictedReadingSample = seedFor('cnm_104', question => question.id === 'cnm_104_q3');
const angleCriterionDomain = seedFor('cnm_129', question => question.id === 'cnm_129_q3');
const measuredGermination = seedFor('cnm_292', question => question.id === 'cnm_292_q1');
const linearMonotonicity = seedFor('cnm_203', question => question.id === 'cnm_203_q1');
const linearIntercept = seedFor('cnm_206', question => question.id === 'cnm_206_q1');
const dataOrganization = seedFor('cnm_300', question => question.id === 'cnm_300_q3');
const histogramAxisConvention = seedFor('cnm_107', question => question.id === 'cnm_107_q3');
const spinnerDesign = seedFor('cnm_315', question => question.id === 'cnm_315_q1');
const barProportions = seedFor('cnm_296', question => question.id === 'cnm_296_q2');
const threeStageTree = seedFor('cnm_287', question => question.id === 'cnm_287_q4');
const trackCompensation = seedFor('cnm_061', question => question.id === 'cnm_061_q4');
const integralSubstitution = seedFor('cnm_089', question => question.id === 'cnm_089_q5');
const finiteTableRepresentation = seedFor('cnm_198', question => question.id === 'cnm_198_q1');
const rotationDescription = seedFor('cnm_244', question => question.id === 'cnm_244_q2');
const factorizationTask = seedFor('cnm_225', question => question.id === 'cnm_225_q1');
const historicalSizeTask = seedFor('cnm_214', question => question.id === 'cnm_214_q2');
const restrictedFrameTask = seedFor('cnm_104', question => question.id === 'cnm_104_q3');
const statisticsWorkflow = seedFor('cnm_300', question => question.id === 'cnm_300_q1');
const statisticsFirstStep = seedFor('cnm_300', question => question.id === 'cnm_300_q2');
const salaryJudgment = seedFor('cnm_303', question => question.id === 'cnm_303_q1');
const inclusiveSchoolFrame = seedFor('cnm_104', question => question.id === 'cnm_104_q2');
const medianStability = seedFor('cnm_214', question => question.id === 'cnm_214_q1');
const stratifiedInclusion = seedFor('cnm_218', question => question.id === 'cnm_218_q4');
const fullSchoolInclusion = seedFor('cnm_302', question => question.id === 'cnm_302_q4');
const earlierSurveyQuestions = questions.filter(question => question.topicId === 'cnm_102' && question.id !== 'cnm_102_q4').map(question => question.id);
const surveyClaims = seedFor('cnm_102', question => question.id === 'cnm_102_q4', earlierSurveyQuestions);
const earlierRepresentativeQuestions = questions.filter(question => question.topicId === 'cnm_104' && question.id !== 'cnm_104_q4').map(question => question.id);
const representativeClaims = seedFor('cnm_104', question => question.id === 'cnm_104_q4', earlierRepresentativeQuestions);
const earlierPrecisionQuestions = questions.filter(question => question.topicId === 'cnm_299' && question.id !== 'cnm_299_q4').map(question => question.id);
const precisionClaims = seedFor('cnm_299', question => question.id === 'cnm_299_q4', earlierPrecisionQuestions);
const earlierSpinnerQuestions = questions.filter(question => question.topicId === 'cnm_315' && question.id !== 'cnm_315_q4').map(question => question.id);
const trialEvidence = seedFor('cnm_315', question => question.id === 'cnm_315_q4', earlierSpinnerQuestions);
const targetURL = (topic, seed) => siteURL('/diagnose/?target=' + topic + '&seed=' + seed);
const sessionKey = 'cnmDiagnose.session.v2';
const selfAssessmentIds = [
  'cnm_085_q1', 'cnm_102_q1', 'cnm_102_q2', 'cnm_102_q3',
  'cnm_105_q1', 'cnm_105_q2', 'cnm_130_q4', 'cnm_198_q2',
  'cnm_292_q2', 'cnm_292_q3', 'cnm_292_q4'
];

function forceQuestion(id) {
  const question = questions.find(question => question.id === id);
  if (!question) throw new Error('Missing reviewed question ' + id);
  const avoid = questions.filter(other => other.topicId === question.topicId && other.id !== id).map(other => other.id);
  return { ...seedFor(question.topicId, candidate => candidate.id === id, avoid), avoid };
}

const selfAssessmentTasks = selfAssessmentIds.map(forceQuestion);

async function preferUnseenQuestion(page, item) {
  await page.addInitScript(ids => {
    if (!localStorage.getItem('cnmDiagnose.seen.v1')) localStorage.setItem('cnmDiagnose.seen.v1', JSON.stringify(ids));
  }, item.avoid);
}

async function oldAutomaticQuestionBank(page) {
  const handler = async route => {
    const response = await route.fetch();
    const bank = await response.json();
    for (const question of bank) delete question.self_assess;
    await route.fulfill({ response, body: JSON.stringify(bank) });
  };
  await page.route('**/data/questions.json*', handler);
  return () => page.unroute('**/data/questions.json*', handler);
}

async function upgradeLegacySave(page, { oldQuestion = null, omitQuestionId = false, omitAnswer = false, earlierDraftBackup = null } = {}) {
  await page.addInitScript(({ key, question, omitQuestionId, omitAnswer, earlierDraftBackup }) => {
    const marker = 'browser.assessment-upgrade.v1';
    if (localStorage.getItem(marker)) return;
    const saved = JSON.parse(localStorage.getItem(key));
    if (!saved) throw new Error('Missing legacy session');
    for (const record of saved.answers) delete record.assessment;
    if (omitQuestionId && saved.answers[0]) delete saved.answers[0].qid;
    if (omitAnswer && saved.answers[0]) delete saved.answers[0].text;
    if (earlierDraftBackup) saved.draftBackup = earlierDraftBackup;
    if (question && saved.draft) saved.draft.questionFingerprint = JSON.stringify([
      question.type, question.prompt, question.choices || [], question.answer,
      question.accept || [], question.unit || '', !!question.unordered, question.variables || []
    ]);
    localStorage.setItem(key, JSON.stringify(saved));
    localStorage.setItem(marker, '1');
  }, { key: sessionKey, question: oldQuestion, omitQuestionId, omitAnswer, earlierDraftBackup });
}

async function selfAssessmentFeedback(page, item, selected) {
  await expect(page.locator('#q-text')).toHaveText(item.question.prompt);
  await expect(page.locator('#assessment-notice')).toBeVisible();
  await expect(page.locator('.verdict')).toHaveCount(0);
  await expect(page.getByText('你的答案：' + selected.key + '. ' + selected.text, { exact: true })).toBeVisible();
  await expect(page.locator('.refans')).toContainText('参考建议');
  await expect(page.locator('.refans')).toContainText(item.question.choices.find(option => option.key === item.question.answer).text);
  await expect(page.locator('#explain')).toContainText(item.question.explanation);
  await expect(page.locator('#btn-right')).toBeVisible();
  await expect(page.locator('#btn-wrong')).toBeVisible();
  await noHorizontalOverflow(page);
}

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

for (const failure of ['404', 'invalid-json', 'network', 'incomplete-bank', 'invalid-question-id', 'self-assess-false']) {
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
        : failure === 'invalid-question-id' ? JSON.stringify(questions.map((question, index) => index ? question : { ...question, id: 'invalid-id' }))
          : failure === 'self-assess-false' ? JSON.stringify(questions.map(question => question.id === selfAssessmentIds[0] ? { ...question, self_assess: false } : question)) : '{broken-json';
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

for (const [topic, item] of [
  ['cnm_070', explicitAnglePositions], ['cnm_104', restrictedReadingSample]
]) {
  test('63-item reviewed wording ' + topic + ' keeps its selected answer and feedback after refresh', { tag: '@grading-contract' }, async ({ page }) => {
    await page.goto(targetURL(topic, item.seed));
    await expect(page.locator('#q-text')).toHaveText(item.question.prompt);
    await activate(page, page.locator('#choice-A'));
    await activate(page, page.locator('#btn-submit'));
    await expect(page.locator('.verdict')).toContainText('不正确');
    await activate(page, page.getByRole('button', { name: '重新作答', exact: true }));
    const correct = page.locator('#choice-' + item.question.answer);
    await activate(page, correct);
    await page.reload();
    await expect(correct).toHaveAttribute('aria-pressed', 'true');
    await activate(page, page.locator('#btn-submit'));
    await expect(page.locator('.verdict')).toHaveText('自动判定：正确');
    await page.reload();
    await expect(page.locator('.verdict')).toHaveText('自动判定：正确');
    await expect(page.locator('#q-text')).toHaveText(item.question.prompt);
    await noHorizontalOverflow(page);
  });
}

for (const [topic, item, condition] of [
  ['cnm_129', angleCriterionDomain, '0°<∠AOB<180°'],
  ['cnm_292', measuredGermination, '尚无这种新型种子在规定条件下的可靠发芽资料']
]) {
  test('43-item reviewed conditions ' + topic + ' keep current references and grading after refresh', { tag: '@grading-contract' }, async ({ page }) => {
    await page.goto(targetURL(topic, item.seed));
    await expect(page.locator('#q-text')).toHaveText(item.question.prompt);
    await expect(page.locator('#q-text')).toContainText(condition);
    await activate(page, page.locator('#choice-A'));
    await activate(page, page.locator('#btn-submit'));
    await expect(page.locator('.verdict')).toHaveText('自动判定：不正确');
    await activate(page, page.getByRole('button', { name: '重新作答', exact: true }));
    const correct = page.locator('#choice-' + item.question.answer);
    await activate(page, correct);
    await page.reload();
    await expect(correct).toHaveAttribute('aria-pressed', 'true');
    await activate(page, page.locator('#btn-submit'));
    await expect(page.locator('.verdict')).toHaveText('自动判定：正确');
    await page.reload();
    await expect(page.locator('#q-text')).toHaveText(item.question.prompt);
    await expect(page.locator('.verdict')).toHaveText('自动判定：正确');
    await expect(page.locator('.refans')).toContainText(item.question.choices.find(option => option.key === item.question.answer).text);
    await expect(page.locator('#explain')).toContainText(item.question.explanation);
    await noHorizontalOverflow(page);
  });
}

for (const [topic, item] of [['cnm_203', linearMonotonicity], ['cnm_206', linearIntercept]]) {
  test('41-item reference model ' + topic + ' preserves free-response self assessment after refresh', async ({ page }) => {
    expect(item.question.type).toBe('self');
    expect(item.question.verify).toBe("model('" + item.question.id + "')");
    await page.goto(targetURL(topic, item.seed));
    await expect(page.locator('#q-text')).toHaveText(item.question.prompt);
    await page.locator('textarea#ans').fill(item.question.answer);
    await activate(page, page.locator('#btn-peek'));
    await expect(page.locator('.refans')).toContainText(item.question.answer);
    await expect(page.locator('.verdict')).toHaveCount(0);
    await expect(page.locator('#btn-right')).toBeVisible();
    await expect(page.locator('#btn-wrong')).toBeVisible();
    await page.reload();
    await expect(page.getByText('你的答案：' + item.question.answer, { exact: true })).toBeVisible();
    expect((await savedSession(page)).draft.answer).toBe(item.question.answer);
    await expect(page.locator('.refans')).toContainText(item.question.answer);
    await expect(page.locator('#explain')).toContainText(item.question.explanation);
    await expect(page.locator('.verdict')).toHaveCount(0);
    await activate(page, page.locator('#btn-right'));
    await expect(page.locator('#summary')).toContainText('目标知识点已掌握');
    await page.reload();
    await expect(page.locator('#summary')).toContainText('目标知识点已掌握');
    await noHorizontalOverflow(page);
  });
}

test('41-item data organization distinguishes counting from inference after refresh', { tag: '@grading-contract' }, async ({ page }) => {
  await page.goto(targetURL('cnm_300', dataOrganization.seed));
  await expect(page.locator('#q-text')).toHaveText(dataOrganization.question.prompt);
  await activate(page, page.locator('#choice-C'));
  await activate(page, page.locator('#btn-submit'));
  await expect(page.locator('.verdict')).toHaveText('自动判定：不正确');
  await activate(page, page.getByRole('button', { name: '重新作答', exact: true }));
  await activate(page, page.locator('#choice-' + dataOrganization.question.answer));
  await activate(page, page.locator('#btn-submit'));
  await expect(page.locator('.verdict')).toHaveText('自动判定：正确');
  await page.reload();
  await expect(page.locator('#q-text')).toHaveText(dataOrganization.question.prompt);
  await expect(page.locator('.verdict')).toHaveText('自动判定：正确');
  await expect(page.locator('#explain')).toContainText(dataOrganization.question.explanation);
  await noHorizontalOverflow(page);
});

test('36-item histogram wording states the frequency-height convention and keeps feedback after refresh', { tag: '@grading-contract' }, async ({ page }) => {
  await page.goto(targetURL('cnm_107', histogramAxisConvention.seed));
  await expect(page.locator('#q-text')).toHaveText(histogramAxisConvention.question.prompt);
  await expect(page.locator('#q-text')).toContainText(/等组距|组距相等/);
  await activate(page, page.locator('#choice-A'));
  await activate(page, page.locator('#btn-submit'));
  await expect(page.locator('.verdict')).toHaveText('自动判定：不正确');
  await activate(page, page.getByRole('button', { name: '重新作答', exact: true }));
  await activate(page, page.locator('#choice-' + histogramAxisConvention.question.answer));
  await activate(page, page.locator('#btn-submit'));
  await page.reload();
  await expect(page.locator('#q-text')).toHaveText(histogramAxisConvention.question.prompt);
  await expect(page.locator('.verdict')).toHaveText('自动判定：正确');
  await expect(page.locator('#explain')).toContainText(histogramAxisConvention.question.explanation);
  await noHorizontalOverflow(page);
});

test('36-item spinner reference retains trial limits and student self assessment after refresh', async ({ page }) => {
  await page.goto(targetURL('cnm_315', spinnerDesign.seed));
  await expect(page.locator('#q-text')).toHaveText(spinnerDesign.question.prompt);
  await page.locator('textarea#ans').fill(spinnerDesign.question.answer);
  await activate(page, page.locator('#btn-peek'));
  await expect(page.locator('.refans')).toContainText(spinnerDesign.question.answer);
  await expect(page.locator('.refans')).toContainText('有限');
  await expect(page.locator('.verdict')).toHaveCount(0);
  await page.reload();
  await expect(page.getByText('你的答案：' + spinnerDesign.question.answer, { exact: true })).toBeVisible();
  expect((await savedSession(page)).draft.answer).toBe(spinnerDesign.question.answer);
  await expect(page.locator('.refans')).toContainText(spinnerDesign.question.answer);
  await expect(page.locator('#explain')).toContainText(spinnerDesign.question.explanation);
  await expect(page.locator('.verdict')).toHaveCount(0);
  await expect(page.locator('#btn-wrong')).toBeVisible();
  await noHorizontalOverflow(page);
  await activate(page, page.locator('#btn-right'));
  await expect(page.locator('#summary')).toContainText('目标知识点已掌握');
  await page.reload();
  await expect(page.locator('#summary')).toContainText('目标知识点已掌握');
});

for (const [topic, item] of [['cnm_296', barProportions], ['cnm_287', threeStageTree]]) {
  test('33-item precise task ' + topic + ' keeps current grading and explanation after refresh', { tag: '@grading-contract' }, async ({ page }) => {
    await page.goto(targetURL(topic, item.seed));
    await expect(page.locator('#q-text')).toHaveText(item.question.prompt);
    const wrong = item.question.choices.find(option => option.key !== item.question.answer).key;
    await activate(page, page.locator('#choice-' + wrong));
    await activate(page, page.locator('#btn-submit'));
    await expect(page.locator('.verdict')).toHaveText('自动判定：不正确');
    await activate(page, page.getByRole('button', { name: '重新作答', exact: true }));
    await activate(page, page.locator('#choice-' + item.question.answer));
    await activate(page, page.locator('#btn-submit'));
    await expect(page.locator('.verdict')).toHaveText('自动判定：正确');
    await page.reload();
    await expect(page.locator('#q-text')).toHaveText(item.question.prompt);
    await expect(page.locator('.verdict')).toHaveText('自动判定：正确');
    await expect(page.locator('#explain')).toContainText(item.question.explanation);
    await noHorizontalOverflow(page);
  });
}

test('33-item fairness task uses the unseen advanced item and preserves its full feedback', async ({ page }) => {
  await page.addInitScript(ids => {
    if (!localStorage.getItem('cnmDiagnose.seen.v1')) localStorage.setItem('cnmDiagnose.seen.v1', JSON.stringify(ids));
  }, earlierSpinnerQuestions);
  await page.goto(targetURL('cnm_315', trialEvidence.seed));
  await expect(page.locator('#q-text')).toHaveText(trialEvidence.question.prompt);
  await activate(page, page.locator('#choice-D'));
  await activate(page, page.locator('#btn-submit'));
  await expect(page.locator('.verdict')).toHaveText('自动判定：不正确');
  await activate(page, page.getByRole('button', { name: '重新作答', exact: true }));
  const correct = page.locator('#choice-' + trialEvidence.question.answer);
  await activate(page, correct);
  await page.reload();
  await expect(correct).toHaveAttribute('aria-pressed', 'true');
  await activate(page, page.locator('#btn-submit'));
  await expect(page.locator('.verdict')).toHaveText('自动判定：正确');
  await page.reload();
  await expect(page.locator('#q-text')).toHaveText(trialEvidence.question.prompt);
  await expect(page.locator('.verdict')).toHaveText('自动判定：正确');
  await expect(page.locator('.refans')).toContainText(trialEvidence.question.choices.find(option => option.key === trialEvidence.question.answer).text);
  await expect(page.locator('#explain')).toContainText(trialEvidence.question.explanation);
  await noHorizontalOverflow(page);
});

async function reviewedChoiceAfterRefresh(page, { topic, item, wrong, conditions }) {
  await page.goto(targetURL(topic, item.seed));
  await expect(page).toHaveTitle(/数学知识点诊断小工具/);
  await expect(page.locator('#q-text')).toHaveText(item.question.prompt);
  for (const condition of conditions) await expect(page.locator('#q-text')).toContainText(condition);
  await noHorizontalOverflow(page);
  await activate(page, page.locator('#choice-' + wrong));
  await activate(page, page.locator('#btn-submit'));
  await expect(page.locator('.verdict')).toHaveText('自动判定：不正确');
  await activate(page, page.getByRole('button', { name: '重新作答', exact: true }));
  const correct = page.locator('#choice-' + item.question.answer);
  await activate(page, correct);
  await page.reload();
  await expect(page.locator('#q-text')).toHaveText(item.question.prompt);
  await expect(correct).toHaveAttribute('aria-pressed', 'true');
  expect((await savedSession(page)).draft.answer).toBe(item.question.answer);
  await noHorizontalOverflow(page);
  await activate(page, page.locator('#btn-submit'));
  await expect(page.locator('.verdict')).toHaveText('自动判定：正确');
  const reference = item.question.choices.find(option => option.key === item.question.answer).text;
  await expect(page.locator('.refans')).toContainText(reference);
  await expect(page.locator('#explain')).toContainText(item.question.explanation);
  await page.reload();
  await expect(page.locator('#q-text')).toHaveText(item.question.prompt);
  await expect(page.locator('.verdict')).toHaveText('自动判定：正确');
  await expect(page.locator('.refans')).toContainText(reference);
  await expect(page.locator('#explain')).toContainText(item.question.explanation);
  await noHorizontalOverflow(page);
}

for (const example of [
  { topic: 'cnm_102', item: surveyClaims, wrong: 'D', conditions: [], avoid: earlierSurveyQuestions },
  { topic: 'cnm_104', item: representativeClaims, wrong: 'C', conditions: [], avoid: earlierRepresentativeQuestions },
  { topic: 'cnm_299', item: precisionClaims, wrong: 'B', conditions: [], avoid: earlierPrecisionQuestions }
]) {
  test('16-item advanced task ' + example.item.question.id + ' keeps its exact premise, grading and explanation after refresh', async ({ page }) => {
    await page.addInitScript(ids => {
      if (!localStorage.getItem('cnmDiagnose.seen.v1')) localStorage.setItem('cnmDiagnose.seen.v1', JSON.stringify(ids));
    }, example.avoid);
    await reviewedChoiceAfterRefresh(page, example);
  });
}

for (const example of [
  { topic: 'cnm_104', item: inclusiveSchoolFrame, wrong: 'A', conditions: [] },
  { topic: 'cnm_214', item: medianStability, wrong: 'C', conditions: [] },
  { topic: 'cnm_218', item: stratifiedInclusion, wrong: 'D', conditions: [] },
  { topic: 'cnm_302', item: fullSchoolInclusion, wrong: 'C', conditions: [] }
]) {
  test('20-item explicit mathematical goal ' + example.item.question.id + ' preserves grading and current feedback after refresh', async ({ page }) => {
    await reviewedChoiceAfterRefresh(page, example);
    if (example.item.question.id.endsWith('_q1')) {
      const topic = topics.find(topic => topic.id === example.topic);
      await page.goto(siteURL('/#' + example.topic));
      await expect(page).toHaveTitle(/中小学数学知识图谱/);
      await expect(page.locator('#main .title')).toHaveText(topic.name);
      await expect(page.locator('#main .q > div')).toHaveText(example.item.question.prompt);
      await activate(page, page.locator('#main details.ans > summary'));
      await expect(page.locator('#main details.ans > div')).toHaveText(topic.diagnostic_question.answer);
      await expect(page.locator('#main details.ans > div')).toBeVisible();
      await noHorizontalOverflow(page);
      await page.reload();
      await expect(page.locator('#main .q > div')).toHaveText(example.item.question.prompt);
    }
  });
}

for (const example of [
  { topic: 'cnm_225', item: factorizationTask, wrong: 'B', conditions: [] },
  { topic: 'cnm_214', item: historicalSizeTask, wrong: 'A', conditions: [] },
  { topic: 'cnm_300', item: statisticsWorkflow, wrong: 'B', conditions: [] }
]) {
  test('25-item explicit task ' + example.item.question.id + ' keeps grading, reference and explanation after refresh', async ({ page }) => {
    await reviewedChoiceAfterRefresh(page, example);
    if (example.item.question.id.endsWith('_q1')) {
      const topic = topics.find(topic => topic.id === example.topic);
      await page.goto(siteURL('/#' + example.topic));
      await expect(page.locator('#main .title')).toHaveText(topic.name);
      await expect(page.locator('#main .q > div')).toHaveText(topic.diagnostic_question.question);
      await activate(page, page.locator('#main details.ans > summary'));
      await expect(page.locator('#main details.ans > div')).toHaveText(topic.diagnostic_question.answer);
      await expect(page.locator('#main details.ans > div')).toBeVisible();
      await noHorizontalOverflow(page);
    }
  });
}

for (const example of [
  { topic: 'cnm_104', item: restrictedFrameTask, wrong: 'C', conditions: [] },
  { topic: 'cnm_300', item: statisticsFirstStep, wrong: 'C', conditions: [] }
]) {
  test('25-item grading contract ' + example.item.question.id + ' retains current constraints after refresh', { tag: '@grading-contract' }, async ({ page }) => {
    await reviewedChoiceAfterRefresh(page, example);
  });
}

test('25-item salary interpretation remains self assessed with its draft and reference after refresh', async ({ page }) => {
  const draft = '平均数20，中位数9；代表性还需要说明比较目标。';
  expect(salaryJudgment.question.type).toBe('self');
  expect(salaryJudgment.question.verify).toBeUndefined();
  expect(salaryJudgment.question.answer).toContain('千元');
  expect(salaryJudgment.question.answer).toContain('若');
  const preview = topics.find(topic => topic.id === 'cnm_303').diagnostic_question;
  expect(preview.answer).toBe(salaryJudgment.question.answer);
  await page.goto(siteURL('/#cnm_303'));
  await expect(page.locator('#main .q > div')).toHaveText(preview.question);
  await activate(page, page.locator('#main details.ans > summary'));
  await expect(page.locator('#main details.ans > div')).toHaveText(preview.answer);
  await page.reload();
  await activate(page, page.locator('#main details.ans > summary'));
  await expect(page.locator('#main details.ans > div')).toHaveText(preview.answer);
  await noHorizontalOverflow(page);
  await page.goto(targetURL('cnm_303', salaryJudgment.seed));
  await expect(page).toHaveTitle(/数学知识点诊断/);
  await expect(page.locator('#q-text')).toHaveText(salaryJudgment.question.prompt);
  await page.locator('textarea#ans').fill(draft);
  await page.reload();
  await expect(page.locator('textarea#ans')).toHaveValue(draft);
  await activate(page, page.locator('#btn-peek'));
  await expect(page.locator('.refans')).toContainText(salaryJudgment.question.answer);
  await expect(page.locator('#explain')).toContainText(salaryJudgment.question.explanation);
  await expect(page.locator('.verdict')).toHaveCount(0);
  await expect(page.locator('#btn-right')).toBeVisible();
  await expect(page.locator('#btn-wrong')).toBeVisible();
  await page.reload();
  await expect(page.getByText('你的答案：' + draft, { exact: true })).toBeVisible();
  expect((await savedSession(page)).draft.answer).toBe(draft);
  await expect(page.locator('.refans')).toContainText(salaryJudgment.question.answer);
  await expect(page.locator('#explain')).toContainText(salaryJudgment.question.explanation);
  await expect(page.locator('.verdict')).toHaveCount(0);
  await expect(page.locator('#btn-right')).toBeVisible();
  await expect(page.locator('#btn-wrong')).toBeVisible();
  await noHorizontalOverflow(page);
});

for (const item of selfAssessmentTasks) {
  test('explicit self assessment ' + item.question.id + ' keeps a nonreference selection pending until human confirmation', { tag: '@grading-contract' }, async ({ page }) => {
    expect(item.question.type).toBe('choice');
    expect(item.question.self_assess).toBe(true);
    const selected = item.question.choices.find(option => option.key !== item.question.answer);
    await preferUnseenQuestion(page, item);
    await page.goto(targetURL(item.question.topicId, item.seed));
    await expect(page.locator('#q-text')).toHaveText(item.question.prompt);
    await activate(page, page.locator('#choice-' + selected.key));
    await activate(page, page.locator('#btn-submit'));
    await selfAssessmentFeedback(page, item, selected);
    expect((await savedSession(page)).answers).toHaveLength(0);
    await page.reload();
    await selfAssessmentFeedback(page, item, selected);
    expect((await savedSession(page)).answers).toHaveLength(0);

    // A different choice is not automatically a weakness: the learner confirms
    // their own reasoned understanding after reading the conditional advice.
    await activate(page, page.locator('#btn-right'));
    await expect(page.locator('#summary')).toContainText('目标知识点已掌握');
    expect((await savedSession(page)).answers).toEqual([
      expect.objectContaining({ qid: item.question.id, text: selected.key, result: 'correct', assessment: 'self' })
    ]);
    await page.reload();
    await expect(page.locator('#summary')).toContainText('目标知识点已掌握');
    expect((await savedSession(page)).answers).toHaveLength(1);
    await expect(page.locator('#assessment-review-notice')).toHaveCount(0);
    await noHorizontalOverflow(page);
  });
}

test('contextual questionnaire choices retain selection, advice and an explicit wrong self assessment on every layout', async ({ page }, info) => {
  const item = selfAssessmentTasks.find(item => item.question.id === 'cnm_292_q4');
  const selected = item.question.choices.find(option => option.key === 'A');
  await preferUnseenQuestion(page, item);
  await page.goto(targetURL(item.question.topicId, item.seed));
  await activate(page, page.locator('#choice-A'));
  await page.reload();
  await expect(page.locator('#choice-A')).toHaveAttribute('aria-pressed', 'true');
  expect((await savedSession(page)).answers).toHaveLength(0);
  await activate(page, page.locator('#btn-submit'));
  await selfAssessmentFeedback(page, item, selected);
  await page.reload();
  await selfAssessmentFeedback(page, item, selected);
  if (info.project.name.includes('phone')) {
    for (const viewport of [{ width: 320, height: 568 }, { width: 844, height: 390 }]) {
      await page.setViewportSize(viewport);
      await noHorizontalOverflow(page);
      await expect(page.locator('#btn-wrong')).toBeVisible();
    }
  }
  await page.screenshot({ path: info.outputPath('choice-self-assessment.png') });
  await activate(page, page.locator('#btn-wrong'));
  expect((await savedSession(page)).answers).toEqual([
    expect.objectContaining({ qid: item.question.id, text: selected.key, result: 'wrong', assessment: 'self' })
  ]);
  await page.reload();
  expect((await savedSession(page)).answers).toHaveLength(1);
  expect((await savedSession(page)).answers[0].assessment).toBe('self');
  await expect(page.locator('#assessment-review-notice')).toHaveCount(0);
  await noHorizontalOverflow(page);
});

for (const legacyFields of [8, 9]) {
  test('an old ' + (legacyFields === 8 ? 'eight-field' : 'nine-field policy-only') + ' automatic feedback draft becomes self assessment without losing the selected alternative', async ({ page }) => {
    const item = selfAssessmentTasks.find(item => item.question.id === 'cnm_292_q2');
    const selected = item.question.choices.find(option => option.key === 'C');
    await preferUnseenQuestion(page, item);
    const restoreCurrentBank = await oldAutomaticQuestionBank(page);
    await page.goto(targetURL(item.question.topicId, item.seed));
    await activate(page, page.locator('#choice-' + selected.key));
    await activate(page, page.locator('#btn-submit'));
    await expect(page.locator('.verdict')).toHaveText('自动判定：不正确');
    expect((await savedSession(page)).answers).toHaveLength(0);
    if (legacyFields === 9) {
      const fingerprint = JSON.parse((await savedSession(page)).draft.questionFingerprint);
      expect(fingerprint).toHaveLength(9);
      expect(fingerprint[8]).toBe(false);
    }
    await upgradeLegacySave(page, { oldQuestion: legacyFields === 8 ? item.question : null });
    await restoreCurrentBank();
    await page.reload();
    await selfAssessmentFeedback(page, item, selected);
    expect((await savedSession(page)).answers).toHaveLength(0);
    expect((await savedSession(page)).draft.answer).toBe(selected.key);
    await expect(page.locator('#draft-backup')).toHaveCount(0);
    await page.reload();
    await selfAssessmentFeedback(page, item, selected);
    expect((await savedSession(page)).answers).toHaveLength(0);
  });
}

for (const omitQuestionId of [false, true]) {
  test('legacy completed history ' + (omitQuestionId ? 'without an old question id' : 'with question ids') + ' pauses at each changed policy and restores the valid tail after confirmation', async ({ page }) => {
    const targets = ['cnm_085', 'cnm_225', 'cnm_292'];
    const qids = ['cnm_085_q1', 'cnm_225_q1', 'cnm_292_q2'];
    const avoid = questions.filter(question => targets.includes(question.topicId) && !qids.includes(question.id)).map(question => question.id);
    await page.addInitScript(ids => {
      if (!localStorage.getItem('cnmDiagnose.seen.v1')) localStorage.setItem('cnmDiagnose.seen.v1', JSON.stringify(ids));
    }, avoid);
    const restoreCurrentBank = await oldAutomaticQuestionBank(page);
    const seed = 'browser-legacy-assessment';
    const legacyGraph = E.buildGraph(topics, read('dependencies'), questions.map(question => {
      const copy = { ...question }; delete copy.self_assess; return copy;
    }));
    let modeled = E.createSession(legacyGraph, targets, { seed, avoid });
    const sequence = [];
    await page.goto(targetURL(targets.join(','), seed));
    for (let item; (item = E.nextItem(legacyGraph, modeled));) {
      sequence.push(item.question);
      await expect(page.locator('#q-text')).toHaveText(item.question.prompt);
      await answerCorrectly(page, item);
      modeled = E.applyAnswer(legacyGraph, modeled, item.topicId, 'correct', { text: item.question.answer });
    }
    expect(sequence.map(question => question.id)).toEqual(['cnm_292_q2', 'cnm_225_q1', 'cnm_085_q1']);
    await expect(page.locator('#summary')).toBeVisible();
    const legacyAnswers = (await savedSession(page)).answers.map(record => {
      const copy = { ...record }; delete copy.assessment; return copy;
    });
    if (omitQuestionId) delete legacyAnswers[0].qid;
    await upgradeLegacySave(page, { omitQuestionId });
    await restoreCurrentBank();
    await page.reload();

    const first = { question: sequence[0] };
    const firstChoice = first.question.choices.find(option => option.key === first.question.answer);
    await expect(page.locator('#assessment-review-notice')).toBeVisible();
    await selfAssessmentFeedback(page, first, firstChoice);
    expect((await savedSession(page)).answers).toHaveLength(0);
    expect((await savedSession(page)).assessmentHistoryBackup).toEqual(legacyAnswers);
    await activate(page, page.locator('#assessment-history-backup summary'));
    await expect(page.locator('#assessment-history-backup')).toBeVisible();
    await noHorizontalOverflow(page);
    await page.reload();
    await selfAssessmentFeedback(page, first, firstChoice);
    expect((await savedSession(page)).assessmentHistoryBackup).toEqual(legacyAnswers);

    await activate(page, page.locator('#btn-right'));
    const final = { question: sequence[2] };
    const finalChoice = final.question.choices.find(option => option.key === final.question.answer);
    await expect(page.locator('#assessment-review-notice')).toBeVisible();
    await selfAssessmentFeedback(page, final, finalChoice);
    expect((await savedSession(page)).answers).toEqual([
      expect.objectContaining({ qid: sequence[0].id, result: 'correct', assessment: 'self' }),
      expect.objectContaining({ qid: sequence[1].id, result: 'correct' })
    ]);
    expect((await savedSession(page)).assessmentHistoryBackup).toEqual(legacyAnswers);
    await page.reload();
    await selfAssessmentFeedback(page, final, finalChoice);
    expect((await savedSession(page)).answers).toHaveLength(2);
    expect((await savedSession(page)).assessmentHistoryBackup).toEqual(legacyAnswers);

    await activate(page, page.locator('#btn-right'));
    await expect(page.locator('#summary')).toContainText('目标知识点已掌握');
    expect((await savedSession(page)).answers.map(record => record.qid)).toEqual(sequence.map(question => question.id));
    expect((await savedSession(page)).answers.filter(record => record.assessment === 'self')).toHaveLength(2);
    await page.reload();
    await expect(page.locator('#summary')).toContainText('目标知识点已掌握');
    await expect(page.locator('#assessment-review-notice')).toHaveCount(0);
    expect((await savedSession(page)).answers).toHaveLength(3);
    expect((await savedSession(page)).assessmentHistoryBackup).toEqual(legacyAnswers);
    await noHorizontalOverflow(page);
  });
}

test('changing a legacy self assessment excludes an obsolete follow-up while preserving the complete history backup', async ({ page }) => {
  const first = selfAssessmentTasks.find(item => item.question.id === 'cnm_102_q1');
  const followUp = { question: questions.find(question => question.id === 'cnm_102_q2') };
  const selected = first.question.choices.find(option => option.key === 'B');
  await preferUnseenQuestion(page, first);
  const restoreCurrentBank = await oldAutomaticQuestionBank(page);
  await page.goto(targetURL(first.question.topicId, first.seed));
  await activate(page, page.locator('#choice-' + selected.key));
  await activate(page, page.locator('#btn-submit'));
  await expect(page.locator('.verdict')).toHaveText('自动判定：不正确');
  await activate(page, page.locator('#btn-next'));
  await expect(page.locator('#q-text')).toHaveText(followUp.question.prompt);
  await answerCorrectly(page, followUp);
  await expect(page.locator('#summary')).toBeVisible();
  const legacyAnswers = (await savedSession(page)).answers.map(record => {
    const copy = { ...record }; delete copy.assessment; return copy;
  });
  expect(legacyAnswers.map(record => record.qid)).toEqual([first.question.id, followUp.question.id]);
  await upgradeLegacySave(page);
  await restoreCurrentBank();
  await page.reload();
  await selfAssessmentFeedback(page, first, selected);
  await expect(page.locator('#assessment-review-notice')).toBeVisible();
  expect((await savedSession(page)).answers).toHaveLength(0);
  expect((await savedSession(page)).assessmentHistoryBackup).toEqual(legacyAnswers);

  await activate(page, page.locator('#btn-right'));
  // Policy review is required even for this now obsolete record. Reviewing it
  // must not reintroduce a second attempt after the first is self-assessed right.
  const followUpChoice = followUp.question.choices.find(option => option.key === followUp.question.answer);
  await selfAssessmentFeedback(page, followUp, followUpChoice);
  await expect(page.locator('#assessment-review-notice')).toBeVisible();
  expect((await savedSession(page)).answers).toEqual([
    expect.objectContaining({ qid: first.question.id, text: selected.key, result: 'correct', assessment: 'self' })
  ]);
  expect((await savedSession(page)).assessmentHistoryBackup).toEqual(legacyAnswers);
  await page.reload();
  await selfAssessmentFeedback(page, followUp, followUpChoice);
  expect((await savedSession(page)).answers).toHaveLength(1);
  expect((await savedSession(page)).assessmentHistoryBackup).toEqual(legacyAnswers);
  await activate(page, page.locator('#btn-right'));
  await expect(page.locator('#summary')).toContainText('目标知识点已掌握');
  await expect(page.locator('#log tbody tr')).toHaveCount(1);
  expect((await savedSession(page)).answers.map(record => record.qid)).toEqual([first.question.id]);
  expect((await savedSession(page)).assessmentHistoryBackup).toEqual(legacyAnswers);
  await page.reload();
  await expect(page.locator('#summary')).toContainText('目标知识点已掌握');
  await expect(page.locator('#assessment-review-notice')).toHaveCount(0);
  expect((await savedSession(page)).answers.map(record => record.qid)).toEqual([first.question.id]);
  expect((await savedSession(page)).assessmentHistoryBackup).toEqual(legacyAnswers);
  await noHorizontalOverflow(page);
});

test('assessment migration retains both an earlier backup and the displaced current draft across repeated refreshes', async ({ page }) => {
  const targets = ['cnm_085', 'cnm_225', 'cnm_292'];
  const selectedIds = ['cnm_085_q1', 'cnm_225_q1', 'cnm_292_q2'];
  const avoid = questions.filter(question => targets.includes(question.topicId) && !selectedIds.includes(question.id)).map(question => question.id);
  await page.addInitScript(ids => {
    if (!localStorage.getItem('cnmDiagnose.seen.v1')) localStorage.setItem('cnmDiagnose.seen.v1', JSON.stringify(ids));
  }, avoid);
  const restoreCurrentBank = await oldAutomaticQuestionBank(page);
  await page.goto(targetURL(targets.join(','), 'browser-legacy-assessment'));
  const first = { question: questions.find(question => question.id === 'cnm_292_q2') };
  await expect(page.locator('#q-text')).toHaveText(first.question.prompt);
  await answerCorrectly(page, first);
  await expect(page.locator('#q-text')).toHaveText(factorizationTask.question.prompt);
  const currentSelection = factorizationTask.question.choices.find(option => option.key === 'B');
  await activate(page, page.locator('#choice-' + currentSelection.key));
  const displacedDraft = (await savedSession(page)).draft;
  expect(displacedDraft.questionId).toBe(factorizationTask.question.id);
  expect(displacedDraft.answer).toBe(currentSelection.key);
  const earlierDraft = {
    key: numeric.question.topicId + '#1', questionId: numeric.question.id,
    prompt: numeric.question.prompt, answer: '更早题目更新前保留的计算：123 + 7', phase: 'ask'
  };
  await upgradeLegacySave(page, { earlierDraftBackup: earlierDraft });
  await restoreCurrentBank();
  await page.reload();
  for (let refresh = 0; refresh < 3; refresh++) {
    await expect(page.locator('#assessment-review-notice')).toBeVisible();
    await expect(page.locator('#q-text')).toHaveText(first.question.prompt);
    const saved = await savedSession(page);
    expect(saved.answers).toHaveLength(0);
    expect(saved.draftBackup).toEqual(displacedDraft);
    expect(saved.draftBackupHistory).toEqual([earlierDraft]);
    await activate(page, page.locator('#draft-backup summary'));
    await expect(page.locator('#draft-backup p')).toHaveText(displacedDraft.prompt);
    await expect(page.locator('#draft-backup pre')).toHaveText(currentSelection.key);
    await activate(page, page.locator('#draft-backup-history summary'));
    await expect(page.locator('#draft-backup-history')).toContainText(earlierDraft.prompt);
    await expect(page.locator('#draft-backup-history')).toContainText(earlierDraft.answer);
    await noHorizontalOverflow(page);
    if (refresh < 2) await page.reload();
  }
});

for (const omitAnswer of [false, true]) {
  test('legacy automatic wrong ' + (omitAnswer ? 'without a saved selection' : 'with a saved alternative') + ' is excluded until explicit self assessment', { tag: '@grading-contract' }, async ({ page }) => {
    const item = selfAssessmentTasks.find(item => item.question.id === 'cnm_292_q2');
    const selected = item.question.choices.find(option => option.key === 'C');
    await preferUnseenQuestion(page, item);
    const restoreCurrentBank = await oldAutomaticQuestionBank(page);
    await page.goto(targetURL(item.question.topicId, item.seed));
    await activate(page, page.locator('#choice-' + selected.key));
    await activate(page, page.locator('#btn-submit'));
    await expect(page.locator('.verdict')).toHaveText('自动判定：不正确');
    await activate(page, page.locator('#btn-next'));
    expect((await savedSession(page)).answers).toHaveLength(1);
    await upgradeLegacySave(page, { omitAnswer });
    await restoreCurrentBank();
    await page.reload();
    await expect(page.locator('#assessment-review-notice')).toBeVisible();
    await expect(page.locator('#q-text')).toHaveText(item.question.prompt);
    await expect(page.locator('.verdict')).toHaveCount(0);
    expect((await savedSession(page)).answers).toHaveLength(0);
    if (omitAnswer) {
      expect((await savedSession(page)).draft.answer).toBe('');
      await expect(page.getByText('你的答案：' + selected.key + '. ' + selected.text, { exact: true })).toHaveCount(0);
    } else await selfAssessmentFeedback(page, item, selected);
    await page.reload();
    await expect(page.locator('#assessment-review-notice')).toBeVisible();
    expect((await savedSession(page)).answers).toHaveLength(0);
    expect((await savedSession(page)).assessmentHistoryBackup).toHaveLength(1);
    await activate(page, page.locator('#btn-right'));
    await expect(page.locator('#summary')).toContainText('目标知识点已掌握');
    expect((await savedSession(page)).answers).toEqual([
      expect.objectContaining({ qid: item.question.id, result: 'correct', assessment: 'self' })
    ]);
    await page.reload();
    await expect(page.locator('#summary')).toContainText('目标知识点已掌握');
    await expect(page.locator('#assessment-review-notice')).toHaveCount(0);
    expect((await savedSession(page)).answers).toHaveLength(1);
    await noHorizontalOverflow(page);
  });
}

test('classroom format retains fixed-key automatic grading and the self assessment scope stays explicit', { tag: '@grading-contract' }, async ({ page }) => {
  expect(questions.filter(question => question.self_assess === true).map(question => question.id).sort()).toEqual([...selfAssessmentIds].sort());
  const item = forceQuestion('cnm_118_q1');
  expect(item.question.self_assess).toBeUndefined();
  await preferUnseenQuestion(page, item);
  await reviewedChoiceAfterRefresh(page, { topic: item.question.topicId, item, wrong: 'A', conditions: [] });
  await expect(page.locator('#assessment-notice')).toHaveCount(0);
});

for (const example of [
  { topic: 'cnm_061', item: trackCompensation, wrong: 'A', conditions: [/同一终点线/, /400\s*m/] },
  { topic: 'cnm_089', item: integralSubstitution, wrong: 'B', conditions: [/避免引入分数/, /整系数一次式/] }
]) {
  test('29-item grading contract ' + example.topic + ' rejects an irrelevant rule and restores full feedback', { tag: '@grading-contract' }, async ({ page }) => {
    await reviewedChoiceAfterRefresh(page, example);
  });
}

for (const example of [
  { topic: 'cnm_198', item: finiteTableRepresentation, wrong: 'D', conditions: [/非退化实区间/, /有限个/, /未给解析式/] },
  { topic: 'cnm_244', item: rotationDescription, wrong: 'D', conditions: [/无向转角大小/, /方向分开记录/] }
]) {
  test('29-item responsive reference ' + example.topic + ' retains preview, selection and explanation across refresh', async ({ page }, info) => {
    if (example.topic === 'cnm_198') {
      const topic = topics.find(topic => topic.id === example.topic);
      expect(topic.diagnostic_question.question).toBe(example.item.question.prompt);
      await page.goto(siteURL('/#' + example.topic));
      await expect(page).toHaveTitle(/中小学数学知识图谱/);
      await expect(page.locator('#main .title')).toHaveText(topic.name);
      await expect(page.locator('#main .q > div')).toHaveText(example.item.question.prompt);
      await activate(page, page.locator('#main details.ans > summary'));
      await expect(page.locator('#main details.ans > div')).toHaveText(topic.diagnostic_question.answer);
      await expect(page.locator('#main details.ans > div')).toBeVisible();
      await noHorizontalOverflow(page);
      await page.reload();
      await expect(page.locator('#main .q > div')).toHaveText(example.item.question.prompt);
      await activate(page, page.locator('#main details.ans > summary'));
      await expect(page.locator('#main details.ans > div')).toHaveText(topic.diagnostic_question.answer);
      await expect(page.locator('#main details.ans > div')).toBeVisible();
      await noHorizontalOverflow(page);
    }
    await reviewedChoiceAfterRefresh(page, example);
    if (example.topic === 'cnm_244') {
      await expect(page.locator('#explain')).toContainText('0°、180°及整周');
      await expect(page.locator('#explain')).toContainText('另一种充分信息');
    }
    if (info.project.name === 'phone' || info.project.name === 'webkit-tablet') {
      await page.locator('.verdict').scrollIntoViewIfNeeded();
      await page.screenshot({ path: '/tmp/cnm-review-29/' + example.topic + '-' + info.project.name + '-feedback.png' });
    }
  });
}
