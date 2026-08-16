// header.js
// Handles sticky header scroll state, hide-on-scroll-down, mobile hamburger
// drawer, and the "Nosotros" dropdown.

const HEADER_HIDE_THRESHOLD = 84; // approx header height in px
const SCROLLED_THRESHOLD = 8;
// Minimum net scroll distance (px) since the last state change before the
// header's hide/show state is allowed to flip. Without this, momentum/
// inertial scrolling (trackpads especially) produces tiny, noisy
// frame-to-frame direction changes that make the header flicker
// show/hide rapidly instead of staying stable.
const SCROLL_DELTA_TOLERANCE = 6;
const MOBILE_BREAKPOINT = 980;

export function initHeader() {
  const header = document.getElementById('fcrd2Header');
  if (!header) return;

  initScrollBehavior(header);
  initMobileToggle(header);
  initNosotrosDropdown();
}

function initScrollBehavior(header) {
  // anchorY is the reference point a scroll gesture is measured from. It
  // only moves once we've confirmed a real, deliberate scroll (net delta
  // past the tolerance) — small back-and-forth jitter around a resting
  // point never accumulates into a state change, which is what keeps the
  // bar from flickering.
  let anchorY = Math.max(window.scrollY || 0, 0);
  let ticking = false;

  const update = () => {
    const currentY = Math.max(window.scrollY || 0, 0);

    header.classList.toggle('fcrd2-scrolled', currentY > SCROLLED_THRESHOLD);

    if (currentY <= HEADER_HIDE_THRESHOLD) {
      // Always show the header near the very top of the page, regardless
      // of scroll direction.
      header.classList.remove('fcrd2-hide');
      anchorY = currentY;
    } else {
      const delta = currentY - anchorY;
      if (delta > SCROLL_DELTA_TOLERANCE) {
        header.classList.add('fcrd2-hide');
        anchorY = currentY;
      } else if (delta < -SCROLL_DELTA_TOLERANCE) {
        header.classList.remove('fcrd2-hide');
        anchorY = currentY;
      }
      // else: net movement since the anchor is still within tolerance —
      // treat it as scroll noise and leave both the visibility state and
      // the anchor alone, so a slow/deliberate scroll keeps accumulating
      // toward the threshold instead of being reset every frame.
    }

    ticking = false;
  };

  window.addEventListener(
    'scroll',
    () => {
      if (!ticking) {
        window.requestAnimationFrame(update);
        ticking = true;
      }
    },
    { passive: true }
  );
}

function initMobileToggle(header) {
  const toggle = document.getElementById('fcrd2MobileToggle');
  const overlay = document.getElementById('fcrd2MenuOverlay');
  if (!toggle || !overlay) return;

  const openMenu = () => {
    toggle.classList.add('open');
    overlay.classList.add('open');
    overlay.setAttribute('aria-hidden', 'false');
    toggle.setAttribute('aria-expanded', 'true');
    document.body.style.overflow = 'hidden';
  };

  const closeMenu = () => {
    toggle.classList.remove('open');
    overlay.classList.remove('open');
    overlay.setAttribute('aria-hidden', 'true');
    toggle.setAttribute('aria-expanded', 'false');
    document.body.style.overflow = '';
  };

  toggle.addEventListener('click', () => {
    if (overlay.classList.contains('open')) {
      closeMenu();
    } else {
      openMenu();
    }
  });

  overlay.querySelectorAll('a').forEach((link) => {
    link.addEventListener('click', closeMenu);
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && overlay.classList.contains('open')) {
      closeMenu();
    }
  });

  window.addEventListener('resize', () => {
    if (window.innerWidth > MOBILE_BREAKPOINT && overlay.classList.contains('open')) {
      closeMenu();
    }
  });
}

function initNosotrosDropdown() {
  const ddBtn = document.getElementById('fcrd2DdBtn');
  const dd = document.getElementById('fcrd2Dd');
  if (!ddBtn || !dd) return;

  ddBtn.addEventListener('click', (event) => {
    event.stopPropagation();
    dd.classList.toggle('open');
  });

  document.addEventListener('click', (event) => {
    if (!dd.contains(event.target)) {
      dd.classList.remove('open');
    }
  });
}
