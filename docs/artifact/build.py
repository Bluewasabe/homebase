"""Build the shareable bake-off page: inline every screenshot as a data URI.

Run:  python docs/artifact/build.py [out.html] [template.html]
"""
import base64
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SHOTS = ROOT / "docs/screenshots/phase-1"
tpl_path = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "docs/artifact/template.html"
tpl = tpl_path.read_text(encoding="utf-8")


def inline(m):
    name = m.group(1)
    data = (SHOTS / f"{name}.jpg").read_bytes()
    return "data:image/jpeg;base64," + base64.b64encode(data).decode()


html = re.sub(r"\{\{IMG:([a-z0-9-]+)\}\}", inline, tpl)
out = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs/artifact/bakeoff.html"
out.write_text(html, encoding="utf-8")
print(out, f"{out.stat().st_size/1e6:.1f} MB")
