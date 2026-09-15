# PLAN.md — Homebase

Spec: `docs/superpowers/specs/2026-09-15-homebase-design.md`
Plan (phases 0+1): `docs/superpowers/plans/2026-09-15-phase-0-1-bakeoff.md`

## Status

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Spec, repo, LXC 110 `hub`, deploy script | ✅ 2026-09-15 |
| 1 | Uptime Kuma, healthwatch feed, six-variant bake-off, comparison | ✅ built 2026-09-15 — **Chris picks** |
| 2 | Promote winner to :80, retire duplicates, socket proxies, Docker widgets | 🔲 |
| 3 | Grafana course revision with visuals; Chris stands up the stack | 🔲 |
| 4 | Authentik viewer/admin groups; remote access | 🔲 |
| 5 | Actions via Olivetin (admin only) | 🔲 |

---

## Phase 0 — Foundation

- [x] Design spec written, reviewed, amended (inventory source, service status, healthwatch feed)
- [x] Repo `c:/Users/Bluew/Code/homebase`, branch `phase-1-bakeoff`
- [x] LXC 110 `hub` on pve: Debian 12, 4 GB, 2 vCPU, 20 GB, Docker 29, IP **192.168.1.141** (DHCP)
- [x] nginx-vm memory set 8192 → 4096 (applies on its next restart; not rebooted)
- [x] `ops/deploy.sh` — tar over ssh, compose up, port health gate, rollback
- [x] Uptime Kuma :3001, feed :3009 deployed and answering

### Phase 0 — Lessons Learned
- `tar` from Git Bash carries Windows uid 197609; extract with `--no-same-owner --no-same-permissions`.
- pve LVM-thin is overcommitted (398 GiB of thin volumes on a 365 GiB pool, 16 GiB VG free). Fine today, but don't add big disks without checking `pvesm status`.
- Plex on Windows keeps its token in the registry (`HKCU\Software\Plex, Inc.\Plex Media Server\PlexOnlineToken`), not Preferences.xml.

---

## Phase 1 — Bake-off

- [x] `inventory/hosts.yaml` + `inventory/services.yaml` generated from healthwatch state + `docker ps -a` (Server-Rig 31, PlexBoy 17) — homelab-map.md was 6 months stale
- [x] Service status vocabulary: live / paused / retired. Retired: palworld2, openclaw. Paused: hytale, tube-intel ×2
- [x] `ops/kuma-sync.py` → 55 monitors (ping per host, http, gamedig for all 12 game ports), status page `homelab`
- [x] healthwatch `agent.ps1` pushes a BOM-free `latest.json` to hub after every sweep; hub added to its host list
- [x] Read-only credentials: Proxmox `homepage@pve!homebase` (PVEAuditor), Plex token. Both in hub `.env` + `~/.ssh/homebase-secrets-2026-09-15.txt`
- [x] Six variants live: H1 :3101, H2 :3102, H3 :3103, G1 :3201, G2 :3202, G3 :3203
- [x] `ops/check-inventory.py` — every variant links all 29 live services
- [x] `ops/shoot.mjs` — screenshots at 1440×900 and 390×844, looked at
- [x] `docs/comparison.md` + artifact page (https://claude.ai/artifact/17RGq8xZi4mpF1hgStEynH)
- [x] homelab-map.md container tables regenerated (`ops/map-tables.py`)
- [x] PR opened — https://github.com/Bluewasabe/homebase/pull/1
- [x] Three from-scratch variants added on request: C1 Flight Deck :3301, C2 Rack :3302, C3 Transit :3303 (`custom/`, one nginx + mcstatus sidecar, `compose/custom`). Artifact: https://claude.ai/artifact/WHNeZyteFE9ZffZEx5Bh5U
- [ ] **Chris picks the winner** (nine candidates now)

### On Chris
- UniFi read-only local user (for a UniFi widget in phase 2)
- Discord channel + webhook URL for alerts (`DISCORD_WEBHOOK_URL` in hub `.env`, then rerun `ops/kuma-sync.py`)
- UDM Pro DHCP reservation for hub 192.168.1.141
- **File Browser on Server-Rig is broken**: compose publishes 8085→85 but the app listens on 80

### Phase 1 — Lessons Learned
- Homepage 2.x serves a statically generated page: settings.yaml (layout, theme, title) only take effect after `POST /api/revalidate`. A real browser triggers it via `/api/hash`; headless screenshots and fresh visitors do not. `ops/deploy.sh` now forces it after every deploy. (First diagnosis blamed the `layout:` map form; both forms work.)
- Homepage YAML: a label like `C: free` needs quotes (colon-space starts a mapping).
- PowerShell `Set-Content -Encoding UTF8` writes a BOM; `JSON.parse` and gjson both reject it. Write feed files with `[Text.UTF8Encoding]::new($false)`.
- Uptime Kuma `accepted_statuscodes` only takes the fixed buckets (`200-299`, `300-399`, …). CouchDB answers 401 everywhere, so its monitor accepts `400-499`.
- Glance `di:` icons for github / scrypted / cadvisor / homepage / homarr render blank; `si:` and `mdi:` fallbacks work.
- Custom pages: keep secrets out of the browser by letting nginx inject the Proxmox/Plex headers (`compose/custom/nginx`); the nginx image's envsubst leaves nginx's own `$vars` alone as long as no env var shares the name.
- Palworld has no external probe without its REST API; gamedig and Steam A2S both fail. Docker healthcheck via the feed is the signal.

---

## Phase 2 — Promote + retire *(not started)*
- [ ] Winner → `compose/hub` on :80; other five stopped, configs kept
- [ ] Stop Server-Rig `homepage` + `homarr`; stop pve `homepage-vm` (1005) + delete `homarr-vm` (1004)
- [ ] Remove `home.bookclub44.com` NPM host + Cloudflare record
- [ ] `docker-socket-proxy` (read-only) on PlexBoy + Server-Rig (+ Hyper-V rule `New-NetFirewallHyperVRule` for 2375)
- [ ] Docker widgets show all three hosts

## Phase 3 — Grafana course *(not started)*
- [ ] Move `observability/course` + `stack` here; retarget to hub
- [ ] Reference stack at alt ports; screenshot every module; remove it
- [ ] Chris executes; old minecraft-* stack retired once his Prometheus scrapes

## Phase 4 — Auth + remote *(not started)*
## Phase 5 — Actions *(not started)*
