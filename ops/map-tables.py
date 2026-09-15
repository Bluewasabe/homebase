"""Print homelab-map.md container tables from inventory/services.yaml.

Run:  python ops/map-tables.py [host ...]      default: Server-Rig PlexBoy
Paste the output over the matching table in c:/Users/Bluew/Code/plan/homelab-map.md.
"""
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
services = yaml.safe_load((ROOT / "inventory/services.yaml").read_text(encoding="utf-8"))
hosts = sys.argv[1:] or ["Server-Rig", "PlexBoy"]

for host in hosts:
    rows = [s for s in services if s["host"] == host]
    print(f"\n### {host} — containers (inventory 2026-09-15)\n")
    print("| Container | Port | Purpose | Status |")
    print("|-----------|------|---------|--------|")
    for s in rows:
        port = s.get("port", "")
        proto = "/udp" if s.get("kind") == "game-udp" else ""
        purpose = s.get("note") or s["label"]
        print(f"| {s['name']} | {port}{proto} | {purpose} | {s['status']} |")
