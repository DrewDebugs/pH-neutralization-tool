"""Equilibrium tests C1-C8 (strong acid / strong base) and W1-W4 (acetic acid)."""
import math

import numpy as np
import pytest
from scipy.optimize import brentq

from phsim.chemistry import (buffer_capacity, charge_balance_residual,
                             pH_sensitivities, solve_pH)
from phsim.constants import KA_ACETIC, KW


def closed_form_strong_pH(a, b):
    """Quadratic solution of [H+] + b = Kw/[H+] + a, in the form that avoids
    subtracting two nearly equal numbers (the hand calculation)."""
    d = a - b
    if d >= 0:
        h = d / 2 + math.sqrt((d / 2) ** 2 + KW)
    else:
        h = 2 * KW / (-d + math.sqrt(d * d + 4 * KW))
    return -math.log10(h)


# ---- C1-C5: hand calculations --------------------------------------------
def test_C1_pure_water_is_pH_7():
    assert solve_pH(0.0, 0.0) == pytest.approx(7.0, abs=1e-6)


@pytest.mark.parametrize("c", [1e-4, 1e-2, 1.0])
def test_C2_equivalence_point_is_pH_7(c):
    assert solve_pH(c, c) == pytest.approx(7.0, abs=1e-6)


@pytest.mark.parametrize("c, expected", [(0.01, 2.0), (0.001, 3.0)])
def test_C3_strong_acid(c, expected):
    assert solve_pH(c, 0.0) == pytest.approx(expected, abs=1e-3)


def test_C4_very_dilute_acid_is_not_pH_8():
    # 1e-8 M HCl: water's own H+ (1e-7) dominates. Answer 6.978, not 8.
    assert solve_pH(1e-8, 0.0) == pytest.approx(6.978, abs=1e-3)


def test_C5_partial_and_over_neutralization():
    assert solve_pH(0.01, 0.009) == pytest.approx(3.0, abs=1e-3)   # 0.001 M acid left
    assert solve_pH(0.01, 0.02) == pytest.approx(12.0, abs=1e-3)   # 0.01 M base left


# ---- C6-C8: independent cross-checks ---------------------------------------
def test_C6_bisection_matches_closed_form_on_grid():
    grid = np.logspace(-8, 0, 50)
    worst = max(abs(solve_pH(a, b) - closed_form_strong_pH(a, b))
                for a in grid for b in grid)
    assert worst < 1e-8


@pytest.mark.parametrize("a, b, w", [(0.01, 0.0, 0.0), (0.0, 0.05, 0.1),
                                     (0.003, 0.004, 0.02), (1e-6, 0.0, 1e-5)])
def test_C7_bisection_matches_scipy_brentq(a, b, w):
    reference = brentq(lambda p: charge_balance_residual(p, a, b, w), -2, 16, xtol=1e-14)
    assert solve_pH(a, b, w) == pytest.approx(reference, abs=1e-8)


@pytest.mark.parametrize("pH", [2.0, 4.0, 4.76, 7.0, 9.0, 12.0])
@pytest.mark.parametrize("w", [0.0, 0.05])
def test_C8_buffer_capacity_equals_minus_dg_dpH(pH, w):
    d = 1e-6
    numeric = -(charge_balance_residual(pH + d, 0, 0, w)
                - charge_balance_residual(pH - d, 0, 0, w)) / (2 * d)
    assert buffer_capacity(pH, w) == pytest.approx(numeric, rel=1e-5)


def test_charge_balance_is_satisfied_at_solution():
    pH = solve_pH(0.01, 0.0099, 0.002)
    assert abs(charge_balance_residual(pH, 0.01, 0.0099, 0.002)) < 1e-12


def test_pH_rises_with_sodium():
    pHs = [solve_pH(0.01, b) for b in np.linspace(0, 0.02, 41)]
    assert all(later > earlier for earlier, later in zip(pHs, pHs[1:]))


def test_sensitivities_match_finite_differences():
    a, b, w = 0.004, 0.003, 0.01
    pH = solve_pH(a, b, w)
    dpH_da, dpH_db, dpH_dw = pH_sensitivities(pH, w)
    d = 1e-8
    ph = lambda a, b, w: solve_pH(a, b, w, tol=1e-14)   # tight tolerance for differencing
    assert dpH_da == pytest.approx((ph(a + d, b, w) - ph(a - d, b, w)) / (2 * d), rel=1e-5)
    assert dpH_db == pytest.approx((ph(a, b + d, w) - ph(a, b - d, w)) / (2 * d), rel=1e-5)
    assert dpH_dw == pytest.approx((ph(a, b, w + d) - ph(a, b, w - d)) / (2 * d), rel=1e-5)


# ---- W1-W4: weak acid ---------------------------------------------------------
def test_W1_acetic_acid_alone():
    # Hand calc: [H+]^2/(C-[H+]) = Ka  ->  [H+] = (-Ka + sqrt(Ka^2 + 4 Ka C))/2
    C = 0.1
    h = (-KA_ACETIC + math.sqrt(KA_ACETIC ** 2 + 4 * KA_ACETIC * C)) / 2
    assert -math.log10(h) == pytest.approx(2.881, abs=2e-3)
    assert solve_pH(0.0, 0.0, C) == pytest.approx(-math.log10(h), abs=2e-3)


def test_W2_half_equivalence_pH_equals_pKa():
    pKa = -math.log10(KA_ACETIC)
    assert solve_pH(0.0, 0.05, 0.1) == pytest.approx(pKa, abs=0.01)


def test_W3_pH_equals_pKa_fails_when_dilute():
    # At 1e-4 M, [H+] (~1e-5) is not small compared with [A-] (5e-5), so the
    # Henderson-Hasselbalch shortcut is wrong by ~0.2 pH. A teaching test.
    pKa = -math.log10(KA_ACETIC)
    assert solve_pH(0.0, 0.5e-4, 1e-4) - pKa > 0.1


def test_W4_sodium_acetate_equivalence_point():
    # 0.05 M sodium acetate: [OH-] = sqrt(Kb C), Kb = Kw/Ka
    C = 0.05
    oh = math.sqrt(KW / KA_ACETIC * C)
    expected = 14 + math.log10(oh)
    assert expected == pytest.approx(8.73, abs=0.02)
    assert solve_pH(0.0, C, C) == pytest.approx(expected, abs=0.02)
