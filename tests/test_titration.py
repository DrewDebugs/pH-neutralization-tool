"""Titration curve and gain tests T1-T4, W5 (gain part), inverse titration."""
import numpy as np
import pytest

from phsim.chemistry import solve_pH

from phsim.titration import (equivalence_ratio, influent_stream, mix_with_reagent,
                             process_gain, reagent_for_pH)
from conftest import CA_DEFAULT, CR_DEFAULT, F_DEFAULT


def test_T1_strong_acid_crosses_pH_7_at_equivalence_ratio(influent):
    r_eq = equivalence_ratio(CA_DEFAULT, 0.0, CR_DEFAULT)
    assert r_eq == pytest.approx(0.01)
    FR = reagent_for_pH(influent, CR_DEFAULT, 7.0)
    assert FR / F_DEFAULT == pytest.approx(r_eq, rel=1e-6)


def precise_pH(stream):
    """Finite differences need a much tighter pH tolerance than the app uses."""
    return solve_pH(stream.a, stream.b, stream.w, tol=1e-14)


def _gain_check(inlet, target_pHs):
    for target in target_pHs:
        FR = reagent_for_pH(inlet, CR_DEFAULT, target)
        d = FR * 1e-8
        numeric = (precise_pH(mix_with_reagent(inlet, FR + d, CR_DEFAULT))
                   - precise_pH(mix_with_reagent(inlet, FR - d, CR_DEFAULT))) / (2 * d)
        assert process_gain(inlet, FR, CR_DEFAULT) == pytest.approx(numeric, rel=1e-4), target


def test_T2_gain_formula_matches_finite_difference(influent):
    _gain_check(influent, np.linspace(2.5, 12.0, 20))


def test_W5_gain_formula_with_acetic_acid():
    _gain_check(influent_stream(F_DEFAULT, 0.002, 0.01), np.linspace(3.0, 11.5, 20))


def test_T3_gain_is_largest_at_equivalence(influent):
    r_eq = equivalence_ratio(CA_DEFAULT, 0.0, CR_DEFAULT)
    ratios = r_eq * np.linspace(0.5, 1.5, 2001)     # includes r_eq exactly
    gains = [process_gain(influent, r * F_DEFAULT, CR_DEFAULT) for r in ratios]
    assert ratios[int(np.argmax(gains))] == pytest.approx(r_eq, rel=1e-3)


def test_T4_gain_at_pH7_is_over_100x_gain_at_pH4(influent):
    g7 = process_gain(influent, reagent_for_pH(influent, CR_DEFAULT, 7.0), CR_DEFAULT)
    g4 = process_gain(influent, reagent_for_pH(influent, CR_DEFAULT, 4.0), CR_DEFAULT)
    assert g7 / g4 > 100


def test_acetic_acid_flattens_the_curve_near_pKa():
    # Buffering: with acetic acid present the gain at pH 4.76 is much lower
    # than for the same total acid as HCl only at the same pH.
    strong = influent_stream(F_DEFAULT, 0.012)
    weak = influent_stream(F_DEFAULT, 0.002, 0.01)
    g_strong = process_gain(strong, reagent_for_pH(strong, CR_DEFAULT, 4.76), CR_DEFAULT)
    g_weak = process_gain(weak, reagent_for_pH(weak, CR_DEFAULT, 4.76), CR_DEFAULT)
    assert g_strong / g_weak > 10


def test_reagent_for_pH_inverts_mixing(influent):
    for target in (3.0, 7.0, 10.0):
        FR = reagent_for_pH(influent, CR_DEFAULT, target)
        assert mix_with_reagent(influent, FR, CR_DEFAULT).pH == pytest.approx(target, abs=1e-6)


def test_unreachable_target_raises(influent):
    with pytest.raises(ValueError):
        reagent_for_pH(influent, 0.001, 11.5)    # 0.001 M NaOH is only pH 11
