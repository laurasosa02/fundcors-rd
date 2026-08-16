// main.js
// Entry point loaded via <script type="module" src="js/main.js" defer> in
// index.html. Imports every init-prefixed function exported by the modules
// under ./modules/ and runs them once the DOM is ready.
//
// Each init call is wrapped in its own try/catch. This is a small
// institutional site, not a SPA — if one module throws (a missing element,
// a third-party map library that failed to load, whatever), the rest of
// the page's interactivity must keep working. A broken FAQ accordion
// should never be able to take down the login form next to it.

import { initHeader } from './modules/header.js';
import { initSmoothScroll } from './modules/smoothScroll.js';
import { initScrollSpy } from './modules/scrollspy.js';
import { initReveal } from './modules/reveal.js';
import { initFaq } from './modules/faq.js';
import { initAuth } from './modules/auth.js';
import { initInscripcionForm } from './modules/inscripcionForm.js';
import { initMap } from './modules/map.js';

// Note: ./modules/api.js exports no init-prefixed function — it's a pure
// fetch/CSRF helper library consumed by auth.js and inscripcionForm.js, not
// something that runs on its own. Same for ./modules/downloads.js, which
// exports renderDownloads() (called internally by auth.js after a
// successful login/session check) rather than an init-prefixed entry
// point. Neither is called directly here; see the build report for
// details on this naming.

/**
 * Runs an init function, isolating any error it throws so a single broken
 * module can't stop the rest of main.js from running.
 * @param {string} name - label used in the console.error output
 * @param {() => unknown} fn - the init function to invoke
 */
function safeInit(name, fn) {
  try {
    const result = fn();
    // Several init functions are async and return a promise; catch
    // rejections there too instead of letting them become unhandled
    // rejections.
    if (result && typeof result.catch === 'function') {
      result.catch((err) => {
        console.error(`[main.js] ${name} failed:`, err);
      });
    }
  } catch (err) {
    console.error(`[main.js] ${name} failed:`, err);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  safeInit('initHeader', initHeader);
  safeInit('initSmoothScroll', initSmoothScroll);
  safeInit('initScrollSpy', initScrollSpy);
  safeInit('initReveal', initReveal);
  safeInit('initFaq', initFaq);
  safeInit('initAuth', initAuth);
  safeInit('initInscripcionForm', initInscripcionForm);
  safeInit('initMap', initMap);
});
