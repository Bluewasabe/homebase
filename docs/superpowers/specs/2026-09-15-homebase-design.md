# Homebase — Design Spec

*Date: 2026-09-15 | Status: approved by Chris 2026-09-15 (incl. amendments: inventory source, service status, healthwatch feed)*

## Purpose

A single home base for the homelab: one page that links to every tool and shows
fleet health at a glance, backed by real up/down monitoring and, later, metrics and
logs. Primary user is Chris. Read-only for everyone by default; a later phase adds
an Authentik admin group that can take actions.

Goal it serves (from `~/.claude/CLAUDE.md`): *know where everything is, secure and
redundant, centrally managed, not frantically maintained.*

## Current state this replaces

| Thing | Where | Problem |
|---|---|---|
| Homepage container | Server-Rig :3005 | Orphaned, duplicate |
| homepage-vm 1005 | pve | Orphaned, duplicate |
| Homarr x2 | Server-Rig :7575, pve homarr-vm 1004 | Retired, still running |
| home.bookclub44.com | NPM -> 192.168.1.158 | Dead target |
| minecraft-grafana / -prometheus / -cadvisor | Server-Rig :3000/:9090/:8080 | Stale, Minecraft-only, on the least stable host |
| healthwatch | BlueRig scheduled task | Fleet sweep every 2 min, nothing displays it |

None of the September incidents (Server-Rig WSL memory ceiling and thread
exhaustion, PlexBoy USB hub resets, backups broken since late August) were visible
on any existing dashboard.

## Layered model

| Layer | Job | Tool |
|---|---|---|
| Front door | Links to every tool, one-glance status | Homepage **or** Glance (bake-off decides) |
| Up/down | Reachability, alert when down, status page | Uptime Kuma |
| Metrics + logs | Trends, disk, memory ceilings, log search | Prometheus + Grafana + Loki + Alloy (Chris builds it via the course) |
| Alerts | Push to Discord/phone | Uptime Kuma now, Grafana alerting later |
| Actions | Restart the thing | healthwatch queue today; Olivetin behind Authentik admin group in phase 5 |

## Placement

New LXC on pve (192.168.1.6):

| Field | Value |
|---|---|
| ID / name | 110 / `hub` |
| Template | Debian 12 |
| Resources | 4 GB RAM, 2 vCPU, 20 GB disk |
| Network | main LAN 192.168.1.0/24, static IP reserved on UDM Pro (value chosen at creation) |
| Runtime | Docker CE inside the LXC (nesting + keyctl enabled, same as LXC 100/101) |
| Exposure | LAN only. No NPM route. No public DNS. Remote access is phase 4. |

Why pve: it never runs games, never gets rebooted mid-week, and already hosts the
control plane (NPM). Monitoring must not live on the host it most needs to watch.
nginx-vm (1001) is reduced from 8 GB to 4 GB RAM to make room; NPM needs far less.

Everything in this project runs on `hub`: the bake-off variants, the promoted
winner, Uptime Kuma, and later the Grafana stack.

## Repository

`c:/Users/Bluew/Code/homebase` -> `github.com/Bluewasabe/homebase` (public; no
secrets committed). Uses the PLAN.md + CLAUDE.md phased methodology.

```
homebase/
├── README.md  PLAN.md  CLAUDE.md
├── docs/
│   ├── superpowers/specs/         this file
│   ├── comparison.md              bake-off: screenshots side by side, pros/cons
│   └── screenshots/<phase>/       1440x900 and 390x844 per variant
├── compose/
│   ├── uptime-kuma/docker-compose.yml
│   ├── bakeoff/docker-compose.yml     all six variants, ports 3101-3103, 3201-3203
│   └── hub/docker-compose.yml         the promoted winner on port 80
├── homepage/
│   ├── h1-console/   h2-rack/   h3-pocket/     (each: services.yaml, widgets.yaml,
│   │                                            bookmarks.yaml, settings.yaml)
├── glance/
│   ├── g1-feed/   g2-ops/   g3-pages/          (each: glance.yml)
├── course/                        Grafana tutorial (moved from observability/course)
├── stack/                         Grafana/Prometheus/Loki/Alloy compose + configs
│                                  (moved from observability/stack, retargeted to hub)
├── ops/
│   ├── deploy.sh                  rsync repo -> LXC, compose up, health-gated, rolls back
│   └── shoot.mjs                  screenshot every variant at both sizes
└── .env.example                   every variable the LXC .env needs, no values
```

Secrets (API tokens, Uptime Kuma password, Grafana admin password) live only in
`/opt/homebase/.env` on the LXC. `.env` is gitignored.

The existing `c:/Users/Bluew/Code/observability/` project is absorbed: its course
and stack move here and it is archived (folder renamed `observability--archived`,
note left in `referenceMDs-local-export/`).

## The six bake-off variants

Each variant is a complete, live configuration on its own port, sharing the same
Uptime Kuma instance and the same read-only credentials. Not mockups.

| Port | Variant | Concept | What it tests |
|---|---|---|---|
| 3101 | **H1 Console** (Homepage) | One column per machine (BlueRig, PlexBoy, Server-Rig, pve). Every service with a status dot and a live widget where one exists. Resource bars across the top. | Maximum information density |
| 3102 | **H2 Rack** (Homepage) | Organized by function: Media, Games, AI, Infra, Business, Dev. Large cards. Uptime Kuma summary is the headline. | Function-first mental model |
| 3103 | **H3 Pocket** (Homepage) | Phone-first, 3-second read for the workday away from home: fleet health strip, open alerts, top 8 links, everything else collapsed. | Remote / mobile use |
| 3201 | **G1 Feed** (Glance) | Start-page: monitor groups, Docker widget, calendar, weather, homelab RSS column. | Glance as a personal start page |
| 3202 | **G2 Ops** (Glance) | Glance pushed toward a console: monitor groups per host, server-stats, custom-API widgets against Uptime Kuma. | Whether Glance can match Homepage on ops |
| 3203 | **G3 Pages** (Glance) | Multi-page: Home, Game Servers, Media, Business, Dev. | Navigation as the organizing idea |

**Inventory source.** `plan/homelab-map.md` is stale (2026-03-19; Server-Rig now runs
atm11, bettermc, create, cobblemon, dragons, bedrock-creative/survival, palworld3 and
backup sidecars, none documented). The service inventory for Uptime Kuma and all six
variants is therefore generated from **healthwatch state** (`healthwatch/state/baseline.json`
and `latest.json`) plus a live `docker ps` on each host, written to `inventory/services.yaml`
in this repo. Phase 1 also rewrites the machine tables in `plan/homelab-map.md` from that
same data.

**Every service carries a status:**

| Status | Meaning | Uptime Kuma | Front door |
|---|---|---|---|
| live | expected up | monitor active, alerts | linked, status dot |
| paused | intentionally down, may return | monitor exists, paused | listed under "Paused", no dot |
| retired | not coming back | no monitor | listed under "Retired" or omitted |

Decisions as of 2026-09-15: `palworld2-server` **retired** (palworld3 exists; exit 137 was
the WSL memory ceiling). `hytale-server` **paused**. `tube-intel-web` + `tube-intel-worker`
**paused** (exit 137, same ceiling). home.bookclub44.com target, port 5001 forward, and
openclaw-gateway are **retired**. Nothing paused or retired is restarted by this project;
the Server-Rig `.wslconfig` memory cap must be raised first (separate task).

## Shared backing services (phase 1)

**Uptime Kuma** on `hub` at :3001, with monitors for:

- Every host: BlueRig, PlexBoy, Server-Rig, pve, nginx-vm, LXC 100 (fibi), LXC 101 (plausible)
- Every HTTP service in the map (NPM admin, Proxmox UI, Plex, Open WebUI, n8n,
  Authentik, PhotoPrism, file-browser, Ollama, TubeIntel, media-manager, fibi,
  plausible, searxng, excalidraw)
- Every game port: the eight Minecraft servers (TCP), Palworld x2, Hytale,
  Bedrock x2 (UDP: port monitor only)
- Notifications: Discord webhook (existing family server, channel chosen by Chris)

**Read-only credentials** required for live widgets:

| Credential | Who gets it | Owner |
|---|---|---|
| Proxmox API token, PVEAuditor role | Homepage/Glance Proxmox widget | Claude creates via SSH root@pve |
| Plex token | Plex widget | Claude reads from Preferences.xml on PlexBoy via SSH |
| Uptime Kuma API key | Homepage widget, Glance custom-API | Claude creates in Kuma after first login |
| UniFi read-only local user | UniFi widget | **Chris** (UDM Pro UI) |
| NPM API user | NPM widget | Claude creates via NPM admin (optional, phase 2) |

**healthwatch feed.** healthwatch on BlueRig already collects per-host disk free,
container state, and restart counts every 2 minutes and nothing displays it. `agent.ps1`
gains one step: after each sweep it copies `state/latest.json` to `hub` over SSH
(BlueRig's key authorized on the LXC). `hub` serves it read-only as
`http://hub:3009/latest.json` from a tiny static container. Both Homepage (`customapi`
widget) and Glance (`custom-api` widget) read it, so every variant shows per-host disk
free and container counts on day one. Disk thresholds (PlexBoy C: at 9% free on
2026-09-15 is the motivating case) render red in every variant.

**Not in phase 1:** Docker container widgets for remote hosts. They need a read-only
`docker-socket-proxy` on PlexBoy and Server-Rig plus a Hyper-V firewall rule on
Server-Rig. During the bake-off the Docker widgets show only `hub`'s own
containers; `docs/comparison.md` states this explicitly.

## Grafana course with visuals

Chris stands up Grafana himself. The existing ten-module course
(`observability/course/module-00..09`) is revised, not rewritten:

- Stack (Prometheus, Grafana, Loki, Alloy, cAdvisor) targets `hub`, not Server-Rig.
- windows_exporter installs natively on BlueRig, PlexBoy, and Server-Rig.
- cAdvisor plus docker-socket-proxy per Docker host (PlexBoy, Server-Rig, hub).
- Phase 1 of the course (decommission the old minecraft-* stack) moves to **after**
  Chris's Grafana is scraping, so monitoring never has a gap.
- Alerts go to the same Discord webhook as Uptime Kuma.

**Visuals.** Claude stands up a throwaway reference stack on `hub` at alternate
ports (`grafana-ref` :3300, `prometheus-ref` :9390, etc.), walks every module in
order capturing annotated screenshots of the real screens at each step, commits
them under `course/img/module-NN/`, then removes the reference stack. Architecture
and data-flow figures are inline SVG in the module markdown. Chris then deploys on
the canonical ports (:3000/:9090/:3100) using the screenshots as the "this is what
right looks like" check.

## Phases

| Phase | Scope | Exit criteria |
|---|---|---|
| 0 | Spec, repo, PLAN/CLAUDE, LXC 110 created, Docker installed, `ops/deploy.sh` working | `ssh root@<hub-ip> docker ps` works from BlueRig; deploy.sh deploys an empty stack and health-gates |
| 1 | Inventory from healthwatch + `docker ps`; Uptime Kuma + monitors (live/paused) + Discord; healthwatch feed to hub; read-only creds; six variants live; screenshots; `docs/comparison.md`; homelab-map.md machine tables regenerated | All six ports answer; every monitor green or explained in comparison.md; screenshots at 1440x900 and 390x844 for each variant, looked at; comparison committed; **Chris picks** |
| 2 | Winner promoted to port 80 on `hub` (URL is just `http://hub`); other five stopped (configs kept); retire Server-Rig homepage/homarr, pve homepage-vm/homarr-vm; remove dead home.bookclub44.com NPM host + DNS; docker-socket-proxy on PlexBoy + Server-Rig with Hyper-V rule; Docker widgets live | Duplicates gone; Docker widgets show all three hosts |
| 3 | Grafana course revision with visuals; reference stack captured and removed; Chris executes the course; old minecraft-* stack retired after his stack scrapes | Chris's Grafana shows all three Windows hosts and all Docker hosts; front door links to it |
| 4 | Authentik forward-auth on the front door and Grafana: `homebase-viewer` and `homebase-admin` groups; Grafana viewer/admin mapped from groups; remote access (Tailscale on hub, or UDM WireGuard, decided then) | Viewer login sees everything read-only; admin group exists with nothing to do yet |
| 5 | Actions: Olivetin behind `homebase-admin`; buttons for container restart per host and game-server ops (restart, backup now, who's online); reuses healthwatch queue or SSH | Admin can restart a game server from the front door; viewer cannot see the buttons |

Each phase is one PR, `phase-N-short-description`, `--base main`.

## Error handling and safety

- `ops/deploy.sh` mirrors FIBI's: rsync to `/opt/homebase`, `docker compose up -d`,
  poll each variant's port, roll back to the previous compose on failure.
- Nothing in this project is reachable from the internet until phase 4.
- All credentials created for widgets are read-only roles; no widget gets a token
  that can change state.
- Creating LXC 110 and shrinking nginx-vm are the only changes to existing
  infrastructure in phases 0-1. Retirements happen in phase 2 only after the winner
  is live.
- Server-Rig is fragile (WSL memory at 94%, thread exhaustion 09-02). Phase 2's
  socket proxy on Server-Rig is a single small container with a memory limit, and
  log reads there stay bounded.

## Testing

- `ops/shoot.mjs` (Playwright, same pattern as `fibi/tests/shoot.mjs`) screenshots
  every variant at 1440x900 and 390x844; screenshots are looked at before any
  "it works" claim.
- Uptime Kuma's own monitors are the integration test for the fleet inventory: a
  red monitor is either a real outage or a wrong entry, and comparison.md says which.
- Each Homepage/Glance config is validated by the container starting cleanly
  (`docker compose logs` free of YAML/config errors) before screenshotting.

## Out of scope

- VLANs, DDNS, backups, PhotoPrism consolidation (tracked in homelab-map goals).
- A family-facing status page (can be added in phase 4 via Uptime Kuma's status
  page; not part of this spec).
- Any write-capable action before phase 5.
