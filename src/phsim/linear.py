"""Linearization, transfer functions and Routh-Hurwitz stability (L1-L6).

Polynomials are plain Python lists of coefficients, HIGHEST power first:
    [3, 2, 1]  means  3 s^2 + 2 s + 1
"""

import math

from .chemistry import pH_sensitivities
from .titration import mix_with_reagent, reagent_for_pH, influent_stream


# ---------------------------------------------------------------- polynomials
def poly_mul(p, q):
    """Product of two polynomials (like multiplying out brackets by hand)."""
    result = [0.0] * (len(p) + len(q) - 1)
    for i, pi in enumerate(p):
        for j, qj in enumerate(q):
            result[i + j] += pi * qj
    return result


def poly_add(p, q):
    """Sum of two polynomials of possibly different length."""
    n = max(len(p), len(q))
    p = [0.0] * (n - len(p)) + list(p)
    q = [0.0] * (n - len(q)) + list(q)
    return [pi + qi for pi, qi in zip(p, q)]


def poly_trim(p):
    """Drop leading zero coefficients (e.g. from a lag with tau = 0)."""
    i = 0
    while i < len(p) - 1 and p[i] == 0.0:
        i += 1
    return p[i:]


# ------------------------------------------------------------ linearization
def linearize_stage(inlet, FR, CR, V):
    """(L1, L2) Linear model of one stage around steady state.

    Deviation form of (D1-D3): every invariant x obeys
        V dx'/dt = -Q x' + (dx/dFR)*Q * FR'  (+ inlet terms)
    so all three share ONE time constant tau = V/Q, and
        pH' = dpH/da a' + dpH/db b' + dpH/dw w'
    gives G_p(s) = Kp / (tau s + 1). Kp is found with the chain rule:
        Kp = sum_x (dpH/dx) * (dx/dFR),  dx/dFR from mixing (T1):
        da/dFR = -a/Q,  db/dFR = (CR - b)/Q,  dw/dFR = -w/Q
    Kp equals the titration-curve slope (T3): same physics, two routes.

    Disturbance gains for the influent of this stage:
        flow:  dx/dQ_in = (x_in - x)/Q
        HCl:   da/da_in = Q_in/Q ;  acetic: dw/dw_in = Q_in/Q
    """
    out = mix_with_reagent(inlet, FR, CR)
    Q = out.Q
    dpH_da, dpH_db, dpH_dw = pH_sensitivities(out.pH, out.w)

    Kp = (dpH_da * (-out.a / Q) + dpH_db * ((CR - out.b) / Q)
          + dpH_dw * (-out.w / Q))
    K_flow = (dpH_da * (inlet.a - out.a) + dpH_db * (inlet.b - out.b)
              + dpH_dw * (inlet.w - out.w)) / Q
    K_Ca = dpH_da * inlet.Q / Q
    K_Cw = dpH_dw * inlet.Q / Q
    return {"Kp": Kp, "tau": V / Q, "K_flow": K_flow, "K_Ca": K_Ca,
            "K_Cw": K_Cw, "pH": out.pH, "Q": Q}


# ------------------------------------------------------- transfer functions
def loop_polynomials(Kp, tau, tau_v, tau_m, theta):
    """(L3) Numerator and denominator of G_v * G_p * G_m (no controller).

    G_v = 1/(tau_v s + 1),  G_p = Kp/(tau s + 1),  G_m = e^(-theta s)/(tau_m s + 1)
    Dead time by 1st-order Pade: e^(-theta s) ~ (1 - theta s/2)/(1 + theta s/2)
    (APPROXIMATE; exact only as theta*omega -> 0).
    """
    num = [Kp]
    den = poly_mul(poly_mul([tau_v, 1.0], [tau, 1.0]), [tau_m, 1.0])
    if theta > 0.0:
        num = poly_mul(num, [-theta / 2.0, 1.0])
        den = poly_mul(den, [theta / 2.0, 1.0])
    return num, poly_trim(den)


def characteristic_polynomial(Kc, Kp, tau, tau_v, tau_m, theta=0.0, tauI=math.inf):
    """1 + Gc*G = 0 written as a polynomial = 0.

    P-only (Gc = Kc):              den + Kc*num = 0
    PI (Gc = Kc (tauI s + 1)/(tauI s)):  tauI s den + Kc (tauI s + 1) num = 0
    """
    num, den = loop_polynomials(Kp, tau, tau_v, tau_m, theta)
    if math.isinf(tauI):
        return poly_trim(poly_add(den, [Kc * c for c in num]))
    left = poly_mul([tauI, 0.0], den)
    right = poly_mul([Kc * tauI, Kc], num)
    return poly_trim(poly_add(left, right))


# ----------------------------------------------------------- Routh-Hurwitz
def routh_array(coeffs, eps=1e-12):
    """Build the Routh array (one list per row, rows s^n down to s^0).

    Row 1: a_n, a_(n-2), ...   Row 2: a_(n-1), a_(n-3), ...
    Each next entry uses the two rows above it (r1 = two rows up,
    r2 = one row up) -- the textbook rule:
        new[j] = (r2[0]*r1[j+1] - r1[0]*r2[j+1]) / r2[0]
    A zero in the first column is replaced by a tiny eps (standard trick).
    """
    n = len(coeffs) - 1
    width = n // 2 + 1
    row1 = [float(c) for c in coeffs[0::2]] + [0.0] * width
    row2 = [float(c) for c in coeffs[1::2]] + [0.0] * width
    rows = [row1[:width], row2[:width]]
    for _ in range(n - 1):
        r1, r2 = rows[-2], rows[-1]
        if r2[0] == 0.0:
            r2[0] = eps
        new = [(r2[0] * r1[j + 1] - r1[0] * r2[j + 1]) / r2[0] for j in range(width - 1)]
        rows.append(new + [0.0])
    return rows


def is_stable(coeffs):
    """Routh criterion: stable iff every first-column entry has the same
    sign (and none is zero). Each sign change = one root in the right half
    plane.
    """
    coeffs = poly_trim(coeffs)
    if len(coeffs) == 1:
        return True
    first_column = [row[0] for row in routh_array(coeffs)]
    sign = 1.0 if coeffs[0] > 0 else -1.0
    return all(sign * c > 0.0 for c in first_column)


def ultimate_gain_cubic(Kp, tau, tau_v, tau_m):
    """(L4) Closed-form Routh result for P-only control, no dead time.

    Characteristic equation: a3 s^3 + a2 s^2 + a1 s + (1 + Kc Kp) = 0
        a3 = tau_v tau tau_m
        a2 = tau_v tau + tau_v tau_m + tau tau_m
        a1 = tau_v + tau + tau_m
    Routh row s^1 is positive iff a2 a1 > a3 (1 + Kc Kp), so
        Kc_u = (a1 a2 / a3 - 1) / Kp
    At Kc_u the s^2 row gives a2 s^2 + (1 + Kc_u Kp) = 0
        -> omega_u = sqrt(a1 / a3),  P_u = 2 pi / omega_u
    If tau_v or tau_m is 0 the loop is only 2nd order: stable for any
    Kc > 0, and we return infinity.
    """
    a3 = tau_v * tau * tau_m
    a2 = tau_v * tau + tau_v * tau_m + tau * tau_m
    a1 = tau_v + tau + tau_m
    if a3 == 0.0:
        return math.inf, None, None
    Kcu = (a1 * a2 / a3 - 1.0) / Kp
    omega = math.sqrt(a1 / a3)
    return Kcu, omega, 2.0 * math.pi / omega


def ultimate_gain(Kp, tau, tau_v, tau_m, theta=0.0):
    """Largest stable P-only gain Kc_u and the oscillation period P_u.

    No dead time -> exact closed form (L4).
    Dead time -> Pade (L5): bisection on Kc using the Routh test, then
    omega_u from the auxiliary polynomial (the s^2 row: A s^2 + B = 0).
    Returns (Kc_u, omega_u, P_u); Kc_u = inf if never unstable.
    """
    if theta <= 0.0:
        return ultimate_gain_cubic(Kp, tau, tau_v, tau_m)

    def stable(Kc):
        return is_stable(characteristic_polynomial(Kc, Kp, tau, tau_v, tau_m, theta))

    high = 1.0 / Kp
    while stable(high):
        high *= 2.0
        if high * Kp > 1e9:
            return math.inf, None, None
    low = 0.0
    for _ in range(100):
        mid = 0.5 * (low + high)
        if stable(mid):
            low = mid
        else:
            high = mid
    rows = routh_array(characteristic_polynomial(low, Kp, tau, tau_v, tau_m, theta))
    A, B = rows[-3][0], rows[-3][1]          # the s^2 row
    omega = math.sqrt(B / A)
    return low, omega, 2.0 * math.pi / omega


def ziegler_nichols_pi(Kcu, Pu):
    """Ziegler-Nichols (1942) closed-loop PI rule: Kc = 0.45 Kcu, tauI = Pu/1.2."""
    if math.isinf(Kcu):
        return math.inf, math.inf
    return 0.45 * Kcu, Pu / 1.2


# ---------------------------------------------- stable range vs set point
def kcu_vs_setpoint(F, Ca, Cw, CR, V, tau_v, tau_m, theta, setpoints):
    """(L6) For a single stage: Kp and Kc_u at each set point.

    Shows the main result: Kc_u = (lag-only number)/Kp, so the stable
    range shrinks by exactly the factor the titration slope grows.
    """
    influent = influent_stream(F, Ca, Cw)
    rows = []
    for SP in setpoints:
        try:
            FR = reagent_for_pH(influent, CR, SP)
        except ValueError:
            continue
        lin = linearize_stage(influent, FR, CR, V)
        Kcu, omega, Pu = ultimate_gain(lin["Kp"], lin["tau"], tau_v, tau_m, theta)
        rows.append({"SP": SP, "Kp": lin["Kp"], "tau": lin["tau"],
                     "Kcu": Kcu, "Pu": Pu})
    return rows
