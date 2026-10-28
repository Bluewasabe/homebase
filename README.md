# Homebase

The homelab's front door: one page that links to every tool and shows fleet health
at a glance, backed by Uptime Kuma for up/down and a live feed from healthwatch.
Runs on a small Proxmox LXC (`hub`, 192.168.1.141). LAN only.

## For the person using it

| What | Where |
|---|---|
| Bake-off variants (pick one) | H1 Console `:3101` · H2 Rack `:3102` · H3 Pocket `:3103` · G1 Feed `:3201` · G2 Ops `:3202` · G3 Pages `:3203` |
| Up/down for every host and service | Uptime Kuma `:3001`, public status page `/status/homelab` |
| Fleet snapshot (JSON) | `:3009/latest.json`, refreshed every 5 minutes by healthwatch on BlueRig |
| Comparison with screenshots | `docs/comparison.md` |

Service status vocabulary: **live** (linked, monitored, alerts), **paused** (monitor exists
but silenced, listed under Paused), **retired** (not coming back).

## For the person maintaining it

```bash
bash ops/deploy.sh                 # ship tracked files to hub, compose up, health gate, rollback
python ops/check-inventory.py      # every live service linked from every variant?
KUMA_ENV=~/.ssh/homebase-secrets-2026-09-15.txt python ops/kuma-sync.py   # inventory → monitors
node ops/shoot.mjs docs/screenshots/phase-1                                # screenshots, then look at them
```

`inventory/services.yaml` is the only list of services. Add a service there, add it to
each variant, run the checker, run the Kuma sync, deploy. Secrets live only in
`/opt/homebase/.env` on hub (`.env.example` lists the keys).

Layout, rules, and gotchas: `CLAUDE.md`. Phase tracking: `PLAN.md`. Design: `docs/superpowers/specs/`.

## Where this is going

1. **Phase 2** — promote the chosen variant to port 80, retire the two orphaned Homepages
   and Homarrs, add read-only Docker socket proxies so container widgets cover every host.
2. **Phase 3** — Grafana/Prometheus/Loki course with screenshots, stood up by Chris on hub.
3. **Phase 4** — Authentik viewer/admin groups, remote access.
4. **Phase 5** — admin-only actions (restart a game server) via Olivetin.
