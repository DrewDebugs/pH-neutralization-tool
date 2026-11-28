# Reference checklist

Every citation used in the project, what it supports, and its status. **Nothing marked
"unverified" is used in any calculation.** Before submission, find each source (library,
Google Books, publisher site), write the edition and page, and change the status.

| # | Source | Used for | Where in project | Status |
|---|---|---|---|---|
| 1 | Seborg, Edgar, Mellichamp & Doyle, *Process Dynamics and Control*, 4th ed., Wiley, 2016 | Linearization, transfer functions, Routh array, Padé approximation, PI control | `linear.py`, Theory page | **4th edition confirmed** (student's copy). **Padé: verified**: Section 6.2, p. 91, Eq. 6-29 (1/1 Padé) = the formula in `linear.loop_polynomials`. **Routh: verified**: Section 11.4.2 (printed page ☐); the text states that replacing e^(−θs) by a Padé approximation gives an *approximate* Routh analysis (our method for dead time), and (Section 11.4.1, after Eq. 11-91) that a stable 1st- or 2nd-order open loop with no time delay is stable for all positive Kc (our reason for the valve lag; test L8). **Ziegler–Nichols**: Section 12.3 cites Ziegler & Nichols (1942) and states the rules give a 1/4 decay ratio, "considered to be excessively oscillatory" (supports the README warning). **Continuous-cycling PI factors: verified**, Table 12.7 (PI: Kc = 0.45 Kcu, τI = Pu/1.2) = `linear.ziegler_nichols_pi`. Printed pages for Routh / Table 12.7 ☐ (optional) |
| 2 | Ziegler & Nichols, "Optimum settings for automatic controllers," *Trans. ASME* 64 (1942) 759–768 | PI tuning Kc = 0.45 Kc,u, τI = Pu/1.2 | `linear.ziegler_nichols_pi`, Auto-tune button | **Cited by Seborg 4th ed., Section 12.3** (year 1942 confirmed). Full entry from Seborg's reference list ☐. **Factors verified via Seborg Table 12.7.** Full entry from Seborg's reference list ☐ |
| 3 | Harris, *Quantitative Chemical Analysis*, W. H. Freeman | Charge balance method, Kw = 1.0e-14 at 25 °C, acetic acid pKa = 4.757 | `constants.py`, `chemistry.py` | Solutions manual (Ch. 9, "Monoprotic Acid-Base Equilibria", answers 9-27 to 9-30) confirms pH = pKa + log([A⁻]/[HA]) and the buffer-capacity concept. **pKa verified**: answer 9-41 states "pKa for acetic acid is 4.756" (Ka = 1.754×10⁻⁵). The model's Ka = 1.75×10⁻⁵ (pKa 4.757) is that value rounded to 3 significant figures; effect ≤ 0.001 pH. Edition of the student's copy ☐ |
| 4 | Shinskey, *pH and pIon Control in Process and Waste Streams*, Wiley, 1973 | Background on why pH control is hard; staging | References page only | Exists (confident). Nothing quoted yet. |
| 5 | McMillan, *pH Measurement and Control*, ISA (2nd ed. 1994) | Background; possible rules of thumb | References page only | Exists (confident). Check for later editions: ☐ |
| 6 | Liptak (ed.), *Instrument Engineers' Handbook*, Vol. 2, CRC Press | pH-control chapter | References page only | Seborg 4th ed. cites "Lipták, 2006" (Table 12.4). Full entry from Seborg's reference list ☐; pH chapter ☐ |
| 7 | 40 CFR 133.102(c) | Default final band pH 6.0–9.0 (POTW secondary treatment) | Design helper defaults | **Verified** (eCFR text): "The effluent values for pH shall be maintained within the limits of 6.0 to 9.0 unless the publicly owned treatment works demonstrates that…" [49 FR 37006, Sept. 20, 1984; 49 FR 40405, Oct. 16, 1984]. Applies to POTWs and allows exceptions; industrial discharges follow their permit. |
| 8 | Gustafsson & Waller, *Chem. Eng. Sci.* 38 (1983) 389–398 | Origin of the reaction-invariant model | References page only | **Unverified** — check or drop |
| 9 | McAvoy, Hsu & Lowenthal, *Ind. Eng. Chem. Process Des. Dev.* 11 (1972) 68–70 | Early pH CSTR dynamics | References page only | **Unverified** — check or drop |

## Rules of thumb NOT used (and not to be stated as fact unless found with a page number)

- Number of stages required for a given influent pH.
- Minimum residence time, or mixing-time / dead-time-to-residence-time ratios, for neutralization tanks.
- Typical achievable control valve rangeability and resolution. (The tool's defaults —
  50:1 and 0.5 % — are labeled "assumed"; replace them with vendor data or a cited value.)
- Intermediate set points of the default 2- and 3-stage designs (pH 4; pH 3 and 4.5) are
  illustrative choices made for this project, not literature values.
