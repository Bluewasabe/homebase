"""Create/update Uptime Kuma monitors and the `homelab` status page from inventory/.

Run:
  KUMA_URL=http://192.168.1.141:3001 KUMA_USER=admin KUMA_PASSWORD=... python ops/kuma-sync.py
  (or point KUMA_ENV at a .env-style file that has KUMA_ADMIN_USER / KUMA_ADMIN_PASSWORD)

Idempotent: monitors are matched by name ("<host> · <label>"). paused services are
created then paused; retired services are skipped; kuma: none is skipped.
DISCORD_WEBHOOK_URL (env) adds a default Discord notification when non-empty.
"""
import os
import pathlib
import sys

import yaml
from uptime_kuma_api import MonitorType, NotificationType, UptimeKumaApi

ROOT = pathlib.Path(__file__).resolve().parent.parent


def load_env_file(path):
    out = {}
    for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


env = {}
if os.environ.get("KUMA_ENV"):
    env = load_env_file(os.environ["KUMA_ENV"])
URL = os.environ.get("KUMA_URL") or f"http://{env.get('HUB_IP', '192.168.1.141')}:3001"
USER = os.environ.get("KUMA_USER") or env.get("KUMA_ADMIN_USER", "admin")
PASSWORD = os.environ.get("KUMA_PASSWORD") or env.get("KUMA_ADMIN_PASSWORD", "")
WEBHOOK = os.environ.get("DISCORD_WEBHOOK_URL") or env.get("DISCORD_WEBHOOK_URL", "")
if not PASSWORD:
    sys.exit("no Kuma password (KUMA_PASSWORD or KUMA_ENV)")

hosts = {h["name"]: h for h in yaml.safe_load((ROOT / "inventory/hosts.yaml").read_text(encoding="utf-8"))}
services = yaml.safe_load((ROOT / "inventory/services.yaml").read_text(encoding="utf-8"))

api = UptimeKumaApi(URL, timeout=30)
if api.need_setup():
    api.setup(USER, PASSWORD)
    print("first-run setup done")
api.login(USER, PASSWORD)

existing = {m["name"]: m for m in api.get_monitors()}
planned = []  # (name, host, kwargs, paused)

# one ping monitor per host that has an IP and is not a cloud bucket
for h in hosts.values():
    if h.get("ip"):
        planned.append((f"{h['name']} · host", h["name"], dict(type=MonitorType.PING, hostname=h["ip"], interval=60), False))

for s in services:
    kuma = s.get("kuma", "none")
    if s["status"] == "retired" or kuma == "none":
        continue
    host = hosts.get(s["host"], {})
    name = f"{s['host']} · {s['label']}"
    paused = s["status"] == "paused" or s.get("monitor") == "paused"
    if kuma == "http":
        target = s.get("check") or s["url"]
        codes = ["200-299", "300-399"] + [str(c)[0] + "00-" + str(c)[0] + "99" for c in s.get("accept", [])]
        kw = dict(type=MonitorType.HTTP, url=target, interval=60, maxretries=2,
                  accepted_statuscodes=sorted(set(codes)), ignoreTls=True)
    elif kuma == "port":
        kw = dict(type=MonitorType.PORT, hostname=host["ip"], port=int(s["port"]), interval=60, maxretries=2)
    elif kuma == "ping":
        kw = dict(type=MonitorType.PING, hostname=host["ip"], interval=60)
    elif kuma == "steam":
        kw = dict(type=MonitorType.STEAM, hostname=host["ip"], port=int(s.get("query", s["port"])), interval=120, maxretries=3)
    elif kuma.startswith("gamedig:"):
        kw = dict(type=MonitorType.GAMEDIG, game=kuma.split(":", 1)[1], hostname=host["ip"],
                  port=int(s["port"]), interval=120, maxretries=3)
    else:
        print(f"skip {name}: unknown kuma kind {kuma}")
        continue
    planned.append((name, s["host"], kw, paused))

ids_by_host = {}
for name, host, kw, paused in planned:
    if name in existing:
        mid = existing[name]["id"]
        api.edit_monitor(mid, name=name, **kw)
        verb = "updated"
    else:
        mid = api.add_monitor(name=name, **kw)["monitorID"]
        verb = "created"
    if paused:
        api.pause_monitor(mid)
        verb += "+paused"
    else:
        try:
            api.resume_monitor(mid)
        except Exception:
            pass
    ids_by_host.setdefault(host, []).append(mid)
    print(f"{verb:16} {name}")

# status page: one group per host, weight by order in hosts.yaml
order = list(hosts.keys())
groups = []
for i, host in enumerate(sorted(ids_by_host, key=lambda h: order.index(h) if h in order else 99)):
    groups.append({"name": host, "weight": i + 1, "monitorList": [{"id": m} for m in ids_by_host[host]]})
slug = "homelab"
pages = {p["slug"] for p in api.get_status_pages()}
if slug not in pages:
    api.add_status_page(slug, "Homelab")
api.save_status_page(slug, title="Homelab", description="Every host and service the home base watches.",
                     theme="dark", showTags=True, publicGroupList=groups)
print(f"status page {slug}: {sum(len(g['monitorList']) for g in groups)} monitors in {len(groups)} groups")

if WEBHOOK:
    names = {n["name"] for n in api.get_notifications()}
    if "Discord" not in names:
        api.add_notification(name="Discord", type=NotificationType.DISCORD, discordWebhookUrl=WEBHOOK,
                             isDefault=True, applyExisting=True)
        print("discord notification added (default, applied to existing)")

api.disconnect()
