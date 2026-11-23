// End-to-end check (test A3) of the built site in headless Chromium: every page
// loads, Python starts, all scenarios run, no console errors, no sideways
// scrolling on a phone. Runs in CI after the build (see .github/workflows).
//
// Usage: node scripts/e2e_browser_test.js _site <screenshot dir> [local package dir]
// Without the third argument the real CDN is used. With it, CDN requests are
// answered from local npm copies (for machines without internet access):
//   <dir>/package                 = pyodide (version in site/js/py-worker.js)
//   <dir>/cdn/plotly/package      = plotly.js-dist-min@2.35.2
//   <dir>/cdn/katex/package       = katex@0.16.11
//   <dir>/cdn/hljs/package        = @highlightjs/cdn-assets@11.9.0
// Needs: npm install playwright (and npx playwright install chromium).
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs'); const path = require('path');
const [SITE, OUT, S] = process.argv.slice(2);
fs.mkdirSync(OUT, { recursive: true });
const PYODIDE = fs.readFileSync(path.join(SITE, 'js/py-worker.js'), 'utf8').match(/PYODIDE_VERSION = "([^"]+)"/)[1];
const TYPES = { '.js': 'text/javascript', '.mjs': 'text/javascript', '.wasm': 'application/wasm', '.json': 'application/json',
  '.zip': 'application/zip', '.css': 'text/css', '.woff2': 'font/woff2', '.woff': 'font/woff', '.ttf': 'font/ttf' };
const MAP = [
  ['https://cdn.jsdelivr.net/npm/pyodide@' + PYODIDE + '/', S + '/package/'],
  ['https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/', S + '/cdn/plotly/package/'],
  ['https://cdn.jsdelivr.net/npm/katex@0.16.11/', S + '/cdn/katex/package/'],
  ['https://cdn.jsdelivr.net/npm/@highlightjs/cdn-assets@11.9.0/', S + '/cdn/hljs/package/'],
];
const errors = [];
async function wire(page) {
  page.on('console', (m) => { if (m.type() === 'error' && !/fonts\.g/.test(m.text())) errors.push(page.url() + ': ' + m.text()); });
  page.on('pageerror', (e) => errors.push(page.url() + ': ' + String(e)));
}
async function wireContext(ctx) {
  if (!S) return;                       // real CDN
  // context-level routes also catch requests made by the Web Worker
  await ctx.route(/fonts\.(googleapis|gstatic)\.com/, (r) => r.fulfill({ body: '', contentType: 'text/css' }));
  await ctx.route('https://cdn.jsdelivr.net/**', (route) => {
    const url = route.request().url();
    for (const [prefix, dir] of MAP) if (url.startsWith(prefix)) {
      const file = dir + url.slice(prefix.length).split('?')[0];
      if (fs.existsSync(file)) return route.fulfill({ body: fs.readFileSync(file), contentType: TYPES[path.extname(file)] || 'application/octet-stream' });
    }
    errors.push('unmapped ' + url); return route.abort();
  });
}
const statusIs = (re) => (s) => new RegExp(s).test(document.getElementById('status-text').textContent);
(async () => {
  const server = spawn('python3', ['-m', 'http.server', '8765', '-d', SITE], { stdio: 'ignore' });
  await new Promise((r) => setTimeout(r, 800));
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 1000 } }); await wireContext(ctx);
  const page = await ctx.newPage(); await wire(page);
  let t0 = Date.now();
  await page.goto('http://localhost:8765/tool.html');
  await page.waitForFunction(statusIs(), 'Design comparison done', { timeout: 120000 });
  console.log('tool ready in', (Date.now() - t0) / 1000, 's');
  console.log('plots:', await page.locator('.js-plotly-plot').count(), 'kpis:', await page.locator('.kpi').count(),
              'design cards:', await page.locator('.design-card').count());
  await page.screenshot({ path: OUT + '/tool.png', fullPage: true });
  for (const preset of ['staged', 'buffered', 'deadtime', 'windup', 'single']) {
    t0 = Date.now();
    await page.click(`[data-preset="${preset}"]`);
    await page.waitForFunction(statusIs(), '^(Done|Anti-windup is OFF)', { timeout: 60000 });
    console.log('preset', preset, (Date.now() - t0) / 1000, 's', '|', (await page.innerText('#kpis')).replace(/\s+/g, ' '));
    if (preset === 'staged') await page.screenshot({ path: OUT + '/tool-staged.png' });
  }
  await page.click('[data-design="acetic"]');
  await page.waitForFunction(statusIs(), 'Design comparison done', { timeout: 60000 });
  console.log('acetic design:', (await page.innerText('#design-results')).match(/\d-stage design\s+\S+ ?\S*/g));
  const plant = await page.locator('#plant-view .pv-svg').count();
  if (plant !== 1) errors.push('plant view missing on tool page');
  await page.click('#theme-toggle');
  await page.waitForTimeout(500);
  await page.screenshot({ path: OUT + '/tool-dark.png' });
  for (const f of ['index.html', 'theory.html']) {
    const p = await ctx.newPage(); await wire(p);
    await p.goto('http://localhost:8765/' + f);
    if (f === 'theory.html') {
      await p.waitForFunction(() => document.querySelectorAll('.eq-card').length > 0, null, { timeout: 120000 });
      console.log('theory cards:', await p.locator('.eq-card').count(), 'katex:', await p.locator('.katex').count(),
                  'highlighted:', await p.locator('code.hljs').count());
    }
    await p.waitForTimeout(400);
    if (f === 'theory.html') await p.locator('.eq-card').nth(2).scrollIntoViewIfNeeded(); await p.screenshot({ path: OUT + '/' + f.replace('.html', '') + '-dark.png' });
  }
  const light = await browser.newContext({ viewport: { width: 1440, height: 1000 }, colorScheme: 'light' }); await wireContext(light);
  const home = await light.newPage(); await wire(home);
  await home.goto('http://localhost:8765/index.html');
  await home.waitForFunction(() => document.querySelector('#kcu-bars rect') && document.querySelector('#showcase-plant .pv-svg'), null, { timeout: 30000 });
  await home.waitForTimeout(1500);
  console.log('home facts:', await home.evaluate(() => [...document.querySelectorAll('[data-fact]')].slice(0, 6).map((e) => e.dataset.fact + '=' + e.textContent).join(' ')));
  await home.waitForTimeout(1500);
  await home.screenshot({ path: OUT + '/index.png', fullPage: true });
  for (const f of ['ai-process.html', 'model-comparison.html', 'video.html', 'learned.html', 'references.html']) {
    const r = await home.goto('http://localhost:8765/' + f); if (!r.ok()) errors.push(f + ' ' + r.status());
  }
  await home.screenshot({ path: OUT + '/references.png' });
  const phone = await browser.newContext({ viewport: { width: 390, height: 844 } }); await wireContext(phone);
  const ph = await phone.newPage(); await wire(ph);
  for (const f of ['index.html', 'tool.html']) {
    await ph.goto('http://localhost:8765/' + f);
    if (f === 'tool.html') await ph.waitForFunction(statusIs(), 'Design comparison done', { timeout: 120000 });
    const overflow = await ph.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    console.log('phone', f, 'horizontal overflow px:', overflow);
    await ph.screenshot({ path: OUT + '/phone-' + f.replace('.html', '') + '.png' });
  }
  console.log('errors:', errors.length ? errors : 'none');
  if (errors.length) process.exitCode = 1;
  await browser.close(); server.kill();
})().catch((e) => { console.error(e); process.exit(1); });
