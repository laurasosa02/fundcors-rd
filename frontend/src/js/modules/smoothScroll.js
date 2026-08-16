// smoothScroll.js
// Intercepts in-page anchor link clicks and smooth-scrolls to the target,
// offsetting for the sticky header's actual rendered height.

const SCROLL_GAP = 16; // small breathing room below the header

export function initSmoothScroll() {
  document.addEventListener('click', handleClick);
}

function handleClick(event) {
  const anchor = event.target.closest('a[href^="#"]');
  if (!anchor) return;

  const href = anchor.getAttribute('href');
  if (!href || href === '#') return;

  let target;
  try {
    target = document.querySelector(href);
  } catch (err) {
    return;
  }
  if (!target) return;

  event.preventDefault();

  const header = document.getElementById('fcrd2Header');
  const headerHeight = header ? header.offsetHeight : 0;

  const targetRect = target.getBoundingClientRect();
  const currentScrollY = window.scrollY || window.pageYOffset || 0;
  const targetPosition = targetRect.top + currentScrollY - headerHeight - SCROLL_GAP;

  window.scrollTo({
    top: targetPosition,
    behavior: 'smooth',
  });
}
