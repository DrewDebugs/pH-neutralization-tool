"""Controller and measurement: PI with anti-windup, probe lag, dead time.

Sign convention: error e = SP - measured pH. Adding NaOH raises pH (process
gain K > 0), so a POSITIVE controller gain Kc gives negative feedback:
pH too low -> e > 0 -> more reagent.
"""

import math
from collections import deque


class PIController:
    """Discrete PI controller, positional form, executed every dt seconds.

    (C1) u = bias + Kc * ( e + I / tauI ),  then clipped to [0, u_max]
    (C2) I <- I + e*dt, EXCEPT when the output is clipped and the error
         would push it further past the limit (conditional integration).

    Why anti-windup: if the valve is wide open and pH is still low, the
    integral would keep growing ("winding up"). When the upset ends, the
    huge integral holds the valve open far too long -> big overshoot.
    Freezing I while saturated prevents that.

    tauI = math.inf gives P-only control (the integral term is dropped).
    """

    def __init__(self, Kc, tauI, bias, u_max, setpoint, anti_windup=True):
        self.Kc = Kc
        self.tauI = tauI
        self.bias = bias
        self.u_max = u_max
        self.setpoint = setpoint
        self.anti_windup = anti_windup
        self.integral = 0.0          # running integral of error, pH*s

    def output(self, measured_pH, dt):
        e = self.setpoint - measured_pH
        if math.isinf(self.tauI):
            u_unclipped = self.bias + self.Kc * e                      # P-only
        else:
            u_unclipped = self.bias + self.Kc * (e + self.integral / self.tauI)
        u = min(max(u_unclipped, 0.0), self.u_max)                     # valve limits

        if not math.isinf(self.tauI):
            pushing_high = u_unclipped > self.u_max and self.Kc * e > 0
            pushing_low = u_unclipped < 0.0 and self.Kc * e < 0
            winding_up = pushing_high or pushing_low
            if not (self.anti_windup and winding_up):
                self.integral += e * dt
        return u


class DeadTime:
    """Transport delay of n_steps samples (e.g. a sample line to the probe).

    A first-in, first-out queue: push today's value, get the value from
    n_steps samples ago. theta is rounded to a whole number of time steps.
    """

    def __init__(self, n_steps, initial_value):
        self.n_steps = n_steps
        self.queue = deque([initial_value] * n_steps)

    def push(self, value):
        if self.n_steps == 0:
            return value
        self.queue.append(value)
        return self.queue.popleft()


def probe_update(measured, true_value, dt, tau_m):
    """(D6) First-order probe lag: tau_m d(pH_m)/dt = pH - pH_m.

    Exact solution over one step with the input held constant:
        pH_m(t+dt) = pH_m + (1 - exp(-dt/tau_m)) * (pH - pH_m)
    tau_m = 0 means an ideal (instant) probe.
    """
    if tau_m <= 0.0:
        return true_value
    return measured + (1.0 - math.exp(-dt / tau_m)) * (true_value - measured)
