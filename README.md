# pH Neutralization Design & Control Tool

**Live site:** https://drewdebugs.github.io/pH-neutralization-tool/

Course project for Process Dynamics & Controls (AI project: AI wrote the code; the
student explains and defends it). A static website for an engineer designing or
troubleshooting a wastewater pH neutralization system. It shows **why** pH control is
hard (the process gain changes by orders of magnitude near pH 7) and **how** engineers
cope (staging, tank size, reagent strength, tuning).

The plan is in [`docs/PLAN_v1.md`](docs/PLAN_v1.md). Citations still to verify are in
[`docs/REFERENCE_CHECKLIST.md`](docs/REFERENCE_CHECKLIST.md).

## Layout

```
src/phsim/         the model: pure Python, standard library only. The SAME files run in the browser.
  constants.py     Kw, Ka, unit conversion
  chemistry.py     (E1–E4) charge balance, pH by bisection, buffer capacity
  titration.py     (T1–T3) mixing, titration curve, process gain, inverse titration
  plant.py         (D1–D3, D5) tank balances on reaction invariants, steady state
  control.py       (C1–C2, D6) PI with limits + anti-windup, dead time, probe lag
  simulate.py      time stepping (RK4 + algebraic pH), disturbances
  linear.py        (L1–L6) linearization, transfer functions, Routh array, Kc,u, Padé
  verify.py        finds Kc,u by brute-force simulation (checks Routh; used by tests + build)
  design.py        1/2/3-stage comparison: valve rangeability and resolution
  api.py           JSON bridge for the web page (the only place units are converted)
  theory_map.py    which function implements which equation (used by the Theory page)
tests/             pytest: 74 tests; numpy/scipy are used only here, as independent cross-checks
site/              the website source
  *.html           one file per page (content only)
  _partials/       head.html, header.html (menu), footer.html: inserted into every page by the build
  css/style.css    all styling; colors are tokens, dark mode redefines them
  js/py-worker.js  runs Python (Pyodide) in a background thread; the ONE place the Pyodide version is set
  js/py.js         callPy(name, params): sends a call to the worker, returns the result
  js/tool.js       Tool page: form, scenarios, Plotly charts, design cards
  js/plantview.js  animated plant (tank color = simulated pH), used on Home and Tool
  js/phcolor.js    pH -> universal-indicator color (decoration only)
  js/home.js       Home page: beaker, illustrations, showcase (reads data/showcase.json)
  js/theory.js     Theory page: KaTeX equation + inspect.getsource() code
  js/theme.js      light/dark toggle
scripts/
  build_site.py    assemble _site/: pages + partials, model files, Home page data and numbers
  e2e_browser_test.js   opens the built site in headless Chromium (runs in CI)
.github/workflows/pages.yml   pytest → build → browser test → deploy (only if everything passes)
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

Then open http://localhost:8000. Always view `_site/`, not `site/`: the build inserts the
menu and footer, copies the Python model, and computes the Home page numbers. (Opening an
HTML file directly does not work: the page must fetch files over HTTP.)

Optional browser test (needs Node.js):

```bash
npm install --no-save playwright@1.64.1 && npx playwright install chromium
```

```bash
node scripts/e2e_browser_test.js _site screenshots
```

## Editing pages

- Page text: edit `site/<page>.html` between `<main>` and `</main>`. The four placeholder
  pages (AI Process, Model Comparison, Video, What I Learned) each have a "Coming soon" box
  to replace.
- Menu or footer: edit `site/_partials/header.html` or `footer.html` once; every page updates.
- Video: paste the YouTube embed `<iframe>` into `site/video.html`.
- Push to `main`: GitHub runs the tests and the browser test, then deploys.

## Where the numbers on the Home page come from

None are typed in by hand. `scripts/build_site.py` runs the model at build time and writes
`_site/data/showcase.json`: the titration curve, two simulations (one tank vs two stages),
and "facts" such as the 5,000× gain rise, the Routh-vs-simulation gap (the same check as
test L5), the pH 6→8 caustic difference, and the test count (from `pytest --collect-only`).
Change the model and the Home page follows.

## Hand calculations

[`docs/HAND_CALCULATIONS.md`](docs/HAND_CALCULATIONS.md) reworks the key tests with a calculator:
strong acid (including 1×10⁻⁸ M HCl → pH 6.98), weak acid at half-equivalence, the Routh
limit at set point 4, and the anti-windup test.

## Measured facts

| Item | Value |
|---|---|
| Tests | 74 passed, ~15–20 s |
| Pyodide | 0.29.5 (set in `site/js/py-worker.js`), from `cdn.jsdelivr.net/npm/pyodide@…` (~12 MB, cached after the first visit) |
| Python ready + first full run (headless Chromium) | ~4–5 s |
| One full Run (titration + stability + 60 min simulation) | ~1 s, in a background thread (the page stays responsive) |
| Routh Kc,u vs nonlinear simulation, P-only, SP 4 (test L5) | 0.06 % apart; period 53.87 s both |
| Padé Kc,u vs simulation with a true 10 s dead time (test L7) | 1.8 % apart |

## Changes from the plan (and why)

- **No numpy in the model; numpy/scipy only in the tests.** The solver is bisection, the
  ODEs are a few lines of RK4, and polynomials are lists. Pyodide then needs no extra
  packages (faster first load), every line is plain Python, and scipy (`brentq`,
  `signal.step`) and `numpy.roots` act as *independent* checks in the tests. If scipy is
  required in the model, `chemistry.solve_pH` can be swapped for `scipy.optimize.brentq`.
- **Time step is capped** at (fastest time constant)/10, e.g. 0.5 s with a 5 s valve lag.
- **Ziegler–Nichols is aggressive.** Auto-tune uses Z–N from the Routh Kc,u; Z–N aims for
  quarter-amplitude decay, so oscillatory responses are expected. Halve Kc and compare.
- **Acetic acid in the design helper** is a scenario button, not the default: with the
  default intermediate set points (below the acetic pKa of 4.76) every design becomes
  infeasible, which is itself a design lesson (see the note on the Tool page).

## Known limitations (stated openly)

Model assumptions (each is a deliberate simplification for a B.S.-level tool):
- Ideal solutions (activity coefficients = 1) at a fixed 25 °C; K<sub>w</sub> and K<sub>a</sub> do not vary with temperature.
- Perfectly mixed tanks (no mixing dead time); constant volume; additive volumes.
- Instantaneous acid–base equilibrium; no CO<sub>2</sub> exchange, no precipitation.
- Linear valve with a first-order lag; no characteristic curve, stiction or deadband.
- Dead time rounded to whole time steps; the controller is digital with a fixed sample time.

Analysis limits:
- Routh–Hurwitz is applied to the linearized loop at one operating point; far from it the
  nonlinear loop can behave differently (that is the point of the tool, but it is a limit).
- Dead time enters Routh only through a 1st-order Padé approximation (1.8 % error in test L7).
- Ziegler–Nichols tuning is aggressive (aims for quarter-amplitude decay); oscillatory
  responses are expected.

Design helper:
- Valve rangeability (50:1) and resolution (0.5 %) defaults are assumed, not sourced.
- The intermediate set points of the default 2- and 3-stage designs (pH 4; pH 3 and 4.5) are
  illustrative choices, not a literature rule (stated in `design.py`). With acetic acid present
  every default design is infeasible; finding a good mixed-acid staging is left open.

Sources: see `docs/REFERENCE_CHECKLIST.md` for the verification status of each citation.

## What you should be able to explain (checklist)

- Why reaction invariants (a, b, w) remove stiffness, and why pH is algebraic.
- Why the charge balance has exactly one root, and why bisection on pH always works.
- Why Kp of the linearized tank equals the titration slope, and τ = V/Q.
- Routh for the cubic: Kc,u = (a1·a2/a3 − 1)/Kp; why Pu does not depend on Kp.
- Why tank + probe alone (2nd order) never goes unstable under P-only.
- Conditional-integration anti-windup (`control.py`), and test K4 that shows it works.
- How `verify.py` finds Kc,u by simulation, and why it agrees with Routh to 0.06 %.
- Design helper: rangeability = max/min demand; resolution = band width in reagent flow
  as % of valve size; why staging (and dilute trim reagent) relaxes the resolution.
