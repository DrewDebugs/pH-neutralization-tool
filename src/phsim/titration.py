"""Mixing, titration curve and steady-state process gain (equations T1-T3).

A Stream is a flow plus its three reaction invariants. Mixing a stream with
NaOH reagent is all the steady-state chemistry we need: a well-mixed tank at
steady state has the same composition as its mixed inlet.
"""

from dataclasses import dataclass

from .chemistry import solve_pH, buffer_capacity, fraction_ionized
from .constants import KA_ACETIC


@dataclass(frozen=True)
class Stream:
    """A liquid stream.

    Q : volumetric flow, m^3/s
    a : total chloride, mol/L
    b : total sodium, mol/L
    w : total acetate, mol/L
    """
    Q: float
    a: float
    b: float
    w: float = 0.0

    @property
    def pH(self):
        return solve_pH(self.a, self.b, self.w)


def influent_stream(F, Ca, Cw=0.0):
    """The acidic wastewater: HCl at Ca and acetic acid at Cw, no sodium."""
    return Stream(Q=F, a=Ca, b=0.0, w=Cw)


def mix_with_reagent(inlet, FR, CR):
    """(T1) Mix an inlet stream with NaOH reagent (flow FR, conc. CR).

    Component balances on a mixing point (volumes additive):
        Q = Q_in + FR
        a = Q_in*a_in / Q                    (no Cl in reagent)
        b = (Q_in*b_in + FR*CR) / Q          (Na from both streams)
        w = Q_in*w_in / Q                    (no acetate in reagent)
    """
    Q = inlet.Q + FR
    a = inlet.Q * inlet.a / Q
    b = (inlet.Q * inlet.b + FR * CR) / Q
    w = inlet.Q * inlet.w / Q
    return Stream(Q=Q, a=a, b=b, w=w)


def equivalence_ratio(Ca, Cw, CR):
    """(T2) Reagent/influent flow ratio that exactly neutralizes all acid.

    Moles of base = moles of acid:  FR*CR = F*(Ca + Cw)  ->  r = (Ca+Cw)/CR.
    For a strong acid only, pH = 7.00 at this ratio.
    """
    return (Ca + Cw) / CR


def process_gain(inlet, FR, CR, ka=KA_ACETIC):
    """(T3) Steady-state gain K = d(pH)/d(FR), in pH per (m^3/s).

    Implicit differentiation of the charge balance g = 0 after mixing:
        K = [ (CR - b) + a + alpha*w ] / (Q * beta)
    Numerator: how fast mixing changes net base concentration as FR rises
      (CR - b)/Q  : more reagent adds Na
      a/Q, alpha*w/Q : more reagent dilutes the acid (removes neg. charge)
    Denominator beta: how much net base it takes to move pH by one unit.
    Near equivalence (strong acid) beta is tiny, so K is huge.
    """
    mixed = mix_with_reagent(inlet, FR, CR)
    pH = mixed.pH
    beta = buffer_capacity(pH, mixed.w, ka)
    alpha = fraction_ionized(pH, ka)
    numerator = (CR - mixed.b) + mixed.a + alpha * mixed.w
    return numerator / (mixed.Q * beta)


def reagent_for_pH(inlet, CR, target_pH, iterations=100):
    """Inverse titration: the reagent flow FR that gives the target pH.

    pH of the mixture rises monotonically with FR, so bisection on FR works.
    Returns 0 if the inlet is already at or above the target.
    Raises ValueError if the target is above the pH of the reagent itself
    (no amount of this reagent can reach it).
    """
    if inlet.pH >= target_pH:
        return 0.0
    if target_pH >= solve_pH(0.0, CR) - 1e-9:
        raise ValueError("target pH %.2f cannot be reached with %.3g M NaOH"
                         % (target_pH, CR))
    # Start the upper bound at twice the stoichiometric demand, then double
    # it until the mixture overshoots the target.
    high = 2.0 * inlet.Q * (inlet.a + inlet.w) / CR + 1e-12
    while mix_with_reagent(inlet, high, CR).pH < target_pH:
        high *= 2.0
    low = 0.0
    for _ in range(iterations):
        mid = 0.5 * (low + high)
        if mix_with_reagent(inlet, mid, CR).pH < target_pH:
            low = mid
        else:
            high = mid
    return 0.5 * (low + high)


def titration_curve(influent, CR, ratios):
    """pH and gain at each reagent/influent ratio r = FR/F.

    Returns (pH_list, gain_list) with gain in pH per (m^3/s).
    """
    pH_list, gain_list = [], []
    for r in ratios:
        FR = r * influent.Q
        pH_list.append(mix_with_reagent(influent, FR, CR).pH)
        gain_list.append(process_gain(influent, FR, CR))
    return pH_list, gain_list
