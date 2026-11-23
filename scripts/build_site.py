"""Assemble the website in _site/.

1. Copy site/ and insert the shared pieces (site/_partials/*.html) wherever
   a page says <!--#include NAME-->, marking the current page in the menu.
2. Copy the Python model (the SAME files pytest tests) to _site/py/phsim/
   and list them in a manifest that site/js/py-worker.js reads.
3. Run the model once to precompute the Home page: titration curve, two
   simulations, and every headline number ("facts"), so no number on the
   Home page is typed in by hand and the Home page needs no Python download.

Usage:  python scripts/build_site.py
        python -m http.server -d _site 8000     # then open http://localhost:8000
"""
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE, MODEL, OUT = ROOT / "site", ROOT / "src" / "phsim", ROOT / "_site"
sys.path.insert(0, str(ROOT / "src"))


# ------------------------------------------------------------ 1. pages
def build_pages():
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(SITE, OUT, ignore=shutil.ignore_patterns("_partials"))
    partials = {p.stem: p.read_text() for p in (SITE / "_partials").glob("*.html")}
    for page in OUT.glob("*.html"):
        html = page.read_text()
        html = re.sub(r"[ \t]*<!--#include (\w+)-->\n?", lambda m: partials[m.group(1)], html)
        html = html.replace(f'<a href="{page.name}">', f'<a href="{page.name}" aria-current="page">')
        page.write_text(html)
    (OUT / ".nojekyll").write_text("")      # serve files as-is on GitHub Pages


# ------------------------------------------------------------ 2. model
def copy_model():
    (OUT / "py" / "phsim").mkdir(parents=True)
    names = sorted(p.name for p in MODEL.glob("*.py"))
    for name in names:
        shutil.copy(MODEL / name, OUT / "py" / "phsim" / name)
    (OUT / "py" / "manifest.json").write_text(json.dumps(names))
    return names


# ------------------------------------------------------------ 3. showcase
def sig(x, digits=2):
    """Round to significant figures and add thousands separators: 4987 -> '5,000'."""
    if x == 0:
        return "0"
    rounded = round(x, -int(math.floor(math.log10(abs(x)))) + digits - 1)
    decimals = max(0, digits - 1 - int(math.floor(math.log10(abs(x)))))
    return f"{rounded:,.{decimals}f}"


def count_tests():
    try:
        out = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q"], cwd=ROOT,
                             capture_output=True, text=True, timeout=120).stdout
        return int(re.search(r"(\d+) tests? collected", out).group(1))
    except Exception:            # pytest not installed: leave the number out
        return None


def showcase():
    from phsim import api, verify
    from phsim.constants import per_hour_to_per_second as to_si, per_second_to_per_hour as to_h
    from phsim.linear import kcu_vs_setpoint, linearize_stage, ultimate_gain
    from phsim.simulate import Instruments
    from phsim.titration import influent_stream, reagent_for_pH

    p = json.loads(api.defaults())
    F, Ca = to_si(p["influent"]["F"]), p["influent"]["Ca"]
    s1, ins = p["stages"][0], p["instruments"]
    CR, V = s1["CR"], s1["V"]
    inst = Instruments(ins["tau_v"], ins["tau_m"], ins["theta"])
    influent = influent_stream(F, Ca)

    # Stability limit and gain at set points 3..7
    rows = {r["SP"]: r for r in kcu_vs_setpoint(F, Ca, 0.0, CR, V, inst.tau_v, inst.tau_m,
                                                 inst.theta, [3.0, 4.0, 5.0, 6.0, 7.0])}
    FR = {sp: to_h(reagent_for_pH(influent, CR, sp)) for sp in (3.0, 6.0, 7.0, 8.0)}
    gain7 = rows[7.0]["Kp"] / 3600.0                       # pH per m^3/h

    # Routh vs nonlinear simulation at SP 4 (same check as test L5)
    lin = linearize_stage(influent, reagent_for_pH(influent, CR, 4.0), CR, V)
    Kcu, _, Pu = ultimate_gain(lin["Kp"], lin["tau"], inst.tau_v, inst.tau_m)
    Kc_sim, _ = verify.simulated_ultimate_gain(F, Ca, CR, V, 4.0, inst, Kcu, Pu)

    def thin(sim, n=600):
        step = max(1, len(sim["t"]) // n)
        return {k: ([[round(v, 4) for v in s[::step]] for s in sim[k]] if k != "t" else sim[k][::step])
                for k in ("t", "pH", "pH_measured", "FR", "SP")}

    single = json.loads(api.simulation(json.dumps(p)))
    staged = json.loads(api.defaults())
    staged["n_stages"] = 2
    staged["stages"][0]["SP"] = 4.0
    staged["stages"][1]["CR"] = 0.01
    for k, a in enumerate(json.loads(api.stability(json.dumps(staged)))["stages"]):
        staged["stages"][k]["Kc"] = 0.5 * a["Kcu"]   # half the stability limit
        staged["stages"][k]["tauI"] = 2.0 * a["Pu"]
    two = json.loads(api.simulation(json.dumps(staged)))
    titration = json.loads(api.titration(json.dumps(p)))
    n_tests = count_tests()

    facts = {
        "gain_ratio": sig(rows[7.0]["Kp"] / rows[3.0]["Kp"]),
        "kcu_ratio": sig(rows[3.0]["Kcu"] / rows[7.0]["Kcu"]),
        "flow_change_pct": sig(100 * (FR[7.0] - FR[3.0]) / FR[7.0]),
        "routh_vs_sim_pct": f"{abs(100 * (Kc_sim / Kcu - 1)):.2f}",
        "n_tests": str(n_tests) if n_tests else "",
        "cliff_L_per_h": sig(1000 * (FR[8.0] - FR[6.0])),
        "cliff_pct": sig(100 * (FR[8.0] - FR[6.0]) / FR[7.0], 1),
        "reagent_L_per_h": sig(1000 * FR[7.0]),
        "gain7": sig(gain7),
        "mL_per_pH": sig(1e6 / gain7),
        "single_min": f"{min(single['pH'][-1]):.1f}", "single_max": f"{max(single['pH'][-1]):.1f}",
        "staged_min": f"{min(two['pH'][-1]):.1f}", "staged_max": f"{max(two['pH'][-1]):.1f}",
        "kcu_bars": [[sp, to_h(rows[sp]["Kcu"])] for sp in (3.0, 4.0, 5.0, 6.0, 7.0)],
    }
    return {
        "facts": facts,
        "titration": {k: titration[k] for k in ("ratio", "pH", "r_eq", "gain_pH", "gain")},
        "single": dict(thin(single), FR_max=[s["FR_max"] for s in p["stages"][:1]],
                       disturbances=p["disturbances"]),
        "staged": dict(thin(two), FR_max=[s["FR_max"] for s in staged["stages"][:2]],
                       disturbances=staged["disturbances"]),
    }


if __name__ == "__main__":
    build_pages()
    names = copy_model()
    data = showcase()
    (OUT / "data").mkdir()
    (OUT / "data" / "showcase.json").write_text(json.dumps(data))
    print("Built %s with %d Python files; facts: %s" % (
        OUT, len(names), {k: v for k, v in data["facts"].items() if k != "kcu_bars"}))
