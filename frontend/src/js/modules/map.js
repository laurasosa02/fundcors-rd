// map.js
// Real-time Leaflet map of the GNSS/CORS station network. Unlike the design
// reference prototype — which parsed a live NTRIP sourcetable straight from
// the browser and broke on mixed-content/CORS since the caster is plain
// HTTP — this module only ever talks to our own backend (see ./api.js),
// which does the NTRIP proxying server-side and hands back already-parsed
// station data. Nothing here invents or hardcodes a station: every marker
// on the map comes straight from the live GET /stations/ response.
//
// Leaflet itself is not bundled — it's only worth the download once the map
// section is about to scroll into view, so it's lazy-loaded from a CDN via
// an IntersectionObserver on the #estado-actual section.

import { apiFetch } from './api.js';

const LEAFLET_CSS_URL = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
const LEAFLET_JS_URL = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';

const DR_CENTER = [18.7357, -70.1627];
const DR_ZOOM = 8;

const INTERSECTION_ROOT_MARGIN = '300px';
const POLL_INTERVAL_MS = 60000;
const STATION_RADIUS_METERS = 30000;

const COLOR_FRESH = '#16a34a';
const COLOR_STALE = '#d97706';
const COLOR_UNKNOWN = '#9ca3af';

const STATUS_NO_DATA = 'Datos NTRIP no disponibles';
const STATUS_STALE_FETCH = 'No se pudo actualizar, mostrando ultimo dato disponible';

// Resolved the first time the Leaflet <script> finishes loading, so a
// second call to loadLeaflet() (shouldn't normally happen, but cheap to
// guard) reuses the same promise instead of injecting duplicate tags.
let leafletLoadPromise = null;

/**
 * Boots the real-time CORS station map. Waits for the #estado-actual
 * section to be near the viewport (via IntersectionObserver) before paying
 * the cost of loading Leaflet and fetching station data. No-ops gracefully
 * if the #fcrd2-map mount point isn't present in the DOM.
 * @returns {Promise<void>}
 */
export async function initMap() {
  const mapEl = document.getElementById('fcrd2-map');
  if (!mapEl) return;

  const dotEl = document.getElementById('fcrd2MapDot');
  const statusEl = document.getElementById('fcrd2MapStatus');
  const section = document.getElementById('estado-actual');

  const boot = () => {
    // Fire-and-forget: initMap resolves as soon as the observer (or the
    // fallback) is wired up rather than blocking on Leaflet loading + the
    // first station fetch, which could otherwise stall the rest of the
    // page's startup until the user scrolls the map into view.
    bootstrapMap(mapEl, dotEl, statusEl);
  };

  if (section && 'IntersectionObserver' in window) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            observer.disconnect();
            boot();
          }
        });
      },
      { rootMargin: INTERSECTION_ROOT_MARGIN },
    );
    observer.observe(section);
  } else {
    boot();
  }
}

/**
 * Injects Leaflet's stylesheet + script tags (once) and resolves once the
 * script has finished loading and window.L is available.
 * @returns {Promise<void>}
 */
function loadLeaflet() {
  if (window.L) return Promise.resolve();
  if (leafletLoadPromise) return leafletLoadPromise;

  leafletLoadPromise = new Promise((resolve, reject) => {
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = LEAFLET_CSS_URL;
    document.head.appendChild(link);

    const script = document.createElement('script');
    script.src = LEAFLET_JS_URL;
    script.async = true;
    script.addEventListener('load', () => resolve());
    script.addEventListener('error', () => reject(new Error('No se pudo cargar Leaflet.')));
    document.head.appendChild(script);
  });

  return leafletLoadPromise;
}

/**
 * Loads Leaflet, initializes the map exactly once centered on the
 * Dominican Republic, then performs the first station draw and starts the
 * 60s poll. Any failure to load Leaflet itself is reported through the
 * same status indicator used for a failed station fetch.
 * @param {HTMLElement} mapEl
 * @param {HTMLElement|null} dotEl
 * @param {HTMLElement|null} statusEl
 * @returns {Promise<void>}
 */
async function bootstrapMap(mapEl, dotEl, statusEl) {
  try {
    await loadLeaflet();
  } catch (err) {
    setStatus(dotEl, statusEl, COLOR_UNKNOWN, STATUS_NO_DATA);
    return;
  }

  // The section may have been removed from the DOM while Leaflet was
  // loading (or the CDN script failed silently) — bail out rather than
  // handing a detached/incomplete node to L.map().
  if (!window.L || !mapEl.isConnected) {
    setStatus(dotEl, statusEl, COLOR_UNKNOWN, STATUS_NO_DATA);
    return;
  }

  const map = window.L.map(mapEl).setView(DR_CENTER, DR_ZOOM);
  window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19,
  }).addTo(map);

  const stationLayer = window.L.layerGroup().addTo(map);

  // Tracks whether the layer has ever held real markers, so a later failed
  // fetch knows whether to report "no data at all" or "stale, but showing
  // the last known good draw".
  let hasStations = false;

  const draw = () => fetchAndDrawStations();

  /**
   * Internal: fetches the current station list from our backend and
   * (re)draws it onto stationLayer. Leaves any previously drawn markers
   * untouched on a failed/non-ok response.
   * @returns {Promise<void>}
   */
  async function fetchAndDrawStations() {
    let result;
    try {
      result = await apiFetch('/stations/');
    } catch (err) {
      reportFetchFailure();
      return;
    }

    const { ok, data } = result;
    const stations = ok && data && Array.isArray(data.stations) ? data.stations : null;

    if (!ok || !stations) {
      reportFetchFailure();
      return;
    }

    stationLayer.clearLayers();

    stations.forEach((station) => {
      if (!station) return;
      const lat = Number(station.lat);
      const lon = Number(station.lon);
      if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;

      const name = station.name || '';
      const location = station.location || '';

      window.L.circleMarker([lat, lon], {
        radius: 7,
        color: '#ffffff',
        weight: 2,
        fillColor: COLOR_FRESH,
        fillOpacity: 0.9,
      })
        .bindPopup(`<strong>${escapeHtml(name)}</strong><br>${escapeHtml(location)}`)
        .addTo(stationLayer);

      window.L.circle([lat, lon], {
        radius: STATION_RADIUS_METERS,
        color: '#dc2626',
        weight: 1.5,
        fill: false,
      }).addTo(stationLayer);
    });

    const count = stations.length;
    hasStations = count > 0;

    const stale = Boolean(data.stale);
    const color = stale ? COLOR_STALE : COLOR_FRESH;
    const label = stale
      ? `Datos desactualizados - N de estaciones: ${count}`
      : `Estacion activa - N de estaciones: ${count}`;

    setStatus(dotEl, statusEl, color, label);
  }

  /**
   * Internal: called when a station fetch fails outright (network error)
   * or comes back non-ok/malformed. Never touches stationLayer — existing
   * markers, if any, stay on the map.
   */
  function reportFetchFailure() {
    if (hasStations) {
      // Leave the dot's color as-is: it still reflects the last known
      // fresh/stale state, which is more informative than graying it out.
      setStatus(dotEl, statusEl, null, STATUS_STALE_FETCH);
    } else {
      setStatus(dotEl, statusEl, COLOR_UNKNOWN, STATUS_NO_DATA);
    }
  }

  await draw();

  let intervalId = setInterval(draw, POLL_INTERVAL_MS);

  // Nice-to-have: pause polling while the tab is hidden and resume (with an
  // immediate refresh) when it becomes visible again, instead of quietly
  // burning requests against a background tab.
  if (typeof document.visibilityState !== 'undefined') {
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'hidden') {
        if (intervalId !== null) {
          clearInterval(intervalId);
          intervalId = null;
        }
      } else if (intervalId === null) {
        draw();
        intervalId = setInterval(draw, POLL_INTERVAL_MS);
      }
    });
  }
}

/**
 * Sets the freshness dot color (skipped when color is null/undefined, so a
 * caller can update just the status text) and the status line text.
 * @param {HTMLElement|null} dotEl
 * @param {HTMLElement|null} statusEl
 * @param {string|null|undefined} color
 * @param {string} text
 */
function setStatus(dotEl, statusEl, color, text) {
  if (dotEl && color) dotEl.style.background = color;
  if (statusEl) statusEl.textContent = text;
}

/**
 * Minimal HTML-escaper for popup content built from backend station
 * name/location strings.
 * @param {unknown} value
 * @returns {string}
 */
function escapeHtml(value) {
  return String(value == null ? '' : value).replace(
    /[&<>"']/g,
    (char) =>
      ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
      })[char],
  );
}
