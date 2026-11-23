"""The only bridge between the web page (JavaScript) and the model.

Every public function takes a JSON string of user inputs in DISPLAY units
and returns a JSON string. Display units:
    flow m^3/h, concentration mol/L, volume m^3, lags and dead time s,
    simulation time min, controller gain (m^3/h)/pH, integral time s
                                      (integral time 0 or empty = P-only)
All unit conversion happens here and nowhere else.
"""

import inspect
import json
import math

from . import theory_map
from .constants import per_hour_to_per_second as to_si, per_second_to_per_hour as to_h
from .design import StageDesign, compare_design
from .linear import (characteristic_polynomial, is_stable, kcu_vs_setpoint,
                     linearize_stage, ultimate_gain, ziegler_nichols_pi)
from .plant import steady_state_at_setpoints
from .simulate import Disturbance, Instruments, StageSettings, simulate
from .titration import equivalence_ratio, influent_stream, titration_curve

DEFAULTS = {
    "influent": {"F": 36.0, "Ca": 0.01, "Cw": 0.0},
    "n_stages": 1,
    "stages": [
        {"V": 10.0, "CR": 1.0, "FR_max": 0.72, "SP": 7.0, "Kc": 0.002, "tauI": 45.0},
        {"V": 10.0, "CR": 0.01, "FR_max": 0.72, "SP": 7.0, "Kc": 0.002, "tauI": 45.0},
        {"V": 10.0, "CR": 0.01, "FR_max": 0.72, "SP": 7.0, "Kc": 0.002, "tauI": 45.0},
    ],
    "instruments": {"tau_v": 5.0, "tau_m": 15.0, "theta": 0.0},
    "sim": {"t_end": 60.0, "dt": 1.0, "anti_windup": True},
    "disturbances": [{"t": 5.0, "F": None, "Ca": 0.012, "Cw": None},
                     {"t": 30.0, "F": 30.0, "Ca": None, "Cw": None}],
    "design": {
        "F_min": 18.0, "F_max": 36.0, "Ca_min": 0.002, "Ca_max": 0.02,
        "Cw_min": 0.0, "Cw_max": 0.0, "margin": 1.25,
        "valve_rangeability": 50.0, "valve_resolution_pct": 0.5,
        "designs": {
            "1": [{"SP": 7.0, "band_low": 6.0, "band_high": 9.0, "CR": 1.0, "V": 10.0}],
            "2": [{"SP": 4.0, "band_low": 3.5, "band_high": 4.5, "CR": 1.0, "V": 10.0},
                  {"SP": 7.0, "band_low": 6.0, "band_high": 9.0, "CR": 0.01, "V": 10.0}],
            "3": [{"SP": 3.0, "band_low": 2.8, "band_high": 3.2, "CR": 1.0, "V": 10.0},
                  {"SP": 4.5, "band_low": 4.0, "band_high": 5.0, "CR": 0.1, "V": 10.0},
                  {"SP": 7.0, "band_low": 6.0, "band_high": 9.0, "CR": 0.01, "V": 10.0}],
        },
    },
}


# ------------------------------------------------------------------ helpers
def _clean(x):
    """Make results JSON-safe: infinity/NaN -> None, tuples -> lists."""
    if isinstance(x, float) and (math.isinf(x) or math.isnan(x)):
        return None
    if isinstance(x, dict):
        return {k: _clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_clean(v) for v in x]
    return x


def _merge(defaults, user):
    """User inputs override defaults (missing keys fall back to defaults)."""
    if isinstance(defaults, dict) and isinstance(user, dict):
        out = dict(defaults)
        for k, v in user.items():
            out[k] = _merge(defaults.get(k), v)
        return out
    return user if user is not None else defaults


def _params(params_json):
    user = json.loads(params_json) if params_json else {}
    return _merge(DEFAULTS, user)


def _tauI(value):
    """Integral time from the form: 0, empty or None means P-only."""
    return math.inf if not value else float(value)


def _stage_settings(p):
    stages = []
    for s in p["stages"][: int(p["n_stages"])]:
        stages.append(StageSettings(V=s["V"], CR=s["CR"], FR_max=to_si(s["FR_max"]),
                                    SP=s["SP"], Kc=to_si(s["Kc"]), tauI=_tauI(s["tauI"])))
    return stages


def _instruments(p):
    i = p["instruments"]
    return Instruments(tau_v=i["tau_v"], tau_m=i["tau_m"], theta=i["theta"])


def _decimate(n_points, max_points=1500):
    step = max(1, n_points // max_points)
    return list(range(0, n_points, step))


# ------------------------------------------------------------ public calls
def defaults():
    return json.dumps(DEFAULTS)


def titration(params_json):
    """Titration curve (pH vs FR/F) and gain d(pH)/d(FR) vs pH, stage 1 reagent."""
    p = _params(params_json)
    inf = p["influent"]
    CR = p["stages"][0]["CR"]
    r_eq = equivalence_ratio(inf["Ca"], inf["Cw"], CR)
    # Even grid from 0 to 2*r_eq, plus extra points crowded around r_eq
    # where pH changes fastest (so the steep part is drawn smoothly).
    ratios = [2.0 * r_eq * i / 300 for i in range(301)]
    ratios += [r_eq * (1 + sgn * 10.0 ** (-k / 4)) for sgn in (-1, 1) for k in range(4, 33)]
    ratios = sorted(set(r for r in ratios if r >= 0))
    influent = influent_stream(to_si(inf["F"]), inf["Ca"], inf["Cw"])
    pH, gain = titration_curve(influent, CR, ratios)
    by_pH = sorted(zip(pH, gain))
    return json.dumps(_clean({
        "ratio": ratios, "pH": pH, "r_eq": r_eq,
        "gain_pH": [x for x, _ in by_pH],
        "gain": [g / 3600.0 for _, g in by_pH],        # pH per (m^3/h)
    }))


def stability(params_json):
    """Kc_u vs set point for stage 1, plus a linear analysis of each stage."""
    p = _params(params_json)
    inf, ins = p["influent"], _instruments(p)
    F = to_si(inf["F"])
    s1 = p["stages"][0]
    setpoints = [3.0 + 0.1 * i for i in range(81)]
    rows = kcu_vs_setpoint(F, inf["Ca"], inf["Cw"], s1["CR"], s1["V"],
                           ins.tau_v, ins.tau_m, ins.theta, setpoints)
    curve = {"SP": [r["SP"] for r in rows],
             "Kcu": [to_h(r["Kcu"]) for r in rows],        # (m^3/h)/pH
             "Kp": [r["Kp"] / 3600.0 for r in rows],         # pH/(m^3/h)
             "Pu": [r["Pu"] for r in rows]}

    stages = _stage_settings(p)
    influent = influent_stream(F, inf["Ca"], inf["Cw"])
    FR_list, outlets = steady_state_at_setpoints(
        influent, [s.SP for s in stages], [s.CR for s in stages], [s.FR_max for s in stages])
    inlets = [influent] + outlets[:-1]
    analysis = []
    for s, inlet, FR in zip(stages, inlets, FR_list):
        lin = linearize_stage(inlet, FR, s.CR, s.V)
        Kcu, omega, Pu = ultimate_gain(lin["Kp"], lin["tau"], ins.tau_v, ins.tau_m, ins.theta)
        Kc_zn, tauI_zn = ziegler_nichols_pi(Kcu, Pu) if Pu else (math.inf, math.inf)
        poly = characteristic_polynomial(s.Kc, lin["Kp"], lin["tau"], ins.tau_v,
                                         ins.tau_m, ins.theta, s.tauI)
        analysis.append({
            "SP": s.SP, "pH_reached": lin["pH"], "FR": to_h(FR),
            "Kp": lin["Kp"] / 3600.0, "tau": lin["tau"],
            "K_flow": lin["K_flow"] / 3600.0, "K_Ca": lin["K_Ca"],
            "Kcu": to_h(Kcu), "Pu": Pu, "Kc_zn": to_h(Kc_zn), "tauI_zn": tauI_zn,
            "char_poly": poly, "stable_now": is_stable(poly),
        })
    return json.dumps(_clean({"curve": curve, "stages": analysis,
                              "pade": ins.theta > 0}))


def simulation(params_json):
    """Closed-loop response to the user's disturbance steps."""
    p = _params(params_json)
    inf, sim = p["influent"], p["sim"]
    disturbances = [Disturbance(t=60.0 * d["t"],
                                F=to_si(d["F"]) if d.get("F") is not None else None,
                                Ca=d.get("Ca"), Cw=d.get("Cw"))
                    for d in p["disturbances"]]
    out = simulate(to_si(inf["F"]), inf["Ca"], inf["Cw"], _stage_settings(p),
                   _instruments(p), 60.0 * sim["t_end"], sim["dt"],
                   disturbances, bool(sim["anti_windup"]))
    idx = _decimate(len(out["t"]))
    pick = lambda series: [series[i] for i in idx]
    return json.dumps(_clean({
        "t": [out["t"][i] / 60.0 for i in idx],
        "pH": [pick(x) for x in out["pH"]],
        "pH_measured": [pick(x) for x in out["pH_measured"]],
        "FR": [[to_h(v) for v in pick(x)] for x in out["FR"]],
        "SP": [pick(x) for x in out["SP"]],
        "dt": out["dt"],
    }))


def design(params_json):
    """1-, 2- and 3-stage comparison table."""
    p = _params(params_json)
    d, ins = p["design"], _instruments(p)
    results = {}
    for n, stage_list in d["designs"].items():
        stages = [StageDesign(**s) for s in stage_list]
        try:
            r = compare_design([to_si(d["F_min"]), to_si(d["F_max"])],
                               [d["Ca_min"], d["Ca_max"]], [d["Cw_min"], d["Cw_max"]],
                               stages, d["margin"], d["valve_rangeability"],
                               d["valve_resolution_pct"], ins.tau_v, ins.tau_m, ins.theta)
        except ValueError as err:
            results[n] = {"error": str(err)}
            continue
        for s in r["stages"]:
            for key in ("demand_min", "demand_max", "FR_max", "Kcu"):
                s[key] = to_h(s[key])
            s["Kp"] = s["Kp"] / 3600.0
        results[n] = r
    return json.dumps(_clean(results))


def theory():
    """Equations with the exact source code of the function implementing each."""
    entries = []
    for e in theory_map.ENTRIES:
        entries.append(dict(e, code=inspect.getsource(theory_map.function_for(e))))
    return json.dumps(entries)
