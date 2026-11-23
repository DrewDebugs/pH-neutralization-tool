// Home page graphics. All numbers come from data/showcase.json, which
// scripts/build_site.py computes with the Python model (api.py) at build time.

const $id = (id) => document.getElementById(id);

function sci(x) {
  const e = Math.floor(Math.log10(x));
  const m = x / 10 ** e;
  return `${m.toFixed(1)}×10<sup>${e}</sup>`;
}

// ---------------------------------------------------------- the beaker
function setupBeaker(tit) {
  const slider = $id("bk-slider");
  const W = 300, H = 150, xMax = 2 * tit.r_eq;
  const X = (r) => 10 + (W - 20) * r / xMax;
  const Y = (p) => H - 10 - (H - 20) * p / 14;
  const curve = tit.ratio.filter((r) => r <= xMax)
    .map((r, i) => `${i ? "L" : "M"}${X(r).toFixed(1)} ${Y(tit.pH[i]).toFixed(1)}`).join(" ");
  $id("bk-curve").setAttribute("d", curve);
  $id("bk-eq").setAttribute("x1", X(tit.r_eq)); $id("bk-eq").setAttribute("x2", X(tit.r_eq));

  let lastDrop = 0;
  function update(fromUser) {
    const pct = Number(slider.value);
    const r = pct / 100 * tit.r_eq;
    const pH = interp(r, tit.ratio, tit.pH);
    const gain = Math.exp(interp(pH, tit.gain_pH, tit.gain.map(Math.log)));
    const col = phColor(pH);
    $id("bk-liq").setAttribute("fill", col);
    $id("bk-wave").setAttribute("fill", col);
    $id("bk-ph").textContent = pH.toFixed(2);
    $id("bk-ph").style.color = col;
    $id("bk-pct").textContent = pct + "%";
    $id("bk-h").innerHTML = sci(10 ** -pH) + " M";
    $id("bk-gain").innerHTML = gain >= 1000 ? Math.round(gain).toLocaleString("en-US") : gain.toPrecision(3);
    $id("bk-marker").setAttribute("transform", `translate(0, ${(14 - pH) / 14 * 220})`);
    $id("bk-dot").setAttribute("cx", X(r)); $id("bk-dot").setAttribute("cy", Y(pH));
    $id("bk-dot").setAttribute("fill", col);
    slider.style.setProperty("--fill", pct / 2 + "%");
    const msg = pH < 6 ? "Still acidic: most of the acid is not yet neutralized."
      : pH <= 8 ? "The cliff: a tiny bit more caustic swings pH by whole units."
      : "Overshoot: now the excess is caustic.";
    $id("bk-msg").textContent = msg;
    if (fromUser && performance.now() - lastDrop > 140) { lastDrop = performance.now(); drop(col); }
  }
  function drop() {
    const d = document.createElementNS("http://www.w3.org/2000/svg", "path");
    d.setAttribute("d", "M150 40 q-6 9 0 13 q6 -4 0 -13z");
    d.setAttribute("class", "bk-drop");
    $id("bk-drops").appendChild(d);
    setTimeout(() => d.remove(), 700);
  }
  slider.addEventListener("input", () => update(true));
  update(false);
}

// ------------------------------------------------------ the "cliff" chart
function setupCliff(tit) {
  const svg = $id("cliff-svg");
  if (!svg) return;
  const W = 320, H = 170, x0 = 0.9 * tit.r_eq, x1 = 1.1 * tit.r_eq;
  const X = (r) => 12 + (W - 24) * (r - x0) / (x1 - x0);
  const Y = (p) => H - 12 - (H - 24) * p / 14;
  const pts = tit.ratio.map((r, i) => [r, tit.pH[i]]).filter(([r]) => r >= x0 && r <= x1);
  $id("cliff-path").setAttribute("d", pts.map(([r, p], i) => `${i ? "L" : "M"}${X(r).toFixed(1)} ${Y(p).toFixed(1)}`).join(" "));
  $id("cliff-band").setAttribute("y", Y(8)); $id("cliff-band").setAttribute("height", Y(6) - Y(8));
}

// ----------------------------------------------------- plant showcase
function setupShowcase(data) {
  const el = $id("showcase-plant");
  const sets = {
    single: Object.assign({}, data.single, { influent: 2.0 }),
    staged: Object.assign({}, data.staged, { influent: 2.0 }),
  };
  const view = createPlantView(el, sets.single, { seconds: 16 });
  const captions = {
    single: "One tank, set point pH 7, tuned by Ziegler–Nichols: the loop limit-cycles between pH 3.5 and 10.3. The effluent is out of spec most of the time.",
    staged: "Two stages: 1 M caustic to pH 4, then 0.01 M caustic to pH 7. Same disturbances; the effluent stays between pH 6.3 and 7.8.",
  };
  document.querySelectorAll("[data-show]").forEach((b) => b.addEventListener("click", () => {
    document.querySelectorAll("[data-show]").forEach((o) => o.setAttribute("aria-pressed", String(o === b)));
    view.setData(sets[b.dataset.show]);
    $id("showcase-caption").textContent = captions[b.dataset.show];
    view.play();
  }));
  $id("showcase-caption").textContent = captions.single;
  // start playing when the section scrolls into view
  if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches && "IntersectionObserver" in window) {
    const io = new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting)) { view.play(); io.disconnect(); }
    }, { threshold: 0.35 });
    io.observe(el);
  }
}

// --------------------------------------------------------- count-up stats
function countUp() {
  const els = document.querySelectorAll("[data-count]");
  const run = (el) => {
    const target = Number(el.dataset.count), decimals = Number(el.dataset.decimals || 0);
    const t0 = performance.now(), dur = 1200;
    const step = (ts) => {
      const f = Math.min(1, (ts - t0) / dur), e = 1 - (1 - f) ** 3;
      el.textContent = (target * e).toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
      if (f < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  };
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches || !("IntersectionObserver" in window)) return;
  const io = new IntersectionObserver((entries) => entries.forEach((e) => {
    if (e.isIntersecting) { run(e.target); io.unobserve(e.target); }
  }), { threshold: 0.6 });
  els.forEach((el) => io.observe(el));
}

(async () => {
  countUp();
  const data = await (await fetch("data/showcase.json")).json();
  setupBeaker(data.titration);
  setupCliff(data.titration);
  setupShowcase(data);
})().catch((err) => console.error(err));
