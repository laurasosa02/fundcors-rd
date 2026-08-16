// downloads.js
// The four download rows are static HTML (fixed institutional links), not
// per-user data, so this module's real job is not to render rows — it's to
// reconfirm with the backend that the session is still authorized every
// time the gated view is entered, since the session could have expired
// between the initial page load and the user clicking into this view. As
// an optional bonus it also refreshes each static row's href from the
// backend response, matched by the row's visible label text.

import { apiFetch } from './api.js';

const SESSION_EXPIRED_MSG = 'Tu sesión expiró, inicia sesión de nuevo.';

/**
 * Reconfirms download access with GET /downloads/. If the backend says the
 * session is no longer authorized, sends the user back to the auth card
 * with an explanatory message. Otherwise, opportunistically refreshes the
 * static rows' hrefs from the response.
 * @returns {Promise<void>}
 */
export async function renderDownloads() {
  let result;
  try {
    result = await apiFetch('/downloads/');
  } catch (err) {
    // Network failure: leave the static rows as-is rather than bouncing
    // the user out of a session that may still be valid.
    return;
  }

  const { ok, status, data } = result;

  if (status === 401 || status === 403) {
    revokeAccess();
    return;
  }

  if (ok && data && Array.isArray(data.downloads)) {
    refreshRowLinks(data.downloads);
  }
}

/**
 * Hides the downloads block, shows the auth card again, and leaves an
 * explanatory message in the login form.
 */
function revokeAccess() {
  const authCard = document.getElementById('fcrd2AuthCard');
  const downloads = document.getElementById('fcrd2Downloads');
  const loginMsg = document.getElementById('fcrd2LoginMsg');

  if (downloads) downloads.hidden = true;
  if (authCard) authCard.hidden = false;
  if (loginMsg) loginMsg.textContent = SESSION_EXPIRED_MSG;
}

/**
 * Optional belt-and-suspenders refresh of the static rows' hrefs, matching
 * each backend entry to a row by its visible label text. Skips gracefully
 * when a label doesn't match anything in the DOM.
 * @param {Array<{label?: string, description?: string, url?: string}>} items
 */
function refreshRowLinks(items) {
  const list = document.querySelector('.fcrd2-download-list');
  if (!list) return;

  const rows = Array.from(list.querySelectorAll('.fcrd2-download-row'));
  if (!rows.length) return;

  items.forEach((item) => {
    if (!item || !item.label || !item.url) return;

    const label = item.label.trim();
    const row = rows.find((candidate) => {
      const labelEl = candidate.querySelector('.label');
      return labelEl && labelEl.textContent.trim() === label;
    });
    if (!row) return;

    const link = row.querySelector('.fcrd2-download-action');
    if (link) link.href = item.url;
  });
}
