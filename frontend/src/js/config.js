// config.js
// Central place for environment-dependent frontend settings. Only this file
// should know about hostnames, backend URLs, and Django cookie/header names.

const isLocalHost =
  window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

// Placeholder production backend subdomain — swap this once real deployment
// details are confirmed. Everything else in the app reads API_BASE_URL,
// never a hardcoded URL, so this is the only line that needs to change.
//
// The dev backend origin is built from the page's own hostname (not a
// hardcoded "localhost" literal) because browsers treat localhost and
// 127.0.0.1 as different origins for CORS purposes even though they
// resolve to the same machine — this way it always matches however the
// frontend dev server was actually opened.
export const API_BASE_URL = isLocalHost
  ? `${window.location.protocol}//${window.location.hostname}:8000`
  : 'https://api.fundcorsrd.com';

// Django's default CSRF cookie/header names.
export const CSRF_COOKIE_NAME = 'csrftoken';
export const CSRF_HEADER_NAME = 'X-CSRFToken';

// reCAPTCHA v2 site key. Site keys are meant to be public (they're always
// visible in the page source of any site using reCAPTCHA) — only the
// matching secret key must stay server-side (see the backend's
// RECAPTCHA_SECRET_KEY setting).
//
// This is the real production site key for fundcorsrd.com, issued at
// https://www.google.com/recaptcha/admin (swapped in from Google's public
// test key on 2026-08-20 — see that commit for the prior test-key value).
// The matching RECAPTCHA_SECRET_KEY must be set as a real environment
// variable wherever config.settings.prod actually runs; without it,
// registration fails closed rather than silently accepting no protection.
export const RECAPTCHA_SITE_KEY = '6LeCI40tAAAAAN-qNHx-ziQoAX-lwoTkUnpw5CeQ';
