"""Checking Routh-Hurwitz against the full nonlinear simulation.

Routh gives the largest stable P-only gain Kc_u of the LINEARIZED loop.
Here we find the same limit by brute force: simulate the nonlinear model
after a tiny upset and ask "do the oscillations grow or shrink?", then
bisect on Kc. Used by test L5/L7 and by the website build (headline number).
"""

from .simulate import Disturbance, StageSettings, simulate


def _peak_to_peak(values):
    return max(values) - min(values)


def oscillation_growth(F, Ca, CR, V, SP, Kc, instruments, Pu, periods=14, dt=0.1):
    """Simulate P-only control after a 0.01 % influent-flow step.

    Compares the oscillation amplitude (peak-to-peak of the measured pH)
    early in the run with the amplitude at the end, each over 2 periods.
    Returns (growth, period): growth > 1 means unstable; period is measured
    from the zero crossings of the late oscillation (seconds).
    """
    stage = StageSettings(V=V, CR=CR, FR_max=1.0, SP=SP, Kc=Kc)
    t_end = periods * Pu
    out = simulate(F, Ca, 0.0, [stage], instruments, t_end, dt,
                   [Disturbance(t=0.0, F=1.0001 * F)])
    t, y = out["t"], out["pH_measured"][0]
    early = [v for ti, v in zip(t, y) if 0.3 * t_end < ti < 0.3 * t_end + 2 * Pu]
    late_t = [ti for ti in t if ti > t_end - 2 * Pu]
    late = y[len(y) - len(late_t):]
    growth = _peak_to_peak(late) / _peak_to_peak(early)

    mean = sum(late) / len(late)
    crossings = [late_t[i] for i in range(1, len(late))
                 if (late[i - 1] - mean) * (late[i] - mean) < 0]
    gaps = [b - a for a, b in zip(crossings, crossings[1:])]
    period = 2 * sum(gaps) / len(gaps)
    return growth, period


def simulated_ultimate_gain(F, Ca, CR, V, SP, instruments, Kc_guess, Pu, bisections=9):
    """Smallest Kc whose oscillations grow, found by bisection between
    0.7 and 1.3 times the Routh estimate. Returns (Kc_u_simulated, period).
    """
    def growth(Kc):
        return oscillation_growth(F, Ca, CR, V, SP, Kc, instruments, Pu)[0]

    low, high = 0.7 * Kc_guess, 1.3 * Kc_guess
    if not (growth(low) < 1 < growth(high)):
        raise ValueError("the simulated limit is not within +/-30 % of the guess")
    for _ in range(bisections):
        mid = 0.5 * (low + high)
        if growth(mid) < 1:
            low = mid
        else:
            high = mid
    Kc = 0.5 * (low + high)
    return Kc, oscillation_growth(F, Ca, CR, V, SP, Kc, instruments, Pu)[1]
