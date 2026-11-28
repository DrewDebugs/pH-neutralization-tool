"""Physical constants and unit conversions used everywhere in phsim.

Internal units (used by every function in this package):
    time           s
    volume         m^3
    flow           m^3/s
    concentration  mol/L  (= kmol/m^3)

Why these units are consistent: every balance multiplies a flow by a
concentration and divides by a volume, e.g. (m^3/s)(kmol/m^3)/(m^3)
= kmol/m^3/s, which is the units of d(concentration)/dt. So mol/L can be
used for concentration with m^3 for volume without any conversion factor.

The website shows flows in m^3/h. The ONLY place that converts is api.py.
"""

import math

# Ion product of water at 25 C (Assumption 1 in the plan).
# 1.0e-14 is used exactly, so a neutral solution is exactly pH 7.00.
KW = 1.0e-14

# Acid-dissociation constant of acetic acid at 25 C.
# Harris (Quantitative Chemical Analysis) gives pKa = 4.756, i.e. Ka = 1.754e-5;
# 1.75e-5 is that value rounded to 3 significant figures (pKa 4.757, a 0.001 pH difference).
KA_ACETIC = 1.75e-5

# ln(10): appears whenever we differentiate 10**(-pH) with respect to pH,
# because d(10**-pH)/d(pH) = -ln(10) * 10**-pH.
LN10 = math.log(10.0)

SECONDS_PER_HOUR = 3600.0


def per_hour_to_per_second(flow_m3_per_h):
    """Convert a flow from m^3/h (what the user types) to m^3/s (internal)."""
    return flow_m3_per_h / SECONDS_PER_HOUR


def per_second_to_per_hour(flow_m3_per_s):
    """Convert a flow from m^3/s (internal) to m^3/h (what the user sees)."""
    return flow_m3_per_s * SECONDS_PER_HOUR
