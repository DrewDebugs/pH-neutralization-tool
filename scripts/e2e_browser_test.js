// Optional end-to-end check (test A3) of the built site in headless Chromium.
// Usage: node scripts/e2e_browser_test.js <dir with npm packages> _site <screenshot dir>
// CDN requests are answered from local npm copies (pyodide@0.29.5 unpacked to
// <dir>/package, plotly and katex to <dir>/cdn/{plotly,katex}/package), so the
// test also works without internet access. Needs: npm install playwright.
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs'); const path = require('path');
const S = process.argv[2], SITE = process.argv[3], OUT = process.argv[4];
const TYPES = { '.js': 'text/javascript', '.mjs': 'text/javascript', '.wasm': 'application/wasm',
  '.json': 'application/json', '.zip': 'application/zip', '.css': 'text/css', '.woff2': 'font/woff2', '.ttf': 'font/ttf', '.woff': 'font/woff' };
const MAP = [
  ['https://cdn.jsdelivr.net/npm/pyodide@0.29.5/', S + '/package/'],
  ['https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/', S + '/cdn/plotly/package/'],
  ['https://cdn.jsdelivr.net/npm/katex@0.16.11/', S + '/cdn/katex/package/'],
];
(async () => {
  const server = spawn('python3', ['-m', 'http.server', '8765', '-d', SITE], { stdio: 'ignore' });
  await new Promise(r => setTimeout(r, 800));
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 }, deviceScaleFactor: 1 });
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push(String(e)));
  await page.route('https://cdn.jsdelivr.net/**', route => {
    const url = route.request().url();
    for (const [prefix, dir] of MAP) if (url.startsWith(prefix)) {
      const file = dir + url.slice(prefix.length).split('?')[0];
      if (fs.existsSync(file)) return route.fulfill({ body: fs.readFileSync(file), contentType: TYPES[path.extname(file)] || 'application/octet-stream' });
    }
    errors.push('unmapped ' + url); return route.abort();
  });
  let t0 = Date.now();
  await page.goto('http://localhost:8765/tool.html');
  await page.waitForFunction(() => document.getElementById('status').textContent.includes('Design comparison done'), null, { timeout: 120000 });
  console.log('tool ready in', (Date.now() - t0) / 1000, 's; status:', await page.textContent('#status'));
  console.log('plots drawn:', await page.locator('.js-plotly-plot').count());
  console.log('design cards:', await page.locator('#design-results .card').count());
  console.log(await page.innerText('#stage-analysis'));
  await page.screenshot({ path: OUT + '/tool.png', fullPage: true });
  // two stages + auto-tune
  await page.selectOption('[data-path="n_stages"]', '2');
  await page.fill('[data-path="stages.0.SP"]', '4');
  t0 = Date.now();
  await page.click('#autotune');
  await page.waitForFunction(() => document.getElementById('status').textContent.startsWith('Done'), null, { timeout: 60000 });
  console.log('2-stage autotune run', (Date.now() - t0) / 1000, 's');
  console.log(await page.innerText('#stage-analysis'));
  await page.screenshot({ path: OUT + '/tool-2stage.png', fullPage: false });
  const p2 = await browser.newPage({ viewport: { width: 1300, height: 900 } });
  p2.on('pageerror', e => errors.push(String(e)));
  await p2.route('https://cdn.jsdelivr.net/**', route => {
    const url = route.request().url();
    for (const [prefix, dir] of MAP) if (url.startsWith(prefix)) {
      const file = dir + url.slice(prefix.length).split('?')[0];
      if (fs.existsSync(file)) return route.fulfill({ body: fs.readFileSync(file), contentType: TYPES[path.extname(file)] || 'application/octet-stream' });
    }
    errors.push('unmapped ' + url); return route.abort();
  });
  await p2.goto('http://localhost:8765/theory.html');
  await p2.waitForFunction(() => document.querySelectorAll('#equations .card').length > 0, null, { timeout: 120000 });
  console.log('theory cards:', await p2.locator('#equations .card').count(), 'katex:', await p2.locator('.katex').count());
  await p2.screenshot({ path: OUT + '/theory.png' });
  for (const f of ['index.html','ai-process.html','model-comparison.html','video.html','learned.html','references.html']) {
    const r = await p2.goto('http://localhost:8765/' + f); if (!r.ok()) errors.push(f + ' ' + r.status());
  }
  console.log('errors:', errors.length ? errors : 'none');
  await browser.close(); server.kill();
})().catch(e => { console.error(e); process.exit(1); });
