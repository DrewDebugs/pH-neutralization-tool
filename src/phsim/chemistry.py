"""Equilibrium chemistry: pH from a charge balance (equations E1-E4).

The solution is described by three "reaction invariants" (all mol/L):
    a = total chloride   [Cl-]            (from HCl, fully dissociated)
    b = total sodium     [Na+]            (from NaOH, fully dissociated)
    w = total acetate    [HA] + [A-]      (acetic acid, partly dissociated)

Neutralization reactions (H+ + OH- -> H2O, H+ + A- <-> HA) shuffle H+ around
but can never create or destroy Cl, Na or total acetate. So a, b, w are set
only by mixing, and pH follows from them algebraically.
"""

from .constants import KW, KA_ACETIC, LN10

# Bracket for the pH search. pH -2 means [H+] = 100 mol/L and pH 16 means
# [OH-] = 100 mol/L: no real solution lies outside this range.
PH_LOW = -2.0
PH_HIGH = 16.0


def fraction_ionized(pH, ka=KA_ACETIC):
    """(E2) alpha = [A-]/([HA]+[A-]) = Ka / (Ka + [H+]).

    alpha -> 0 at low pH (acid stays as HA), alpha -> 1 at high pH.
    alpha = 0.5 exactly when [H+] = Ka, i.e. pH = pKa.
    """
    h = 10.0 ** (-pH)
    return ka / (ka + h)


def charge_balance_residual(pH, a, b, w=0.0, ka=KA_ACETIC):
    """(E3) g(pH) = positive charge - negative charge (mol/L).

    Positive ions: H+ and Na+.  Negative ions: OH-, Cl-, A-.
        g = [H+] + b - [OH-] - a - [A-]
    with [OH-] = Kw/[H+] (E1) and [A-] = w*alpha (E2).

    The true pH is where g = 0 (the solution is electrically neutral).
    As pH rises, [H+] falls and [OH-] and [A-] rise, so g strictly
    DECREASES with pH. That guarantees exactly one root.
    """
    h = 10.0 ** (-pH)        # [H+]
    oh = KW / h              # [OH-]   (E1)
    acetate = w * ka / (ka + h)  # [A-] (E2)
    return h + b - oh - a - acetate


def solve_pH(a, b, w=0.0, ka=KA_ACETIC, tol=1e-10):
    """Find the pH where the charge balance is satisfied, by bisection.

    Bisection: keep a bracket [low, high] that contains the root, and halve
    it each iteration. Because g(pH) is strictly decreasing:
        g(mid) > 0  -> too much positive charge -> too much H+ -> the true
                       pH is HIGHER than mid -> move the low end up.
        g(mid) <= 0 -> the true pH is lower -> move the high end down.
    18 pH units / 2**38 < 1e-10, so ~38 halvings. It cannot diverge.

    We search in pH (a log scale) rather than [H+] so that the problem is
    equally well-scaled at pH 1 and pH 13.
    """
    low, high = PH_LOW, PH_HIGH
    while high - low > tol:
        mid = 0.5 * (low + high)
        if charge_balance_residual(mid, a, b, w, ka) > 0.0:
            low = mid
        else:
            high = mid
    return 0.5 * (low + high)


def buffer_capacity(pH, w=0.0, ka=KA_ACETIC):
    """(E4) beta = mol/L of strong base needed per unit rise in pH.

    beta = ln(10) * ( [H+] + [OH-] + w*Ka*[H+]/(Ka+[H+])**2 )

    Derivation: beta = -d(g)/d(pH). Each term of g differentiated w.r.t. pH:
        d[H+]/dpH  = -ln10*[H+]
        d[OH-]/dpH = +ln10*[OH-]
        d[A-]/dpH  = +ln10 * w*Ka*[H+]/(Ka+[H+])**2
    A large beta means the solution resists pH change ("buffered").
    For a strong acid only, beta is smallest at pH 7, where both [H+] and
    [OH-] are tiny -> that is why pH 7 is so hard to control.
    """
    h = 10.0 ** (-pH)
    oh = KW / h
    weak_acid_term = w * ka * h / (ka + h) ** 2
    return LN10 * (h + oh + weak_acid_term)


def pH_sensitivities(pH, w=0.0, ka=KA_ACETIC):
    """Partial derivatives of pH w.r.t. the invariants (a, b, w).

    From implicit differentiation of g(pH, a, b, w) = 0:
        dpH/dx = -(dg/dx) / (dg/dpH) = (dg/dx) / beta
    and dg/db = +1, dg/da = -1, dg/dw = -alpha. So
        dpH/da = -1/beta,  dpH/db = +1/beta,  dpH/dw = -alpha/beta.
    Used for linearization (L1, L2).
    """
    beta = buffer_capacity(pH, w, ka)
    alpha = fraction_ionized(pH, ka)
    return -1.0 / beta, 1.0 / beta, -alpha / beta
