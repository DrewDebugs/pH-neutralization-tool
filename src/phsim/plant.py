"""Neutralization tanks in series: dynamic balances and steady state (D1-D3, D5).

Tank k receives the outlet of tank k-1 (tank 1 receives the influent) plus
its own NaOH reagent flow FR_k. Constant liquid volume (overflow weir), so
    Q_k = Q_(k-1) + FR_k.

State of each tank: [a, b, w, FR]
    a, b, w = reaction invariants in the tank (mol/L), see chemistry.py
    FR      = reagent flow actually delivered by the valve (m^3/s)
"""

from .titration import Stream, mix_with_reagent, reagent_for_pH


def tank_derivatives(states, influent, V_list, CR_list, u_list, tau_v):
    """Time derivatives of every tank state.

    For tank k with volume V (all well mixed, so outlet = tank contents):
      (D1) V da/dt = Q_in*a_in - Q*a
      (D3) V db/dt = Q_in*b_in + FR*CR - Q*b
      (D2) V dw/dt = Q_in*w_in - Q*w
      (D5) tau_v dFR/dt = u - FR          (valve/actuator lag)
    "In - out" only: no reaction term, because a, b, w are reaction
    invariants. These ODEs are LINEAR in a, b, w -> not stiff.
    """
    derivatives = []
    # The stream entering tank 1 is the influent.
    Q_in, a_in, b_in, w_in = influent.Q, influent.a, influent.b, influent.w
    for k, (a, b, w, FR) in enumerate(states):
        V = V_list[k]
        Q = Q_in + FR                       # outlet flow of this tank
        da = (Q_in * a_in - Q * a) / V
        db = (Q_in * b_in + FR * CR_list[k] - Q * b) / V
        dw = (Q_in * w_in - Q * w) / V
        if tau_v > 0.0:
            dFR = (u_list[k] - FR) / tau_v
        else:
            dFR = 0.0                       # instant valve: FR is set to u directly
        derivatives.append([da, db, dw, dFR])
        # This tank's outlet is the next tank's inlet.
        Q_in, a_in, b_in, w_in = Q, a, b, w
    return derivatives


def steady_state(influent, FR_list, CR_list):
    """Steady state of the tank train for fixed reagent flows.

    At steady state d/dt = 0 in (D1-D3), which gives exactly the mixing
    balance (T1): each tank's contents = its inlet mixed with its reagent.
    Returns a list of Streams (outlet of each tank).
    """
    outlets = []
    inlet = influent
    for FR, CR in zip(FR_list, CR_list):
        outlet = mix_with_reagent(inlet, FR, CR)
        outlets.append(outlet)
        inlet = outlet
    return outlets


def steady_state_at_setpoints(influent, SP_list, CR_list, FR_max_list):
    """Reagent flows that put every tank at its set point (nominal design).

    Solved stage by stage with inverse titration. If a valve cannot deliver
    the demand, its flow is limited to FR_max (the tank then sits below SP).
    Returns (FR_list, outlets).
    """
    FR_list, outlets = [], []
    inlet = influent
    for SP, CR, FR_max in zip(SP_list, CR_list, FR_max_list):
        FR = min(reagent_for_pH(inlet, CR, SP), FR_max)
        outlet = mix_with_reagent(inlet, FR, CR)
        FR_list.append(FR)
        outlets.append(outlet)
        inlet = outlet
    return FR_list, outlets


def states_from_streams(outlets, FR_list):
    """Pack steady-state streams into the [a, b, w, FR] state lists."""
    return [[s.a, s.b, s.w, FR] for s, FR in zip(outlets, FR_list)]


def stream_of_tank(state, Q):
    """Convert one tank state back to a Stream (for pH or linearization)."""
    a, b, w, _ = state
    return Stream(Q=Q, a=a, b=b, w=w)
