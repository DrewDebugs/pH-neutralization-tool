# Hand calculations behind the key tests

Each section reworks one automated test by hand, so the result can be checked with a
calculator, without trusting the code. Every number below was also computed by the model;
they agree to the digits shown. Constants: K<sub>w</sub> = 1.0×10⁻¹⁴, K<sub>a</sub>(acetic) = 1.75×10⁻⁵
(pK<sub>a</sub> = 4.757).

---

## 1. Strong acid: 0.01 M HCl → pH 2.00, and 1×10⁻⁸ M HCl → pH 6.98 (tests C3, C4)

**Charge balance** (positive = negative), with no sodium:

  [H⁺] = [Cl⁻] + [OH⁻] = a + K<sub>w</sub>/[H⁺]

Multiply by [H⁺]: &nbsp; [H⁺]² − a[H⁺] − K<sub>w</sub> = 0 &nbsp; → &nbsp; [H⁺] = (a + √(a² + 4K<sub>w</sub>)) / 2

**0.01 M:** √(10⁻⁴ + 4×10⁻¹⁴) ≈ 0.0100000000002, so [H⁺] = 0.0100000 → **pH = 2.000**.
Water's own contribution (K<sub>w</sub>/[H⁺] = 10⁻¹² M) is ten orders of magnitude too small to matter.

**1×10⁻⁸ M:** the shortcut "pH = −log(10⁻⁸) = 8" is impossible: adding acid to water
cannot make it basic. The full quadratic:

  [H⁺] = (10⁻⁸ + √(10⁻¹⁶ + 4×10⁻¹⁴)) / 2 = (10⁻⁸ + 2.0025×10⁻⁷) / 2 = 1.0512×10⁻⁷ M

  **pH = 6.978** &nbsp; (model: 6.9783)

*Why it matters:* the acid is now smaller than water's own 10⁻⁷ M of H⁺, so the
K<sub>w</sub> term dominates. A model that drops K<sub>w</sub> fails this test, and the same term is what
sets the pH near neutral in the tanks.

---

## 2. Weak acid: half-equivalence → pH = pK<sub>a</sub>, but only when concentrated (tests W2, W3)

At half-equivalence, sodium b = w/2 (half the acetic acid has been neutralized).
Charge balance: [H⁺] + b = [OH⁻] + [A⁻]. In acid solution [OH⁻] is negligible, so

  [A⁻] = b + [H⁺], &nbsp;&nbsp; [HA] = w − [A⁻] = b − [H⁺]

Put these in K<sub>a</sub> = [H⁺][A⁻]/[HA]:

  K<sub>a</sub>(b − [H⁺]) = [H⁺](b + [H⁺]) &nbsp; → &nbsp; [H⁺]² + (b + K<sub>a</sub>)[H⁺] − K<sub>a</sub>b = 0

**w = 0.1 M (b = 0.05):** [H⁺] = 1.7488×10⁻⁵ M → **pH = 4.757**, equal to pK<sub>a</sub> (4.757).
[H⁺] is 0.035 % of b, so [A⁻] ≈ [HA] and the Henderson–Hasselbalch shortcut holds.

**w = 1×10⁻⁴ M (b = 5×10⁻⁵):**
[H⁺]² + 6.75×10⁻⁵ [H⁺] − 8.75×10⁻¹⁰ = 0 → [H⁺] = 1.1128×10⁻⁵ M → **pH = 4.954**,
which is **0.20 above pK<sub>a</sub>** (model: 4.9536).

*Why:* now [H⁺] (1.1×10⁻⁵) is 22 % of b (5×10⁻⁵), so [A⁻] = b + [H⁺] and [HA] = b − [H⁺]
are no longer equal. "pH = pK<sub>a</sub> at half-equivalence" is a shortcut that assumes
[H⁺] ≪ b; test W3 documents where it breaks.

---

## 3. Routh–Hurwitz vs simulation at set point 4 (test L5)

**Operating point** (default case: 0.01 M HCl at 36 m³/h = 0.01 m³/s, 1 M NaOH, V = 10 m³):
reagent flow for pH 4 = 9.899×10⁻⁵ m³/s (0.3564 m³/h), so Q = 0.010099 m³/s and

  τ = V/Q = 10 / 0.010099 = **990.2 s**

Process gain (slope of the titration curve, equation T3): K<sub>p</sub> = 4.3008×10⁵ pH per m³/s
(= 119.5 pH per m³/h).

**Characteristic equation**, P-only, valve lag τ<sub>v</sub> = 5 s, probe lag τ<sub>m</sub> = 15 s:

  (τ<sub>v</sub>s + 1)(τs + 1)(τ<sub>m</sub>s + 1) + K<sub>c</sub>K<sub>p</sub> = 0 &nbsp;→&nbsp; a₃s³ + a₂s² + a₁s + (1 + K<sub>c</sub>K<sub>p</sub>) = 0

| coefficient | formula | value |
|---|---|---|
| a₃ | τ<sub>v</sub>·τ·τ<sub>m</sub> | 5 × 990.2 × 15 = 74,265 s³ |
| a₂ | τ<sub>v</sub>τ + τ<sub>v</sub>τ<sub>m</sub> + ττ<sub>m</sub> | 4,951 + 75 + 14,853 = 19,879 s² |
| a₁ | τ<sub>v</sub> + τ + τ<sub>m</sub> | 1,010.2 s |

**Routh array:**

| row | column 1 | column 2 |
|---|---|---|
| s³ | a₃ | a₁ |
| s² | a₂ | 1 + K<sub>c</sub>K<sub>p</sub> |
| s¹ | (a₂a₁ − a₃(1 + K<sub>c</sub>K<sub>p</sub>)) / a₂ | 0 |
| s⁰ | 1 + K<sub>c</sub>K<sub>p</sub> | |

All of a₃, a₂, 1 + K<sub>c</sub>K<sub>p</sub> are positive for K<sub>c</sub> > 0, so stability only needs the s¹ entry > 0:

  K<sub>c</sub>K<sub>p</sub> < a₁a₂/a₃ − 1 = 270.41 − 1 = 269.41

  **K<sub>c,u</sub> = 269.41 / 4.3008×10⁵ = 6.264×10⁻⁴ (m³/s)/pH** (= 2.255 (m³/h)/pH)

At K<sub>c,u</sub> the s¹ row is zero; the s² row gives the auxiliary equation
a₂s² + (1 + K<sub>c,u</sub>K<sub>p</sub>) = 0 → s = ±jω<sub>u</sub> with ω<sub>u</sub>² = a₁/a₃ (using 1 + K<sub>c,u</sub>K<sub>p</sub> = a₁a₂/a₃):

  ω<sub>u</sub> = √(1010.2 / 74,265) = 0.1166 rad/s, &nbsp; **P<sub>u</sub> = 2π/ω<sub>u</sub> = 53.87 s**

Note P<sub>u</sub> contains no K<sub>p</sub>: the oscillation period is set by the lags only, while the
gain limit is divided by the chemistry (K<sub>p</sub>).

**The brute-force check** (`src/phsim/verify.py`): simulate the full nonlinear model under
P-only control after a 0.01 % flow upset, and compare the peak-to-peak pH swing early in the
run with the swing at the end. Grows → unstable; shrinks → stable. Start between 0.7 and
1.3 × the Routh value and halve the interval 9 times (bisection).

  Result: simulated K<sub>c,u</sub> = 6.268×10⁻⁴ (**0.06 %** from Routh), period 53.87 s.

The small gap comes from the simulation being nonlinear and digital (0.1 s steps), while
Routh is exact for the linearized, continuous model. With a 10 s dead time (test L7), the Padé
estimate (1.898×10⁻⁴) differs from simulation with a true delay (1.863×10⁻⁴) by **1.8 %**,
because Padé is an approximation of e<sup>−θs</sup>.

---

## 4. Anti-windup (test K4)

**Setup:** set point pH 4, Ziegler–Nichols PI (K<sub>c</sub> = 0.45 K<sub>c,u</sub> = 2.819×10⁻⁴ (m³/s)/pH,
τ<sub>I</sub> = P<sub>u</sub>/1.2 = 44.9 s). The valve is deliberately small: maximum 0.4276 m³/h, only 1.2 × the
nominal demand of 0.3564 m³/h.

**Upset:** at t = 60 s the HCl doubles to 0.02 M, so the demand (≈0.71 m³/h) is far beyond the
valve. The valve sits wide open and pH falls to 2.21 either way: no controller can fix this.
At t = 1500 s the HCl returns to 0.01 M.

**What differs is the recovery** (peak pH after t = 1500 s):

| | peak pH after the upset ends |
|---|---|
| with anti-windup (conditional integration) | **4.14** (small overshoot above SP 4) |
| without anti-windup | **9.97** (massive overshoot) |

**Why:** for ~24 minutes the error e = SP − pH was about +1.8. Without anti-windup the integral
∫e dt keeps growing the whole time, even though the valve can't open further. When the upset
ends, that huge integral holds the valve wide open long after the pH has recovered, which
drives the tank far into the basic region. With conditional integration, the integral is frozen
whenever the valve is saturated *and* the error would push it further into saturation, so there
is nothing to unwind.

The test passes if the anti-windup peak is lower and the overshoot without it is more than
twice as large (it is 5.97 vs 0.14 pH units above set point).
