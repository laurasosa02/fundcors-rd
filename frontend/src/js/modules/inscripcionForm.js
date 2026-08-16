// inscripcionForm.js
// Wires the membership "Inscripción" form to the real backend: submits the
// four fields to POST /inscripcion/, shows the resulting success/validation
// message next to the submit button, and keeps the manual WhatsApp link
// (#fcrd2WaSend) working as a secondary option by live-updating its href
// with a prefilled summary of whatever the user has typed so far.

import { apiFetch } from './api.js';

const WA_BASE_URL = 'https://wa.me/18292504307';
const SUCCESS_MSG = 'Solicitud recibida. Nos pondremos en contacto contigo pronto.';
const GENERIC_ERROR_MSG = 'Ocurrió un error. Intenta de nuevo.';

/**
 * Boots the Inscripción form: submit handling against the backend and a
 * live-updating WhatsApp fallback link. No-ops gracefully if the form isn't
 * on the page.
 * @returns {Promise<void>}
 */
export async function initInscripcionForm() {
  const form = document.getElementById('fcrd2InscripcionForm');
  if (!form) return;

  const waLink = document.getElementById('fcrd2WaSend');

  updateWaLink(form, waLink);
  form.addEventListener('input', () => {
    updateWaLink(form, waLink);
  });

  form.addEventListener('submit', (event) => {
    handleSubmit(event, form);
  });
}

/**
 * Handles the Inscripción form submit: POST /inscripcion/, then shows a
 * success message and resets the form, or shows the first validation error
 * and leaves the form filled in so the user can fix it.
 * @param {SubmitEvent} event
 * @param {HTMLFormElement} form
 */
async function handleSubmit(event, form) {
  event.preventDefault();
  const msgEl = getOrCreateMsgEl(form);
  const fields = form.elements;

  const body = {
    nombre: fields.nombre.value,
    cedula: fields.cedula.value,
    telefono: fields.telefono.value,
    correo: fields.correo.value,
  };

  let result;
  try {
    result = await apiFetch('/inscripcion/', { method: 'POST', body });
  } catch (err) {
    setMessage(msgEl, GENERIC_ERROR_MSG);
    return;
  }

  const { status, data } = result;

  if (status === 201) {
    setMessage(msgEl, (data && data.message) || SUCCESS_MSG);
    form.reset();
    return;
  }

  if (status === 400 && data && data.errors) {
    setMessage(msgEl, firstErrorMessage(data.errors));
    return;
  }

  setMessage(msgEl, GENERIC_ERROR_MSG);
}

/**
 * Finds the submit button's status message paragraph, creating it right
 * after the submit button if it doesn't exist yet.
 * @param {HTMLFormElement} form
 * @returns {HTMLElement}
 */
function getOrCreateMsgEl(form) {
  let msgEl = form.querySelector('.fcrd2-form-msg');
  if (msgEl) return msgEl;

  msgEl = document.createElement('p');
  msgEl.className = 'fcrd2-form-msg';
  msgEl.setAttribute('role', 'status');

  const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
  if (submitBtn && submitBtn.parentNode) {
    submitBtn.insertAdjacentElement('afterend', msgEl);
  } else {
    form.appendChild(msgEl);
  }

  return msgEl;
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

/**
 * Rebuilds the WhatsApp link's href from whatever the user has typed so
 * far, only including fields that currently have a non-empty value.
 * @param {HTMLFormElement} form
 * @param {HTMLAnchorElement|null} waLink
 */
function updateWaLink(form, waLink) {
  if (!waLink) return;

  const fields = form.elements;
  const nombre = fields.nombre ? fields.nombre.value.trim() : '';
  const cedula = fields.cedula ? fields.cedula.value.trim() : '';
  const telefono = fields.telefono ? fields.telefono.value.trim() : '';
  const correo = fields.correo ? fields.correo.value.trim() : '';

  let text = 'Hola, quiero inscribirme a la red FUNDCORSRD.';
  if (nombre) text += ` Nombre: ${nombre}.`;
  if (cedula) text += ` Cedula: ${cedula}.`;
  if (telefono) text += ` Telefono: ${telefono}.`;
  if (correo) text += ` Correo: ${correo}.`;

  waLink.href = `${WA_BASE_URL}?text=${encodeURIComponent(text)}`;
}
