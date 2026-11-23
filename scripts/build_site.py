"""Assemble the website in _site/: the static pages plus the Python model.

The browser needs the SAME phsim/*.py files that pytest tests, so we copy
them (not rewrite them) into _site/py/phsim/ and list them in a manifest
that site/js/py.js reads.

Usage:  python scripts/build_site.py
        python -m http.server -d _site 8000     # then open http://localhost:8000
"""
import json
import shutil
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
print("Built %s with %d Python files" % (OUT, len(names)))
