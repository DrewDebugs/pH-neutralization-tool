"""Design helper G1-G4 and website glue A1-A2."""
import itertools
import json
import math

import pytest

from phsim import api, theory_map
from phsim.constants import KW
from phsim.design import StageDesign, compare_design, default_designs, stage_inlets
from phsim.titration import reagent_for_pH
from conftest import CR_DEFAULT, F_DEFAULT

F_RANGE = [0.5 * F_DEFAULT, F_DEFAULT]
CA_RANGE = [0.002, 0.02]


def test_G1_single_stage_rangeability_is_load_ratio():
    stages = [StageDesign(7.0, 6.0, 9.0, CR_DEFAULT, 10.0)]
    r = compare_design(F_RANGE, CA_RANGE, [0.0], stages, 1.25, 50, 0.5)
    expected = (F_RANGE[1] * CA_RANGE[1]) / (F_RANGE[0] * CA_RANGE[0])
    assert r["stages"][0]["rangeability"] == pytest.approx(expected, rel=1e-6)


def test_G2_resolution_matches_hand_calculation():
    # Strong acid: at a target pH, net base after mixing = [OH-] - [H+], so
    #   CR*FR - Ca*F = (F + FR)*(oh - h)  ->  FR = F (Ca + d) / (CR - d), d = oh - h
    F, Ca, margin = F_DEFAULT, 0.01, 1.25

    def FR_hand(pH):
        d = KW / 10 ** -pH - 10 ** -pH
        return F * (Ca + d) / (CR_DEFAULT - d)

    stages = [StageDesign(7.0, 6.0, 9.0, CR_DEFAULT, 10.0)]
    r = compare_design([F], [Ca], [0.0], stages, margin, 50, 0.5)
    expected = 100 * (FR_hand(9.0) - FR_hand(6.0)) / (margin * FR_hand(7.0))
    assert r["stages"][0]["resolution_pct"] == pytest.approx(expected, rel=1e-6)


def test_G3_staging_relaxes_final_valve_resolution():
    designs = default_designs()
    one = compare_design(F_RANGE, CA_RANGE, [0.0], designs[1], 1.25, 50, 0.5)
    two = compare_design(F_RANGE, CA_RANGE, [0.0], designs[2], 1.25, 50, 0.5)
    assert two["stages"][-1]["resolution_pct"] > 10 * one["stages"][-1]["resolution_pct"]
    assert not one["feasible"] and two["feasible"]


def test_G4_corners_bracket_interior_demand():
    s = StageDesign(7.0, 6.0, 9.0, CR_DEFAULT, 10.0)
    corners = [reagent_for_pH(i, s.CR, s.SP)
               for i in stage_inlets(F_RANGE, CA_RANGE, [0.0, 0.005], [s], 0)]
    for F, Ca, Cw in itertools.product([0.6 * F_DEFAULT, 0.8 * F_DEFAULT],
                                       [0.005, 0.01, 0.015], [0.001, 0.003]):
        from phsim.titration import influent_stream
        d = reagent_for_pH(influent_stream(F, Ca, Cw), s.CR, s.SP)
        assert min(corners) <= d <= max(corners)


def _strict_json(text):
    def reject(constant):
        raise ValueError("non-standard JSON constant " + constant)
    return json.loads(text, parse_constant=reject)


@pytest.mark.parametrize("name", ["titration", "stability", "simulation", "design"])
def test_A1_api_returns_strict_json(name):
    result = _strict_json(getattr(api, name)("{}"))
    assert result


def test_A1_api_handles_three_stages_with_dead_time_and_acetic_acid():
    p = json.loads(api.defaults())
    p["n_stages"] = 3
    p["influent"]["Cw"] = 0.005
    p["instruments"]["theta"] = 10.0
    p["stages"][0]["SP"], p["stages"][1]["SP"] = 4.0, 5.5
    params = json.dumps(p)
    for name in ("titration", "stability", "simulation", "design"):
        _strict_json(getattr(api, name)(params))
    sim = _strict_json(api.simulation(params))
    assert len(sim["pH"]) == 3


def test_A2_every_theory_entry_points_to_real_code():
    entries = _strict_json(api.theory())
    assert len(entries) == len(theory_map.ENTRIES)
    for e in entries:
        assert "def " in e["code"] and e["latex"]
