# CLAUDE.md — Homebase

Global rules (git workflow, shell env, GitHub account) live in `~/.claude/CLAUDE.md`.
Homelab context lives in `c:/Users/Bluew/Code/CLAUDE.md`.

---

## What this is

The homelab's front door and monitoring layer. One LXC (`hub`, 110 on pve,
**192.168.1.141**) runs Uptime Kuma, a static feed of healthwatch's fleet snapshot,
and the dashboard. Phase 1 runs six dashboard variants side by side so Chris can pick;
phase 2 promotes the winner to port 80.

Spec: `docs/superpowers/specs/2026-09-15-homebase-design.md`. Status: `PLAN.md`.

## Connect

```bash
ssh root@192.168.1.141          # hub (BlueRig key authorized)
ssh root@192.168.1.6            # pve: pct exec 110 -- ...
```

Secrets: `/opt/homebase/.env` on hub; backup at `~/.ssh/homebase-secrets-2026-09-15.txt`
on BlueRig. `.env.example` lists every key. **Never commit `.env`.**

## Layout

```
inventory/hosts.yaml       machines            inventory/services.yaml  every service (status: live|paused|retired)
compose/uptime-kuma/       :3001               compose/feed/            :3009 nginx serving /opt/homebase/feed/latest.json
compose/bakeoff/           six variants        compose/hub/             (phase 2) the winner on :80
homepage/h1-console h2-rack h3-pocket          glance/g1-feed g2-ops g3-pages
ops/deploy.sh              tar→hub, compose up, port health gate, rollback
ops/kuma-sync.py           inventory → Uptime Kuma monitors + status page `homelab` (idempotent)
ops/check-inventory.py     test: every live service linked from every variant
ops/shoot.mjs              screenshots 1440×900 + 390×844 → docs/screenshots/<phase>/
ops/map-tables.py          prints homelab-map.md container tables from inventory
docs/comparison.md         bake-off evidence
```

## Daily commands

| Task | Command |
|---|---|
| Deploy everything | `bash ops/deploy.sh` |
| Deploy one stack | `bash ops/deploy.sh bakeoff` |
| Config-only change to a variant | deploy, then `ssh root@192.168.1.141 docker restart h1-console` (Homepage caches config; Glance too) |
| Add/change a service | edit `inventory/services.yaml` → edit each variant → `python ops/check-inventory.py` → `KUMA_ENV=~/.ssh/homebase-secrets-2026-09-15.txt python ops/kuma-sync.py` |
| Screenshots | `node ops/shoot.mjs docs/screenshots/<phase>` then **look at every file** |
| Feed check | `curl -s http://192.168.1.141:3009/latest.json \| head -c 300` |

healthwatch (`c:/Users/Bluew/Code/healthwatch`, not a git repo) pushes the feed. If the
feed is stale, check `healthwatch/agent.log` for `feed push failed`.

## Rules

- Every service in a dashboard comes from `inventory/services.yaml`. The checker must pass before a deploy.
- Read-only credentials only. No token that can change state goes into any widget.
- Nothing paused or retired gets started by this project. Nothing on other hosts gets stopped until phase 2.
- **Look at screenshots before claiming a variant works** (FIBI lesson). Both viewports.
- Kuma monitor names are `<host> · <label>`; the sync matches on name, so renaming a label creates a new monitor (delete the old one in the UI).
- Homepage 2.x: `layout:` must be the list form. Quote any label containing `: `.
- Glance: `${VAR}` in `glance.yml` must exist in the container env or Glance refuses to start.

## Safe to commit

Everything except `.env`, `node_modules/`, and anything under `feed/` on hub. Screenshots are committed (JPEG q85).

## Phases

See `PLAN.md`. One PR per phase, branch `phase-N-short-description`, `gh pr create --base main`.
