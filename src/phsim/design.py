"""Design helper: compare 1-, 2- and 3-stage neutralization designs.

Everything here is computed from the model (no hidden rules of thumb):
for each stage, over the whole range of influent conditions, how much must
the reagent valve turn down (rangeability) and how finely must it deliver
reagent (resolution) to keep that stage inside its pH band?
"""

import itertools
from dataclasses import dataclass

from .linear import linearize_stage, ultimate_gain
from .titration import influent_stream, mix_with_reagent, reagent_for_pH


@dataclass
class StageDesign:
    SP: float          # set point
    band_low: float    # lowest acceptable outlet pH of this stage
    band_high: float   # highest acceptable outlet pH of this stage
    CR: float          # NaOH concentration, mol/L
    V: float           # tank volume, m^3


def stage_inlets(F_range, Ca_range, Cw_range, stages, k):
    """All worst-case inlet streams to stage k (0-based).

    Stage 0: the corners of the influent envelope (reagent demand rises
    monotonically with F, Ca and Cw, so the corners bound it).
    Stage k > 0: the outlet of stage k-1 when stage k-1 sits at either
    edge of its band, for each of ITS worst-case inlets.
    """
    inlets = [influent_stream(F, Ca, Cw)
              for F, Ca, Cw in itertools.product(F_range, Ca_range, Cw_range)]
    for j in range(k):
        s = stages[j]
        next_inlets = []
        for inlet in inlets:
            for edge in (s.band_low, s.band_high):
                FR = reagent_for_pH(inlet, s.CR, edge)
                next_inlets.append(mix_with_reagent(inlet, FR, s.CR))
        inlets = next_inlets
    return inlets


def analyze_stage(inlets, s, margin, tau_v, tau_m, theta):
    """Valve requirements and loop stability for one stage.

    demand      : reagent flow needed at SP for each worst-case inlet
    FR_max      : valve size = margin * largest demand (a design choice)
    rangeability: largest demand / smallest demand
    resolution  : smallest change in reagent flow that moves the outlet
                  from the bottom to the top of the band, as % of FR_max.
                  The valve must deliver flow at least this precisely.
    """
    demand = [reagent_for_pH(i, s.CR, s.SP) for i in inlets]
    FR_max = margin * max(demand)
    smallest = min(demand)
    rangeability = max(demand) / smallest if smallest > 0 else float("inf")
    band_widths = [reagent_for_pH(i, s.CR, s.band_high) - reagent_for_pH(i, s.CR, s.band_low)
                   for i in inlets]
    resolution_pct = 100.0 * min(band_widths) / FR_max

    # Linear analysis at the middle (median-demand) inlet.
    mid = sorted(zip(demand, range(len(inlets))))[len(inlets) // 2][1]
    lin = linearize_stage(inlets[mid], demand[mid], s.CR, s.V)
    Kcu, _, Pu = ultimate_gain(lin["Kp"], lin["tau"], tau_v, tau_m, theta)
    return {"SP": s.SP, "band": [s.band_low, s.band_high], "CR": s.CR, "V": s.V,
            "demand_min": smallest, "demand_max": max(demand), "FR_max": FR_max,
            "rangeability": rangeability, "resolution_pct": resolution_pct,
            "Kp": lin["Kp"], "tau": lin["tau"], "Kcu": Kcu, "Pu": Pu}


def compare_design(F_range, Ca_range, Cw_range, stages, margin,
                   valve_rangeability, valve_resolution_pct,
                   tau_v=5.0, tau_m=15.0, theta=0.0):
    """Analyze every stage of one design and give a feasibility verdict.

    A stage is feasible if the valve can turn down far enough
    (needed rangeability <= valve rangeability) AND is precise enough
    (needed resolution >= valve resolution).
    """
    results = []
    for k, s in enumerate(stages):
        inlets = stage_inlets(F_range, Ca_range, Cw_range, stages, k)
        r = analyze_stage(inlets, s, margin, tau_v, tau_m, theta)
        r["rangeability_ok"] = r["rangeability"] <= valve_rangeability
        r["resolution_ok"] = r["resolution_pct"] >= valve_resolution_pct
        r["feasible"] = r["rangeability_ok"] and r["resolution_ok"]
        results.append(r)
    return {"stages": results,
            "total_volume": sum(s.V for s in stages),
            "feasible": all(r["feasible"] for r in results)}


def default_designs():
    """Illustrative 1-, 2- and 3-stage designs for the default case.

    The intermediate set points and bands are NOT from a literature rule;
    they were picked so each upstream stage removes most of the acid while
    sitting on a less steep part of the titration curve. Change them in
    the Tool and watch the verdicts.
    """
    final = StageDesign(SP=7.0, band_low=6.0, band_high=9.0, CR=0.01, V=10.0)
    return {
        1: [StageDesign(7.0, 6.0, 9.0, 1.0, 10.0)],
        2: [StageDesign(4.0, 3.5, 4.5, 1.0, 10.0), final],
        3: [StageDesign(3.0, 2.8, 3.2, 1.0, 10.0),
            StageDesign(4.5, 4.0, 5.0, 0.1, 10.0), final],
    }
