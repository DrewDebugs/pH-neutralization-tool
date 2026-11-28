# AI log 1: building the project with Claude Code

- **Tool:** Claude Code (Anthropic), cloud session, with access to this repository
- **Model:** _(fill in: shown in the Claude Code session details)_
- **Dates:** 2026-11-23 to 2026-11-28
- **Role of the AI:** wrote the plan, all code, tests and website; deployed to GitHub Pages
- **Role of the student:** wrote the requirements, answered design questions, approved
  actions, verifies sources, and must explain every equation and line

The prompts below are copied verbatim. "Outcome" is a short summary of what the AI did.

---

## Prompt 1: the plan

```text
/Plan I'm a 3rd-year chemical engineering undergraduate building a course project for
Process Dynamics & Controls. It is explicitly an AI project: AI writes the code, and I must
be able to explain every equation and every important line of code to a skeptical audience.
Plan only. Do not write code yet.

GOAL
Build a static website that is a practical design/simulation tool for an engineer
designing or troubleshooting a wastewater pH neutralization system. The tool should
show WHY pH control is hard (process gain changes by orders of magnitude near the
equivalence point) and HOW engineers deal with it (staged tanks, tank sizing,
reagent choice, tuning).

AUDIENCE AND LEVEL
- Users: a plant/process engineer with a B.S. in chemical engineering.
- Keep ALL theory at the level a B.S. chemical engineer can understand: mass
  balances, charge balance, equilibrium constants, linearization, Laplace transfer
  functions, PI control, Routh-Hurwitz. No advanced methods (no MPC, no nonlinear
  observers, no adaptive control) unless clearly labeled "beyond scope".

TECHNICAL CONSTRAINTS
- Hosted free on GitHub Pages. No backend server.
- Core model written in Python (numpy/scipy), run in the browser with Pyodide.
  The same Python module must run locally and be tested with pytest.
- Simple, readable code with comments that explain the chemical engineering.
  Prefer clarity over cleverness or performance.

MODEL SCOPE (propose details, state all assumptions)
1. Equilibrium: compute pH from a charge balance for (a) strong acid + strong base,
   required; (b) one weak acid such as acetic acid, to show buffering, required
   but in a later milestone. 25 °C, ideal solutions.
2. Titration curve and process gain: plot pH vs. reagent-to-influent ratio, and
   d(pH)/d(reagent flow) vs. pH.
3. Dynamics: continuous well-mixed neutralization tank(s), using reaction
   invariants (total acid and total base balances) with pH computed algebraically
   from the charge balance. Support 1 to 3 tanks in series.
4. Control: PI controller manipulating reagent flow, with valve limits (0 to max
   flow) and simple anti-windup, a first-order pH probe lag, and optional
   transport dead time. Disturbances: step changes in influent flow and
   concentration.
5. Linear analysis: linearize at a chosen operating point, give the transfer
   function, and use Routh-Hurwitz (proportional-only case) to show how the stable
   Kc range shrinks as the process gain grows. Plot stable Kc range vs. set point.
6. Design helper: given influent range and target pH band, compare 1, 2 and 3
   stage designs and report reagent valve rangeability needed. Any rule of thumb
   must cite a real, checkable source (textbook or standard); if you are not sure
   a source exists, say so instead of inventing one.

WEBSITE SECTIONS
- Home: one paragraph saying this is an AI project exploring AI capabilities, and
  what the tool does.
- Tool: inputs (influent acid/base type, concentration, flow; reagent; tank
  volumes; number of stages; controller tuning; disturbances) and plots
  (titration curve, gain vs. pH, closed-loop response, stable Kc range).
- Theory: each equation shown next to the exact Python code that implements it.
- AI Process, Model Comparison, Video and Transcript, What I Learned, References:
  placeholder pages I will fill in.

VERIFICATION (must be automated pytest tests, and listed in the plan)
- Strong acid/strong base: equivalence point at pH 7.00 (25 °C); pH at known
  points matches hand calculation.
- Weak acid: pH at half-equivalence equals pKa.
- Dynamic simulation reaches the same steady state as the algebraic solution.
- Small-step response matches the linearized transfer function.
- Proportional-only closed loop: simulated onset of sustained oscillation matches
  the Routh-Hurwitz Kc bound within a stated tolerance.

DELIVERABLES OF THIS PLAN
- Ask me clarifying questions first if anything important is ambiguous.
- Then give: the model equations and assumptions; file/folder structure; milestones
  in build order, each with acceptance criteria; the test list; risks (numerical
  stiffness near equivalence point, Pyodide load time, etc.) and how you'll handle
  them; and anything you recommend cutting to keep scope realistic for a student
  project of about 20 to 30 hours.
- Save the final plan as docs/PLAN_v1.md.
```

**AI's clarifying questions and the student's answers** (multiple choice):

| Question | Answer chosen |
|---|---|
| Which influent/reagent combinations? | Acidic influent only (Recommended) |
| How should plots be drawn? | Plotly.js (Recommended) |
| How should Routh–Hurwitz treat dead time? | Padé approx + note (Recommended) |

**Outcome:** wrote `docs/PLAN_v1.md`: equations E1–E4, T1–T3, D1–D6, C1–C2, L1–L6;
assumptions; file layout; 9 milestones (~28 h); 40+ planned tests; risks; cuts; references
split into "confident" and "not sure: verify or drop". Proposed three decisions for approval:
numpy-only core, an added valve lag (because tank + probe alone is never unstable under
P-only control), and one PI loop per stage.

## Prompt 2

```text
okay just do it all
```

**Outcome:** built the whole plan. Changed one decision while building: the model uses the
Python standard library only (numpy/scipy only in tests as independent checks), because the
container could not download numpy for in-browser testing and it made every line plainer.
71 tests; website verified in a headless browser.

## Prompt 3

```text
Deploy it
```

**Outcome:** the AI's attempt to create a GitHub repository was blocked by the session's
permission system; it committed locally and asked the student to create the repository.

## Prompt 4

```text
okay its ready
```

**Outcome:** pushed to GitHub; CI ran 71 tests on GitHub's servers and deployed the site.

## Prompt 5

```text
Now decorate it and make the website look awesome
```

**Outcome:** full redesign: fonts, light/dark theme, colorblind-checked chart colors, scenario
buttons, KPI tiles, process diagram.

## Prompt 6

```text
MUCH MORE GRAPHICS AND MORE APPEALING LOOKING
```

**Outcome:** universal-indicator color scheme; animated plant view (tanks colored by simulated
pH); interactive beaker; illustrated "three reasons pH control is hard"; control-loop block
diagram. Home page data precomputed from the Python model at build time.

## Prompt 7

```text
What is left to do on the project
```

**Outcome:** list split into "only you can do", "cleanup I can do", "optional".

## Prompt 8

```text
Yes do everything left you have to do then provide a list of what I have to do
```

**Outcome:** Home page numbers computed by the build; Python moved to a Web Worker; shared
page header/footer; acetic-acid design scenario; browser test added to CI (first test
against the real CDN: passed); 74 tests.

## Prompt 9

```text
Did I not mention that I have to compare this against a different AI
```

**Outcome:** AI acknowledged it had treated "Model Comparison" as a page to fill in without
asking what it meant; proposed a fair comparison method (same prompt, fixed reference cases,
rubric) and noted it should not grade its own work against another AI's.

## Prompt 10

```text
Tell me everything I should do before handing this over to another AI for the critique which
should be like the last step before making the video
```

**Outcome:** ordered checklist: finish own text, understand the work, list known weaknesses,
freeze a version, package the code, write a neutral critique prompt, record the session,
verify every finding before accepting it.

## Prompt 11

```text
Give me links to everything I need to check and tell me what im looking for then I will tell
you which ones to cross off
```

**Outcome:** 32 numbered items with direct links (live pages, code lines, citations).

## Prompt 12

The student quoted items 24–30 of that list, then wrote:

```text
you can do all this just give me the sources I need to verify then once I verify them all I
will give to another AI to critique the plan and implement it and provide new code for you to
compare with then you can make adjustments based on the critique and comparison and then you
will put them all in the AI process along with our prompts the comparison and the other AI
prompts which I will provide to you to put in there
```

**Outcome:** wrote `docs/HAND_CALCULATIONS.md` (items 24–27), ran the suite (74 passed),
added "Known limitations" to the README (items 29–30), started this log.

---

## Mistakes the AI made, and how each was caught

Useful for the AI Process page: none of these reached the live site.

| What went wrong | Caught by |
|---|---|
| Finite-difference gain test failed: the check itself was too coarse (solver tolerance 1e-10, then a step size too large for a gain that changes ×10 per pH) | the test failing; fixed the test's precision, not the formula |
| Time-step test compared two runs that were secretly the same step (dt was capped at τ<sub>v</sub>/10) | the test crashing on mismatched lengths |
| Padé root check picked the wrong complex pair of roots | the test; the model's ω<sub>u</sub> matched the correct pair exactly |
| "Small-step" test used a step too big for a nonlinear process (gain changes 11 % over the step) | the test; step reduced to 0.01 % |
| Dead-time test assumed 10 steps when dt had been capped (20 steps) | the test |
| Plots overflowed their cards; design cards overflowed on phones | screenshots / automated overflow check |
| Windup scenario so undersized it never recovered, so it did not demonstrate windup | reviewing the scenario's numbers |
| Animation timestamps could go negative (plant view crash; count-up showing "−64") | browser test console errors / reading the numbers |
| Interpreted "Model Comparison" without asking what it meant | the student |
| With acetic acid, every default staging design is infeasible | design-helper output; kept as a scenario and a stated limitation |
