# Homebase Phase 0 + 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the `hub` LXC on pve with Uptime Kuma, the healthwatch feed, and six live front-door variants (three Homepage, three Glance), screenshotted and compared so Chris can pick one.

**Architecture:** One Debian 12 LXC (110, `hub`) running Docker. Three compose stacks under `/opt/homebase`: `uptime-kuma` (up/down layer), `feed` (nginx serving healthwatch's `latest.json`), `bakeoff` (six dashboards on 3101-3103 / 3201-3203). A YAML inventory in the repo is the single list of hosts and services; a checker proves every variant links every live service; a sync script creates Uptime Kuma monitors from the same file. Deploy is tar-over-ssh from BlueRig.

**Tech Stack:** Proxmox `pct`, Docker CE, Uptime Kuma 1.23, nginx:alpine, gethomepage/homepage, glanceapp/glance, Python 3 (`pyyaml`, `uptime-kuma-api`), Node 24 + puppeteer for screenshots.

## Global Constraints

- LXC 110 `hub`, Debian 12, 4 GB RAM, 2 vCPU, 20 GB disk, unprivileged, nesting+keyctl, LAN only (spec: Placement).
- Ports on hub: Uptime Kuma 3001, feed 3009, H1 3101, H2 3102, H3 3103, G1 3201, G2 3202, G3 3203 (spec: Variants, Feed).
- Secrets only in `/opt/homebase/.env` on hub and `~/.ssh/homebase-secrets-2026-09-15.txt` on BlueRig. Never committed.
- All credentials created are read-only (PVEAuditor, Plex read token).
- Service status is `live | paused | retired`. Retired: palworld2-server, openclaw-gateway, mission-control link target stays (container runs), home.bookclub44.com, port-5001 forward. Paused: hytale-server, tube-intel-web-1, tube-intel-worker-1.
- Nothing paused or retired is started. No existing container on any host is stopped in these phases.
- Screenshots at 1440x900 and 390x844 for every variant, looked at before claiming success.
- Git: branch `phase-1-bakeoff`, stage files by name, PR with `--base main`.

---

## File Structure

| File | Responsibility |
|---|---|
| `PLAN.md`, `CLAUDE.md`, `README.md` | Phase tracking, project rules, overview |
| `.env.example` | Every variable hub's `.env` needs, no values |
| `inventory/hosts.yaml` | Machines: name, ip, kind, ssh user |
| `inventory/services.yaml` | Every service: name, host, url, port, kind, status, groups, icon, widget hints |
| `ops/check-inventory.py` | Test: every `live` service URL appears in every variant config |
| `ops/kuma-sync.py` | Create/update Uptime Kuma monitors + status page from inventory |
| `ops/deploy.sh` | tar repo → `/opt/homebase` on hub, compose up, health-poll, rollback |
| `ops/shoot.mjs` | Screenshot every variant at both viewports |
| `ops/map-tables.py` | Print homelab-map.md container tables from inventory |
| `compose/uptime-kuma/docker-compose.yml` | Uptime Kuma |
| `compose/feed/docker-compose.yml`, `compose/feed/nginx.conf` | Static JSON feed on 3009 |
| `compose/bakeoff/docker-compose.yml` | Six dashboards |
| `homepage/h1-console/*.yaml`, `h2-rack`, `h3-pocket` | Homepage variants |
| `glance/g1-feed/glance.yml`, `g2-ops`, `g3-pages` | Glance variants |
| `docs/comparison.md`, `docs/screenshots/phase-1/*.jpg` | Bake-off evidence |
| `healthwatch/agent.ps1` (other repo), `healthwatch/config.json` | Feed push + hub host entry |

---

### Task 0.1: Repo scaffold

**Files:** Create `PLAN.md`, `CLAUDE.md`, `README.md`, `.env.example`, `package.json`.

- [ ] **Step 1: Write PLAN.md** with the six-phase table from the spec, phases 0 and 1 expanded into checklists matching this plan's tasks, and a "Lessons Learned" stub per phase.
- [ ] **Step 2: Write CLAUDE.md** with: repo layout, hub connection (`ssh root@<hub-ip>`), the three stacks and their restart commands, what is safe to commit, the status vocabulary, and "look at screenshots before claiming success".
- [ ] **Step 3: Write README.md** (short: what, why, how to deploy, how to add a service).
- [ ] **Step 4: Write `.env.example`**:

```
# /opt/homebase/.env on hub — never commit the real one
KUMA_ADMIN_USER=admin
KUMA_ADMIN_PASSWORD=
PROXMOX_URL=https://192.168.1.6:8006
PROXMOX_TOKEN_ID=homepage@pve!homebase
PROXMOX_TOKEN_SECRET=
PLEX_URL=http://192.168.1.217:32400
PLEX_TOKEN=
DISCORD_WEBHOOK_URL=
```

- [ ] **Step 5: `npm init -y && npm i puppeteer js-yaml`** (puppeteer's Chrome is already cached from FIBI).
- [ ] **Step 6: Rename branch** `git branch -m phase-1-bakeoff`; commit scaffold.

### Task 0.2: Create LXC 110 `hub`

**Interfaces:** Produces `HUB_IP` (recorded in `CLAUDE.md` and `inventory/hosts.yaml`).

- [ ] **Step 1: Create the container** on pve:

```bash
ssh root@192.168.1.6 'pct create 110 local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst \
  --hostname hub --memory 4096 --swap 1024 --cores 2 \
  --rootfs local-lvm:20 --net0 name=eth0,bridge=vmbr0,firewall=1,ip=dhcp \
  --unprivileged 1 --features nesting=1,keyctl=1 --onboot 1 \
  --ssh-public-keys /dev/stdin' < ~/.ssh/id_ed25519.pub
```

- [ ] **Step 2: Mirror LXC 101's Docker-friendly lines** (known working on this pve):

```bash
ssh root@192.168.1.6 'printf "lxc.apparmor.profile: unconfined\nlxc.cgroup2.devices.allow: a\nlxc.cap.drop: \n" >> /etc/pve/lxc/110.conf && pct start 110 && sleep 8 && pct exec 110 -- hostname -I'
```

Expected: an IP in 192.168.1.0/24. Record as `HUB_IP`.

- [ ] **Step 3: Install Docker + tools inside**:

```bash
ssh root@192.168.1.6 'pct exec 110 -- bash -c "apt-get update -qq && apt-get install -y -qq curl ca-certificates gnupg rsync && curl -fsSL https://get.docker.com | sh && docker --version && systemctl enable --now docker"'
```

- [ ] **Step 4: Verify from BlueRig**: `ssh -o StrictHostKeyChecking=accept-new root@$HUB_IP docker ps` → empty table, exit 0.
- [ ] **Step 5: Shrink nginx-vm for next boot** (no reboot now): `ssh root@192.168.1.6 'qm set 1001 --memory 4096'`. Record in PLAN.md that it takes effect on the next nginx-vm restart.
- [ ] **Step 6: Commit** `inventory/hosts.yaml` with all hosts including hub.

### Task 0.3: Deploy script + Uptime Kuma + feed

**Files:** `ops/deploy.sh`, `compose/uptime-kuma/docker-compose.yml`, `compose/feed/docker-compose.yml`, `compose/feed/nginx.conf`.

- [ ] **Step 1: Write `ops/deploy.sh`**:

```bash
#!/usr/bin/env bash
# Deploy the homebase repo to hub and bring the stacks up, health-gated.
#   ops/deploy.sh [stack ...]      default: all stacks
set -euo pipefail
HUB="${HUB:-root@HUB_IP}"
REMOTE=/opt/homebase
STACKS=("$@"); [ ${#STACKS[@]} -eq 0 ] && STACKS=(feed uptime-kuma bakeoff)
cd "$(dirname "$0")/.."
git ls-files -z | tar --null -czf - -T - | ssh "$HUB" "
  set -e; mkdir -p $REMOTE; rm -rf $REMOTE.prev; [ -d $REMOTE/compose ] && cp -a $REMOTE $REMOTE.prev || true
  tar -xzf - -C $REMOTE"
for s in "${STACKS[@]}"; do
  ssh "$HUB" "cd $REMOTE/compose/$s && docker compose --env-file $REMOTE/.env up -d --remove-orphans"
done
# health gate: every published port must answer within 90s
PORTS=$(ssh "$HUB" "cd $REMOTE && for s in ${STACKS[*]}; do docker compose -f compose/\$s/docker-compose.yml --env-file .env config 2>/dev/null | grep -oE 'published: \"?[0-9]+' | grep -oE '[0-9]+'; done")
fail=0
for p in $PORTS; do
  ok=0; for i in $(seq 1 30); do
    if ssh "$HUB" "curl -s -o /dev/null -m 3 http://127.0.0.1:$p/" ; then ok=1; break; fi; sleep 3; done
  if [ $ok = 1 ]; then echo "port $p ok"; else echo "port $p FAILED"; fail=1; fi
done
if [ $fail = 1 ]; then
  echo "rolling back"; ssh "$HUB" "[ -d $REMOTE.prev ] && rm -rf $REMOTE && mv $REMOTE.prev $REMOTE && cd $REMOTE && for s in ${STACKS[*]}; do (cd compose/\$s && docker compose --env-file $REMOTE/.env up -d); done"; exit 1
fi
echo "deploy ok"
```

- [ ] **Step 2: Write `compose/uptime-kuma/docker-compose.yml`**:

```yaml
services:
  uptime-kuma:
    image: louislam/uptime-kuma:1
    container_name: uptime-kuma
    restart: unless-stopped
    ports: ["3001:3001"]
    volumes:
      - kuma-data:/app/data
    logging: { driver: json-file, options: { max-size: "10m", max-file: "3" } }
    deploy: { resources: { limits: { memory: 512M } } }
volumes:
  kuma-data:
```

- [ ] **Step 3: Write the feed** — `compose/feed/docker-compose.yml`:

```yaml
services:
  feed:
    image: nginx:alpine
    container_name: feed
    restart: unless-stopped
    ports: ["3009:80"]
    volumes:
      - /opt/homebase/feed:/usr/share/nginx/html:ro
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
    logging: { driver: json-file, options: { max-size: "10m", max-file: "3" } }
    deploy: { resources: { limits: { memory: 64M } } }
```

`compose/feed/nginx.conf`:

```
server {
  listen 80;
  root /usr/share/nginx/html;
  add_header Access-Control-Allow-Origin * always;
  add_header Cache-Control "no-store" always;
  location / { autoindex off; try_files $uri =404; }
}
```

- [ ] **Step 4: Seed hub**: `ssh root@$HUB_IP 'mkdir -p /opt/homebase/feed && echo "{\"overall\":\"UNKNOWN\",\"hosts\":[]}" > /opt/homebase/feed/latest.json'`; create `/opt/homebase/.env` from `.env.example` with a generated `KUMA_ADMIN_PASSWORD` (`openssl rand -base64 24`); copy the password into `~/.ssh/homebase-secrets-2026-09-15.txt` on BlueRig.
- [ ] **Step 5: Run** `ops/deploy.sh feed uptime-kuma`. Expected: `port 3009 ok`, `port 3001 ok`, `deploy ok`.
- [ ] **Step 6: Verify** `curl -s http://$HUB_IP:3009/latest.json` returns the seed JSON; `curl -sI http://$HUB_IP:3001` returns 200/302.
- [ ] **Step 7: Commit** the four files.

### Task 1.1: Inventory + checker

**Files:** `inventory/services.yaml`, `ops/check-inventory.py`.

**Interfaces:** Produces the service schema every later task reads:

```yaml
- name: cobblemon-mc          # container or service name
  label: Cobblemon             # display name
  host: Server-Rig             # key into hosts.yaml
  kind: game-mc | game-udp | http | tcp | infra
  url: http://192.168.1.5:2342 # link target (omit for game ports)
  port: 25572
  status: live | paused | retired
  fn: media | games | ai | infra | business | dev | family
  icon: photoprism.png         # dashboard-icons name
  kuma: gamedig:minecraft | http | port | ping | none
```

- [ ] **Step 1: Write `inventory/services.yaml`** from the 2026-09-15 `docker ps` sweeps (Server-Rig 31 containers, PlexBoy 17) plus pve guests, NPM, Proxmox UI, UDM, Vaultwarden (8222, newly found, not in the map), Plex native, healthwatch feed, Uptime Kuma, and the six variants themselves. Statuses per Global Constraints.
- [ ] **Step 2: Write `ops/check-inventory.py`**:

```python
"""Every live service with a url must be linked from every variant config."""
import sys, pathlib, yaml
root = pathlib.Path(__file__).resolve().parent.parent
svcs = yaml.safe_load((root/'inventory/services.yaml').read_text())
live = [s for s in svcs if s['status']=='live' and s.get('url') and s.get('link', True)]
variants = {p.name: ''.join(f.read_text() for f in p.glob('*.yaml')) for p in (root/'homepage').iterdir()}
variants |= {p.name: (p/'glance.yml').read_text() for p in (root/'glance').iterdir()}
bad = 0
for v, text in variants.items():
    missing = [s['name'] for s in live if s['url'] not in text]
    print(f"{v}: {len(live)-len(missing)}/{len(live)} live services linked" + (f"  MISSING {missing}" if missing else ''))
    bad |= bool(missing)
sys.exit(bad)
```

- [ ] **Step 3: Run it** — expected: exits 1 (no variants yet). Commit both files.

### Task 1.2: Uptime Kuma monitors from inventory

**Files:** `ops/kuma-sync.py`.

- [ ] **Step 1: `pip install uptime-kuma-api pyyaml`** on BlueRig.
- [ ] **Step 2: Write `ops/kuma-sync.py`** — first-run `setup()` if needed, then for each host a `ping` monitor, for each service by `kuma:` kind an `http` / `port` / `gamedig` monitor named `<host> · <label>`, `paused` services created then paused, `retired` skipped; then a status page `homelab` (slug used by the Homepage widget and Glance JSON) containing every monitor grouped by host; Discord notification added only if `DISCORD_WEBHOOK_URL` is non-empty. Idempotent: match on monitor name.
- [ ] **Step 3: Run** `python ops/kuma-sync.py` with `KUMA_URL=http://$HUB_IP:3001` and credentials from the secrets file. Expected output: one line per monitor `created|updated|paused`, then `status page homelab: N monitors`.
- [ ] **Step 4: Verify** `curl -s http://$HUB_IP:3001/api/status-page/homelab | head -c 300` returns JSON with `publicGroupList`. Wait 2 minutes, then `curl -s http://$HUB_IP:3001/api/status-page/heartbeat/homelab` shows heartbeats. Note every red monitor and why in a scratch list for comparison.md.
- [ ] **Step 5: Commit**.

### Task 1.3: healthwatch feed

**Files:** Modify `c:/Users/Bluew/Code/healthwatch/agent.ps1:242` (after latest.json write), `healthwatch/config.json` (add hub host).

- [ ] **Step 1: Add the push** right after line 242:

```powershell
  # homebase feed: publish the snapshot to hub (best effort, never fails the sweep)
  try {
    $feedTarget = 'root@HUB_IP:/opt/homebase/feed/latest.json'
    & scp -q -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=8 (Join-Path $StateDir 'latest.json') $feedTarget 2>$null
  } catch { Write-Log "feed push failed: $_" }
```

(Confirm `Write-Log` is the agent's log function name; use whatever it is.)

- [ ] **Step 2: Add hub to `config.json` hosts**: `{ "name": "hub", "ip": "HUB_IP", "mode": "portsonly", "critical": false, "ports": [{"port":3001,"label":"uptime-kuma"},{"port":3009,"label":"feed"},{"port":3101,"label":"h1"},{"port":3102,"label":"h2"},{"port":3103,"label":"h3"},{"port":3201,"label":"g1"},{"port":3202,"label":"g2"},{"port":3203,"label":"g3"}] }`
- [ ] **Step 3: Run one sweep by hand** (`powershell -File agent.ps1` with whatever switch runs a single sweep; check the file header). Expected: `curl -s http://$HUB_IP:3009/latest.json | python -c "import json,sys; d=json.load(sys.stdin); print(d['generatedAtLocal'], d['overall'], len(d['hosts']))"` prints a timestamp from now.
- [ ] **Step 4: Commit healthwatch changes in its own repo** (if it is one) or note in PLAN.md that healthwatch is uncommitted local tooling.

### Task 1.4: Read-only credentials

- [ ] **Step 1: Proxmox token**:

```bash
ssh root@192.168.1.6 'pveum user add homepage@pve --comment "homebase read-only" 2>/dev/null; pveum acl modify / -user homepage@pve -role PVEAuditor; pveum user token add homepage@pve homebase --privsep 0 --output-format json'
```

Copy `value` into hub `.env` `PROXMOX_TOKEN_SECRET` and the secrets file.

- [ ] **Step 2: Plex token**: `ssh Bluew@192.168.1.217 powershell -c "Select-String -Path \"$env:LOCALAPPDATA\Plex Media Server\Preferences.xml\" -Pattern 'PlexOnlineToken=\"([^\"]+)\"' | % { $_.Matches[0].Groups[1].Value }"` → `PLEX_TOKEN` in hub `.env` and secrets file. Verify: `curl -s "http://192.168.1.217:32400/identity?X-Plex-Token=..." | head -c 200`.
- [ ] **Step 3: Verify Proxmox token**: `curl -sk -H "Authorization: PVEAPIToken=homepage@pve!homebase=<secret>" https://192.168.1.6:8006/api2/json/nodes | head -c 200` returns node list.

### Task 1.5: Homepage variants H1, H2, H3

**Files:** `homepage/h1-console/{settings,services,widgets,bookmarks,docker}.yaml`, same for `h2-rack`, `h3-pocket`; `compose/bakeoff/docker-compose.yml` (homepage half).

- [ ] **Step 1: Compose** — three `ghcr.io/gethomepage/homepage:latest` services, container names `h1-console` etc., ports 3101-3103→3000, each mounting `../../homepage/<variant>:/app/config` and `/var/run/docker.sock:/var/run/docker.sock:ro`, env `HOMEPAGE_ALLOWED_HOSTS=*`, `HOMEPAGE_VAR_PROXMOX_TOKEN_ID`, `HOMEPAGE_VAR_PROXMOX_TOKEN_SECRET`, `HOMEPAGE_VAR_PLEX_TOKEN`, `HOMEPAGE_VAR_HUB_IP` from `.env`; memory limit 256M; log rotation.
- [ ] **Step 2: H1 Console** — `settings.yaml`: `title: Console`, `theme: dark`, `color: zinc`, `headerStyle: clean`, `layout:` four groups `BlueRig`, `PlexBoy`, `Server-Rig`, `pve` each `style: column`, plus `Hub`. `widgets.yaml`: `resources` (hub cpu/mem/disk), `datetime`, `search`, and a `customapi` per host against `http://{{HOMEPAGE_VAR_HUB_IP}}:3009/latest.json` mapping `hosts.N.cpuPct`, `memUsedPct`, `disks.0.freePct`. `services.yaml`: every service under its machine group with `href`, `icon`, `siteMonitor`, widgets for `proxmox`, `plex`, `uptimekuma` (slug `homelab`), `photoprism`? (needs key, skip), `ollama`? (no widget; siteMonitor only). Paused/retired in a final `Paused / Retired` group without `siteMonitor`.
- [ ] **Step 3: H2 Rack** — `color: slate`, `headerStyle: boxed`, `layout` groups `Media`, `Games`, `AI`, `Infra`, `Business`, `Dev`, `Family` in `style: row, columns: 3`. `widgets.yaml`: `uptimekuma` summary is first, then `datetime`. Uses `fn:` from inventory for grouping.
- [ ] **Step 4: H3 Pocket** — `color: neutral`, `headerStyle: underlined`, `hideVersion: true`, `layout`: `Fleet` (customapi health strip: overall, warnCount, critCount, per-host disk min) and `Alerts` (customapi list of `alerts[].msg`) expanded; `Top 8` expanded (Plex, Proxmox, NPM, Uptime Kuma, n8n, Open WebUI, PhotoPrism, Vaultwarden); every other group `initiallyCollapsed: true`. Single column (`layout` default with `style: column`).
- [ ] **Step 5: Run** `python ops/check-inventory.py` → three Homepage variants all `N/N`. Deploy `ops/deploy.sh bakeoff`. `ssh root@$HUB_IP 'docker logs h1-console --tail 30'` (and h2, h3) free of `error`/`Invalid`.
- [ ] **Step 6: Commit**.

### Task 1.6: Glance variants G1, G2, G3

**Files:** `glance/g1-feed/glance.yml`, `glance/g2-ops/glance.yml`, `glance/g3-pages/glance.yml`; compose additions.

- [ ] **Step 1: Compose** — three `glanceapp/glance:latest`, ports 3201-3203→8080, mount `../../glance/<variant>/glance.yml:/app/config/glance.yml:ro` and docker socket ro; env `HUB_IP`, `PROXMOX_*`, `PLEX_TOKEN` (Glance reads `${VAR}` from env). Memory 128M.
- [ ] **Step 2: G1 Feed** — single page, three columns: small (clock, weather Philadelphia, calendar, bookmarks by fn), full (monitor groups: Hub, PlexBoy, Server-Rig, pve as `monitor` widgets with `sites`; `docker-containers`; `custom-api` healthwatch summary), small (RSS: selfh.st, Grafana blog, r/homelab via `reddit` widget). Theme: default dark.
- [ ] **Step 3: G2 Ops** — single page, `server-stats` at top, `monitor` widget per host with `style: compact`, `custom-api` widget rendering the healthwatch feed as a table (host, cpu, mem, worst disk, containers running/total, restart count) with Go template conditionals coloring `freePct < 10` red; `custom-api` against `http://${HUB_IP}:3001/api/status-page/heartbeat/homelab` showing red monitors; `docker-containers`. Theme: custom `background-color`, `primary-color` to look like a console.
- [ ] **Step 4: G3 Pages** — pages `Home` (health strip + top links), `Game Servers` (monitors per game port + bookmarks + healthwatch container list filtered to `-mc`/`palworld`/`bedrock`), `Media` (Plex, PhotoPrism, media-manager, file-browser), `AI` (Ollama x2, Open WebUI, n8n, searxng, excalidraw), `Infra` (pve, NPM, Authentik, Vaultwarden, Uptime Kuma, UDM), `Business & Dev` (fibi, plausible, TubeIntel paused, repos).
- [ ] **Step 5: Run** checker → all six `N/N`. Deploy `bakeoff`. Logs for g1/g2/g3 free of `error`/`failed to parse`.
- [ ] **Step 6: Commit**.

### Task 1.7: Screenshots and review loop

**Files:** `ops/shoot.mjs`, `docs/screenshots/phase-1/*.jpg`.

- [ ] **Step 1: Write `ops/shoot.mjs`** (puppeteer, same shape as FIBI's): for each of the six `{name, port}` and each viewport (`desktop 1440x900 dpr1`, `mobile 390x844 dpr2`), `goto http://HUB_IP:port/`, `waitUntil networkidle2`, sleep 4000 for widgets, full-page JPEG q85 to `docs/screenshots/phase-1/<name>-<viewport>.jpg`. Also shoot Uptime Kuma's status page `/status/homelab`.
- [ ] **Step 2: Run** `node ops/shoot.mjs` → 13 files.
- [ ] **Step 3: Look at every file** (Read tool). For each variant list what is broken: empty widgets, `API error`, overflow, unreadable mobile. Fix configs, redeploy, reshoot. Repeat until each variant is clean or the defect is explained in comparison.md.
- [ ] **Step 4: Commit** screenshots.

### Task 1.8: Comparison doc, map tables, artifact

**Files:** `docs/comparison.md`, `ops/map-tables.py`, `plan/homelab-map.md` (other folder), artifact HTML in scratchpad.

- [ ] **Step 1: `ops/map-tables.py`** prints a markdown table per host (`Container | Port | Purpose | Status`) from inventory. Replace the PlexBoy and Server-Rig container tables in `plan/homelab-map.md` with its output and bump the "Last updated" line.
- [ ] **Step 2: `docs/comparison.md`**: per variant, both screenshots, what it shows live, what is stubbed until phase 2 (remote Docker widgets), red monitors and why, pros/cons, and a scoring table (glanceability, density, mobile, live data, config effort, extensibility). No recommendation stronger than one paragraph; Chris picks.
- [ ] **Step 3: Artifact page**: private artifact with an architecture SVG (hosts → exporters/feed → hub → variants), the layered model, all screenshots embedded as data URIs, and the scoring table. Publish, share link.
- [ ] **Step 4: Commit**.

### Task 1.9: Push and PR

- [ ] **Step 1** `git push -u origin phase-1-bakeoff` after `gh repo create Bluewasabe/homebase --public --source=. --remote=origin` (repo does not exist yet). Verify no `.env`, no secrets, no tokens in `git grep -i token`.
- [ ] **Step 2** `gh pr create --base main --title "Phase 0+1 — hub LXC, Uptime Kuma, six-variant bake-off"` with the comparison summary and screenshot links. Show the URL.
- [ ] **Step 3** Update PLAN.md lessons learned; update `referenceMDs-local-export/homebase/CLAUDE.md`; update memory.

---

## Self-review

- Spec coverage: placement (0.2), repo (0.1), variants (1.5, 1.6), Uptime Kuma + statuses (1.2), credentials (1.4), healthwatch feed (1.3), inventory source + map regen (1.1, 1.8), screenshots + comparison (1.7, 1.8), deploy/rollback (0.3), PR (1.9). Grafana course, retirements, auth, actions are phases 2-5, not here.
- Placeholders: `HUB_IP` is a value discovered in 0.2 and substituted everywhere after; noted as such.
- Names consistent: status page slug `homelab`, feed path `/opt/homebase/feed/latest.json`, port table matches spec.
