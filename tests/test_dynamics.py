"""Plant dynamics P1-P5 and control K1-K5."""
import math

import numpy as np
import pytest
from scipy import signal

from phsim.linear import linearize_stage, ultimate_gain, ziegler_nichols_pi
from phsim.plant import steady_state, steady_state_at_setpoints, states_from_streams
from phsim.simulate import (Disturbance, Instruments, StageSettings, rk4_step,
                            simulate)
from phsim.titration import influent_stream, reagent_for_pH
from conftest import CA_DEFAULT, CR_DEFAULT, F_DEFAULT, V_DEFAULT

FR_MAX = 2 * F_DEFAULT * CA_DEFAULT / CR_DEFAULT      # valve = 2x nominal demand


def open_loop_stages(n, SPs=(4.0, 5.5, 7.0)):
    """n stages with Kc = 0: reagent flows stay at their initial (bias) value."""
    CRs = [CR_DEFAULT, 0.1, 0.01]
    return [StageSettings(V=V_DEFAULT, CR=CRs[k], FR_max=FR_MAX, SP=SPs[k], Kc=0.0)
            for k in range(n)]


# ---- P1-P4 ----------------------------------------------------------------
@pytest.mark.parametrize("n", [1, 2, 3])
def test_P1_simulation_reaches_algebraic_steady_state(n, instruments):
    stages = open_loop_stages(n)
    FR_list, _ = steady_state_at_setpoints(influent_stream(F_DEFAULT, CA_DEFAULT),
                                           [s.SP for s in stages], [s.CR for s in stages],
                                           [s.FR_max for s in stages])
    new_F, new_Ca = 0.8 * F_DEFAULT, 0.011
    t_end = 15 * n * V_DEFAULT / new_F
    out = simulate(F_DEFAULT, CA_DEFAULT, 0.0, stages, instruments, t_end, dt=2.0,
                   disturbances=[Disturbance(t=0.0, F=new_F, Ca=new_Ca)])
    expected = steady_state(influent_stream(new_F, new_Ca), FR_list, [s.CR for s in stages])
    for k in range(n):
        assert out["pH"][k][-1] == pytest.approx(expected[k].pH, abs=1e-4)


def test_P2_sodium_and_chloride_are_conserved():
    stages = open_loop_stages(1)
    influent = influent_stream(F_DEFAULT, 0.015)          # an upset: more acid
    FR = reagent_for_pH(influent_stream(F_DEFAULT, CA_DEFAULT), CR_DEFAULT, 4.0)
    a0 = CA_DEFAULT * F_DEFAULT / (F_DEFAULT + FR)
    state = [[a0, CR_DEFAULT * FR / (F_DEFAULT + FR), 0.0, FR]]
    dt, Q = 1.0, F_DEFAULT + FR
    cl_in = cl_out = na_in = na_out = 0.0
    for _ in range(3000):
        new = rk4_step(state, dt, influent, [V_DEFAULT], [CR_DEFAULT], [FR], 5.0)
        # trapezoid rule for the outflow integral
        cl_out += 0.5 * (state[0][0] + new[0][0]) * Q * dt
        na_out += 0.5 * (state[0][1] + new[0][1]) * Q * dt
        cl_in += influent.a * F_DEFAULT * dt
        na_in += CR_DEFAULT * FR * dt
        state = new
    cl_accumulated = V_DEFAULT * (state[0][0] - a0)
    na_accumulated = V_DEFAULT * (state[0][1] - CR_DEFAULT * FR / Q)
    assert cl_in - cl_out == pytest.approx(cl_accumulated, rel=1e-4)
    assert na_in - na_out == pytest.approx(na_accumulated, abs=1e-4 * na_in)


def test_P3_halving_time_step_changes_little(instruments):
    stages = open_loop_stages(2)
    upset = [Disturbance(t=0.0, F=0.9 * F_DEFAULT, Ca=0.012)]
    # (dt is capped at tau_v/10 = 0.5 s by the step rule, so compare 0.5 vs 0.25)
    coarse = simulate(F_DEFAULT, CA_DEFAULT, 0.0, stages, instruments, 2000, 0.5, upset)
    fine = simulate(F_DEFAULT, CA_DEFAULT, 0.0, stages, instruments, 2000, 0.25, upset)
    assert (coarse["dt"], fine["dt"]) == (0.5, 0.25)
    for k in range(2):
        diff = np.array(coarse["pH"][k]) - np.array(fine["pH"][k][::2])
        assert np.max(np.abs(diff)) < 1e-3


def test_P4_no_drift_at_steady_state(instruments):
    stages = [StageSettings(V=V_DEFAULT, CR=CR_DEFAULT, FR_max=FR_MAX, SP=4.0,
                            Kc=1e-5, tauI=60.0)]
    out = simulate(F_DEFAULT, CA_DEFAULT, 0.0, stages, instruments, 10 * 1000, 2.0)
    assert np.max(np.abs(np.array(out["pH"][0]) - 4.0)) < 1e-6


def test_P5_small_step_matches_linear_transfer_function(influent, instruments):
    FR0 = reagent_for_pH(influent, CR_DEFAULT, 4.0)
    step = 1e-4 * FR0          # small enough that the gain barely changes
    stages = [StageSettings(V=V_DEFAULT, CR=CR_DEFAULT, FR_max=FR_MAX, SP=4.0, Kc=0.0)]
    out = simulate(F_DEFAULT, CA_DEFAULT, 0.0, stages, instruments, 6000, 1.0,
                   [Disturbance(t=0.0, stage=0, bias=FR0 + step)])
    lin = linearize_stage(influent, FR0, CR_DEFAULT, V_DEFAULT)
    # Kp / ((tau_v s + 1)(tau s + 1)(tau_m s + 1)), built and solved by scipy
    den = np.polymul(np.polymul([5.0, 1.0], [lin["tau"], 1.0]), [15.0, 1.0])
    t = np.array(out["t"])
    _, y = signal.step(([lin["Kp"] * step], den), T=t)
    simulated = np.array(out["pH_measured"][0]) - 4.0
    assert np.max(np.abs(simulated - y)) < 0.02 * abs(y[-1])


# ---- K1-K5: control ----------------------------------------------------------
def zn_pi_stage(influent, SP, instruments, FR_max=FR_MAX):
    FR = reagent_for_pH(influent, CR_DEFAULT, SP)
    lin = linearize_stage(influent, FR, CR_DEFAULT, V_DEFAULT)
    Kcu, _, Pu = ultimate_gain(lin["Kp"], lin["tau"], instruments.tau_v,
                               instruments.tau_m, instruments.theta)
    Kc, tauI = ziegler_nichols_pi(Kcu, Pu)
    return StageSettings(V=V_DEFAULT, CR=CR_DEFAULT, FR_max=FR_max, SP=SP, Kc=Kc, tauI=tauI), lin


def test_K1_K2_PI_removes_offset_and_respects_valve_limits(influent, instruments):
    stage, _ = zn_pi_stage(influent, 4.0, instruments)
    out = simulate(F_DEFAULT, CA_DEFAULT, 0.0, [stage], instruments, 3000, 1.0,
                   [Disturbance(t=60.0, F=1.2 * F_DEFAULT), Disturbance(t=1500, Ca=0.03)])
    u = np.array(out["u"][0])
    assert u.min() >= 0.0 and u.max() <= FR_MAX                # K1
    assert max(u) == FR_MAX                                     # it did saturate
    t = np.array(out["t"])
    before_second_upset = (t > 1300) & (t < 1500)
    assert np.max(np.abs(np.array(out["pH"][0])[before_second_upset] - 4.0)) < 0.01   # K2


def test_K3_P_only_offset_matches_linear_prediction(influent, instruments):
    FR = reagent_for_pH(influent, CR_DEFAULT, 4.0)
    lin = linearize_stage(influent, FR, CR_DEFAULT, V_DEFAULT)
    Kcu, _, _ = ultimate_gain(lin["Kp"], lin["tau"], 5.0, 15.0)
    Kc = 0.5 * Kcu
    dF = 0.01 * F_DEFAULT
    stage = StageSettings(V=V_DEFAULT, CR=CR_DEFAULT, FR_max=FR_MAX, SP=4.0, Kc=Kc)
    out = simulate(F_DEFAULT, CA_DEFAULT, 0.0, [stage], instruments, 3000, 1.0,
                   [Disturbance(t=0.0, F=F_DEFAULT + dF)])
    predicted = lin["K_flow"] * dF / (1 + Kc * lin["Kp"])
    assert out["pH"][0][-1] - 4.0 == pytest.approx(predicted, rel=0.05)


def test_K4_anti_windup_reduces_overshoot(influent, instruments):
    tight_valve = 1.2 * reagent_for_pH(influent, CR_DEFAULT, 4.0)
    stage, _ = zn_pi_stage(influent, 4.0, instruments, FR_max=tight_valve)
    upset = [Disturbance(t=60.0, Ca=2 * CA_DEFAULT), Disturbance(t=1500.0, Ca=CA_DEFAULT)]
    peaks = {}
    for aw in (True, False):
        out = simulate(F_DEFAULT, CA_DEFAULT, 0.0, [stage], instruments, 3000, 1.0, upset, aw)
        t, pH = np.array(out["t"]), np.array(out["pH"][0])
        peaks[aw] = pH[t > 1500].max()
    assert peaks[True] < peaks[False]
    assert peaks[False] - 4.0 > 2 * (peaks[True] - 4.0)


def test_K5_dead_time_delays_measurement_exactly():
    ins = Instruments(tau_v=5.0, tau_m=0.0, theta=10.0)
    FR0 = F_DEFAULT * CA_DEFAULT / CR_DEFAULT
    stage = StageSettings(V=V_DEFAULT, CR=CR_DEFAULT, FR_max=FR_MAX, SP=4.0, Kc=0.0)
    out = simulate(F_DEFAULT, CA_DEFAULT, 0.0, [stage], ins, 200, 1.0,
                   [Disturbance(t=0.0, stage=0, bias=0.5 * FR0)])
    pH, measured = out["pH"][0], out["pH_measured"][0]
    n = round(10.0 / out["dt"])                 # dead time in steps (dt may be capped)
    assert pH[n] != pH[0]
    assert measured[n:] == pH[:-n]
