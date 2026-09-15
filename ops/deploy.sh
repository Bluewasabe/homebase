#!/usr/bin/env bash
# Deploy the homebase repo to hub and bring stacks up, health-gated.
#
#   ops/deploy.sh [stack ...]        default: feed uptime-kuma bakeoff
#   HUB=root@192.168.1.141 ops/deploy.sh bakeoff
#
# Ships only git-tracked files (tar over ssh), keeps the previous tree in
# /opt/homebase.prev, polls every published port, rolls back on failure.
set -euo pipefail
HUB="${HUB:-root@192.168.1.141}"
REMOTE=/opt/homebase
STACKS=("$@")
[ ${#STACKS[@]} -eq 0 ] && STACKS=(feed uptime-kuma bakeoff custom)
cd "$(dirname "$0")/.."

echo "==> shipping tracked files to $HUB:$REMOTE"
git ls-files -z | tar --null --owner=0 --group=0 -czf - -T - | ssh "$HUB" "
  set -e
  mkdir -p $REMOTE
  rm -rf $REMOTE.prev
  if [ -d $REMOTE/compose ]; then mkdir -p $REMOTE.prev && cp -a $REMOTE/compose $REMOTE/homepage $REMOTE/glance $REMOTE.prev/ 2>/dev/null || true; fi
  tar --no-same-owner --no-same-permissions -xzf - -C $REMOTE && chmod +x $REMOTE/ops/*.sh"

for s in "${STACKS[@]}"; do
  echo "==> compose up: $s"
  ssh "$HUB" "cd $REMOTE/compose/$s && docker compose --env-file $REMOTE/.env up -d --build --remove-orphans --quiet-pull"
done

# Homepage 2.x serves a statically generated page and re-reads settings.yaml only
# when /api/revalidate is hit (a real browser does this via /api/hash; headless
# screenshots and fresh visitors do not). Force it after every deploy.
echo "==> homepage revalidate"
for p in 3101 3102 3103; do
  ssh "$HUB" "docker ps --format '{{.Ports}}' | grep -q ':$p->' && docker restart \$(docker ps --format '{{.Names}} {{.Ports}}' | grep ':$p->' | cut -d' ' -f1) >/dev/null && sleep 6 && curl -s -o /dev/null -m 10 -w '    %{http_code} revalidate :$p\n' -X POST http://127.0.0.1:$p/api/revalidate" || true
done

echo "==> health gate"
PORTS=$(ssh "$HUB" "cd $REMOTE && for s in ${STACKS[*]}; do
  docker compose -f compose/\$s/docker-compose.yml --env-file .env config 2>/dev/null \
    | grep -oE 'published: \"?[0-9]+' | grep -oE '[0-9]+'; done")
fail=0
for p in $PORTS; do
  ok=0
  for i in $(seq 1 30); do
    if ssh "$HUB" "curl -s -o /dev/null -m 3 http://127.0.0.1:$p/"; then ok=1; break; fi
    sleep 3
  done
  if [ $ok = 1 ]; then echo "    port $p ok"; else echo "    port $p FAILED"; fail=1; fi
done

if [ $fail = 1 ]; then
  echo "==> rolling back"
  ssh "$HUB" "
    if [ -d $REMOTE.prev ]; then
      cp -a $REMOTE.prev/. $REMOTE/
      cd $REMOTE && for s in ${STACKS[*]}; do
        (cd compose/\$s && docker compose --env-file $REMOTE/.env up -d) || true
      done
    fi"
  exit 1
fi
echo "==> deploy ok"
