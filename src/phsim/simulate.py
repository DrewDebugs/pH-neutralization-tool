"""Closed-loop time simulation of 1-3 neutralization stages.

Each time step of length dt (= controller sample time):
  1. apply any disturbance whose time has come
  2. each PI controller reads its measured pH and sets valve signal u
     (u is held constant for the step, as in a real digital controller)
  3. advance the tank and valve ODEs (D1-D3, D5) with 4th-order Runge-Kutta
  4. solve the charge balance for the new pH in each tank (D4)
  5. pass that pH through the dead time and the probe lag (D6)
"""

import math
from dataclasses import dataclass
from typing import Optional

from .control import PIController, DeadTime, probe_update
from .chemistry import solve_pH
from .plant import tank_derivatives, steady_state_at_setpoints, states_from_streams
from .titration import influent_stream


@dataclass
class StageSettings:
    """One neutralization stage: tank + NaOH valve + PI loop."""
    V: float                        # tank volume, m^3
    CR: float                       # NaOH concentration, mol/L
    FR_max: float                   # valve maximum flow, m^3/s
    SP: float                       # pH set point
    Kc: float                       # controller gain, (m^3/s) per pH
    tauI: float = math.inf          # integral time, s (inf = P-only)
    bias: Optional[float] = None    # controller bias, m^3/s (None = flow at SP)


@dataclass
class Instruments:
    """Lags shared by every loop (seconds)."""
    tau_v: float = 5.0              # valve/actuator lag
    tau_m: float = 15.0             # pH probe lag
    theta: float = 0.0              # transport dead time to the probe


@dataclass
class Disturbance:
    """A step change at time t. Fields left as None are unchanged.

    F, Ca, Cw : new influent flow (m^3/s) and acid concentrations (mol/L)
    stage, SP, bias : new set point / controller bias for one stage
    (changing bias with Kc = 0 is a manual "open-loop" step in reagent flow)
    """
    t: float
    F: Optional[float] = None
    Ca: Optional[float] = None
    Cw: Optional[float] = None
    stage: Optional[int] = None
    SP: Optional[float] = None
    bias: Optional[float] = None


def largest_allowed_dt(stages, instruments, F):
    """Time step rule: dt <= (fastest time constant) / 10.

    Fastest of: valve lag, probe lag, and each tank residence time V/F.
    The tank ODEs are linear, so RK4 at this step is very accurate.
    """
    candidates = [s.V / F for s in stages]
    for tau in (instruments.tau_v, instruments.tau_m):
        if tau > 0.0:
            candidates.append(tau)
    return min(candidates) / 10.0


def rk4_step(states, dt, influent, V_list, CR_list, u_list, tau_v):
    """One classical Runge-Kutta step for the list-of-lists tank states."""
    def f(x):
        return tank_derivatives(x, influent, V_list, CR_list, u_list, tau_v)

    def shifted(x, k, h):  # x + h*k, element by element
        return [[xi + h * ki for xi, ki in zip(xr, kr)] for xr, kr in zip(x, k)]

    k1 = f(states)
    k2 = f(shifted(states, k1, dt / 2))
    k3 = f(shifted(states, k2, dt / 2))
    k4 = f(shifted(states, k3, dt))
    return [[x + dt / 6 * (a + 2 * b + 2 * c + d)
             for x, a, b, c, d in zip(xr, r1, r2, r3, r4)]
            for xr, r1, r2, r3, r4 in zip(states, k1, k2, k3, k4)]


def simulate(F, Ca, Cw, stages, instruments, t_end, dt=1.0,
             disturbances=(), anti_windup=True):
    """Run the closed loop from the steady state at the set points.

    F, Ca, Cw : nominal influent flow (m^3/s), HCl and acetic acid (mol/L)
    Returns a dict of lists: t, pH[k], pH_measured[k], u[k], FR[k], SP[k].
    """
    dt = min(dt, largest_allowed_dt(stages, instruments, F))
    n = len(stages)
    V_list = [s.V for s in stages]
    CR_list = [s.CR for s in stages]
    influent = influent_stream(F, Ca, Cw)

    # Start at steady state with every tank at its set point.
    FR0, outlets = steady_state_at_setpoints(
        influent, [s.SP for s in stages], CR_list, [s.FR_max for s in stages])
    states = states_from_streams(outlets, FR0)
    pH = [o.pH for o in outlets]

    controllers = []
    for s, FR in zip(stages, FR0):
        bias = FR if s.bias is None else s.bias
        controllers.append(PIController(s.Kc, s.tauI, bias, s.FR_max, s.SP, anti_windup))
    delay_steps = int(round(instruments.theta / dt))
    delays = [DeadTime(delay_steps, p) for p in pH]
    measured = list(pH)

    pending = sorted(disturbances, key=lambda d: d.t)
    out = {"t": [], "pH": [[] for _ in range(n)], "pH_measured": [[] for _ in range(n)],
           "u": [[] for _ in range(n)], "FR": [[] for _ in range(n)],
           "SP": [[] for _ in range(n)], "dt": dt}
    n_steps = int(round(t_end / dt))

    for step in range(n_steps + 1):
        t = step * dt
        # 1. disturbances due at or before this time
        while pending and pending[0].t <= t + 1e-9:
            d = pending.pop(0)
            influent = influent_stream(d.F if d.F is not None else influent.Q,
                                       d.Ca if d.Ca is not None else influent.a,
                                       d.Cw if d.Cw is not None else influent.w)
            if d.stage is not None and d.SP is not None:
                controllers[d.stage].setpoint = d.SP
            if d.stage is not None and d.bias is not None:
                controllers[d.stage].bias = d.bias
        # 2. controllers
        u = [c.output(m, dt) for c, m in zip(controllers, measured)]
        # record the state at time t
        out["t"].append(t)
        for k in range(n):
            out["pH"][k].append(pH[k])
            out["pH_measured"][k].append(measured[k])
            out["u"][k].append(u[k])
            out["FR"][k].append(states[k][3])
            out["SP"][k].append(controllers[k].setpoint)
        if step == n_steps:
            break
        # 3. tanks and valves
        if instruments.tau_v <= 0.0:          # instant valve
            for k in range(n):
                states[k][3] = u[k]
        states = rk4_step(states, dt, influent, V_list, CR_list, u, instruments.tau_v)
        # 4. pH from the charge balance (algebraic)
        pH = [solve_pH(x[0], x[1], x[2]) for x in states]
        # 5. dead time, then probe lag
        for k in range(n):
            delayed = delays[k].push(pH[k])
            measured[k] = probe_update(measured[k], delayed, dt, instruments.tau_m)
    return out
