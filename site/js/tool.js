// Tool page: builds the input form, sends the inputs to Python (api.py),
// and draws the results with Plotly. No engineering is done here: every
// number shown comes from the Python model.

let DEFAULTS = null;
const $ = (id) => document.getElementById(id);
const setStatus = (text) => { $("status").textContent = text; };

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
  return a >= 1e4 || a < 1e-3 ? x.toExponential(digits - 1) : Number(x.toPrecision(digits)).toString();
}
function numberInput(path, value) {
  const v = value === null || value === undefined ? "" : value;
  return `<input type="number" step="any" data-path="${path}" value="${v}">`;
}
function field(path, label, unit) {
  return `<label class="field"><span>${label} <span class="unit">${unit}</span></span>` +
         numberInput(path, getPath(DEFAULTS, path)) + `</label>`;
}

// ------------------------------------------------------------- the forms
const STAGE_ROWS = [
  ["V", "Tank volume", "m³"], ["CR", "NaOH conc.", "mol/L"],
  ["FR_max", "Valve max flow", "m³/h"], ["SP", "Set point", "pH"],
  ["Kc", "Gain Kc", "(m³/h)/pH"], ["tauI", "τI (0 = P-only)", "s"],
];

function buildMainForm() {
  const stageTable = STAGE_ROWS.map(([key, label, unit]) =>
    `<tr><th>${label}<br><span class="unit">${unit}</span></th>` +
    [0, 1, 2].map((k) => `<td>${numberInput(`stages.${k}.${key}`, DEFAULTS.stages[k][key])}</td>`).join("") +
    `</tr>`).join("");
  const disturbanceRows = [0, 1, 2].map((k) => {
    const d = DEFAULTS.disturbances[k] || {};
    return `<tr>` + ["t", "F", "Ca", "Cw"].map((key) =>
      `<td>${numberInput(`disturbances.${k}.${key}`, d[key])}</td>`).join("") + `</tr>`;
  }).join("");

  $("inputs").innerHTML = `
    <fieldset><legend>Influent (acidic wastewater)</legend>
      ${field("influent.F", "Flow", "m³/h")}
      ${field("influent.Ca", "HCl", "mol/L")}
      ${field("influent.Cw", "Acetic acid", "mol/L")}
    </fieldset>
    <fieldset><legend>Stages (tanks in series)</legend>
      <label class="field"><span>Number of stages</span>
        <select data-path="n_stages">${[1, 2, 3].map((n) =>
          `<option ${n === DEFAULTS.n_stages ? "selected" : ""}>${n}</option>`).join("")}</select></label>
      <div class="scroll-x"><table class="grid">
        <tr><th></th><th>Stage 1</th><th>Stage 2</th><th>Stage 3</th></tr>${stageTable}
      </table></div>
      <p class="muted" style="font-size:13px">Each stage has its own NaOH valve and PI loop.
        Stage 1's tank volume and NaOH strength are also used for the titration and stability plots.</p>
    </fieldset>
    <fieldset><legend>Instruments</legend>
      ${field("instruments.tau_v", "Valve lag τv", "s")}
      ${field("instruments.tau_m", "Probe lag τm", "s")}
      ${field("instruments.theta", "Dead time θ", "s")}
    </fieldset>
    <fieldset><legend>Disturbances (step changes)</legend>
      <div class="scroll-x"><table class="grid">
        <tr><th>time<br><span class="unit">min</span></th><th>new flow<br><span class="unit">m³/h</span></th>
            <th>new HCl<br><span class="unit">mol/L</span></th><th>new acetic<br><span class="unit">mol/L</span></th></tr>
        ${disturbanceRows}
      </table></div>
      <p class="muted" style="font-size:13px">Leave a cell blank for "no change"; blank time = row unused.</p>
    </fieldset>
    <fieldset><legend>Simulation</legend>
      ${field("sim.t_end", "Duration", "min")}
      ${field("sim.dt", "Controller sample time", "s")}
      <label class="field"><span>Anti-windup</span>
        <input type="checkbox" data-path="sim.anti_windup" ${DEFAULTS.sim.anti_windup ? "checked" : ""}></label>
    </fieldset>`;
}

function buildDesignForm() {
  const d = DEFAULTS.design;
  const designTables = ["1", "2", "3"].map((n) => {
    const rows = d.designs[n].map((s, j) => `<tr><td>${j + 1}</td>` +
      ["SP", "band_low", "band_high", "CR", "V"].map((key) =>
        `<td>${numberInput(`design.designs.${n}.${j}.${key}`, s[key])}</td>`).join("") + `</tr>`).join("");
    return `<h3>${n}-stage design</h3><div class="scroll-x"><table class="grid">
      <tr><th>#</th><th>SP</th><th>band low</th><th>band high</th><th>NaOH M</th><th>V m³</th></tr>${rows}</table></div>`;
  }).join("");
  $("design-inputs").innerHTML = `
    <fieldset><legend>Influent range</legend>
      ${field("design.F_min", "Flow min", "m³/h")}${field("design.F_max", "Flow max", "m³/h")}
      ${field("design.Ca_min", "HCl min", "mol/L")}${field("design.Ca_max", "HCl max", "mol/L")}
      ${field("design.Cw_min", "Acetic min", "mol/L")}${field("design.Cw_max", "Acetic max", "mol/L")}
    </fieldset>
    <fieldset><legend>Valve capability (assumed — enter your vendor's data)</legend>
      ${field("design.valve_rangeability", "Rangeability", "max/min")}
      ${field("design.valve_resolution_pct", "Resolution", "% of max")}
      ${field("design.margin", "Sizing margin", "× max demand")}
    </fieldset>
    <fieldset><legend>Stages of each design</legend>${designTables}</fieldset>`;
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

// ---------------------------------------------------------------- plotting
const STAGE_COLORS = ["#2a7fb8", "#d9822b", "#4f9a4a"];

function plotLayout(xTitle, yTitle, extra = {}) {
  const css = getComputedStyle(document.documentElement);
  const text = css.getPropertyValue("--text").trim();
  const grid = css.getPropertyValue("--plot-grid").trim();
  const axis = (title) => ({ title: { text: title }, gridcolor: grid, zerolinecolor: grid });
  return Object.assign({
    paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
    font: { color: text, size: 12 }, margin: { l: 60, r: 16, t: 10, b: 46 },
    xaxis: axis(xTitle), yaxis: axis(yTitle),
    legend: { orientation: "h", y: -0.25 }, showlegend: true,
  }, extra);
}
const PLOT_CONFIG = { responsive: true, displaylogo: false };

function drawTitration(r) {
  Plotly.newPlot("plot-titration", [
    { x: r.ratio, y: r.pH, mode: "lines", name: "pH", line: { color: STAGE_COLORS[0] } },
    { x: [r.r_eq, r.r_eq], y: [0, 14], mode: "lines", name: "equivalence r_eq",
      line: { dash: "dot", color: "gray" } },
  ], plotLayout("Reagent-to-influent ratio  F_R / F", "pH", { showlegend: false }), PLOT_CONFIG);
  Plotly.newPlot("plot-gain", [
    { x: r.gain_pH, y: r.gain, mode: "lines", name: "gain", line: { color: STAGE_COLORS[1] } },
  ], plotLayout("pH", "d(pH)/d(F_R)   [pH per m³/h]",
    { yaxis: { type: "log", title: { text: "d(pH)/d(F_R)   [pH per m³/h]" } }, showlegend: false }),
  PLOT_CONFIG);
}

function drawSimulation(s, params) {
  const pHTraces = [], flowTraces = [];
  s.pH.forEach((series, k) => {
    const color = STAGE_COLORS[k];
    pHTraces.push({ x: s.t, y: series, mode: "lines", name: `tank ${k + 1} pH`, line: { color } });
    pHTraces.push({ x: s.t, y: s.pH_measured[k], mode: "lines", name: `tank ${k + 1} measured`,
                    line: { color, dash: "dot", width: 1.5 } });
    pHTraces.push({ x: s.t, y: s.SP[k], mode: "lines", name: `SP ${k + 1}`,
                    line: { color, dash: "dash", width: 1 }, showlegend: false });
    flowTraces.push({ x: s.t, y: s.FR[k], mode: "lines", name: `stage ${k + 1} reagent`, line: { color } });
    const fmax = params.stages[k].FR_max;
    flowTraces.push({ x: [s.t[0], s.t[s.t.length - 1]], y: [fmax, fmax], mode: "lines",
                      name: `valve max ${k + 1}`, line: { color, dash: "dot", width: 1 }, showlegend: false });
  });
  Plotly.newPlot("plot-response", pHTraces, plotLayout("time  [min]", "pH"), PLOT_CONFIG);
  Plotly.newPlot("plot-flow", flowTraces, plotLayout("time  [min]", "reagent flow  [m³/h]"), PLOT_CONFIG);
}

function drawStability(st, params) {
  const c = st.curve;
  const s1 = params.stages[0];
  const traces = [
    { x: c.SP, y: c.Kcu, mode: "lines", name: "Kc,u (stability limit)", line: { color: STAGE_COLORS[0] } },
    { x: [c.SP[0], c.SP[c.SP.length - 1]], y: [s1.Kc, s1.Kc], mode: "lines",
      name: "stage 1 Kc (current)", line: { color: STAGE_COLORS[1], dash: "dash" } },
  ];
  const title = "Kc,u  [(m³/h)/pH]" + (st.pade ? "  (Padé approx.)" : "");
  Plotly.newPlot("plot-kcu", traces, plotLayout("set point pH",
    title, { yaxis: { type: "log", title: { text: title } } }), PLOT_CONFIG);

  const rows = st.stages.map((a, k) => `<tr>
    <td>${k + 1}</td><td>${fmt(a.SP)}</td><td>${fmt(a.FR)}</td>
    <td>G<sub>p</sub>(s) = ${fmt(a.Kp)} / (${fmt(a.tau)} s + 1)</td>
    <td>${fmt(a.Kcu)}</td><td>${a.Pu ? fmt(a.Pu) : "—"}</td>
    <td>${fmt(a.Kc_zn)} / ${a.tauI_zn ? fmt(a.tauI_zn) : "—"}</td>
    <td class="${a.stable_now ? "ok" : "fail"}">${a.stable_now ? "stable" : "UNSTABLE"}</td></tr>`).join("");
  $("stage-analysis").innerHTML = `<table class="grid">
    <tr><th>Stage</th><th>SP</th><th>F<sub>R</sub> m³/h</th><th>Linearized process (gain pH per m³/h, τ s)</th>
      <th>Kc,u (m³/h)/pH</th><th>P<sub>u</sub> s</th><th>Z–N PI: Kc / τI</th><th>Current tuning (linear)</th></tr>
    ${rows}</table>`;
}

function drawDesign(results) {
  $("design-results").innerHTML = ["1", "2", "3"].map((n) => {
    const r = results[n];
    if (r.error) return `<div class="card"><h3>${n}-stage</h3><p class="fail">${r.error}</p></div>`;
    const rows = r.stages.map((s, k) => `<tr><td>${k + 1}</td><td>${fmt(s.SP)} (${s.band[0]}–${s.band[1]})</td>
      <td>${fmt(s.demand_min)} – ${fmt(s.demand_max)}</td><td>${fmt(s.FR_max)}</td>
      <td class="${s.rangeability_ok ? "ok" : "fail"}">${fmt(s.rangeability)} : 1</td>
      <td class="${s.resolution_ok ? "ok" : "fail"}">${fmt(s.resolution_pct)} %</td>
      <td>${fmt(s.Kp)}</td><td>${fmt(s.Kcu)}</td></tr>`).join("");
    return `<div class="card"><h3>${n}-stage design —
      <span class="${r.feasible ? "ok" : "fail"}">${r.feasible ? "feasible" : "not feasible"}</span>
      <span class="muted">(total volume ${fmt(r.total_volume)} m³)</span></h3>
      <div class="scroll-x"><table class="grid"><tr><th>Stage</th><th>SP (band)</th><th>Demand m³/h</th>
      <th>Valve max m³/h</th><th>Rangeability needed</th><th>Resolution needed</th>
      <th>K<sub>p</sub> pH/(m³/h)</th><th>Kc,u (m³/h)/pH</th></tr>${rows}</table></div></div>`;
  }).join("");
}

// ------------------------------------------------------------------ actions
async function runAll() {
  const params = readInputs("inputs");
  const buttons = document.querySelectorAll("button");
  buttons.forEach((b) => (b.disabled = true));
  try {
    const t0 = performance.now();
    setStatus("Computing titration curve…");
    drawTitration(await callPy("titration", params, setStatus));
    setStatus("Linearizing and running Routh–Hurwitz…");
    drawStability(await callPy("stability", params, setStatus), params);
    setStatus("Simulating…");
    drawSimulation(await callPy("simulation", params, setStatus), params);
    setStatus(`Done in ${((performance.now() - t0) / 1000).toFixed(1)} s.`);
  } catch (err) {
    setStatus("Error: " + err.message);
    console.error(err);
  } finally {
    buttons.forEach((b) => (b.disabled = false));
  }
}

async function autoTune() {
  const st = await callPy("stability", readInputs("inputs"), setStatus);
  st.stages.forEach((a, k) => {
    document.querySelector(`[data-path="stages.${k}.Kc"]`).value = a.Kc_zn === null ? "" : Number(a.Kc_zn.toPrecision(3));
    document.querySelector(`[data-path="stages.${k}.tauI"]`).value = a.tauI_zn === null ? 0 : Number(a.tauI_zn.toPrecision(3));
  });
  await runAll();
}

async function runDesign() {
  const params = readInputs("design-inputs");
  params.instruments = readInputs("inputs").instruments;
  setStatus("Comparing designs…");
  drawDesign(await callPy("design", params, setStatus));
  setStatus("Design comparison done.");
}

async function init() {
  DEFAULTS = await callPy("defaults", undefined, setStatus);
  buildMainForm();
  buildDesignForm();
  $("run").addEventListener("click", runAll);
  $("autotune").addEventListener("click", autoTune);
  $("run-design").addEventListener("click", runDesign);
  await runAll();
  await runDesign();
}

init().catch((err) => setStatus("Could not start Python: " + err.message));
