"""Assemble the website in _site/: the static pages plus the Python model.

The browser needs the SAME phsim/*.py files that pytest tests, so we copy
them (not rewrite them) into _site/py/phsim/ and list them in a manifest
that site/js/py.js reads.

It also runs the model once to precompute the Home page showcase
(titration curve + two simulations), so the Home page needs no Python download.

Usage:  python scripts/build_site.py
        python -m http.server -d _site 8000     # then open http://localhost:8000
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE, MODEL, OUT = ROOT / "site", ROOT / "src" / "phsim", ROOT / "_site"

if OUT.exists():
    shutil.rmtree(OUT)
shutil.copytree(SITE, OUT)
(OUT / "py" / "phsim").mkdir(parents=True)
names = sorted(p.name for p in MODEL.glob("*.py"))
for name in names:
    shutil.copy(MODEL / name, OUT / "py" / "phsim" / name)
(OUT / "py" / "manifest.json").write_text(json.dumps(names))
(OUT / ".nojekyll").write_text("")      # serve files as-is on GitHub Pages


def showcase():
    """Home-page data, computed by the same api.py the Tool page calls."""
    sys.path.insert(0, str(ROOT / "src"))
    from phsim import api

    def thin(sim, n=600):
        step = max(1, len(sim["t"]) // n)
        return {k: ([[round(v, 4) for v in s[::step]] for s in sim[k]] if k != "t" else sim[k][::step])
                for k in ("t", "pH", "pH_measured", "FR", "SP")}

    p = json.loads(api.defaults())
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
    return {
        "titration": {k: titration[k] for k in ("ratio", "pH", "r_eq", "gain_pH", "gain")},
        "single": dict(thin(single), FR_max=[s["FR_max"] for s in p["stages"][:1]],
                       disturbances=p["disturbances"]),
        "staged": dict(thin(two), FR_max=[s["FR_max"] for s in staged["stages"][:2]],
                       disturbances=staged["disturbances"]),
    }


(OUT / "data").mkdir()
(OUT / "data" / "showcase.json").write_text(json.dumps(showcase()))
print("Built %s with %d Python files" % (OUT, len(names)))
