// Shared data loader for the from-scratch front doors. Everything comes through
// the same-origin proxy (nginx): /feed/ /kuma/ /pve/ /plex/ /mc/
// Usage:  const d = await HB.load();  HB.status('Server-Rig', 'Cobblemon') -> 'up'
(function () {
  const S = window.HB_SERVICES || [];
  const HOSTS = window.HB_HOSTS || [];
  const HOST_IP = Object.fromEntries(HOSTS.map(h => [h.name, h.ip]));

  async function j(url, ms = 8000) {
    const c = new AbortController();
    const t = setTimeout(() => c.abort(), ms);
    try {
      const r = await fetch(url, { signal: c.signal, cache: 'no-store' });
      if (!r.ok) throw new Error(r.status);
      return await r.json();
    } finally { clearTimeout(t); }
  }

  const KUMA_STATUS = { 0: 'down', 1: 'up', 2: 'pending', 3: 'maint' };
  let last = null;

  async function load() {
    const [feed, page, hb, plex, pve, guests] = await Promise.all([
      j('/feed/latest.json').catch(() => null),
      j('/kuma/api/status-page/homelab').catch(() => null),
      j('/kuma/api/status-page/heartbeat/homelab').catch(() => null),
      j('/plex/status/sessions').catch(() => null),
      j('/pve/api2/json/nodes/pve/status').catch(() => null),
      j('/pve/api2/json/cluster/resources?type=vm').catch(() => null),
    ]);

    // Kuma: flatten monitors with current status + 24h uptime
    const kuma = { groups: [], byName: {} };
    if (page && hb) {
      for (const g of page.publicGroupList || []) {
        const grp = { name: g.name, monitors: [] };
        for (const m of g.monitorList || []) {
          const beats = hb.heartbeatList?.[m.id] || [];
          const lastBeat = beats[beats.length - 1];
          const status = lastBeat ? (KUMA_STATUS[lastBeat.status] || 'pending') : 'paused';
          const up24 = hb.uptimeList?.[`${m.id}_24`];
          const mon = { id: m.id, name: m.name, status, up24, beats, ping: lastBeat?.ping ?? null };
          grp.monitors.push(mon);
          kuma.byName[m.name] = mon;
        }
        kuma.groups.push(grp);
      }
    }

    // Minecraft / Bedrock live status (real handshake) for every live game server
    const games = S.filter(s => (s.kind === 'game-mc' || s.name.startsWith('bedrock')) && s.status === 'live');
    const mc = await Promise.all(games.map(async s => {
      const ip = HOST_IP[s.host];
      const path = s.kind === 'game-mc' ? '/mc/java' : '/mc/bedrock';
      const r = await j(`${path}?host=${ip}&port=${s.port}`, 9000).catch(() => ({ online: false, players: 0, max: 0, version: '' }));
      return { ...s, ...r };
    }));

    const plexInfo = plex ? {
      streams: plex.MediaContainer?.size || 0,
      sessions: (plex.MediaContainer?.Metadata || []).map(m => ({
        user: m.User?.title, title: m.grandparentTitle ? `${m.grandparentTitle} · ${m.title}` : m.title,
        state: m.Player?.state, player: m.Player?.title,
      })),
    } : null;

    const pveInfo = pve ? {
      cpu: Math.round((pve.data.cpu || 0) * 100),
      memPct: Math.round(pve.data.memory.used / pve.data.memory.total * 100),
      memUsedGB: +(pve.data.memory.used / 2 ** 30).toFixed(1),
      memTotalGB: +(pve.data.memory.total / 2 ** 30).toFixed(1),
      rootPct: Math.round(pve.data.rootfs.used / pve.data.rootfs.total * 100),
      uptimeDays: Math.floor(pve.data.uptime / 86400),
      guests: (guests?.data || []).map(g => ({ name: g.name, type: g.type, status: g.status, vmid: g.vmid, mem: g.maxmem, cpu: g.cpu })),
    } : null;

    last = { feed, kuma, mc, plex: plexInfo, pve: pveInfo, at: new Date() };
    return last;
  }

  // Service status combining Kuma (by "<host> · <label>") and the game handshake
  function status(host, label) {
    if (!last) return 'none';
    const m = last.kuma.byName[`${host} · ${label}`];
    if (m) return m.status;
    return 'none';
  }
  function serviceStatus(s) {
    if (s.status === 'paused') return 'paused';
    if (s.status === 'retired') return 'retired';
    const g = last?.mc?.find(x => x.name === s.name);
    if (g) return g.online ? 'up' : 'down';
    return status(s.host, s.label);
  }
  function host(name) { return last?.feed?.hosts?.find(h => h.name === name) || null; }
  function worstDisk(h) {
    if (!h?.disks?.length) return null;
    return h.disks.reduce((a, b) => (b.freePct < a.freePct ? b : a));
  }
  function fmtAgo(iso) {
    if (!iso) return '';
    const s = Math.max(0, (Date.now() - new Date(iso)) / 1000);
    if (s < 90) return `${Math.round(s)}s ago`;
    if (s < 5400) return `${Math.round(s / 60)}m ago`;
    return `${(s / 3600).toFixed(1)}h ago`;
  }

  window.HB = { services: S, hosts: HOSTS, hostIp: HOST_IP, load, status, serviceStatus, host, worstDisk, fmtAgo, get last() { return last; } };
})();
