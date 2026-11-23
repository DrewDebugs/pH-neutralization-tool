// Tool page: builds the input form, sends the inputs to Python (api.py),
// and draws the results with Plotly. No engineering is done here: every
// number shown comes from the Python model.

let DEFAULTS = null;
let LAST = null;          // last results, so plots can be redrawn on theme change
let PLANT = null;         // the animated plant view
const $ = (id) => document.getElementById(id);

function setStatus(text, busy = false) {
  $("status-text").textContent = text;
  $("status").classList.toggle("busy", busy);
}

// ---------------------------------------------------------------- helpers
function getPath(obj, path) {
  return path.split(".").reduce((o, k) => (o == null ? undefined : o[k]), obj);
}
function setPath(obj, path, value) {
  const keys = path.split(".");
  let o = obj;
  keys.slice(0, -1).forEach((k, i) => {
    if (o[k] == null) o[k] = /^\d+$/.test(keys[i + 1]) ? [] : {};
    o = o[k];
  });
  o[keys[keys.length - 1]] = value;
}
function fmt(x, digits = 3) {
  if (x === null || x === undefined) return "∞";
  if (x === 0) return "0";
  const a = Math.abs(x);
  if (a >= 1e4 || a < 1e-3) {
    const [m, e] = x.toExponential(digits - 1).split("e");
    return `${m}×10<sup>${Number(e)}</sup>`;
  }
  return Number(x.toPrecision(digits)).toLocaleString("en-US");
}
const plain = (html) => html.replace(/<sup>(.*?)<\/sup>/g, "^$1").replace("×10^", "e");
function css(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}
function rgba(hex, alpha) {
  const n = parseInt(hex.replace("#", ""), 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${alpha})`;
}
const seriesColor = (k) => css(`--series-${k + 1}`);
const ICON_OK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12l5 5 9-10"/></svg>';
const ICON_FAIL = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>';
const badge = (ok, yes, no) => `<span class="badge ${ok ? "ok" : "fail"}">${ok ? ICON_OK : ICON_FAIL}${ok ? yes : no}</span>`;

function numberInput(path, value) {
  const v = value === null || value === undefined ? "" : value;
  return `<input type="number" step="any" data-path="${path}" value="${v}" aria-label="${path}">`;
}
function field(path, label, unit) {
  return `<label class="field"><span>${label} <span class="unit">${unit}</span></span>` +
         numberInput(path, getPath(DEFAULTS, path)) + `</label>`;
}
function group(title, body, open = true) {
  return `<details class="group" ${open ? "open" : ""}><summary><span class="dot"></span>${title}</summary>
    <div class="body">${body}</div></details>`;
}

// ------------------------------------------------------------- the forms
const STAGE_ROWS = [
  ["V", "Tank volume", "m³"], ["CR", "NaOH conc.", "mol/L"],
  ["FR_max", "Valve max flow", "m³/h"], ["SP", "Set point", "pH"],
  ["Kc", "Gain K<sub>c</sub>", "(m³/h)/pH"], ["tauI", "τ<sub>I</sub> (0 = P-only)", "s"],
];

function buildMainForm() {
  const swatch = (k) => `<span class="stage-swatch" style="background:var(--series-${k + 1})"></span>`;
  const stageTable = STAGE_ROWS.map(([key, label, unit]) =>
    `<tr><th>${label}<br><span class="unit">${unit}</span></th>` +
    [0, 1, 2].map((k) => `<td>${numberInput(`stages.${k}.${key}`, DEFAULTS.stages[k][key])}</td>`).join("") +
    `</tr>`).join("");
  const disturbanceRows = [0, 1, 2].map((k) => {
    const d = DEFAULTS.disturbances[k] || {};
    return `<tr>` + ["t", "F", "Ca", "Cw"].map((key) =>
      `<td>${numberInput(`disturbances.${k}.${key}`, d[key])}</td>`).join("") + `</tr>`;
  }).join("");

  $("inputs").innerHTML =
    group("Influent (acidic wastewater)",
      field("influent.F", "Flow", "m³/h") + field("influent.Ca", "HCl", "mol/L") +
      field("influent.Cw", "Acetic acid", "mol/L")) +
    group("Stages (tanks in series)", `
      <label class="field"><span>Number of stages</span>
        <select data-path="n_stages" aria-label="Number of stages">${[1, 2, 3].map((n) =>
          `<option ${n === DEFAULTS.n_stages ? "selected" : ""}>${n}</option>`).join("")}</select></label>
      <div class="scroll-x"><table class="grid">
        <tr><th></th>${[0, 1, 2].map((k) => `<th>${swatch(k)}Stage ${k + 1}</th>`).join("")}</tr>${stageTable}
      </table></div>
      <p class="hint">Each stage has its own NaOH valve and PI loop. Stage 1's volume and NaOH strength also drive the titration and stability plots.</p>`) +
    group("Instruments",
      field("instruments.tau_v", "Valve lag τ<sub>v</sub>", "s") +
      field("instruments.tau_m", "Probe lag τ<sub>m</sub>", "s") +
      field("instruments.theta", "Dead time θ", "s")) +
    group("Disturbances (step changes)", `
      <div class="scroll-x"><table class="grid">
        <tr><th>time<br><span class="unit">min</span></th><th>flow<br><span class="unit">m³/h</span></th>
            <th>HCl<br><span class="unit">mol/L</span></th><th>acetic<br><span class="unit">mol/L</span></th></tr>
        ${disturbanceRows}
      </table></div>
      <p class="hint">New values after each step. Blank cell = no change; blank time = row unused.</p>`) +
    group("Simulation", field("sim.t_end", "Duration", "min") + field("sim.dt", "Controller sample time", "s") +
      `<label class="field"><span>Anti-windup</span>
        <input type="checkbox" data-path="sim.anti_windup" ${DEFAULTS.sim.anti_windup ? "checked" : ""}></label>`);
}

function buildDesignForm() {
  const d = DEFAULTS.design;
  const designTables = ["1", "2", "3"].map((n) => {
    const rows = d.designs[n].map((s, j) => `<tr><td>${j + 1}</td>` +
      ["SP", "band_low", "band_high", "CR", "V"].map((key) =>
        `<td>${numberInput(`design.designs.${n}.${j}.${key}`, s[key])}</td>`).join("") + `</tr>`).join("");
    return `<p style="margin:12px 0 4px;font-weight:600">${n}-stage design</p><div class="scroll-x"><table class="grid">
      <tr><th>#</th><th>SP</th><th>band low</th><th>band high</th><th>NaOH <span class="unit">M</span></th><th>V <span class="unit">m³</span></th></tr>${rows}</table></div>`;
  }).join("");
  $("design-inputs").innerHTML =
    group("Influent range",
      field("design.F_min", "Flow min", "m³/h") + field("design.F_max", "Flow max", "m³/h") +
      field("design.Ca_min", "HCl min", "mol/L") + field("design.Ca_max", "HCl max", "mol/L") +
      field("design.Cw_min", "Acetic min", "mol/L") + field("design.Cw_max", "Acetic max", "mol/L")) +
    group("Valve capability (assumed)",
      field("design.valve_rangeability", "Rangeability", "max : min") +
      field("design.valve_resolution_pct", "Resolution", "% of max") +
      field("design.margin", "Sizing margin", "× max demand") +
      `<p class="hint">Replace these with your valve vendor's data.</p>`) +
    group("Stages of each design", designTables, false);
}

// Read every input back into one params object (starting from the defaults).
function readInputs(formId) {
  const params = JSON.parse(JSON.stringify(DEFAULTS));
  if (formId === "inputs") params.disturbances = [];
  document.querySelectorAll(`#${formId} [data-path]`).forEach((el) => {
    let value;
    if (el.type === "checkbox") value = el.checked;
    else if (el.tagName === "SELECT") value = Number(el.value);
    else value = el.value.trim() === "" ? null : Number(el.value);
    setPath(params, el.dataset.path, value);
  });
  params.disturbances = (params.disturbances || []).filter((d) => d && d.t !== null);
  return params;
}
function setInput(path, value) {
  const el = document.querySelector(`[data-path="${path}"]`);
  if (el.type === "checkbox") el.checked = value; else el.value = value === null ? "" : value;
}

// ---------------------------------------------------------------- plotting
function layout(xTitle, yTitle, extra = {}) {
  const axis = (title) => ({
    title: { text: title, font: { size: 12, color: css("--text-2") } },
    gridcolor: css("--grid"), linecolor: css("--axis"), zerolinecolor: css("--grid"),
    tickfont: { color: css("--muted"), size: 11 }, automargin: true,
  });
  const base = {
    paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
    font: { family: "Inter, system-ui, sans-serif", color: css("--text"), size: 12 },
    margin: { l: 56, r: 12, t: 8, b: 44 },
    xaxis: axis(xTitle), yaxis: axis(yTitle),
    legend: { orientation: "h", y: -0.24, font: { size: 11, color: css("--text-2") } },
    hoverlabel: { bgcolor: css("--surface"), bordercolor: css("--border-strong"),
                  font: { family: "Inter, system-ui, sans-serif", color: css("--text") } },
    showlegend: true,
  };
  for (const [k, v] of Object.entries(extra)) base[k] = typeof v === "object" && !Array.isArray(v) && base[k] ? Object.assign(base[k], v) : v;
  return base;
}
const CONFIG = { responsive: true, displaylogo: false, displayModeBar: "hover",
                 modeBarButtonsToRemove: ["lasso2d", "select2d", "autoScale2d"] };

function drawTitration(r, st, params) {
  const s1 = st.stages[0];
  const opRatio = s1.FR / params.influent.F;
  Plotly.react("plot-titration", [
    { x: r.ratio, y: r.pH, mode: "lines", name: "pH", line: { color: seriesColor(0), width: 2.5 },
      hovertemplate: "F<sub>R</sub>/F = %{x:.5f}<br>pH %{y:.2f}<extra></extra>" },
    { x: [r.r_eq, r.r_eq], y: [0, 14], mode: "lines", name: "equivalence", hoverinfo: "skip",
      line: { dash: "dot", color: css("--muted"), width: 1.5 } },
    { x: [opRatio], y: [s1.SP], mode: "markers", name: "stage 1 set point",
      marker: { size: 11, color: seriesColor(1), line: { width: 2, color: css("--surface") } },
      hovertemplate: "Operating point<br>F<sub>R</sub>/F = %{x:.5f}, pH %{y:.2f}<extra></extra>" },
  ], layout("reagent-to-influent ratio  F<sub>R</sub> / F", "pH", {
    yaxis: { range: [0, 14] },
    // faint universal-indicator bands, one per pH unit (decoration only)
    shapes: [...Array(14).keys()].map((p) => ({ type: "rect", xref: "paper", x0: 0, x1: 1, y0: p, y1: p + 1,
      fillcolor: phColor(p + 0.5, 0.09), line: { width: 0 }, layer: "below" })),
  }), CONFIG);

  Plotly.react("plot-gain", [
    { x: r.gain_pH, y: r.gain, mode: "lines", name: "gain", line: { color: seriesColor(0), width: 2.5 },
      hovertemplate: "pH %{x:.2f}<br>%{y:.3s} pH per m³/h<extra></extra>" },
    { x: [s1.SP], y: [s1.Kp], mode: "markers", name: "stage 1 set point",
      marker: { size: 11, color: seriesColor(1), line: { width: 2, color: css("--surface") } },
      hovertemplate: "Set point pH %{x:.2f}<br>K<sub>p</sub> = %{y:.3s}<extra></extra>" },
  ], layout("pH", "d(pH)/d(F<sub>R</sub>)  [pH per m³/h]", { yaxis: { type: "log" } }), CONFIG);
}

function disturbanceShapes(params) {
  return params.disturbances.map((d) => ({
    type: "line", xref: "x", yref: "paper", x0: d.t, x1: d.t, y0: 0, y1: 1,
    line: { color: css("--muted"), width: 1, dash: "dot" },
  }));
}

function drawSimulation(s, params) {
  const pH = [], flow = [];
  s.pH.forEach((series, k) => {
    const color = seriesColor(k);
    pH.push({ x: s.t, y: series, mode: "lines", name: `tank ${k + 1}`, line: { color, width: 2 },
              hovertemplate: `tank ${k + 1}: pH %{y:.2f}<extra></extra>` });
    pH.push({ x: s.t, y: s.pH_measured[k], mode: "lines", name: `probe ${k + 1}`, showlegend: false,
              line: { color, dash: "dot", width: 1.5 }, hovertemplate: `probe ${k + 1}: %{y:.2f}<extra></extra>` });
    pH.push({ x: s.t, y: s.SP[k], mode: "lines", name: `SP ${k + 1}`, showlegend: false, hoverinfo: "skip",
              line: { color, dash: "dash", width: 1 } });
    flow.push({ x: s.t, y: s.FR[k], mode: "lines", name: `stage ${k + 1}`, line: { color, width: 2 },
                hovertemplate: `stage ${k + 1}: %{y:.4f} m³/h<extra></extra>` });
    const fmax = params.stages[k].FR_max;
    flow.push({ x: [s.t[0], s.t[s.t.length - 1]], y: [fmax, fmax], mode: "lines", hoverinfo: "skip",
                name: `max ${k + 1}`, showlegend: false, line: { color, dash: "dot", width: 1 } });
  });
  const shapes = disturbanceShapes(params);
  Plotly.react("plot-response", pH, layout("time  [min]", "pH", { hovermode: "x unified", shapes }), CONFIG);
  Plotly.react("plot-flow", flow, layout("time  [min]", "reagent flow  [m³/h]", { hovermode: "x unified", shapes }), CONFIG);
}

function drawStability(st, params) {
  const c = st.curve;
  const kc = params.stages[0].Kc;
  const finite = c.Kcu.filter((v) => v !== null);
  const floor = Math.min(...finite, kc || Infinity) / 5;
  const accent = seriesColor(0);
  const title = "K<sub>c,u</sub>  [(m³/h)/pH]" + (st.pade ? "  · Padé" : "");
  Plotly.react("plot-kcu", [
    { x: c.SP, y: c.SP.map(() => floor), mode: "lines", line: { width: 0 }, hoverinfo: "skip", showlegend: false },
    { x: c.SP, y: c.Kcu, mode: "lines", name: "stable region", fill: "tonexty", fillcolor: rgba(accent, 0.14),
      line: { color: accent, width: 2.5 }, hovertemplate: "SP %{x:.1f}<br>K<sub>c,u</sub> = %{y:.3s}<extra></extra>" },
    { x: [params.stages[0].SP], y: [kc], mode: "markers", name: "your stage 1 K<sub>c</sub>",
      marker: { size: 12, symbol: "diamond", color: seriesColor(1), line: { width: 2, color: css("--surface") } },
      hovertemplate: "Your K<sub>c</sub> = %{y:.3s} at SP %{x:.1f}<extra></extra>" },
  ], layout("set point pH", title, { yaxis: { type: "log" } }), CONFIG);

  const rows = st.stages.map((a, k) => `<tr>
    <td><span class="stage-swatch" style="background:var(--series-${k + 1})"></span>${k + 1}</td>
    <td>${fmt(a.SP)}</td><td>${fmt(a.FR)}</td>
    <td>${fmt(a.Kp)} / (${fmt(a.tau)} s + 1)</td>
    <td>${fmt(a.Kcu)}</td><td>${a.Pu ? fmt(a.Pu) : "—"}</td>
    <td>${fmt(a.Kc_zn)} / ${a.tauI_zn ? fmt(a.tauI_zn) : "—"}</td>
    <td>${badge(a.stable_now, "stable", "unstable")}</td></tr>`).join("");
  $("stage-analysis").innerHTML = `<table class="grid">
    <tr><th>Stage</th><th>SP</th><th>F<sub>R</sub> <span class="unit">m³/h</span></th>
      <th>G<sub>p</sub>(s) <span class="unit">pH per m³/h</span></th>
      <th>K<sub>c,u</sub></th><th>P<sub>u</sub> <span class="unit">s</span></th><th>Z–N K<sub>c</sub> / τ<sub>I</sub></th><th>Your tuning</th></tr>
    ${rows}</table>`;
}

function drawKpis(st, s, params) {
  const s1 = st.stages[0];
  const last = s.pH.length - 1;
  const sp = s.SP[last][s.SP[last].length - 1];
  const final = s.pH[last];
  const lo = Math.min(...final), hi = Math.max(...final);
  const outside = final.filter((v, i) => Math.abs(v - s.SP[last][i]) > 0.5).length / final.length;
  const margin = s1.Kcu === null || !params.stages[0].Kc ? null : s1.Kcu / params.stages[0].Kc;
  const tile = (label, value, sub) => `<div class="kpi"><div class="k-label">${label}</div>
    <div class="k-value">${value}</div><div class="k-sub">${sub}</div></div>`;
  $("kpis").innerHTML =
    tile("Process gain at stage 1 SP", fmt(s1.Kp), `pH per m³/h · τ = ${fmt(s1.tau / 60)} min`) +
    tile("Stability limit K<sub>c,u</sub>", fmt(s1.Kcu), margin === null ? "P-only, stage 1" : `your K<sub>c</sub> is ${fmt(100 / margin, 2)}% of it`) +
    tile(`Final tank pH range`, `${lo.toFixed(2)}–${hi.toFixed(2)}`, `set point ${fmt(sp)} · over the run`) +
    tile("Time outside SP ± 0.5", `${Math.round(100 * outside)}%`, `final stage (stage ${last + 1})`);
}

function drawDesign(results) {
  $("design-results").innerHTML = ["1", "2", "3"].map((n) => {
    const r = results[n];
    if (r.error) return `<div class="card design-card"><div class="top"><h3>${n}-stage design</h3>${badge(false, "", "error")}</div><p class="fail">${r.error}</p></div>`;
    const train = `<div class="train"><span class="muted">influent</span>` + r.stages.map((s, k) =>
      `<span class="arrow">→</span><span class="tank" style="border-color:var(--series-${k + 1})">pH ${fmt(s.SP)}</span>`).join("") +
      `<span class="arrow">→</span><span class="muted">effluent</span></div>`;
    const rows = r.stages.map((s, k) => `<tr>
      <td><span class="stage-swatch" style="background:var(--series-${k + 1})"></span>${k + 1}</td>
      <td>${fmt(s.SP)} <span class="muted">(${s.band[0]}–${s.band[1]})</span></td>
      <td>${fmt(s.demand_min)} – ${fmt(s.demand_max)}</td><td>${fmt(s.FR_max)}</td>
      <td>${badge(s.rangeability_ok, fmt(s.rangeability) + " : 1", fmt(s.rangeability) + " : 1")}</td>
      <td>${badge(s.resolution_ok, fmt(s.resolution_pct) + " %", fmt(s.resolution_pct) + " %")}</td>
      <td>${fmt(s.Kp)}</td><td>${fmt(s.Kcu)}</td></tr>`).join("");
    return `<div class="card design-card">
      <div class="top"><h3>${n}-stage design</h3>${badge(r.feasible, "feasible", "not feasible")}
        <span class="meta">total volume ${fmt(r.total_volume)} m³</span></div>
      ${train}
      <div class="scroll-x"><table class="grid"><tr><th>Stage</th><th>SP <span class="unit">(band)</span></th>
        <th>Demand <span class="unit">m³/h</span></th><th>Valve max <span class="unit">m³/h</span></th>
        <th>Rangeability needed</th><th>Resolution needed</th>
        <th>K<sub>p</sub> <span class="unit">pH/(m³/h)</span></th><th>K<sub>c,u</sub> <span class="unit">(m³/h)/pH</span></th></tr>${rows}</table></div></div>`;
  }).join("");
}

function redrawAll() {
  if (!LAST) return;
  drawTitration(LAST.titration, LAST.stability, LAST.params);
  drawStability(LAST.stability, LAST.params);
  drawSimulation(LAST.simulation, LAST.params);
}

// ------------------------------------------------------------------ actions
function lockButtons(locked) {
  document.querySelectorAll("button.btn, button.chip").forEach((b) => (b.disabled = locked));
}

async function runAll() {
  const params = readInputs("inputs");
  lockButtons(true);
  try {
    const t0 = performance.now();
    const say = (t) => setStatus(t, true);
    say("Titration curve…");
    const titration = await callPy("titration", params, say);
    say("Linearizing + Routh–Hurwitz…");
    const stability = await callPy("stability", params, say);
    say("Simulating…");
    const simulation = await callPy("simulation", params, say);
    LAST = { params, titration, stability, simulation };
    redrawAll();
    const plantData = Object.assign({}, simulation, {
      FR_max: params.stages.slice(0, simulation.pH.length).map((st) => st.FR_max),
      disturbances: params.disturbances, influent: titration.pH[0] });
    if (!PLANT) PLANT = createPlantView($("plant-view"), plantData, { seconds: 16 });
    else PLANT.setData(plantData);
    PLANT.play();
    drawKpis(stability, simulation, params);
    setStatus(`Done in ${((performance.now() - t0) / 1000).toFixed(1)} s`);
  } catch (err) {
    setStatus("Error: " + err.message);
    console.error(err);
  } finally {
    lockButtons(false);
  }
}

async function autoTune() {
  setStatus("Computing Ziegler–Nichols settings…", true);
  const st = await callPy("stability", readInputs("inputs"));
  st.stages.forEach((a, k) => {
    setInput(`stages.${k}.Kc`, a.Kc_zn === null ? "" : Number(a.Kc_zn.toPrecision(3)));
    setInput(`stages.${k}.tauI`, a.tauI_zn === null ? 0 : Number(a.tauI_zn.toPrecision(3)));
  });
  await runAll();
}

async function runDesign() {
  const params = readInputs("design-inputs");
  params.instruments = readInputs("inputs").instruments;
  setStatus("Comparing designs…", true);
  drawDesign(await callPy("design", params));
  setStatus("Design comparison done");
}

// Scenarios: start from the defaults, change a few inputs, then run.
const PRESETS = {
  single: { set: {}, tune: false },
  staged: { set: { n_stages: 2, "stages.0.SP": 4, "stages.1.CR": 0.01 }, tune: true },
  buffered: { set: { "influent.Ca": 0.002, "influent.Cw": 0.01, "stages.0.SP": 4.76,
                     "disturbances.0.Ca": 0.003 }, tune: true },
  deadtime: { set: { n_stages: 2, "stages.0.SP": 4, "stages.1.CR": 0.01, "instruments.theta": 10 }, tune: true },
  windup: { set: { "stages.0.SP": 4, "stages.0.FR_max": 0.5, "disturbances.0.Ca": 0.015,
                   "disturbances.1.t": 20, "disturbances.1.F": null, "disturbances.1.Ca": 0.01,
                   "sim.t_end": 50, "sim.anti_windup": false }, tune: true,
            note: "Anti-windup is OFF: see the overshoot after minute 20. Tick it and press Run to compare." },
};

async function applyPreset(name) {
  document.querySelectorAll("[data-preset]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.preset === name)));
  buildMainForm();
  for (const [path, value] of Object.entries(PRESETS[name].set)) setInput(path, value);
  if (PRESETS[name].tune) await autoTune(); else await runAll();
  if (PRESETS[name].note) setStatus(PRESETS[name].note);
}

// Design scenarios: HCl only, or HCl plus up to 2 mM acetic acid.
const DESIGN_NOTES = {
  hcl: "",
  acetic: "With acetic acid (pKa 4.76) a first stage that stops at pH 4 leaves most of the weak acid for the " +
          "trim stage, whose demand then varies hugely: its rangeability requirement explodes. Try moving the " +
          "intermediate set points, the bands and the trim-stage NaOH strength to find a feasible design.",
};
async function applyDesignScenario(name) {
  document.querySelectorAll("[data-design]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.design === name)));
  setInput("design.Cw_max", name === "acetic" ? 0.002 : 0);
  $("design-note").textContent = DESIGN_NOTES[name];
  await runDesign();
}

async function init() {
  setStatus("Loading Python in your browser (first visit downloads ~12 MB)…", true);
  DEFAULTS = await callPy("defaults", undefined, (t) => setStatus(t, true));
  buildMainForm();
  buildDesignForm();
  $("run").addEventListener("click", runAll);
  $("autotune").addEventListener("click", autoTune);
  $("run-design").addEventListener("click", runDesign);
  document.querySelectorAll("[data-preset]").forEach((b) =>
    b.addEventListener("click", () => applyPreset(b.dataset.preset)));
  document.querySelectorAll("[data-design]").forEach((b) =>
    b.addEventListener("click", () => applyDesignScenario(b.dataset.design)));
  window.addEventListener("themechange", redrawAll);
  await runAll();
  await runDesign();
}

init().catch((err) => setStatus("Could not start Python: " + err.message));
