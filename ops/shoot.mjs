/**
 * Screenshot every front-door variant (and the Uptime Kuma status page) at
 * desktop and phone size. Evidence for docs/comparison.md and every phase PR.
 *
 *   node ops/shoot.mjs [outDir] [hubIp] [name,name]
 *   node ops/shoot.mjs docs/screenshots/phase-1 192.168.1.141
 *
 * Full-page JPEG q85 (a DPR-2 phone PNG is ~1 MB; these get committed).
 */
import puppeteer from 'puppeteer';
import fs from 'fs';
import path from 'path';

const OUT = process.argv[2] || 'docs/screenshots/phase-1';
const HUB = process.argv[3] || '192.168.1.141';
fs.mkdirSync(OUT, { recursive: true });

const ONLY = (process.argv[4] || '').split(',').filter(Boolean);
const TARGETS_ALL = [
  { name: 'h1-console', url: `http://${HUB}:3101/` },
  { name: 'h2-rack',    url: `http://${HUB}:3102/` },
  { name: 'h3-pocket',  url: `http://${HUB}:3103/` },
  { name: 'g1-feed',    url: `http://${HUB}:3201/` },
  { name: 'g2-ops',     url: `http://${HUB}:3202/` },
  { name: 'g3-pages',   url: `http://${HUB}:3203/` },
  { name: 'g3-games',   url: `http://${HUB}:3203/games` },
  { name: 'c1-flight-deck', url: `http://${HUB}:3301/` },
  { name: 'c2-rack',    url: `http://${HUB}:3302/` },
  { name: 'c3-transit', url: `http://${HUB}:3303/` },
  { name: 'kuma-status', url: `http://${HUB}:3001/status/homelab` },
];
const TARGETS = ONLY.length ? TARGETS_ALL.filter(t => ONLY.includes(t.name)) : TARGETS_ALL;
const VIEWPORTS = {
  desktop: { width: 1440, height: 900, deviceScaleFactor: 1 },
  mobile:  { width: 390,  height: 844, deviceScaleFactor: 2, isMobile: true, hasTouch: true },
};
const sleep = ms => new Promise(r => setTimeout(r, ms));

const browser = await puppeteer.launch({ headless: true, args: ['--ignore-certificate-errors'] });
try {
  for (const [vpName, vp] of Object.entries(VIEWPORTS)) {
    const page = await browser.newPage();
    await page.setViewport(vp);
    for (const t of TARGETS) {
      const file = path.join(OUT, `${t.name}-${vpName}.jpg`);
      try {
        await page.goto(t.url, { waitUntil: 'networkidle2', timeout: 45000 });
        await sleep(6000); // widgets poll after first paint; minecraft/proxmox take a few seconds
        await page.screenshot({ path: file, type: 'jpeg', quality: 85, fullPage: true });
        console.log(`saved ${file}`);
      } catch (e) {
        console.log(`FAILED ${t.name} ${vpName}: ${e.message}`);
      }
    }
    await page.close();
  }
} finally {
  await browser.close();
}
