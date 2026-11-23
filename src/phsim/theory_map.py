"""Which Python function implements which equation (for the Theory page).

The Theory page shows each equation in LaTeX next to the source code of the
function listed here, read with inspect.getsource() at run time -- so the
code on the page is always exactly the code that runs.
"""

import importlib

ENTRIES = [
    {"id": "E2", "title": "Fraction of acetic acid ionized",
     "latex": r"\alpha = \frac{[A^-]}{[HA]+[A^-]} = \frac{K_a}{K_a + [H^+]}",
     "function": "chemistry.fraction_ionized"},
    {"id": "E1, E3", "title": "Charge balance (electroneutrality)",
     "latex": r"g(\mathrm{pH}) = [H^+] + b - \frac{K_w}{[H^+]} - a - w\,\alpha = 0",
     "function": "chemistry.charge_balance_residual"},
    {"id": "E3", "title": "Solving the charge balance by bisection",
     "latex": r"g \text{ strictly decreasing in pH} \Rightarrow \text{one root in } [-2, 16]",
     "function": "chemistry.solve_pH"},
    {"id": "E4", "title": "Buffer capacity",
     "latex": r"\beta = -\frac{\partial g}{\partial\,\mathrm{pH}} = \ln 10\left([H^+] + [OH^-] + \frac{w K_a [H^+]}{(K_a+[H^+])^2}\right)",
     "function": "chemistry.buffer_capacity"},
    {"id": "T1", "title": "Mixing influent with reagent",
     "latex": r"Q = Q_{in}+F_R,\quad a=\frac{Q_{in}a_{in}}{Q},\quad b=\frac{Q_{in}b_{in}+F_R C_R}{Q},\quad w=\frac{Q_{in}w_{in}}{Q}",
     "function": "titration.mix_with_reagent"},
    {"id": "T2", "title": "Equivalence ratio",
     "latex": r"r_{eq} = \frac{F_R}{F}\Big|_{eq} = \frac{C_a + C_w}{C_R}",
     "function": "titration.equivalence_ratio"},
    {"id": "T3", "title": "Process gain = slope of the titration curve",
     "latex": r"K = \frac{d\,\mathrm{pH}}{dF_R} = \frac{(C_R - b) + a + \alpha w}{Q\,\beta}",
     "function": "titration.process_gain"},
    {"id": "D1-D3, D5", "title": "Tank balances on reaction invariants + valve lag",
     "latex": r"V\frac{dx}{dt} = Q_{in}x_{in} + F_R c_{R,x} - Q x,\quad x\in\{a,b,w\};\qquad \tau_v\frac{dF_R}{dt} = u - F_R",
     "function": "plant.tank_derivatives"},
    {"id": "D6", "title": "pH probe lag (exact discrete update)",
     "latex": r"\mathrm{pH}_m(t+\Delta t) = \mathrm{pH}_m + \left(1 - e^{-\Delta t/\tau_m}\right)\left(\mathrm{pH}(t-\theta) - \mathrm{pH}_m\right)",
     "function": "control.probe_update"},
    {"id": "C1-C2", "title": "PI controller with valve limits and anti-windup",
     "latex": r"u = \bar u + K_c\left(e + \frac{1}{\tau_I}\int e\,dt\right),\quad 0 \le u \le F_{R,max},\quad e = SP - \mathrm{pH}_m",
     "function": "control.PIController.output"},
    {"id": "L1-L2", "title": "Linearization: first-order process transfer function",
     "latex": r"G_p(s) = \frac{K_p}{\tau s + 1},\quad \tau = \frac{V}{Q},\quad K_p = \sum_{x}\frac{\partial\,\mathrm{pH}}{\partial x}\frac{\partial x}{\partial F_R}",
     "function": "linear.linearize_stage"},
    {"id": "L3", "title": "Loop transfer function with Pade dead time",
     "latex": r"G(s) = \frac{1}{\tau_v s+1}\cdot\frac{K_p}{\tau s+1}\cdot\frac{1}{\tau_m s+1}\cdot\frac{1-\theta s/2}{1+\theta s/2}",
     "function": "linear.loop_polynomials"},
    {"id": "L4", "title": "Routh array",
     "latex": r"r_{i,j} = \frac{r_{i-1,0}\,r_{i-2,j+1} - r_{i-2,0}\,r_{i-1,j+1}}{r_{i-1,0}}",
     "function": "linear.routh_array"},
    {"id": "L4", "title": "Ultimate gain, P-only, no dead time (closed form)",
     "latex": r"K_{c,u} = \frac{a_1 a_2/a_3 - 1}{K_p},\quad \omega_u = \sqrt{a_1/a_3},\quad P_u = \frac{2\pi}{\omega_u}",
     "function": "linear.ultimate_gain_cubic"},
    {"id": "L5", "title": "Ultimate gain with dead time (Pade + Routh + bisection)",
     "latex": r"K_{c,u} = \max\{K_c : \text{Routh first column all positive}\}",
     "function": "linear.ultimate_gain"},
    {"id": "ZN", "title": "Ziegler-Nichols PI tuning",
     "latex": r"K_c = 0.45\,K_{c,u},\quad \tau_I = P_u/1.2",
     "function": "linear.ziegler_nichols_pi"},
    {"id": "Design", "title": "Valve rangeability and resolution for one stage",
     "latex": r"R = \frac{\max F_R(SP)}{\min F_R(SP)},\quad \text{resolution} = \frac{\min\left[F_R(\mathrm{pH}_{hi}) - F_R(\mathrm{pH}_{lo})\right]}{F_{R,max}}",
     "function": "design.analyze_stage"},
]


def function_for(entry):
    """Import and return the function (or method) named in an entry."""
    module_name, *attrs = entry["function"].split(".")
    obj = importlib.import_module("phsim." + module_name)
    for attr in attrs:
        obj = getattr(obj, attr)
    return obj
