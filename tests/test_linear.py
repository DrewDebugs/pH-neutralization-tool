"""Linear analysis and Routh-Hurwitz tests L1-L8."""
import math

import numpy as np
import pytest

from phsim.linear import (characteristic_polynomial, is_stable, kcu_vs_setpoint,
                          linearize_stage, ultimate_gain, ultimate_gain_cubic,
                          ziegler_nichols_pi)
from phsim import verify
from phsim.simulate import Instruments
from phsim.titration import influent_stream, process_gain, reagent_for_pH
from conftest import CA_DEFAULT, CR_DEFAULT, F_DEFAULT, V_DEFAULT

RNG = np.random.default_rng(12345)


def test_L1_linearized_gain_equals_titration_slope():
    for Cw in (0.0, 0.01):
        inlet = influent_stream(F_DEFAULT, CA_DEFAULT, Cw)
        for SP in np.linspace(3.0, 11.0, 10):
            FR = reagent_for_pH(inlet, CR_DEFAULT, SP)
            lin = linearize_stage(inlet, FR, CR_DEFAULT, V_DEFAULT)
            assert lin["Kp"] == pytest.approx(process_gain(inlet, FR, CR_DEFAULT), rel=1e-9)


def test_L2_routh_array_matches_textbook_cubic_condition():
    for _ in range(1000):
        a3, a2, a1, a0 = 10 ** RNG.uniform(-2, 3, 4) * RNG.choice([1, 1, 1, -1], 4)
        textbook = (a3 > 0 and a2 > 0 and a1 > 0 and a0 > 0 and a2 * a1 > a3 * a0) or \
                   (a3 < 0 and a2 < 0 and a1 < 0 and a0 < 0 and a2 * a1 > a3 * a0)
        if abs(a2 * a1 - a3 * a0) < 1e-9 * abs(a2 * a1):
            continue                                       # skip marginal cases
        assert is_stable([a3, a2, a1, a0]) == textbook


def test_L3_routh_matches_numpy_roots():
    checked = 0
    for _ in range(1000):
        degree = RNG.integers(2, 6)
        coeffs = list(10 ** RNG.uniform(-2, 2, degree + 1))
        largest_real = max(np.roots(coeffs).real)
        if abs(largest_real) < 1e-6:
            continue
        assert is_stable(coeffs) == (largest_real < 0)
        checked += 1
    assert checked > 900


def test_L4_roots_lie_on_imaginary_axis_at_ultimate_gain():
    Kp, tau, tau_v, tau_m = 3.0, 1000.0, 5.0, 15.0
    Kcu, omega, Pu = ultimate_gain_cubic(Kp, tau, tau_v, tau_m)
    roots = np.roots(characteristic_polynomial(Kcu, Kp, tau, tau_v, tau_m))
    pair = roots[np.argmax(roots.imag)]
    assert abs(pair.real) < 1e-6 * omega
    assert pair.imag == pytest.approx(omega, rel=1e-6)


def simulated_ultimate_gain(SP, ins, Kc_guess, Pu):
    """Default case; the bisection itself lives in phsim/verify.py."""
    return verify.simulated_ultimate_gain(F_DEFAULT, CA_DEFAULT, CR_DEFAULT, V_DEFAULT,
                                          SP, ins, Kc_guess, Pu)


def test_L5_simulated_onset_of_oscillation_matches_routh():
    ins = Instruments(tau_v=5.0, tau_m=15.0, theta=0.0)
    inlet = influent_stream(F_DEFAULT, CA_DEFAULT)
    FR = reagent_for_pH(inlet, CR_DEFAULT, 4.0)
    lin = linearize_stage(inlet, FR, CR_DEFAULT, V_DEFAULT)
    Kcu, _, Pu = ultimate_gain(lin["Kp"], lin["tau"], 5.0, 15.0)
    Kc_sim, period = simulated_ultimate_gain(4.0, ins, Kcu, Pu)
    print("Routh Kcu=%.4g  simulated=%.4g  (%.2f%%); Pu=%.2f s, sim=%.2f s"
          % (Kcu, Kc_sim, 100 * (Kc_sim / Kcu - 1), Pu, period))
    assert Kc_sim == pytest.approx(Kcu, rel=0.05)
    assert period == pytest.approx(Pu, rel=0.05)


def test_L6_stable_range_shrinks_near_neutral():
    rows = kcu_vs_setpoint(F_DEFAULT, CA_DEFAULT, 0.0, CR_DEFAULT, V_DEFAULT,
                           5.0, 15.0, 0.0, [4.0, 7.0])
    assert rows[1]["Kcu"] < rows[0]["Kcu"] / 100


def test_L7_pade_estimate_close_to_true_dead_time_simulation():
    ins = Instruments(tau_v=5.0, tau_m=15.0, theta=10.0)
    inlet = influent_stream(F_DEFAULT, CA_DEFAULT)
    FR = reagent_for_pH(inlet, CR_DEFAULT, 4.0)
    lin = linearize_stage(inlet, FR, CR_DEFAULT, V_DEFAULT)
    Kcu, _, Pu = ultimate_gain(lin["Kp"], lin["tau"], 5.0, 15.0, 10.0)
    Kc_sim, period = simulated_ultimate_gain(4.0, ins, Kcu, Pu)
    print("Pade Kcu=%.4g  simulated (true dead time)=%.4g  (%.2f%%); Pu=%.1f, sim=%.1f"
          % (Kcu, Kc_sim, 100 * (Kc_sim / Kcu - 1), Pu, period))
    assert Kc_sim == pytest.approx(Kcu, rel=0.15)


def test_L8_second_order_loop_never_unstable_under_P_only():
    assert ultimate_gain(3.0, 1000.0, 0.0, 15.0, 0.0)[0] == math.inf
    assert ultimate_gain(3.0, 1000.0, 5.0, 0.0, 0.0)[0] == math.inf


def test_pade_kcu_from_bisection_agrees_with_numpy_roots():
    Kp, tau, tau_v, tau_m, theta = 2.0, 1000.0, 5.0, 15.0, 10.0
    Kcu, omega, _ = ultimate_gain(Kp, tau, tau_v, tau_m, theta)
    roots = np.roots(characteristic_polynomial(Kcu, Kp, tau, tau_v, tau_m, theta))
    upper = roots[roots.imag > 0]
    pair = upper[np.argmin(np.abs(upper.real))]     # the pair closest to the axis
    assert abs(pair.real) < 1e-6 * omega
    assert pair.imag == pytest.approx(omega, rel=1e-4)


def test_ziegler_nichols_pi_is_stable_in_linear_model():
    Kp, tau, tau_v, tau_m = 3.0, 1000.0, 5.0, 15.0
    Kcu, _, Pu = ultimate_gain(Kp, tau, tau_v, tau_m)
    Kc, tauI = ziegler_nichols_pi(Kcu, Pu)
    assert is_stable(characteristic_polynomial(Kc, Kp, tau, tau_v, tau_m, 0.0, tauI))
    assert not is_stable(characteristic_polynomial(1.5 * Kcu, Kp, tau, tau_v, tau_m, 0.0, tauI))
