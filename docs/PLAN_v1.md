# pH Neutralization Design & Control Tool — Plan v1

Course: Process Dynamics & Controls (3rd-year ChE). AI-written code; the student must be able
to explain every equation and every important line.
Status: **implemented (all milestones M0–M8).** 71 pytest tests pass; site verified in headless
Chromium. Deviations from this plan are listed in README.md ("Changes from the plan").

---

## 0. Decisions already made (from clarifying questions)

| Topic | Decision |
|---|---|
| Chemistry scope | **Acidic influent only.** Influent: HCl (milestone 1), then HCl + acetic acid (later milestone). Reagent: NaOH only (strength chosen per stage). Alkaline influent, lime and soda ash are **beyond scope**. |
| Plotting | **Plotly.js** in the browser. Python returns plain numbers (lists/dicts); one small JS file draws them. |
| Dead time in Routh–Hurwitz | Routh on the **delay-free** model is the exact, tested baseline. Dead time is added with a **1st-order Padé approximation**, labeled "approximate", and compared against simulation that uses true dead time. |

### Decisions I recommend but need your OK

1. **Core uses numpy only; scipy is used only in the tests.** The pH solver is a plain
   bisection (about 10 lines, impossible to fail on a monotone function) and the time stepping is
   a hand-written loop. scipy (`brentq`, `solve_ivp`, `signal`) is then used in pytest as an
   *independent cross-check* of my code. Reasons: (a) every line in the core is explainable
   with no "black box" library call, (b) Pyodide downloads far less on first load (scipy is the
   largest package by far). Your brief said "numpy/scipy" — if your instructor expects scipy in
   the model itself, say so and I'll use `brentq`/`solve_ivp` in the core instead.
2. **Add a first-order valve/actuator lag τ_v** (default 5 s). Reason — and this is a good
   teaching point in itself: a tank (1st order) + probe (1st order) under P-only control is a
   2nd-order loop, which is **stable for every Kc > 0**; Routh gives no upper bound. A real loop
   always has a third lag or dead time; the valve lag provides it in an exactly analyzable way so
   the "Routh vs simulation" test can be tight. The UI will let you set τ_v = 0 and θ = 0 and see
   "Kc,u = ∞".
3. **Each stage has its own NaOH valve and its own PI loop** (the usual staged arrangement),
   rather than one valve on tank 1 with tanks 2–3 acting only as filters.

---

## 1. Model: assumptions and equations

### 1.1 Assumptions (all shown on the Theory page)

1. 25 °C, ideal solutions (activity coefficients = 1). Kw = 1.0×10⁻¹⁴ exactly (chosen so
   equivalence is exactly pH 7.00; the measured value at 25 °C is ≈1.0×10⁻¹⁴ — Harris; CRC
   Handbook).
2. Acetic acid Ka = 1.75×10⁻⁵ (pKa ≈ 4.757) (Harris, *Quantitative Chemical Analysis*,
   acid-dissociation table — verify edition/page).
3. HCl and NaOH fully dissociated. Acid–base reactions are instantaneous (equilibrium at every
   instant); only mixing/flow is dynamic.
4. Each tank is a perfectly mixed CSTR with **constant liquid volume** (overflow). Volumes are
   additive, so outlet flow = inlet flow + reagent flow.
5. Influent contains no Na⁺. Reagent is NaOH solution of concentration C_R (dilute, e.g.
   0.1–2 M; 50 % caustic ≈ 19 M is mentioned but heats/mixes differently — beyond scope).
6. Probe: first-order lag τ_m. Transport dead time θ in the sample/measurement path.
7. Valve: delivered flow follows controller output through a first-order lag τ_v, clipped to
   [0, F_R,max]. Valve is linear (flow ∝ signal); characteristic curves, stiction and
   hysteresis are beyond scope.
8. No CO₂ absorption/stripping, no precipitation, no temperature effects of reaction.

### 1.2 Units (one place, at the API boundary)

Internal: time **s**, volume **m³**, flow **m³/s**, concentration **mol/L** (= kmol/m³; the
balances only ever multiply flow × concentration and divide by volume, so units cancel
consistently). The UI shows flows in **m³/h** and times in **min/s**; conversion happens only in
`api.py`.

### 1.3 Reaction invariants (state variables)

Per tank k (stage k = 1..N, N ≤ 3):

- a_k = total chloride, [Cl⁻] (mol/L)
- w_k = total acetate, [HA] + [A⁻] (mol/L)  (zero until the weak-acid milestone)
- b_k = total sodium, [Na⁺] (mol/L)

Why these: the reactions H⁺ + OH⁻ → H₂O and H⁺ + A⁻ ⇌ HA move H⁺ around but **cannot create or
destroy Cl, total acetate, or Na**. So their balances have no reaction term — they are plain
mixing balances. pH is then *computed* from them, not integrated. This removes the stiffness
that would appear if [H⁺] itself were a state (it changes by 10⁷ near equivalence).

### 1.4 Equilibrium (algebraic, at every instant)

- (E1) Kw = [H⁺][OH⁻]  →  [OH⁻] = Kw / [H⁺]
- (E2) Ka = [H⁺][A⁻]/[HA]  →  [A⁻] = w·α, with α = Ka / (Ka + [H⁺])  (fraction ionized)
- (E3) Charge balance: [H⁺] + b = [OH⁻] + a + [A⁻]

Writing h = 10^(−pH), define

  g(pH) = h + b − Kw/h − a − w·Ka/(Ka + h) = 0.

g is **strictly decreasing** in pH (every term either falls or is constant as pH rises), so there
is **exactly one root**. Solver: bisection on pH ∈ [−2, 16], until bracket < 1×10⁻¹⁰ (≈ 38
halvings). Working in pH (log space) rather than h keeps the problem well-scaled from pH 0 to 14.

Cross-check used only in tests (strong acid, w = 0), written in the cancellation-free form:
- if a ≥ b: h = (a−b)/2 + √(((a−b)/2)² + Kw)
- if a < b: h = 2Kw / ((b−a) + √((b−a)² + 4Kw))

- (E4) Buffer capacity (mol/L per pH unit):
  β = ln(10)·( h + Kw/h + w·Ka·h/(Ka + h)² )
  Note −∂g/∂pH = β exactly. β is the "resistance" of the solution to pH change.

### 1.5 Titration curve and process gain (steady-state mixing of influent + reagent)

- (T1) Q = F + F_R;  a = C_a·F/Q;  w = C_w·F/Q;  b = C_R·F_R/Q
- (T2) Reagent-to-influent ratio r = F_R/F; equivalence at r_eq = (C_a + C_w)/C_R.
- (T3) Gain by implicit differentiation of g = 0:

  K = dpH/dF_R = −(∂g/∂F_R)/(∂g/∂pH) = [ (C_R − b) + a + α·w ] / (Q·β)

  Every quantity is already computed, so the gain plot is exact (no finite differences in the
  app; finite differences are used in the tests to check this formula).

Sanity numbers (default case: 0.01 M HCl at 36 m³/h, 1 M NaOH, computed while writing this plan):

| Set point pH | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|
| Reagent flow (m³/h) | 0.324 | 0.356 | 0.360 | 0.360 | 0.360 |
| Gain K (pH per m³/h) | 12 | 119 | 1.2×10³ | 1.2×10⁴ | 6.0×10⁴ |

Gain rises ×5000 between pH 3 and 7 while reagent flow changes by only 10 %. That table *is*
the story of the project.

### 1.6 Dynamics (N tanks in series, stage k gets its own reagent)

Q₀ = F (influent), Q_k = Q_{k−1} + F_R,k. Influent: a₀ = C_a(t), w₀ = C_w(t), b₀ = 0.

- (D1) V_k da_k/dt = Q_{k−1}·a_{k−1} − Q_k·a_k
- (D2) V_k dw_k/dt = Q_{k−1}·w_{k−1} − Q_k·w_k
- (D3) V_k db_k/dt = Q_{k−1}·b_{k−1} + F_R,k·C_R,k − Q_k·b_k
- (D4) pH_k = solution of (E3) with (a_k, w_k, b_k) — algebraic
- (D5) Valve: τ_v dF_R,k/dt = u_k − F_R,k, with u_k clipped to [0, F_R,max,k]
- (D6) Probe: τ_m dpH_m,k/dt = pH_k(t − θ) − pH_m,k

Disturbances: step in influent flow F and/or step in C_a (and C_w) at user-chosen times.

**Time stepping (explainable, not clever):** fixed step Δt = controller sample time
(default 1 s; forced ≤ min(τ_v, τ_m, V/Q)/10).
Each step: (1) controller computes u from current measured pH, held constant over the step
(this is what a real DCS does); (2) RK4 advances (D1–D3, D5) — these are linear ODEs and cost
almost nothing; (3) pH solved **once per tank per step** (D4); (4) the dead time is a FIFO list
of past pH values, θ rounded to whole steps; (5) probe updated with the exact first-order
update pH_m ← pH_m + (1 − e^(−Δt/τ_m))·(pH_delayed − pH_m).

### 1.7 PI controller with limits and anti-windup

Error e = SP − pH_m. Because adding base raises pH (K > 0), Kc > 0 with this error sign.
(Terminology "direct/reverse acting" differs between vendors; the Theory page explains the sign
via this equation instead of the words.)

- (C1) u_n = ū + Kc·( e_n + I_n/τ_I ),  then u_n clipped to [0, F_R,max]
- (C2) Anti-windup by **conditional integration**: I_{n+1} = I_n + e_n·Δt **only if** the
  output was not clipped, or if the error would drive it back inside the limits. Otherwise I is
  frozen.
- P-only: τ_I = ∞ (I term dropped). ū = bias = steady reagent flow that gives SP at nominal
  influent (found by inverting the titration curve with bisection). This makes the P-only
  offset visible and explainable.

### 1.8 Linearization and transfer functions (single loop, stage k)

Deviation variables around steady state (x̄, F̄_R). From (D1–D3) every invariant obeys
V dx′/dt = −Q̄·x′ + (inflow-coefficient)·F_R′, **all with the same time constant τ = V/Q̄**.
Since pH′ = (∂pH/∂b)b′ + (∂pH/∂a)a′ + (∂pH/∂w)w′ with ∂pH/∂b = 1/β, ∂pH/∂a = −1/β,
∂pH/∂w = −α/β:

- (L1) G_p(s) = K_p / (τs + 1), and **K_p equals the titration gain K from (T3)**. (A nice
  result: the dynamic gain is just the slope of the titration curve.)
- (L2) Disturbance TFs G_F(s), G_C(s): same τ, gains from the same partial derivatives.
- (L3) G_v(s) = 1/(τ_v s + 1); G_m(s) = e^(−θs)/(τ_m s + 1); Padé: e^(−θs) ≈ (1 − θs/2)/(1 + θs/2).
- (L4) **P-only, no dead time** — characteristic equation:
  a₃s³ + a₂s² + a₁s + (1 + Kc·K_p) = 0, where
  a₃ = τ_v·τ·τ_m, a₂ = τ_vτ + τ_vτ_m + ττ_m, a₁ = τ_v + τ + τ_m.
  Routh: all first-column entries positive ⇔ −1 < Kc·K_p < a₁a₂/a₃ − 1, so
  **Kc,u = (a₁a₂/a₃ − 1)/K_p**, ω_u = √(a₁/a₃), P_u = 2π/ω_u.
  Key insight: P_u does not depend on K_p, but Kc,u ∝ 1/K_p — so the stable Kc range shrinks by
  the same factor the titration slope grows. Default case: Kc,u ≈ 22.5 (m³/h)/pH at SP 3 vs
  ≈ 0.0045 at SP 7; P_u ≈ 54 s at both.
- (L5) **With Padé dead time**: 4th-order characteristic polynomial; a general Routh-array
  function (numbers, not symbols) checks stability; Kc,u found by bisection on Kc. Labeled
  approximate.
- (L6) Stable Kc range vs SP: evaluate (L4)/(L5) at the steady state for each SP from 3 to 11.
- Multi-stage note: stage k's controller never affects stages upstream, so the linearized
  closed-loop system is block-triangular and its poles are the union of each loop's poles.
  Per-loop analysis is therefore exact for the linear model. (PI Routh is a stretch goal; P-only
  is what the brief requires.)

### 1.9 Design helper (first principles; no hidden rules of thumb)

Inputs: influent F ∈ [F_min, F_max], C_a ∈ [C_min, C_max] (plus C_w later); final pH band
(default 6.0–9.0, matching the US secondary-treatment limit in 40 CFR 133.102(c) — note the
actual limit for an industrial discharge is set by its permit / local pretreatment rules);
N = 1, 2, 3; per-stage SP, band, reagent strength and tank volume; valve capability
(rangeability R_v and resolution as % of full flow — **user inputs, defaults labeled
"assumed, not sourced"**).

Per stage, computed exactly from the model:
1. Reagent demand at SP at the 4 corners of the influent envelope (demand is monotone in F
   and C_a, so corners bound it). Stage k's inlet is the previous stage's outlet at the edges
   of its band.
2. Valve size F_R,max = margin × max demand (margin is a user input, default 1.25, labeled a
   design choice).
3. **Required rangeability** = max demand / min demand.
4. **Required resolution** = (F_R at upper band edge − F_R at lower band edge), worst corner,
   as % of F_R,max. This is the exact (nonlinear) version of "band / gain".
5. K_p, Kc,u and P_u at SP; residence time V/Q.
6. Verdict per stage: rangeability ≤ R_v and resolution ≥ valve resolution.
7. (Stretch) closed-loop simulation of a standard disturbance for each design: peak
   deviation, % time in band, reagent used.

Rules of thumb from the literature (number of stages vs influent pH, mixing/residence time
ratios, etc.) are **not encoded in any calculation**. They may appear only in a "What the
literature says" box, and only after you verify the exact page (see §6).

---

## 2. File / folder structure

```
README.md                     how to run tests, serve locally, deploy
pyproject.toml                pytest config (src layout); no build step needed
requirements-dev.txt          numpy, scipy (tests only), pytest
src/phsim/
  __init__.py
  constants.py      Kw, Ka, unit conversions (m³/h ↔ m³/s)           ~40 lines
  chemistry.py      (E1–E4): charge balance, pH bisection, β        ~80
  titration.py      (T1–T3): mixing, curve, gain, inverse titration  ~90
  plant.py          (D1–D3): tank balances, steady state of N tanks  ~90
  control.py        (C1–C2), valve lag, probe lag, dead-time FIFO    ~90
  simulate.py       time-stepping loop, disturbances, RK4            ~120
  linear.py         (L1–L6): TF, Routh (closed form + general), Padé ~130
  design.py         §1.9 stage comparison                            ~120
  api.py            thin JSON-friendly functions called from JS      ~100
  theory_map.py     list of (equation id, LaTeX, python function)    ~60
tests/
  test_chemistry.py  test_titration.py  test_plant.py  test_control.py
  test_simulate.py   test_linear.py     test_design.py test_api.py  test_theory_map.py
site/
  index.html  tool.html  theory.html
  ai-process.html  model-comparison.html  video.html  learned.html  references.html
  css/style.css
  js/py.js          load Pyodide (pinned version), write phsim/*.py into its file system
  js/tool.js        read form → call api → Plotly.newPlot                ~250 lines
  js/theory.js      render LaTeX (KaTeX) next to inspect.getsource(fn)   ~60
scripts/build_site.py         copy site/ + src/phsim → _site/ (for local serving & deploy)
.github/workflows/pages.yml   on push: pytest → build_site → deploy to GitHub Pages
docs/PLAN_v1.md               this file
docs/REFERENCE_CHECKLIST.md   each citation, status (verified / unverified), page number
```

Budget: Python core ≈ 900 lines including comments; JS ≈ 350 lines. Every function ≤ ~30
lines, with a docstring naming the equation it implements, e.g. `"""Implements (E3)."""`.

**Theory page shows the exact code:** the browser calls Python's `inspect.getsource()` on the
function listed in `theory_map.py`, so the code shown is literally the code that runs — it
cannot drift out of date. `test_theory_map.py` fails if a listed function is missing.

**Why `scripts/build_site.py`:** GitHub Pages "deploy from branch" can only serve the repo root
or `/docs`; using a GitHub Actions deployment of a built `_site/` folder keeps `docs/` for
documents and lets CI refuse to deploy if any test fails.

---

## 3. Milestones (build order, ≈ 28 h total)

| # | Milestone | Est. | Acceptance criteria |
|---|---|---|---|
| M0 | Repo, pytest, CI skeleton | 1.5 h | `pytest` runs (1 trivial test) locally and in GitHub Actions; placeholder `index.html` live on Pages. |
| M1 | Strong-acid equilibrium, titration curve, gain (E1–E4, T1–T3) | 3 h | Tests C1–C8, T1–T4 pass. Quick matplotlib script (local only) shows titration and gain curves; you can explain g(pH) and why bisection always works. |
| M2 | Tank dynamics, open loop, 1–3 tanks (D1–D4) | 3 h | Tests P1–P5 pass: steady state = algebra; mass conserved; dt-halving check. |
| M3 | Control: PI, limits, anti-windup, valve & probe lags, dead time, disturbances (D5–D6, C1–C2) | 4 h | Tests K1–K5 pass. A plot of a saturating step with/without anti-windup shows the difference. |
| M4 | Linear analysis, Routh, Kc,u vs SP (L1–L6) | 3 h | Tests L1–L8 pass, including **simulated onset of oscillation vs Routh within 5 %**. |
| M5 | Website + Pyodide + Tool page | 5 h | Tool page on GitHub Pages: inputs → 4 plots (titration, gain vs pH, closed-loop response, Kc,u vs SP). First load time measured and recorded in README. A default simulation runs in < 3 s after load. Placeholder pages exist. |
| M6 | Weak acid (acetic) everywhere | 2.5 h | Tests W1–W5 pass; Tool lets you add acetic acid and the gain plot visibly flattens near pKa. |
| M7 | Design helper (§1.9) | 3 h | Tests G1–G4 pass; Tool shows a 1/2/3-stage comparison table with feasibility verdict per stage. |
| M8 | Theory page, references, polish | 3 h | Every equation (E, T, D, C, L) shown next to its source; `REFERENCE_CHECKLIST.md` complete; all external links work. |

Build order rationale: everything hard to explain (chemistry, Routh) is finished and tested in
pure Python before any web work, so a web problem can never block the engineering content.

---

## 4. Test list (all pytest; tolerances stated)

**Chemistry (M1)**
- C1 Pure water (a = b = 0) → pH 7.000 (±1e-6).
- C2 Equivalence (a = b) at 1e-4, 1e-2, 1 M → pH 7.000 (±1e-6).
- C3 0.01 M HCl → pH 2.000; 0.001 M → 3.000 (±1e-3) — hand calc.
- C4 1×10⁻⁸ M HCl → pH 6.978 (±1e-3) — the classic "not pH 8" trap; needs Kw in the balance.
- C5 Partial neutralization: 0.01 M HCl + NaOH to b = 0.009 M → pH 3.000 (±1e-3); excess base b − a = 0.01 M → pH 12.000.
- C6 Bisection vs closed form (E3, w = 0) on a 50×50 grid of (a, b), 1e-8 to 1 M: |ΔpH| < 1e-8.
- C7 Bisection vs `scipy.optimize.brentq` (independent method): |ΔpH| < 1e-8.
- C8 β from (E4) vs numerical −Δg/ΔpH: relative error < 1e-5.

**Titration and gain (M1)**
- T1 pH crosses 7.00 at r = r_eq = C_a/C_R (±1e-6 relative).
- T2 Gain (T3) vs central finite difference at 20 points from pH 2 to 12: relative error < 1e-4.
- T3 Strong acid: gain is maximum at the equivalence point.
- T4 Gain at pH 7 / gain at pH 4 > 100 for the default case (documents the core claim).

**Plant dynamics (M2)**
- P1 1, 2, 3 tanks: simulation to 15·Στ_k reaches the algebraic steady state (±1e-4 pH).
- P2 Sodium and chloride conservation: ∫in − ∫out − accumulation < 1e-6 relative.
- P3 Halving Δt changes the pH trajectory by < 1e-3 pH.
- P4 Constant inputs at steady state → states unchanged (no drift) over 10 τ.
- P5 Open-loop small step in F_R at a buffered point (SP = 4, step 0.1 %): simulated pH matches
  K_p(1 − e^(−t/τ)) (with probe and valve lags included via their TFs, computed with
  `scipy.signal.step`) within 2 % of the final change. This is "small-step response matches
  the linearized TF".

**Control (M3)**
- K1 Valve output never < 0 or > F_R,max in any test run.
- K2 PI at buffered SP (pH 4) eliminates offset after an influent step: |pH − SP| < 0.01.
- K3 P-only offset matches linear prediction e_ss = Δd·K_d/(1 + Kc·K_p) within 5 %.
- K4 Anti-windup: after a saturating disturbance, overshoot with conditional integration is
  less than without it, and the integral state stays bounded.
- K5 Dead time: with θ = 10 s, the measured pH starts to respond exactly θ after the tank pH
  (±1 step).

**Linear analysis (M4)**
- L1 (L1) gain K_p equals titration gain (T3) at 10 operating points (rel. < 1e-9 — same formula
  reached two ways).
- L2 Closed-form Routh cubic vs general Routh array: same stable/unstable verdict on 1000 random
  coefficient sets.
- L3 General Routh array vs `numpy.roots` (any root with Re > 0?) on the same random sets.
- L4 At Kc = Kc,u, closed-loop roots have a pair with |Re| < 1e-6·ω_u and Im = ω_u (±1e-6 rel).
- L5 **Onset of sustained oscillation, nonlinear simulation**, P-only, no dead time, at SP = 4
  (gain varies little over a 1e-4-pH excursion): bisect on Kc using "oscillation amplitude
  grows vs decays over 10 periods". Simulated Kc,u within **5 %** of Routh; simulated period
  within 5 % of P_u. (The same test on the *linear* simulation must agree within 1 %; the gap
  between the two shows nonlinearity + discretization.)
- L6 Kc,u(SP = 7) < Kc,u(SP = 4)/100 for the default case (the "shrinking range" claim).
- L7 Padé: Kc,u from (L5) vs simulation with true dead time θ = 10 s: within 15 %; actual
  error recorded in README (documented approximation, not hidden).
- L8 τ_v = 0 and θ = 0 → function reports Kc,u = ∞ (2nd-order loop never goes unstable under P).

**Weak acid (M6)**
- W1 0.1 M acetic acid alone → pH 2.881 (±2e-3) — quadratic hand calc.
- W2 Half-equivalence (b = w/2) at w = 0.1 M → pH = pKa ± 0.01.
- W3 Same at w = 1e-4 M: pH − pKa > 0.1 — documents *when* "pH = pKa" fails (dilute: [H⁺] is no
  longer negligible vs [A⁻]). Teaching test.
- W4 Equivalence of 0.1 M acetic → 0.05 M sodium acetate pH ≈ 8.73 (±0.02, hand calc
  [OH⁻] = √(Kw/Ka · C)).
- W5 T2 (gain vs finite difference) and P1 repeated with acetic acid present.

**Design helper (M7)**
- G1 Single stage, strong acid: required rangeability = (F_max·C_max)/(F_min·C_min) (±1e-6 rel).
- G2 Required resolution matches inverse-titration hand calc for one case.
- G3 Default case: required resolution (% of full flow) for the final stage is larger
  (easier) for 2 stages than for 1.
- G4 Monotonicity check: demand at the 4 corners brackets demand at 25 interior points.

**Website glue (M5, M8)**
- A1 Every `api.py` function returns only JSON-serializable types (lists, floats, str, dict).
- A2 `theory_map.py`: every listed function exists and `inspect.getsource` works on it.
- A3 (Optional, manual or Playwright) Tool page loads in headless Chromium and draws 4 plots.

---

## 5. Risks and how they are handled

| Risk | Handling |
|---|---|
| **Numerical stiffness near equivalence** | Eliminated by design: states are reaction invariants whose ODEs are linear with time constant V/Q; pH is algebraic. Bisection in pH space cannot fail or diverge (unique root, guaranteed bracket). |
| Precision near equivalence (h ≈ 1e-7 next to a ≈ 1e-2) | Solve in pH, not h; tolerance 1e-10 pH; tests C2/C6 at extremes. Closed-form check uses the cancellation-free form. |
| Linear-vs-nonlinear tests failing because the loop leaves the linear region | Run linear checks (P5, L5) at buffered/low-gain points with tiny perturbations; also run the same test on the linear model so failures can be attributed. |
| **Pyodide load time** | numpy-only core (no scipy download); pin an exact Pyodide version from the jsDelivr CDN at build time; show a "Loading Python…" status; measure and record actual time in M5 (target < 10–15 s first visit, cached afterwards). |
| Python loops are slow in the browser | pH solved once per tank per step (not per RK stage); default run ≈ 3600 steps × ≤3 tanks; a "Run" button rather than live sliders. Measured in M5; if too slow, increase Δt within the stability rule or shorten horizon. |
| Browser freezes during a run | Accept a 1–3 s freeze with a spinner. Web Worker is a stretch goal (adds JS you'd have to explain). |
| Sign/unit errors | Single unit-conversion point (`api.py`); Kc sign derived from the error definition; tests use physical hand-calc numbers. |
| Dead time rounding to whole steps | Documented; test K5; Δt small relative to θ. |
| **AI-invented citations** | Every reference goes into `REFERENCE_CHECKLIST.md` with status; nothing unverified is used in a calculation; you check page numbers before the final submission. |
| Scope creep / explainability | Line budget above; each function ≤ 30 lines; "beyond scope" box on Theory page. |
| GitHub Pages path issues | Relative URLs only; CI deploys `_site/`; test the deployed URL at M0. |

---

## 6. References (status honestly marked)

Confident these exist (still verify edition and page before citing):
1. Seborg, Edgar, Mellichamp & Doyle, *Process Dynamics and Control*, 4th ed., Wiley, 2016 —
   linearization, transfer functions, Routh array, Padé approximation, Ziegler–Nichols, PI.
2. Ziegler & Nichols, "Optimum settings for automatic controllers," *Trans. ASME* 64 (1942)
   759–768 — source for any ZN tuning default (Kc = 0.45 Kc,u, τ_I = P_u/1.2 for PI).
3. Harris, *Quantitative Chemical Analysis*, W. H. Freeman (any recent edition) — charge
   balance, Kw, acetic acid pKa.
4. Shinskey, *pH and pIon Control in Process and Waste Streams*, Wiley, 1973.
5. McMillan, *pH Measurement and Control*, ISA (2nd ed. 1994; check for later editions).
6. Liptak (ed.), *Instrument Engineers' Handbook*, Vol. 2 (Process Control), CRC Press — has a
   pH-control chapter (verify edition and chapter number).
7. US 40 CFR 133.102(c) — pH 6.0–9.0 for secondary treatment effluent (applies to POTWs;
   cited only as a typical band).

Believe these exist but **not certain of details — verify or drop**:
8. Gustafsson & Waller, "Dynamic modeling and reaction invariant control of pH," *Chem. Eng.
   Sci.* 38 (1983) 389–398 — origin of the reaction-invariant approach.
9. McAvoy, Hsu & Lowenthal, "Dynamics of pH in controlled stirred tank reactors," *Ind. Eng.
   Chem. Process Des. Dev.* 11 (1972) 68–70.

Rules of thumb I am **not** sure of and will **not** state as fact unless you find them with a
page number (likely in refs 4–6): how many stages for a given influent pH; minimum residence
time or mixing-time ratios for neutralization tanks; typical achievable reagent valve
rangeability/resolution. Until verified, the tool asks the user for these numbers and labels
the defaults "assumed".

---

## 7. Recommended cuts (to fit 20–30 h)

Already out of scope (labeled "beyond scope" on the site): alkaline influent, lime/soda ash and
carbonate chemistry, activity coefficients, temperature dependence of Kw/Ka, non-ideal mixing,
valve characteristics/stiction, gain scheduling / titration-curve characterizers, feedforward,
MPC, adaptive control, nonlinear observers.

If behind schedule, cut in this order (latest first to cut = most important to keep):
1. Design-helper closed-loop simulation (keep the algebraic comparison table).
2. A3 browser smoke test and Web Worker.
3. Per-stage tuning inputs → use automatic defaults (Kc = 0.45 Kc,u, τ_I = P_u/1.2, Ziegler–
   Nichols, ref 2) with one global "detuning factor".
4. Padé/dead-time Routh (L5, L7) → dead time in simulation only.
5. Weak acid in dynamics → keep it in equilibrium/titration/gain plots only.

Never cut: M1–M4 tests (they are your evidence for a skeptical audience), the gain-vs-pH plot,
and the Kc,u-vs-SP plot.

---

## 8. Open items for you

- Confirm the numpy-only-core / scipy-in-tests choice (Decision 1).
- Confirm adding the valve lag τ_v (Decision 2) and one PI loop per stage (Decision 3).
- Default case numbers (0.01 M HCl, 36 m³/h, 1 M NaOH, 10 m³ tank, τ_m = 15 s, τ_v = 5 s,
  θ = 10 s) — change if your course uses a specific example.
- GitHub repo name/owner, when you're ready for M0.
