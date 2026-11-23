"""Website structure checks (no browser needed). The browser test itself is
scripts/e2e_browser_test.js, run in CI after the build."""
import re
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent / "site"
PAGES = sorted(SITE.glob("*.html"))


def test_every_page_uses_the_shared_partials():
    assert len(PAGES) == 8
    for page in PAGES:
        html = page.read_text()
        for name in ("head", "header", "footer"):
            assert f"<!--#include {name}-->" in html, (page.name, name)
            assert (SITE / "_partials" / f"{name}.html").exists()


def test_every_page_is_in_the_menu():
    header = (SITE / "_partials" / "header.html").read_text()
    for page in PAGES:
        assert f'href="{page.name}"' in header, page.name


def test_pyodide_version_is_set_in_exactly_one_place():
    files = [p for p in SITE.rglob("*") if p.is_file()]
    hard_coded = [p.name for p in files if re.search(r"pyodide@\d", p.read_text(errors="ignore"))]
    constant = [p.name for p in files if 'PYODIDE_VERSION = "' in p.read_text(errors="ignore")]
    assert hard_coded == [] and constant == ["py-worker.js"]
