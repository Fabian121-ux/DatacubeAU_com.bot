import { spawn } from 'node:child_process';
import process from 'node:process';

const chromePath = process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const url = process.env.ADMIN_UI_URL || 'http://127.0.0.1:8765/admin.html';
const port = Number(process.env.CHROME_DEBUG_PORT || (9223 + Math.floor(Math.random() * 1000)));
const widths = (process.env.VIEWPORTS || '320,360,375,390,414,768,1024,1280,1440')
  .split(',')
  .map(v => Number(v.trim()))
  .filter(Boolean);

if (typeof WebSocket === 'undefined') {
  throw new Error('Node WebSocket client is unavailable. Use Node 22+.');
}

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

async function fetchJson(path, opts) {
  const res = await fetch(`http://127.0.0.1:${port}${path}`, opts);
  if (!res.ok) throw new Error(`${path} returned ${res.status}`);
  return res.json();
}

async function waitForChrome() {
  const deadline = Date.now() + 10000;
  let lastError;
  while (Date.now() < deadline) {
    try {
      return await fetchJson('/json/version');
    } catch (err) {
      lastError = err;
      await sleep(150);
    }
  }
  throw lastError || new Error('Chrome did not start');
}

class Cdp {
  constructor(wsUrl) {
    this.wsUrl = wsUrl;
    this.id = 0;
    this.pending = new Map();
    this.waiters = new Map();
  }

  connect() {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(this.wsUrl);
      this.ws.onopen = () => resolve();
      this.ws.onerror = err => reject(err);
      this.ws.onmessage = event => this.onMessage(JSON.parse(event.data));
    });
  }

  onMessage(message) {
    if (message.id && this.pending.has(message.id)) {
      const { resolve, reject } = this.pending.get(message.id);
      this.pending.delete(message.id);
      if (message.error) reject(new Error(message.error.message || JSON.stringify(message.error)));
      else resolve(message.result || {});
      return;
    }
    const list = this.waiters.get(message.method);
    if (!list) return;
    while (list.length) list.shift()(message.params || {});
  }

  send(method, params = {}) {
    const id = ++this.id;
    this.ws.send(JSON.stringify({ id, method, params }));
    return new Promise((resolve, reject) => this.pending.set(id, { resolve, reject }));
  }

  waitFor(method, timeoutMs = 10000) {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error(`Timed out waiting for ${method}`)), timeoutMs);
      const resolver = params => {
        clearTimeout(timer);
        resolve(params);
      };
      if (!this.waiters.has(method)) this.waiters.set(method, []);
      this.waiters.get(method).push(resolver);
    });
  }

  close() {
    this.ws.close();
  }
}

async function evaluate(cdp, expression) {
  const result = await cdp.send('Runtime.evaluate', {
    expression,
    awaitPromise: true,
    returnByValue: true
  });
  if (result.exceptionDetails) {
    const details = result.exceptionDetails.exception?.description || result.exceptionDetails.text || 'Runtime.evaluate failed';
    throw new Error(details);
  }
  return result.result.value;
}

async function waitForExpression(cdp, expression, timeoutMs = 5000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      if (await evaluate(cdp, expression)) return;
    } catch (_) {}
    await sleep(100);
  }
  throw new Error(`Timed out waiting for ${expression}`);
}

async function navigate(cdp, targetUrl) {
  await cdp.send('Page.enable');
  await cdp.send('Runtime.enable');
  await cdp.send('Page.navigate', { url: targetUrl });
  await waitForExpression(cdp, `typeof window.activateTab === 'function' && typeof window.zinaAdminResponsiveCheck === 'function'`, 8000);
  await sleep(150);
}

async function stubNetwork(cdp) {
  await cdp.send('Page.addScriptToEvaluateOnNewDocument', {
    source: `
      window.fetch = async () => new Response(JSON.stringify({
        items: [],
        data: [],
        content: '',
        analytics: {},
        username: 'responsive-test',
        last_login: null,
        database: 'ok',
        waha: 'WORKING',
        ai_enabled: true,
        environment: 'responsive-test',
        today: { messages: 0, ai_calls: 0, total_tokens: 0 },
        totals: {
          contacts: 0,
          memory_entries: 0,
          conversation_timeline_entries: 0,
          conversation_summaries: 0,
          cache_entries: 0
        }
      }), { status: 200, headers: { 'content-type': 'application/json' } });
    `
  });
}

function stressScript() {
  return `
    (() => {
      const row = '<table><thead><tr><th>Name</th><th>Identifier</th><th>Description</th><th>Status</th><th>Actions</th></tr></thead><tbody>' +
        '<tr><td>Very Long Human Readable Record Name Used For Layout Testing</td><td><code>2348000000000-very-long-chat-id@g.us/participant/alternate-lid-identifier-that-must-wrap</code></td><td>Natural text should wrap cleanly across multiple lines without forcing the page wider than the viewport. This includes FAQ answers, memory text, log messages, filenames, URLs, and error details.</td><td><span class="badge badge-green">Enabled and synchronized</span></td><td><button class="btn btn-ghost btn-sm">View</button> <button class="btn btn-danger btn-sm">Disable</button></td></tr>' +
        '</tbody></table>';
      document.querySelectorAll('.tbl-wrap').forEach(el => {
        if (!el.querySelector('table')) el.innerHTML = row;
      });
      if (window.enhanceResponsiveTables) window.enhanceResponsiveTables(document);
    })()
  `;
}

async function collect(cdp, tab, width) {
  await evaluate(cdp, `activateTab(${JSON.stringify(tab)}, { push: false })`);
  await sleep(60);
  await evaluate(cdp, stressScript());
  return evaluate(cdp, `(() => {
    const report = window.zinaAdminResponsiveCheck ? window.zinaAdminResponsiveCheck() : {
      viewport: document.documentElement.clientWidth,
      documentWidth: document.documentElement.scrollWidth,
      bodyWidth: document.body.scrollWidth,
      hasHorizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
      offenders: []
    };
    const panel = document.querySelector('.panel.active');
    const navToggle = document.getElementById('navToggle');
    return {
      width: ${width},
      tab: ${JSON.stringify(tab)},
      ...report,
      activePanel: panel ? panel.id : null,
      tableCellsWithLabels: document.querySelectorAll('.panel.active .tbl-wrap td[data-label]').length,
      navToggleVisible: navToggle ? getComputedStyle(navToggle).display !== 'none' : false
    };
  })()`);
}

async function testMobileNav(cdp) {
  return evaluate(cdp, `(async () => {
    const toggle = document.getElementById('navToggle');
    const sidebar = document.getElementById('adminSidebar');
    const overlay = document.getElementById('navOverlay');
    if (!toggle || getComputedStyle(toggle).display === 'none') return { skipped: true };
    toggle.click();
    await new Promise(resolve => setTimeout(resolve, 320));
    const wasOpen = document.body.classList.contains('nav-open');
    const openReport = window.zinaAdminResponsiveCheck();
    const openRect = sidebar.getBoundingClientRect();
    overlay.click();
    await new Promise(resolve => setTimeout(resolve, 320));
    return {
      skipped: false,
      opened: wasOpen && openRect.left >= -1 && openRect.right <= document.documentElement.clientWidth + 1,
      closed: !document.body.classList.contains('nav-open'),
      openReport
    };
  })()`);
}

const chrome = spawn(chromePath, [
  '--headless=new',
  `--remote-debugging-port=${port}`,
  `--user-data-dir=/private/tmp/zina-admin-responsive-${Date.now()}`,
  '--no-first-run',
  '--disable-gpu',
  '--hide-scrollbars',
  'about:blank'
], { stdio: ['ignore', 'pipe', 'pipe'] });

let exitCode = 0;
try {
  await waitForChrome();
  const target = await fetchJson(`/json/new?${encodeURIComponent('about:blank')}`, { method: 'PUT' });
  const cdp = new Cdp(target.webSocketDebuggerUrl);
  await cdp.connect();
  await stubNetwork(cdp);
  const failures = [];
  const results = [];

  for (const width of widths) {
    await cdp.send('Emulation.setDeviceMetricsOverride', {
      width,
      height: 1200,
      deviceScaleFactor: 1,
      mobile: width <= 760
    });
    await navigate(cdp, url + '#status');
    await evaluate(cdp, stressScript());
    const tabs = await evaluate(cdp, `Array.from(document.querySelectorAll('#nav button[data-tab]')).map(btn => btn.dataset.tab)`);
    for (const tab of tabs) {
      const result = await collect(cdp, tab, width);
      results.push(result);
      if (result.hasHorizontalOverflow || result.offenders.length) {
        failures.push(result);
      }
    }
    const nav = await testMobileNav(cdp);
    if (!nav.skipped && (!nav.opened || !nav.closed || nav.openReport.hasHorizontalOverflow || nav.openReport.offenders.length)) {
      failures.push({ width, tab: 'mobile-nav', ...nav.openReport, nav });
    }
  }

  cdp.close();
  const summary = {
    url,
    widths,
    tabsTested: [...new Set(results.map(r => r.tab))],
    checks: results.length,
    failures: failures.length,
    firstFailures: failures.slice(0, 5)
  };
  console.log(JSON.stringify(summary, null, 2));
  if (failures.length) exitCode = 1;
} finally {
  chrome.kill();
}

process.exit(exitCode);
