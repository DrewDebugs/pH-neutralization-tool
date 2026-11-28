# Reference checklist

Every citation used in the project, what it supports, and its status. **Nothing marked
"unverified" is used in any calculation.** Before submission, find each source (library,
Google Books, publisher site), write the edition and page, and change the status.

| # | Source | Used for | Where in project | Status |
|---|---|---|---|---|
| 1 | Seborg, Edgar, Mellichamp & Doyle, *Process Dynamics and Control*, 4th ed., Wiley, 2016 | Linearization, transfer functions, Routh array, Padé approximation, PI control | `linear.py`, Theory page | **4th edition confirmed** (student's copy). **Padé: verified**: Section 6.2, p. 91, Eq. 6-29 (1/1 Padé) = the formula in `linear.loop_polynomials`. **Routh: verified**: Section 11.4.2 (printed page ☐); the text states that replacing e^(−θs) by a Padé approximation gives an *approximate* Routh analysis (our method for dead time), and (Section 11.4.1, after Eq. 11-91) that a stable 1st- or 2nd-order open loop with no time delay is stable for all positive Kc (our reason for the valve lag; test L8). **Ziegler–Nichols**: index gives printed pp. 211, 215; PI factors ☐ |
| 2 | Ziegler & Nichols, "Optimum settings for automatic controllers," *Trans. ASME* 64 (1942) 759–768 | PI tuning Kc = 0.45 Kc,u, τI = Pu/1.2 | `linear.ziegler_nichols_pi`, Auto-tune button | Exists (confident). Confirm the 0.45 and 1/1.2 factors in the paper or in ref 1: ☐ |
| 3 | Harris, *Quantitative Chemical Analysis*, W. H. Freeman | Charge balance method, Kw = 1.0e-14 at 25 °C, acetic acid pKa = 4.757 | `constants.py`, `chemistry.py` | Exists (confident). Edition + table/page for pKa: ☐ |
| 4 | Shinskey, *pH and pIon Control in Process and Waste Streams*, Wiley, 1973 | Background on why pH control is hard; staging | References page only | Exists (confident). Nothing quoted yet. |
| 5 | McMillan, *pH Measurement and Control*, ISA (2nd ed. 1994) | Background; possible rules of thumb | References page only | Exists (confident). Check for later editions: ☐ |
| 6 | Liptak (ed.), *Instrument Engineers' Handbook*, Vol. 2, CRC Press | pH-control chapter | References page only | Exists; edition/chapter unverified: ☐ |
| 7 | 40 CFR 133.102(c) | Default final band pH 6.0–9.0 (POTW secondary treatment) | Design helper defaults | Believed correct; check eCFR text: ☐. Industrial discharges follow their permit. |
| 8 | Gustafsson & Waller, *Chem. Eng. Sci.* 38 (1983) 389–398 | Origin of the reaction-invariant model | References page only | **Unverified** — check or drop |
| 9 | McAvoy, Hsu & Lowenthal, *Ind. Eng. Chem. Process Des. Dev.* 11 (1972) 68–70 | Early pH CSTR dynamics | References page only | **Unverified** — check or drop |

## Rules of thumb NOT used (and not to be stated as fact unless found with a page number)

- Number of stages required for a given influent pH.
- Minimum residence time, or mixing-time / dead-time-to-residence-time ratios, for neutralization tanks.
- Typical achievable control valve rangeability and resolution. (The tool's defaults —
  50:1 and 0.5 % — are labeled "assumed"; replace them with vendor data or a cited value.)
- Intermediate set points of the default 2- and 3-stage designs (pH 4; pH 3 and 4.5) are
  illustrative choices made for this project, not literature values.
