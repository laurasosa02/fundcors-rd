// api.js
// Thin fetch wrapper shared by the rest of the app for talking to the
// Django backend: resolves the CSRF cookie/token once per page load,
// serializes JSON bodies, and normalizes every response to
// { ok, status, data } instead of throwing on non-2xx statuses.

import { API_BASE_URL, CSRF_COOKIE_NAME, CSRF_HEADER_NAME } from '../config.js';

const CSRF_UNSAFE_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE'];

// Module-level cache: once ensureCsrf() has been kicked off, later calls
// (even concurrent ones) reuse the same in-flight/resolved request instead
// of hitting the backend again.
let csrfRequest = null;
let csrfToken = null;

/**
 * Reads a cookie value by name from document.cookie.
 * @param {string} name
 * @returns {string|null}
 */
export function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === `${name}=`) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

/**
 * Makes sure Django has set the csrftoken cookie, fetching it exactly once
 * per page load. Prefers the cookie value once it's set; falls back to the
 * csrfToken field of the endpoint's JSON body if the cookie can't be read
 * (e.g. HttpOnly in some environment). Resolved value is cached on the
 * module for apiFetch to reuse.
 * @returns {Promise<void>}
 */
export async function ensureCsrf() {
  if (!csrfRequest) {
    csrfRequest = (async () => {
      const response = await fetch(`${API_BASE_URL}/auth/csrf/`, {
        method: 'GET',
        credentials: 'include',
      });

      let body = null;
      try {
        body = await response.json();
      } catch (err) {
        body = null;
      }

      csrfToken = getCookie(CSRF_COOKIE_NAME) || (body && body.csrfToken) || null;
    })();

    // Let a failed attempt be retried by a later call instead of leaving
    // every future request permanently stuck on a rejected promise.
    csrfRequest.catch(() => {
      csrfRequest = null;
    });
  }

  return csrfRequest;
}

function isPlainObject(value) {
  return Object.prototype.toString.call(value) === '[object Object]';
}

/**
 * Generic fetch wrapper for the app. Always sends credentials, attaches the
 * CSRF header for unsafe methods, and JSON-encodes plain-object bodies.
 * Never throws for non-2xx HTTP responses (401/403/429/400 validation
 * errors, etc.) — callers inspect `ok`/`status`/`data` themselves. Only a
 * genuine network failure rejects the returned promise.
 * @param {string} path - e.g. '/donations/'
 * @param {RequestInit} [options]
 * @returns {Promise<{ ok: boolean, status: number, data: any }>}
 */
export async function apiFetch(path, options = {}) {
  const { method, headers, body, ...rest } = options;
  const normalizedMethod = (method || 'GET').toUpperCase();

  const finalHeaders = new Headers(headers || {});
  let finalBody = body;

  if (CSRF_UNSAFE_METHODS.includes(normalizedMethod)) {
    await ensureCsrf();
    if (csrfToken) {
      finalHeaders.set(CSRF_HEADER_NAME, csrfToken);
    }
  }

  if (isPlainObject(finalBody)) {
    finalBody = JSON.stringify(finalBody);
    if (!finalHeaders.has('Content-Type')) {
      finalHeaders.set('Content-Type', 'application/json');
    }
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    method: normalizedMethod,
    headers: finalHeaders,
    body: finalBody,
    credentials: 'include',
  });

  const contentType = response.headers.get('Content-Type') || '';
  const data = contentType.includes('application/json') ? await response.json() : null;

  return {
    ok: response.ok,
    status: response.status,
    data,
  };
}
