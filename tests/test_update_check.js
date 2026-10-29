'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../update-check.js'), 'utf8');
const OLD = 'a'.repeat(40), NEW = 'b'.repeat(40);

async function run(options = {}) {
  const elements = new Map(), documentEvents = {}, windowEvents = {}, requests = [], redirects = [], dispatched = [];
  const createElement = () => ({
    style: {}, children: [], events: {}, setAttribute() {},
    addEventListener(name, handler) { this.events[name] = handler; },
    append(...children) { this.children.push(...children); }
  });
  const document = {
    querySelector(selector) {
      if (selector === 'meta[name="app-version"]') return { content: options.current || OLD };
      if (selector === 'meta[name="app-update-policy"]' && options.policy) return { content: options.policy };
      return null;
    },
    currentScript: { src: 'https://example.test/cn-math-taxonomy-QD/update-check.js?v=' + OLD },
    hidden: false, createElement,
    addEventListener(name, handler) { documentEvents[name] = handler; },
    getElementById: id => elements.get(id),
    body: { append(element) { elements.set(element.id, element); } }
  };
  const window = {
    addEventListener(name, handler) { windowEvents[name] = handler; },
    dispatchEvent(event) { dispatched.push(event.type); }
  };
  if (options.earlyTracker !== false) window.__cnmPageInteracted = !!options.interactedBeforeLoad;
  const location = {
    href: options.url || 'https://example.test/cn-math-taxonomy-QD/?target=cnm_221&seed=fixed#path',
    replace(url) { redirects.push(url); }
  };
  const context = {
    URL, AbortController, Event, setTimeout, clearTimeout, document, window, location,
    async fetch(url, config) {
      requests.push({ url, config });
      if (options.interact) documentEvents.input();
      if (options.offline) throw new Error('offline');
      return { ok: options.ok !== false, json: async () => ({ version: options.latest || NEW }) };
    }
  };
  vm.runInNewContext(source, context);
  await new Promise(resolve => setImmediate(resolve));
  return { elements, requests, redirects, documentEvents, windowEvents, location, dispatched };
}

(async function () {
  const outdated = await run();
  assert.equal(outdated.redirects.length, 1);
  assert.deepEqual(outdated.dispatched, ['cnm:before-update']);
  const next = new URL(outdated.redirects[0]);
  assert.equal(next.searchParams.get('_v'), NEW);
  assert.equal(next.searchParams.get('target'), 'cnm_221');
  assert.equal(next.searchParams.get('seed'), 'fixed');
  assert.equal(next.hash, '#path');
  assert.equal(new URL(outdated.requests[0].url).pathname, '/cn-math-taxonomy-QD/version.json');
  assert(new URL(outdated.requests[0].url).searchParams.has('check'));
  assert.equal(outdated.requests[0].config.cache, 'no-store');
  console.log('ok untouched browse page reloads once, bypasses cache, preserves route/parameters/hash');

  for (const options of [{ interact: true }, { interactedBeforeLoad: true }, { earlyTracker: false }]) {
    const active = await run(options);
    assert.equal(active.redirects.length, 0);
    const notice = active.elements.get('release-update');
    assert(notice);
    active.location.href = 'https://example.test/cn-math-taxonomy-QD/?q=changed#cnm_222';
    notice.children[1].events.click();
    assert.equal(active.redirects.length, 1);
    assert.deepEqual(active.dispatched, ['cnm:before-update']);
    const clicked = new URL(active.redirects[0]);
    assert.equal(clicked.searchParams.get('q'), 'changed');
    assert.equal(clicked.hash, '#cnm_222');
    assert.equal(clicked.searchParams.get('_v'), NEW);
  }
  console.log('ok input before/during checker load and legacy untracked pages prompt, retaining the latest navigation');

  for (const options of [
    { policy: 'prompt' },
    { url: 'https://example.test/cn-math-taxonomy-QD/diagnose/?target=cnm_221' },
    { url: 'https://example.test/cn-math-taxonomy-QD/diagnose/index.html?target=cnm_221', earlyTracker: false }
  ]) {
    const diagnosis = await run(options);
    assert.equal(diagnosis.redirects.length, 0);
    assert(diagnosis.elements.has('release-update'));
  }
  console.log('ok diagnosis and explicit prompt-policy pages never refresh automatically');

  const retried = await run({ url: 'https://example.test/cn-math-taxonomy-QD/?_v=' + NEW });
  assert.equal(retried.redirects.length, 0);
  assert(retried.elements.has('release-update'));
  console.log('ok stale versioned HTML does not enter a reload loop');

  for (const options of [{ latest: OLD }, { offline: true }, { ok: false }, { latest: 'invalid' }]) {
    const result = await run(options);
    assert.equal(result.redirects.length, 0);
    assert.equal(result.elements.size, 0);
  }
  const development = await run({ current: 'development' });
  assert.equal(development.requests.length, 0);
  console.log('ok current release, offline/error responses, malformed metadata and local development do not interrupt the app');
})().catch(error => { console.error(error); process.exitCode = 1; });
