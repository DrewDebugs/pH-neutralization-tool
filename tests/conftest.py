"""Shared default case used by many tests (same numbers as the plan, section 1.5).

0.01 M HCl at 36 m^3/h, neutralized with 1 M NaOH in a 10 m^3 tank.
"""
import pytest

from phsim.constants import per_hour_to_per_second
from phsim.simulate import Instruments
from phsim.titration import influent_stream

F_DEFAULT = per_hour_to_per_second(36.0)   # m^3/s
CA_DEFAULT = 0.01                           # mol/L HCl
CR_DEFAULT = 1.0                            # mol/L NaOH
V_DEFAULT = 10.0                            # m^3


@pytest.fixture
def influent():
    return influent_stream(F_DEFAULT, CA_DEFAULT)


@pytest.fixture
def instruments():
    return Instruments(tau_v=5.0, tau_m=15.0, theta=0.0)
