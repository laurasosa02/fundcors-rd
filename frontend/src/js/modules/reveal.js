// reveal.js
// Scroll-triggered reveal animation for the hero and top-level sections,
// with a timed fallback so content never stays hidden if IO doesn't fire.

const REVEAL_CLASS = 'fcrd2-reveal';
const IN_CLASS = 'in';
const SAFETY_TIMEOUT = 2500;

export function initReveal() {
  const targets = getRevealTargets();
  if (!targets.length) return;

  targets.forEach((el) => el.classList.add(REVEAL_CLASS));

  const observer = new IntersectionObserver(
    (entries, obs) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add(IN_CLASS);
          obs.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.12 }
  );

  targets.forEach((el) => observer.observe(el));

  window.setTimeout(() => {
    document.querySelectorAll(`.${REVEAL_CLASS}`).forEach((el) => {
      el.classList.add(IN_CLASS);
    });
  }, SAFETY_TIMEOUT);
}

function getRevealTargets() {
  const targets = [];
  const seen = new Set();

  const hero = document.getElementById('fcrd2Hero') || document.querySelector('.fcrd2-hero');
  if (hero && !seen.has(hero)) {
    targets.push(hero);
    seen.add(hero);
  }

  const container = document.querySelector('main') || document.body;
  Array.from(container.children)
    .filter((el) => el.tagName === 'SECTION')
    .forEach((section) => {
      if (!seen.has(section)) {
        targets.push(section);
        seen.add(section);
      }
    });

  return targets;
}
