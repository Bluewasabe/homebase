"""Every live, linkable service must be linked from every front-door variant.

Run:  python ops/check-inventory.py
Exit: 0 when every variant links every live service, 1 otherwise.
"""
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
services = yaml.safe_load((ROOT / "inventory/services.yaml").read_text(encoding="utf-8"))
live = [s for s in services if s["status"] == "live" and s.get("url") and s.get("link", True)]

variants = {}
for p in sorted((ROOT / "homepage").glob("*/")):
    variants[p.name] = "".join(f.read_text(encoding="utf-8") for f in p.glob("*.yaml"))
for p in sorted((ROOT / "glance").glob("*/")):
    variants[p.name] = (p / "glance.yml").read_text(encoding="utf-8")

if not variants:
    print("no variant configs found")
    sys.exit(1)

bad = False
for name, text in variants.items():
    missing = [s["name"] for s in live if s["url"] not in text]
    line = f"{name}: {len(live) - len(missing)}/{len(live)} live services linked"
    if missing:
        line += f"  MISSING {missing}"
        bad = True
    print(line)
sys.exit(1 if bad else 0)
