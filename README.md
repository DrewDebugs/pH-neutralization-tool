# pH Neutralization Design & Control Tool

Course project for Process Dynamics & Controls (AI project: AI wrote the code; the
student explains and defends it). A static website for an engineer designing or
troubleshooting a wastewater pH neutralization system. It shows **why** pH control is
hard (the process gain changes by orders of magnitude near pH 7) and **how** engineers
cope (staging, tank size, reagent strength, tuning).

The plan is in [`docs/PLAN_v1.md`](docs/PLAN_v1.md). Citations still to verify are in
[`docs/REFERENCE_CHECKLIST.md`](docs/REFERENCE_CHECKLIST.md).

## Layout

```
src/phsim/       the model (pure Python, standard library only) — same files run in the browser
  constants.py   Kw, Ka, unit conversion
  chemistry.py   (E1–E4) charge balance, pH by bisection, buffer capacity
  titration.py   (T1–T3) mixing, titration curve, process gain, inverse titration
  plant.py       (D1–D3, D5) tank balances on reaction invariants, steady state
  control.py     (C1–C2, D6) PI with limits + anti-windup, dead time, probe lag
  simulate.py    time stepping (RK4 + algebraic pH), disturbances
  linear.py      (L1–L6) linearization, transfer functions, Routh array, Kc,u, Padé
  design.py      1/2/3-stage comparison: valve rangeability and resolution
  api.py         JSON bridge for the web page (the only place units are converted)
  theory_map.py  which function implements which equation (used by the Theory page)
tests/           pytest: 71 tests, numpy/scipy used only here as independent cross-checks
site/            HTML/CSS/JS (Plotly for plots, KaTeX for equations, Pyodide for Python)
scripts/         build_site.py (assemble _site/), e2e_browser_test.js (optional browser test)
.github/workflows/pages.yml   run tests → build → deploy to GitHub Pages (only if tests pass)
```

## Run the tests

```bash
pip install -r requirements-dev.txt
```

```bash
pytest -q
```

Add `-s` to see the printed comparisons, e.g.
`Routh Kcu=0.0006264 simulated=0.0006268 (0.06%)` and
`Pade Kcu=0.0001898 simulated (true dead time)=0.0001863 (-1.82%)`.

## Run the website locally

```bash
python scripts/build_site.py
```

```bash
python -m http.server -d _site 8000
```

Then open http://localhost:8000. (Opening the HTML file directly does not work: the page
must fetch the Python files over HTTP.)

## Deploy to GitHub Pages

1. Push this folder to a GitHub repository (branch `main`).
2. In the repository: Settings → Pages → Build and deployment → Source: **GitHub Actions**.
3. Every push runs `pytest`; the site is deployed only if all tests pass.

## Measured facts (recorded for the plan)

| Item | Value |
|---|---|
| Tests | 71 passed, ~15 s |
| Pyodide | 0.29.5, loaded from `cdn.jsdelivr.net/npm/pyodide@0.29.5/` (~12 MB uncompressed, cached after first visit) |
| Python ready + first full run (local headless Chromium, files served locally) | ~4–5 s |
| One full Run (titration + stability + 60 min simulation) in the browser | ~1 s |
| Routh Kc,u vs nonlinear simulation, P-only, SP 4 (test L5) | 0.06 % apart; period 53.87 s both |
| Padé Kc,u vs simulation with true 10 s dead time (test L7) | 1.8 % apart |

## Changes from the plan (and why)

- **No numpy in the model; numpy/scipy only in the tests.** The plan proposed a
  numpy-only core. While building, it became clear numpy was not needed at all: the
  solver is bisection, the ODEs are a few lines of RK4, and polynomials are lists.
  Benefits: Pyodide needs no extra packages (faster first load), every line is plain
  Python you can read aloud, and scipy (`brentq`, `signal.step`) and `numpy.roots` act
  as *independent* checks in the tests. If your instructor requires scipy in the model,
  `chemistry.solve_pH` can be swapped for `scipy.optimize.brentq` in one line.
- **Time step is capped** at (fastest time constant)/10, e.g. 0.5 s with a 5 s valve lag,
  whatever the user types. The simulation reports the step it actually used.
- **Ziegler–Nichols is aggressive.** Auto-tune uses Z–N from the Routh Kc,u; Z–N aims
  for quarter-amplitude decay, so oscillatory responses are expected (and the
  nonlinearity makes it worse away from the linearization point). Detune by hand
  (e.g. halve Kc) and compare.

## What you should be able to explain (checklist)

- Why reaction invariants (a, b, w) remove stiffness, and why pH is algebraic.
- Why the charge balance has exactly one root, and why bisection on pH always works.
- Why Kp of the linearized tank equals the titration slope, and τ = V/Q.
- Routh for the cubic: Kc,u = (a1·a2/a3 − 1)/Kp; why Pu does not depend on Kp.
- Why tank + probe alone (2nd order) never goes unstable under P-only.
- Conditional-integration anti-windup (`control.py`), and test K4 that shows it works.
- Design helper: rangeability = max/min demand; resolution = band width in reagent flow
  as % of valve size; why staging (and dilute trim reagent) relaxes the resolution.
