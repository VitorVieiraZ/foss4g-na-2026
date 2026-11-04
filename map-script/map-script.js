// Mergin Maps map script: "Locate me" button.
// Click it to centre the map on your GPS position and drop a marker
// (with an accuracy circle). Click again to refresh the position.
// Runs in the Mergin Maps web map's sandboxed iframe; uses the global MerginMaps object.

import { transform, getPointResolution } from 'https://esm.sh/ol@10.8.0/proj';

const map = MerginMaps.getMap();
const mapEl = MerginMaps.getMapElement();
const view = map.getView();

// Mergin Maps app colours
const BAR = '#00423c';
const MINT = '#66c68f';
const RED = '#e1312d';

if (getComputedStyle(mapEl).position === 'static') mapEl.style.position = 'relative';

// ---------- Marker layer: our own canvas, redrawn after every map render ----------
const canvas = document.createElement('canvas');
Object.assign(canvas.style, {
  position: 'absolute', inset: '0', width: '100%', height: '100%',
  pointerEvents: 'none', zIndex: '1000',
});
mapEl.appendChild(canvas);
const ctx = canvas.getContext('2d');

let fix = null;        // { coord: [x, y] in view projection, accuracy: metres }
let pulseStart = 0;    // ms timestamp of the last drop, for the drop pulse

function toViewCoord(lon, lat) {
  const code = view.getProjection().getCode();
  if (code === 'EPSG:4326') return [lon, lat];
  if (['EPSG:3857', 'EPSG:900913', 'EPSG:102100'].includes(code)) {
    const R = 6378137;
    return [R * lon * Math.PI / 180, R * Math.log(Math.tan(Math.PI / 4 + lat * Math.PI / 360))];
  }
  return transform([lon, lat], 'EPSG:4326', code); // other projections, if known to OL
}

function draw() {
  const dpr = window.devicePixelRatio || 1;
  const w = mapEl.clientWidth, h = mapEl.clientHeight;
  if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
  }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);
  if (!fix) return;

  const px = map.getPixelFromCoordinate(fix.coord);
  if (!px) return;
  const [x, y] = px;

  // Accuracy circle (metres -> pixels)
  let mPerPx = view.getResolution();
  try { mPerPx = getPointResolution(view.getProjection(), view.getResolution(), fix.coord, 'm'); } catch (e) {}
  const r = fix.accuracy / mPerPx;
  if (r > 12 && r < 4000) {
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(102,198,143,0.18)';
    ctx.strokeStyle = 'rgba(0,66,60,0.55)';
    ctx.lineWidth = 1.5;
    ctx.fill();
    ctx.stroke();
  }

  // Drop pulse for the first 1.2 s
  const t = (performance.now() - pulseStart) / 1200;
  if (t < 1) {
    ctx.beginPath();
    ctx.arc(x, y, 10 + 30 * t, 0, Math.PI * 2);
    ctx.strokeStyle = `rgba(225,49,45,${0.6 * (1 - t)})`;
    ctx.lineWidth = 3;
    ctx.stroke();
    requestAnimationFrame(() => map.render());
  }

  // Marker: white ring + red dot
  ctx.beginPath();
  ctx.arc(x, y, 9, 0, Math.PI * 2);
  ctx.fillStyle = '#fff';
  ctx.shadowColor = 'rgba(0,0,0,0.35)';
  ctx.shadowBlur = 4;
  ctx.fill();
  ctx.shadowBlur = 0;
  ctx.beginPath();
  ctx.arc(x, y, 6, 0, Math.PI * 2);
  ctx.fillStyle = RED;
  ctx.fill();
}
map.on('postrender', draw);
new ResizeObserver(() => map.render()).observe(mapEl);

// ---------- Button + status label ----------
const box = document.createElement('div');
Object.assign(box.style, {
  position: 'absolute', right: '12px', bottom: '96px', zIndex: '1001',
  display: 'flex', alignItems: 'center', gap: '8px', flexDirection: 'row-reverse',
  fontFamily: 'Inter, system-ui, sans-serif',
});

const btn = document.createElement('button');
btn.type = 'button';
btn.title = 'Centre on my location';
btn.setAttribute('aria-label', 'Centre on my location');
Object.assign(btn.style, {
  width: '44px', height: '44px', borderRadius: '50%', border: 'none',
  background: BAR, color: '#fff', cursor: 'pointer', padding: '0',
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
});
// Crosshair icon built as SVG nodes
const NS = 'http://www.w3.org/2000/svg';
const svg = document.createElementNS(NS, 'svg');
svg.setAttribute('width', '22'); svg.setAttribute('height', '22'); svg.setAttribute('viewBox', '0 0 24 24');
svg.setAttribute('fill', 'none'); svg.setAttribute('stroke', 'currentColor');
svg.setAttribute('stroke-width', '2'); svg.setAttribute('stroke-linecap', 'round');
for (const [tag, attrs] of [
  ['circle', { cx: 12, cy: 12, r: 7 }],
  ['circle', { cx: 12, cy: 12, r: 2.5, fill: 'currentColor' }],
  ['line', { x1: 12, y1: 1, x2: 12, y2: 4 }],
  ['line', { x1: 12, y1: 20, x2: 12, y2: 23 }],
  ['line', { x1: 1, y1: 12, x2: 4, y2: 12 }],
  ['line', { x1: 20, y1: 12, x2: 23, y2: 12 }],
]) {
  const el = document.createElementNS(NS, tag);
  for (const k in attrs) el.setAttribute(k, attrs[k]);
  svg.appendChild(el);
}
btn.appendChild(svg);

const label = document.createElement('div');
Object.assign(label.style, {
  background: 'rgba(255,255,255,0.95)', color: '#273b36', fontSize: '13px',
  padding: '6px 10px', borderRadius: '6px', boxShadow: '0 1px 4px rgba(0,0,0,0.25)',
  whiteSpace: 'nowrap', display: 'none',
});

box.appendChild(btn);
box.appendChild(label);
mapEl.appendChild(box);

let hideTimer;
function say(text, ms = 4000) {
  label.textContent = text;
  label.style.display = 'block';
  clearTimeout(hideTimer);
  if (ms) hideTimer = setTimeout(() => { label.style.display = 'none'; }, ms);
}

// Don't let clicks on the control reach the map (identify popup)
for (const ev of ['click', 'pointerdown', 'pointerup', 'dblclick', 'touchstart']) {
  box.addEventListener(ev, (e) => e.stopPropagation());
}

// ---------- Geolocation ----------
// The iframe may not be allowed to ask for location; fall back to the parent page.
function geo() {
  try { if (parent && parent.navigator && parent.navigator.geolocation) return parent.navigator.geolocation; } catch (e) {}
  return navigator.geolocation;
}

let spin;
btn.addEventListener('click', () => {
  const g = geo();
  if (!g) { say('Location is not available in this browser'); return; }
  say('Finding your location…', 0);
  spin = btn.animate([{ transform: 'rotate(0deg)' }, { transform: 'rotate(360deg)' }],
    { duration: 1200, iterations: Infinity });

  g.getCurrentPosition((pos) => {
    spin && spin.cancel();
    const { longitude, latitude, accuracy } = pos.coords;
    fix = { coord: toViewCoord(longitude, latitude), accuracy: accuracy || 0 };
    pulseStart = performance.now();
    const z = view.getZoom();
    view.animate({ center: fix.coord, zoom: Math.max(z ?? 0, 17), duration: 600 });
    say(`±${Math.round(accuracy)} m · ${latitude.toFixed(5)}, ${longitude.toFixed(5)}`, 6000);
    map.render();
  }, (err) => {
    spin && spin.cancel();
    const msg = { 1: 'Location permission denied', 2: 'Position unavailable', 3: 'Location timed out' }[err.code];
    say(msg || 'Could not get location');
  }, { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 });
});
