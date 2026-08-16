// header.js
// Handles sticky header scroll state, hide-on-scroll-down, mobile hamburger
// drawer, and the "Nosotros" dropdown.

const HEADER_HIDE_THRESHOLD = 84; // approx header height in px
const SCROLLED_THRESHOLD = 8;
const MOBILE_BREAKPOINT = 980;

export function initHeader() {
  const header = document.getElementById('fcrd2Header');
  if (!header) return;

  initScrollBehavior(header);
  initMobileToggle(header);
  initNosotrosDropdown();
}

function initScrollBehavior(header) {
  let lastScrollY = window.scrollY || 0;
  let ticking = false;

  const update = () => {
    const currentScrollY = window.scrollY || 0;

    if (currentScrollY > SCROLLED_THRESHOLD) {
      header.classList.add('fcrd2-scrolled');
    } else {
      header.classList.remove('fcrd2-scrolled');
    }

    const scrollingDown = currentScrollY > lastScrollY;

    if (scrollingDown && currentScrollY > HEADER_HIDE_THRESHOLD) {
      header.classList.add('fcrd2-hide');
    } else if (!scrollingDown) {
      header.classList.remove('fcrd2-hide');
    }

    lastScrollY = currentScrollY;
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
