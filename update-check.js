/* Check the deployed release, even when the browser restored an older HTML page. */
(function () {
  'use strict';
  const current = document.querySelector('meta[name="app-version"]').content;
  if (current === 'development') return;
  const manifest = new URL('version.json', document.currentScript.src);
  const policy = document.querySelector('meta[name="app-update-policy"]');
  const promptOnly = (policy && policy.content === 'prompt') || /\/diagnose(?:\/|\/index\.html)?$/.test(new URL(location.href).pathname);
  // Old HTML may not have the early tracker: prompting is safer than guessing
  // whether somebody typed an answer before this deferred script arrived.
  const earlyTracking = typeof window.__cnmPageInteracted === 'boolean';
  let interacted = window.__cnmPageInteracted === true;
  let checking = false;
  let lastCheck = 0;
  let pendingVersion = null;
  ['pointerdown', 'keydown', 'input'].forEach(function (event) {
    document.addEventListener(event, function () { interacted = true; }, { once: true, capture: true });
  });

  function updateUrl(version) {
    const url = new URL(location.href);
    url.searchParams.set('_v', version);
    return url;
  }

  function reloadVersion(version) {
    window.dispatchEvent(new Event('cnm:before-update'));
    location.replace(updateUrl(version).href);
  }

  function offerUpdate(version) {
    pendingVersion = version;
    if (document.getElementById('release-update')) return;
    const notice = document.createElement('aside');
    notice.id = 'release-update';
    notice.setAttribute('role', 'status');
    notice.style.cssText = 'position:fixed;z-index:10;top:max(12px,env(safe-area-inset-top));left:12px;right:12px;margin:auto;max-width:560px;padding:12px 16px;background:#fff;color:#1f2933;border:2px solid #2563eb;border-radius:10px;box-shadow:0 4px 24px #1e293b26;display:flex;align-items:center;gap:12px;font:15px/1.6 -apple-system,sans-serif';
    const text = document.createElement('span');
    text.textContent = '发现新版本，完成当前操作后可更新页面。';
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = '更新页面';
    button.style.cssText = 'flex-shrink:0;min-height:44px;padding:8px 12px;border:0;border-radius:6px;background:#2563eb;color:#fff;font:inherit;cursor:pointer';
    // Keep any topic/URL changes made after the banner first appeared.
    button.addEventListener('click', function () { reloadVersion(pendingVersion); });
    notice.append(text, button);
    document.body.append(notice);
  }

  async function check(allowReload) {
    if (checking || (lastCheck && Date.now() - lastCheck < 15000)) return;
    checking = true;
    lastCheck = Date.now();
    const controller = new AbortController();
    const timeout = setTimeout(function () { controller.abort(); }, 5000);
    try {
      const request = new URL(manifest);
      request.searchParams.set('check', String(Date.now()));
      const response = await fetch(request.href, { cache: 'no-store', signal: controller.signal });
      if (!response.ok) return;
      const latest = (await response.json()).version;
      if (!/^[a-f0-9]{40}$/.test(latest) || latest === current) return;
      const url = new URL(location.href);
      // A versioned URL already served old HTML: wait for propagation, never loop.
      const alreadyRetried = url.searchParams.get('_v') === latest;
      if (allowReload && !promptOnly && earlyTracking && !interacted && !window.__cnmPageInteracted && !alreadyRetried) reloadVersion(latest);
      else offerUpdate(latest);
    } catch (e) { /* Offline or a failed version check must not block the app. */ }
    finally { clearTimeout(timeout); checking = false; }
  }

  check(true);
  window.addEventListener('pageshow', function (event) { if (event.persisted) check(false); });
  document.addEventListener('visibilitychange', function () { if (!document.hidden) check(false); });
})();
