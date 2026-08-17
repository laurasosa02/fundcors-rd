// auth.js
// Wires the login/register auth card: tab switching, the session check on
// load, the register/login form submissions, and logout. Talks to the
// backend only through apiFetch (see ./api.js) and swaps visibility
// between the auth card and the gated downloads block based on session
// state.

import { apiFetch } from './api.js';
import { renderDownloads } from './downloads.js';
import { RECAPTCHA_SITE_KEY } from '../config.js';

const REGISTER_SUCCESS_MSG =
  'Revisa tu correo para verificar tu cuenta y activar tu acceso de inmediato.';
const PASSWORD_MISMATCH_MSG = 'Las contraseñas no coinciden.';
const RECAPTCHA_REQUIRED_MSG = 'Por favor, completa la verificación de seguridad.';
const LOGIN_INVALID_MSG = 'Credenciales inválidas.';
const GENERIC_ERROR_MSG = 'Ocurrió un error. Intenta de nuevo.';

// reCAPTCHA state. The widget renders explicitly (see the script tag and
// the fcrd-recaptcha-ready event dispatched in index.html) rather than
// automatically, because its container lives inside the "Registrarse"
// tab panel, which starts hidden — auto-render into a display:none
// container doesn't size correctly. Rendering is deferred until both the
// API script has loaded AND the register tab has been opened at least
// once, whichever happens last — recaptchaApiReady starts out true if
// the script had *already* finished loading (and dispatched its event)
// before this module got a chance to run and add the listener below.
let recaptchaApiReady = typeof window.grecaptcha !== 'undefined';
let recaptchaWidgetId = null;

window.addEventListener('fcrd-recaptcha-ready', () => {
  recaptchaApiReady = true;
  tryRenderRecaptcha();
});

function tryRenderRecaptcha() {
  if (!recaptchaApiReady || recaptchaWidgetId !== null) return;
  const container = document.getElementById('fcrd2Recaptcha');
  if (!container || typeof window.grecaptcha === 'undefined' || !window.grecaptcha.render) return;

  recaptchaWidgetId = window.grecaptcha.render(container, { sitekey: RECAPTCHA_SITE_KEY });
}

/**
 * Boots the authentication UI: tab switching, the initial session check,
 * and the register/login/logout handlers.
 * @returns {Promise<void>}
 */
export async function initAuth() {
  const authCard = document.getElementById('fcrd2AuthCard');
  const downloads = document.getElementById('fcrd2Downloads');
  const loginForm = document.getElementById('fcrd2LoginForm');
  const registerForm = document.getElementById('fcrd2RegisterForm');
  const logoutBtn = document.getElementById('fcrd2LogoutBtn');

  initTabs(authCard);

  if (loginForm) {
    loginForm.addEventListener('submit', (event) => {
      handleLogin(event, loginForm, authCard, downloads);
    });
  }

  if (registerForm) {
    registerForm.addEventListener('submit', (event) => {
      handleRegister(event, registerForm);
    });
  }

  if (logoutBtn) {
    logoutBtn.addEventListener('click', () => {
      handleLogout(authCard, downloads);
    });
  }

  await checkSession(authCard, downloads);
}

/**
 * Wires the login/register tab buttons to toggle the active tab, panel,
 * and subtitle.
 * @param {HTMLElement|null} authCard
 */
function initTabs(authCard) {
  if (!authCard) return;

  const tabs = Array.from(authCard.querySelectorAll('.fcrd2-auth-tab'));
  tabs.forEach((tab) => {
    tab.addEventListener('click', () => {
      switchTab(authCard, tab.dataset.tab);
    });
  });
}

/**
 * Activates the given tab (login/register) within the auth card, showing
 * its panel and subtitle and hiding the other pair.
 * @param {HTMLElement} authCard
 * @param {string} target - 'login' or 'register'
 */
function switchTab(authCard, target) {
  if (!authCard || !target) return;

  authCard.querySelectorAll('.fcrd2-auth-tab').forEach((tab) => {
    tab.classList.toggle('active', tab.dataset.tab === target);
  });

  authCard.querySelectorAll('.fcrd2-auth-panel').forEach((panel) => {
    panel.style.display = panel.dataset.tabPanel === target ? '' : 'none';
  });

  authCard.querySelectorAll('.sub[data-tab-sub]').forEach((sub) => {
    sub.style.display = sub.dataset.tabSub === target ? '' : 'none';
  });

  if (target === 'register') tryRenderRecaptcha();
}

/**
 * Checks GET /auth/me/ and shows either the gated downloads block or the
 * auth card depending on whether the session is authenticated + approved.
 * @param {HTMLElement|null} authCard
 * @param {HTMLElement|null} downloads
 */
async function checkSession(authCard, downloads) {
  let data = null;

  try {
    ({ data } = await apiFetch('/auth/me/'));
  } catch (err) {
    data = null;
  }

  const isApproved = Boolean(data && data.authenticated && data.status === 'approved');

  if (isApproved) {
    showDownloads(authCard, downloads);
    await renderDownloads();
  } else {
    showAuthCard(authCard, downloads);
  }
}

/**
 * Handles the register form submit: client-side password match check,
 * then POST /auth/register/.
 * @param {SubmitEvent} event
 * @param {HTMLFormElement} form
 */
async function handleRegister(event, form) {
  event.preventDefault();
  const msgEl = document.getElementById('fcrd2RegisterMsg');
  const fields = form.elements;

  const password = fields.password.value;
  const passwordConfirm = fields.password_confirm.value;

  if (password !== passwordConfirm) {
    setMessage(msgEl, PASSWORD_MISMATCH_MSG);
    return;
  }

  const recaptchaToken =
    recaptchaWidgetId !== null && window.grecaptcha
      ? window.grecaptcha.getResponse(recaptchaWidgetId)
      : '';

  if (!recaptchaToken) {
    setMessage(msgEl, RECAPTCHA_REQUIRED_MSG);
    return;
  }

  const body = {
    nombre: fields.nombre.value,
    cedula: fields.cedula.value,
    telefono: fields.telefono.value,
    email: fields.email.value,
    password,
    password_confirm: passwordConfirm,
    recaptcha_token: recaptchaToken,
  };

  let result;
  try {
    result = await apiFetch('/auth/register/', { method: 'POST', body });
  } catch (err) {
    setMessage(msgEl, GENERIC_ERROR_MSG);
    resetRecaptcha();
    return;
  }

  const { status, data } = result;

  if (status === 201) {
    setMessage(msgEl, REGISTER_SUCCESS_MSG);
    form.reset();
    resetRecaptcha();
    return;
  }

  // reCAPTCHA tokens are single-use — any failed submission needs a fresh
  // one before the user can retry, success or not.
  resetRecaptcha();

  if (status === 400 && data && data.errors) {
    setMessage(msgEl, firstErrorMessage(data.errors));
    return;
  }

  setMessage(msgEl, GENERIC_ERROR_MSG);
}

function resetRecaptcha() {
  if (recaptchaWidgetId !== null && window.grecaptcha) {
    window.grecaptcha.reset(recaptchaWidgetId);
  }
}

/**
 * Handles the login form submit: POST /auth/login/, then either reveals
 * the downloads block or shows the appropriate error message.
 * @param {SubmitEvent} event
 * @param {HTMLFormElement} form
 * @param {HTMLElement|null} authCard
 * @param {HTMLElement|null} downloads
 */
async function handleLogin(event, form, authCard, downloads) {
  event.preventDefault();
  const msgEl = document.getElementById('fcrd2LoginMsg');
  const fields = form.elements;

  const body = {
    email: fields.email.value,
    password: fields.password.value,
  };

  let result;
  try {
    result = await apiFetch('/auth/login/', { method: 'POST', body });
  } catch (err) {
    setMessage(msgEl, GENERIC_ERROR_MSG);
    return;
  }

  const { status, data } = result;

  if (status === 200 && data && data.status === 'approved') {
    setMessage(msgEl, '');
    showDownloads(authCard, downloads);
    await renderDownloads();
    return;
  }

  if (status === 401) {
    setMessage(msgEl, LOGIN_INVALID_MSG);
    return;
  }

  if (status === 403) {
    setMessage(msgEl, (data && data.message) || GENERIC_ERROR_MSG);
    return;
  }

  setMessage(msgEl, GENERIC_ERROR_MSG);
}

/**
 * Handles the logout button: POST /auth/logout/, then unconditionally
 * returns the UI to the auth card on the login tab.
 * @param {HTMLElement|null} authCard
 * @param {HTMLElement|null} downloads
 */
async function handleLogout(authCard, downloads) {
  try {
    await apiFetch('/auth/logout/', { method: 'POST' });
  } catch (err) {
    // Ignore network errors here — we reset the UI to the auth card
    // regardless of the outcome.
  }

  showAuthCard(authCard, downloads);
  switchTab(authCard, 'login');

  const loginMsg = document.getElementById('fcrd2LoginMsg');
  setMessage(loginMsg, '');
}

function showDownloads(authCard, downloads) {
  if (authCard) authCard.hidden = true;
  if (downloads) downloads.hidden = false;
}

function showAuthCard(authCard, downloads) {
  if (authCard) authCard.hidden = false;
  if (downloads) downloads.hidden = true;
}

function setMessage(el, text) {
  if (el) el.textContent = text;
}

/**
 * Pulls the first validation message out of a DRF-style errors object
 * ({ field: [messages...], __all__: [messages...] }).
 * @param {Record<string, string[]>} errors
 * @returns {string}
 */
function firstErrorMessage(errors) {
  const keys = Object.keys(errors);
  for (let i = 0; i < keys.length; i++) {
    const value = errors[keys[i]];
    if (Array.isArray(value) && value.length) {
      return value[0];
    }
  }
  return GENERIC_ERROR_MSG;
}
